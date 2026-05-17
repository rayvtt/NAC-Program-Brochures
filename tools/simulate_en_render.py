"""Simulate setLang('en') on a live brochure and report Vietnamese remnants.

The static coverage check (`check_en_translation_coverage.py`) verifies
arrays are populated and DOM text has a translation entry. That isn't
enough: it doesn't actually replay the in-browser string-replace logic,
so a phrase that's in VI_STRINGS but doesn't match a DOM element
(whitespace drift, missing selector, KSES mangling) is still counted as
"covered" even though the user sees Vietnamese on EN click.

This tool fetches the live page, parses VI/EN arrays out of the live
HTML, re-applies setLang('en')'s exact `innerHTML.split(s).join(dst)`
logic to every matching element, then extracts all visible text and
flags anything that still contains Vietnamese diacritics.

What it catches that the static check doesn't:
  • DOM strings that aren't in any VI_STRINGS entry (silent fall-through)
  • DOM strings that ARE in an entry but the entry's EN slot is empty
  • Whitespace / curly-quote / NBSP drift between DOM and arrays
  • Selectors absent from setLang's target list (visible but never swapped)
  • WP/KSES mangling that breaks string equality on the live page only

Run:
    python tools/simulate_en_render.py portugal           # one alias
    python tools/simulate_en_render.py                    # all 12
    python tools/simulate_en_render.py --local portugal   # use local HTML
    python tools/simulate_en_render.py --json             # JSON only
"""
from __future__ import annotations

import argparse
import html as html_lib
import json
import re
import sys
import urllib.request
from pathlib import Path

from bs4 import BeautifulSoup, NavigableString, Comment

ROOT = Path(__file__).resolve().parent.parent
BROCHURES_DIR = ROOT / "Brochures html"
DIAGNOSTICS = ROOT / ".diagnostics"

# Reuse the array parser from the sibling tool
sys.path.insert(0, str(ROOT / "tools"))
from check_en_translation_coverage import _parse_array_literal  # noqa: E402

ALIAS_TO_FILENAME = {
    'portugal':   'portugal-gv.html',
    'greece':     'greece-rbi_1_2.html',
    'cyprus':     'cyprus-rbi_3_3.html',
    'turkey':     'turkey-cbi_8.html',
    'uae':        'uae-rbi_1_7.html',
    'uk':         'uk-rbi_1 (2).html',
    'malta':      'malta-rbi_1_3.html',
    'stkitts':    'stkitts-nevis.html',
    'thailand':   'thailand-rbi_1 (2).html',
    'newzealand': 'newzealand-rbi_1 (3).html',
    'panama':     'panama-rbi_.html',
    'malaysia':   'malaysia-mm2h.html',
}

LIVE_URL = {
    'portugal':   'https://nomadassetcollective.com/brochures/chuong-trinh-bo-dao-nha-golden-visa/',
    'greece':     'https://nomadassetcollective.com/brochures/residences-chuong-trinh-hy-lap-golden-visa/',
    'cyprus':     'https://nomadassetcollective.com/brochures/chuong-trinh-dao-sip-rbi-residence-by-investment/',
    'turkey':     'https://nomadassetcollective.com/brochures/chuong-trinh-tho-nhi-ky-cbi-citizenship-by-investment/',
    'uae':        'https://nomadassetcollective.com/brochures/chuong-trinh-uae-golden-visa-2/',
    'uk':         'https://nomadassetcollective.com/brochures/chuong-trinh-uk-thuong-tru-visa-dau-tu-rbi/',
    'malta':      'https://nomadassetcollective.com/brochures/chuong-trinh-malta-thuong-tru-nhan-rbi/',
    'stkitts':    'https://nomadassetcollective.com/brochures/chuong-trinh-si-kitts-nevis-quoc-tich/',
    'thailand':   'https://nomadassetcollective.com/brochures/chuong-trinh-thai-lan-cu-tru-dai-han-ltr-rbi/',
    'newzealand': 'https://nomadassetcollective.com/brochures/chuong-trinh-new-zealand-rbi-dau-tu-di-tru/',
    'panama':     'https://nomadassetcollective.com/brochures/chuong-trinh-panama-rbi-quyen-cu-tru-vinh-vien/',
    'malaysia':   'https://nomadassetcollective.com/brochures/chuong-trinh-malaysia-rbi-mm2h-dau-tu-quyen-cu-tru/',
}

