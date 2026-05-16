"""Convert text-only ``.article-cta`` blocks to the magazine-style
banner-card structure used by Turkey.

Old structure:
    <div class="article-cta">
      <div class="article-cta-icon">📖</div>
      <div class="article-cta-text">PREFIX: <a href="URL">TITLE</a> SUFFIX</div>
      <a class="article-cta-btn" href="URL">BUTTON</a>
    </div>

New structure:
    <div class="article-cta">
      <a class="article-cta-banner" href="URL"
         style="background-image:url('PLACEHOLDER')">
        <span class="article-cta-kicker">KICKER</span>
        <h3 class="article-cta-title">TITLE</h3>
      </a>
      <div class="article-cta-body">
        <p class="article-cta-desc">FULL_TEXT_WITHOUT_TITLE</p>
        <a class="article-cta-btn" href="URL">BUTTON</a>
      </div>
    </div>

After running this, run ``tools/refresh_article_covers.py`` to replace
the placeholder cover with the real og:image from each article URL.

Also injects the new ``.article-cta-*`` CSS (cover-image variant) into
the brochure's <style> block — overrides the old text-only CSS in place.

Idempotent — skips blocks that already have ``article-cta-banner``.

Run:
    python tools/migrate_article_cta_banner.py             # all 11
    python tools/migrate_article_cta_banner.py portugal    # one alias
    python tools/migrate_article_cta_banner.py --dry-run
"""
from __future__ import annotations

import html as html_lib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BROCHURES_DIR = ROOT / "Brochures html"
TURKEY = BROCHURES_DIR / "turkey-cbi_8.html"
SKIP = {"NAC-BROCHURES-OVERVIEW.html", "NAC-RESIDENCE-INDEX.html", "turkey-cbi_8.html"}

PLACEHOLDER_COVER = "https://blog.nomadassetcollective.com/wp-content/uploads/2026/05/18-1024x683.jpg"

KICKER_BY_URL = [
    ("/so-sanh", "Công cụ"),
    ("/property-hub", "BĐS đã thẩm định"),
    ("/nac-residence-index", "Công cụ phân tích"),
    ("/tu-van-nhanh", "Tư vấn miễn phí"),
    ("blog.nomadassetcollective.com", "Bài viết đề xuất"),
]

KICKER_BY_PREFIX = [
    ("đọc thêm phân tích", "Bài viết đề xuất"),
    ("xem hướng dẫn chi tiết", "Hướng dẫn chi tiết"),
    ("tìm hiểu thêm", "Phân tích NAC"),
    ("tìm hiểu góc nhìn", "Góc nhìn NAC"),
    ("chưa quyết định", "Công cụ"),
    ("góc nhìn", "Góc nhìn NAC"),
    ("tham khảo", "Phân tích NAC"),
]


def pick_kicker(url: str, prefix_text: str) -> str:
    """Choose a short kicker label based on prefix wording and URL pattern."""
    p = prefix_text.lower().strip().rstrip(":")
    for needle, label in KICKER_BY_PREFIX:
        if needle in p:
            return label
    for needle, label in KICKER_BY_URL:
        if needle in url:
            return label
    return "Bài viết đề xuất"


def extract_banner_css() -> str:
    """Pull the .article-cta + banner CSS rules from Turkey verbatim."""
    src = TURKEY.read_text(encoding="utf-8")
    m = re.search(
        r'/\*\s*── ARTICLE CTA — Banner card[\s\S]*?'
        r'@media \(max-width: 600px\) \{\s*'
        r'\.article-cta-banner[\s\S]*?\}\s*\}',
        src,
    )
    if not m:
        raise RuntimeError("Cannot find article-cta CSS in Turkey")
    return m.group(0)


# Match a single text-only .article-cta block (the old layout).
# Captures icon, prefix text, title (link), suffix text, btn url, btn text.
OLD_BLOCK_RE = re.compile(
    r'<div class="article-cta"([^>]*)>\s*'
    r'<div class="article-cta-icon">([^<]+)</div>\s*'
    r'<div class="article-cta-text">(.*?)</div>\s*'
    r'<a class="article-cta-btn" href="([^"]+)"[^>]*>([^<]+)</a>\s*'
    r'</div>',
    re.DOTALL,
)
# Inner: parse PREFIX <a href="URL">TITLE</a> SUFFIX from article-cta-text
LINK_IN_TEXT_RE = re.compile(
    r'^(.*?)<a href="([^"]+)"[^>]*>(.*?)</a>(.*)$',
    re.DOTALL,
)


