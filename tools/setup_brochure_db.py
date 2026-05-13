#!/usr/bin/env python3
"""Create / sync the [NAC - Program Brochures] Notion DB schema.

Reads SCHEMA from data/brochure_schema.py, GETs the DB's current shape,
PATCHes to add any missing properties. Idempotent: re-running is safe
(properties that already match are left alone).

Notion API will NOT:
  - delete properties (you must do that manually in Notion UI)
  - rename properties (must delete + add new)
  - change a property's TYPE in-place (must delete + recreate)

But it WILL:
  - add new properties
  - extend select options
  - update existing rich_text / number / url / select stubs

Required env vars (set as GitHub Action secrets):
    NOTION_KEY              the Notion integration token (Bearer)

Run:
    python tools/setup_brochure_db.py            # show diff + apply
    python tools/setup_brochure_db.py --dry-run  # show diff only
"""
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from data.brochure_schema import SCHEMA, NOTION_DB_ID  # noqa: E402

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


def main():
    dry = '--dry-run' in sys.argv

    token = os.environ.get('NOTION_KEY')
    if not token:
        sys.exit('❌ NOTION_KEY env var missing. Set it as a GitHub secret (or export locally).')

    print(f'GET database {NOTION_DB_ID}…')
    status, body = http('GET', f'{NOTION_BASE}/databases/{NOTION_DB_ID}', token=token)
    if status != 200:
        sys.exit(f'❌ HTTP {status} fetching DB: {body[:300]}')
    db = json.loads(body)
    existing = db.get('properties', {})
    print(f'  found {len(existing)} existing properties')

    to_add = {}
    title_prop_name = None
    for name, prop in existing.items():
        if prop.get('type') == 'title':
            title_prop_name = name

    for name, type_config in SCHEMA.items():
        if name == 'alias' and title_prop_name and title_prop_name != 'alias':
            # Notion's default title property is named "Name" until renamed.
            # Rename via the rename-key trick: we'll add `alias` as a new
            # field separately, OR rely on user to rename "Name" → "alias".
            # We'll skip auto-renaming and warn instead.
            print(f'  ⚠ existing title property is named "{title_prop_name}" — '
                  f'rename it to "alias" in Notion UI for cleanest mapping.')
            continue
        if name in existing:
            continue
        # PATCH cannot add a title property — DB always has exactly one
        if 'title' in type_config:
            print(f'  · {name}: title (must exist in DB; skipping)')
            continue
        to_add[name] = type_config

    if not to_add:
        print('\n✓ All schema properties already present. Nothing to do.')
        return

    print(f'\nWill add {len(to_add)} new properties:')
    for name in to_add:
        t = next(iter(to_add[name]))
        print(f'  + {name:36s} ({t})')

    if dry:
        print('\n--dry-run — not applying.')
        return

    print(f'\nPATCH /databases/{NOTION_DB_ID}…')
    payload = json.dumps({'properties': to_add}, ensure_ascii=False)
    status, body = http(
        'PATCH', f'{NOTION_BASE}/databases/{NOTION_DB_ID}', token=token, body=payload,
    )
    if status == 200:
        result = json.loads(body)
        final = result.get('properties', {})
        added = sum(1 for n in to_add if n in final)
        print(f'✓ patched — {added}/{len(to_add)} properties added.')
        missing = [n for n in to_add if n not in final]
        if missing:
            print(f'⚠ Notion accepted PATCH but these props missing in response: {missing}')
    else:
        sys.exit(f'❌ HTTP {status} patching DB: {body[:500]}')


if __name__ == '__main__':
    main()
