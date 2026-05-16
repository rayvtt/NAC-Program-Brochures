"""Install the NAC Residence Index banner (with animated globe + 12 KPI
pills) into the §07 comparison section of every brochure.

Replicates from Turkey: replaces whatever article-CTA currently sits at
the end of the comparison/proscons/etc section with the canonical NAC
Index banner-card. Adds the required CSS, the canvas-globe IIFE, and
the WP-safety addEventListener pattern so the same KSES traps don't
bite the EN rollout.

Idempotent — bails on second run because the marker
``id="nacIndexGlobe"`` already exists.

Run:
    python tools/install_nac_index_banner.py             # all 11 (skip Turkey)
    python tools/install_nac_index_banner.py portugal    # one alias
    python tools/install_nac_index_banner.py --dry-run
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BROCHURES_DIR = ROOT / "Brochures html"
TURKEY = BROCHURES_DIR / "turkey-cbi_8.html"
SKIP = {"NAC-BROCHURES-OVERVIEW.html", "NAC-RESIDENCE-INDEX.html", "turkey-cbi_8.html"}


def slice_between(text: str, start_marker: str, end_marker: str) -> str | None:
    """Return text between markers (exclusive of markers themselves)."""
    s = text.find(start_marker)
    if s < 0:
        return None
    e = text.find(end_marker, s + len(start_marker))
    if e < 0:
        return None
    return text[s:e]


def extract_turkey_blocks() -> dict:
    """Pull the NAC Index banner CSS / HTML / JS templates from Turkey."""
    src = TURKEY.read_text(encoding="utf-8")

    # 1. CSS block — from "/* ── NAC INDEX banner variant" to the next "/* ──" comment
    css_match = re.search(
        r'/\*\s*── NAC INDEX banner variant[\s\S]*?(?=/\* ── FOOTER)',
        src,
    )
    if not css_match:
        # Fallback: grab from .nac-index-banner first rule through .nac-index-pills-mobile end
        css_match = re.search(
            r'\.nac-index-banner\s*\{[\s\S]*?\.nac-index-pills-mobile\s*\{[\s\S]*?\}\s*\}',
            src,
        )
        if not css_match:
            raise RuntimeError("Cannot find NAC Index CSS in Turkey")
    css_block = css_match.group(0)

    # 2. HTML banner block — from "<div class=\"article-cta nac-index-cta\""
    # to the matching </div></div> (depth 2)
    html_start = src.find('<div class="article-cta nac-index-cta"')
    if html_start < 0:
        raise RuntimeError("Cannot find NAC Index HTML block in Turkey")
    # Walk to find matching close — depth-track <div … </div>
    depth = 0
    i = html_start
    end = -1
    while i < len(src):
        m_open = re.match(r'<div\b', src[i:i+5])
        m_close = re.match(r'</div>', src[i:i+6])
        if m_open:
            depth += 1
            i += 4
        elif m_close:
            depth -= 1
            i += 6
            if depth == 0:
                end = i
                break
        else:
            i += 1
    if end < 0:
        raise RuntimeError("Cannot find end of NAC Index HTML block")
    html_block = src[html_start:end]

    # 3. JS IIFE — the canvas globe script
    js_match = re.search(
        r'<script>\s*// ── NAC INDEX animated globe[\s\S]*?</script>',
        src,
    )
    if not js_match:
        raise RuntimeError("Cannot find NAC Index globe JS in Turkey")
    js_block = js_match.group(0)

    return {"css": css_block, "html": html_block, "js": js_block}


def insert_css(text: str, css_block: str) -> tuple[str, bool]:
    """Insert NAC Index CSS just before the closing </style>. Idempotent."""
    if ".nac-index-banner" in text:
        return text, False
    # Find the FIRST </style> (brochures only have one main <style> block)
    pos = text.find("</style>")
    if pos < 0:
        return text, False
    indent = "\n\n/* ──────────────────────────────────────────────\n"
    indent += "   NAC INDEX banner — animated globe + 12 KPI pills\n"
    indent += "   Lifted from Turkey master via install_nac_index_banner.py\n"
    indent += "   ────────────────────────────────────────────── */\n"
    return text[:pos] + indent + css_block + "\n" + text[pos:], True


def insert_html(text: str, html_block: str) -> tuple[str, bool]:
    """Insert the banner before the </section> that closes section #compare.

    Falls back to inserting before the proscons section if compare doesn't
    have a clear container. If neither, inserts before the FIRST <hr class="divider">
    after the comparison table.
    """
    if 'id="nacIndexGlobe"' in text:
        return text, False

    # Try: end of section id="compare" (most brochures use this slug)
    m = re.search(r'(<section[^>]*id="compare"[^>]*>[\s\S]*?)</section>', text)
    if not m:
        # Alt: id="comparison"
        m = re.search(r'(<section[^>]*id="comparison"[^>]*>[\s\S]*?)</section>', text)
    if not m:
        # Alt: any section that contains a comp-table
        m = re.search(
            r'(<section[^>]*>[\s\S]*?comp-table[\s\S]*?)</section>', text,
        )
    if not m:
        # Last resort: before the closing of section before #proscons
        m = re.search(r'(<section[^>]*>[\s\S]*?</section>)\s*(?=<hr[^>]*>\s*<!--\s*0?7|<hr[^>]*>\s*<!--\s*08|<section[^>]*id="proscons")', text)
    if not m:
        return text, False

    insert_at = m.end() - len("</section>")
    new = text[:insert_at] + "\n      " + html_block + "\n    " + text[insert_at:]
    return new, True


def insert_js(text: str, js_block: str) -> tuple[str, bool]:
    """Insert the canvas-globe IIFE just before the bilingual engine
    script. Falls back to inserting before </body>."""
    if "nacIndexGlobe" in text and "<canvas class=\"nac-index-globe\"" in text:
        # Check if JS already present
        if "// ── NAC INDEX animated globe" in text:
            return text, False
    # Try to insert before the "Full bilingual engine" comment
    pos = text.find("// ── Full bilingual engine ──")
    if pos > 0:
        # Backtrack to find the opening <script> tag
        script_open = text.rfind("<script>", 0, pos)
        if script_open > 0:
            return text[:script_open] + js_block + "\n\n" + text[script_open:], True

    # Fallback: insert before </body>
    pos = text.rfind("</body>")
    if pos < 0:
        return text, False
    return text[:pos] + js_block + "\n\n" + text[pos:], True


def add_wp_safety_bind(text: str) -> tuple[str, bool]:
    """Add the addEventListener bind for #btn-vi / #btn-en if a setLang
    function exists but no addEventListener wiring is present. This
    prevents the KSES inline-onclick strip from killing the toggle when
    the brochure later gets bilingual migration."""
    if "function setLang" not in text:
        return text, False  # no toggle yet, skip
    if 'getElementById(\'btn-en\').addEventListener' in text or \
       'getElementById("btn-en").addEventListener' in text:
        return text, False  # already bound
    # Find the closing brace of setLang function and inject after the
    # script's closing </script>
    bind_block = """
