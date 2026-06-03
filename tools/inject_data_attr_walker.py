"""Inject a data-vi/data-en attribute walker into the setLang function
of all legacy brochures (the 11 that use VI_STRINGS/EN_STRINGS).

Currently these brochures toggle EN/VI via string-replace on innerHTML.
The listings section (rendered by apply_listings.py) uses data-vi/data-en
attributes which setLang ignores. This patch adds "Pass 0" — a
querySelectorAll('[data-vi][data-en]') loop that toggles element content
from the attribute, BEFORE Pass 1 (innerHTML replacement) fires.

Idempotent — guarded by /* PASS-0-DATA-ATTR */ marker.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BROCHURE_DIR = ROOT / 'Brochures html'
MARKER = '/* PASS-0-DATA-ATTR */'

INJECT = """
  /* PASS-0-DATA-ATTR */
  // Pass 0 — toggle elements that have explicit data-vi / data-en
  // attributes (listings section, pulsing live-tag, listing footnotes,
  // etc). Runs before the legacy VI_STRINGS innerHTML replacement so
  // precise bilingual attrs take priority.
  document.querySelectorAll('[data-vi][data-en]').forEach(function(el) {
    var val = el.getAttribute('data-' + lang);
    if (val === null) return;
    if (val.indexOf('<') >= 0) el.innerHTML = val;
    else el.textContent = val;
  });

"""

# Inject right after `document.documentElement.lang = lang;` inside setLang
ANCHOR = "document.documentElement.lang = lang;"


def patch_one(path: Path) -> bool:
    html = path.read_text()
    if MARKER in html:
        return False
    if ANCHOR not in html:
        return False
    # Only patch legacy brochures (those with VI_STRINGS). Turkey uses
    # data-vi/data-en natively via buildCharts(lang).
    if 'VI_STRINGS' not in html and "VI_STRINGS" not in html:
        return False
    new_html = html.replace(ANCHOR, ANCHOR + '\n' + INJECT, 1)
    if new_html == html:
        return False
    path.write_text(new_html)
    return True


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if args:
        files = []
        for arg in args:
            files.extend(BROCHURE_DIR.glob(f'*{arg}*.html'))
    else:
        files = sorted(BROCHURE_DIR.glob('*.html'))
    files = [f for f in files if not f.name.startswith('NAC-BROCHURES')]
    files = [f for f in files if f.name != 'index.html']
    files = [f for f in files if 'RESIDENCE-INDEX' not in f.name]

    updated = unchanged = 0
    for f in files:
        if patch_one(f):
            updated += 1
            print(f'  ✓ {f.name}')
        else:
            unchanged += 1
            print(f'  · {f.name}')
    print(f'\n{updated} updated, {unchanged} unchanged.')


if __name__ == '__main__':
    main()
