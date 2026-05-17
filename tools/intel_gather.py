#!/usr/bin/env python3
"""Daily intel scraper for the 12 brochure countries.

Polls each country's configured sources (intel_sources.py) and extracts
signals related to investment migration: pricing thresholds, policy
dates, change-trigger keywords. Each run appends one JSON file per
country to .diagnostics/weekly-intel/<YYYY-MM-DD>/<alias>.json so the
weekly digest can aggregate the last 7 days.

Run:
    python tools/intel_gather.py                # all countries
    python tools/intel_gather.py turkey         # one country
    python tools/intel_gather.py --quiet        # less output

Defensive by design: network failures on a single source skip that
source, never the whole run. Empty results still write a file with
{"signals": []} so the digest job knows the run happened.
"""
from __future__ import annotations

import datetime as dt
import html as html_lib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.intel_sources import (  # noqa: E402
    ALL_ALIASES,
    COUNTRY_SOURCES,
    INDUSTRY_PRESS,
    REDDIT_SUBS,
)

OUT_DIR = ROOT / '.diagnostics' / 'weekly-intel'
UA = 'nac-intel-gatherer/1.0 (+https://nomadassetcollective.com)'
TIMEOUT = 15
MAX_BODY_BYTES = 800_000  # 800KB cap per fetch — guards against huge pages


# ── HTTP helpers ─────────────────────────────────────────────────────────


def http_get(url: str, *, accept: str = 'text/html,*/*') -> tuple[int, str]:
    """Return (status, body). Body is '' on non-200 or any error."""
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': accept})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            data = r.read(MAX_BODY_BYTES + 1)
            if len(data) > MAX_BODY_BYTES:
                data = data[:MAX_BODY_BYTES]
            return r.status, data.decode('utf-8', errors='replace')
    except urllib.error.HTTPError as e:
        return e.code, ''
    except Exception:
        return 0, ''


def strip_html(text: str) -> str:
    """Crude tag stripper — fine for keyword/regex matching."""
    text = re.sub(r'<script[^>]*>.*?</script>', ' ', text, flags=re.S | re.I)
    text = re.sub(r'<style[^>]*>.*?</style>', ' ', text, flags=re.S | re.I)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = html_lib.unescape(text)
    return re.sub(r'\s+', ' ', text).strip()


# ── Signal extraction ────────────────────────────────────────────────────


# Money: "$400,000", "$400K", "USD 400,000", "€350,000", "350,000 EUR"
MONEY_RE = re.compile(
    r'(?:'
    r'(?:US|USD|EUR|GBP|MYR|AED|NZD|THB)\s*\$?\s*[\d,]+(?:\.\d+)?\s*[KkMm]?'
    r'|\$\s*[\d,]+(?:\.\d+)?\s*[KkMm]?'
    r'|€\s*[\d,]+(?:\.\d+)?\s*[KkMm]?'
    r'|£\s*[\d,]+(?:\.\d+)?\s*[KkMm]?'
    r'|[\d,]+(?:\.\d+)?\s*(?:USD|EUR|GBP|MYR|AED|NZD|THB|baht)'
    r')'
)

# Years 2024–2030 and quarter markers
DATE_RE = re.compile(r'\b(?:20[2-3]\d|Q[1-4]\s*20[2-3]\d|Q[1-4]/?20[2-3]\d)\b')

# Change-trigger keywords. Case-insensitive. Each match contributes a "signal".
CHANGE_TRIGGERS = re.compile(
    r'(?i)\b('
    r'increase[ds]?|decrease[ds]?|raise[ds]?|raised\s+to|lower(?:ed)?\s+to|'
    r'suspend(?:ed)?|paus(?:ed|e)|abolish(?:ed)?|terminat(?:ed|e)|'
    r'new\s+(?:rule|threshold|minimum|requirement)|'
    r'effective\s+(?:from\s+|as\s+of\s+)?(?:20[2-3]\d|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)|'
    r'reform(?:ed)?|amend(?:ed|ment)|'
    r'(?:no\s+longer|will\s+(?:no\s+longer|cease)|'
    r'starting\s+(?:from\s+)?20[2-3]\d|'
    r'as\s+of\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+20[2-3]\d)'
    r')\b'
)


