"""Add VI/EN translation pairs directly to a brochure's bilingual arrays.

Used to patch in translations for DOM strings that exist on the page but
don't have a corresponding entry in VI_STRINGS / EN_STRINGS — usually
surfaced by `tools/simulate_en_render.py`.

The pairs go through the same `js_escape_string` + `merge_arrays` logic
as `tools/inject_notion_en_to_html.py`, so the encoding (innerHTML form,
KSES-safe quote choice) stays consistent.

Run:
    python tools/add_translation_pairs.py <alias> <pairs.json>

Where `pairs.json` is:
    {
      "vi text 1": "en text 1",
      "vi text 2": "en text 2"
    }
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from inject_notion_en_to_html import (  # noqa: E402
    ALIAS_TO_FILENAME, BROCHURES_DIR, VI_RE, EN_RE,
    parse_array_literal, merge_arrays, format_array,
)


def main():
    if len(sys.argv) < 3:
        print("Usage: add_translation_pairs.py <alias> <pairs.json>")
        return 1
    alias, pairs_path = sys.argv[1], Path(sys.argv[2])
    if alias not in ALIAS_TO_FILENAME:
        print(f"Unknown alias: {alias}")
        return 1
    pairs_dict = json.loads(pairs_path.read_text(encoding='utf-8'))
    pairs = [(k, v) for k, v in pairs_dict.items() if k and v]

    html_path = BROCHURES_DIR / ALIAS_TO_FILENAME[alias]
    html = html_path.read_text(encoding='utf-8')

    vi_m = VI_RE.search(html)
    en_m = EN_RE.search(html)
    if not vi_m or not en_m:
        print(f"  ⚠ {alias}: no VI_STRINGS / EN_STRINGS arrays found")
        return 1

    existing_vi = parse_array_literal(vi_m.group(2))
    existing_en = parse_array_literal(en_m.group(2))

    new_vi, new_en, added, updated = merge_arrays(existing_vi, existing_en, pairs)

    vi_block = format_array(new_vi)
    en_block = format_array(new_en)

    html_new = html
    html_new = html_new[:en_m.start(2)] + en_block + html_new[en_m.end(2):]
    vi_m2 = VI_RE.search(html_new)
    if vi_m2:
        html_new = html_new[:vi_m2.start(2)] + vi_block + html_new[vi_m2.end(2):]

    html_path.write_text(html_new, encoding='utf-8')
    print(f"  ✓ {alias}: +{added} new, ~{updated} updated (total VI items: {len(new_vi)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
