"""Re-wire CTA backlinks across every brochure.

Two passes, idempotent:

1. **Booking URL migration**: every ``https://calendly.com/ray-vtt/30min``
   becomes ``https://calendar.app.google/gnbtNBTBDKuHUasw7`` (the new
   Google Calendar 30-min slot picker from NAC-LINKS.md). Additionally,
   the *header pill* CTA — the FIRST occurrence of the
   ``nomadassetcollective.com/tu-van-nhanh/`` link in each brochure
   (`📅 Tư Vấn Miễn Phí` in the top nav) — is rewired to the Google
   Calendar URL too. Body / mid-section ``tu-van-nhanh`` mentions are
   left alone (they still funnel into the WP quick-advisor form).

2. **WhatsApp green icon**: any header-pill WhatsApp link that uses the
   `💬 WhatsApp` emoji is upgraded to the canonical WhatsApp brand SVG
   (filled brand green #25D366). Other ``.cta-btn-wa`` / ``.nac-tool--wa``
   instances are already brand green via existing CSS — no change.

Run:
    python tools/rewire_cta_links.py             # all brochures
    python tools/rewire_cta_links.py turkey      # one alias
    python tools/rewire_cta_links.py --dry-run   # preview
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BROCHURES_DIR = ROOT / "Brochures html"

OLD_CALENDLY = "https://calendly.com/ray-vtt/30min"
TU_VAN_NHANH = "https://nomadassetcollective.com/tu-van-nhanh/"
GOOGLE_CALENDAR = "https://calendar.app.google/gnbtNBTBDKuHUasw7"

# Header-pill WhatsApp emoji → WhatsApp brand SVG. Match the simple
# anchor pattern used uniformly across brochures (no other classes).
HEADER_WA_PATTERN = re.compile(
    r'<a\s+href="https://wa\.me/447388646000"\s+target="_blank"(?P<extra>[^>]*)>'
    r'💬\s*WhatsApp</a>',
    re.IGNORECASE,
)

# Inline-SVG WhatsApp brand logo, brand-green pill, white-stroked icon.
# Used in the header pill (no theming, always green).
WA_SVG_PILL = (
    '<a href="https://wa.me/447388646000" target="_blank"\\g<extra> '
    'style="display:inline-flex;align-items:center;gap:6px;background:#25D366;'
    'color:#fff !important;padding:6px 12px;border-radius:7px;'
    'text-decoration:none;font-weight:600;font-size:12px;">'
    '<svg viewBox="0 0 24 24" style="width:13px;height:13px;fill:#fff;flex-shrink:0">'
    '<path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/>'
    '</svg>WhatsApp</a>'
)


def process_file(path: Path, dry_run: bool = False) -> dict:
    """Return counters for the file."""
    text = path.read_text(encoding="utf-8")
    original = text
    counts = {
        "calendly_swaps": 0,
        "header_pill_swaps": 0,
        "whatsapp_icon_swaps": 0,
    }

    # 1a. Swap every Calendly link to Google Calendar
    if OLD_CALENDLY in text:
        counts["calendly_swaps"] = text.count(OLD_CALENDLY)
        text = text.replace(OLD_CALENDLY, GOOGLE_CALENDAR)

    # 1b. Swap the *first* tu-van-nhanh occurrence — that's always the
    # header pill ("📅 Tư Vấn Miễn Phí" in the top nav). Body / section
    # CTAs come later in the file and stay pointing at tu-van-nhanh.
    first_tvn = text.find(TU_VAN_NHANH)
    if first_tvn != -1:
        text = text[:first_tvn] + GOOGLE_CALENDAR + text[first_tvn + len(TU_VAN_NHANH):]
        counts["header_pill_swaps"] = 1

    # 2. Upgrade any `💬 WhatsApp` emoji links to the green-pill SVG icon
    new_text, n = HEADER_WA_PATTERN.subn(WA_SVG_PILL, text)
    if n:
        text = new_text
        counts["whatsapp_icon_swaps"] = n

    if text == original:
        return counts

    if dry_run:
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
        if not files:
            print(f"No brochure matches: {aliases}", file=sys.stderr)
            return 1
    else:
        files = sorted(BROCHURES_DIR.glob("*.html"))

    skip = {"NAC-BROCHURES-OVERVIEW.html", "NAC-RESIDENCE-INDEX.html"}
    totals = {"calendly_swaps": 0, "header_pill_swaps": 0, "whatsapp_icon_swaps": 0}

    for f in files:
        if f.name in skip:
            continue
        c = process_file(f, dry_run=dry_run)
        any_change = any(c.values())
        if any_change:
            print(
                f"{'[dry]' if dry_run else '✓'} {f.name}: "
                f"calendly={c['calendly_swaps']}, "
                f"header_pill={c['header_pill_swaps']}, "
                f"wa_icon={c['whatsapp_icon_swaps']}"
            )
        for k, v in c.items():
            totals[k] += v

    print(
        f"\nDone — calendly={totals['calendly_swaps']}, "
        f"header_pill={totals['header_pill_swaps']}, "
        f"wa_icon={totals['whatsapp_icon_swaps']} "
        f"({'dry-run' if dry_run else 'applied'})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
