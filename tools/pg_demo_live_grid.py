#!/usr/bin/env python3
"""§03 Live Demo polish:
  - drop the leftover last-child full-width rule so all 6 demos sit in a clean 2×3 grid (3 per column)
  - add a flashing green LIVE chip to every demo frame

Idempotent. WP-safe (no inline handlers / \\" escapes).
"""
import sys
from pathlib import Path

HTML = Path(__file__).resolve().parent.parent / "Brochures html" / "NAC-PARTNERS.html"
html = HTML.read_text(encoding="utf-8")
if ".snap-live{" in html:
    sys.exit("already applied — .snap-live present")

# 1) remove the last-child full-width rule (was for the old 5-frame odd layout)
lastchild = '@media(min-width:861px){.snap-grid .snap:last-child{grid-column:1/-1}.snap-grid .snap:last-child .snap-frame{height:360px}.snap-grid .snap:last-child .snap-frame iframe{height:720px}}'
assert lastchild in html, "last-child rule not found"
html = html.replace(lastchild + "\n", "", 1)

# 2) LIVE-chip CSS — appended after the snap-pitch rule
anchor = '.snap-pitch{margin-top:10px;font-size:12.5px;color:var(--blue);background:rgba(24,0,173,.05);border-left:3px solid var(--blue);padding:9px 13px;border-radius:0 8px 8px 0;font-style:italic;line-height:1.55}'
assert anchor in html
css = anchor + """
.snap-live{position:absolute;top:10px;left:10px;z-index:3;display:inline-flex;align-items:center;gap:6px;background:rgba(255,255,255,.94);border:1px solid rgba(22,163,74,.35);border-radius:999px;padding:4px 10px 4px 8px;font-size:10px;font-weight:800;letter-spacing:1px;text-transform:uppercase;color:#15a34a;box-shadow:0 2px 8px rgba(0,0,0,.12);pointer-events:none;animation:snapLiveBlink 2s ease-in-out infinite}
.snap-live-dot{width:7px;height:7px;border-radius:50%;background:#22c55e;animation:snapLivePing 1.6s ease-out infinite}
@keyframes snapLivePing{0%{box-shadow:0 0 0 0 rgba(34,197,94,.55)}70%{box-shadow:0 0 0 7px rgba(34,197,94,0)}100%{box-shadow:0 0 0 0 rgba(34,197,94,0)}}
@keyframes snapLiveBlink{0%,100%{opacity:1}50%{opacity:.62}}
@media(prefers-reduced-motion:reduce){.snap-live,.snap-live-dot{animation:none}}"""
html = html.replace(anchor, css, 1)

# 3) insert the chip into every demo frame (shared data-copy key → all 6 stay in sync + editable)
chip = ('<div class="snap-frame"><span class="snap-live"><span class="snap-live-dot"></span>'
        '<span data-copy="pg-live" data-vi="TRỰC TIẾP" data-en="LIVE">TRỰC TIẾP</span></span>')
n = html.count('<div class="snap-frame">')
assert n == 6, f"expected 6 demo frames, found {n}"
html = html.replace('<div class="snap-frame">', chip, n)

HTML.write_text(html, encoding="utf-8")
print(f"live chips added to {n} demos; 2×3 grid restored")
