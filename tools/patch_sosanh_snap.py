#!/usr/bin/env python3
"""Patch data/sosanh_payload.json into var DB_STATIC = {...}; inside
NAC-SO-SANH.html — a surgical single-line regex replace, never a
full-file regenerate (same class of patch as inject_notion_en_to_html.py
for the brochure family).

WP-safety: NAC-SO-SANH.html's own in-file comment documents that a
backslash anywhere in this file is silently stripped by WP's wp_unslash
on every push. This script hard-fails rather than emit one — see
check_no_backslash() below.

Run:
    python tools/patch_sosanh_snap.py
    python tools/patch_sosanh_snap.py --dry-run   # validate only, don't write
"""
import datetime
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HTML_PATH = ROOT / 'Brochures html' / 'NAC-SO-SANH.html'
PAYLOAD_PATH = ROOT / 'data' / 'sosanh_payload.json'

DB_STATIC_RE = re.compile(r'var DB_STATIC = \{.*?\};', re.DOTALL)


def check_no_backslash(s, label):
    if chr(92) in s:
        sys.exit(f'❌ literal backslash found in {label} — WP wp_unslash would corrupt this on push')


def main():
    dry = '--dry-run' in sys.argv

    payload = json.loads(PAYLOAD_PATH.read_text(encoding='utf-8'))
    countries = payload['countries']
    if not countries:
        sys.exit('❌ empty countries dict — refusing to patch (would blank the live tool)')

    codes = list(countries.keys())
    if len(codes) != len(set(codes)):
        sys.exit(f'❌ duplicate country codes in payload: {codes}')

    db_static = {
        'asOf': datetime.datetime.now(datetime.timezone.utc).strftime('%d/%m/%Y'),
        'countries': countries,
    }
    db_static_js = json.dumps(db_static, ensure_ascii=False, separators=(',', ':'))
    check_no_backslash(db_static_js, 'the generated DB_STATIC blob')

    html = HTML_PATH.read_text(encoding='utf-8')
    if not DB_STATIC_RE.search(html):
        sys.exit('❌ "var DB_STATIC = {...};" not found in NAC-SO-SANH.html — has the file structure changed?')

    # lambda replacement — re.sub would otherwise mis-interpret a literal
    # backslash-digit run inside the replacement string as a backreference
    # (moot today since check_no_backslash already forbids backslashes, but
    # this is the correct way to inject arbitrary text regardless)
    new_html = DB_STATIC_RE.sub(lambda _m: 'var DB_STATIC = ' + db_static_js + ';', html, count=1)
    check_no_backslash(new_html, 'the patched HTML file')

    if new_html == html:
        print('  · unchanged (no-op)')
        return

    old_codes = set()
    m = re.search(r'"countries":\{(.*)', html, re.DOTALL)
    if m:
        old_codes = set(re.findall(r'"code":"([a-z]{2})"', m.group(1)[:200000]))
    new_codes = set(codes)
    added = new_codes - old_codes
    removed = old_codes - new_codes
    if added:
        print(f'  + countries added: {sorted(added)}')
    if removed:
        print(f'  - countries removed: {sorted(removed)}')
    print(f'  {len(new_codes)} countries, asOf {db_static["asOf"]}')

    if dry:
        print('--dry-run — not writing.')
        return

    HTML_PATH.write_text(new_html, encoding='utf-8')
    print(f'  wrote {HTML_PATH}')


if __name__ == '__main__':
    main()
