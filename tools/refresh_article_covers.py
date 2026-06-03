"""Refresh article-CTA cover images from each linked article's og:image.

Scans every brochure HTML in ``Brochures html/`` for
``<a class="article-cta-banner" href="..." style="background-image:url(...)">``
blocks, fetches the linked URL, extracts the ``og:image`` meta tag, and
rewrites the inline ``background-image`` to point at that URL.

Banners that carry the ``nac-index-banner`` class are skipped — they paint
a canvas globe, not a static image.

**Bare-homepage fallback (added Q2/2026):** any banner whose ``href`` is
the bare blog homepage (``https://blog.nomadassetcollective.com/`` —
typically a placeholder when Notion has no specific URL for that CTA yet)
is rewritten to a real, randomised article PDP picked from the NAC blog
categories (Góc Nhìn NAC + Phân Tích). The pick is deterministic per
``(alias, fortnight)`` so the same brochure shows the same article for a
2-week window and then rotates. See ``tools/pick_random_blog_article.py``.

The fallback runs BEFORE the og:image refresh in the same pass, so the
new href flows straight into the cover-update step in the same script
invocation.

Run:
    python tools/refresh_article_covers.py             # all brochures
    python tools/refresh_article_covers.py turkey      # one brochure
    python tools/refresh_article_covers.py --dry-run   # show changes only

Designed to be idempotent: re-running with no upstream changes is a no-op.
"""
from __future__ import annotations

import html as html_lib
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BROCHURES_DIR = ROOT / "Brochures html"

sys.path.insert(0, str(ROOT / "tools"))
from pick_random_blog_article import pick as pick_random_article  # noqa: E402

# Hrefs we treat as "no real article" placeholders that should be backfilled
# with a random PDP. The trailing slash variant is what the page template
# typically renders; the no-slash variant is included defensively.
HOMEPAGE_HREFS = {
    "https://blog.nomadassetcollective.com/",
    "https://blog.nomadassetcollective.com",
}

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/16.6 Safari/605.1.15"
)

# Match the whole <a class="article-cta-banner ..." ...> opening tag
BANNER_RE = re.compile(
    r'<a\s+class="article-cta-banner([^"]*)"\s+([^>]*?)>',
    re.IGNORECASE,
)
# Match the full banner block including the inner h3.article-cta-title we may
# need to rewrite during a homepage→random-PDP swap. Non-greedy so each
# banner block stays distinct.
FULL_BANNER_RE = re.compile(
    r'<a\s+class="article-cta-banner([^"]*)"\s+([^>]*?)>'
    r'(\s*<span class="article-cta-kicker"[^>]*>[\s\S]*?</span>\s*)?'
    r'(<h3 class="article-cta-title"[^>]*>)([\s\S]*?)(</h3>)'
    r'([\s\S]*?</a>)',
    re.IGNORECASE,
)
HREF_RE = re.compile(r'href="([^"]+)"', re.IGNORECASE)
BG_RE = re.compile(r'background-image\s*:\s*url\(\s*([\'"])(.*?)\1\s*\)', re.IGNORECASE)
# .article-cta-btn — the read-more button that sits next to the banner; we
# rewrite its href to match the banner whenever we backfill a random PDP.
CTA_BTN_RE = re.compile(
    r'(<a\s+class="article-cta-btn"\s+href=")([^"]+)("[^>]*>)',
    re.IGNORECASE,
)

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


# Map filename prefix → brochure alias. Mirrors sync_brochures.py / apply_listings.py.
_ALIAS_BY_PREFIX = {
    "turkey": "turkey", "portugal": "portugal", "greece": "greece",
    "cyprus": "cyprus", "uae": "uae", "uk": "uk", "malta": "malta",
    "stkitts": "stkitts", "thailand": "thailand", "newzealand": "newzealand",
    "panama": "panama", "malaysia": "malaysia",
    "antigua": "antigua",
    "italy": "italy",
    "spain": "spain",
    "montenegro": "montenegro",
}


