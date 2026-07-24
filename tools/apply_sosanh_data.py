#!/usr/bin/env python3
"""Apply an in-page DATA edit to the So Sánh tool AND write it back to Notion.

Driven by .github/workflows/apply-sosanh-data.yml, which the in-page editor
(?edit=1 on the live page) dispatches with input `changes`:

    {"gr": {"vat": {"vi": "24%", "en": "24%"}, "gdp": 2.4}, "mt": {...}}

Sibling of tools/apply_sosanh_copy.py, but for a fundamentally different
kind of edit:

  apply_sosanh_copy.py  →  the CHROME (var I18N): hero, section titles, row
                           labels. Authored here, HTML is the source of truth.
  apply_sosanh_data.py  →  the COUNTRY DATA (var DB_STATIC): every value in
                           the comparison columns. **Notion is the source of
                           truth** — data/sosanh_payload.json is regenerated
                           from it on every fortnightly sync.

That difference is the whole reason this script exists. Patching only the
HTML would look right for a fortnight and then get silently reverted by the
next `pull_sosanh_from_notion.py` run. So the write order here is:

    1. Notion  (the source of truth — must succeed, or nothing else happens)
    2. data/sosanh_payload.json  (keeps the committed snapshot in step)
    3. var DB_STATIC in the HTML (so the edit is live in ~2 min instead of
       waiting for the 1st/15th cron)

If step 1 fails the script exits non-zero WITHOUT touching the repo, so the
page never disagrees with Notion. Steps 2-3 are the same transformation the
fortnightly pipeline performs, just applied to one field instead of all.

Field names are validated against data/sosanh_schema.py — the same single
source of truth the pull/patch tools use — so a typo'd or injected key is
rejected rather than silently creating a junk Notion property.
"""
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'data'))

from sosanh_schema import (  # noqa: E402
    NOTION_DB_ID,
    TEXT_FIELDS,
    NUM_FIELDS,
)

PAYLOAD_PATH = ROOT / 'data' / 'sosanh_payload.json'
LOG = ROOT / 'SOSANH-SYNC-LOG.md'
NOTION_VERSION = '2022-06-28'
NOTION_BASE = 'https://api.notion.com/v1'

CODE_RE = re.compile(r'^[a-z]{2}$')


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
    except urllib.error.URLError as e:
        return 0, str(e)


def code_to_page_id(token):
    """code → Notion page id. The payload deliberately does not store page
    ids (they would go stale on a row re-create), so resolve by querying the
    DB, exactly as the pull tool does."""
    out, cursor = {}, None
    while True:
        body = {'page_size': 100}
        if cursor:
            body['start_cursor'] = cursor
        status, resp = http(
            'POST', f'{NOTION_BASE}/databases/{NOTION_DB_ID}/query',
            token=token, body=json.dumps(body),
        )
        if status != 200:
            sys.exit(f'❌ HTTP {status} querying Notion DB: {resp[:400]}')
        data = json.loads(resp)
        for row in data.get('results', []):
            prop = (row.get('properties') or {}).get('code') or {}
            parts = prop.get('rich_text') or prop.get('title') or []
            code = ''.join(p.get('plain_text', '') for p in parts).strip().lower()
            if code:
                out[code] = row['id']
        if not data.get('has_more'):
            break
        cursor = data.get('next_cursor')
    return out


def rich_text_prop(value):
    return {'rich_text': [{'type': 'text', 'text': {'content': value}}]} if value else {'rich_text': []}


def build_props(field, value):
    """One editable field → the Notion property patch for it. Bilingual text
    fields patch ONLY the languages present in the payload, so editing the VI
    column never blanks the EN one."""
    props = {}
    if field in TEXT_FIELDS:
        prefix = TEXT_FIELDS[field]
        if not isinstance(value, dict):
            raise ValueError(f'{field}: text field needs {{vi,en}}, got {type(value).__name__}')
        for lang, suffix in (('vi', 'VI'), ('en', 'EN')):
            if lang in value:
                if not isinstance(value[lang], str):
                    raise ValueError(f'{field}.{lang}: expected a string')
                props[f'{prefix} ({suffix})'] = rich_text_prop(value[lang])
        return props
    if field in NUM_FIELDS:
        if value is None or value == '':
            props[NUM_FIELDS[field]] = {'number': None}
            return props
        try:
            props[NUM_FIELDS[field]] = {'number': float(value)}
        except (TypeError, ValueError):
            raise ValueError(f'{field}: expected a number, got {value!r}')
        return props
    raise ValueError(f'{field}: not an editable field (not in sosanh_schema)')


