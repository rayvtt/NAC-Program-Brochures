#!/usr/bin/env python3
"""Inject the Twemoji flag-renderer block into every brochure before </body>.

Background: country-flag emojis (🇦🇺, 🇹🇷, etc.) render as letter pairs
("AU", "TR") on Windows and some Android builds because those platforms
don't ship country-flag glyphs. Twemoji rewrites flag emojis as inline
SVG images on those platforms so every viewer sees a real flag.

The Overview brochure already has this block (PR #127). This script
applies the same block to all other brochures. Idempotent — re-runs
report 0 changes.

Run:
    python tools/inject_twemoji.py              # all brochures
    python tools/inject_twemoji.py turkey       # one
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
HTML_DIR = ROOT / "Brochures html"

MARKER = "twemoji.parse"  # presence of this identifies an already-injected file

BLOCK = """
<!-- Twemoji: render flag emojis as images on platforms that show
     country codes (Windows, some Android). CDN-hosted SVGs. -->
<script src="https://cdn.jsdelivr.net/npm/twemoji@14.0.2/dist/twemoji.min.js" crossorigin="anonymous"></script>
<script>
if (typeof twemoji !== 'undefined') {
  twemoji.parse(document.body, {
    folder: 'svg',
    ext: '.svg',
    className: 'twemoji-flag'
  });
}
</script>
<style>
/* Size twemoji flag images to match the surrounding text */
img.twemoji-flag { height: 1em; width: 1em; vertical-align: -0.1em; display: inline-block; }
.card-flag img.twemoji-flag { height: 28px; width: 28px; vertical-align: baseline; }
</style>
"""


def inject_one(path: Path) -> str:
    html = path.read_text(encoding="utf-8")
    if MARKER in html:
        return "skip"
    if "</body>" not in html:
        return "no-body"
    new_html = html.replace("</body>", BLOCK + "\n</body>", 1)
    path.write_text(new_html, encoding="utf-8")
    return "injected"


def matches(target: str | None) -> list[Path]:
    files = sorted(HTML_DIR.glob("*.html"))
    if not target:
        return files
    return [f for f in files if target.lower() in f.name.lower()]


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else None
    files = matches(target)
    if not files:
        sys.exit(f"No brochures match {target!r}")
    counts = {"injected": 0, "skip": 0, "no-body": 0}
    for f in files:
        result = inject_one(f)
        counts[result] += 1
        sym = {"injected": "✓", "skip": "·", "no-body": "✗"}[result]
        print(f"  {sym} {f.name:<35} {result}")
    print(f"\n{counts['injected']} injected, "
          f"{counts['skip']} already had it, {counts['no-body']} skipped (no </body>)")


if __name__ == "__main__":
    main()
