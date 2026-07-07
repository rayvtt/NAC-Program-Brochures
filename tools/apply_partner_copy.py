#!/usr/bin/env python3
"""Apply a copy-change map to the Partner Gateway page (NAC-PARTNERS.html).

Driven by .github/workflows/apply-partner-copy.yml, which the in-page
editor (?edit=1 on the live page) dispatches with input `changes`:

    {"pg-a788c2": {"vi": "…", "en": "…"}, …}

Keys anchor to data-copy="<key>" elements; values are written into the
data-vi / data-en attributes (setLang hydrates all text from them).
Mirrors NAC---Property-Hub/scripts/apply-homepage-copy.mjs in Python
(this repo's tooling idiom).

Env: CHANGES — the JSON change map.
"""
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILE = ROOT / 'Brochures html' / 'NAC-PARTNERS.html'
LOG = ROOT / 'PARTNER-COPY-LOG.md'

KEY_RE = re.compile(r'^[a-z0-9_.-]+$', re.I)


def esc_attr(t: str) -> str:
    return (t.replace('&', '&amp;').replace('<', '&lt;')
             .replace('>', '&gt;').replace('"', '&quot;'))


def unesc(t: str) -> str:
    return (t.replace('&quot;', '"').replace('&lt;', '<')
             .replace('&gt;', '>').replace('&amp;', '&'))


def clip(t: str, n: int) -> str:
    return t[:n] + '…' if len(t) > n else t


def append_log(entries, source):
    if not entries:
        return
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M') + ' UTC'
    block = f'\n## {ts} · {source}\n\n'
    for e in entries:
        block += (f"- `{e['key']}` {e['lang'].upper()}: "
                  f"“{clip(e['oldVal'], 140)}” → “{clip(e['newVal'], 140)}”\n")
    cur = LOG.read_text(encoding='utf-8') if LOG.exists() else '# Partner Gateway Copy Log\n'
    LOG.write_text(cur + block, encoding='utf-8')


def update_inline_log(html, entries, source):
    m = re.search(r'<script type="application/json" id="copyLog">(.*?)</script>',
                  html, re.DOTALL)
    if not m:
        return html
    try:
        lst = json.loads(m.group(1))
    except (json.JSONDecodeError, ValueError):
        lst = []
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')
    add = [{'t': ts, 's': source, 'k': e['key'], 'l': e['lang'],
            'o': clip(e['oldVal'], 90), 'n': clip(e['newVal'], 90)} for e in entries]
    lst = (add + lst)[:40]
    # `<` must not appear inside a <script> block — escape as < in the JSON.
    js = json.dumps(lst, ensure_ascii=False).replace('<', '\\u003c')
    return html.replace(
        m.group(0),
        '<script type="application/json" id="copyLog">' + js + '</script>')


def main():
    changes = json.loads(os.environ.get('CHANGES') or '{}')
    html = FILE.read_text(encoding='utf-8')
    changed = 0
    log_entries = []

    for key, val in changes.items():
        if not KEY_RE.match(key):
            print(f'⚠ invalid key skipped: {key}', file=sys.stderr)
            continue
        m = re.search(r'<[^>]*data-copy="' + re.escape(key) + r'"[^>]*>', html)
        if not m:
            print(f'⚠ key not found: {key}', file=sys.stderr)
            continue
        tag = before = m.group(0)
        vi = val.get('vi', '').strip() if isinstance(val.get('vi'), str) else ''
        en = val.get('en', '').strip() if isinstance(val.get('en'), str) else ''
        old_vi_m = re.search(r'data-vi="([^"]*)"', tag)
        old_en_m = re.search(r'data-en="([^"]*)"', tag)
        old_vi = old_vi_m.group(1) if old_vi_m else ''
        old_en = old_en_m.group(1) if old_en_m else ''
        if vi and esc_attr(vi) != old_vi:
            log_entries.append({'key': key, 'lang': 'vi', 'oldVal': unesc(old_vi), 'newVal': vi})
        if en and esc_attr(en) != old_en:
            log_entries.append({'key': key, 'lang': 'en', 'oldVal': unesc(old_en), 'newVal': en})
        # lambda replacement — keeps backslashes in the new value literal
        if vi:
            tag = re.sub(r'data-vi="[^"]*"', lambda _: 'data-vi="' + esc_attr(vi) + '"', tag, count=1)
        if en:
            tag = re.sub(r'data-en="[^"]*"', lambda _: 'data-en="' + esc_attr(en) + '"', tag, count=1)
        if tag != before:
            html = html.replace(before, tag, 1)
            changed += 1
            print(f'✎ {key}')

    if changed:
        html = update_inline_log(html, log_entries, 'in-page editor')
        FILE.write_text(html, encoding='utf-8')
        append_log(log_entries, 'in-page editor')
        print(f'Applied {changed} change(s).')
    else:
        print('Nothing to apply.')


if __name__ == '__main__':
    main()
