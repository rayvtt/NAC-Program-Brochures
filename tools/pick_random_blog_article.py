#!/usr/bin/env python3
"""Pick a "random" published article from the NAC blog category pages.

Two categories are scanned:
  - Góc Nhìn NAC : https://blog.nomadassetcollective.com/category/goc-nhin-nac/
  - Phân Tích    : https://blog.nomadassetcollective.com/category/phan-tich/

Used as the fallback for `article-cta-banner` cards that ship pointing at
the bare blog homepage (e.g. when Notion has no specific article URL for
a section yet — Malta §03 etc.). Instead of the visitor seeing a generic
"Đọc thêm trên blog" card that lands on the homepage, we substitute a
real article PDP with its own og:image + og:title.

Randomisation is **deterministic per (alias, fortnight)** so:
  - the same brochure shows the same pick across re-runs within a 2-week window
    (avoids flicker every 10 min when the cron rebuilds the HTML)
  - the pick rotates fortnightly so visitors who come back see fresh content
  - different brochures naturally show different articles in the same window

Run:
    python tools/pick_random_blog_article.py                # random article
    python tools/pick_random_blog_article.py --alias malta  # deterministic per Malta+fortnight
    python tools/pick_random_blog_article.py --json
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import html as html_lib
import json
import re
import sys
import urllib.request
from typing import Optional

CATEGORY_URLS = [
    'https://blog.nomadassetcollective.com/category/goc-nhin-nac/',
    'https://blog.nomadassetcollective.com/category/phan-tich/',
]

UA = 'NAC-Brochure-Build/1.0 (+nomadassetcollective.com)'


def fetch(url: str, timeout: int = 15) -> str:
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode('utf-8', errors='replace')


# WordPress category index links to each post twice — once on the thumbnail,
# once on the title. We dedupe by URL. Skip pagination + category links by
# requiring exactly one path segment after the host.
POST_URL_RE = re.compile(
    r'href="(https://blog\.nomadassetcollective\.com/[^/"#?]+/)"'
)


def list_articles_in_category(category_url: str) -> list[str]:
    try:
        html = fetch(category_url)
    except Exception:
        return []
    seen = []
    seen_set = set()
    for m in POST_URL_RE.finditer(html):
        u = m.group(1)
        # Skip the category root itself, /author/, /tag/, /page/, etc.
        if '/category/' in u or '/author/' in u or '/tag/' in u or '/page/' in u:
            continue
        if u in seen_set:
            continue
        seen.append(u)
        seen_set.add(u)
    return seen


# Pull og:title + og:image from the article PDP. These power the card's
# h3.article-cta-title and background-image respectively.
META_RE = re.compile(
    r'<meta[^>]+property=["\']og:([a-z:]+)["\'][^>]+content=["\']([^"\']+)["\']',
    re.IGNORECASE,
)


# WordPress og:title tends to come back as "Post title - Site Name"; strip
# any trailing " - NAC Times" / " | NAC Times" so it reads cleanly in a card.
SITE_SUFFIX_RE = re.compile(r'\s*[-|–—]\s*NAC\s*Times\s*$', re.IGNORECASE)


def fetch_article_meta(url: str) -> dict:
    try:
        h = fetch(url)
    except Exception:
        return {}
    meta = {}
    for m in META_RE.finditer(h):
        meta[m.group(1)] = html_lib.unescape(m.group(2))
    title = SITE_SUFFIX_RE.sub('', meta.get('title', '')).strip()
    return {
        'url': url,
        'title': title,
        'image': meta.get('image', '').strip(),
    }


def _fortnight_index(today: Optional[_dt.date] = None) -> int:
    """ISO year × 26 + ISO week ÷ 2 — same fortnight scheme used by
    apply_listings.py for listing-card rotation."""
    today = today or _dt.date.today()
    iso = today.isocalendar()
    return iso[0] * 26 + iso[1] // 2


def _pick_index(items: list, alias: Optional[str], today: Optional[_dt.date] = None) -> int:
    """Deterministic pick: hash(alias + fortnight) % len(items). If no alias
    is supplied, use plain fortnight so all callers without alias get the
    same article (cheap stability)."""
    seed = f'{alias or ""}:{_fortnight_index(today)}'
    h = hashlib.sha256(seed.encode('utf-8')).digest()
    n = int.from_bytes(h[:4], 'big')
    return n % len(items)


def pick(alias: Optional[str] = None) -> Optional[dict]:
    """Return one article {url, title, image} or None on total failure."""
    urls: list[str] = []
    for cat in CATEGORY_URLS:
        urls.extend(list_articles_in_category(cat))
    # De-dupe across categories (some posts appear in both)
    seen, dedup = set(), []
    for u in urls:
        if u not in seen:
            dedup.append(u)
            seen.add(u)
    if not dedup:
        return None

    # Try the deterministic pick first, then walk the list if its og: data is
    # incomplete — guarantees we don't return {url, "", ""} when a better
    # candidate is one slot away.
    start = _pick_index(dedup, alias)
    for offset in range(len(dedup)):
        candidate = dedup[(start + offset) % len(dedup)]
        meta = fetch_article_meta(candidate)
        if meta.get('title') and meta.get('image'):
            return meta
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--alias', help='Brochure alias for deterministic seeding')
    ap.add_argument('--json', action='store_true', help='Emit JSON')
    args = ap.parse_args()

    chosen = pick(args.alias)
    if not chosen:
        print('No article found in either category.', file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(chosen, ensure_ascii=False, indent=2))
    else:
        print(f"url:   {chosen['url']}")
        print(f"title: {chosen['title']}")
        print(f"image: {chosen['image']}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
