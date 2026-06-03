"""Lock the hero breadcrumb to the same typography as the
"NAC BROCHURE 2026" header tagline:
  9px / weight 400 / 1.4px letter-spacing / uppercase / line-height 1.

Keeps the white-on-dark hero color scheme intact (the breadcrumb sits
on the dark hero background, not the page nav). Idempotent —
/*BREADCRUMB-LOCK-V1*/ marker.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BROCHURE_DIR = ROOT / 'Brochures html'
MARKER = '/*BREADCRUMB-LOCK-V1*/'

CSS = """
/* Breadcrumb typography lock — match "NAC BROCHURE 2026" tagline
   look. Colors preserved (white-on-dark hero). /*BREADCRUMB-LOCK-V1*/ */
.breadcrumb {
  font-size: 9px !important;
  font-weight: 400 !important;
  letter-spacing: 1.4px !important;
  line-height: 1 !important;
  text-transform: uppercase !important;
  gap: 8px !important;
}
.breadcrumb a,
.breadcrumb span {
  font-size: inherit !important;
  font-weight: inherit !important;
  letter-spacing: inherit !important;
  line-height: inherit !important;
  text-transform: inherit !important;
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
