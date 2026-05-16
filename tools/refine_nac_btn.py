"""Finishing touches on the NAC consultation footer block:

1. Rewire the **Book a Free Consultation / Đặt Lịch Tư Vấn** button to
   Google Calendar. This targets specifically the ``<a class="nac-btn"``
   anchor inside the dark NAC consultation footer that still pointed at
   ``tu-van-nhanh/`` — that's the only ``nac-btn`` class instance in
   each brochure (the navbar / sections use ``cta-btn-primary`` instead).

2. Make the WhatsApp **icon** brand green (#25D366) while leaving the
   surrounding box untouched. Replaces ``fill:#fff`` and
   ``fill:currentColor`` inside any inline SVG that sits in a
   ``.nac-btn-wa`` anchor.

Idempotent — re-running with no upstream changes is a no-op.

Run:
    python tools/refine_nac_btn.py             # all brochures
    python tools/refine_nac_btn.py turkey      # one alias
    python tools/refine_nac_btn.py --dry-run
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BROCHURES_DIR = ROOT / "Brochures html"

TVN = "https://nomadassetcollective.com/tu-van-nhanh/"
GOOGLE_CAL = "https://calendar.app.google/gnbtNBTBDKuHUasw7"

# Anchor that uses class="nac-btn" (not cta-btn-primary, not nac-btn-wa)
# pointing at tu-van-nhanh. Tolerate any extra attrs.
NAC_BTN_RE = re.compile(
    r'(<a\s+class="nac-btn"[^>]*?href=")'
    + re.escape(TVN)
    + r'(")',
    re.IGNORECASE,
)

# Match the .nac-btn-wa anchor and its inline SVG so we only touch the
# WhatsApp icon (other anchors with #fff fills stay untouched).
NAC_BTN_WA_BLOCK_RE = re.compile(
    r'(<a\s+class="nac-btn-wa"[^>]*>\s*<svg[^>]*style="[^"]*?)'
    r'(fill\s*:\s*(?:#fff|#FFF|currentColor))'
    r'([^"]*"[^>]*>)',
    re.IGNORECASE,
)


def process_file(path: Path, dry_run: bool = False) -> dict:
    text = path.read_text(encoding="utf-8")
    original = text
    counts = {"book_swap": 0, "wa_icon_green": 0}

    new_text, n = NAC_BTN_RE.subn(rf"\g<1>{GOOGLE_CAL}\g<2>", text)
    if n:
        text = new_text
        counts["book_swap"] = n

    new_text, n = NAC_BTN_WA_BLOCK_RE.subn(r"\1fill:#25D366\3", text)
    if n:
        text = new_text
        counts["wa_icon_green"] = n

    if text == original or dry_run:
        return counts
    path.write_text(text, encoding="utf-8")
    return counts


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
    totals = {"book_swap": 0, "wa_icon_green": 0}

    for f in files:
        if f.name in skip:
            continue
        c = process_file(f, dry_run=dry_run)
        if any(c.values()):
            print(
                f"{'[dry]' if dry_run else '✓'} {f.name}: "
                f"book={c['book_swap']}, wa_icon={c['wa_icon_green']}"
            )
        for k, v in c.items():
            totals[k] += v

    print(
        f"\nDone — book={totals['book_swap']}, wa_icon={totals['wa_icon_green']} "
        f"({'dry-run' if dry_run else 'applied'})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
