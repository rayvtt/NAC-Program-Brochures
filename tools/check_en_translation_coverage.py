"""EN translation coverage report — what flips on EN click vs what stays VN.

For each brochure, parses the HTML and statically determines which
Vietnamese body content would actually be translated when the user
clicks EN, vs what stays Vietnamese.

Coverage logic per text node:
  - TRANSLATED if the text matches a VI_STRINGS entry with non-empty EN
  - TRANSLATED if the parent element has data-vi/data-en attrs (both non-empty)
  - SKIP (acceptable) if the text contains only proper nouns/numbers/dates
  - SKIP if Notion field is also empty for this content
  - GAP otherwise — flagged as needing translation

Outputs:
  - Per-brochure summary (translated / gap / skip counts + coverage %)
  - Top 10 gaps per brochure (sample of untranslated strings)
  - Writes a JSON report to .diagnostics/en-coverage.json

Run:
    python tools/check_en_translation_coverage.py             # all 12
    python tools/check_en_translation_coverage.py portugal    # one alias
    python tools/check_en_translation_coverage.py --json      # JSON only
"""
from __future__ import annotations

import html as html_lib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BROCHURES_DIR = ROOT / "Brochures html"
DATA_DIR = ROOT / "data"
DIAGNOSTICS_DIR = ROOT / ".diagnostics"

SKIP_FILES = {"NAC-BROCHURES-OVERVIEW.html", "NAC-RESIDENCE-INDEX.html"}

# Selectors that hold user-facing prose that SHOULD be translated
PROSE_SELECTORS = [
    r'<p class="sec-sub"[^>]*>([\s\S]*?)</p>',
    r'<div class="ov-value"[^>]*>([\s\S]*?)</div>',
    r'<div class="ov-note"[^>]*>([\s\S]*?)</div>',
    r'<div class="ov-label"[^>]*>([\s\S]*?)</div>',
    r'<div class="info-text"[^>]*>([\s\S]*?)</div>',
    r'<div class="tier-name"[^>]*>([\s\S]*?)</div>',
    r'<div class="tier-region"[^>]*>([\s\S]*?)</div>',
    r'<span class="ttag"[^>]*>([\s\S]*?)</span>',
    r'<div class="tl-week"[^>]*>([\s\S]*?)</div>',
    r'<div class="tl-title"[^>]*>([\s\S]*?)</div>',
    r'<div class="tl-body"[^>]*>([\s\S]*?)</div>',
    r'<div class="fam-title"[^>]*>([\s\S]*?)</div>',
    r'<div class="fam-note"[^>]*>([\s\S]*?)</div>',
    r'<h3[^>]*>([^<]+)</h3>',
    r'<div class="nac-box"[^>]*>[\s\S]*?<p[^>]*>([\s\S]+?)</p>',
    r'<li[^>]*>([\s\S]+?)</li>',
]

# Vietnamese diacritic characters — used to detect "is this text Vietnamese?"
VN_CHARS = set('ăâđêôơưĂÂĐÊÔƠƯấầắằộồứừờáàảãấầẩẫậăắằẳẵặéèẻẽếềểễệíìỉĩịóòỏõốồổỗộớờởỡợúùủũứừửữựýỳỷỹỵÁÀẢÃẤẦẨẪẬĂẮẰẲẴẶÉÈẺẼẾỀỂỄỆÍÌỈĨỊÓÒỎÕỐỒỔỖỘỚỜỞỠỢÚÙỦŨỨỪỬỮỰÝỲỶỸỴ')

# Proper nouns / brand names that legitimately stay in original form
SKIP_PHRASES = {
    'AIMA', 'NIF', 'AFM', 'PoA', 'CMVM', 'DGMM', 'IRN', 'TCMB', 'TKDF', 'CGT',
    'NHR', 'CSI', 'NHC', 'ARI', 'IDD', 'BĐS',
    'Türkiye', 'Portugal', 'Greece', 'Cyprus', 'Spain', 'Malta', 'UAE', 'Thailand',
    'NAC', 'Schengen', 'Athens', 'Lisbon', 'Mykonos', 'Santorini', 'Istanbul', 'Antalya',
    'Beylikdüzü', 'Başakşehir', 'Kağıthane', 'Şişli', 'Levent',
    'Henley & Partners', 'AIMA', 'SEF', 'SPK', 'CBRT', 'KAMA', 'CIP', 'CMBT',
}

ALIAS_TO_FILENAME = {
    'portugal': 'portugal-gv.html',
    'greece': 'greece-rbi_1_2.html',
    'cyprus': 'cyprus-rbi_3_3.html',
    'turkey': 'turkey-cbi_8.html',
    'uae': 'uae-rbi_1_7.html',
    'uk': 'uk-rbi_1 (2).html',
    'malta': 'malta-rbi_1_3.html',
    'stkitts': 'stkitts-nevis.html',
    'thailand': 'thailand-rbi_1 (2).html',
    'newzealand': 'newzealand-rbi_1 (3).html',
    'panama': 'panama-rbi_.html',
    'malaysia': 'malaysia-mm2h.html',
}


