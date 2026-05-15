#!/usr/bin/env python3
"""Apply per-brochure nav-right link configuration to each brochure HTML.

Replaces the link region inside <div class="nav-right">…</div> (between
the opening tag and the inner <div class="lang-toggle">) with the link
set configured for each alias in data/nav.py.

Idempotent: re-rendering produces the same output, so re-running is safe.

Run:
    python tools/apply_nav.py            # all brochures
    python tools/apply_nav.py portugal   # one
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from data.nav import LINKS_BY_ALIAS  # noqa: E402

BROCHURE_DIR = ROOT / 'Brochures html'

ALIAS_FILE = {
    'portugal':   'portugal-gv.html',
    'greece':     'greece-rbi_1_2.html',
    'cyprus':     'cyprus-rbi_3_3.html',
    'turkey':     'turkey-cbi_8.html',
    'uae':        'uae-rbi_1_7.html',
    'uk':         'uk-rbi_1 (2).html',
    'malta':      'malta-rbi_1_3.html',
    'stkitts':    'stkitts-nevis.html',
    'thailand':   'thailand-rbi_1 (2).html',
    'newzealand': 'newzealand-rbi_1 (3).html',
    'panama':     'panama-rbi_.html',
    'malaysia':   'malaysia-mm2h.html',
}

# Match the existing <a class="nav-link">…</a> items and any <span class="nav-sep">
# separators between them, sitting between <div class="nav-right"> and the
# nested <div class="lang-toggle">.
NAV_REGION_RE = re.compile(
    r'(<div class="nav-right">\s*\n)'
    r'(?:\s*(?:<a class="nav-link"[^>]*>[^<]*</a>|<span class="nav-sep">[^<]*</span>)\s*\n)+'
    r'(\s*<div class="lang-toggle">)'
)


def render_links(links):
    parts = []
    for i, (label, href) in enumerate(links):
        if i > 0:
            parts.append('      <span class="nav-sep">·</span>')
        parts.append(f'      <a class="nav-link" href="{href}" target="_blank">{label}</a>')
    return '\n'.join(parts) + '\n'


def patch(alias):
    fname = ALIAS_FILE.get(alias)
    if not fname:
        return None, 'no filename mapping'
    links = LINKS_BY_ALIAS.get(alias)
    if not links:
        return None, 'no nav config in data/nav.py'
    path = BROCHURE_DIR / fname
    if not path.exists():
        return None, f'file not found ({fname})'

    raw = path.read_bytes()
    crlf = b'\r\n' in raw
    text = raw.decode('utf-8').replace('\r\n', '\n') if crlf else raw.decode('utf-8')

    rendered = render_links(links)
    new_text, n = NAV_REGION_RE.subn(r'\1' + rendered + r'\2', text, count=1)
    if n == 0:
        return None, 'nav-right region not found'
    if new_text == text:
        return False, 'no changes'

    out = new_text.replace('\n', '\r\n') if crlf else new_text
    path.write_bytes(out.encode('utf-8'))
    return True, 'patched'


def main():
    args = sys.argv[1:]
    aliases = args or list(ALIAS_FILE.keys())
    patched = skipped = failed = 0
    for alias in aliases:
        ok, msg = patch(alias)
        if ok is True:
            mark, patched = '✓', patched + 1
        elif ok is False:
            mark, skipped = '–', skipped + 1
        else:
            mark, failed = '✗', failed + 1
        print(f'  {mark} {alias:12s}  {msg}')
    print(f'\n{patched} patched, {skipped} skipped, {failed} failed.')


if __name__ == '__main__':
    main()
