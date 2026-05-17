"""Parse a Notion-MCP fetch response and extract VI/EN string pairs.

Reads /tmp/notion_<alias>.txt (the raw MCP response text) and writes
/tmp/notion_<alias>_pairs.json — a flat list of {vi, en} pairs ready
for injection into a brochure's VI_STRINGS / EN_STRINGS arrays.

Usage:
    python tools/parse_notion_to_pairs.py <alias>
"""
import json
import re
import sys
from pathlib import Path

TMP = Path("/tmp")


def unescape_notion(s: str) -> str:
    """Reverse the backslash-escape Notion-MCP uses for special chars."""
    for esc, raw in [
        (r"\<", "<"), (r"\>", ">"),
        (r"\[", "["), (r"\]", "]"),
        (r"\{", "{"), (r"\}", "}"),
        (r"\&", "&"), (r"\$", "$"),
        (r"\~", "~"), (r"\*", "*"),
        (r"\#", "#"), (r"\|", "|"),
        (r"\(", "("), (r"\)", ")"),
        (r"\+", "+"), (r"\!", "!"),
        (r"\=", "="), (r"\-", "-"),
        (r"\.", "."), (r"\_", "_"),
        (r"\`", "`"),
    ]:
        s = s.replace(esc, raw)
    return s


def strip_md_links(s: str) -> str:
    """Notion MCP wraps URLs in [text](url) markdown — collapse to plain."""
    if not isinstance(s, str): return s
    # [text](url) → text
    s = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'\1', s)
    return s


def extract_properties_json(raw: str) -> dict:
    """Pull the JSON inside <properties> ... </properties>."""
    m = re.search(r'<properties>\s*(\{.*?\})\s*</properties>', raw, re.DOTALL)
    if not m:
        raise RuntimeError("Cannot find <properties> block")
    js = m.group(1)
    js = unescape_notion(js)
    return json.loads(js)


def parse_inner_json(value: str):
    """If `value` looks like a JSON array/object, parse it. Else return None."""
    if not isinstance(value, str): return None
    v = value.strip()
    if not (v.startswith("[") or v.startswith("{")): return None
    try:
        return json.loads(v)
    except json.JSONDecodeError:
        return None


# Named (VI) → (EN) field pairs.  Each entry is the COMMON suffix.
NAMED_PAIRS = [
    # (vi_key, en_key)
    ("hero · badge (VI)", "hero · badge (EN)"),
    ("hero · breadcrumb (VI)", "hero · breadcrumb (EN)"),
    ("hero · title top (VI)", "hero · title top (EN)"),
    ("hero · title em (VI)", "hero · title em (EN)"),
    ("hero · desc (VI)", "hero · desc (EN)"),
    ("NAC score label (VI)", "NAC score label (EN)"),
    ("country (VI)", "country (EN)"),
    ("program (VI)", "program (EN)"),
    ("① subtitle (VI)", "① subtitle (EN)"),
    ("① factcheck (VI)", "① factcheck (EN)"),
    ("① article CTA text (VI)", "① article CTA text (EN)"),
    ("② subtitle (VI)", "② subtitle (EN)"),
    ("② warning box (VI)", "② warning box (EN)"),
    ("② NAC note (VI)", "② NAC note (EN)"),
    ("③ subtitle (VI)", "③ subtitle (EN)"),
    ("④ subtitle (VI)", "④ subtitle (EN)"),
    ("④ compare note (VI)", "④ compare note (EN)"),
    ("⑤ subtitle (VI)", "⑤ subtitle (EN)"),
    ("⑤ inheritance note (VI)", "⑤ inheritance note (EN)"),
    ("⑤ special note (VI)", "⑤ special note (EN)"),
    ("⑥ subtitle (VI)", "⑥ subtitle (EN)"),
    ("⑥ dual citizenship note (VI)", "⑥ dual citizenship note (EN)"),
    ("⑥ NAC strategy note (VI)", "⑥ NAC strategy note (EN)"),
    ("⑦ subtitle (VI)", "⑦ subtitle (EN)"),
    ("⑦ CTA text (VI)", "⑦ CTA text (EN)"),
    ("⑧ subtitle (VI)", "⑧ subtitle (EN)"),
    ("⑧ risk note (VI)", "⑧ risk note (EN)"),
    ("⑨ subtitle (VI)", "⑨ subtitle (EN)"),
    ("⑨ CTA heading (VI)", "⑨ CTA heading (EN)"),
    ("⑨ CTA body (VI)", "⑨ CTA body (EN)"),
    ("⑨ recommendation (VI)", "⑨ recommendation (EN)"),
]


def extract_pairs(props: dict) -> list:
    """Walk all bilingual properties + nested JSON, output [{vi, en}, ...]."""
    pairs = []
    seen_vi = set()

    def add(vi, en):
        if not vi or not en: return
        vi = strip_md_links(vi).strip()
        en = strip_md_links(en).strip()
        if not vi or not en or vi == en: return
        if vi in seen_vi: return
        seen_vi.add(vi)
        pairs.append({"vi": vi, "en": en})

    # 1. Named flat pairs
    for vi_key, en_key in NAMED_PAIRS:
        if vi_key in props and en_key in props:
            add(props[vi_key], props[en_key])

    # 2. Nested JSON fields — walk recursively
    json_fields = [
        "hero · stats (JSON)", "① overview cards (JSON)",
        "② tiers (JSON)", "③ timeline (JSON)", "④ family cards (JSON)",
        "⑤ tax cards (JSON)", "⑥ roadmap (JSON)", "⑦ compare rows (JSON)",
        "⑧ pros (JSON)", "⑧ cons (JSON)",
    ]
    for field in json_fields:
        v = props.get(field)
        if not v: continue
        data = parse_inner_json(v)
        if data is None: continue
        # Walk dicts/lists, pair up *_vi and *_en
        for item in (data if isinstance(data, list) else [data]):
            if not isinstance(item, dict): continue
            for k_vi in list(item.keys()):
                if not k_vi.endswith("_vi"): continue
                base = k_vi[:-3]
                k_en = base + "_en"
                if k_en in item:
                    v_vi = item[k_vi]
                    v_en = item[k_en]
                    # Pair scalar values
                    if isinstance(v_vi, str) and isinstance(v_en, str):
                        add(v_vi, v_en)
                    elif isinstance(v_vi, list) and isinstance(v_en, list):
                        # tags arrays
                        for a, b in zip(v_vi, v_en):
                            if isinstance(a, str) and isinstance(b, str):
                                add(a, b)
            # Some pros/cons use {"vi": ..., "en": ...}
            if "vi" in item and "en" in item:
                if isinstance(item["vi"], str) and isinstance(item["en"], str):
                    add(item["vi"], item["en"])

    return pairs


def main():
    if len(sys.argv) < 2:
        print("usage: parse_notion_to_pairs.py <alias>", file=sys.stderr)
        sys.exit(1)
    alias = sys.argv[1]
    raw_path = TMP / f"notion_{alias}.txt"
    out_path = TMP / f"notion_{alias}_pairs.json"
    if not raw_path.exists():
        print(f"missing {raw_path}", file=sys.stderr)
        sys.exit(1)
    raw = raw_path.read_text(encoding="utf-8")
    props = extract_properties_json(raw)
    pairs = extract_pairs(props)
    out_path.write_text(json.dumps(pairs, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  {alias}: {len(pairs)} VI/EN pairs extracted → {out_path}")


if __name__ == "__main__":
    main()
