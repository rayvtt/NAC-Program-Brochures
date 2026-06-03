#!/usr/bin/env python3
"""Repoint every brochure's Property Hub links to that country's WP CLP.

Now that Country Landing Pages exist at
  https://nomadassetcollective.com/property-hub-bat-dong-san/<country>/
each country brochure's "Property Hub" links (nav link, listings-section
"all eligible properties" link, sidebar hub tool) should deep-link to that
country's CLP instead of the generic hub.

- Countries whose CLP is live on WP -> link to the country CLP.
- Countries with no CLP yet -> fall back to the parent hub (no 404). Re-run this
  script after their CLP is created to upgrade the link.
- Non-country files (overview / index) -> canonical parent hub.

Idempotent: running again with no upstream change reports 0 edits.
Verify live CLP slugs with:
  curl -s https://nomadassetcollective.com/page-sitemap.xml \\
    | grep -oE 'property-hub-bat-dong-san/[a-z-]+/'
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BROCHURES = ROOT / "Brochures html"
HUB = "https://nomadassetcollective.com/property-hub-bat-dong-san/"

# brochure filename -> country CLP slug (None = no country / use parent hub)
BROCHURE_COUNTRY = {
    "antigua-cbi.html": "antigua",
    "australia-rbi.html": "australia",
    "cyprus-rbi_3_3.html": "cyprus",
    "greece-rbi_1_2.html": "greece",
    "italy-investor.html": "italy",
    "malaysia-mm2h.html": "malaysia",
    "malta-rbi_1_3.html": "malta",
    "montenegro-rbi.html": "montenegro",
    "nauru-cbi.html": "nauru",
    "newzealand-rbi_1 (3).html": "new-zealand",
    "panama-rbi_.html": "panama",
    "portugal-gv.html": "portugal",
    "spain-gv.html": "spain",
    "stkitts-nevis.html": "st-kitts-nevis",
    "thailand-rbi_1 (2).html": "thailand",
    "turkey-cbi_8.html": "turkey",
    "uae-rbi_1_7.html": "uae",
    "uk-rbi_1 (2).html": "uk",
}

# CLP slugs that are LIVE on WP (verified via page-sitemap.xml). Brochure
# countries not in this set fall back to the parent hub until their CLP exists.
LIVE_CLP = {
    "australia", "cyprus", "greece", "malaysia", "montenegro",
    "panama", "thailand", "turkey", "uae", "uk",
}

# Matches the bare hub link or the ?program=...&country=... variant, but never
# the target (property-hub-bat-dong-san) because it requires "property-hub/".
LINK_RE = re.compile(r"https://nomadassetcollective\.com/property-hub/(?:\?[^\"'\s]*)?")


def target_for(filename: str) -> str:
    slug = BROCHURE_COUNTRY.get(filename)
    if slug and slug in LIVE_CLP:
        return f"{HUB}{slug}/"
    return HUB  # no country, or CLP not live yet


def main() -> int:
    only = sys.argv[1] if len(sys.argv) > 1 else None
    total = 0
    for path in sorted(BROCHURES.glob("*.html")):
        if only and only not in path.name:
            continue
        html = path.read_text(encoding="utf-8")
        tgt = target_for(path.name)
        new_html, n = LINK_RE.subn(tgt, html)
        if n and new_html != html:
            path.write_text(new_html, encoding="utf-8")
            kind = "CLP" if tgt != HUB else "parent hub"
            print(f"  ✓ {path.name}: {n} link(s) -> {tgt}  [{kind}]")
            total += n
        else:
            print(f"  · {path.name}: no change")
    print(f"\nRewrote {total} link(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