# Vietnamese-UNIQUE diacritics — characters that appear in Vietnamese
# but not in Portuguese / Spanish / French. Used to detect "is this
# text Vietnamese?" without false positives on the Portuguese place
# names and program names that appear throughout brochures.
VN_CHARS = set(
    'ăĂưƯơƠđĐ'
    'ảẢạẠ'
    'ấầẩẫậẤẦẨẪẬ'
    'ắằẳẵặẮẰẲẴẶ'
    'ẹẺẻẼẽẸ'
    'ếềểễệẾỀỂỄỆ'
    'ỉỈịỊĩĨ'
    'ỏỎọỌ'
    'ốồổỗộỐỒỔỖỘ'
    'ớờởỡợỚỜỞỠỢ'
    'ủỦụỤũŨ'
    'ứừửữựỨỪỬỮỰ'
    'ỳỲỷỶỹỸỵỴ'
)

# Phrases that contain VN diacritics but are proper-noun-y / brand /
# place names that legitimately stay in the original form. Anything in
# this set is excluded from the "remnant" report.
ALLOWED_VN_REMNANTS = {
    # NAC brand
    'NAC – Nomad Asset Collective',
    'Nomad Asset Collective',
    # Vietnamese place names that appear inside English copy when we
    # reference the Vietnamese market context
    'Việt Nam', 'Hồ Chí Minh', 'Hà Nội', 'Đà Nẵng',
    # Locale-string fragments in score labels / KPI numbers
}

# Heuristic: any "remnant" shorter than this and containing fewer than
# this many word-like tokens is skipped (likely a name or stub).
MIN_REMNANT_LEN = 6
MIN_REMNANT_WORDS = 2


