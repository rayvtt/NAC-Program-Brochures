#!/usr/bin/env python3
"""Create / sync the [NAC - Program Brochures] Notion DB schema.

Reads SCHEMA + NOTION_NAMES from data/brochure_schema.py. Does two
things idempotently:

  1. RENAME the default title property to "alias" if it isn't already
     (Notion auto-creates the title as "Name").
  2. ADD any missing properties (per NOTION_NAMES display names).

Won't delete properties — Notion API doesn't support that. Stale columns
must be removed manually in the Notion UI.

Required env vars (set as GitHub Action secrets):
    NOTION_KEY

Run:
    python tools/setup_brochure_db.py
    python tools/setup_brochure_db.py --dry-run
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


def main():
    dry = '--dry-run' in sys.argv
    token = os.environ.get('NOTION_KEY')
    if not token:
        sys.exit('❌ NOTION_KEY env var missing.')

    print(f'GET database {NOTION_DB_ID}…')
    status, body = http('GET', f'{NOTION_BASE}/databases/{NOTION_DB_ID}', token=token)
    if status != 200:
        sys.exit(f'❌ HTTP {status} fetching DB: {body[:300]}')
    db = json.loads(body)
    existing = db.get('properties', {})  # name → property object
    print(f'  found {len(existing)} existing properties')

    # Build PATCH payload
    patch_props = {}

    # 1. Rename title property to "alias" if needed
    title_current_name = next((n for n, p in existing.items() if p.get('type') == 'title'), None)
    if title_current_name:
        if title_current_name != NOTION_NAMES['alias']:
            print(f'  rename title: "{title_current_name}" → "{NOTION_NAMES["alias"]}"')
            patch_props[title_current_name] = {'name': NOTION_NAMES['alias']}
    else:
        print('  ⚠ no title property found — Notion DB must have one (this is unusual)')

    # 2. Add missing non-title properties
    existing_names_after = set(existing.keys()) - ({title_current_name} if title_current_name else set())
    target_names = set(NOTION_NAMES.values()) - {NOTION_NAMES['alias']}   # alias handled via rename

    to_add = []
    for tech_key, type_config in SCHEMA.items():
        notion_name = NOTION_NAMES[tech_key]
        if 'title' in type_config:
            continue  # handled via rename above
        if notion_name in existing.keys():
            continue
        patch_props[notion_name] = type_config
        to_add.append(notion_name)

    if not patch_props:
        print('\n✓ Schema already up to date. Nothing to do.')
        return

    print(f'\nPATCH summary:')
    if title_current_name and title_current_name != NOTION_NAMES['alias']:
        print(f'  · rename title → "{NOTION_NAMES["alias"]}"')
    print(f'  · add {len(to_add)} new properties')
    for n in to_add[:8]:
        t = next(iter(patch_props[n]))
        print(f'      + {n:42s} ({t})')
    if len(to_add) > 8:
        print(f'      … and {len(to_add) - 8} more')

    if dry:
        print('\n--dry-run — not applying.')
        return

    print(f'\nPATCH /databases/{NOTION_DB_ID}…')
    payload = json.dumps({'properties': patch_props}, ensure_ascii=False)
    status, body = http(
        'PATCH', f'{NOTION_BASE}/databases/{NOTION_DB_ID}', token=token, body=payload,
    )
    if status == 200:
        result = json.loads(body)
        final = result.get('properties', {})
        added = sum(1 for n in to_add if n in final)
        print(f'✓ patched — {added}/{len(to_add)} new properties created.')
        missing = [n for n in to_add if n not in final]
        if missing:
            print(f'⚠ missing in response: {missing}')
    else:
        sys.exit(f'❌ HTTP {status}: {body[:600]}')


if __name__ == '__main__':
    main()
