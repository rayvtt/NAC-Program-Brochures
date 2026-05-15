#!/usr/bin/env python3
"""Generate index.html at repo root — a GitHub-Pages preview index for
all program brochures.

For each brochure (per data/brochure_identity.py), renders:
    <flag> <Country> <Program> — Preview ↗ · Live ↗

Preview link  → ./Brochures html/<filename> (served by GitHub Pages)
Live link     → https://nomadassetcollective.com/brochures/<wp_slug>/

Run:
    python tools/build_preview_index.py
"""
import html
import sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from data.brochure_identity import IDENTITY  # noqa: E402

LIVE_BASE = 'https://nomadassetcollective.com/brochures'

# Display order — alphabetical by country_vi, but typically left as identity order
ORDER = [
    'portugal', 'greece', 'cyprus', 'turkey', 'uae', 'uk', 'malta',
    'stkitts', 'thailand', 'newzealand', 'panama', 'malaysia',
]


def render_row(alias):
    d = IDENTITY[alias]
    flag = d['flag']
    title = d['program_vi']  # already includes country name (e.g. "Bồ Đào Nha Golden Visa")
    # Local preview path — spaces URL-encoded.
    preview_path = f"./Brochures%20html/{quote(d['source_filename'])}"
    live_url = f"{LIVE_BASE}/{d['wp_slug']}/"
    return (
        '    <li class="row">\n'
        f'      <span class="flag">{flag}</span>\n'
        f'      <span class="title">{html.escape(title)}</span>\n'
        f'      <a class="link preview" href="{preview_path}" target="_blank" rel="noopener">Preview ↗</a>\n'
        f'      <a class="link live"    href="{html.escape(live_url)}" target="_blank" rel="noopener">Live ↗</a>\n'
        '    </li>'
    )


def render_page():
    rows = '\n'.join(render_row(a) for a in ORDER)
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>NAC Brochures — Preview Index</title>
<meta name="description" content="Preview index for all NAC Program Brochures. Each entry links to the GitHub-Pages preview and the live WordPress version.">
<style>
  :root {{
    --bg: #faf6eb;
    --fg: #14181f;
    --muted: #6b7280;
    --rule: rgba(20,24,31,0.08);
    --accent: #c4922c;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{
    background: var(--bg); color: var(--fg);
    font-family: 'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif;
    -webkit-font-smoothing: antialiased;
    font-size: 16px; line-height: 1.55;
  }}
  body {{ padding: 56px 24px 80px; }}
  main {{ max-width: 760px; margin: 0 auto; }}
  h1 {{
    font-size: 28px; font-weight: 700; letter-spacing: -0.01em;
    margin-bottom: 8px;
  }}
  .sub {{
    color: var(--muted); font-size: 14px;
    margin-bottom: 36px;
  }}
  ul.rows {{ list-style: none; }}
  li.row {{
    display: flex; align-items: center; gap: 14px;
    padding: 14px 0;
    border-bottom: 1px solid var(--rule);
  }}
  .flag {{ font-size: 22px; line-height: 1; flex-shrink: 0; width: 28px; text-align: center; }}
  .title {{ flex: 1; font-weight: 500; font-size: 15px; }}
  .link {{
    font-size: 13px; font-weight: 600;
    text-decoration: none;
    padding: 6px 10px; border-radius: 6px;
    transition: background 0.15s ease, color 0.15s ease;
    white-space: nowrap;
  }}
  .link.preview {{ color: var(--accent); }}
  .link.preview:hover {{ background: rgba(196,146,60,0.12); }}
  .link.live    {{ color: var(--fg); }}
  .link.live:hover    {{ background: rgba(20,24,31,0.06); }}
  footer {{
    margin-top: 48px;
    font-size: 12px; color: var(--muted);
    text-align: center;
  }}
  footer a {{ color: var(--accent); text-decoration: none; }}
  @media (max-width: 540px) {{
    body {{ padding: 32px 16px 60px; }}
    h1 {{ font-size: 22px; }}
    li.row {{ flex-wrap: wrap; gap: 8px; }}
    .title {{ flex-basis: calc(100% - 42px); font-size: 14px; }}
    .link {{ font-size: 12px; padding: 5px 8px; }}
  }}
</style>
</head>
<body>
<main>
  <h1>NAC Brochures — Preview Index</h1>
  <p class="sub">{len(ORDER)} country brochures. <em>Preview</em> opens the GitHub-Pages copy; <em>Live</em> opens the production WordPress page.</p>

  <ul class="rows">
{rows}
  </ul>

  <footer>
    Nomad Asset Collective ·
    <a href="https://github.com/rayvtt/NAC-Program-Brochures" target="_blank" rel="noopener">repo</a> ·
    <a href="https://nomadassetcollective.com/brochures/" target="_blank" rel="noopener">brochures gateway</a>
  </footer>
</main>
</body>
</html>
'''


def main():
    out = ROOT / 'index.html'
    out.write_text(render_page(), encoding='utf-8')
    print(f'✓ wrote {out.relative_to(ROOT)} ({len(ORDER)} brochures listed)')


if __name__ == '__main__':
    main()
