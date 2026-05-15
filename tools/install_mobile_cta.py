#!/usr/bin/env python3
"""Install the mobile sticky CTA bar across all brochures.

Mobile-only fixed-bottom bar with 3 icon links: WhatsApp · Property Hub · Blog.
Adds:
  1. CSS block (inside the brochure's <style>) — mobile-only styling.
  2. HTML block (just before </body>) — the <div class="nac-mobile-cta"> bar.

Idempotent: skips files that already contain MOBILE_CTA_MARKER.

Run:
    python tools/install_mobile_cta.py              # patch all 12 brochures
    python tools/install_mobile_cta.py portugal     # patch one
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

MOBILE_CTA_MARKER = 'MOBILE CTA BAR'

CSS_BLOCK = '''
/* ============================================================
   MOBILE CTA BAR — sticky bottom bar (mobile only)
   3 icon links: WhatsApp · Property Hub · Blog.
   Auto-themes via var(--country) / var(--country-lt).
   ============================================================ */
.nac-mobile-cta { display: none; }

@media (max-width: 720px) {
  .nac-mobile-cta {
    display: flex;
    position: fixed;
    bottom: 0; left: 0; right: 0;
    background: rgba(255,255,255,0.97);
    -webkit-backdrop-filter: blur(8px);
    backdrop-filter: blur(8px);
    border-top: 1px solid var(--border, #e5e7eb);
    padding: 10px 16px calc(10px + env(safe-area-inset-bottom, 0px));
    justify-content: space-around;
    align-items: center;
    gap: 12px;
    z-index: 90;
    box-shadow: 0 -2px 12px rgba(0,0,0,0.08);
  }
  .nac-mobile-cta a {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 48px; height: 48px;
    border-radius: 999px;
    background: var(--country-lt, #f3f4f6);
    color: var(--country, #1f2937);
    text-decoration: none;
    transition: transform 0.15s ease, background 0.15s ease, color 0.15s ease;
  }
  .nac-mobile-cta a:active {
    transform: scale(0.94);
    background: var(--country, #1f2937);
    color: #fff;
  }
  .nac-mobile-cta a svg { width: 22px; height: 22px; display: block; }
  .nac-mobile-cta a.cta-wa { background: #25D366; color: #fff; }
  .nac-mobile-cta a.cta-wa:active { background: #1da851; color: #fff; }

  /* Keep the float-toc-btn visible above the new CTA bar. */
  .float-toc-btn { bottom: 84px !important; }

  /* Prevent the bar from covering page content on scroll-end. */
  body { padding-bottom: 80px; }
}
'''

HTML_BLOCK = '''
<!-- MOBILE CTA BAR — sticky bottom on mobile only (PB template; installed by tools/install_mobile_cta.py) -->
<div class="nac-mobile-cta" role="navigation" aria-label="Quick actions">
  <a class="cta-wa" href="https://wa.me/447388646000" target="_blank" rel="noopener" aria-label="WhatsApp" title="WhatsApp">
    <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.297-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 0 1-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 0 1-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 0 1 2.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0 0 12.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 0 0 5.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893A11.821 11.821 0 0 0 20.464 3.488"/></svg>
  </a>
  <a href="https://nomadassetcollective.com/property-hub/" target="_blank" rel="noopener" aria-label="Property Hub" title="Property Hub">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 21V9.5L12 3l9 6.5V21"/><path d="M9 21v-7h6v7"/><path d="M3 21h18"/></svg>
  </a>
  <a href="https://blog.nomadassetcollective.com/" target="_blank" rel="noopener" aria-label="Blog" title="Blog">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 4h12a2 2 0 0 1 2 2v14H6a2 2 0 0 1-2-2z"/><path d="M18 6h1a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2h-1"/><line x1="8" y1="9"  x2="14" y2="9"/><line x1="8" y1="13" x2="14" y2="13"/><line x1="8" y1="17" x2="11" y2="17"/></svg>
  </a>
</div>
'''


def patch_one(path):
    raw = path.read_bytes()
    crlf = b'\r\n' in raw
    doc = raw.decode('utf-8').replace('\r\n', '\n') if crlf else raw.decode('utf-8')
    original = doc
    did = []

    # 1. CSS — inject before </style>
    if MOBILE_CTA_MARKER not in doc:
        if '</style>' not in doc:
            return None, 'no </style> tag found'
        doc = doc.replace('</style>', CSS_BLOCK + '\n</style>', 1)
        did.append('CSS')

    # 2. HTML — inject before </body>
    if 'class="nac-mobile-cta"' not in doc:
        if '</body>' not in doc:
            return None, 'no </body> tag found'
        doc = doc.replace('</body>', HTML_BLOCK + '\n</body>', 1)
        did.append('HTML')

    if doc == original:
        return False, 'already fully patched'
    out = doc.replace('\n', '\r\n') if crlf else doc
    path.write_bytes(out.encode('utf-8'))
    return True, f'patched ({" + ".join(did)})'


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
