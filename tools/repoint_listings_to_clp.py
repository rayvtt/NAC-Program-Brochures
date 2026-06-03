#!/usr/bin/env python3
"""Repoint the "All RBI-eligible properties →" link below each brochure's
listings section from the old Property Hub catalog query
(`/property-hub/?program=…&country=…`) to the new Country Listing Page
(`/property-hub-bat-dong-san/<slug>/`).

Only brochures whose country has a Live CLP in the Notion "🌍 NAC -
Country Listings" DB are repointed. Brochures without a CLP keep the
existing Property Hub catalog link rather than getting dead links.

Idempotent — re-running reports 0 changes.

Run:
    python tools/repoint_listings_to_clp.py            # all brochures
    python tools/repoint_listings_to_clp.py cyprus     # one
"""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent.parent
HTML_DIR = ROOT / "Brochures html"

# Confirmed Live CLPs from the Notion DB (🌍 NAC - Country Listings) on
# 2026-06-03. The map key is the brochure ALIAS (matches sync_brochures.py),
# value is the CLP URL slug used at /property-hub-bat-dong-san/<slug>/.
#
# Brochures NOT listed here keep their existing Property Hub catalog
# link — no CLP exists yet, so the old link is the better fallback.
CLP_SLUG = {
    "cyprus":     "cyprus",
    "turkey":     "turkey",
    "uk":         "united-kingdom",
    "greece":     "greece",
    "panama":     "panama",
    "uae":        "uae",
    "malaysia":   "malaysia",
    "thailand":   "thailand",
    "australia":  "australia",
}

# Brochure FILENAME prefix → alias (the file naming has version suffixes
# and stray spaces; map by leading token).
FILE_TO_ALIAS = {
    "antigua-cbi":      "antigua",
    "australia-rbi":    "australia",
    "cyprus-rbi":       "cyprus",
    "greece-rbi":       "greece",
    "italy-investor":   "italy",
    "malaysia-mm2h":    "malaysia",
    "malta-rbi":        "malta",
    "montenegro-rbi":   "montenegro",
    "nauru-cbi":        "nauru",
    "newzealand-rbi":   "newzealand",
    "panama-rbi":       "panama",
    "portugal-gv":      "portugal",
    "stkitts-nevis":    "stkitts",
    "thailand-rbi":     "thailand",
    "turkey-cbi":       "turkey",
    "uae-rbi":          "uae",
    "uk-rbi":           "uk",
    "spain-gv":         "spain",
}

OLD_PATTERN = re.compile(
    r'(class="(?:listings-fn-link|listing-placeholder-link)"\s+href=")'
    r'https://nomadassetcollective\.com/property-hub/\?program=[a-z]+&country=[a-z]+'
    r'(")'
)


def file_alias(path: Path) -> str | None:
    stem = path.stem.lower().strip()
    for prefix, alias in FILE_TO_ALIAS.items():
        if stem.startswith(prefix):
            return alias
    return None


def repoint_one(path: Path) -> str:
    alias = file_alias(path)
    if not alias:
        return "no-alias"
    if alias not in CLP_SLUG:
        return f"no-clp ({alias})"

    html = path.read_text(encoding="utf-8")
    new_url = f"https://nomadassetcollective.com/property-hub-bat-dong-san/{CLP_SLUG[alias]}/"

    new_html, n = OLD_PATTERN.subn(rf'\g<1>{new_url}\g<2>', html)
    if n == 0:
        return "already" if new_url in html else "no-match"

    path.write_text(new_html, encoding="utf-8")
    return f"repointed ({n})"


def matches(target: str | None) -> list[Path]:
    files = sorted(HTML_DIR.glob("*.html"))
    if not target:
        return files
    return [f for f in files if target.lower() in f.name.lower()]


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else None
    files = matches(target)
    if not files:
        sys.exit(f"No brochures match {target!r}")
    counts = {"repointed": 0, "already": 0, "no-clp": 0, "no-match": 0, "no-alias": 0}
    for f in files:
        result = repoint_one(f)
        key = result.split(" ")[0]
        counts[key] = counts.get(key, 0) + 1
        sym = {"repointed": "✓", "already": "·", "no-clp": "○",
               "no-match": "?", "no-alias": "—"}[key]
        print(f"  {sym} {f.name:<35} {result}")
    print(f"\n{counts.get('repointed',0)} repointed, "
          f"{counts.get('already',0)} already pointed, "
          f"{counts.get('no-clp',0)} no CLP yet (kept old link), "
          f"{counts.get('no-match',0)} no-match, "
          f"{counts.get('no-alias',0)} no-alias")


if __name__ == "__main__":
    main()
