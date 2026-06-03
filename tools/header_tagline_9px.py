"""Shrink the "NAC BROCHURE 2026" header tagline from 11px → 9px
(original slim subtitle size). Same letter-spacing + line-height.

Idempotent — guarded by /*HEADER-TAGLINE-9PX*/ marker.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BROCHURE_DIR = ROOT / 'Brochures html'
NEW_MARKER = '/*HEADER-TAGLINE-9PX*/'


def patch_one(path: Path) -> bool:
    html = path.read_text()
    if NEW_MARKER in html:
        return False

    old = '.logo-sub  { font-size: 11px; letter-spacing: 1.4px; line-height: 1.2; }'
    new = '.logo-sub  { font-size: 9px; letter-spacing: 1.4px; line-height: 1.2; } ' + NEW_MARKER
    if old not in html:
        return False

    path.write_text(html.replace(old, new, 1))
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
