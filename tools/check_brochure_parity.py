"""Brochure parity audit — check each brochure against Turkey template.

The workloop that backstops "is brochure X at Turkey parity?".
Runs a battery of checks lifted from TURKEY-TEMPLATE.md and prints a
status matrix:

  ✓ = present and correct
  ✗ = missing or broken
  ~ = partial / needs review

Categories tested:
  1. WP-safety: addEventListener bind for #btn-en/#btn-vi (KSES inline-onclick fix)
  2. WP-safety: no \\\" sequences in <script> blocks (KSES backslash-unescape)
  3. Sidebar CTA pill (cream-glass with tc-cal/tc-wa/tc-idx/tc-cmp chips)
  4. Header pill: Google Calendar URL on the 📅 Tư Vấn Miễn Phí link
  5. Header pill: WhatsApp icon SVG (not 💬 emoji)
  6. NAC footer Book CTA → Google Calendar
  7. WhatsApp .nac-btn-wa icon fill: #25D366
  8. Bilingual engine: data-vi/data-en attribute count (>50 = migrated)
  9. Chart bilingual: buildCharts(lang) wrapper exists
 10. Matrix chart aspectRatio swap (square on mobile)
 11. NAC Index banner with canvas globe (§07)
 12. 12 KPI icon pills (desktop + mobile)
 13. Article CTA banner-card structure (cover-image variant)
 14. Article cover URL: not a placeholder (og:image-driven)
 15. JS parses cleanly (no syntax errors)

Run:
    python tools/check_brochure_parity.py
    python tools/check_brochure_parity.py turkey      # one alias
    python tools/check_brochure_parity.py --verbose   # show details
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BROCHURES_DIR = ROOT / "Brochures html"

GOOGLE_CAL = "calendar.app.google/gnbtNBTBDKuHUasw7"
SKIP = {"NAC-BROCHURES-OVERVIEW.html", "NAC-RESIDENCE-INDEX.html"}

# ANSI colours
GREEN  = "\033[32m"
RED    = "\033[31m"
YELLOW = "\033[33m"
BLUE   = "\033[34m"
GRAY   = "\033[90m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

CHECK = f"{GREEN}✓{RESET}"
CROSS = f"{RED}✗{RESET}"
PART  = f"{YELLOW}~{RESET}"


def check(name: str, ok: bool, note: str = "") -> tuple[str, bool, str]:
    return name, ok, note


def audit_one(path: Path) -> list:
    text = path.read_text(encoding="utf-8")
    results = []

    # 1. WP-safety: addEventListener bind for lang buttons
    has_addev = bool(re.search(
        r"getElementById\(['\"]btn-en['\"]\)\.addEventListener", text
    )) or bool(re.search(
        r"btn-en[^}]*addEventListener", text, re.DOTALL
    ))
    has_inline_onclick = 'onclick="setLang(' in text
    if has_addev:
        results.append(check("WP-safety: addEventListener bound to lang btns", True))
    elif has_inline_onclick:
        results.append(check(
            "WP-safety: lang btns use inline onclick (KSES will strip on WP)",
            False, "Bind via addEventListener at script end",
        ))
    else:
        results.append(check("WP-safety: lang btns", False, "No toggle wiring at all"))

    # 2. WP-safety: no \" inside <script> tags (KSES unescapes → SyntaxError)
    scripts = re.findall(r"<script[^>]*>(.*?)</script>", text, re.DOTALL)
    bad_escapes = sum(s.count('\\"') for s in scripts)
    results.append(check(
        "WP-safety: no \\\" in <script> blocks",
        bad_escapes == 0,
        f"{bad_escapes} occurrence(s) — replace with curly quotes" if bad_escapes else "",
    ))

    # 3. Sidebar CTA pill
    has_sidebar_pill = (
        ".tc-cal" in text and ".tc-wa" in text
        and ".tc-idx" in text and ".tc-cmp" in text
        and "rgba(250,245,232" in text
    )
    results.append(check("Sidebar CTA cream-glass pill (4 chips)", has_sidebar_pill))

    # 4. Booking CTA points at Google Calendar (sidebar tc-cal OR nav 📅)
    booking_to_google = bool(re.search(
        r'class="tc-cal"[^>]*href="https://calendar\.app\.google/', text
    )) or bool(re.search(
        r'<a href="https://calendar\.app\.google/[^"]+"[^>]*>📅', text
    ))
    results.append(check("Header / sidebar booking → Google Calendar", booking_to_google))

    # 5. WhatsApp icon SVG (not 💬 emoji) — sidebar tc-wa OR inline green pill
    has_wa_emoji_only = bool(re.search(
        r'<a href="https://wa\.me/[^"]+"[^>]*>💬\s*WhatsApp</a>', text
    ))
    has_wa_svg = bool(re.search(
        r'class="tc-wa"[^>]*href="https://wa\.me/', text
    )) or bool(re.search(
        r'<a href="https://wa\.me/[^"]+"[^>]*background:#25D366', text
    ))
    results.append(check(
        "Header / sidebar WhatsApp: SVG (not 💬 emoji)",
        has_wa_svg and not has_wa_emoji_only,
    ))

    # 6. Footer Book CTA → Google Calendar
    book_to_google = bool(re.search(
        r'<a class="nac-btn" href="https://calendar\.app\.google/', text
    ))
    # Some brochures use a different footer pattern (e.g. Cyprus)
    has_nac_btn = 'class="nac-btn"' in text and 'class="nac-btn-wa"' in text
    if has_nac_btn:
        results.append(check("Footer Book CTA → Google", book_to_google))
    else:
        # Different footer; skip
        results.append(check("Footer Book CTA → Google", True, "n/a — different footer"))

    # 7. WhatsApp .nac-btn-wa icon green
    wa_btn_block = re.search(
        r'<a\s+class="nac-btn-wa"[^>]*>\s*<svg[^>]*style="[^"]*"', text
    )
    if wa_btn_block:
        block = text[wa_btn_block.start():wa_btn_block.end()]
        wa_icon_green = "#25D366" in block
        results.append(check("WhatsApp .nac-btn-wa icon: #25D366", wa_icon_green))
    else:
        results.append(check("WhatsApp .nac-btn-wa icon: #25D366", True, "n/a"))

    # 8. Bilingual coverage — accept either data-vi/data-en attrs (Turkey
    # pattern, more robust) OR legacy VI_STRINGS/EN_STRINGS arrays
    # (works fine, less robust to text edits).
    n_data_vi = len(re.findall(r"\bdata-vi=", text))
    n_data_en = len(re.findall(r"\bdata-en=", text))
    has_legacy = "VI_STRINGS" in text and "EN_STRINGS" in text
    if n_data_vi >= 200:
        results.append(check(
            f"Bilingual support (data-attr: {n_data_vi} attrs)", True,
        ))
    elif has_legacy:
        results.append(check(
            "Bilingual support (legacy VI_STRINGS/EN_STRINGS)", True,
            f"data-attr migration pending (currently {n_data_vi} attrs)",
        ))
    else:
        results.append(check("Bilingual support", False, "Neither pattern present"))

    # 9. Chart bilingual wrapper
    has_buildcharts = bool(re.search(r"\bbuildCharts\s*\(", text))
    results.append(check("Chart bilingual buildCharts(lang) wrapper", has_buildcharts))

    # 10. Matrix chart mobile aspectRatio
    has_matrix_mobile = "max-width: 600px" in text and "aspectRatio" in text and "matrixCollapse" in text
    has_matrix = 'id="matrixChart"' in text
    if has_matrix:
        results.append(check("Matrix chart mobile aspectRatio + collapsible", has_matrix_mobile))
    else:
        results.append(check("Matrix chart mobile aspectRatio + collapsible", True, "n/a — no matrix chart"))

    # 11. NAC Index banner with canvas globe
    has_globe = 'id="nacIndexGlobe"' in text and "nac-index-banner" in text
    results.append(check("NAC Index banner with canvas globe", has_globe))

    # 12. 12 KPI icon pills
    has_pills = "nac-index-pills" in text and "nac-pill" in text and text.count("nac-pill") >= 12
    results.append(check("12 KPI icon pills", has_pills))

    # 13. Article CTA banner-card structure
    has_banner_card = (
        ".article-cta-banner" in text
        and ".article-cta-kicker" in text
        and ".article-cta-title" in text
    )
    results.append(check("Article CTA: banner-card structure", has_banner_card))

    # 14. Article cover not a placeholder (only flag if Unsplash sits
    # inside an .article-cta block — Unsplash in the hero bg is fine)
    article_cta_blocks = re.findall(
        r'<div class="article-cta[^"]*"[^>]*>[\s\S]*?</div>\s*(?:</section|</div\s*>)',
        text,
    )
    article_has_unsplash = any(
        "images.unsplash.com" in blk for blk in article_cta_blocks
    )
    results.append(check(
        "Article cover: real og:image (no Unsplash placeholder)",
        not article_has_unsplash,
    ))

    # 15. JS parses — only check executable <script> blocks (skip
    # JSON-LD which is data, not JS).
    script_tags = re.finditer(
        r'<script([^>]*)>(.*?)</script>', text, re.DOTALL,
    )
    errs = 0
    err_detail = ""
    for m in script_tags:
        attrs, body = m.group(1), m.group(2).strip()
        if not body:
            continue
        # Skip non-JS script types
        type_m = re.search(r'type\s*=\s*[\'"]([^\'"]+)[\'"]', attrs)
        if type_m and type_m.group(1) not in ("text/javascript", "application/javascript", "module"):
            continue
        # Skip external src= scripts (no body anyway)
        if 'src=' in attrs and not body:
            continue
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as tf:
            tf.write(body)
            tmp = tf.name
        try:
            r = subprocess.run(
                ["node", "--check", tmp],
                capture_output=True, text=True, timeout=10,
            )
            if r.returncode:
                errs += 1
                if not err_detail:
                    err_lines = [l for l in r.stderr.split("\n") if "SyntaxError" in l]
                    err_detail = err_lines[0] if err_lines else "parse error"
        finally:
            Path(tmp).unlink(missing_ok=True)
    results.append(check(
        "All <script> blocks parse cleanly (node --check)",
        errs == 0,
        err_detail if errs else "",
    ))

    return results


def main() -> int:
    args = sys.argv[1:]
    verbose = "--verbose" in args or "-v" in args
    args = [a for a in args if not a.startswith("-")]

    if args:
        aliases = [a.lower() for a in args]
        files = [
            p for p in sorted(BROCHURES_DIR.glob("*.html"))
            if p.name not in SKIP
            and any(p.name.lower().startswith(a) for a in aliases)
        ]
    else:
        files = [p for p in sorted(BROCHURES_DIR.glob("*.html")) if p.name not in SKIP]

    print(f"\n{BOLD}NAC Brochure Parity Audit{RESET} — vs TURKEY-TEMPLATE.md")
    print(f"{GRAY}{'─' * 76}{RESET}")

    summary = []
    for f in files:
        results = audit_one(f)
        passed = sum(1 for _, ok, _ in results if ok)
        total = len(results)
        summary.append((f.name, passed, total, results))

        status = GREEN if passed == total else (YELLOW if passed >= total - 3 else RED)
        print(f"\n{BOLD}{f.name}{RESET}  {status}{passed}/{total}{RESET}")
        for name, ok, note in results:
            icon = CHECK if ok else CROSS
            note_str = f" {GRAY}— {note}{RESET}" if note and (not ok or verbose) else ""
            if not ok or verbose:
                print(f"  {icon} {name}{note_str}")

    print(f"\n{GRAY}{'─' * 76}{RESET}")
    print(f"{BOLD}Summary:{RESET}")
    for name, p, t, _ in summary:
        bar = "█" * p + "░" * (t - p)
        color = GREEN if p == t else (YELLOW if p >= t - 3 else RED)
        print(f"  {color}{bar}{RESET}  {p:>2}/{t}  {name}")

    full_parity = sum(1 for _, p, t, _ in summary if p == t)
    print(f"\n  {GREEN}{full_parity}{RESET} of {len(summary)} brochures at full Turkey parity.\n")

    return 0 if full_parity == len(summary) else 1


if __name__ == "__main__":
    raise SystemExit(main())
