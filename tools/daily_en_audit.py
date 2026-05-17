"""Daily EN audit — three-pronged health check on each live brochure.

For each brochure, fetches the live WordPress page and runs:

  1. TOGGLE  — is the EN toggle wired correctly?
                 · setLang defined
                 · btn-vi / btn-en both have working bindings (onclick or addEventListener)
                 · VI_STRINGS / EN_STRINGS arrays present + populated
                 · No JS syntax errors anywhere
  2. SECTIONS — every brochure section (01-09 + hero + listings + footer)
                has its prose translatable. Walks DOM, identifies VN text,
                checks whether it's in the translation arrays OR has
                data-vi/data-en attrs. Flags Notion → live gaps separately.
  3. CHARTS   — does this brochure have a chart bilingual mechanism?
                 · Turkey-style buildCharts(lang) wrapper, OR
                 · post-setLang Chart.instances translator
                If neither, charts will stay Vietnamese on EN click.

Output: per-brochure aggregated status, written to
.diagnostics/daily-en-audit.json. Designed to be parsed by the
daily-en-audit.yml workflow which surfaces failures as GitHub Issues.

Run:
    python tools/daily_en_audit.py             # all 12, fetch live
    python tools/daily_en_audit.py portugal    # one alias
    python tools/daily_en_audit.py --local     # use local files, skip fetch
"""
from __future__ import annotations

import html as html_lib
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIAGNOSTICS = ROOT / ".diagnostics"

sys.path.insert(0, str(ROOT / "tools"))
from check_en_translation_coverage import (
    check_translation_coverage,
    ALIAS_TO_FILENAME,
    is_vietnamese,
    is_skippable,
    extract_visible_text,
    parse_vi_en_arrays,  # uses the corrected state-machine parser
)
from check_live_en_coverage import LIVE_SLUG, LIVE_BASE, UA

# ANSI
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
GRAY = "\033[90m"
BOLD = "\033[1m"
RESET = "\033[0m"


# ── Check 1: TOGGLE wiring ────────────────────────────────────────────
def check_toggle(html: str) -> dict:
    """Verify the EN toggle is correctly wired."""
    issues = []

    if 'function setLang' not in html:
        issues.append('setLang function missing')

    # Both buttons exist
    if 'id="btn-vi"' not in html: issues.append('#btn-vi button missing')
    if 'id="btn-en"' not in html: issues.append('#btn-en button missing')

    # Buttons have a way to fire setLang — onclick OR addEventListener
    has_inline = 'onclick="setLang' in html
    has_bind = (
        'btn-en\').addEventListener' in html
        or 'btn-en").addEventListener' in html
        or 'getElementById("btn-en")' in html and 'addEventListener' in html
    )
    if not (has_inline or has_bind):
        issues.append('btn-en has no click handler (KSES strip + no addEventListener)')

    # Arrays populated
    vi_m = re.search(r'(?:const|let|var)\s+VI_STRINGS\s*=\s*(\[[\s\S]+?\])\s*;', html)
    en_m = re.search(r'(?:const|let|var)\s+EN_STRINGS\s*=\s*(\[[\s\S]+?\])\s*;', html)
    if not vi_m: issues.append('VI_STRINGS array missing')
    if not en_m: issues.append('EN_STRINGS array missing')

    if vi_m and en_m:
        vi_items = re.findall(r"['\"]((?:[^'\"\\]|\\.)+)['\"]", vi_m.group(1))
        en_items = re.findall(r"['\"]((?:[^'\"\\]|\\.)+)['\"]", en_m.group(1))
        if len(vi_items) < 50:
            issues.append(f'VI_STRINGS only {len(vi_items)} entries — sparse coverage')
        empty_en = sum(1 for s in en_items if not s)
        if empty_en > 5:
            issues.append(f'{empty_en} EN_STRINGS entries are empty')
        # Small diffs are fine — string-replace uses by-value matching, not by index
        if abs(len(vi_items) - len(en_items)) > 15:
            issues.append(f'VI/EN length mismatch ({len(vi_items)} vs {len(en_items)})')

    # No \" in scripts — KSES unescape trap
    for m in re.finditer(r'<script[^>]*>(.*?)</script>', html, re.DOTALL):
        body = m.group(1)
        if r'\"' in body and 'application/ld+json' not in m.group(0)[:60]:
            issues.append('Found \\\" in <script> — KSES unescape will break parsing')
            break

    return {
        'pass': len(issues) == 0,
        'issues': issues,
    }


