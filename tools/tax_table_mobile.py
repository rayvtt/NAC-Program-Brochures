"""Mobile-friendly tax tables across all brochures.

On screens ≤600px:
  - Hide the 3rd column (Ghi chú / Notes)
  - Drop the inline `min-width:560px` lock so the remaining 2 columns
    expand to fill the viewport
  - Inject a small disclaimer beneath each table pointing users to
    desktop for the full notes column

Idempotent — guarded by /*TAX-TABLE-MOBILE-V1*/ marker (CSS) and
<!--TAX-TABLE-NOTE--> marker (per-table HTML insertion).
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BROCHURE_DIR = ROOT / 'Brochures html'
CSS_MARKER = '/*TAX-TABLE-MOBILE-V1*/'
HTML_MARKER = '<!--TAX-TABLE-NOTE-->'

CSS = """
/* Tax table — mobile: hide notes column, let first 2 expand, drop
   the inline min-width lock. /*TAX-TABLE-MOBILE-V1*/ */
.tax-table-mobile-note {
  display: none;
  font-size: 11px;
  color: var(--text3, #6b7280);
  font-style: italic;
  margin: 8px 4px 20px;
  line-height: 1.4;
}
@media (max-width: 600px) {
  .tax-table { min-width: 0 !important; font-size: 12px; table-layout: fixed; }
  .tax-table th, .tax-table td { padding: 8px 10px; word-break: break-word; }
  .tax-table th:nth-child(3),
  .tax-table td:nth-child(3) { display: none !important; }
  .tax-table th:nth-child(1), .tax-table td:nth-child(1) { width: 60%; }
  .tax-table th:nth-child(2), .tax-table td:nth-child(2) { width: 40%; text-align: left; }
  .tax-table-mobile-note { display: block; }
}
"""

DISCLAIMER = (
    f'      {HTML_MARKER}\n'
    f'      <p class="tax-table-mobile-note" '
    f'data-vi="* Cột &quot;Ghi chú&quot; ẩn trên di động — xem trên màn hình lớn để đọc đầy đủ chi tiết." '
    f'data-en="* The &quot;Notes&quot; column is hidden on mobile — view on a larger screen for full detail.">'
    f'* Cột "Ghi chú" ẩn trên di động — xem trên màn hình lớn để đọc đầy đủ chi tiết.</p>'
)

# Match the wrapping <div> ... <table class="tax-table"...> ... </table> ... </div>
WRAPPER_RE = re.compile(
    r'(</table>\s*</div><!-- end tax-table overflow wrapper -->)',
    re.DOTALL,
)


def patch_css(html: str) -> str:
    if CSS_MARKER in html or '</style>' not in html:
        return html
    return html.replace('</style>', CSS + '\n</style>', 1)


def patch_disclaimer(html: str) -> str:
    """Insert the disclaimer paragraph after each tax-table wrapper.

    Skips wrappers that already have the marker right after them.
    """
    if HTML_MARKER in html:
        return html
    if '<table class="tax-table"' not in html:
        return html

    def repl(m):
        return m.group(1) + '\n' + DISCLAIMER

    return WRAPPER_RE.sub(repl, html)


def patch_one(path: Path) -> bool:
    html = path.read_text()
    new_html = patch_css(html)
    new_html = patch_disclaimer(new_html)
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
