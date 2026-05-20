"""Hide the nav-link items (NAC Index · So Sánh · Property Hub) and
their separators from the brochure header on all viewports.

Result per the user request:
  left  → logo + "NAC BROCHURE 2026" only
  right → language toggle only

Idempotent — guarded by /*NAV-RIGHT-LANG-ONLY*/ marker.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BROCHURE_DIR = ROOT / 'Brochures html'
MARKER = '/*NAV-RIGHT-LANG-ONLY*/'

CSS = """
/* Header right side: hide cross-site nav links + separators on every
   viewport so only the language toggle remains. (Mobile rule below
   600px already hid them; this lifts it to apply universally.)
   /*NAV-RIGHT-LANG-ONLY*/ */
.nav-right .nav-link,
.nav-right .nav-sep { display: none !important; }
"""


def patch_one(path: Path) -> bool:
    html = path.read_text()
    if MARKER in html:
        return False
    if '</style>' not in html:
        return False
    new_html = html.replace('</style>', CSS + '\n</style>', 1)
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
