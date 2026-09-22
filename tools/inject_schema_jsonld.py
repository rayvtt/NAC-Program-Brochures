#!/usr/bin/env python3
"""
inject_schema_jsonld.py — schema.org JSON-LD for every country brochure.

Brochures ship with ZERO structured data (no JSON-LD, no canonical, no OG in a
crawlable position — the file's <head> is echoed into the WP page BODY, so only
JSON-LD survives as valid, crawlable structured data). This tool builds a
schema.org @graph from each brochure's Notion payload (data/<alias>_payload.json)
and injects an idempotent

    <script type="application/ld+json" id="nac-schema"> … </script>

block before </head> of the brochure HTML. Mirrors the LLP pattern
(scripts/seo-geo-llm.mjs in the PDP repo): factual, data-gated, deterministic /
idempotent (re-running yields byte-identical output).

@graph per brochure:
  - WebPage         (about a Country, publisher = NAC, primaryImageOfPage)
  - Organization    (NAC, shared @id, logo)
  - Service         (Residency/Citizenship by investment) + Offer (min investment)
  - BreadcrumbList  (Home › Programs › <program>)
  - FAQPage         (3–6 factual Q&As built only from fields that have real data)

WP-safety (this repo's CLAUDE.md §4): every string value is stripped to plain
text with NO double-quotes, NO backslashes and NO angle brackets, so the emitted
block contains zero `\\"` and zero `\\` — safe from wp_unslash AND parity check
#2. The block is type="application/ld+json", which parity check #15 skips.

Usage:
    python tools/inject_schema_jsonld.py               # all brochures
    python tools/inject_schema_jsonld.py portugal      # one alias
    python tools/inject_schema_jsonld.py --dry-run
"""
import json
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML_DIR = os.path.join(ROOT, "Brochures html")
DATA_DIR = os.path.join(ROOT, "data")
ORIGIN = "https://nomadassetcollective.com"
ORG_ID = f"{ORIGIN}/#org"
LOGO = "https://nomadassetcollective.com/wp-content/uploads/2026/05/nac-logo-wordmark.png"
MARKER_ID = "nac-schema"

SERVICE_TYPE = {
    "CBI": "Citizenship by investment",
    "RBI": "Residency by investment",
    "MM2H": "Long-term residency",
    "LTR": "Long-term residency",
    "GV": "Residency by investment",
}

CUR_SYMBOL = {"€": "EUR", "$": "USD", "£": "GBP", "฿": "THB", "ท": "THB", "₫": "VND"}
CUR_CODE = ["EUR", "USD", "GBP", "NZD", "SGD", "AED", "THB", "AUD", "CAD", "VND",
            "CHF", "HKD", "MYR"]


def clean(text, cap=320):
    """HTML → plain text; strip quotes/backslashes/angle brackets; cap at a
    sentence boundary. Guarantees no `"`, `\\`, `<`, `>` in the result."""
    if text is None:
        return ""
    s = str(text)
    s = re.sub(r"<[^>]+>", " ", s)                 # strip tags
    s = (s.replace("&amp;", "&").replace("&nbsp;", " ")
           .replace("&#8217;", "'").replace("&#8216;", "'")
           .replace("&quot;", "").replace("&ldquo;", "").replace("&rdquo;", "")
           .replace("&#8211;", "-").replace("&#8212;", "-").replace("&mdash;", "-"))
    s = s.replace('"', "").replace("\\", " ").replace("<", " ").replace(">", " ")
    s = re.sub(r"\s+", " ", s).strip()
    if cap and len(s) > cap:
        cut = s[:cap]
        m = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
        s = (cut[:m + 1] if m > cap * 0.5 else cut.rstrip() + "…").strip()
    return s


def load_stats(d):
    hs = d.get("hero_stats")
    if isinstance(hs, str):
        try:
            hs = json.loads(hs)
        except Exception:
            hs = None
    return hs if isinstance(hs, list) else []