// Bind lang toggle without relying on inline onclick="" attributes.
// WordPress's KSES filter strips inline event handlers when content is
// saved to ACF fields, so #btn-vi / #btn-en need addEventListener bindings.
(function () {
  function bind() {
    var vi = document.getElementById('btn-vi');
    var en = document.getElementById('btn-en');
    if (vi) vi.addEventListener('click', function () { setLang('vi'); });
    if (en) en.addEventListener('click', function () { setLang('en'); });
    document.querySelectorAll('.float-toc-panel a').forEach(function (a) {
      a.addEventListener('click', function () {
        if (typeof closeFToc === 'function') closeFToc();
      });
    });
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bind);
  } else {
    bind();
  }
})();
"""
    # Find the script tag that defines setLang
    m = re.search(r'function setLang\s*\([^)]*\)\s*\{', text)
    if not m:
        return text, False
    # Find the next </script> after setLang
    end_script = text.find("</script>", m.start())
    if end_script < 0:
        return text, False
    return text[:end_script] + bind_block + "\n" + text[end_script:], True


def process_file(path: Path, blocks: dict, dry_run: bool = False) -> dict:
    text = path.read_text(encoding="utf-8")
    original = text
    out = {"css": 0, "html": 0, "js": 0, "wp_bind": 0}

    text, ok = insert_css(text, blocks["css"])
    if ok:
        out["css"] = 1
    text, ok = insert_html(text, blocks["html"])
    if ok:
        out["html"] = 1
    text, ok = insert_js(text, blocks["js"])
    if ok:
        out["js"] = 1
    text, ok = add_wp_safety_bind(text)
    if ok:
        out["wp_bind"] = 1

    if text == original or dry_run:
        return out
    path.write_text(text, encoding="utf-8")
    return out


def main() -> int:
    args = sys.argv[1:]
    dry_run = "--dry-run" in args
    args = [a for a in args if not a.startswith("--")]

    blocks = extract_turkey_blocks()
    print(f"  templates lifted from Turkey:")
    print(f"    CSS  {len(blocks['css']):>6} chars")
    print(f"    HTML {len(blocks['html']):>6} chars")
    print(f"    JS   {len(blocks['js']):>6} chars\n")

    if args:
        aliases = [a.lower() for a in args]
        files = [
            p for p in sorted(BROCHURES_DIR.glob("*.html"))
            if p.name not in SKIP
            and any(p.name.lower().startswith(a) for a in aliases)
        ]
    else:
        files = [p for p in sorted(BROCHURES_DIR.glob("*.html")) if p.name not in SKIP]

    totals = {"css": 0, "html": 0, "js": 0, "wp_bind": 0}
    for f in files:
        c = process_file(f, blocks, dry_run=dry_run)
        any_change = any(c.values())
        marker = "[dry]" if dry_run else ("✓" if any_change else "·")
        print(
            f"  {marker} {f.name}: "
            f"css={c['css']}, html={c['html']}, js={c['js']}, wp_bind={c['wp_bind']}"
        )
        for k, v in c.items():
            totals[k] += v

    print(
        f"\nDone — css={totals['css']}, html={totals['html']}, "
        f"js={totals['js']}, wp_bind={totals['wp_bind']} "
        f"({'dry-run' if dry_run else 'applied'})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
