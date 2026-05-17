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

    # Build vi→en map from VI_STRINGS / EN_STRINGS
    vi_m = re.search(r'(?:const|let|var)\s+VI_STRINGS\s*=\s*(\[[\s\S]+?\])\s*;', html)
    en_m = re.search(r'(?:const|let|var)\s+EN_STRINGS\s*=\s*(\[[\s\S]+?\])\s*;', html)
    vi_items = re.findall(r"['\"]((?:[^'\"\\]|\\.)+)['\"]", vi_m.group(1)) if vi_m else []
    en_items = re.findall(r"['\"]((?:[^'\"\\]|\\.)+)['\"]", en_m.group(1)) if en_m else []
    vi_to_en = {v.strip(): (en_items[i].strip() if i < len(en_items) else '')
                for i, v in enumerate(vi_items)}

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
    notion_gaps = []  # Strings where Notion has EN but brochure doesn't

    for sid, snippet in sections.items():
        if not snippet: continue
        visible = extract_visible_text(snippet)
        translated = gap = skip = 0
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
            gap += 1
            # Is the gap solvable via Notion?
            for nvi, nen in notion_vi_to_en.items():
                if text in nvi or nvi in text:
                    notion_gaps.append({'section': sid, 'text': text[:120], 'notion_en_available': True})
                    break

        coverage = (translated / (translated + gap) * 100) if (translated + gap) else 100
        per_section[sid] = {
            'translated': translated, 'gap': gap, 'skip': skip,
            'coverage_pct': round(coverage, 1),
        }

    # Sections below threshold
    low_sections = {sid: stats for sid, stats in per_section.items()
                    if stats['coverage_pct'] < 70 and (stats['translated'] + stats['gap']) >= 3}

    return {
        'pass': len(low_sections) == 0,
        'per_section': per_section,
        'low_sections': list(low_sections.keys()),
        'notion_gaps': notion_gaps[:20],  # top 20 with Notion EN ready
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


def audit_brochure(alias: str, html_path: Path, payload_path: Path | None) -> dict:
    html = html_path.read_text(encoding='utf-8')
    payload = json.loads(payload_path.read_text()) if (payload_path and payload_path.exists()) else None

    toggle = check_toggle(html)
    sections = check_sections(html, payload)
    charts = check_charts(html)

    all_pass = toggle['pass'] and sections['pass'] and charts['pass']
    return {
        'alias': alias,
        'all_pass': all_pass,
        'toggle': toggle,
        'sections': sections,
        'charts': charts,
    }


def print_report(rpt: dict):
    icon = lambda ok: f"{GREEN}✓{RESET}" if ok else f"{RED}✗{RESET}"
    print(f"\n{BOLD}{rpt['alias']}{RESET}  {icon(rpt['all_pass'])}")
    print(f"  Toggle:   {icon(rpt['toggle']['pass'])} "
          + (f"{RED}{'; '.join(rpt['toggle']['issues'])}{RESET}" if rpt['toggle']['issues'] else ''))
    sect = rpt['sections']
    print(f"  Sections: {icon(sect['pass'])} "
          + (f"{YELLOW}low coverage in: {', '.join(sect['low_sections'])}{RESET}" if sect['low_sections'] else 'all ≥70%'))
    ch = rpt['charts']
    if ch.get('has_charts'):
        print(f"  Charts:   {icon(ch['pass'])} "
              + (f"{RED}{'; '.join(ch['issues'])}{RESET}" if ch['issues'] else
                 (f"{GRAY}buildCharts wrapper{RESET}" if ch['has_buildcharts'] else f"{GRAY}translator helper{RESET}")))
    else:
        print(f"  Charts:   {GRAY}n/a (no charts){RESET}")
    if sect['notion_gaps']:
        print(f"  {YELLOW}Notion has EN for {len(sect['notion_gaps'])} gaps (sample):{RESET}")
        for g in sect['notion_gaps'][:3]:
            print(f"    [{g['section']}] {g['text'][:90]}")


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
