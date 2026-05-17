"""Inject Notion EN content into each brochure's VI_STRINGS / EN_STRINGS arrays.

Reads each ``data/<alias>_payload.json`` (refreshed by pull_from_notion.py)
and updates the corresponding ``Brochures html/*.html`` to ensure the
legacy bilingual string-replace arrays contain every VI/EN pair from
Notion. Existing array entries are preserved; new pairs are appended.

This is the "missing link" between Notion content and live brochure
HTML — without it, EN content lives in Notion but never reaches the
user-facing toggle.

Idempotent: re-runs that find no new pairs leave the HTML untouched.

Run:
    python tools/inject_notion_en_to_html.py             # all 12
    python tools/inject_notion_en_to_html.py portugal    # one alias
    python tools/inject_notion_en_to_html.py --dry-run
"""
from __future__ import annotations

import html as html_lib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Alias → filename map (same as sync_brochures.py BROCHURES dict)
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

DATA_DIR = ROOT / 'data'
BROCHURES_DIR = ROOT / 'Brochures html'


# Notion payload field name → "is bilingual; has both _vi and _en variants"
# These are the flat scalar text fields from the schema.
BILINGUAL_FIELDS = [
    'hero_badge',
    'hero_breadcrumb',
    'hero_title_top',
    'hero_title_em',
    'hero_desc',
    'nac_score_label',
    'country',
    'program',
    's01_subtitle',
    's01_factcheck',
    's01_article_cta_text',
    's02_subtitle',
    's02_warning_box',
    's02_nac_note',
    's03_subtitle',
    's04_subtitle',
    's04_compare_note',
    's05_subtitle',
    's05_inheritance_note',
    's05_special_note',
    's06_subtitle',
    's06_dual_citizenship_note',
    's06_nac_strategy_note',
    's07_subtitle',
    's07_cta_text',
    's08_subtitle',
    's08_risk_note',
    's09_subtitle',
    's09_cta_heading',
    's09_cta_body',
    's09_recommendation',
]

# JSON-encoded fields with bilingual *_vi/*_en inner keys
JSON_FIELDS = [
    'hero_stats',
    's01_overview_cards',
    's02_tiers',
    's03_timeline',
    's04_family_cards',
    's05_tax_cards',
    's06_roadmap',
    's07_compare_rows',
    's08_pros',
    's08_cons',
]


def strip_md_links(s):
    """[text](url) → text — Notion-MCP wraps URLs in markdown links."""
    if not isinstance(s, str):
        return s
    return re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'\1', s)


def html_attr_unescape(s):
    """Notion stores values with HTML entities pre-escaped (&amp; etc.).
    Brochure DOM has raw text. Decode for matching."""
    if not isinstance(s, str):
        return s
    return html_lib.unescape(s)


def normalize(s):
    """Normalize VI string for set-membership: strip + unescape entities."""
    return html_attr_unescape(strip_md_links(s)).strip()


def parse_json_field(value):
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return None


def extract_pairs(payload: dict) -> list[tuple[str, str]]:
    """Return [(vi, en), ...] from a single brochure payload."""
    pairs = []
    seen_vi = set()

    def add(vi, en):
        vi = normalize(vi)
        en = normalize(en)
        if not vi or not en or vi == en:
            return
        if vi in seen_vi:
            return
        seen_vi.add(vi)
        pairs.append((vi, en))

    # Flat bilingual fields
    for base in BILINGUAL_FIELDS:
        vi = payload.get(f'{base}_vi', '')
        en = payload.get(f'{base}_en', '')
        if vi and en:
            add(vi, en)

    # JSON-encoded bilingual fields
    for base in JSON_FIELDS:
        raw = payload.get(base, '')
        data = parse_json_field(raw)
        if not data:
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if not isinstance(item, dict):
                continue
            # Pair up *_vi / *_en keys
            for k in list(item.keys()):
                if not k.endswith('_vi'):
                    continue
                en_key = k[:-3] + '_en'
                if en_key not in item:
                    continue
                v_vi, v_en = item[k], item[en_key]
                if isinstance(v_vi, str) and isinstance(v_en, str):
                    add(v_vi, v_en)
                elif isinstance(v_vi, list) and isinstance(v_en, list):
                    for a, b in zip(v_vi, v_en):
                        if isinstance(a, str) and isinstance(b, str):
                            add(a, b)
            # Some entries use bare {"vi": ..., "en": ...} (pros/cons)
            if isinstance(item.get('vi'), str) and isinstance(item.get('en'), str):
                add(item['vi'], item['en'])

    return pairs


# Match VI_STRINGS / EN_STRINGS array literals in the HTML
VI_RE = re.compile(r'(const\s+VI_STRINGS\s*=\s*)(\[[\s\S]+?\])(\s*;)')
EN_RE = re.compile(r'(const\s+EN_STRINGS\s*=\s*)(\[[\s\S]+?\])(\s*;)')


def parse_array_literal(s: str) -> list[str]:
    """Parse a JS array literal of strings (single or double quoted)."""
    # Match each quoted string. Handles escaped quotes via simple state machine.
    out = []
    i = 0
    n = len(s)
    while i < n:
        c = s[i]
        if c in ('"', "'"):
            quote = c
            i += 1
            start = i
            buf = []
            while i < n:
                if s[i] == '\\' and i + 1 < n:
                    buf.append(s[i:i+2])
                    i += 2
                    continue
                if s[i] == quote:
                    break
                buf.append(s[i])
                i += 1
            text = ''.join(buf)
            # Reverse JS escapes for matching
            text = text.replace('\\"', '"').replace("\\'", "'").replace('\\\\', '\\')
            out.append(text)
        i += 1
    return out