# ── Check 2: SECTION coverage ─────────────────────────────────────────
SECTION_IDS = ['overview', 'investment', 'listings', 'process', 'family', 'tax',
               'citizenship', 'compare', 'proscons', 'nac']


def split_html_by_sections(html: str) -> dict:
    """Split body HTML into per-section chunks keyed by section id."""
    out = {'hero': '', 'footer': ''}
    # Hero is before first <section
    first_section = html.find('<section')
    if first_section > 0:
        out['hero'] = html[:first_section]
    # Walk each <section id="X">...</section>
    for m in re.finditer(r'<section[^>]+id="([^"]+)"[^>]*>([\s\S]*?)</section>', html):
        sid = m.group(1)
        out[sid] = m.group(2)
    # Footer
    footer_m = re.search(r'<footer[^>]*>([\s\S]*?)</footer>', html)
    if footer_m:
        out['footer'] = footer_m.group(1)
    return out


def check_sections(html: str, payload: dict | None) -> dict:
    """Per-section translation coverage. Flag Notion-has-EN vs no-EN."""
    sections = split_html_by_sections(html)

    # Build vi→en map from VI_STRINGS / EN_STRINGS (use the corrected
    # state-machine parser, not the regex — regex breaks on inner quotes
    # inside HTML attributes and produces misaligned pairs).
    def _normalize_quotes(t):
        """Tolerate ”/" and ’/' differences between array + DOM."""
        return t.replace('”', '"').replace('“', '"').replace('’', "'").replace('‘', "'")

    vi_items, en_items = parse_vi_en_arrays(html)
    vi_to_en = {}
    for i, v in enumerate(vi_items):
        en = en_items[i].strip() if i < len(en_items) else ''
        if not en: continue
        # Tag-rich version (matches HTML innerHTML at click time)
        for variant in {v.strip(), _normalize_quotes(v.strip())}:
            vi_to_en[variant] = en
        # Plain-text version (matches DOM text extracted by audit)
        plain_v = re.sub(r'<[^>]+>', '', v).strip()
        if plain_v:
            plain_e = re.sub(r'<[^>]+>', '', en).strip()
            for variant in {plain_v, _normalize_quotes(plain_v)}:
                if variant not in vi_to_en:
                    vi_to_en[variant] = plain_e

    # Notion EN map
    notion_vi_to_en = {}
    if payload:
        for k, v in payload.items():
            if not k.endswith('_en'): continue
            base = k[:-3]
            vi = payload.get(base + '_vi', '')
            if vi and v:
                notion_vi_to_en[str(vi).strip()] = str(v).strip()

    per_section = {}
    notion_gaps = []  # Real gaps — Notion has EN but brochure doesn't

    for sid, snippet in sections.items():
        if not snippet: continue
        visible = extract_visible_text(snippet)
        translated = fixable_gap = acceptable_gap = skip = 0
        for text in visible:
            if not is_vietnamese(text): continue
            if is_skippable(text):
                skip += 1
                continue
            if text in vi_to_en and vi_to_en[text]:
                translated += 1
                continue
            # Partial match in array
            partial = any(
                vi_to_en[vi] and (text in vi or vi in text) and abs(len(text) - len(vi)) < len(text) * 0.3
                for vi in vi_to_en
                if len(text) > 20
            )
            if partial:
                translated += 1
                continue
            # Is the gap solvable via Notion?  Require substantial
            # overlap (≥60% of shorter string) to avoid false positives
            # like "Bồ Đào Nha" matching every Portugal sentence.
            has_notion_en = False
            for nvi, nen in notion_vi_to_en.items():
                shorter = min(len(text), len(nvi))
                if shorter < 30:
                    continue
                # Find common prefix length
                common = 0
                for a, b in zip(text, nvi):
                    if a == b: common += 1
                    else: break
                if common >= shorter * 0.6:
                    has_notion_en = True
                    notion_gaps.append({'section': sid, 'text': text[:120]})
                    break
            if has_notion_en:
                fixable_gap += 1
            else:
                # User: "It's OK if EN is not in Notion either" — acceptable
                acceptable_gap += 1

        total_translatable = translated + fixable_gap  # acceptable_gap excluded
        coverage = (translated / total_translatable * 100) if total_translatable else 100
        per_section[sid] = {
            'translated': translated,
            'fixable_gap': fixable_gap,
            'acceptable_gap': acceptable_gap,
            'gap': fixable_gap + acceptable_gap,  # for backward compat
            'skip': skip,
            'coverage_pct': round(coverage, 1),
        }

    # A section "fails" only if it has FIXABLE gaps with Notion EN content
    # available. Sections with only "acceptable" gaps (Notion is also
    # empty for that string) pass — per user spec.
    low_sections = {sid: stats for sid, stats in per_section.items()
                    if stats['fixable_gap'] > 0 and stats['coverage_pct'] < 70}

    return {
        'pass': len(low_sections) == 0,
        'per_section': per_section,
        'low_sections': list(low_sections.keys()),
        'notion_gaps': notion_gaps[:20],
    }