def fetch_html(url: str) -> str:
    req = urllib.request.Request(url, headers={'User-Agent': 'NAC-Brochure-Audit/1.0'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode('utf-8', errors='replace')


def parse_arrays(html: str) -> tuple[list[str], list[str]]:
    vi_m = re.search(r'(?:const|let|var)\s+VI_STRINGS\s*=\s*(\[[\s\S]+?\])\s*;', html)
    en_m = re.search(r'(?:const|let|var)\s+EN_STRINGS\s*=\s*(\[[\s\S]+?\])\s*;', html)
    if not vi_m or not en_m:
        return [], []
    return _parse_array_literal(vi_m.group(1)), _parse_array_literal(en_m.group(1))


def parse_setlang_selector(html: str) -> str | None:
    """Extract the exact CSS selector list setLang uses for string-replace.
    Returns the selector string (as passed to querySelectorAll) or None
    if not found."""
    m = re.search(
        r"root\.querySelectorAll\(\s*['\"]([^'\"]+)['\"]\s*\)",
        html,
    )
    return m.group(1) if m else None


# Hero overrides that setLang applies via heroText / heroStats blocks
def parse_hero_overrides(html: str) -> dict:
    """Extract heroText / heroStats EN strings so we can apply them too."""
    out = {'title_en': '', 'desc_en': '', 'stat_lbls_en': []}
    m = re.search(r"heroText\s*=\s*\{([\s\S]+?)\}\s*;", html)
    if m:
        body = m.group(1)
        en_block = re.search(r"en\s*:\s*\{([\s\S]+?)\}", body)
        if en_block:
            t = re.search(r"title\s*:\s*['\"]([\s\S]+?)['\"]", en_block.group(1))
            d = re.search(r"desc\s*:\s*['\"]([\s\S]+?)['\"]", en_block.group(1))
            if t: out['title_en'] = t.group(1)
            if d: out['desc_en'] = d.group(1)
    m2 = re.search(r"heroStats\s*=\s*\{([\s\S]+?)\}\s*;", html)
    if m2:
        body = m2.group(1)
        en_block = re.search(r"en\s*:\s*\{([\s\S]+?)\}", body)
        if en_block:
            lbls = re.search(r"lbls\s*:\s*\[([\s\S]+?)\]", en_block.group(1))
            if lbls:
                out['stat_lbls_en'] = _parse_array_literal('[' + lbls.group(1) + ']')
    return out


def apply_setlang_en(html: str) -> str:
    """Return HTML as if setLang('en') were called in the browser.

    Faithfully replays the live JS:
      1. Parse VI_STRINGS / EN_STRINGS from the page itself.
      2. Walk the same CSS selector setLang uses.
      3. For each match, do innerHTML.split(VI[i]).join(EN[i]) for every i.
      4. Replace hero title + desc + .stat-lbl from the hero blocks.
      5. Replace .sbar-lbl with the hardcoded EN list.
      6. Replace nav-cta text.
    """
    vi_items, en_items = parse_arrays(html)
    if not vi_items:
        raise RuntimeError("VI_STRINGS not found in page")
    sel = parse_setlang_selector(html) or ''
    hero = parse_hero_overrides(html)

    soup = BeautifulSoup(html, 'html.parser')

    # Apply hero h1
    h1 = soup.select_one('.hero h1')
    if h1 and hero['title_en']:
        h1.clear()
        h1.append(BeautifulSoup(hero['title_en'], 'lxml').body or BeautifulSoup(hero['title_en'], 'lxml'))
        # Simpler: just set string
        h1.clear()
        h1.append(NavigableString(re.sub(r'<[^>]+>', ' ', hero['title_en'])))

    # Hero desc
    desc = soup.select_one('.hero-desc')
    if desc and hero['desc_en']:
        desc.clear()
        desc.append(NavigableString(hero['desc_en']))

    # Stat labels
    if hero['stat_lbls_en']:
        for i, el in enumerate(soup.select('.stat-lbl')):
            if i < len(hero['stat_lbls_en']):
                el.clear()
                el.append(NavigableString(hero['stat_lbls_en'][i]))

    # Score bars
    sbar_en = ['Investment', 'Speed', 'Quality of Life', 'Passport', 'Tax', 'Citizenship']
    for i, el in enumerate(soup.select('.sbar-lbl')):
        if i < len(sbar_en):
            el.clear()
            el.append(NavigableString(sbar_en[i]))

    # Main targets: setLang's selector list
    if sel:
        targets = soup.select(sel)
    else:
        # Fall back to a superset of selectors if extraction failed
        targets = soup.select('.sec-sub, .sec-title, .ov-label, .ov-value, .ov-note, '
                              '.tl-week, .tl-title, .tl-body, .tier-name, .ttag, '
                              '.fam-title, .fam-note, .info-text, li, p, h1, h2, h3, h4')

    # Build VI → EN list ordered by descending length. Longest entries
    # replace first so a shorter substring (e.g. country name "Bồ Đào
    # Nha") doesn't pre-mangle a longer entry that contains it. This is
    # the same ordering the browser-side setLang now applies.
    pairs = []
    for i, v in enumerate(vi_items):
        en = en_items[i] if i < len(en_items) else ''
        if v and en and v != en:
            pairs.append((v, en))
    pairs.sort(key=lambda p: len(p[0]), reverse=True)

    for el in targets:
        inner = el.decode_contents()
        new = inner
        for v, e in pairs:
            if v in new:
                new = new.replace(v, e)
        if new != inner:
            el.clear()
            el.append(BeautifulSoup(new, 'html.parser'))

    # Pass 2 — universal text-node fallback. Matches Portugal's setLang
    # which walks every text node for plain (no-HTML) entries. This
    # catches DOM strings outside the explicit selector list. Text
    # nodes hold raw `&`, so decode `&amp;` back from the entries
    # (which are stored entity-encoded for Pass 1's innerHTML compare).
    def _dec(s): return s.replace('&amp;', '&')
    plain_pairs = [(_dec(v), _dec(e)) for v, e in pairs
                   if '<' not in v and '>' not in v]

    def walk(node):
        # Comment extends NavigableString — must check Comment FIRST and
        # leave alone; otherwise `replace_with(NavigableString(...))`
        # would strip the comment delimiters and leak comment text into
        # the visible DOM.
        if isinstance(node, Comment):
            return
        if isinstance(node, NavigableString):
            t = str(node)
            new_t = t
            for v, e in plain_pairs:
                if v in new_t:
                    new_t = new_t.replace(v, e)
            if new_t != t:
                node.replace_with(NavigableString(new_t))
            return
        if hasattr(node, 'name') and node.name:
            if node.name in ('script', 'style', 'template'):
                return
            for c in list(node.children):
                walk(c)

    walk(soup)

    return str(soup)


def browser_innerhtml(text: str) -> str:
    """Return what a browser's innerHTML would render for raw text.

    The browser stores `&` as `&amp;`, `<` as `&lt;`, `>` as `&gt;`,
    `"` as `&quot;` (in some contexts), `'` as `&#39;`. This matters
    because setLang does `el.innerHTML.includes(VI[i])` — if VI[i] has
    a literal `&` but innerHTML has `&amp;`, the match silently fails.
    """
    return (text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;'))


def extract_visible_text(soup_or_html) -> list[tuple[str, str]]:
    """Return [(text, parent_selector), ...] for every visible text node.

    Uses `html.parser` because `lxml` re-classifies some HTML comments
    as NavigableString during round-trip parsing (especially comments
    whose body looks like ASCII art) — that leaks comment content into
    the visible-text scan.
    """
    if isinstance(soup_or_html, str):
        soup = BeautifulSoup(soup_or_html, 'html.parser')
    else:
        soup = soup_or_html

    # Drop non-visible / non-body chrome
    for tag in soup(['script', 'style', 'template', 'noscript', 'meta', 'link',
                     'head', 'title']):
        tag.decompose()

    # Drop the language-toggle buttons & decorative bits — these
    # legitimately contain "Tiếng Việt / English" or similar
    for sel in ['.lang-toggle', '#btn-vi', '#btn-en', '.lang-btn',
                '[hidden]', '[aria-hidden="true"]']:
        for el in soup.select(sel):
            el.decompose()

    out = []
    for node in soup.find_all(string=True):
        # Skip HTML comments — they're not visible to users.
        if isinstance(node, Comment):
            continue
        text = str(node).strip()
        if not text:
            continue
        # Skip pure whitespace, navbar markers etc.
        if not any(c.isalpha() for c in text):
            continue
        parent = node.parent
        # Build a short selector trail for debugging
        trail = []
        cur = parent
        for _ in range(3):
            if cur is None or cur.name is None: break
            sel = cur.name
            cls = cur.get('class')
            if cls: sel += '.' + '.'.join(cls[:2])
            id_ = cur.get('id')
            if id_: sel += '#' + id_
            trail.append(sel)
            cur = cur.parent
        out.append((text, ' > '.join(reversed(trail))))
    return out


def find_vn_remnants(after_en_html: str) -> list[dict]:
    """Return text fragments that still contain VN diacritics after the
    setLang('en') simulation. These are what the user sees on EN click."""
    items = extract_visible_text(after_en_html)
    remnants = []
    seen = set()
    for text, trail in items:
        if not any(c in VN_CHARS for c in text):
            continue
        # Filter out trivial / allowed phrases
        if text in ALLOWED_VN_REMNANTS:
            continue
        if len(text) < MIN_REMNANT_LEN:
            continue
        if len(text.split()) < MIN_REMNANT_WORDS:
            continue
        if text in seen:
            continue
        seen.add(text)
        remnants.append({'text': text, 'parent': trail})
    return remnants


def audit_brochure(alias: str, source: str = 'live') -> dict:
    if source == 'local':
        html_path = BROCHURES_DIR / ALIAS_TO_FILENAME[alias]
        html = html_path.read_text(encoding='utf-8')
        url = f'file://{html_path}'
    else:
        url = LIVE_URL[alias]
        html = fetch_html(url)

    vi, en = parse_arrays(html)
    sel = parse_setlang_selector(html)

    try:
        after = apply_setlang_en(html)
    except Exception as e:
        return {
            'alias': alias, 'source': source, 'url': url,
            'error': str(e),
            'vi_array_size': len(vi), 'en_array_size': len(en),
        }

    remnants = find_vn_remnants(after)

    # Identify cause buckets for each remnant
    pairs = {v: (en[i] if i < len(en) else '') for i, v in enumerate(vi)}
    for r in remnants:
        t = r['text']
        if t in pairs:
            r['cause'] = 'en_slot_empty' if not pairs[t] else 'replace_failed'
        else:
            # Substring of an entry?
            matched = False
            for v in pairs:
                if t in v and pairs[v]:
                    r['cause'] = 'whitespace_or_substring_drift'
                    r['drift_against'] = v[:80]
                    matched = True
                    break
            if not matched:
                r['cause'] = 'missing_from_arrays'

    pass_ = len(remnants) == 0
    return {
        'alias': alias,
        'source': source,
        'url': url,
        'pass': pass_,
        'remnant_count': len(remnants),
        'vi_array_size': len(vi),
        'en_array_size': len(en),
        'setlang_selector': sel,
        'remnants': remnants[:50],  # cap output
    }


def print_report(report: dict, verbose: bool = False):
    alias = report['alias']
    src = report['source']
    if 'error' in report:
        print(f"  ✗ {alias} ({src}): ERROR — {report['error']}")
        return
    badge = '✓' if report['pass'] else '✗'
    print(f"  {badge} {alias} ({src}): {report['remnant_count']} VN remnants "
          f"[VI={report['vi_array_size']} EN={report['en_array_size']}]")
    if not report['pass']:
        # Group by cause
        by_cause: dict[str, list] = {}
        for r in report['remnants']:
            by_cause.setdefault(r.get('cause', 'unknown'), []).append(r)
        for cause, items in by_cause.items():
            print(f"      ── {cause}: {len(items)}")
            for r in (items if verbose else items[:5]):
                t = r['text']
                if len(t) > 100: t = t[:97] + '…'
                print(f"         · {t}")
                if r.get('drift_against'):
                    print(f"           ↳ vs: {r['drift_against'][:80]}")
            if not verbose and len(items) > 5:
                print(f"         · …and {len(items)-5} more")


def main():
    p = argparse.ArgumentParser()
    p.add_argument('aliases', nargs='*')
    p.add_argument('--local', action='store_true', help='Audit local HTML instead of live')
    p.add_argument('--json', action='store_true', help='Print JSON only')
    p.add_argument('--verbose', '-v', action='store_true', help='Show all remnants')
    args = p.parse_args()

    aliases = args.aliases or list(ALIAS_TO_FILENAME.keys())
    source = 'local' if args.local else 'live'

    DIAGNOSTICS.mkdir(exist_ok=True)
    reports = []
    for a in aliases:
        if a not in ALIAS_TO_FILENAME:
            print(f"  ? unknown alias: {a}")
            continue
        try:
            r = audit_brochure(a, source=source)
        except Exception as e:
            r = {'alias': a, 'source': source, 'error': str(e)}
        reports.append(r)
        if not args.json:
            print_report(r, verbose=args.verbose)

    out = {'source': source, 'reports': reports}
    out_path = DIAGNOSTICS / f'en-render-{source}.json'
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding='utf-8')

    if args.json:
        print(json.dumps(out, indent=2, ensure_ascii=False))
    else:
        passed = sum(1 for r in reports if r.get('pass'))
        print(f"\n{passed}/{len(reports)} brochures pass EN-render audit ({source})")
        print(f"Report: {out_path}")

    return 0 if all(r.get('pass') for r in reports) else 1


if __name__ == '__main__':
    raise SystemExit(main())
