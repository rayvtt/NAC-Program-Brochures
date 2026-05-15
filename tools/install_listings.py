#!/usr/bin/env python3
"""One-off patcher: install Live Listings spotlight infra into brochures.

Copies (idempotently) into each brochure:
  1. Listings CSS block — extracted from turkey-cbi_8.html, inserted before </style>
  2. Desktop TOC entry (toc-item-spotlight) — between #investment and #process
  3. <!-- LISTINGS START --><!-- LISTINGS END --> markers + surrounding <hr>
     — between section 02 and section 03
  4. Mobile float-toc-panel entry — between the #investment and #process anchors

Turkey is included so the mobile-toc entry can be added to it too;
steps 1-3 are no-ops on Turkey because it's the canonical source.

After patching, run `python tools/apply_listings.py` to fill the markers
with live data from the Property Hub worker.

Idempotent: each step is independently guarded — re-running is safe.

Run:
    python tools/install_listings.py             # patch all 12 brochures
    python tools/install_listings.py portugal    # patch one (by alias)
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BROCHURE_DIR = ROOT / 'Brochures html'
TURKEY = BROCHURE_DIR / 'turkey-cbi_8.html'

# alias → filename. Mirrors sync_brochures.py BROCHURES dict.
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

TOC_ENTRY = (
    '      <li class="toc-item toc-item-spotlight">'
    '<a class="toc-link" href="#listings">'
    '<span class="toc-num">★ </span>BĐS đang mở bán</a></li>\n'
)

MARKERS_BLOCK = """    <!-- LISTINGS START -->
    <!-- LISTINGS END -->

    <hr class="divider">

"""

CSS_BLOCK_RE = re.compile(
    r'/\*\s*=+\s*\n\s*LIVE LISTINGS — Spotlight section between #02 and #03'
    r'.*?(?=\n\s*</style>)',
    re.DOTALL,
)

TOC_ANCHOR_RE = re.compile(
    r'(<li class="toc-item"><a class="toc-link" href="#investment">'
    r'[^<]*<[^>]+>[^<]*</[^>]+>[^<]*</a></li>\n)'
    r'(\s*<li class="toc-item"><a class="toc-link" href="#process">)'
)

PROCESS_BOUNDARY_RE = re.compile(
    r'(<hr class="divider">\n\n)(    <!-- 03 PROCESS -->)'
)

# Mobile float-toc-panel anchor — insert listings entry between the
# #investment item and the #process item. The onclick handler varies
# between brochures (closeFToc() in most, inline DOM call in some), so
# capture it and reuse so the new entry matches local style.
MOBILE_TOC_RE = re.compile(
    r'(<a href="#investment"(\s+onclick="[^"]*")>[^<]*</a>\n)'
    r'(\s*)(<a href="#process"\s+onclick="[^"]*">)'
)


def extract_listings_css():
    turkey_html = TURKEY.read_text(encoding='utf-8')
    m = CSS_BLOCK_RE.search(turkey_html)
    if not m:
        sys.exit('❌ LIVE LISTINGS CSS block not found in turkey-cbi_8.html')
    return m.group(0).rstrip() + '\n'


def patch_one(path, listings_css):
    """Each of the 3 pieces is inserted only if missing. Safe to re-run."""
    raw = path.read_bytes()
    crlf = b'\r\n' in raw
    doc = raw.decode('utf-8').replace('\r\n', '\n') if crlf else raw.decode('utf-8')
    original = doc
    did = []

    # 1. CSS — inject before </style>
    if 'LIVE LISTINGS — Spotlight' not in doc:
        if '</style>' not in doc:
            return None, 'no </style> tag found'
        doc = doc.replace('</style>', listings_css + '</style>', 1)
        did.append('CSS')

    # 2. Desktop TOC entry — between #investment and #process.
    # Match the <li> element (the CSS rule with the same class name will
    # exist after step 1, so a plain class-name substring check is unsafe).
    if 'class="toc-item toc-item-spotlight"' not in doc:
        if not TOC_ANCHOR_RE.search(doc):
            return None, 'TOC anchor (#investment + #process) not found'
        doc = TOC_ANCHOR_RE.sub(r'\1' + TOC_ENTRY + r'\2', doc, count=1)
        did.append('TOC')

    # 3. Markers — before the <!-- 03 PROCESS --> comment.
    # After insertion, the regex no longer matches (markers sit between the
    # hr and the comment), so this is naturally idempotent.
    if '<!-- LISTINGS START -->' not in doc:
        if not PROCESS_BOUNDARY_RE.search(doc):
            return None, 'section 02→03 boundary not found'
        doc = PROCESS_BOUNDARY_RE.sub(r'\1' + MARKERS_BLOCK + r'\2', doc, count=1)
        did.append('markers')

    # 4. Mobile float-toc-panel entry — between #investment and #process.
    # Check for the mobile-specific form (href + onclick), not the
    # desktop TOC link which also targets #listings.
    mobile_already = re.search(
        r'<a href="#listings"[^>]*onclick=', doc
    )
    if not mobile_already:
        m = MOBILE_TOC_RE.search(doc)
        if m:
            onclick_attr = m.group(2)   # e.g. ' onclick="closeFToc()"'
            indent       = m.group(3)
            entry = (f'{indent}<a href="#listings"{onclick_attr}>'
                     f'★ BĐS đang mở bán</a>\n')
            doc = MOBILE_TOC_RE.sub(r'\1' + entry + r'\4', doc, count=1)
            did.append('mobile-toc')

    if doc == original:
        return False, 'already fully patched'
    out = doc.replace('\n', '\r\n') if crlf else doc
    path.write_bytes(out.encode('utf-8'))
    return True, f'patched ({" + ".join(did)})'


def resolve_targets(args):
    if not args:
        return list(TARGETS.values())
    out = []
    for a in args:
        if a in TARGETS:
            out.append(TARGETS[a])
        elif a.endswith('.html'):
            out.append(a)
        else:
            print(f'⚠ unknown alias: {a} (valid: {", ".join(TARGETS)})', file=sys.stderr)
    return out


def main():
    listings_css = extract_listings_css()
    targets = resolve_targets(sys.argv[1:])
    patched = skipped = failed = 0
    for fname in targets:
        path = BROCHURE_DIR / fname
        if not path.exists():
            print(f'  ✗ {fname}: file not found')
            failed += 1
            continue
        ok, msg = patch_one(path, listings_css)
        if ok is True:
            mark = '✓'; patched += 1
        elif ok is False:
            mark = '–'; skipped += 1
        else:
            mark = '✗'; failed += 1
        print(f'  {mark} {fname}: {msg}')
    print(f'\n{patched} patched, {skipped} skipped, {failed} failed.')


if __name__ == '__main__':
    main()
