"""Refresh article-CTA cover images from each linked article's og:image.

Scans every brochure HTML in ``Brochures html/`` for
``<a class="article-cta-banner" href="..." style="background-image:url(...)">``
blocks, fetches the linked URL, extracts the ``og:image`` meta tag, and
rewrites the inline ``background-image`` to point at that URL.

Banners that carry the ``nac-index-banner`` class are skipped — they paint
a canvas globe, not a static image.

Run:
    python tools/refresh_article_covers.py             # all brochures
    python tools/refresh_article_covers.py turkey      # one brochure
    python tools/refresh_article_covers.py --dry-run   # show changes only

Designed to be idempotent: re-running with no upstream changes is a no-op.
"""
from __future__ import annotations

import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BROCHURES_DIR = ROOT / "Brochures html"

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/16.6 Safari/605.1.15"
)

# Match the whole <a class="article-cta-banner ..." ...> opening tag
BANNER_RE = re.compile(
    r'<a\s+class="article-cta-banner([^"]*)"\s+([^>]*?)>',
    re.IGNORECASE,
)
HREF_RE = re.compile(r'href="([^"]+)"', re.IGNORECASE)
BG_RE = re.compile(r'background-image\s*:\s*url\(\s*([\'"])(.*?)\1\s*\)', re.IGNORECASE)

# og:image / twitter:image extraction — tolerant of attribute order
OG_RES = [
    re.compile(
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        re.IGNORECASE,
    ),
    re.compile(
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
        re.IGNORECASE,
    ),
    re.compile(
        r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
        re.IGNORECASE,
    ),
]


def fetch_og_image(url: str) -> str | None:
    """Fetch ``url`` and return the og:image / twitter:image URL, or ``None``."""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            # Cap at 512KB — the <head> is always near the top
            body = r.read(512 * 1024).decode("utf-8", errors="ignore")
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
        print(f"    ! fetch failed: {e}")
        return None

    for pat in OG_RES:
        m = pat.search(body)
        if m:
            return m.group(1).strip()
    return None


def process_file(path: Path, dry_run: bool = False) -> tuple[int, int]:
    """Return ``(updated, unchanged)`` count for ``path``."""
    print(f"\n→ {path.name}")
    text = path.read_text(encoding="utf-8")
    original = text

    updated = 0
    unchanged = 0

    # Find every banner opening tag, then mutate one at a time. We walk
    # via finditer on the *original* text but accumulate edits with offset
    # tracking so we can swap each background-image URL precisely.
    edits: list[tuple[int, int, str]] = []

    for m in BANNER_RE.finditer(text):
        class_extra = m.group(1)
        attrs = m.group(2)

        if "nac-index-banner" in class_extra:
            # Canvas globe banner — no static cover to refresh
            continue

        href_m = HREF_RE.search(attrs)
        bg_m = BG_RE.search(attrs)
        if not href_m or not bg_m:
            continue

        article_url = href_m.group(1)
        current_bg = bg_m.group(2)
        print(f"  • article: {article_url}")

        og = fetch_og_image(article_url)
        if not og:
            print("    ! no og:image found — leaving cover untouched")
            unchanged += 1
            continue

        if og == current_bg:
            print("    = cover already up to date")
            unchanged += 1
            continue

        print(f"    ✓ {current_bg}")
        print(f"      → {og}")

        # Absolute positions in `text` of the bg URL group inside this match
        quote_char = bg_m.group(1)
        url_start = m.start(2) + bg_m.start(2)
        url_end = m.start(2) + bg_m.end(2)
        edits.append((url_start, url_end, og))
        updated += 1

    # Apply edits back-to-front so earlier offsets stay valid
    for start, end, new in reversed(edits):
        text = text[:start] + new + text[end:]

    if text != original:
        if dry_run:
            print(f"  [dry-run] would write {updated} cover URL(s)")
        else:
            path.write_text(text, encoding="utf-8")
            print(f"  → wrote {updated} cover URL(s)")
    elif updated == 0 and unchanged == 0:
        print("  (no article-cta-banner blocks)")

    return updated, unchanged


def main() -> int:
    args = sys.argv[1:]
    dry_run = "--dry-run" in args
    args = [a for a in args if not a.startswith("--")]

    if args:
        # Filter brochures by alias (e.g. "turkey" matches turkey-cbi_8.html)
        aliases = [a.lower() for a in args]
        files = [
            p for p in sorted(BROCHURES_DIR.glob("*.html"))
            if any(p.name.lower().startswith(a) for a in aliases)
        ]
        if not files:
            print(f"No brochure matches: {aliases}", file=sys.stderr)
            return 1
    else:
        files = sorted(BROCHURES_DIR.glob("*.html"))

    total_updated = 0
    total_unchanged = 0
    for f in files:
        if f.name == "NAC-BROCHURES-OVERVIEW.html":
            continue
        u, n = process_file(f, dry_run=dry_run)
        total_updated += u
        total_unchanged += n

    mode = "[dry-run] would update" if dry_run else "updated"
    print(f"\nDone — {mode} {total_updated} cover(s), {total_unchanged} already fresh.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
