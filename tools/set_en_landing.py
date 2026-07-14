#!/usr/bin/env python3
"""Make English the landing language on every brochure-family page.

Injects a small WP-safe script (marker: EN-LANDING-DEFAULT) right before
</body> on each page. On load it switches the page to EN unless the visitor
deep-links ?lang=vi. Idempotent — pages already carrying the marker are
skipped; second run reports 0.

Per-page strategy:
  - 18 country brochures ..... click #btn-en (fires the bound setLang AND the
                               chart-translator click listener, so canvas
                               labels flip too)
  - NAC-BROCHURES-OVERVIEW ... bind setLang to the toggle via addEventListener
                               (its buttons only had inline onclick, which WP
                               KSES strips) + call setLang('en')
  - nac-quiz-tu-van .......... click #btn-en (bound via on())
  - NAC-PARTNERS ............. click #navLangEn (addEventListener-bound)
  - NAC-RESIDENCE-INDEX ...... click #bEN (delegated data-nac-act handler)

WP-safety: no inline handlers, no backslashes anywhere in the snippet.

Usage:
  python tools/set_en_landing.py            # all pages
  python tools/set_en_landing.py greece     # one page (substring match)
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / 'Brochures html'
MARKER = 'EN-LANDING-DEFAULT'

BROCHURES = [
    'antigua-cbi.html', 'australia-rbi.html', 'cyprus-rbi_3_3.html',
    'greece-rbi_1_2.html', 'italy-investor.html', 'malaysia-mm2h.html',
    'malta-rbi_1_3.html', 'montenegro-rbi.html', 'nauru-cbi.html',
    'newzealand-rbi_1 (3).html', 'panama-rbi_.html', 'portugal-gv.html',
    'spain-gv.html', 'stkitts-nevis.html', 'thailand-rbi_1 (2).html',
    'turkey-cbi_8.html', 'uae-rbi_1_7.html', 'uk-rbi_1 (2).html',
]

CLICK_TMPL = """<script>
/* {marker} — land in English unless the visitor deep-links ?lang=vi */
(function () {{
  function goEn() {{
    try {{
      if (new URLSearchParams(location.search).get('lang') === 'vi') return;
    }} catch (e) {{}}
    var b = document.getElementById('{btn}');
    if (b) b.click();
  }}
  if (document.readyState === 'loading') {{
    document.addEventListener('DOMContentLoaded', function () {{ setTimeout(goEn, 60); }});
  }} else {{
    setTimeout(goEn, 60);
  }}
}})();
</script>
"""

OVERVIEW_SNIPPET = """<script>
/* EN-LANDING-DEFAULT — land in English unless ?lang=vi. Also binds the
   VI/EN toggle via addEventListener: the buttons only carried inline
   onclick, which WordPress KSES strips on the live page. */
(function () {
  function init() {
    if (typeof setLang !== 'function') return;
    var vi = document.getElementById('btn-vi');
    var en = document.getElementById('btn-en');
    if (vi && !vi._nacLangBound) { vi._nacLangBound = true; vi.addEventListener('click', function () { setLang('vi'); }); }
    if (en && !en._nacLangBound) { en._nacLangBound = true; en.addEventListener('click', function () { setLang('en'); }); }
    try {
      if (new URLSearchParams(location.search).get('lang') === 'vi') return;
    } catch (e) {}
    setLang('en');
    if (en) en.click();
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { setTimeout(init, 60); });
  } else {
    setTimeout(init, 60);
  }
})();
</script>
"""

PAGES = (
    [(f, CLICK_TMPL.format(marker=MARKER, btn='btn-en')) for f in BROCHURES] + [
    ('NAC-BROCHURES-OVERVIEW.html', OVERVIEW_SNIPPET),
    ('nac-quiz-tu-van.html', CLICK_TMPL.format(marker=MARKER, btn='btn-en')),
    ('NAC-PARTNERS.html', CLICK_TMPL.format(marker=MARKER, btn='navLangEn')),
    ('NAC-RESIDENCE-INDEX.html', CLICK_TMPL.format(marker=MARKER, btn='bEN')),
])


def main():
    only = sys.argv[1].lower() if len(sys.argv) > 1 else None
    changed = 0
    for fname, snippet in PAGES:
        if only and only not in fname.lower():
            continue
        path = ROOT / fname
        if not path.exists():
            print(f'  !! missing: {fname}')
            continue
        html = path.read_text(encoding='utf-8')
        if MARKER in html:
            print(f'  = already set: {fname}')
            continue
        idx = html.rfind('</body>')
        if idx == -1:
            print(f'  !! no </body>: {fname}')
            continue
        path.write_text(html[:idx] + snippet + html[idx:], encoding='utf-8')
        print(f'  + injected: {fname}')
        changed += 1
    print(f'{changed} page(s) updated')


if __name__ == '__main__':
    main()