def parse_money(num):
    """'€250K'→(250000,'EUR'); 'NZD 5M'→(5000000,'NZD'); '$150K+'→(150000,'USD')."""
    if not num:
        return None
    s = str(num).strip()
    cur = None
    for code in CUR_CODE:
        if re.search(r"\b" + code + r"\b", s, re.I):
            cur = code.upper()
            break
    if not cur:
        for sym, code in CUR_SYMBOL.items():
            if sym in s:
                cur = code
                break
    m = re.search(r"([0-9]+(?:[.,][0-9]+)?)\s*([KkMmBb])?", s)
    if not m:
        return None
    val = float(m.group(1).replace(",", ""))
    mult = {"k": 1e3, "m": 1e6, "b": 1e9}.get((m.group(2) or "").lower(), 1)
    amount = int(round(val * mult))
    if not cur:
        cur = "USD"
    return amount, cur


def first_money(d):
    for st in load_stats(d):
        pm = parse_money(st.get("num"))
        if pm:
            return pm
    return None


def build_faq(d, program_en, country_en):
    qa = []
    stats = load_stats(d)
    if stats:
        parts = []
        for st in stats[:4]:
            num = clean(st.get("num"), 40)
            lbl = clean(st.get("lbl_en") or st.get("lbl_vi"), 60)
            if num and lbl:
                parts.append(f"{num} ({lbl})")
            elif num:
                parts.append(num)
        if parts:
            qa.append((
                f"What is the minimum investment for the {program_en}?",
                f"Key figures for the {program_en}: " + "; ".join(parts) + "."))
    desc = clean(d.get("hero_desc_en") or d.get("hero_desc_vi"))
    if desc:
        qa.append((f"What is the {program_en}?", desc))
    proc = clean(d.get("s03_subtitle_en") or d.get("s03_subtitle_vi"))
    if proc:
        qa.append((f"How does the {program_en} application process work?", proc))
    fam = clean(d.get("s04_subtitle_en") or d.get("s04_subtitle_vi"))
    if fam:
        qa.append((f"Which family members can be included in the {program_en}?", fam))
    tax = clean(d.get("s05_subtitle_en") or d.get("s05_subtitle_vi"))
    if tax:
        qa.append((f"What are the tax considerations for the {program_en}?", tax))
    try:
        score = float(d.get("nac_score") or 0)
    except Exception:
        score = 0
    if score > 0:
        lbl = clean(d.get("nac_score_label_en") or d.get("nac_score_label_vi"), 120)
        ans = f"NAC rates the {program_en} {int(round(score))}/100"
        ans += f" ({lbl})." if lbl else "."
        qa.append((f"How does NAC rate the {program_en}?", ans))
    return [{
        "@type": "Question",
        "name": clean(q, 160),
        "acceptedAnswer": {"@type": "Answer", "text": a},
    } for q, a in qa if a]


def build_graph(d):
    program_en = clean(d.get("program_en") or d.get("country_en"), 120) or "Investment Migration Program"
    program_vi = clean(d.get("program_vi"), 120)
    country_en = clean(d.get("country_en"), 80)
    slug = (d.get("wp_slug") or "").strip("/")
    canonical = f"{ORIGIN}/brochures/{slug}/" if slug else f"{ORIGIN}/brochures/"
    code = (d.get("program_code") or "RBI").upper()
    stype = SERVICE_TYPE.get(code, "Residency by investment")
    l2_name = clean(d.get("hero_breadcrumb_en"), 60) or "Investment Migration Programs"
    desc = clean(d.get("hero_desc_en") or d.get("hero_desc_vi"))
    keywords = clean(d.get("hero_badge_en") or d.get("hero_badge_vi"), 160)
    hero = (d.get("hero_bg_img") or "").split("?")[0]

    org = {
        "@type": "Organization",
        "@id": ORG_ID,
        "name": "Nomad Asset Collective",
        "url": f"{ORIGIN}/",
        "logo": LOGO,
    }
    webpage = {
        "@type": "WebPage",
        "@id": f"{canonical}#webpage",
        "url": canonical,
        "name": f"{program_en} | Nomad Asset Collective",
        "inLanguage": "vi",
        "isPartOf": {"@type": "WebSite", "name": "Nomad Asset Collective", "url": f"{ORIGIN}/"},
        "publisher": {"@id": ORG_ID},
    }
    if desc:
        webpage["description"] = desc
    if country_en:
        webpage["about"] = {"@type": "Country", "name": country_en}
    if keywords:
        webpage["keywords"] = keywords
    if hero.startswith("https://"):
        webpage["primaryImageOfPage"] = hero

    service = {
        "@type": "Service",
        "name": program_en,
        "serviceType": stype,
        "provider": {"@id": ORG_ID},
    }
    if program_vi and program_vi != program_en:
        service["alternateName"] = program_vi
    if country_en:
        service["areaServed"] = {"@type": "Country", "name": country_en}
    if desc:
        service["description"] = desc
    pm = first_money(d)
    if pm:
        service["offers"] = {
            "@type": "Offer",
            "price": str(pm[0]),
            "priceCurrency": pm[1],
            "description": "Minimum qualifying investment",
            "url": canonical,
        }

    breadcrumb = {
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": f"{ORIGIN}/"},
            {"@type": "ListItem", "position": 2, "name": l2_name, "item": f"{ORIGIN}/brochures/"},
            {"@type": "ListItem", "position": 3, "name": program_en, "item": canonical},
        ],
    }

    graph = [webpage, org, service, breadcrumb]
    faq = build_faq(d, program_en, country_en)
    if faq:
        graph.append({"@type": "FAQPage", "@id": f"{canonical}#faq", "mainEntity": faq})
    return {"@context": "https://schema.org", "@graph": graph}


