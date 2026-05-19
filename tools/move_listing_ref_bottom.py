"""Move the NAC-ID badge (.listing-ref) from top-right to bottom-right
of the listing hero so it no longer collides with the location +
eligibility pills sharing the top edge.

Idempotent — guarded by /*LISTING-REF-BOTTOM*/ marker.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BROCHURE_DIR = ROOT / 'Brochures html'
MARKER = '/*LISTING-REF-BOTTOM*/'

CSS_PATCH = """
/* Move NAC-ID pill away from the top pills cluster to bottom-right
   of the hero image so it stops crowding the location/eligibility
   pills on long location names like "Hammersmith & Fulham".
   /*LISTING-REF-BOTTOM*/ */
.listing-ref { top: auto !important; bottom: 14px !important; right: 14px !important; }
@media (max-width: 768px) {
  .listing-ref { bottom: 8px !important; right: 8px !important; }
}
"""


def patch_one(path: Path) -> bool:
    html = path.read_text()
    if MARKER in html:
        return False
    if '</style>' not in html:
        return False
    new_html = html.replace('</style>', CSS_PATCH + '\n</style>', 1)
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