# ── Check 3: CHARTS bilingual ─────────────────────────────────────────
def check_charts(html: str) -> dict:
    """Are charts wired to switch language on EN click?"""
    issues = []

    has_charts = 'new Chart(' in html or "id='matrixChart'" in html or 'id="radarChart"' in html
    if not has_charts:
        return {'pass': True, 'has_charts': False, 'issues': []}

    # Pattern A: Turkey-style buildCharts(lang) wrapper
    has_buildcharts = bool(re.search(r'\bbuildCharts\s*\(', html))
    # Pattern B: post-setLang chart translator helper
    has_translator = 'NAC chart translator' in html or '_nacChartTrAttached' in html

    if not (has_buildcharts or has_translator):
        issues.append('Charts present but no buildCharts(lang) wrapper and no translator — labels stay VN')

    # If translator exists, verify the VI→EN dict has core country terms
    if has_translator:
        translator_block = ''
        m = re.search(r'NAC chart translator[\s\S]+?</script>', html)
        if m:
            translator_block = m.group(0)
            for must_have in ['Thổ Nhĩ Kỳ', 'Hy Lạp', 'Bồ Đào Nha', 'Tây Ban Nha']:
                if must_have not in translator_block:
                    issues.append(f'Chart translator missing country term: {must_have}')

    return {
        'pass': len(issues) == 0,
        'has_charts': True,
        'has_buildcharts': has_buildcharts,
        'has_translator': has_translator,
        'issues': issues,
    }


# ── Check 4 & 5: NAC INDEX banner sizing ──────────────────────────────
def check_globe_sizing(html: str) -> dict:
    """Verify globe banner has correct dimensions on mobile + desktop.

    Mobile: CSS Grid 240px globe row + auto kicker + auto title (Turkey pattern)
    Desktop: banner min-height 300px — globe-fit, no extra vertical padding.
             Globe sits 2% from the right edge (close to text, slight overflow).
    """
    issues = []
    has_globe = 'id="nacIndexGlobe"' in html or 'nac-index-banner' in html
    if not has_globe:
        return {'pass': True, 'has_globe': False, 'issues': []}

    # Mobile spec: CSS Grid with 240px row
    if 'grid-template-rows: 240px auto auto' not in html:
        issues.append('Mobile globe layout missing CSS Grid (grid-template-rows: 240px auto auto)')

    # Desktop spec: banner min-height 300px (globe-fit, no vertical padding)
    desktop_m = re.search(
        r'\.nac-index-banner\s*\{[^}]*?min-height:\s*(\d+)px[^}]*?\}',
        html
    )
    if desktop_m:
        mh = int(desktop_m.group(1))
        if mh != 300:
            issues.append(f'Desktop banner min-height: {mh}px (spec: 300px to fit 300px globe)')
    else:
        issues.append('Could not find desktop .nac-index-banner min-height rule')

    return {
        'pass': len(issues) == 0,
        'has_globe': True,
        'issues': issues,
    }


