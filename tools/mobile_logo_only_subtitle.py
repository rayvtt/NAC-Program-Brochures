"""On mobile, hide the "Nomad Asset Collective" main logo text and
keep only the "NAC BROCHURE 2026" uppercase subtitle, so the header
title sits cleanly next to the logo mark.

Idempotent — guarded by /*MOBILE-LOGO-CSS*/ marker.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BROCHURE_DIR = ROOT / 'Brochures html'
MARKER = '/*MOBILE-LOGO-CSS*/'

CSS = """
/* Mobile header: show only "NAC BROCHURE 2026" subtitle, hide
   "Nomad Asset Collective" main label so the header doesn't
   crowd next to the logo mark on small screens. /*MOBILE-LOGO-CSS*/ */
@media (max-width: 600px) {
  .logo-text { display: none; }
  .logo-sub  { font-size: 11px; letter-spacing: 1.4px; line-height: 1.2; }
}
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