# ANSI colors
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
BLUE = "\033[34m"
GRAY = "\033[90m"
BOLD = "\033[1m"
RESET = "\033[0m"


def is_vietnamese(s: str) -> bool:
    """Return True if string contains Vietnamese-specific chars (diacritics)."""
    return any(c in VN_CHARS for c in s)


def is_skippable(s: str) -> bool:
    """Return True if string is a proper noun, number, brand name, etc.
    that's OK to leave untranslated."""
    s_clean = s.strip()
    if not s_clean: return True
    if len(s_clean) < 4: return True
    # All-numeric/date/currency
    if re.match(r'^[\d\s$€£%.,/\-+()]+$', s_clean): return True
    # Just symbols
    if not re.search(r'[a-zA-ZăâđêôơưÁÀẢÃẤẦẨẪẬ]', s_clean): return True
    # Skip-list phrases
    if s_clean in SKIP_PHRASES: return True
    # Mostly proper-noun heavy (no Vietnamese diacritics + short)
    if not is_vietnamese(s_clean) and len(s_clean) < 30: return True
    return False


def parse_vi_en_arrays(html: str) -> tuple[list, list]:
    """Extract VI_STRINGS / EN_STRINGS arrays from brochure HTML."""
    vi_m = re.search(r'(?:const|let|var)\s+VI_STRINGS\s*=\s*(\[[\s\S]+?\])\s*;', html)
    en_m = re.search(r'(?:const|let|var)\s+EN_STRINGS\s*=\s*(\[[\s\S]+?\])\s*;', html)
    vi_items = re.findall(r"['\"]((?:[^'\"\\]|\\.)+)['\"]", vi_m.group(1)) if vi_m else []
    en_items = re.findall(r"['\"]((?:[^'\"\\]|\\.)+)['\"]", en_m.group(1)) if en_m else []
    return vi_items, en_items


def parse_data_vi_en(html: str) -> dict:
    """Extract data-vi → data-en pairs from elements with both attrs."""
    pairs = {}
    # Find every element with both data-vi and data-en
    for m in re.finditer(
        r'data-vi="([^"]+)"[^>]*data-en="([^"]*)"|data-en="([^"]*)"[^>]*data-vi="([^"]+)"',
        html
    ):
        vi = m.group(1) or m.group(4)
        en = m.group(2) or m.group(3)
        if vi:
            pairs[html_lib.unescape(vi).strip()] = html_lib.unescape(en).strip() if en else ''
    return pairs


def extract_visible_text(html: str) -> list:
    """Pull visible text content from prose elements."""
    texts = []
    for pat in PROSE_SELECTORS:
        for m in re.finditer(pat, html):
            content = m.group(1)
            # Strip nested HTML tags to get just text
            plain = re.sub(r'<[^>]+>', ' ', content)
            plain = html_lib.unescape(plain)
            plain = re.sub(r'\s+', ' ', plain).strip()
            if plain:
                texts.append(plain)
    return texts