# ── Check 6: Article URLs point to specific blog PDPs ─────────────────
def check_article_urls(html: str) -> dict:
    """Article CTA banners should link to specific blog posts (PDPs),
    not the bare blog homepage. Exception: cards explicitly tagged with
    the generic "Đọc thêm phân tích trên Blog NAC" copy (the dedup
    fallback) are expected to point at blog homepage."""
    issues = []
    bare_homepage_count = 0
    pdp_count = 0
    total = 0

    # Walk every article-cta-banner anchor
    for m in re.finditer(
        r'<a class="article-cta-banner[^"]*"\s+href="([^"]+)"[^>]*>([\s\S]*?)</a>',
        html
    ):
        href = m.group(1)
        inner = m.group(2)
        # Skip NAC Index banners — they're not article PDPs
        if 'nac-residence-index' in href:
            continue
        # Skip generic blog cards (dedup output)
        if 'Đọc thêm phân tích trên Blog NAC' in inner or 'More analysis on the NAC Blog' in inner:
            continue
        total += 1
        # PDP = a URL with a slug-y path, not just / or /blog/
        # Bare homepage: blog.nomadassetcollective.com/ or blog.nomadassetcollective.com
        bare_pat = re.compile(r'https?://blog\.nomadassetcollective\.com/?$', re.IGNORECASE)
        if bare_pat.match(href):
            bare_homepage_count += 1
        else:
            pdp_count += 1

    if bare_homepage_count > 0:
        issues.append(f'{bare_homepage_count} article CTA(s) point to blog homepage instead of a specific PDP')

    return {
        'pass': len(issues) == 0,
        'total_article_ctas': total,
        'pdp_count': pdp_count,
        'bare_homepage_count': bare_homepage_count,
        'issues': issues,
    }


# ── Check 7: Charts render dimensions ─────────────────────────────────
def check_chart_rendering(html: str) -> dict:
    """Ensure brochure has its chart canvases + matrix has the mobile
    aspectRatio swap. Brochure-specific: not every brochure uses
    Turkey's exact set of 4 charts (e.g. Portugal has timelineChart
    instead of citizenshipChart + compareChart). We just check that
    every <canvas id="*Chart"> in the page is properly wired."""
    issues = []
    canvases = re.findall(r'<canvas\s+id="(\w*Chart)"', html)
    if not canvases:
        return {'pass': True, 'has_charts': False, 'issues': []}

    # Matrix should have aspectRatio swap for mobile
    if 'matrixChart' in canvases:
        if 'aspectRatio' not in html or "matchMedia('(max-width: 600px)')" not in html:
            issues.append('matrixChart missing mobile aspectRatio: 1 swap')

    # No chart should have max-height < 200px (too cramped)
    for m in re.finditer(r'id="(\w+Chart)"[^>]*style="[^"]*max-height:\s*(\d+)', html):
        if int(m.group(2)) < 200:
            issues.append(f'{m.group(1)} has max-height: {m.group(2)}px (cramped)')

    return {
        'pass': len(issues) == 0,
        'has_charts': True,
        'canvases': canvases,
        'issues': issues,
    }


# ── Orchestration ─────────────────────────────────────────────────────
def fetch_live(alias: str) -> Path:
    slug = LIVE_SLUG.get(alias)
    if not slug:
        raise ValueError(f'no live slug for {alias}')
    url = f'{LIVE_BASE}/{slug}/?nc={int(datetime.now(tz=timezone.utc).timestamp())}'
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        body = r.read()
    tmp = Path(f'/tmp/audit_{alias}.html')
    tmp.write_bytes(body)
    return tmp


