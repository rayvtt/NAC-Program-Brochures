"""Wrap each brochure's §05 tax grid (the `.overview-grid` inside
`<section class="section" id="tax">`) in a <details> collapse element
so the 6-card tax rates can be folded on mobile.

Mirrors the matrix-chart collapse pattern. Open on desktop, JS folds
it closed on mobile, user can tap the summary chevron to expand.

Idempotent — guarded by the marker comment <!--TAX-COLLAPSE-->.
Re-running on a brochure that already has the wrap is a no-op.

Also undoes the earlier (mistargeted) comp-table collapse on first run
— see `--keep-comp` to disable that cleanup.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BROCHURE_DIR = ROOT / 'Brochures html'

TAX_MARKER = '<!--TAX-COLLAPSE-->'
COMP_MARKER = '<!--COMP-COLLAPSE-->'

TAX_CSS = """
/* Tax-grid collapse — §05 tax-rate cards fold on mobile.
   Mirrors .chart-collapse pattern. Idempotent — guarded by
   /*TAX-COLLAPSE-CSS*/ marker. */
.tax-collapse { width: 100%; margin-bottom: 20px; }
.tax-collapse > summary { list-style: none; cursor: default; display: flex; align-items: center; justify-content: space-between; padding: 14px 16px; background: var(--bg2); border: 1px solid var(--border); border-radius: var(--r); margin-bottom: 14px; }
.tax-collapse > summary::-webkit-details-marker { display: none; }
.tax-collapse > summary .tax-collapse-title { font-size: 12px; font-weight: 700; color: var(--text2); letter-spacing: -.1px; }
.tax-collapse:not([open]) > summary { margin-bottom: 0; }
.tax-collapse > .overview-grid { margin-bottom: 0 !important; }
.tax-collapse-icon { display: none; }
@media (max-width: 600px) {
  .tax-collapse > summary { cursor: pointer; user-select: none; }
  .tax-collapse-icon { display: inline-block; font-size: 14px; color: var(--text3); transition: transform .2s ease; margin-left: 8px; flex-shrink: 0; }
  .tax-collapse[open] .tax-collapse-icon { transform: rotate(180deg); }
}
/*TAX-COLLAPSE-CSS*/
"""

TAX_JS = """
<script>
/* Tax-grid collapse: closed by default on mobile, open on desktop.
   TAX-COLLAPSE-JS */
(function () {
  function syncTaxCollapse() {
    var det = document.querySelector('details.tax-collapse');
    if (!det) return;
    if (window.matchMedia('(max-width: 600px)').matches) det.open = false;
    else det.open = true;
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', syncTaxCollapse);
  else syncTaxCollapse();
  window.addEventListener('resize', syncTaxCollapse);
})();
</script>
"""

TAX_SUMMARY = (
    '<summary>'
    '<span class="tax-collapse-title" data-vi="Bảng thuế chi tiết" '
    'data-en="Detailed tax breakdown">Bảng thuế chi tiết</span>'
    '<span class="tax-collapse-icon" aria-hidden="true">▾</span>'
    '</summary>'
)


def undo_comp_collapse(html: str) -> str:
    """Strip the mistargeted comp-table wrap added in the previous round."""
    if COMP_MARKER not in html:
        return html
    # Remove the CSS block.
    html = re.sub(
        r'\n/\* Compare-table collapse — table can be folded on mobile.*?/\*COMP-COLLAPSE-CSS\*/\n',
        '\n',
        html,
        flags=re.DOTALL,
    )
    # Remove the JS block.
    html = re.sub(
        r'\n<script>\s*/\* Compare-table collapse.*?COMP-COLLAPSE-JS \*/.*?</script>\n',
        '\n',
        html,
        flags=re.DOTALL,
    )
    # Unwrap the <details> back to plain <table class="comp-table">.
    html = re.sub(
        r'<!--COMP-COLLAPSE-->\n<details class="comp-collapse" open><summary>.*?</summary>(<table class="comp-table">.*?</table>)</details>',
        r'\1',
        html,
        flags=re.DOTALL,
    )
    return html


def add_tax_collapse(html: str) -> str:
    """Wrap §05 tax `.overview-grid` in a `<details class="tax-collapse">`."""
    if TAX_MARKER in html:
        return html

    # 1) Inject CSS once before </style>.
    if '/*TAX-COLLAPSE-CSS*/' not in html and '</style>' in html:
        html = html.replace('</style>', TAX_CSS + '\n</style>', 1)

    # 2) Wrap the overview-grid inside <section ... id="tax"> ... </section>.
    sec_pat = re.compile(
        r'(<section class="section" id="tax">)(.*?)(</section>)',
        re.DOTALL,
    )

    def section_repl(m):
        head, body, tail = m.group(1), m.group(2), m.group(3)
        # Inside the section body, wrap the first <div class="overview-grid"...>...</div>.
        grid_pat = re.compile(
            r'(<div class="overview-grid"[^>]*>)(.*?)(</div>\s*(?=<div class="info-box"|</section>))',
            re.DOTALL,
        )
        new_body, n = grid_pat.subn(
            lambda gm: (
                f'{TAX_MARKER}\n'
                f'<details class="tax-collapse" open>'
                f'{TAX_SUMMARY}'
                f'{gm.group(1)}{gm.group(2)}{gm.group(3)}'
                f'</details>'
            ),
            body,
            count=1,
        )
        return f'{head}{new_body}{tail}' if n else m.group(0)

    new_html, n = sec_pat.subn(section_repl, html, count=1)
    if n == 0 or TAX_MARKER not in new_html:
        return html

    # 3) Inject JS once before </body>.
    if 'TAX-COLLAPSE-JS' not in new_html:
        new_html = new_html.replace('</body>', TAX_JS + '\n</body>', 1)

    return new_html


def patch_one(path: Path, keep_comp: bool) -> str:
    """Return 'updated' / 'unchanged' / 'no-tax-section'."""
    html_before = path.read_text()
    html = html_before
    if not keep_comp:
        html = undo_comp_collapse(html)
    html = add_tax_collapse(html)
    if html == html_before:
        return 'unchanged'
    path.write_text(html)
    return 'updated'


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    keep_comp = '--keep-comp' in sys.argv
    files = []
    if args:
        for arg in args:
            files.extend(BROCHURE_DIR.glob(f'*{arg}*.html'))
    else:
        files = sorted(BROCHURE_DIR.glob('*.html'))
    files = [f for f in files if not f.name.startswith('NAC-BROCHURES')]
    files = [f for f in files if f.name != 'index.html']
    files = [f for f in files if 'RESIDENCE-INDEX' not in f.name]

    updated = unchanged = 0
    for f in files:
        result = patch_one(f, keep_comp)
        if result == 'updated':
            updated += 1
            print(f'  ✓ {f.name}')
        else:
            unchanged += 1
            print(f'  · {f.name}')

    print(f'\n{updated} updated, {unchanged} unchanged.')


if __name__ == '__main__':
    main()
