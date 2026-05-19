"""Wrap each brochure's `<table class="comp-table">` in a <details>
collapse element so the table can be folded on mobile.

The pattern mirrors the matrix-chart collapse already in Turkey:
desktop shows everything (`<details open>`); a tiny chevron appears on
mobile and the summary header is tappable to fold.

Idempotent — guarded by the marker comment <!--COMP-COLLAPSE-->.
Re-running on a brochure that already has the wrap is a no-op.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BROCHURE_DIR = ROOT / 'Brochures html'

# Marker so re-running is idempotent.
MARKER = '<!--COMP-COLLAPSE-->'

# CSS added once near the existing .chart-collapse rules.
CSS_SNIPPET = """
/* Compare-table collapse — table can be folded on mobile.
   Mirrors .chart-collapse pattern (matrix chart). Idempotent — guarded
   by /*COMP-COLLAPSE-CSS*/ marker. */
.comp-collapse { width: 100%; margin-bottom: 0; }
.comp-collapse > summary { list-style: none; cursor: default; display: flex; align-items: center; justify-content: space-between; padding: 14px 16px; background: var(--bg2); border: 1px solid var(--border); border-bottom: none; border-radius: var(--r) var(--r) 0 0; }
.comp-collapse > summary::-webkit-details-marker { display: none; }
.comp-collapse > summary .comp-collapse-title { font-size: 12px; font-weight: 700; color: var(--text2); letter-spacing: -.1px; }
.comp-collapse[open] > summary { border-radius: var(--r) var(--r) 0 0; }
.comp-collapse:not([open]) > summary { border-radius: var(--r); border-bottom: 1px solid var(--border); }
.comp-collapse > .comp-table { border-radius: 0 0 var(--r) var(--r); border-top: none; }
.comp-collapse-icon { display: none; }
@media (max-width: 600px) {
  .comp-collapse > summary { cursor: pointer; user-select: none; }
  .comp-collapse-icon { display: inline-block; font-size: 14px; color: var(--text3); transition: transform .2s ease; margin-left: 8px; flex-shrink: 0; }
  .comp-collapse[open] .comp-collapse-icon { transform: rotate(180deg); }
}
/*COMP-COLLAPSE-CSS*/
"""

# JS that closes the <details> on mobile on first load.
JS_SNIPPET = """
<script>
/* Compare-table collapse: closed by default on mobile, open on desktop.
   COMP-COLLAPSE-JS */
(function () {
  function syncCompCollapse() {
    var det = document.querySelector('details.comp-collapse');
    if (!det) return;
    if (window.matchMedia('(max-width: 600px)').matches) det.open = false;
    else det.open = true;
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', syncCompCollapse);
  else syncCompCollapse();
  window.addEventListener('resize', syncCompCollapse);
})();
</script>
"""

SUMMARY_HTML = (
    '<summary>'
    '<span class="comp-collapse-title" data-vi="Bảng so sánh chi tiết" '
    'data-en="Detailed comparison table">Bảng so sánh chi tiết</span>'
    '<span class="comp-collapse-icon" aria-hidden="true">▾</span>'
    '</summary>'
)


def patch_one(path: Path) -> bool:
    """Return True if the file was modified."""
    html = path.read_text()
    if MARKER in html:
        return False

    # 1) Inject CSS right after .chart-collapse rules (look for the close
    #    of the matrix-collapse media query).
    if '/*COMP-COLLAPSE-CSS*/' not in html:
        # Anchor: the line that says `.chart-collapse[open] > summary .chart-title`
        # closing brace is near "transform: rotate(180deg); }".
        # Simpler: append right before the closing </style> tag.
        if '</style>' in html:
            html = html.replace('</style>', CSS_SNIPPET + '\n</style>', 1)
        else:
            return False

    # 2) Wrap the <table class="comp-table"> in a <details> element with a
    #    summary. Keep the closing </table> tag in place; close </details>
    #    after.
    pat = re.compile(
        r'(<table class="comp-table">)(.*?)(</table>)',
        re.DOTALL,
    )

    def repl(m):
        return (
            f'{MARKER}\n'
            f'<details class="comp-collapse" open>'
            f'{SUMMARY_HTML}'
            f'{m.group(1)}{m.group(2)}{m.group(3)}'
            f'</details>'
        )

    new_html, n = pat.subn(repl, html, count=1)
    if n == 0:
        return False

    # 3) Add the JS snippet once before </body>.
    if 'COMP-COLLAPSE-JS' not in new_html:
        new_html = new_html.replace('</body>', JS_SNIPPET + '\n</body>', 1)

    path.write_text(new_html)
    return True


def main():
    args = sys.argv[1:]
    files = []
    if args:
        for arg in args:
            matches = list(BROCHURE_DIR.glob(f'*{arg}*.html'))
            files.extend(matches)
    else:
        files = sorted(BROCHURE_DIR.glob('*.html'))

    # Skip non-brochure helper HTMLs.
    files = [f for f in files if not f.name.startswith('NAC-BROCHURES')]
    files = [f for f in files if f.name != 'index.html']

    updated = skipped = 0
    for f in files:
        if patch_one(f):
            updated += 1
            print(f'  ✓ {f.name}')
        else:
            skipped += 1
            print(f'  · {f.name} (already wrapped or no comp-table)')

    print(f'\n{updated} updated, {skipped} unchanged.')


if __name__ == '__main__':
    main()