def excerpt_around(text: str, span: tuple[int, int], width: int = 140) -> str:
    """Pull a clean ~280-char excerpt centred on `span`."""
    a, b = span
    start = max(0, a - width)
    end = min(len(text), b + width)
    snip = text[start:end].strip()
    if start > 0:
        snip = '…' + snip
    if end < len(text):
        snip = snip + '…'
    return snip


def extract_signals(
    text: str,
    *,
    source: str,
    url: str,
    authority: int,
    keywords: list[str],
) -> list[dict]:
    """Pull money/date/trigger signals near country keyword mentions."""
    out: list[dict] = []
    low = text.lower()

    # Find every place a keyword appears, then look ±240 chars for signals.
    keyword_hits: list[int] = []
    for kw in keywords:
        kw_low = kw.lower()
        i = 0
        while True:
            j = low.find(kw_low, i)
            if j == -1:
                break
            keyword_hits.append(j)
            i = j + len(kw_low)

    if not keyword_hits:
        # Fall back to entire text (cheap match on small pages).
        keyword_hits = [0]

    seen_excerpts: set[str] = set()
    for hit in keyword_hits[:30]:  # cap per page
        a = max(0, hit - 240)
        b = min(len(text), hit + 240)
        window = text[a:b]
        for kind, pattern in (
            ('money', MONEY_RE),
            ('date', DATE_RE),
            ('trigger', CHANGE_TRIGGERS),
        ):
            for m in pattern.finditer(window):
                excerpt = excerpt_around(text, (a + m.start(), a + m.end()))
                key = (kind, excerpt[:80])
                if key in seen_excerpts:
                    continue
                seen_excerpts.add(key)
                out.append({
                    'kind': kind,
                    'matched': m.group(0).strip(),
                    'excerpt': excerpt,
                    'source': source,
                    'url': url,
                    'authority': authority,
                })
                if len(out) >= 40:  # cap per source
                    return out
    return out


# ── Reddit JSON API ──────────────────────────────────────────────────────


def reddit_search(sub: str, query: str, *, days: int = 1) -> list[dict]:
    """Query r/<sub>/search.json for `query`. Returns post dicts."""
    qs = urllib.parse.urlencode({
        'q': query,
        'restrict_sr': 'on',
        'sort': 'new',
        't': 'week',
        'limit': 25,
    })
    url = f'https://www.reddit.com/r/{sub}/search.json?{qs}'
    status, body = http_get(url, accept='application/json')
    if status != 200 or not body:
        return []
    try:
        data = json.loads(body)
    except Exception:
        return []
    cutoff = time.time() - days * 86400
    posts = []
    for child in data.get('data', {}).get('children', []):
        d = child.get('data', {})
        if d.get('created_utc', 0) < cutoff:
            continue
        posts.append({
            'title': d.get('title', ''),
            'selftext': d.get('selftext', '')[:1200],
            'url': 'https://www.reddit.com' + d.get('permalink', ''),
            'sub': sub,
            'score': d.get('score', 0),
            'num_comments': d.get('num_comments', 0),
            'ts': d.get('created_utc', 0),
        })
    return posts


def reddit_signals_for_country(alias: str, *, days: int) -> list[dict]:
    """Aggregate Reddit signals across REDDIT_SUBS and per-country terms."""
    terms = COUNTRY_SOURCES[alias].get('reddit_terms', [])
    if not terms:
        return []
    out: list[dict] = []
    for sub in REDDIT_SUBS:
        for term in terms:
            posts = reddit_search(sub, term, days=days)
            for p in posts:
                full = f"{p['title']}\n\n{p['selftext']}"
                sigs = extract_signals(
                    full,
                    source=f'r/{sub}',
                    url=p['url'],
                    authority=1,
                    keywords=terms,
                )
                # If no triggers but post still references the country, keep
                # the post itself as a low-confidence "mention" signal.
                if not sigs and any(t.lower() in full.lower() for t in terms):
                    out.append({
                        'kind': 'mention',
                        'matched': p['title'][:140],
                        'excerpt': full[:280],
                        'source': f'r/{sub}',
                        'url': p['url'],
                        'authority': 1,
                        'reddit_score': p['score'],
                    })
                else:
                    out.extend(sigs)
            # Be polite — small sleep between sub queries
            time.sleep(0.3)
    return out


