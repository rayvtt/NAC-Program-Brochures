"""Inject CSS for the new <div class="sec-live-tag"> + pulsing dot used
by the listings section header. Pairs with the apply_listings.py
template change that moved "Đang Mở Bán" out of the H2 onto its own line.

Idempotent — guarded by /*SEC-LIVE-TAG-V1*/ marker.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BROCHURE_DIR = ROOT / 'Brochures html'
MARKER = '/*SEC-LIVE-TAG-V1*/'

CSS = """
/* Listings live-tag — small pulsing-dot indicator below the section
   title (mirrors a status badge). /*SEC-LIVE-TAG-V1*/ */
.sec-live-tag {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin: 4px 0 14px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 1.2px;
  text-transform: uppercase;
  color: var(--green, #10b981);
}
.sec-live-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--green, #10b981);
  box-shadow: 0 0 0 0 rgba(16,185,129,0.7);
  animation: sec-live-pulse 1.8s infinite;
  flex-shrink: 0;
}
@keyframes sec-live-pulse {
  0%   { box-shadow: 0 0 0 0   rgba(16,185,129,0.7); }
  70%  { box-shadow: 0 0 0 10px rgba(16,185,129,0); }
  100% { box-shadow: 0 0 0 0   rgba(16,185,129,0); }
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
