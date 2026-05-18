#!/usr/bin/env python3
"""Generate index.html — a GitHub-Pages preview index for all program brochures.

Style mirrors the PH PDP preview index
(https://rayvtt.github.io/Nac-Property-Hub-Listing-PDP/): an Instagram-
style square-tile grid with country / program name + Preview/Live buttons.

Each tile's background photo is pulled from the corresponding card on
NAC-BROCHURES-OVERVIEW.html (so the preview index visually matches what
ships on nomadassetcollective.com/brochures/).

Run:
    python tools/build_preview_index.py
"""
import html
import re
import sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from data.brochure_identity import IDENTITY  # noqa: E402

OVERVIEW_PATH = ROOT / 'Brochures html' / 'NAC-BROCHURES-OVERVIEW.html'
LIVE_BASE = 'https://nomadassetcollective.com/brochures'

# data-index → alias mapping. Based on overview card order.
INDEX_TO_ALIAS = {
    0:  'portugal',
    1:  'greece',
    2:  'cyprus',
    3:  'turkey',
    4:  'uae',
    5:  'uk',
    7:  'malta',
    10: 'stkitts',
    13: 'thailand',
    14: 'malaysia',
    16: 'newzealand',
    17: 'panama',
}

# Display order — top to bottom, left to right in the grid.
ORDER = [
    'portugal', 'greece', 'cyprus', 'turkey', 'uae', 'uk',
    'malta', 'stkitts', 'antigua', 'thailand', 'newzealand', 'panama', 'malaysia',
]


def extract_photos():
    """Map alias → background photo URL by parsing the overview HTML."""
    if not OVERVIEW_PATH.exists():
        sys.exit(f'❌ overview not found: {OVERVIEW_PATH}')
    text = OVERVIEW_PATH.read_text(encoding='utf-8')
    pattern = re.compile(
        r'data-index="(\d+)"[^>]*>\s*'
        r'<div class="card-photo" style="background-image:url\(\'([^\']+)\'',
        re.DOTALL,
    )
    photos = {}
    for m in pattern.finditer(text):
        idx = int(m.group(1))
        url = m.group(2)
        if idx in INDEX_TO_ALIAS:
            photos[INDEX_TO_ALIAS[idx]] = url
    return photos


def _strip_country_prefix(program, country):
    """Trim the country name from the front of the program name if it duplicates."""
    if program.startswith(country + ' '):
        return program[len(country) + 1:]
    return program


def render_tile(alias, photos):
    d = IDENTITY[alias]
    flag = d['flag']
    country_vi = d['country_vi']
    country_en = d['country_en']
    name_vi = _strip_country_prefix(d['program_vi'], country_vi)
    name_en = _strip_country_prefix(d['program_en'], country_en)
    photo = photos.get(alias, d.get('cover', ''))
    preview_path = f"./Brochures%20html/{quote(d['source_filename'])}"
    live_url = f"{LIVE_BASE}/{d['wp_slug']}/"
    return (
        f'      <div class="tile" data-alias="{alias}">\n'
        f'        <div class="tile-img" style="background-image:url(\'{html.escape(photo)}\')"></div>\n'
        f'        <div class="tile-info">\n'
        f'          <span class="tile-country">'
        f'<span data-i18n data-vi="{html.escape(flag)} {html.escape(country_vi)}" data-en="{html.escape(flag)} {html.escape(country_en)}">'
        f'{flag} {html.escape(country_vi)}'
        f'</span></span>\n'
        f'          <span class="tile-name" data-i18n data-vi="{html.escape(name_vi)}" data-en="{html.escape(name_en)}">{html.escape(name_vi)}</span>\n'
        f'        </div>\n'
        f'        <div class="tile-btns">\n'
        f'          <a href="{preview_path}" class="tile-btn tile-btn-preview" target="_blank" rel="noopener">'
        f'<span data-i18n data-vi="Preview ↗" data-en="Preview ↗">Preview ↗</span></a>\n'
        f'          <a href="{html.escape(live_url)}" class="tile-btn tile-btn-live" target="_blank" rel="noopener">'
        f'<span data-i18n data-vi="Live ↗" data-en="Live ↗">Live ↗</span></a>\n'
        f'        </div>\n'
        f'      </div>'
    )