def check_translation_coverage(alias: str, html_path: Path, payload_path: Path | None) -> dict:
    """Return a coverage report for one brochure."""
    html = html_path.read_text(encoding='utf-8')
    vi_items, en_items = parse_vi_en_arrays(html)
    vi_to_en = {}
    for i, v in enumerate(vi_items):
        en = en_items[i] if i < len(en_items) else ''
        vi_to_en[v.strip()] = en.strip() if en else ''
    data_attr_pairs = parse_data_vi_en(html)

    # Also check Notion payload for which fields HAVE EN content
    notion_has_en_for = set()
    notion_pairs = {}
    if payload_path and payload_path.exists():
        payload = json.loads(payload_path.read_text(encoding='utf-8'))
        for key, value in payload.items():
            if not key.endswith('_en'): continue
            base = key[:-3]
            vi_val = payload.get(base + '_vi', '')
            if vi_val and value:
                notion_pairs[str(vi_val).strip()] = str(value).strip()
                notion_has_en_for.add(str(vi_val).strip())

    visible = extract_visible_text(html)

    translated = 0
    gap = 0
    skip = 0
    gap_samples = []

    seen = set()
    for text in visible:
        if not is_vietnamese(text):
            continue  # Not Vietnamese; nothing to translate
        if text in seen:
            continue
        seen.add(text)
        if is_skippable(text):
            skip += 1
            continue
        # Translation sources to check:
        # 1. data-vi/data-en
        if text in data_attr_pairs and data_attr_pairs[text]:
            translated += 1
            continue
        # 2. VI_STRINGS entry with non-empty EN
        if text in vi_to_en and vi_to_en[text]:
            translated += 1
            continue
        # 3. Partial match in VI_STRINGS (text is substring of an entry)
        partial_match = False
        for vi_key, en_val in vi_to_en.items():
            if en_val and (text in vi_key or vi_key in text):
                if len(text) > 20 and abs(len(text) - len(vi_key)) < len(text) * 0.3:
                    partial_match = True
                    break
        if partial_match:
            translated += 1
            continue
        # 4. Notion has EN content for this exact text (gap = inject not run yet)
        if text in notion_pairs:
            gap_samples.append({'text': text[:120], 'reason': 'notion_has_en_not_injected'})
            gap += 1
            continue
        # 5. Drift: Notion has a similar VI/EN pair (>60% prefix overlap) but
        # text doesn't match exactly — drift between HTML and Notion content
        text_lower = text.lower()
        text_prefix = text_lower[:max(40, len(text_lower) // 3)]
        drift_match = False
        for notion_vi in notion_pairs:
            notion_lower = notion_vi.lower()
            # Match if first 40 chars overlap significantly
            if (text_prefix in notion_lower or notion_lower[:max(40, len(notion_lower) // 3)] in text_lower):
                # Common opening words = drift candidate
                drift_match = True
                break
        if drift_match:
            gap_samples.append({'text': text[:120], 'reason': 'text_drift_vs_notion'})
            gap += 1
            continue
        # 6. Else, no EN available anywhere
        gap_samples.append({'text': text[:120], 'reason': 'no_en_available'})
        gap += 1

    total = translated + gap + skip
    coverage = (translated / (translated + gap) * 100) if (translated + gap) else 100

    return {
        'alias': alias,
        'html_file': html_path.name,
        'visible_vn_strings': total,
        'translated': translated,
        'gap': gap,
        'skip': skip,
        'coverage_pct': round(coverage, 1),
        'gap_samples': gap_samples[:10],
        'vi_array_size': len(vi_items),
        'en_array_size': len(en_items),
        'data_attr_pairs': len(data_attr_pairs),
        'notion_en_fields': len(notion_pairs),
    }


def print_report(report: dict, verbose: bool = False):
    cov = report['coverage_pct']
    color = GREEN if cov >= 95 else (YELLOW if cov >= 70 else RED)
    print(f"\n{BOLD}{report['alias']}{RESET}  {color}{cov:>5.1f}%{RESET} "
          f"({report['translated']} translated / {report['gap']} gap / {report['skip']} skip "
          f"of {report['visible_vn_strings']} VN strings)")
    print(f"  {GRAY}VI_STRINGS={report['vi_array_size']}  EN_STRINGS={report['en_array_size']}  "
          f"data-attr pairs={report['data_attr_pairs']}  Notion EN fields={report['notion_en_fields']}{RESET}")
    if report['gap'] > 0 and (verbose or cov < 95):
        print(f"  {YELLOW}Top gaps:{RESET}")
        for g in report['gap_samples'][:5]:
            reason_color = RED if g['reason'] == 'no_en_available' else YELLOW
            print(f"    {reason_color}•{RESET} {g['text']}")
            print(f"      {GRAY}reason: {g['reason']}{RESET}")


def main() -> int:
    args = sys.argv[1:]
    json_only = '--json' in args
    verbose = '-v' in args or '--verbose' in args
    args = [a for a in args if not a.startswith('-')]

    aliases = args if args else list(ALIAS_TO_FILENAME.keys())

    if not json_only:
        print(f"\n{BOLD}EN Translation Coverage Report{RESET}")
        print(f"{GRAY}{'─' * 70}{RESET}")

    reports = []
    for alias in aliases:
        if alias not in ALIAS_TO_FILENAME:
            continue
        html_path = BROCHURES_DIR / ALIAS_TO_FILENAME[alias]
        payload_path = DATA_DIR / f'{alias}_payload.json'
        try:
            r = check_translation_coverage(alias, html_path, payload_path)
            reports.append(r)
            if not json_only:
                print_report(r, verbose=verbose)
        except Exception as e:
            print(f'  ✗ {alias}: error {e}')

    if not json_only:
        print(f"\n{GRAY}{'─' * 70}{RESET}")
        avg = sum(r['coverage_pct'] for r in reports) / len(reports) if reports else 0
        full = sum(1 for r in reports if r['coverage_pct'] >= 95)
        partial = sum(1 for r in reports if 70 <= r['coverage_pct'] < 95)
        low = sum(1 for r in reports if r['coverage_pct'] < 70)
        print(f"{BOLD}Summary:{RESET}  avg {avg:.1f}%  ·  "
              f"{GREEN}{full} ≥95%{RESET}  ·  "
              f"{YELLOW}{partial} 70-94%{RESET}  ·  "
              f"{RED}{low} <70%{RESET}")

    # Always write JSON report
    DIAGNOSTICS_DIR.mkdir(exist_ok=True)
    out = DIAGNOSTICS_DIR / 'en-coverage.json'
    out.write_text(json.dumps({
        'generated_at': __import__('datetime').datetime.utcnow().isoformat() + 'Z',
        'reports': reports,
    }, ensure_ascii=False, indent=2), encoding='utf-8')
    if not json_only:
        print(f"\n  → JSON report: {out.relative_to(ROOT)}")
    else:
        print(json.dumps(reports, ensure_ascii=False, indent=2))

    return 0 if all(r['coverage_pct'] >= 70 for r in reports) else 1


if __name__ == '__main__':
    raise SystemExit(main())
