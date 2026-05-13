#!/usr/bin/env python3
"""Pull all brochure rows from the Notion DB → data/<alias>_payload.json.

Required env: NOTION_KEY (the Notion integration token).

Run:
    python tools/pull_from_notion.py
    python tools/pull_from_notion.py --dry-run    # show diff, don't write

In CI: runs before build_brochures.py so each deploy reflects the
current Notion state.
"""
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from data.brochure_schema import SCHEMA, NOTION_NAMES, NOTION_DB_ID  # noqa: E402

NOTION_VERSION = '2022-06-28'
NOTION_BASE = 'https://api.notion.com/v1'


def http(method, url, *, token, body=None):
    req = urllib.request.Request(url, method=method)
    req.add_header('Authorization', f'Bearer {token}')
    req.add_header('Notion-Version', NOTION_VERSION)
    req.add_header('Content-Type', 'application/json')
    data = body.encode('utf-8') if isinstance(body, str) else body
    try:
        with urllib.request.urlopen(req, data=data, timeout=30) as r:
            return r.status, r.read().decode('utf-8', errors='replace')
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8', errors='replace')


def decode_property(prop):
    if not prop:
        return ''
    t = prop['type']
    if t == 'title':
        return ''.join(rt['plain_text'] for rt in prop['title'])
    if t == 'rich_text':
        return ''.join(rt['plain_text'] for rt in prop['rich_text'])
    if t == 'number':
        return prop.get('number') if prop.get('number') is not None else 0
    if t == 'select':
        sel = prop.get('select')
        return sel['name'] if sel else ''
    if t == 'status':
        st = prop.get('status')
        return st['name'] if st else ''
    if t == 'url':
        return prop.get('url') or ''
    return ''


def alias_key_from_title(title):
    """'🇹🇷 turkey' → 'turkey'. Falls back to the whole title if no space.
    Always lowercased so Notion auto-capitalising the title (or a manual
    edit with different case) doesn't desync from data/<alias>_payload.json."""
    parts = title.split(' ', 1)
    raw = parts[1] if len(parts) == 2 else title
    return raw.strip().lower()


def query_all_rows(token):
    """Page through the DB query endpoint. Notion paginates at 100/page."""
    rows = []
    next_cursor = None
    while True:
        body = {'page_size': 100}
        if next_cursor:
            body['start_cursor'] = next_cursor
        status, resp = http(
            'POST',
            f'{NOTION_BASE}/databases/{NOTION_DB_ID}/query',
            token=token,
            body=json.dumps(body),
        )
        if status != 200:
            sys.exit(f'❌ HTTP {status} querying DB: {resp[:400]}')
        data = json.loads(resp)
        rows.extend(data.get('results', []))
        if not data.get('has_more'):
            break
        next_cursor = data.get('next_cursor')
    return rows


def main():
    dry = '--dry-run' in sys.argv
    token = os.environ.get('NOTION_KEY')
    if not token:
        sys.exit('❌ NOTION_KEY env var missing.')

    print(f'Querying {NOTION_DB_ID}…')
    rows = query_all_rows(token)
    print(f'  fetched {len(rows)} rows')

    out_dir = ROOT / 'data'
    written = updated = unchanged = 0

    for row in rows:
        props = row.get('properties', {})

        payload = {}
        for tech_key in SCHEMA.keys():
            notion_name = NOTION_NAMES[tech_key]
            payload[tech_key] = decode_property(props.get(notion_name))

        title = payload.get('alias', '').strip()
        alias_key = alias_key_from_title(title)
        if not alias_key:
            print(f'  ⚠ row {row["id"]}: empty alias title, skipping')
            continue

        out_path = out_dir / f'{alias_key}_payload.json'
        new_json = json.dumps(payload, ensure_ascii=False, indent=2)

        # Debug: surface a sentinel field for diagnosing pipeline gaps
        badge = payload.get('hero_badge_vi', '')
        badge_preview = badge[:80] + ('…' if len(badge) > 80 else '')
        print(f'    hero_badge_vi: {badge_preview!r}')

        if out_path.exists():
            old_json = out_path.read_text(encoding='utf-8')
            if old_json == new_json:
                print(f'  · {alias_key:12s} (unchanged)')
                unchanged += 1
                continue
            print(f'  ⤴ {alias_key:12s} (updated)')
            updated += 1
        else:
            print(f'  + {alias_key:12s} (new)')

        if not dry:
            out_path.write_text(new_json, encoding='utf-8')
            written += 1

    print(f'\nSummary: {written} written, {unchanged} unchanged, {updated} updated (existing).')
    if dry:
        print('--dry-run — no files written.')


if __name__ == '__main__':
    main()
