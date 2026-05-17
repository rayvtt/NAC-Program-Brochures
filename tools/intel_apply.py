#!/usr/bin/env python3
"""Apply checked checkboxes from the weekly intel issue to Notion + payload files.

Triggered by `.github/workflows/intel-apply.yml` on issue edit. Reads the
issue body (passed in via --body-file=<path>), finds every `- [x]` line
followed by `<!-- intel:... -->`, mutates the corresponding
`data/<alias>_payload.json`, and PATCHes the matching Notion DB row.

The 10-min `pull-notion` workflow then propagates the change to the
brochure HTML and WordPress.

Trailer grammar:
    <!-- intel:alias=<alias>;field=<root>;jsonpath=<path>;new=<value>;kind=money -->
    <!-- intel:alias=<alias>;action=force_review -->

For `kind=money`, the script:
  - parses the existing JSON in the targeted field,
  - replaces the matched amount string with `new`,
  - writes the payload back, and
  - PATCHes the Notion DB row's rich_text property.

`action=force_review` is a no-op for Notion writes but still logged for
the apply summary so the audit trail shows it was acknowledged.

Run:
    python tools/intel_apply.py --body-file=/tmp/issue.md           # apply
    python tools/intel_apply.py --body-file=/tmp/issue.md --dry-run # preview
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from data.brochure_schema import NOTION_DB_ID, NOTION_NAMES  # noqa: E402
from tools.intel_sources import COUNTRY_SOURCES  # noqa: E402

DATA_DIR = ROOT / 'data'
NOTION_VERSION = '2022-06-28'
NOTION_BASE = 'https://api.notion.com/v1'


# ── Trailer parsing ──────────────────────────────────────────────────────


# Checked line followed by an HTML-comment trailer on the next line(s)
CHECKBOX_RE = re.compile(
    r'^- \[x\][^\n]*(?:\n[^\n]*)*?\n?\s*<!--\s*intel:([^>]+?)\s*-->',
    re.MULTILINE,
)


def parse_trailer(payload: str) -> dict:
    """`alias=turkey;field=hero_stats;jsonpath=0.num;new=$500K;kind=money`
    → {'alias':'turkey','field':'hero_stats','jsonpath':'0.num','new':'$500K','kind':'money'}
    """
    out = {}
    for chunk in payload.split(';'):
        chunk = chunk.strip()
        if '=' not in chunk:
            continue
        k, v = chunk.split('=', 1)
        out[k.strip()] = v.strip()
    return out


def find_checked(body: str) -> list[dict]:
    """Return every `[x]` checkbox's parsed trailer, in document order."""
    return [parse_trailer(m.group(1)) for m in CHECKBOX_RE.finditer(body)]


# ── Payload mutation ─────────────────────────────────────────────────────


def navigate(obj, path: str):
    """'0.num' → obj[0]['num']. Returns (parent, key) for assignment."""
    parts = re.findall(r'\d+|[A-Za-z_][A-Za-z0-9_]*', path)
    if not parts:
        return None, None
    parent = obj
    for p in parts[:-1]:
        if p.isdigit():
            parent = parent[int(p)]
        else:
            parent = parent[p]
    last = parts[-1]
    return parent, int(last) if last.isdigit() else last


def apply_money_change(payload: dict, field: str, json_path: str, new_value: str) -> bool:
    """Update a money string inside a JSON-rich-text field. Returns True if changed."""
    raw = payload.get(field)
    if raw is None:
        return False
    try:
        arr = json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        return False
    parent, key = navigate(arr, json_path)
    if parent is None or key is None:
        return False
    try:
        before = parent[key]
    except (KeyError, IndexError, TypeError):
        return False
    if before == new_value:
        return False
    parent[key] = new_value
    payload[field] = json.dumps(arr, ensure_ascii=False)
    return True


# ── Notion API ───────────────────────────────────────────────────────────


def notion_http(method: str, path: str, *, token: str, body: dict | None = None):
    req = urllib.request.Request(NOTION_BASE + path, method=method)
    req.add_header('Authorization', f'Bearer {token}')
    req.add_header('Notion-Version', NOTION_VERSION)
    req.add_header('Content-Type', 'application/json')
    data = json.dumps(body).encode('utf-8') if body is not None else None
    try:
        with urllib.request.urlopen(req, data=data, timeout=20) as r:
            return r.status, json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode('utf-8') or '{}')


def find_notion_row(alias: str, token: str) -> str | None:
    """Return the Notion page_id whose alias title matches `<flag> <alias>`."""
    status, data = notion_http(
        'POST',
        f'/databases/{NOTION_DB_ID}/query',
        token=token,
        body={'page_size': 100},
    )
    if status != 200:
        return None
    for row in data.get('results', []):
        title_prop = row.get('properties', {}).get('alias', {})
        title_rt = title_prop.get('title', [])
        title = ''.join(rt.get('plain_text', '') for rt in title_rt)
        # Title looks like '🇹🇷 turkey' — alias is the last whitespace-separated token
        parts = title.strip().split()
        if parts and parts[-1].lower() == alias.lower():
            return row['id']
    return None


