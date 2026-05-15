#!/usr/bin/env python3
"""Install / refresh the mobile floating CTA pill across all brochures.

A refined cream/light floating pill at the bottom-center on mobile,
with three quick links: WhatsApp · Property Hub · Blog. Icon-only
when collapsed; expands to icon + label on hover (desktop) or tap
(touch).

Components installed:
  1. CSS block (inside the brochure's <style>) — the .nac-tools pill rules.
  2. HTML block (just before </body>) — the <div class="nac-tools"> pill.
  3. JS snippet (just before </body>) — wireCollapsePill() tap handler.

Idempotency:
  - Strips legacy v1 (.nac-mobile-cta strip-style bar) AND legacy v2
    (dark Nobu-style pill) before installing the current cream pill,
    so re-runs after a redesign end up clean rather than stacked.
  - The new install is itself guarded: if .nac-tools already exists
    AND uses the current marker, the step is a no-op.

Run:
    python tools/install_mobile_cta.py              # patch all 12 brochures
    python tools/install_mobile_cta.py portugal     # patch one (by alias)
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BROCHURE_DIR = ROOT / 'Brochures html'

TARGETS = {
    'portugal':   'portugal-gv.html',
    'greece':     'greece-rbi_1_2.html',
    'cyprus':     'cyprus-rbi_3_3.html',
    'turkey':     'turkey-cbi_8.html',
    'uae':        'uae-rbi_1_7.html',
    'uk':         'uk-rbi_1 (2).html',
    'malta':      'malta-rbi_1_3.html',
    'stkitts':    'stkitts-nevis.html',
    'thailand':   'thailand-rbi_1 (2).html',
    'newzealand': 'newzealand-rbi_1 (3).html',
    'panama':     'panama-rbi_.html',
    'malaysia':   'malaysia-mm2h.html',
}

# ---- Legacy variants to strip ----------------------------------------------

# v1: full-width strip bar (class .nac-mobile-cta).
LEGACY_V1_CSS_RE = re.compile(
    r'\n?/\*\s*=+\s*\n\s*MOBILE CTA BAR.*?\n}\n',
    re.DOTALL,
)
LEGACY_V1_CSS_NOHEAD_RE = re.compile(
    r'\n?\.nac-mobile-cta\s*\{[^}]*\}\s*\n\s*@media \(max-width: 720px\) \{.*?\n}\n',
    re.DOTALL,
)
LEGACY_V1_HTML_RE = re.compile(
    r'\n?<!-- MOBILE CTA BAR — sticky bottom on mobile only.*?</div>\n?',
    re.DOTALL,
)

# v2: dark Nobu-style pill (.nac-tools, original install).
LEGACY_V2_CSS_RE = re.compile(
    r'\n?/\*\s*=+\s*\n\s*NAC TOOLS PILL — floating bottom-center pill \(Nobu PDP style\).*?\n}\n',
    re.DOTALL,
)
LEGACY_V2_HTML_RE = re.compile(
    r'\n?<!-- NAC TOOLS PILL — floating bottom CTA \(mobile only; mirrors PH PDP style.*?</script>\n?',
    re.DOTALL,
)

# ---- Current install: refined cream pill -----------------------------------

CSS_MARKER = 'NAC TOOLS PILL — floating bottom-center pill (refined cream)'
HTML_MARKER = 'NAC TOOLS PILL — floating bottom CTA (mobile only; refined cream'

CSS_BLOCK = '''
/* ============================================================
   NAC TOOLS PILL — floating bottom-center pill (refined cream)
   Mobile-only. Collapses to icon-only; expands on hover/tap.
   Light glass background to feel airy against brochure body.
   ============================================================ */
.nac-tools { display:none; }

@media (max-width: 720px) {
  .nac-tools {
    position:fixed; bottom:1.1rem; left:50%; transform:translateX(-50%); z-index:80;
    display:flex; align-items:center; gap:.2rem;
    padding:.35rem .4rem;
    background:rgba(250,245,232,.94);
    backdrop-filter:blur(22px) saturate(180%);
    -webkit-backdrop-filter:blur(22px) saturate(180%);
    border:1px solid rgba(125,90,30,.10);
    border-radius:100px;
    box-shadow:
      0 10px 30px rgba(15,26,54,.10),
      0 0 0 1px rgba(15,26,54,.03),
      inset 0 1px 0 rgba(255,250,240,.95);
    font-family: 'Be Vietnam Pro', sans-serif;
  }
  .nac-tool {
    display:inline-flex; align-items:center; gap:0;
    padding:.5rem .55rem;
    border-radius:100px;
    font-size:.72rem; font-weight:600;
    color:#14181f;
    text-decoration:none;
    background:transparent; border:none; cursor:pointer;
    white-space:nowrap;
    transition:gap .28s cubic-bezier(.4,0,.2,1),
               padding .28s cubic-bezier(.4,0,.2,1),
               color .2s ease, background .2s ease;
  }
  .nac-tool svg { flex-shrink:0; display:block; }
  .nac-tool-txt {
    display:inline-block; max-width:0; opacity:0; overflow:hidden;
    transform:translateX(-4px);
    transition:max-width .28s cubic-bezier(.4,0,.2,1),
               opacity .22s ease,
               transform .28s cubic-bezier(.4,0,.2,1);
  }
  .nac-tools.is-open .nac-tool { gap:.4rem; padding:.5rem .85rem; }
  .nac-tools.is-open .nac-tool-txt { max-width:100px; opacity:1; transform:translateX(0); }

  /* Color-coded buttons (light-theme values) */
  .nac-tool--wa    { color:#1eb955; }
  .nac-tool--wa:hover, .nac-tool--wa:active   { color:#138a3e; background:rgba(30,185,85,.12); }
  .nac-tool--hub   { color:#c4922c; }
  .nac-tool--hub:hover, .nac-tool--hub:active { color:#9a701f; background:rgba(196,146,60,.14); }
  .nac-tool--blog  { color:#d97c44; }
  .nac-tool--blog:hover, .nac-tool--blog:active { color:#a85b28; background:rgba(217,124,68,.14); }

  /* Push float-toc-btn up so the pill doesn't crowd it */
  .float-toc-btn { bottom: 84px !important; }

  /* Give the body bottom breathing room */
  body { padding-bottom: 80px; }
}
'''

HTML_BLOCK = '''
<!-- NAC TOOLS PILL — floating bottom CTA (mobile only; refined cream; installed by tools/install_mobile_cta.py) -->
<div class="nac-tools">
  <a href="https://wa.me/447388646000" target="_blank" rel="noopener" class="nac-tool nac-tool--wa" aria-label="WhatsApp">
    <svg viewBox="0 0 24 24" width="15" height="15" fill="currentColor" aria-hidden="true"><path d="M19.05 4.91A9.816 9.816 0 0 0 12.04 2c-5.46 0-9.91 4.45-9.91 9.91 0 1.75.46 3.45 1.32 4.95L2.05 22l5.25-1.38a9.9 9.9 0 0 0 4.74 1.21h.01c5.46 0 9.91-4.45 9.91-9.91 0-2.65-1.03-5.14-2.91-7.01zm-7.01 15.24h-.01a8.21 8.21 0 0 1-4.19-1.15l-.3-.18-3.12.82.83-3.04-.2-.32a8.24 8.24 0 0 1-1.26-4.38c0-4.54 3.7-8.24 8.24-8.24 2.2 0 4.27.86 5.82 2.42a8.18 8.18 0 0 1 2.41 5.83c.02 4.54-3.68 8.24-8.22 8.24zm4.52-6.16c-.25-.12-1.47-.72-1.69-.81-.23-.08-.39-.12-.56.12-.17.25-.64.81-.78.97-.14.17-.29.19-.54.06-.25-.12-1.05-.39-1.99-1.23-.74-.66-1.23-1.47-1.38-1.72-.14-.25-.02-.38.11-.51.11-.11.25-.29.37-.43.12-.14.17-.25.25-.41.08-.17.04-.31-.02-.43-.06-.12-.56-1.34-.76-1.84-.2-.48-.41-.42-.56-.43-.14-.01-.31-.01-.48-.01-.17 0-.43.06-.66.31-.22.25-.86.85-.86 2.07 0 1.22.89 2.4 1.01 2.56.12.17 1.75 2.67 4.23 3.74.59.26 1.05.41 1.41.52.59.19 1.13.16 1.56.1.48-.07 1.47-.6 1.67-1.18.21-.58.21-1.07.14-1.18s-.21-.16-.46-.28z"/></svg>
    <span class="nac-tool-txt">WhatsApp</span>
  </a>
  <a href="https://nomadassetcollective.com/property-hub/" target="_blank" rel="noopener" class="nac-tool nac-tool--hub" aria-label="Property Hub">
    <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 11l9-8 9 8"/><path d="M5 9v11h14V9"/><path d="M10 20v-6h4v6"/></svg>
    <span class="nac-tool-txt">Property Hub</span>
  </a>
  <a href="https://blog.nomadassetcollective.com/" target="_blank" rel="noopener" class="nac-tool nac-tool--blog" aria-label="Blog">
    <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 20h9M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>
    <span class="nac-tool-txt">Blog</span>
  </a>
</div>
<script>
/* tap-to-expand for touch devices; hover-to-expand handled by CSS */
(function(){
  var el = document.querySelector('.nac-tools');
  if (!el) return;
  if (!window.matchMedia('(hover: none)').matches) return;
  el.addEventListener('click', function(e){
    if (!el.classList.contains('is-open')) {
      e.preventDefault();
      e.stopPropagation();
      el.classList.add('is-open');
    }
  }, true);
  document.addEventListener('click', function(e){
    if (!el.contains(e.target)) el.classList.remove('is-open');
  });
})();
</script>
'''


def patch_one(path):
    raw = path.read_bytes()
    crlf = b'\r\n' in raw
    doc = raw.decode('utf-8').replace('\r\n', '\n') if crlf else raw.decode('utf-8')
    original = doc
    did = []

    # Strip legacy variants (v1 strip-bar + v2 dark pill)
    for rx, label in [
        (LEGACY_V1_CSS_RE,        'v1 CSS'),
        (LEGACY_V1_CSS_NOHEAD_RE, 'v1 CSS (nohead)'),
        (LEGACY_V1_HTML_RE,       'v1 HTML'),
        (LEGACY_V2_CSS_RE,        'v2 CSS'),
        (LEGACY_V2_HTML_RE,       'v2 HTML'),
    ]:
        new = rx.sub('', doc)
        if new != doc:
            did.append(f'stripped {label}')
            doc = new

    # Install current cream pill
    if CSS_MARKER not in doc:
        if '</style>' not in doc:
            return None, 'no </style> tag'
        doc = doc.replace('</style>', CSS_BLOCK + '\n</style>', 1)
        did.append('CSS')
    if HTML_MARKER not in doc:
        if '</body>' not in doc:
            return None, 'no </body> tag'
        doc = doc.replace('</body>', HTML_BLOCK + '\n</body>', 1)
        did.append('HTML+JS')

    if doc == original:
        return False, 'already in target state'
    out = doc.replace('\n', '\r\n') if crlf else doc
    path.write_bytes(out.encode('utf-8'))
    return True, f'patched ({", ".join(did)})'


def main():
    args = sys.argv[1:]
    if not args:
        targets = list(TARGETS.values())
    else:
        targets = [TARGETS[a] for a in args if a in TARGETS]
    patched = skipped = failed = 0
    for fname in targets:
        path = BROCHURE_DIR / fname
        if not path.exists():
            print(f'  ✗ {fname}: not found')
            failed += 1
            continue
        ok, msg = patch_one(path)
        if ok is True:
            mark, patched = '✓', patched + 1
        elif ok is False:
            mark, skipped = '–', skipped + 1
        else:
            mark, failed = '✗', failed + 1
        print(f'  {mark} {fname}: {msg}')
    print(f'\n{patched} patched, {skipped} skipped, {failed} failed.')


if __name__ == '__main__':
    main()