def main():
    raw = os.environ.get('CHANGES', '').strip()
    if not raw:
        sys.exit('❌ CHANGES is empty')
    try:
        changes = json.loads(raw)
    except json.JSONDecodeError as e:
        sys.exit(f'❌ CHANGES is not valid JSON: {e}')
    if not isinstance(changes, dict) or not changes:
        sys.exit('❌ CHANGES must be a non-empty object keyed by country code')

    token = os.environ.get('NOTION_KEY') or os.environ.get('NOTION_TOKEN')
    if not token:
        sys.exit('❌ NOTION_KEY is required — Notion is the source of truth for this data')

    # ── validate everything BEFORE writing anything ────────────────────
    planned = []
    for code, fields in changes.items():
        code = str(code).strip().lower()
        if not CODE_RE.match(code):
            sys.exit(f'❌ {code!r} is not a 2-letter country code')
        if not isinstance(fields, dict) or not fields:
            sys.exit(f'❌ {code}: expected a non-empty object of fields')
        for field, value in fields.items():
            try:
                planned.append((code, field, value, build_props(field, value)))
            except ValueError as e:
                sys.exit(f'❌ {e}')

    ids = code_to_page_id(token)
    missing = sorted({c for c, _, _, _ in planned} - set(ids))
    if missing:
        sys.exit(f'❌ no Notion row for country code(s): {", ".join(missing)}')

    # ── 1. Notion first — the source of truth ──────────────────────────
    applied = []
    for code, field, value, props in planned:
        status, resp = http(
            'PATCH', f'{NOTION_BASE}/pages/{ids[code]}',
            token=token, body=json.dumps({'properties': props}),
        )
        if status != 200:
            sys.exit(f'❌ HTTP {status} patching {code}.{field} in Notion: {resp[:400]}')
        applied.append((code, field, value))
        print(f'✓ Notion {code}.{field}')

    # ── 2. the committed payload snapshot ──────────────────────────────
    payload = json.loads(PAYLOAD_PATH.read_text(encoding='utf-8'))
    today = datetime.now(timezone.utc).strftime('%d/%m/%Y')
    for code, field, value in applied:
        country = payload.get('countries', {}).get(code)
        if country is None:
            print(f'⚠ {code} not in payload — skipping local snapshot for it')
            continue
        if field in TEXT_FIELDS:
            cur = country.get(field)
            cur = dict(cur) if isinstance(cur, dict) else {}
            cur.update({k: v for k, v in value.items() if k in ('vi', 'en')})
            country[field] = cur
        else:
            country[field] = None if value in (None, '') else float(value)
        # keep the per-field freshness ledger honest — this field changed today
        country.setdefault('_updated', {})[field] = today
    PAYLOAD_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'✓ payload updated ({len(applied)} field(s))')

    # ── 3. re-patch var DB_STATIC so the page is live now, not on the 15th
    r = subprocess.run([sys.executable, str(ROOT / 'tools' / 'patch_sosanh_snap.py')],
                       capture_output=True, text=True)
    sys.stdout.write(r.stdout)
    if r.returncode != 0:
        sys.stderr.write(r.stderr)
        sys.exit('❌ patch_sosanh_snap.py failed — HTML not updated')

    lines = [f'- `{c}` · **{f}** → ' +
             (', '.join(f'{k}: {v!r}' for k, v in val.items()) if isinstance(val, dict) else repr(val))
             for c, f, val in applied]
    stamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    entry = f'\n## {stamp} — in-page data edit (?edit=1)\n\n' + '\n'.join(lines) + '\n'
    prev = LOG.read_text(encoding='utf-8') if LOG.exists() else '# So Sánh sync log\n'
    LOG.write_text(prev.rstrip() + '\n' + entry, encoding='utf-8')
    print(f'✓ logged {len(applied)} change(s) to {LOG.name}')


if __name__ == '__main__':
    main()