# ── HTML / RSS sources ───────────────────────────────────────────────────


def html_signals_for_source(
    alias: str,
    source_name: str,
    url: str,
    authority: int,
) -> list[dict]:
    """Fetch + extract signals from one HTML/RSS page."""
    keywords = COUNTRY_SOURCES[alias].get('keywords', [])
    # Industry-press search pages get the country keyword interpolated
    if '{q}' in url:
        url = url.format(q=urllib.parse.quote_plus(keywords[0] if keywords else alias))
    status, body = http_get(url)
    if status != 200 or not body:
        return []
    text = strip_html(body)
    return extract_signals(
        text,
        source=source_name,
        url=url,
        authority=authority,
        keywords=keywords,
    )


def gather_country(alias: str, *, days: int, quiet: bool) -> dict:
    """Run all sources for one country. Returns a writeable record."""
    cfg = COUNTRY_SOURCES.get(alias)
    if not cfg:
        return {'alias': alias, 'error': 'unknown alias', 'signals': []}

    signals: list[dict] = []

    # 1. Official government / immigration agency pages
    for src_name, src_url, auth, _kind in cfg.get('official', []):
        if not quiet:
            print(f'    · official: {src_name}')
        signals.extend(html_signals_for_source(alias, src_name, src_url, auth))

    # 2. Industry agencies (Henley, Latitude, CS Global, etc.)
    for src_name, src_url, auth, _kind in cfg.get('agency', []):
        if not quiet:
            print(f'    · agency:   {src_name}')
        signals.extend(html_signals_for_source(alias, src_name, src_url, auth))

    # 3. Industry press searches (IMI Daily, IMC, etc.)
    for src_name, search_tpl, auth, _kind in INDUSTRY_PRESS:
        if not quiet:
            print(f'    · press:    {src_name}')
        signals.extend(html_signals_for_source(alias, src_name, search_tpl, auth))

    # 4. Reddit (cross-sub keyword search)
    if not quiet:
        print('    · reddit')
    signals.extend(reddit_signals_for_country(alias, days=days))

    return {
        'alias': alias,
        'gathered_at': dt.datetime.now(dt.timezone.utc).isoformat(),
        'days_window': days,
        'signal_count': len(signals),
        'signals': signals,
    }


# ── Main ─────────────────────────────────────────────────────────────────


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    quiet = '--quiet' in sys.argv
    days = 1  # daily window by default
    for a in sys.argv[1:]:
        if a.startswith('--days='):
            days = int(a.split('=', 1)[1])

    targets = args if args else ALL_ALIASES
    unknown = [t for t in targets if t not in COUNTRY_SOURCES]
    if unknown:
        sys.exit(f'❌ unknown aliases: {unknown}')

    today = dt.date.today().isoformat()
    day_dir = OUT_DIR / today
    day_dir.mkdir(parents=True, exist_ok=True)

    print(f'Intel sweep ({today}, window={days}d) → {day_dir.relative_to(ROOT)}')
    total_signals = 0

    for alias in targets:
        print(f'  {alias}')
        rec = gather_country(alias, days=days, quiet=quiet)
        out = day_dir / f'{alias}.json'
        out.write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding='utf-8')
        n = rec['signal_count']
        total_signals += n
        print(f'    → {n} signals → {out.relative_to(ROOT)}')

    print(f'\nDone. {total_signals} signals across {len(targets)} countries.')
    # Marker file so weekly-digest knows the last successful run
    (OUT_DIR / 'last-run.txt').write_text(today + '\n', encoding='utf-8')
    return 0


if __name__ == '__main__':
    sys.exit(main())