def check_en_render(alias: str, html: str) -> dict:
    """Check #8 — simulate setLang('en') against the page and report
    any visible Vietnamese text that remains. This is the truth test
    for whether the EN toggle actually displays English to users.

    Uses the Node-based jsdom simulator (tools/simulate_en_render.js).
    The earlier Python/BeautifulSoup version normalized whitespace
    differently from a real browser and silently reported pass when
    the live page actually left 40+ Vietnamese strings — never trust
    that simulator again.
    """
    import shutil, subprocess, tempfile
    if not shutil.which('node'):
        return {'pass': False, 'issues': ['node not installed'],
                'remnant_count': 0, 'samples': []}

    js_path = ROOT / 'tools' / 'simulate_en_render.js'
    if not js_path.exists():
        return {'pass': False, 'issues': ['simulate_en_render.js missing'],
                'remnant_count': 0, 'samples': []}

    # The simulator reads from a file path or URL. Write the HTML to
    # a tempfile so we can audit live + local html the same way.
    with tempfile.NamedTemporaryFile('w', suffix='.html', delete=False, encoding='utf-8') as f:
        f.write(html)
        tmp = f.name
    try:
        r = subprocess.run(
            ['node', str(js_path), tmp, '--json'],
            capture_output=True, text=True, timeout=60,
        )
    except (subprocess.TimeoutExpired, OSError) as e:
        return {'pass': False, 'issues': [f'simulator error: {e}'],
                'remnant_count': 0, 'samples': []}
    finally:
        try: Path(tmp).unlink()
        except OSError: pass

    try:
        out = json.loads(r.stdout) if r.stdout.strip() else {}
    except json.JSONDecodeError:
        return {'pass': False, 'issues': [f'simulator non-JSON output: {r.stdout[:200]}'],
                'remnant_count': 0, 'samples': []}

    if out.get('error'):
        return {'pass': False, 'issues': [f'simulator error: {out["error"]}'],
                'remnant_count': 0, 'samples': []}

    if out.get('pass'):
        return {'pass': True, 'issues': [], 'remnant_count': 0, 'samples': []}

    remnants = out.get('remnants', [])
    return {
        'pass': False,
        'issues': [f"{out.get('remnant_count', len(remnants))} Vietnamese remnants after EN click"],
        'remnant_count': out.get('remnant_count', len(remnants)),
        'samples': [{'text': r['text'][:120]} for r in remnants[:5]],
    }


def audit_brochure(alias: str, html_path: Path, payload_path: Path | None) -> dict:
    html = html_path.read_text(encoding='utf-8')
    payload = json.loads(payload_path.read_text()) if (payload_path and payload_path.exists()) else None

    toggle = check_toggle(html)
    sections = check_sections(html, payload)
    charts = check_charts(html)
    globe_sizing = check_globe_sizing(html)
    article_urls = check_article_urls(html)
    chart_rendering = check_chart_rendering(html)
    en_render = check_en_render(alias, html)

    # §01 specifically — even stricter than general section coverage
    overview_ok = sections['per_section'].get('overview', {}).get('coverage_pct', 0) >= 70

    all_pass = (
        toggle['pass'] and sections['pass'] and charts['pass']
        and globe_sizing['pass'] and article_urls['pass']
        and chart_rendering['pass'] and overview_ok
        and en_render['pass']
    )
    return {
        'alias': alias,
        'all_pass': all_pass,
        'toggle': toggle,
        'sections': sections,
        'overview_ok': overview_ok,
        'charts': charts,
        'globe_sizing': globe_sizing,
        'article_urls': article_urls,
        'chart_rendering': chart_rendering,
        'en_render': en_render,
    }