def patch_notion_property(page_id: str, notion_prop_name: str, new_text: str, token: str):
    body = {
        'properties': {
            notion_prop_name: {
                'rich_text': [{'type': 'text', 'text': {'content': new_text}}]
            }
        }
    }
    return notion_http('PATCH', f'/pages/{page_id}', token=token, body=body)


# ── Main ─────────────────────────────────────────────────────────────────


def main() -> int:
    dry = '--dry-run' in sys.argv
    body_file = None
    summary_file = None
    for a in sys.argv[1:]:
        if a.startswith('--body-file='):
            body_file = Path(a.split('=', 1)[1])
        elif a.startswith('--summary-file='):
            summary_file = Path(a.split('=', 1)[1])

    if not body_file or not body_file.exists():
        sys.exit('❌ pass --body-file=<path to issue markdown>')

    token = os.environ.get('NOTION_KEY')
    if not token and not dry:
        sys.exit('❌ NOTION_KEY env missing (needed for live PATCH).')

    body = body_file.read_text(encoding='utf-8')
    checked = find_checked(body)

    if not checked:
        print('No checked boxes found — nothing to apply.')
        if summary_file:
            summary_file.write_text('_No checked boxes._\n', encoding='utf-8')
        return 0

    print(f'Found {len(checked)} checked box(es).')
    applied: list[dict] = []
    skipped: list[dict] = []

    # Cache Notion row IDs so we hit the query endpoint once per alias
    notion_rows: dict[str, str | None] = {}

    for t in checked:
        alias = t.get('alias')
        if not alias or alias not in COUNTRY_SOURCES:
            skipped.append({'reason': 'unknown alias', 'trailer': t})
            continue

        if t.get('action') == 'force_review':
            applied.append({'alias': alias, 'note': 'force_review acknowledged'})
            print(f'  · {alias}: force_review acknowledged (no Notion write)')
            continue

        kind = t.get('kind')
        field = t.get('field')
        json_path = t.get('jsonpath', '')
        new = t.get('new')

        if kind != 'money' or not field or not new:
            skipped.append({'reason': 'unsupported trailer', 'trailer': t})
            continue

        payload_path = DATA_DIR / f'{alias}_payload.json'
        if not payload_path.exists():
            skipped.append({'reason': 'payload missing', 'trailer': t})
            continue

        payload = json.loads(payload_path.read_text(encoding='utf-8'))
        changed = apply_money_change(payload, field, json_path, new)
        if not changed:
            skipped.append({'reason': 'no change (already current or path invalid)', 'trailer': t})
            continue

        print(f'  · {alias}.{field}[{json_path}] → {new}')
        if not dry:
            payload_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + '\n',
                encoding='utf-8',
            )
            # PATCH Notion — find row, then update the field
            if alias not in notion_rows:
                notion_rows[alias] = find_notion_row(alias, token)
            page_id = notion_rows[alias]
            if not page_id:
                skipped.append({'reason': 'Notion row not found', 'trailer': t})
                continue
            notion_prop = NOTION_NAMES.get(field)
            if not notion_prop:
                skipped.append({'reason': f'no Notion property for {field}', 'trailer': t})
                continue
            new_text = payload[field]
            status, resp = patch_notion_property(page_id, notion_prop, new_text, token)
            if status != 200:
                skipped.append({
                    'reason': f'Notion PATCH {status}',
                    'trailer': t,
                    'resp': resp,
                })
                continue
        applied.append({
            'alias': alias,
            'field': field,
            'jsonpath': json_path,
            'new': new,
            'kind': kind,
        })

    # Summary for the apply workflow to comment back
    ts = dt.datetime.now(dt.timezone.utc).isoformat()
    lines = [
        f'### intel-apply run · {ts}',
        '',
        f'Applied: **{len(applied)}** · Skipped: **{len(skipped)}** · Dry-run: **{dry}**',
        '',
    ]
    if applied:
        lines.append('**✅ Applied**')
        for a in applied:
            if 'note' in a:
                lines.append(f"- `{a['alias']}` — {a['note']}")
            else:
                lines.append(
                    f"- `{a['alias']}.{a['field']}` "
                    f"(path `{a['jsonpath']}`) → `{a['new']}`"
                )
        lines.append('')
    if skipped:
        lines.append('**⚠️ Skipped**')
        for s in skipped:
            lines.append(f"- `{s['trailer'].get('alias','?')}` — {s['reason']}")
        lines.append('')

    summary = '\n'.join(lines)
    print('\n' + summary)
    if summary_file:
        summary_file.parent.mkdir(parents=True, exist_ok=True)
        summary_file.write_text(summary, encoding='utf-8')
    return 0


if __name__ == '__main__':
    sys.exit(main())