def render_page():
    photos = extract_photos()
    missing = [a for a in ORDER if a not in photos]
    if missing:
        print(f'⚠ photos not extracted for: {", ".join(missing)} (will fall back to identity.cover)', file=sys.stderr)
    tiles = '\n'.join(render_tile(a, photos) for a in ORDER)
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>NAC Brochures — Program Preview Index</title>
<meta name="description" content="Preview index for all 13 NAC Program Brochures — RBI, CBI, LTR. Each tile links to a GitHub-Pages preview and the live WordPress page.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,500;1,400&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  :root {{
    --bg: #fafaf7; --surface: #fff; --display: #0f1a36; --text: #14181f;
    --muted: #6b7280; --gold: #c4922c; --orange: #d97c44;
    --line: rgba(15,26,54,.08);
    --ff-display: 'Cormorant Garamond', serif;
    --ff-body: 'Inter', -apple-system, sans-serif;
    --ff-mono: 'JetBrains Mono', monospace;
  }}
  body {{
    font-family: var(--ff-body); background: var(--bg); color: var(--text);
    min-height: 100vh; padding: 3rem 1.5rem 5rem;
  }}
  .wrap {{ max-width: 960px; margin: 0 auto; }}
  header {{ text-align: center; margin-bottom: 3rem; }}
  .mark {{ display: inline-flex; flex-direction: column; align-items: center; line-height: 1; }}
  .mark .the {{ font-family: var(--ff-display); font-size: .78rem; letter-spacing: .32em; color: var(--muted); }}
  .mark .nac {{ font-family: var(--ff-display); font-size: 2.3rem; font-weight: 500; letter-spacing: .32em; color: var(--display); margin: .15rem 0 .2rem; padding-left: .32em; }}
  .mark .tag {{ font-family: var(--ff-display); font-size: .72rem; letter-spacing: .38em; color: var(--gold); font-weight: 500; padding-left: .38em; }}
  h1 {{ font-family: var(--ff-display); font-size: 1.6rem; font-weight: 400; font-style: italic; color: var(--display); margin-top: 1.5rem; letter-spacing: -.005em; }}
  .sub {{ font-family: var(--ff-mono); font-size: .7rem; letter-spacing: .18em; text-transform: uppercase; color: var(--muted); margin-top: .5rem; }}

  /* Language toggle pill */
  .lang-toggle {{
    display: inline-flex; align-items: center;
    margin-top: 1.25rem;
    padding: 3px;
    background: rgba(15,26,54,.05);
    border: 1px solid var(--line);
    border-radius: 999px;
    font-family: var(--ff-mono);
    font-size: .6rem; letter-spacing: .15em;
  }}
  .lang-btn {{
    appearance: none; background: transparent; border: none; cursor: pointer;
    padding: 5px 12px; border-radius: 999px;
    color: var(--muted);
    font-family: inherit; font-size: inherit; letter-spacing: inherit;
    font-weight: 600;
    transition: color .15s ease, background .15s ease;
  }}
  .lang-btn.is-active {{ background: var(--display); color: #fff; }}

  /* Instagram-style square tile grid */
  .grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 3px; }}
  @media (max-width: 600px) {{ .grid {{ grid-template-columns: repeat(2, 1fr); }} }}

  .tile {{ position: relative; aspect-ratio: 1; overflow: hidden; background: var(--display); cursor: pointer; }}
  .tile-img {{ position: absolute; inset: 0; background-size: cover; background-position: center; transition: transform .5s ease; }}
  .tile:hover .tile-img {{ transform: scale(1.06); }}
  .tile::after {{
    content: ''; position: absolute; inset: 0;
    background: linear-gradient(to top, rgba(5,8,20,.88) 0%, rgba(5,8,20,.35) 55%, rgba(5,8,20,.05) 100%);
    pointer-events: none;
  }}

  .tile-info {{ position: absolute; bottom: 3.2rem; left: 1rem; right: 1rem; z-index: 1; }}
  .tile-country {{ display: block; font-family: var(--ff-mono); font-size: .58rem; letter-spacing: .14em; text-transform: uppercase; color: rgba(255,255,255,.7); margin-bottom: .35rem; }}
  .tile-name {{ display: block; font-family: var(--ff-display); font-size: 1.15rem; font-weight: 500; color: #fff; line-height: 1.2; }}

  .tile-btns {{ position: absolute; bottom: .75rem; left: 1rem; right: 1rem; z-index: 1; display: flex; gap: .4rem; }}
  .tile-btn {{
    flex: 1; text-align: center; padding: .32rem .4rem;
    border-radius: 6px; font-family: var(--ff-mono);
    font-size: .58rem; letter-spacing: .06em;
    text-decoration: none; text-transform: uppercase;
    font-weight: 500; transition: opacity .15s ease; white-space: nowrap;
  }}
  .tile-btn:hover {{ opacity: .82; }}
  .tile-btn-preview {{ background: rgba(255,255,255,.14); border: 1px solid rgba(255,255,255,.22); color: #fff; }}
  .tile-btn-live {{ background: var(--gold); border: 1px solid var(--gold); color: #fff; }}

  footer {{ text-align: center; margin-top: 2rem; font-family: var(--ff-mono); font-size: .65rem; color: var(--muted); letter-spacing: .08em; }}
  footer a {{ color: var(--orange); text-decoration: none; }}
</style>
</head>
<body>
  <div class="wrap">
    <header>
      <div class="mark">
        <span class="the">THE</span>
        <span class="nac">NAC</span>
        <span class="tag">PROGRAM BROCHURES</span>
      </div>
      <h1 data-i18n data-vi="Bộ Sưu Tập Brochure" data-en="Brochure Preview Index">Bộ Sưu Tập Brochure</h1>
      <p class="sub" data-i18n data-vi="Preview ↗ GitHub · Live ↗ Nomad Site" data-en="Preview ↗ GitHub · Live ↗ Nomad Site">Preview ↗ GitHub · Live ↗ Nomad Site</p>
      <div class="lang-toggle" role="group" aria-label="Language">
        <button class="lang-btn is-active" data-lang="vi" type="button">VI</button>
        <button class="lang-btn"           data-lang="en" type="button">EN</button>
      </div>
    </header>

    <div class="grid">
{tiles}
    </div>

    <footer>
      <span data-i18n data-vi="Xây dựng bởi" data-en="Built by">Built by</span>
      <a href="https://nomadassetcollective.com" target="_blank">Nomad Asset Collective</a> ·
      <a href="https://github.com/rayvtt/NAC-Program-Brochures" target="_blank">repo</a>
    </footer>
  </div>
  <script>
  (function() {{
    var KEY = 'nac-preview-lang';
    var defaultLang = (localStorage.getItem(KEY) === 'en') ? 'en' : 'vi';
    function apply(lang) {{
      document.documentElement.lang = lang;
      document.querySelectorAll('[data-i18n]').forEach(function(el) {{
        var t = el.getAttribute('data-' + lang);
        if (t != null) el.textContent = t;
      }});
      document.querySelectorAll('.lang-btn').forEach(function(btn) {{
        btn.classList.toggle('is-active', btn.dataset.lang === lang);
      }});
      try {{ localStorage.setItem(KEY, lang); }} catch (e) {{}}
    }}
    document.querySelectorAll('.lang-btn').forEach(function(btn) {{
      btn.addEventListener('click', function() {{ apply(btn.dataset.lang); }});
    }});
    apply(defaultLang);
  }})();
  </script>
</body>
</html>
'''


def main():
    out = ROOT / 'index.html'
    out.write_text(render_page(), encoding='utf-8')
    print(f'✓ wrote {out.relative_to(ROOT)} ({len(ORDER)} brochures)')


if __name__ == '__main__':
    main()
