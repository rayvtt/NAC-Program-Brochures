"""Apply the refined sidebar CTA pill design across all 12 brochures.

Replaces:
- The CSS rules for ``.toc-cta-mini`` / ``.toc-cta-mini a`` / ``.toc-cta-mini a:hover``
- The HTML ``<div class="toc-cta-mini">…</div>`` block in each ``<aside class="toc">``

Mirrors the cream-glass aesthetic of the mobile ``.nac-tools`` floating
CTA bar — same colour-coded chips (calendar / WhatsApp / NAC Index /
So Sánh) but stacked vertically under the Mục Lục so it sits sticky in
the left sidebar.

Idempotent — re-runs are no-ops once the new block is in place.

Run:
    python tools/refine_sidebar_cta.py             # all 12
    python tools/refine_sidebar_cta.py turkey      # one alias
    python tools/refine_sidebar_cta.py --dry-run   # preview
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BROCHURES_DIR = ROOT / "Brochures html"

OLD_CSS_RE = re.compile(
    r'\.toc-cta-mini\s*\{[^}]*\}\s*'
    r'\.toc-cta-mini\s*a\s*\{[^}]*\}\s*'
    r'\.toc-cta-mini\s*a:hover\s*\{[^}]*\}',
    re.DOTALL,
)

NEW_CSS = """.toc-cta-mini {
  margin-top: 24px;
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  background: rgba(250,245,232,.94);
  backdrop-filter: blur(22px) saturate(180%);
  -webkit-backdrop-filter: blur(22px) saturate(180%);
  border: 1px solid rgba(125,90,30,.10);
  border-radius: 14px;
  box-shadow: 0 10px 30px rgba(15,26,54,.08), 0 0 0 1px rgba(15,26,54,.03), inset 0 1px 0 rgba(255,250,240,.95);
  font-family: 'Be Vietnam Pro', sans-serif;
}
.toc-cta-mini a {
  display: flex; align-items: center; gap: 9px;
  padding: 8px 10px;
  font-size: 11.5px; font-weight: 600;
  color: #14181f; text-decoration: none;
  background: transparent; border-radius: 8px;
  text-align: left;
  transition: background .15s ease, color .15s ease;
}
.toc-cta-mini a svg { flex-shrink: 0; display: block; }
.toc-cta-mini a:hover { background: rgba(255,255,255,0.78); }
.toc-cta-mini .tc-cal  { color: #5b3aa8; }
.toc-cta-mini .tc-cal:hover  { color: #3d2480; background: rgba(91,58,168,.10); }
.toc-cta-mini .tc-wa   { color: #1eb955; }
.toc-cta-mini .tc-wa:hover   { color: #138a3e; background: rgba(30,185,85,.12); }
.toc-cta-mini .tc-idx  { color: #c4922c; }
.toc-cta-mini .tc-idx:hover  { color: #9a701f; background: rgba(196,146,60,.14); }
.toc-cta-mini .tc-cmp  { color: #d97c44; }
.toc-cta-mini .tc-cmp:hover  { color: #a85b28; background: rgba(217,124,68,.14); }"""

# Match the whole sidebar CTA HTML block — any whitespace, any inner content
OLD_HTML_RE = re.compile(
    r'<div class="toc-cta-mini">[\s\S]*?</div>\s*(?=</aside>)',
    re.DOTALL,
)

NEW_HTML = '''<div class="toc-cta-mini">
      <a class="tc-cal" href="https://calendar.app.google/gnbtNBTBDKuHUasw7" target="_blank" rel="noopener" aria-label="Tư Vấn 30 phút">
        <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3.5" y="5" width="17" height="15.5" rx="2"/><path d="M3.5 9.5h17M8 3.5v3M16 3.5v3"/><circle cx="12" cy="14" r="1.2" fill="currentColor"/></svg>
        <span data-vi="Tư Vấn 30''" data-en="Book 30''">Tư Vấn 30''</span>
      </a>
      <a class="tc-wa" href="https://wa.me/447388646000" target="_blank" rel="noopener" aria-label="WhatsApp NAC">
        <svg viewBox="0 0 24 24" width="15" height="15" fill="currentColor" aria-hidden="true"><path d="M19.05 4.91A9.816 9.816 0 0 0 12.04 2c-5.46 0-9.91 4.45-9.91 9.91 0 1.75.46 3.45 1.32 4.95L2.05 22l5.25-1.38a9.9 9.9 0 0 0 4.74 1.21h.01c5.46 0 9.91-4.45 9.91-9.91 0-2.65-1.03-5.14-2.91-7.01zm-7.01 15.24h-.01a8.21 8.21 0 0 1-4.19-1.15l-.3-.18-3.12.82.83-3.04-.2-.32a8.24 8.24 0 0 1-1.26-4.38c0-4.54 3.7-8.24 8.24-8.24 2.2 0 4.27.86 5.82 2.42a8.18 8.18 0 0 1 2.41 5.83c.02 4.54-3.68 8.24-8.22 8.24zm4.52-6.16c-.25-.12-1.47-.72-1.69-.81-.23-.08-.39-.12-.56.12-.17.25-.64.81-.78.97-.14.17-.29.19-.54.06-.25-.12-1.05-.39-1.99-1.23-.74-.66-1.23-1.47-1.38-1.72-.14-.25-.02-.38.11-.51.11-.11.25-.29.37-.43.12-.14.17-.25.25-.41.08-.17.04-.31-.02-.43-.06-.12-.56-1.34-.76-1.84-.2-.48-.41-.42-.56-.43-.14-.01-.31-.01-.48-.01-.17 0-.43.06-.66.31-.22.25-.86.85-.86 2.07 0 1.22.89 2.4 1.01 2.56.12.17 1.75 2.67 4.23 3.74.59.26 1.05.41 1.41.52.59.19 1.13.16 1.56.1.48-.07 1.47-.6 1.67-1.18.21-.58.21-1.07.14-1.18s-.21-.16-.46-.28z"/></svg>
        <span>WhatsApp</span>
      </a>
      <a class="tc-idx" href="https://nomadassetcollective.com/nac-residence-index/" target="_blank" rel="noopener" aria-label="NAC Residence Index">
        <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a13.5 13.5 0 0 1 0 18M12 3a13.5 13.5 0 0 0 0 18"/></svg>
        <span>NAC Index</span>
      </a>
      <a class="tc-cmp" href="https://nomadassetcollective.com/so-sanh/" target="_blank" rel="noopener" aria-label="So Sánh chương trình">
        <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3v18M5 8h14l-3 6h-8L5 8zM2 20h7M15 20h7"/></svg>
        <span data-vi="So Sánh" data-en="Compare">So Sánh</span>
      </a>
    </div>
  '''


def process_file(path: Path, dry_run: bool = False) -> dict:
    text = path.read_text(encoding="utf-8")
    original = text
    changes = {"css": 0, "html": 0}

    # CSS: replace if the old 3-rule pattern exists; skip if already migrated.
    if "border-radius: 14px;" not in text or ".tc-cal" not in text:
        m = OLD_CSS_RE.search(text)
        if m:
            text = text[:m.start()] + NEW_CSS + text[m.end():]
            changes["css"] = 1

    # HTML: replace the whole sidebar block. Idempotent because the new
    # block contains 'tc-cal' which the old one never did.
    if "tc-cal" not in original.split("toc-cta-mini")[1].split("</div>")[0] if "toc-cta-mini" in original else False:
        pass  # handled below
    m = OLD_HTML_RE.search(text)
    if m:
        block = text[m.start():m.end()]
        if "tc-cal" not in block:
            text = text[:m.start()] + NEW_HTML + text[m.end():]
            changes["html"] = 1

    if text == original or dry_run:
        return changes
    path.write_text(text, encoding="utf-8")
    return changes


def main() -> int:
    args = sys.argv[1:]
    dry_run = "--dry-run" in args
    args = [a for a in args if not a.startswith("--")]

    if args:
        aliases = [a.lower() for a in args]
        files = [
            p for p in sorted(BROCHURES_DIR.glob("*.html"))
            if any(p.name.lower().startswith(a) for a in aliases)
        ]
    else:
        files = sorted(BROCHURES_DIR.glob("*.html"))

    skip = {"NAC-BROCHURES-OVERVIEW.html", "NAC-RESIDENCE-INDEX.html"}
    totals = {"css": 0, "html": 0}

    for f in files:
        if f.name in skip:
            continue
        c = process_file(f, dry_run=dry_run)
        if any(c.values()):
            print(f"{'[dry]' if dry_run else '✓'} {f.name}: css={c['css']}, html={c['html']}")
        for k, v in c.items():
            totals[k] += v

    print(
        f"\nDone — css={totals['css']}, html={totals['html']} "
        f"({'dry-run' if dry_run else 'applied'})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