def render_block(graph):
    body = json.dumps(graph, ensure_ascii=False, indent=2)
    # Hard guarantee for WP-safety + parity: no backslash escapes at all.
    assert "\\" not in body, "schema JSON-LD contains a backslash (WP-unsafe)"
    assert '\\"' not in body
    assert "</" not in body
    return (f'<script type="application/ld+json" id="{MARKER_ID}">\n'
            f"{body}\n</script>")


BLOCK_RE = re.compile(
    r'[ \t]*<script type="application/ld\+json" id="' + MARKER_ID + r'">.*?</script>\n?',
    re.DOTALL)


def inject(html, block):
    """Idempotently place the block immediately before </head>."""
    cleaned = BLOCK_RE.sub("", html)
    if "</head>" in cleaned:
        return cleaned.replace("</head>", block + "\n</head>", 1), True
    # no </head> (fragment) — prepend
    return block + "\n" + cleaned, True


def process(alias, dry=False):
    payload = os.path.join(DATA_DIR, f"{alias}_payload.json")
    if not os.path.exists(payload):
        return f"{alias:12} SKIP (no payload)"
    d = json.load(open(payload, encoding="utf-8"))
    src = d.get("source_filename")
    path = os.path.join(HTML_DIR, src) if src else ""
    if not path or not os.path.exists(path):
        # Fallback: payload source_filename can drift from the real file name
        # (e.g. panama-rbi.html vs panama-rbi_.html). Match by alias prefix,
        # excluding the shared NAC-* index/overview files.
        cands = sorted(
            p for p in glob.glob(os.path.join(HTML_DIR, f"{alias}*.html"))
            if not os.path.basename(p).startswith("NAC-"))
        if not cands:
            return f"{alias:12} SKIP (no HTML file for alias)"
        path = cands[0]
        src = os.path.basename(path)
    graph = build_graph(d)
    block = render_block(graph)
    html = open(path, encoding="utf-8").read()
    new_html, _ = inject(html, block)
    n_types = len(graph["@graph"])
    n_faq = sum(len(g.get("mainEntity", [])) for g in graph["@graph"] if g.get("@type") == "FAQPage")
    if new_html == html:
        return f"{alias:12} unchanged  ({n_types} types, {n_faq} FAQ)"
    if not dry:
        open(path, "w", encoding="utf-8").write(new_html)
    return f"{alias:12} {'would write' if dry else 'WROTE'}    ({n_types} types, {n_faq} FAQ) -> {src}"


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry = "--dry-run" in sys.argv
    if args:
        aliases = args
    else:
        aliases = sorted(
            os.path.basename(f).replace("_payload.json", "")
            for f in glob.glob(os.path.join(DATA_DIR, "*_payload.json")))
        aliases = [a for a in aliases if a != "sosanh"]
    print(f"schema.org JSON-LD injector — {len(aliases)} brochure(s){' [dry-run]' if dry else ''}")
    for a in aliases:
        print("  " + process(a, dry))


if __name__ == "__main__":
    main()
