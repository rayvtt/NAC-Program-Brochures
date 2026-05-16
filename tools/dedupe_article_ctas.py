"""Dedupe article CTA URLs within each brochure.

Rule: if multiple article-cta-banner cards point to the same URL,
later occurrences are redirected to the blog homepage. Keeps the
first occurrence intact (so the specific article is still linked
once) and replaces duplicate URLs with the generic blog landing.

Each card has TWO URL touchpoints:
  - The <a class="article-cta-banner" href="..."> wrapping kicker+title
  - The <a class="article-cta-btn"   href="..."> in the body
Both are rewritten in the same block.

Idempotent — second-pass is a no-op because the duplicate URLs are
already the blog homepage.

Run:
    python tools/dedupe_article_ctas.py             # all 12
    python tools/dedupe_article_ctas.py portugal    # one alias
    python tools/dedupe_article_ctas.py --dry-run
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BROCHURES_DIR = ROOT / "Brochures html"
SKIP = {"NAC-BROCHURES-OVERVIEW.html", "NAC-RESIDENCE-INDEX.html"}

BLOG_HOME = "https://blog.nomadassetcollective.com/"

# Generic copy for cards that got redirected to the blog homepage —
# avoids misleading the reader (title says "Article X" but URL → blog).
REDIRECT_KICKER_VI = "Khám phá thêm"
REDIRECT_KICKER_EN = "Explore more"
REDIRECT_TITLE_VI  = "Đọc thêm phân tích trên Blog NAC"
REDIRECT_TITLE_EN  = "More analysis on the NAC Blog"
REDIRECT_DESC_VI   = "Tất cả bài viết chuyên sâu của đội ngũ NAC dành cho nhà đầu tư HNWI Việt — cập nhật hàng tuần."
REDIRECT_DESC_EN   = "All in-depth analysis from the NAC team for Vietnamese HNWI investors — updated weekly."
REDIRECT_BTN_VI    = "Tới Blog →"
REDIRECT_BTN_EN    = "Visit Blog →"

# Match an entire article-cta block (with banner-card structure):
BLOCK_RE = re.compile(
    r'(<div class="article-cta[^"]*"[^>]*>\s*)'
    r'<a class="article-cta-banner[^"]*"(\s+href=")([^"]+)("[^>]*?)>'
    r'([\s\S]*?)'                                     # banner inner (kicker + title)
    r'</a>\s*'
    r'<div class="article-cta-body">\s*'
    r'<p class="article-cta-desc"([^>]*)>([^<]*)</p>\s*'
    r'<a class="article-cta-btn"\s+href="([^"]+)"([^>]*?)>([^<]+)</a>\s*'
    r'</div>\s*</div>',
    re.DOTALL,
)


def _kicker_html(orig_kicker: str | None) -> str:
    """Return a kicker <span> with data-vi/data-en attrs for the redirect."""
    return (
        f'<span class="article-cta-kicker" '
        f'data-vi="{REDIRECT_KICKER_VI}" data-en="{REDIRECT_KICKER_EN}">'
        f'{REDIRECT_KICKER_VI}</span>'
    )


def _title_html() -> str:
    return (
        f'<h3 class="article-cta-title" '
        f'data-vi="{REDIRECT_TITLE_VI}" data-en="{REDIRECT_TITLE_EN}">'
        f'{REDIRECT_TITLE_VI}</h3>'
    )


def dedupe(text: str) -> tuple[str, int]:
    """Return (new_text, num_redirected)."""
    seen: set[str] = set()
    redirected = 0

    def rewrite(m: re.Match) -> str:
        nonlocal redirected
        block_open       = m.group(1)
        banner_href_open = m.group(2)
        banner_url       = m.group(3)
        banner_attrs     = m.group(4)
        banner_inner     = m.group(5)
        desc_attrs       = m.group(6)
        desc_text        = m.group(7)
        btn_url          = m.group(8)
        btn_attrs        = m.group(9)
        btn_text         = m.group(10)

        # Don't dedupe the NAC Index banner — special CTA target
        if "nac-residence-index" in banner_url or "/so-sanh" in banner_url:
            return m.group(0)

        if banner_url in seen:
            redirected += 1
            # Rebuild a generic "more on the blog" card
            return (
                f'{block_open}'
                f'<a class="article-cta-banner"{banner_href_open}{BLOG_HOME}{banner_attrs}>'
                f'\n          {_kicker_html(None)}'
                f'\n          {_title_html()}'
                f'\n        </a>\n'
                f'        <div class="article-cta-body">\n'
                f'          <p class="article-cta-desc"{desc_attrs} '
                f'data-vi="{REDIRECT_DESC_VI}" data-en="{REDIRECT_DESC_EN}">'
                f'{REDIRECT_DESC_VI}</p>\n'
                f'          <a class="article-cta-btn" href="{BLOG_HOME}"{btn_attrs} '
                f'data-vi="{REDIRECT_BTN_VI}" data-en="{REDIRECT_BTN_EN}">'
                f'{REDIRECT_BTN_VI}</a>\n'
                f'        </div>\n'
                f'      </div>'
            )
        seen.add(banner_url)
        return m.group(0)

    new_text = BLOCK_RE.sub(rewrite, text)
    return new_text, redirected


def main() -> int:
    args = sys.argv[1:]
    dry_run = "--dry-run" in args
    args = [a for a in args if not a.startswith("--")]

    if args:
        aliases = [a.lower() for a in args]
        files = [
            p for p in sorted(BROCHURES_DIR.glob("*.html"))
            if p.name not in SKIP
            and any(p.name.lower().startswith(a) for a in aliases)
        ]
    else:
        files = [p for p in sorted(BROCHURES_DIR.glob("*.html")) if p.name not in SKIP]

    total = 0
    for f in files:
        text = f.read_text(encoding="utf-8")
        new_text, n = dedupe(text)
        marker = "[dry]" if dry_run else ("✓" if n else "·")
        print(f"  {marker} {f.name}: {n} duplicate(s) redirected → blog")
        if n and not dry_run:
            f.write_text(new_text, encoding="utf-8")
        total += n

    print(
        f"\nDone — {total} duplicate CTA URL(s) redirected to blog homepage "
        f"({'dry-run' if dry_run else 'applied'})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
