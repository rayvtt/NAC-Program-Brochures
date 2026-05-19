"""Show the floating .nac-tools CTA pill on tablets / iPads, not just
phones. The original brochure CSS gated it behind `max-width: 720px`,
which hid the pill on the 721-1024px range (iPad portrait + landscape,
Android tablets). Bump the breakpoint to 1024px so it covers everything
below the desktop sidebar breakpoint (901px+ shows the inline sidebar
TOC, but the floating tools still help on iPad).

Idempotent — guarded by /*NAC-TOOLS-1024*/ marker.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BROCHURE_DIR = ROOT / 'Brochures html'
MARKER = '/*NAC-TOOLS-1024*/'


def patch_one(path: Path) -> bool:
    html = path.read_text()
    if MARKER in html:
        return False

    # The original media query block starts with `@media (max-width: 720px) {`
    # and contains `.nac-tools {`. Find that exact pattern and bump 720→1024.
    pat = re.compile(
        r'@media \(max-width:\s*720px\)\s*\{(\s*\.nac-tools\s*\{)',
    )
    new_html, n = pat.subn(
        rf'@media (max-width: 1024px) {{ {MARKER}\1',
        html,
        count=1,
    )
    if n == 0:
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
