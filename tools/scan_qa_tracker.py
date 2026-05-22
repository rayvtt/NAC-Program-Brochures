"""Daily scan of the ✅ NAC Brochures - QA Tracker Notion DB.

Each row = one brochure. Each property = one issue (Notion CHECKBOX).
Checked = OK, unchecked = issue still open.

Env:
  NOTION_KEY  — same secret used by pull_from_notion.py.

Stdlib-only.
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_FILE = ROOT / '.diagnostics' / 'qa-status.md'

DATA_SOURCE_ID = '861f37a2-0eb7-405a-955c-80605052102d'
NOTION_BASE = 'https://api.notion.com/v1'

SKIP_PROPS = {'Brochure', 'Live URL', 'order', 'Notes'}


def http(method, url, *, token, body=None):
    req = urllib.request.Request(url, method=method)
    req.add_header('Authorization', f'Bearer {token}')
    req.add_header('Notion-Version', '2022-06-28')
    req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req, data=body.encode() if body else None, timeout=30) as r:
            return r.status, r.read().decode('utf-8')
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8', errors='replace')


def query_all_rows(token):
    rows = []
    cursor = None
    while True:
        body = json.dumps({'page_size': 100, **({'start_cursor': cursor} if cursor else {})})
        status, resp = http('POST', f'{NOTION_BASE}/data_sources/{DATA_SOURCE_ID}/query',
                            token=token, body=body)
        if status != 200:
            sys.exit(f'❌ HTTP {status} querying QA tracker: {resp[:500]}')
        data = json.loads(resp)
        rows.extend(data.get('results', []))
        if not data.get('has_more'):
            break
        cursor = data.get('next_cursor')
    return rows


def decode_title(p):
    if not p or p.get('type') != 'title':
        return ''
    return ''.join(rt['plain_text'] for rt in p['title'])


def decode_url(p):
    return (p or {}).get('url') or ''


def decode_number(p):
    return (p or {}).get('number')


def decode_text(p):
    if not p or p.get('type') != 'rich_text':
        return ''
    return ''.join(rt['plain_text'] for rt in p['rich_text'])


def issue_key(n):
    m = re.match(r'#(\d+)', n)
    return (int(m.group(1)) if m else 999, n)


def main():
    token = os.environ.get('NOTION_KEY')
    if not token:
        sys.exit('❌ NOTION_KEY env var not set.')

    print('Querying QA Tracker DB…')
    rows = query_all_rows(token)
    print(f'  {len(rows)} rows fetched')

    brochures = []
    issue_names = set()
    for row in rows:
        props = row['properties']
        name = decode_title(props.get('Brochure'))
        url = decode_url(props.get('Live URL'))
        order = decode_number(props.get('order')) or 999
        notes = decode_text(props.get('Notes'))
        checks = {}
        for pname, pval in props.items():
            if pname in SKIP_PROPS:
                continue
            if pval.get('type') != 'checkbox':
                continue
            checks[pname] = bool(pval.get('checkbox'))
            issue_names.add(pname)
        brochures.append({'name': name, 'url': url, 'order': order, 'notes': notes, 'checks': checks})

    brochures.sort(key=lambda b: (b['order'], b['name']))

    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')
    lines = [
        '# NAC Brochures — QA Tracker Status',
        '',
        f'_Last scan: {now}_',
        f'_Source: Notion DB `✅ NAC Brochures - QA Tracker`_',
        '',
    ]

    total = open_count = 0
    open_by_brochure = {}
    open_by_issue = {}

    for b in brochures:
        for issue, ok in b['checks'].items():
            total += 1
            if not ok:
                open_count += 1
                open_by_brochure.setdefault(b['name'], []).append(issue)
                open_by_issue.setdefault(issue, []).append(b['name'])

    if open_count == 0:
        lines += ['## ✅ All checks passing', '',
                  f'Every applicable cell ({total}) is ticked. No open issues.']
    else:
        pct = 100 * (total - open_count) / total if total else 0
        lines.append(f'## 🟡 {open_count} of {total} cells still open ({pct:.1f}% done)')
        lines.append('')

        lines += ['### Open by issue', '']
        for issue in sorted(open_by_issue, key=issue_key):
            lines.append(f'**{issue}**')
            for b in open_by_issue[issue]:
                lines.append(f'  - {b}')
            lines.append('')

        lines += ['### Open by brochure', '']
        for b in brochures:
            if b['name'] not in open_by_brochure:
                continue
            issues = open_by_brochure[b['name']]
            lines.append(f'**{b["name"]}** — {len(issues)} open')
            for issue in sorted(issues, key=issue_key):
                lines.append(f'  - {issue}')
            if b['notes']:
                lines.append(f'  - _note:_ {b["notes"]}')
            lines.append('')

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text('\n'.join(lines) + '\n')
    print(f'  → wrote {OUT_FILE.relative_to(ROOT)}')
    sys.exit(0)


if __name__ == '__main__':
    main()
