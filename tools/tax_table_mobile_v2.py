"""Upgrade the tax-table mobile disclaimer to the pill style already
used by .comp-table-mobile-msg in Greece/Cyprus/Malaysia. Matches the
screenshot the user shared:

  ┌─────────────────────────────────────────────────────┐
  │  📊 Xem thông tin hoàn chỉnh trên desktop / web view│
  └─────────────────────────────────────────────────────┘

Replaces the plain italic line added in PR #112.

Idempotent — guarded by /*TAX-TABLE-MOBILE-V2*/ marker (CSS) and
re-uses the same <!--TAX-TABLE-NOTE--> HTML guard.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BROCHURE_DIR = ROOT / 'Brochures html'
CSS_MARKER_V2 = '/*TAX-TABLE-MOBILE-V2*/'
HTML_MARKER = '<!--TAX-TABLE-NOTE-->'

CSS = """
/* Tax table mobile — pill-style disclaimer + column hiding.
   Matches the .comp-table-mobile-msg look so the two tables read
   alike on small screens. /*TAX-TABLE-MOBILE-V2*/ */
.tax-table-mobile-note { display: none; }
@media (max-width: 600px) {
  .tax-table { min-width: 0 !important; font-size: 12px; table-layout: fixed; }
  .tax-table th, .tax-table td { padding: 8px 10px; word-break: break-word; }
  .tax-table th:nth-child(3),
  .tax-table td:nth-child(3) { display: none !important; }
  .tax-table th:nth-child(1), .tax-table td:nth-child(1) { width: 60%; }
  .tax-table th:nth-child(2), .tax-table td:nth-child(2) { width: 40%; text-align: left; }
  .tax-table-mobile-note {
    display: block;
    background: var(--bg2);
    border: 1px solid var(--border);
    border-radius: var(--r);
    padding: 14px 18px;
    font-size: 13px;
    font-style: italic;
    color: var(--text3);
    text-align: center;
    margin: 12px 0 24px;
    line-height: 1.4;
  }
}
"""

NEW_DISCLAIMER = (
    f'      {HTML_MARKER}\n'
    f'      <div class="tax-table-mobile-note" '
    f'data-vi="📊 Xem thông tin hoàn chỉnh trên desktop / web view" '
    f'data-en="📊 View complete information on desktop / web view">'
    f'📊 Xem thông tin hoàn chỉnh trên desktop / web view</div>'
)


def patch_one(path: Path) -> bool:
    html = path.read_text()
    if CSS_MARKER_V2 in html:
        return False

    # 1) Strip the v1 CSS block + its surrounding /* ... */ comment block.
    html = re.sub(
        r'\n/\* Tax table — mobile: hide notes column.*?/\*TAX-TABLE-MOBILE-V1\*/ \*/.*?(?=\n[^ ]|\n@media|\n\.|</style>)',
        '\n',
        html,
        flags=re.DOTALL,
    )

    # 2) Replace any existing .tax-table-mobile-note <p> element with the new
    # <div>-based markup (we keep the same HTML marker for backwards-compat).
    html = re.sub(
        r'(<!--TAX-TABLE-NOTE-->\s*)<p class="tax-table-mobile-note"[^>]*>[^<]*</p>',
        lambda m: NEW_DISCLAIMER,
        html,
    )

    # 3) Inject the new CSS.
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
