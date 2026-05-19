"""Strip the "Nomad Asset Collective" primary label from the header
across every viewport, keeping only the slim uppercase "NAC BROCHURE
2026" tagline.

Replaces the earlier mobile-only override (/*MOBILE-LOGO-CSS*/) with
a global version (/*HEADER-TAGLINE-ONLY*/).

Idempotent — re-running is a no-op once the new marker is present.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BROCHURE_DIR = ROOT / 'Brochures html'
NEW_MARKER = '/*HEADER-TAGLINE-ONLY*/'

NEW_CSS = """
/* Header: keep only the slim "NAC BROCHURE 2026" tagline. The primary
   "Nomad Asset Collective" label is hidden everywhere (was previously
   mobile-only). /*HEADER-TAGLINE-ONLY*/ */
.logo-text { display: none !important; }
.logo-sub  { font-size: 11px; letter-spacing: 1.4px; line-height: 1.2; }
"""


def patch_one(path: Path) -> bool:
    html = path.read_text()
    if NEW_MARKER in html:
        return False
    if '</style>' not in html:
        return False

    # Strip the older mobile-only block if present so we don't leave
    # dead/duplicate rules in the file.
    html = re.sub(
        r'\n/\* Mobile header: show only.*?/\*MOBILE-LOGO-CSS\*/.*?\}\s*\}\n',
        '\n',
        html,
        flags=re.DOTALL,
    )

    new_html = html.replace('</style>', NEW_CSS + '\n</style>', 1)
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
