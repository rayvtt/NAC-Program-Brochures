#!/usr/bin/env python3
"""POST a brochure JSON payload as a new row in the [NAC - Program Brochures] Notion DB.

Reads data/<alias>_payload.json (e.g. data/turkey_payload.json), maps
each field to its Notion property representation per data/brochure_schema.py,
and POSTs via the Notion API.

Idempotent: if a row with that `alias` already exists, the script
UPDATES it (PATCH /pages/{id}) rather than creating a duplicate.

Run:
    python tools/push_brochure.py turkey            # apply
    python tools/push_brochure.py turkey --dry-run  # preview body only
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

# Notion's 2000-char limit per rich_text block.
RICH_TEXT_LIMIT = 2000


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


def rich_text_chunks(s):
    """Split long strings into 2000-char rich_text blocks (Notion limit)."""
    if not s:
        return [{'text': {'content': ''}}]
    out, i = [], 0
    while i < len(s):
        out.append({'text': {'content': s[i: i + RICH_TEXT_LIMIT]}})
        i += RICH_TEXT_LIMIT
    return out


def field_to_notion(name, value, type_config):
    """Wrap a Python value as the Notion API property payload."""
    kind = next(iter(type_config))
    if kind == 'title':
        return {'title': [{'text': {'content': str(value or '')}}]}
    if kind == 'rich_text':
        return {'rich_text': rich_text_chunks(str(value or ''))}
    if kind == 'number':
        try:
            return {'number': float(value) if value not in (None, '') else None}
        except (TypeError, ValueError):
            return {'number': None}
    if kind == 'select':
        v = (value or '').strip()
        return {'select': {'name': v}} if v else {'select': None}
    if kind == 'status':
        v = (value or '').strip()
        return {'status': {'name': v}} if v else {'status': None}
    if kind == 'url':
        v = (value or '').strip()
        return {'url': v if v else None}
    return {'rich_text': rich_text_chunks(str(value or ''))}  # fallback


def find_existing_row(token, alias):
    """Return page_id of existing row with this alias, or None."""
    query = json.dumps({
        'filter': {'property': NOTION_NAMES['alias'], 'title': {'equals': alias}},
        'page_size': 1,
    })
    status, body = http(
        'POST', f'{NOTION_BASE}/databases/{NOTION_DB_ID}/query', token=token, body=query,
    )
    if status != 200:
        print(f'  ⚠ HTTP {status} querying DB: {body[:200]}', file=sys.stderr)
        return None
    results = json.loads(body).get('results', [])
    return results[0]['id'] if results else None


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    flags = [a for a in sys.argv[1:] if a.startswith('--')]
    dry = '--dry-run' in flags
    if not args:
        sys.exit('usage: push_brochure.py <alias> [--dry-run]')
    alias = args[0]

    payload_path = ROOT / 'data' / f'{alias}_payload.json'
    if not payload_path.exists():
        sys.exit(f'❌ {payload_path} not found. Run extract_{alias}.py first.')
    payload = json.loads(payload_path.read_text(encoding='utf-8'))

    properties = {}
    for tech_key, type_config in SCHEMA.items():
        if tech_key not in payload:
            continue
        notion_name = NOTION_NAMES[tech_key]
        properties[notion_name] = field_to_notion(tech_key, payload[tech_key], type_config)

    token = os.environ.get('NOTION_KEY')
    if not token and not dry:
        sys.exit('❌ NOTION_KEY env var missing.')

    if dry:
        body = {'parent': {'database_id': NOTION_DB_ID}, 'properties': properties}
        print(json.dumps(body, ensure_ascii=False, indent=2)[:2000])
        print('\n--dry-run — not pushing.')
        return

    existing_id = find_existing_row(token, alias)

    if existing_id:
        print(f'Found existing row for "{alias}" ({existing_id}) — updating…')
        body = json.dumps({'properties': properties}, ensure_ascii=False)
        status, resp = http('PATCH', f'{NOTION_BASE}/pages/{existing_id}', token=token, body=body)
    else:
        print(f'No existing row for "{alias}" — creating…')
        body = json.dumps({'parent': {'database_id': NOTION_DB_ID}, 'properties': properties}, ensure_ascii=False)
        status, resp = http('POST', f'{NOTION_BASE}/pages', token=token, body=body)

    if status == 200:
        page = json.loads(resp)
        print(f'✓ row id: {page.get("id")}')
        print(f'  url:    {page.get("url")}')
    else:
        sys.exit(f'❌ HTTP {status}: {resp[:600]}')


if __name__ == '__main__':
    main()