def alias_for(path: Path) -> str | None:
    name = path.name.lower()
    for prefix, alias in _ALIAS_BY_PREFIX.items():
        if name.startswith(prefix):
            return alias
    return None


def backfill_homepage_banners(text: str, alias: str | None) -> tuple[str, int]:
    """Walk every article-cta-banner block. For any banner whose href is the
    bare blog homepage (placeholder), substitute a random NAC-blog PDP +
    rewrite the inner h3 title to match. The neighbouring article-cta-btn
    (the "Read Now →" button) is also rewired to the same URL.

    Returns ``(new_text, swapped_count)``. ``swapped_count == 0`` is a no-op.
    """
    if not text:
        return text, 0

    # First pass: identify all banner blocks that need swapping.
    swap_jobs: list[tuple[re.Match, dict]] = []
    chosen_article: dict | None = None  # cache one pick per (alias, run)
    for m in FULL_BANNER_RE.finditer(text):
        class_extra = m.group(1)
        attrs = m.group(2)
        if "nac-index-banner" in class_extra:
            continue
        href_m = HREF_RE.search(attrs)
        if not href_m:
            continue
        if href_m.group(1) not in HOMEPAGE_HREFS:
            continue
        if chosen_article is None:
            chosen_article = pick_random_article(alias)
            if not chosen_article:
                print("    ! random-article fallback: pick failed, skipping swaps")
                return text, 0
        swap_jobs.append((m, chosen_article))

    if not swap_jobs:
        return text, 0

    # Build edits in reverse to keep offsets stable.
    edits: list[tuple[int, int, str]] = []
    for m, article in swap_jobs:
        new_href = article["url"]
        new_title_text = article["title"] or "Đọc thêm phân tích trên Blog NAC"

        # Edit 1: swap href in the banner's attrs group (group 2).
        attrs = m.group(2)
        href_m = HREF_RE.search(attrs)
        href_start = m.start(2) + href_m.start(1)
        href_end = m.start(2) + href_m.end(1)
        edits.append((href_start, href_end, new_href))

        # Edit 2: swap inner h3 title text (group 5 = title innerHTML).
        title_start = m.start(5)
        title_end = m.end(5)
        # HTML-escape the new title — picker already unescapes from og:title
        safe = html_lib.escape(new_title_text, quote=False)
        edits.append((title_start, title_end, safe))

        print(f"    ✓ random-article fallback ({alias or '?'}):")
        print(f"      url:   {new_href}")
        print(f"      title: {new_title_text}")

    new_text = text
    for start, end, repl in sorted(edits, key=lambda e: -e[0]):
        new_text = new_text[:start] + repl + new_text[end:]

    # Edit pass 3: any .article-cta-btn that still points at the bare
    # homepage gets rewired to the same new article URL. We can do this
    # globally because there's at most one chosen_article per file in this
    # run, and the btns we want to swap are exactly the ones that pointed
    # at the placeholder.
    if chosen_article:
        def btn_sub(b: re.Match) -> str:
            cur = b.group(2)
            if cur in HOMEPAGE_HREFS:
                return f'{b.group(1)}{chosen_article["url"]}{b.group(3)}'
            return b.group(0)
        new_text = CTA_BTN_RE.sub(btn_sub, new_text)

    return new_text, len(swap_jobs)


def process_file(path: Path, dry_run: bool = False) -> tuple[int, int]:
    """Return ``(updated, unchanged)`` count for ``path``."""
    print(f"\n→ {path.name}")
    text = path.read_text(encoding="utf-8")
    original = text

    # Pass 0 — backfill any bare-homepage article CTAs with a random PDP from
    # the NAC blog categories (Góc Nhìn NAC + Phân Tích). Deterministic per
    # (alias, fortnight); fires only when the placeholder is still present.
    alias = alias_for(path)
    text, swapped = backfill_homepage_banners(text, alias)
    if swapped:
        print(f"  ↺ backfilled {swapped} bare-homepage banner(s) with random PDPs")

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
