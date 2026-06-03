"""Move the NAC-ID listing-ref pill back to the TOP-right corner of
the listing hero, smaller and more subtle so it doesn't overlap the
top-left "✓ RBI Eligible" badge.

Supersedes PR #105's bottom-right placement (LISTING-REF-BOTTOM).

Idempotent — guarded by /*LISTING-REF-TOP-V2*/ marker. Re-runs strip
any prior /*LISTING-REF-BOTTOM*/ block to keep the CSS clean.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BROCHURE_DIR = ROOT / 'Brochures html'
MARKER = '/*LISTING-REF-TOP-V2*/'

# CSS: small + top-right + subtle dark glass
CSS = """
/* NAC-ID pill: small + top-right + subtle (back from bottom).
   /*LISTING-REF-TOP-V2*/ */
.listing-ref {
  position: absolute !important;
  top: 8px !important;
  right: 8px !important;
  bottom: auto !important;
  left: auto !important;
  font-size: 8.5px !important;
  font-weight: 600 !important;
  letter-spacing: 0.4px !important;
  padding: 2px 6px !important;
  border-radius: 4px !important;
  background: rgba(0,0,0,0.45) !important;
  color: rgba(255,255,255,0.92) !important;
  line-height: 1.2 !important;
}
@media (max-width: 768px) {
  .listing-ref { font-size: 8px !important; padding: 2px 5px !important; top: 6px !important; right: 6px !important; }
}
"""


def patch_one(path: Path) -> bool:
    html = path.read_text()
    if MARKER in html:
        return False
    # Strip the prior bottom-right override block if present so we don't
    # leave dead CSS that fights the new one.
    html = re.sub(
        r'\n/\* Move NAC-ID pill away from the top pills cluster.*?/\*LISTING-REF-BOTTOM\*/ \*/.*?\}\s*\}\n',
        '\n',
        html,
        flags=re.DOTALL,
    )
    if '</style>' not in html:
        return False
    new_html = html.replace('</style>', CSS + '\n</style>', 1)
    if new_html == path.read_text():
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