def transform_block(m: re.Match) -> str:
    """Turn an old text-only article-cta block into a banner-card block."""
    extra_attrs = m.group(1)
    icon = m.group(2)  # currently unused — kicker is derived from text/URL
    text_inner = m.group(3).strip()
    btn_href = m.group(4)
    btn_label = m.group(5).strip()

    link_match = LINK_IN_TEXT_RE.match(text_inner)
    if not link_match:
        # No inline link inside text — treat the whole text as title
        # and use the btn href as the banner href.
        prefix = ""
        article_url = btn_href
        title = text_inner
        suffix = ""
    else:
        prefix = link_match.group(1).strip()
        article_url = link_match.group(2)
        title = link_match.group(3).strip()
        suffix = link_match.group(4).strip()

    # Clean up prefix / suffix — strip trailing colon, leading dashes, etc.
    prefix_clean = re.sub(r'[:：]\s*$', '', prefix).strip()
    desc = (prefix_clean + (" " if prefix_clean and suffix else "") + suffix).strip()
    if not desc:
        desc = "Phân tích chuyên sâu của đội ngũ NAC Consulting."

    # If the prefix text mentions "Đọc / Xem / Tìm hiểu", strip that
    # prelude from the desc since the button already says "Đọc Ngay →".
    desc = re.sub(r'^(Đọc thêm phân tích chuyên sâu|Xem hướng dẫn chi tiết|Tìm hiểu thêm|Đọc thêm|Xem thêm)\s*', '', desc, flags=re.IGNORECASE)
    desc = desc.strip()
    if not desc:
        desc = "Góc nhìn từ đội ngũ NAC sau hơn 5 năm xử lý hồ sơ cho gia đình Việt."

    kicker = pick_kicker(article_url, prefix)

    # Title might contain HTML entities — keep as-is, browsers will decode
    title_html = title

    return (
        f'<div class="article-cta"{extra_attrs}>\n'
        f'        <a class="article-cta-banner" href="{article_url}" target="_blank" '
        f"style=\"background-image:url('{PLACEHOLDER_COVER}')\">\n"
        f'          <span class="article-cta-kicker">{kicker}</span>\n'
        f'          <h3 class="article-cta-title">{title_html}</h3>\n'
        f'        </a>\n'
        f'        <div class="article-cta-body">\n'
        f'          <p class="article-cta-desc">{desc}</p>\n'
        f'          <a class="article-cta-btn" href="{btn_href}" target="_blank">{btn_label}</a>\n'
        f'        </div>\n'
        f'      </div>'
    )


def replace_old_css(text: str, new_css: str) -> tuple[str, bool]:
    """Replace any legacy .article-cta / .article-cta-text / .article-cta-icon
    / .article-cta-btn rule with the new banner-card CSS. Only fires if the
    banner CSS isn't already present."""
    if ".article-cta-banner" in text:
        return text, False

    # Remove old rules — match a series of .article-cta* rules. Be
    # conservative: only delete rules that exactly target article-cta
    # variants and are simple flat rules (no @media nesting).
    old_re = re.compile(
        r'\.article-cta\s*\{[^}]*\}\s*'
        r'(?:\.article-cta-icon\s*\{[^}]*\}\s*)?'
        r'(?:\.article-cta-text\s*\{[^}]*\}\s*)?'
        r'(?:\.article-cta-btn\s*\{[^}]*\}\s*)?'
        r'(?:\.article-cta-btn:hover\s*\{[^}]*\}\s*)?',
        re.DOTALL,
    )
    text_new = old_re.sub("", text, count=1)

    # Insert the new banner-card CSS just before </style>
    pos = text_new.find("</style>")
    if pos < 0:
        return text, False
    inject = (
        "\n\n/* ── ARTICLE CTA — Banner card (cover image + headline + CTA) ──\n"
        "   Migrated from text-only layout via migrate_article_cta_banner.py */\n"
        + new_css + "\n"
    )
    return text_new[:pos] + inject + text_new[pos:], True


def process_file(path: Path, css: str, dry_run: bool = False) -> dict:
    text = path.read_text(encoding="utf-8")
    original = text
    out = {"blocks_swapped": 0, "css_replaced": 0}

    text, ok = replace_old_css(text, css)
    if ok:
        out["css_replaced"] = 1

    new_text, count = OLD_BLOCK_RE.subn(transform_block, text)
    if count:
        text = new_text
        out["blocks_swapped"] = count

    if text == original or dry_run:
        return out
    path.write_text(text, encoding="utf-8")
    return out


def main() -> int:
    args = sys.argv[1:]
    dry_run = "--dry-run" in args
    args = [a for a in args if not a.startswith("--")]

    css = extract_banner_css()
    print(f"  banner-card CSS lifted from Turkey: {len(css)} chars\n")

    if args:
        aliases = [a.lower() for a in args]
        files = [
            p for p in sorted(BROCHURES_DIR.glob("*.html"))
            if p.name not in SKIP
            and any(p.name.lower().startswith(a) for a in aliases)
        ]
    else:
        files = [p for p in sorted(BROCHURES_DIR.glob("*.html")) if p.name not in SKIP]

    totals = {"blocks_swapped": 0, "css_replaced": 0}
    for f in files:
        c = process_file(f, css, dry_run=dry_run)
        any_change = any(c.values())
        marker = "[dry]" if dry_run else ("✓" if any_change else "·")
        print(
            f"  {marker} {f.name}: "
            f"blocks={c['blocks_swapped']}, css={c['css_replaced']}"
        )
        for k, v in c.items():
            totals[k] += v

    print(
        f"\nDone — blocks={totals['blocks_swapped']}, css={totals['css_replaced']} "
        f"({'dry-run' if dry_run else 'applied'})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
