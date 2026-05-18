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


# Re-use the coverage tool's parser so both tools agree byte-for-byte on
# what each JS array entry decodes to. Critical: it also decodes
# `\uXXXX` escapes, which the previous local copy of this function did
# not — entries like `<a href="...>` were left half-decoded and
# round-tripped back into the HTML as `\\u0022`, breaking the live JS.
from check_en_translation_coverage import _parse_array_literal as parse_array_literal  # noqa: E402


def to_innerhtml_form(s: str) -> str:
    """Encode raw text the way the browser stores it in `innerHTML`.

    `setLang('en')` is `el.innerHTML.split(VI[i]).join(EN[i])`. The browser
    always serializes `&`, `<`, `>` as `&amp;`, `&lt;`, `&gt;` when you
    read `innerHTML` — but only inside TEXT, not inside actual HTML tags.

    So an entry like `Athens · đảo >3,100 dân` must become
    `Athens · đảo &gt;3,100 dân`, while `<strong>NHR</strong>` stays
    intact. We tokenize the string into tag / non-tag spans and only
    encode within the non-tag spans.
    """
    # Encode bare `&` first (not part of an existing entity) on the
    # entire string — entity refs inside attribute values stay valid.
    s = re.sub(r'&(?![a-zA-Z0-9#]+;)', '&amp;', s)
    # Tokenize: split on HTML tags. Keep tags as-is; encode `<`/`>` in text.
    tag_re = re.compile(r'(<\/?[a-zA-Z][^<>]*>)')
    out = []
    last = 0
    for m in tag_re.finditer(s):
        text_part = s[last:m.start()]
        out.append(text_part.replace('<', '&lt;').replace('>', '&gt;'))
        out.append(m.group(0))  # tag stays untouched
        last = m.end()
    tail = s[last:]
    out.append(tail.replace('<', '&lt;').replace('>', '&gt;'))
    return ''.join(out)


def js_escape_string(s: str, quote: str | None = None) -> str:
    """Embed text in a JS string literal that survives WordPress KSES.

    KSES (the WP HTML sanitiser applied to ACF `raw_html_code`) strips
    bare backslashes inside `<script>` content — `\\"` becomes `"`,
    `\\u0022` becomes `u0022`. That breaks any JS escape sequence.

    The safe shape: pick a quote character the content doesn't contain,
    so no escape is needed at all:
      content has `"` only → use `'…'`
      content has `'` only → use `"…"`
      content has neither → use `"…"` (default)
      content has both    → use `"…"` and replace `'` with `’`
                            (typographically correct; matches DOM if
                            the source HTML also uses the curly quote).
    """
    s = to_innerhtml_form(s)
    has_dq = '"' in s
    has_sq = "'" in s
    if quote is None:
        if has_dq and not has_sq:
            quote = "'"
        elif has_sq and not has_dq:
            quote = '"'
        elif has_sq and has_dq:
            # Both present — switch inner `'` to typographic right-single-quote
            # (’), then wrap in SINGLE-quoted JS literal. The `"` in <a href="…">
            # then sits literal inside `'…'` with no escape needed — which is
            # crucial because WordPress KSES strips any `\"` inside <script>
            # tags. Picking `"` as the outer + `\"` escape would re-introduce
            # the original "Mhmm. Mhmm. English" patchy-toggle bug on live.
            s = s.replace("'", '’')
            quote = "'"
        else:
            quote = '"'
    # Escape `\`, control whitespace, and the chosen quote character. The
    # control-whitespace escape is what prevents Trap 3 (multi-line string
    # literals from Notion bullet-list fields landing as raw newlines
    # inside the JS array → SyntaxError → silent EN-toggle + chart death).
    # KSES leaves `\n` / `\r` / `\t` alone inside <script>, unlike `\"`,
    # so these escape sequences are safe on WordPress.
    s = (s.replace('\\', '\\\\')
          .replace('\n', '\\n')
          .replace('\r', '\\r')
          .replace('\t', '\\t')
          .replace(quote, '\\' + quote))
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


def process_brochure(alias: str, html_path: Path, payload_path: Path, dry_run: bool = False,
                     reformat: bool = False) -> dict:
    out = {'pairs_extracted': 0, 'added': 0, 'updated': 0, 'reformatted': False}
    if not html_path.exists():
        print(f'  ✗ {alias}: HTML missing ({html_path.name})')
        return out
    if not payload_path.exists() and not reformat:
        print(f'  ✗ {alias}: payload missing ({payload_path.name})')
        return out

    pairs = []
    if payload_path.exists():
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

    # Always format through the current js_escape_string. If the
    # formatted output differs from what's in the file (e.g. an old
    # `"` form vs. the current single-quoted form), the rewrite
    # below propagates the encoding fix to the brochure HTML.
    vi_block = format_array(new_vi)
    en_block = format_array(new_en)

    needs_reformat = (vi_block != vi_m.group(2) or en_block != en_m.group(2))

    if added == 0 and updated == 0 and not needs_reformat:
        print(f'  · {alias}: {len(pairs)} pairs from Notion · already in sync')
        return out

    if needs_reformat and added == 0 and updated == 0:
        out['reformatted'] = True
        print(f'  ↻ {alias}: reformatting arrays (encoding fix only)')

    # Rebuild HTML with replaced arrays (do EN first so positions don't shift)
    html_new = html
    html_new = html_new[:en_m.start(2)] + en_block + html_new[en_m.end(2):]
    # After EN replacement, VI_RE positions may have shifted. Re-search VI on new text.
    vi_m2 = VI_RE.search(html_new)
    if vi_m2:
        html_new = html_new[:vi_m2.start(2)] + vi_block + html_new[vi_m2.end(2):]

    if added or updated:
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

    totals = {'added': 0, 'updated': 0, 'pairs_extracted': 0, 'reformatted': 0}
    for alias in aliases:
        if alias not in ALIAS_TO_FILENAME:
            print(f'  ? unknown alias: {alias}')
            continue
        fname = ALIAS_TO_FILENAME[alias]
        html_path = BROCHURES_DIR / fname
        payload_path = DATA_DIR / f'{alias}_payload.json'
        c = process_brochure(alias, html_path, payload_path, dry_run=dry_run)
        for k, v in c.items():
            if k in totals:
                totals[k] += int(v) if isinstance(v, bool) else v

    mode = 'dry-run' if dry_run else 'applied'
    print(f"\n{'─' * 70}")
    print(f"Done: {totals['added']} added, {totals['updated']} updated "
          f"across {totals['pairs_extracted']} pairs extracted ({mode}).")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
