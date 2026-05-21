"""Stronger breadcrumb typography lock — higher selector specificity
so it can't be undercut by hero-section ancestors or per-brochure
CSS that v1 missed.

Idempotent — guarded by /*BREADCRUMB-LOCK-V2*/ marker.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BROCHURE_DIR = ROOT / 'Brochures html'
MARKER = '/*BREADCRUMB-LOCK-V2*/'

# Wraps the rule with extra ancestor selectors so it wins even when
# something targets `.hero .breadcrumb` or similar.
CSS = """
/* Breadcrumb typography lock — v2 with belt-and-braces specificity.
   /*BREADCRUMB-LOCK-V2*/ */
.hero .breadcrumb,
.hero-content .breadcrumb,
.hero-i .breadcrumb,
body .breadcrumb {
  font-size: 9px !important;
  font-weight: 400 !important;
  letter-spacing: 1.4px !important;
  line-height: 1 !important;
  text-transform: uppercase !important;
  gap: 8px !important;
}
.hero .breadcrumb a,
.hero .breadcrumb span,
.hero-content .breadcrumb a,
.hero-content .breadcrumb span,
.hero-i .breadcrumb a,
.hero-i .breadcrumb span,
body .breadcrumb a,
body .breadcrumb span {
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
