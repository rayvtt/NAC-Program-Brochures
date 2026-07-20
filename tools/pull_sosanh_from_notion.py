#!/usr/bin/env python3
"""Pull all 14 country rows from the 🔀 NAC - So Sánh Data Notion DB →
data/sosanh_payload.json (the semantic shape NAC-SO-SANH.html's DB_STATIC
blob is generated from — see tools/patch_sosanh_snap.py).

Required env: NOTION_TOKEN (falls back to NOTION_KEY if unset — this repo
uses both names across different scripts; see CLAUDE.md § So Sánh Notion
sync for why).

Run:
    python tools/pull_sosanh_from_notion.py
    python tools/pull_sosanh_from_notion.py --dry-run   # print, don't write
"""
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from data.sosanh_schema import (  # noqa: E402
    IDENTITY_NAMES, NOTION_DB_ID, NUM_FIELDS, TEXT_FIELDS,
)

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
        return None
    t = prop['type']
    if t == 'title':
        return ''.join(rt['plain_text'] for rt in prop['title']).strip()
    if t == 'rich_text':
        return ''.join(rt['plain_text'] for rt in prop['rich_text']).strip()
    if t == 'number':
        return prop.get('number')
    if t == 'checkbox':
        return bool(prop.get('checkbox'))
    if t == 'multi_select':
        return [o['name'] for o in prop.get('multi_select', [])]
    if t == 'select':
        sel = prop.get('select')
        return sel['name'] if sel else None
    return None


def query_all_rows(token):
    """Page through the DB query endpoint. Notion paginates at 100/page —
    14 rows today, so this always finishes in one page, but written to
    scale without a code change if the country list grows."""
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


def build_country(props):
    out = {}
    for key, name in IDENTITY_NAMES.items():
        out[key] = decode_property(props.get(name))
    out['liveInPicker'] = bool(out.get('liveInPicker'))
    out['sortOrder'] = out.get('sortOrder') if out.get('sortOrder') is not None else 999
    out['bloc'] = out.get('bloc') or []

    for key, prefix in TEXT_FIELDS.items():
        vi = decode_property(props.get(f'{prefix} (VI)')) or ''
        en = decode_property(props.get(f'{prefix} (EN)')) or ''
        if vi or en:
            out[key] = {'vi': vi, 'en': en}

    for key, name in NUM_FIELDS.items():
        v = decode_property(props.get(name))
        if v is not None:
            out[key] = v

    return out


def main():
    dry = '--dry-run' in sys.argv
    token = os.environ.get('NOTION_TOKEN') or os.environ.get('NOTION_KEY')
    if not token:
        sys.exit('❌ NOTION_TOKEN (or NOTION_KEY) env var missing.')

    print(f'Querying {NOTION_DB_ID}…')
    rows = query_all_rows(token)
    print(f'  fetched {len(rows)} rows')

    countries = {}
    seen_codes = {}
    for row in rows:
        props = row.get('properties', {})
        country = build_country(props)
        code = country.get('code')
        if not code:
            print(f'  ⚠ row {row["id"]}: empty code, skipping')
            continue
        if code in seen_codes:
            sys.exit(
                f'❌ duplicate code "{code}": {seen_codes[code]} and '
                f'{country.get("vi")!r} both claim it — codes must be unique '
                f'(findCountry() in NAC-SO-SANH.html looks up by exact code match)'
            )
        seen_codes[code] = country.get('vi')
        countries[code] = country

    print(f'  {len(countries)} countries, codes: {sorted(countries.keys())}')

    payload = {'countries': countries}
    new_json = json.dumps(payload, ensure_ascii=False, indent=1)
    if chr(92) in new_json:
        sys.exit('❌ literal backslash in payload — would break WP wp_unslash on the next HTML push')

    out_path = ROOT / 'data' / 'sosanh_payload.json'
    if out_path.exists() and out_path.read_text(encoding='utf-8') == new_json:
        print('  · unchanged')
    else:
        print('  ⤴ changed' if out_path.exists() else '  + new')
        if not dry:
            out_path.write_text(new_json, encoding='utf-8')
            print(f'  wrote {out_path}')

    if dry:
        print('--dry-run — no files written.')


if __name__ == '__main__':
    main()