def js_escape_string(s: str, quote: str = '"') -> str:
    """Escape a string for embedding in a JS literal with the given quote."""
    s = s.replace('\\', '\\\\')
    # Use unicode curly quotes if there's a literal " — DON'T use \"
    # because WordPress KSES unescapes it (documented WP gotcha).
    if quote == '"':
        s = s.replace('"', '”')   # right double quote
    else:
        s = s.replace("'", '’')   # right single quote
    return quote + s + quote


def merge_arrays(existing_vi: list, existing_en: list, new_pairs: list[tuple[str, str]]):
    """Merge new pairs into existing arrays.
    - Preserves index alignment of existing entries
    - Appends new VI/EN pairs that aren't already present
    - For pre-existing VI strings, prefers Notion EN (overrides stale translation)

    Returns: (vi_out, en_out, n_added, n_updated)
    """
    # Build VI → index map for fast lookup
    idx_by_vi = {v: i for i, v in enumerate(existing_vi)}

    vi_out = list(existing_vi)
    en_out = list(existing_en)

    # Pad EN to match VI length
    while len(en_out) < len(vi_out):
        en_out.append('')

    added = 0
    updated = 0
    for vi, en in new_pairs:
        # Match against existing by VI (try both raw and unescaped)
        existing_idx = idx_by_vi.get(vi)
        if existing_idx is None:
            # Also try matching with HTML entity decoded form of existing entries
            for k, v in idx_by_vi.items():
                if normalize(k) == vi:
                    existing_idx = v
                    break
        if existing_idx is not None:
            # Update EN if it changed
            if en_out[existing_idx] != en:
                en_out[existing_idx] = en
                updated += 1
        else:
            vi_out.append(vi)
            en_out.append(en)
            idx_by_vi[vi] = len(vi_out) - 1
            added += 1

    return vi_out, en_out, added, updated


def format_array(items: list[str], indent: str = '  ') -> str:
    """Format a list of strings as a JS array literal, one per line."""
    if not items:
        return '[]'
    lines = ['[']
    for s in items:
        lines.append(f'{indent}{js_escape_string(s)},')
    lines.append(']')
    return '\n'.join(lines)


def process_brochure(alias: str, html_path: Path, payload_path: Path, dry_run: bool = False) -> dict:
    out = {'pairs_extracted': 0, 'added': 0, 'updated': 0}
    if not html_path.exists():
        print(f'  ✗ {alias}: HTML missing ({html_path.name})')
        return out
    if not payload_path.exists():
        print(f'  ✗ {alias}: payload missing ({payload_path.name})')
        return out

    payload = json.loads(payload_path.read_text(encoding='utf-8'))
    pairs = extract_pairs(payload)
    out['pairs_extracted'] = len(pairs)

    html = html_path.read_text(encoding='utf-8')

    vi_m = VI_RE.search(html)
    en_m = EN_RE.search(html)
    if not vi_m or not en_m:
        print(f'  ⚠ {alias}: no VI_STRINGS / EN_STRINGS arrays found — skipping')
        return out

    existing_vi = parse_array_literal(vi_m.group(2))
    existing_en = parse_array_literal(en_m.group(2))

    new_vi, new_en, added, updated = merge_arrays(existing_vi, existing_en, pairs)
    out['added'] = added
    out['updated'] = updated

    if added == 0 and updated == 0:
        print(f'  · {alias}: {len(pairs)} pairs from Notion · already in sync')
        return out

    # Format updated arrays
    vi_block = format_array(new_vi)
    en_block = format_array(new_en)

    # Rebuild HTML with replaced arrays (do EN first so positions don't shift)
    html_new = html
    html_new = html_new[:en_m.start(2)] + en_block + html_new[en_m.end(2):]
    # After EN replacement, VI_RE positions may have shifted. Re-search VI on new text.
    vi_m2 = VI_RE.search(html_new)
    if vi_m2:
        html_new = html_new[:vi_m2.start(2)] + vi_block + html_new[vi_m2.end(2):]

    print(f'  ✓ {alias}: +{added} new, ~{updated} updated (total VI items: {len(new_vi)})')

    if not dry_run:
        html_path.write_text(html_new, encoding='utf-8')

    return out


def main() -> int:
    args = sys.argv[1:]
    dry_run = '--dry-run' in args
    args = [a for a in args if not a.startswith('--')]

    aliases = args if args else list(ALIAS_TO_FILENAME.keys())

    print(f"\nInjecting Notion EN content into brochure VI_STRINGS / EN_STRINGS arrays")
    print(f"{'─' * 70}")

    totals = {'added': 0, 'updated': 0, 'pairs_extracted': 0}
    for alias in aliases:
        if alias not in ALIAS_TO_FILENAME:
            print(f'  ? unknown alias: {alias}')
            continue
        fname = ALIAS_TO_FILENAME[alias]
        html_path = BROCHURES_DIR / fname
        payload_path = DATA_DIR / f'{alias}_payload.json'
        c = process_brochure(alias, html_path, payload_path, dry_run=dry_run)
        for k, v in c.items():
            totals[k] += v

    mode = 'dry-run' if dry_run else 'applied'
    print(f"\n{'─' * 70}")
    print(f"Done: {totals['added']} added, {totals['updated']} updated "
          f"across {totals['pairs_extracted']} pairs extracted ({mode}).")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
