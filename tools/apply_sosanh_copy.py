#!/usr/bin/env python3
"""Apply a copy-change map to the So Sánh compare tool (NAC-SO-SANH.html).

Driven by .github/workflows/apply-sosanh-copy.yml, which the in-page editor
(?edit=1 on the live page) dispatches with input `changes`:

    {"heroS": {"vi": "…", "en": "…", "o_vi": "…", "o_en": "…"}, …}

Unlike Partner Gateway / Homepage V2 (content-derived data-copy keys on
static elements), So Sánh's editable chrome text is re-rendered on every
language toggle / country swap from a single `var I18N = {...}` object
(`t(key)` reads it every time). Patching per-element data-vi/data-en
attributes would get silently overwritten by the next render() call, so
this script instead patches the I18N object literal itself — the one
source every render pulls from, however many times the DOM rebuilds.

Keys here are stable, hand-chosen identifiers (gateT, heroS, ftS, ...),
not content hashes, so there is no key-drift / old-text-fallback need
the sibling scripts have. Presence in the payload still decides an edit,
never truthiness — an empty string is a legitimate deletion.

Also writes back to the 🔀 NAC - So Sánh Copy Notion DB (upsert by Key)
as an audit trail — best-effort: missing/invalid NOTION_TOKEN skips this
step without failing the run (the HTML patch is the part that must not
silently fail).
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILE = ROOT / 'Brochures html' / 'NAC-SO-SANH.html'
LOG = ROOT / 'SOSANH-COPY-LOG.md'
SKIP_FILE = Path(os.environ.get('SKIP_FILE') or '/tmp/copy-apply-skipped.txt')

NOTION_DB_ID = 'd6c57d9d38bf48d698b559a6c5ef6700'  # 🔀 NAC - So Sánh Copy
NOTION_VERSION = '2022-06-28'

KEY_RE = re.compile(r'^[a-zA-Z0-9_]+$')
# One I18N entry per line: `  key:{vi:'...',en:'...'},` — non-greedy up to the
# next `',en:'` / closing `'}` boundary. Values are sanitized (see
# to_js_single_quoted) so they never contain a raw `'`, keeping this safe.
ENTRY_RE_TPL = r"(  %s:\{vi:')(.*?)(',en:')(.*?)('\},?)"


def esc_html(t: str) -> str:
    return t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def unesc_html(t: str) -> str:
    return t.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')


def norm(t) -> str:
    if not isinstance(t, str):
        return ''
    return re.sub(r'\s+', ' ', t).strip()


def to_js_single_quoted(t: str) -> str:
    """Sanitize for insertion into a single-quoted JS string literal, with
    ZERO backslashes (WP's wp_unslash strips one level on every push — see
    this repo's Trap 2). A straight apostrophe would otherwise terminate the
    string early, so swap it for the Unicode curly apostrophe, the same
    workaround this repo already uses elsewhere for the identical class of
    problem. Also strips any literal newline (contenteditable can insert
    one) since these are single-line JS string values."""
    return (t.replace('\n', ' ').replace('\r', '')
             .replace("'", '’'))


def clip(t: str, n: int) -> str:
    return t[:n] + '…' if len(t) > n else t


def show(t: str) -> str:
    return t if t else '∅ (đã xoá)'


def find_entry(html: str, key: str):
    m = re.search(ENTRY_RE_TPL % re.escape(key), html, re.DOTALL)
    return m


def append_log(entries, source):
    if not entries:
        return
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M') + ' UTC'
    block = f'\n## {ts} · {source}\n\n'
    for e in entries:
        block += (f"- `{e['key']}` {e['lang'].upper()}: "
                  f"“{clip(show(e['oldVal']), 140)}” → “{clip(show(e['newVal']), 140)}”\n")
    cur = LOG.read_text(encoding='utf-8') if LOG.exists() else '# So Sánh Copy Log\n'
    LOG.write_text(cur + block, encoding='utf-8')


def notion_req(method, path, body=None):
    token = os.environ.get('NOTION_TOKEN')
    if not token:
        return None
    url = f'https://api.notion.com/v1/{path}'
    data = json.dumps(body).encode('utf-8') if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header('Authorization', f'Bearer {token}')
    req.add_header('Notion-Version', NOTION_VERSION)
    req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        print(f'⚠ Notion API {method} {path} → {e.code}: {e.read().decode("utf-8", "replace")[:300]}',
              file=sys.stderr)
        return None
    except Exception as e:  # noqa: BLE001 — best-effort, never fail the run
        print(f'⚠ Notion API {method} {path} failed: {e}', file=sys.stderr)
        return None


def notion_upsert(key: str, vi: str, en: str):
    """Best-effort upsert into 🔀 NAC - So Sánh Copy by Key. Skips silently
    (returns False) if NOTION_TOKEN is unset or the call fails — the HTML
    patch already happened by the time this runs, so a Notion outage never
    loses the actual edit, only its audit-trail mirror."""
    if not os.environ.get('NOTION_TOKEN'):
        return False
    found = notion_req('POST', f'databases/{NOTION_DB_ID}/query', {
        'filter': {'property': 'Key', 'rich_text': {'equals': key}},
        'page_size': 1,
    })
    props = {
        'VI — Nội dung': {'title': [{'text': {'content': vi[:2000]}}]},
        'Key': {'rich_text': [{'text': {'content': key}}]},
        'EN': {'rich_text': [{'text': {'content': en[:2000]}}]},
        'Nguồn': {'select': {'name': 'in-page editor'}},
        'Cập nhật lúc': {'date': {'start': datetime.now(timezone.utc).isoformat()}},
    }
    if found and found.get('results'):
        page_id = found['results'][0]['id']
        res = notion_req('PATCH', f'pages/{page_id}', {'properties': props})
    else:
        res = notion_req('POST', 'pages', {
            'parent': {'database_id': NOTION_DB_ID},
            'properties': props,
        })
    return res is not None


def main():
    changes = json.loads(os.environ.get('CHANGES') or '{}')
    html = FILE.read_text(encoding='utf-8')
    changed = 0
    log_entries = []
    applied_keys = []
    notion_pending = []  # [(key, vi, en)] — synced only AFTER the file is safely written
    skipped = []  # (key, reason)

    # Pass 1 — pure in-memory string work, no network calls. This is the part
    # that must never be delayed or blocked by anything external.
    for key, val in changes.items():
        if not KEY_RE.match(key):
            skipped.append((key, 'invalid key'))
            continue
        # Presence decides, not truthiness — '' is a deletion, a real edit.
        vi = norm(val['vi']) if isinstance(val.get('vi'), str) else None
        en = norm(val['en']) if isinstance(val.get('en'), str) else None
        if vi is None and en is None:
            skipped.append((key, 'no vi/en value in payload'))
            continue
        m = find_entry(html, key)
        if not m:
            skipped.append((key, 'key not found in I18N object — was it renamed or removed?'))
            continue
        old_vi_raw, old_en_raw = m.group(2), m.group(4)
        old_vi = unesc_html(old_vi_raw.replace('’', "'"))
        old_en = unesc_html(old_en_raw.replace('’', "'"))
        new_vi_raw = to_js_single_quoted(esc_html(vi)) if vi is not None else old_vi_raw
        new_en_raw = to_js_single_quoted(esc_html(en)) if en is not None else old_en_raw
        if vi is not None and new_vi_raw != old_vi_raw:
            log_entries.append({'key': key, 'lang': 'vi', 'oldVal': old_vi, 'newVal': vi})
        if en is not None and new_en_raw != old_en_raw:
            log_entries.append({'key': key, 'lang': 'en', 'oldVal': old_en, 'newVal': en})
        if new_vi_raw != old_vi_raw or new_en_raw != old_en_raw:
            replacement = m.group(1) + new_vi_raw + m.group(3) + new_en_raw + m.group(5)
            html = html[:m.start()] + replacement + html[m.end():]
            changed += 1
            applied_keys.append(key)
            print(f'✎ {key}')
            notion_pending.append((key, vi if vi is not None else old_vi, en if en is not None else old_en))
        else:
            skipped.append((key, 'value identical to current — nothing to change'))

    if changed:
        html = update_inline_log(html, log_entries)
        FILE.write_text(html, encoding='utf-8')
        append_log(log_entries, 'in-page editor')
        print(f'Applied {changed} change(s). File written — Notion sync (best-effort) follows.')
    else:
        print('Nothing to apply.')

    # Pass 2 — Notion mirror, strictly after the file write above. A slow or
    # dead Notion API can never delay, block, or risk the commit that matters.
    notion_synced = 0
    for key, vi, en in notion_pending:
        if notion_upsert(key, vi, en):
            notion_synced += 1
    if notion_pending:
        print(f'{notion_synced}/{len(notion_pending)} synced to Notion.')

    # Loud, visible reporting — a silently lost edit is the worst outcome.
    summary = [f'## So Sánh copy apply — {changed} applied, {len(skipped)} skipped, '
               f'{notion_synced} synced to Notion']
    for k in applied_keys:
        summary.append(f'- ✅ `{k}`')
    real_failures = []
    for k, why in skipped:
        icon = '⚪' if why.startswith('value identical') else '❌'
        summary.append(f'- {icon} `{k}` — {why}')
        if icon == '❌':
            real_failures.append(f'{k}: {why}')
            print(f'⚠ SKIPPED {k}: {why}', file=sys.stderr)
    if not os.environ.get('NOTION_TOKEN'):
        summary.append('- ⚪ Notion sync skipped — NOTION_TOKEN not set (HTML patch still applied)')
    step_summary(summary)
    SKIP_FILE.parent.mkdir(parents=True, exist_ok=True)
    SKIP_FILE.write_text('\n'.join(real_failures), encoding='utf-8')


def update_inline_log(html, entries):
    """Mirror into the inline <script id="copyLog"> history block, same
    pattern as Partner Gateway / Homepage V2 (powers a future 📜 history
    panel if one is added; harmless no-op today if the tag doesn't exist)."""
    m = re.search(r'<script type="application/json" id="copyLog">(.*?)</script>',
                  html, re.DOTALL)
    if not m:
        return html
    try:
        lst = json.loads(m.group(1))
    except (json.JSONDecodeError, ValueError):
        lst = []
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')
    add = [{'t': ts, 's': 'in-page editor', 'k': e['key'], 'l': e['lang'],
            'o': clip(show(e['oldVal']), 90), 'n': clip(show(e['newVal']), 90)} for e in entries]
    lst = (add + lst)[:40]
    js = json.dumps(lst, ensure_ascii=False).replace('<', '\\u003c')
    return html.replace(m.group(0), '<script type="application/json" id="copyLog">' + js + '</script>')


def step_summary(lines):
    path = os.environ.get('GITHUB_STEP_SUMMARY')
    if not path:
        return
    with open(path, 'a', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')


if __name__ == '__main__':
    main()
