"""Force horizontal bar charts (indexAxis: 'y') to LEFT-align their
Y-axis category labels across all brochures.

By default, Chart.js right-aligns Y-axis labels so they sit close to
the chart bars. With variable-length country names this creates an
uneven left margin (short labels far from chart, long labels close).
User wants every label to start at the same X position so the bar
chart looks orderly.

Solution: a small inline <script> at the end of each brochure that
walks every canvas, detects charts with `indexAxis: 'y'`, and sets:
  ticks.crossAlign = 'far'    // push labels to far edge of axis
  ticks.align      = 'center' // vertical centering on tick

Idempotent — guarded by /* CHART-Y-LEFT-ALIGN */ marker.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BROCHURE_DIR = ROOT / 'Brochures html'
MARKER = '/* CHART-Y-LEFT-ALIGN */'

SNIPPET = """
<script>
/* CHART-Y-LEFT-ALIGN */
/* Force LEFT-aligned (uniform indent) Y-axis labels on horizontal
   bar charts so the legends queue up at the same X position. */
(function () {
  function applyLeftAlign() {
    if (typeof Chart === 'undefined') { setTimeout(applyLeftAlign, 100); return; }
    document.querySelectorAll('canvas').forEach(function (canvas) {
      var c = Chart.getChart(canvas);
      if (!c) return;
      var opts = c.config && c.config.options;
      if (!opts || opts.indexAxis !== 'y') return;
      opts.scales = opts.scales || {};
      opts.scales.y = opts.scales.y || {};
      opts.scales.y.ticks = opts.scales.y.ticks || {};
      opts.scales.y.ticks.crossAlign = 'far';
      opts.scales.y.ticks.align = 'center';
      c.update();
    });
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { setTimeout(applyLeftAlign, 250); });
  } else {
    setTimeout(applyLeftAlign, 250);
  }
})();
</script>
"""


def patch_one(path: Path) -> bool:
    html = path.read_text()
    if MARKER in html:
        return False
    if '</body>' not in html:
        return False
    new_html = html.replace('</body>', SNIPPET + '\n</body>', 1)
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