def print_report(rpt: dict):
    icon = lambda ok: f"{GREEN}✓{RESET}" if ok else f"{RED}✗{RESET}"
    print(f"\n{BOLD}{rpt['alias']}{RESET}  {icon(rpt['all_pass'])}")
    # #1 Toggle
    print(f"  1. Toggle:        {icon(rpt['toggle']['pass'])} "
          + (f"{RED}{'; '.join(rpt['toggle']['issues'])}{RESET}" if rpt['toggle']['issues'] else ''))
    # #2 Charts EN
    ch = rpt['charts']
    if ch.get('has_charts'):
        print(f"  2. Charts EN:     {icon(ch['pass'])} "
              + (f"{RED}{'; '.join(ch['issues'])}{RESET}" if ch['issues'] else
                 (f"{GRAY}buildCharts wrapper{RESET}" if ch['has_buildcharts'] else f"{GRAY}translator helper{RESET}")))
    else:
        print(f"  2. Charts EN:     {GRAY}n/a (no charts){RESET}")
    # #3 Overview section
    print(f"  3. §01 Overview:  {icon(rpt['overview_ok'])} "
          + (f"{YELLOW}coverage too low{RESET}" if not rpt['overview_ok'] else ''))
    # #4 + #5 Globe sizing
    gs = rpt['globe_sizing']
    if gs.get('has_globe'):
        print(f"  4-5. Globe size:  {icon(gs['pass'])} "
              + (f"{RED}{'; '.join(gs['issues'])}{RESET}" if gs['issues'] else f"{GRAY}mobile + desktop OK{RESET}"))
    # #6 Article URLs
    au = rpt['article_urls']
    print(f"  6. Article URLs:  {icon(au['pass'])} "
          + (f"{RED}{'; '.join(au['issues'])}{RESET}" if au['issues'] else f"{GRAY}{au['pdp_count']}/{au['total_article_ctas']} → PDP{RESET}"))
    # #7 Chart rendering
    cr = rpt['chart_rendering']
    if cr.get('has_charts'):
        print(f"  7. Chart render:  {icon(cr['pass'])} "
              + (f"{RED}{'; '.join(cr['issues'])}{RESET}" if cr['issues'] else f"{GRAY}all canvases + mobile aspectRatio{RESET}"))
    # #8 EN render — does clicking EN actually show English?
    er = rpt.get('en_render', {})
    if er:
        msg = (f"{RED}{er['remnant_count']} VN remnants{RESET}"
               if not er.get('pass') else f"{GRAY}no VN remnants on EN click{RESET}")
        print(f"  8. EN displays:   {icon(er.get('pass'))} {msg}")
        if er.get('samples'):
            for s in er['samples'][:3]:
                print(f"     {GRAY}· {s['text'][:80]}{RESET}")
    # Section gaps detail
    sect = rpt['sections']
    if sect['low_sections']:
        print(f"     {YELLOW}low sections: {', '.join(sect['low_sections'])}{RESET}")
    if sect['notion_gaps']:
        print(f"     {YELLOW}Notion has EN for {len(sect['notion_gaps'])} gaps (sample):{RESET}")
        for g in sect['notion_gaps'][:3]:
            print(f"       [{g['section']}] {g['text'][:80]}")


def main() -> int:
    args = sys.argv[1:]
    use_local = '--local' in args
    args = [a for a in args if not a.startswith('--')]

    aliases = args if args else list(LIVE_SLUG.keys())

    label = 'LOCAL' if use_local else 'LIVE'
    print(f"\n{BOLD}Daily EN Audit ({label}){RESET}")
    print(f"{GRAY}{'─' * 70}{RESET}")

    reports = []
    for alias in aliases:
        if alias not in ALIAS_TO_FILENAME:
            continue
        if use_local:
            html_path = ROOT / 'Brochures html' / ALIAS_TO_FILENAME[alias]
        else:
            try:
                html_path = fetch_live(alias)
            except Exception as e:
                print(f"  ✗ {alias}: fetch failed — {e}")
                continue
        payload_path = ROOT / 'data' / f'{alias}_payload.json'
        try:
            r = audit_brochure(alias, html_path, payload_path)
            reports.append(r)
            print_report(r)
        except Exception as e:
            print(f"  ✗ {alias}: audit error — {e}")

    # Summary
    print(f"\n{GRAY}{'─' * 70}{RESET}")
    pass_count = sum(1 for r in reports if r['all_pass'])
    print(f"{BOLD}Summary:{RESET}  {GREEN}{pass_count}/{len(reports)} brochures fully passing{RESET}")

    # Failures categorized
    fail_toggle = [r['alias'] for r in reports if not r['toggle']['pass']]
    fail_sections = [r['alias'] for r in reports if not r['sections']['pass']]
    fail_charts = [r['alias'] for r in reports if not r['charts']['pass']]
    if fail_toggle: print(f"  {RED}Toggle issues:{RESET}    {', '.join(fail_toggle)}")
    if fail_sections: print(f"  {YELLOW}Section gaps:{RESET}    {', '.join(fail_sections)}")
    if fail_charts: print(f"  {YELLOW}Chart issues:{RESET}    {', '.join(fail_charts)}")

    # Write JSON
    DIAGNOSTICS.mkdir(exist_ok=True)
    out = DIAGNOSTICS / 'daily-en-audit.json'
    out.write_text(json.dumps({
        'generated_at': datetime.now(tz=timezone.utc).isoformat(),
        'source': 'live' if not use_local else 'local',
        'pass_count': pass_count,
        'total': len(reports),
        'reports': reports,
    }, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"  → JSON report: {out.relative_to(ROOT)}")

    return 0 if pass_count == len(reports) else 1


if __name__ == '__main__':
    raise SystemExit(main())
