"""Lock the brochure header to a single consistent style across all
16 brochures, matching the Greece template (which most others already
follow). Portugal had drifted (different size, color, letter-spacing,
nav-right gap), and a few sub-properties may differ on others.

Applies via !important so it wins regardless of each brochure's
local CSS. Idempotent — guarded by /*HEADER-LOCK-V1*/ marker.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BROCHURE_DIR = ROOT / 'Brochures html'
MARKER = '/*HEADER-LOCK-V1*/'

CSS = """
/* Header style lock — Greece template values, applied to all 16
   brochures for visual consistency. Wins over per-brochure CSS via
   !important. /*HEADER-LOCK-V1*/ */
.nav-i { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.logo { display: flex; align-items: center; gap: 10px; text-decoration: none; flex-shrink: 0; }
.logo-mark { width: 32px !important; height: 32px !important; border-radius: 7px; flex-shrink: 0; overflow: hidden; }
.logo-mark img { width: 100% !important; height: 100% !important; object-fit: cover !important; border-radius: 0 !important; display: block; }
.logo-text-wrap { display: flex; flex-direction: column; gap: 1px; }
.logo-text { display: none !important; }
.logo-sub  {
  font-size: 9px !important;
  font-weight: 400 !important;
  letter-spacing: 1.4px !important;
  line-height: 1 !important;
  text-transform: uppercase !important;
  color: var(--text4, #94a3b8) !important;
  margin: 0 !important;
}
.nav-right { display: flex; align-items: center; gap: 6px !important; }
.nav-right .nav-link, .nav-right .nav-sep { display: none !important; }
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
