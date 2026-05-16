"""Add a post-setLang chart translator to every non-Turkey brochure.

The 11 non-Turkey brochures use the legacy setLang() string-replace
pattern. That covers DOM text but NOT Chart.js dataset labels / axis
titles / tooltip callbacks (which are JS literals inside chart config).

Instead of rewriting each brochure's chart code to use Turkey's
buildCharts(lang) wrapper (per-brochure, fragile), inject a generic
translator that:
  1. Walks Chart.instances (Chart.js v4 global)
  2. Snapshots original VI labels on first call
  3. Swaps to EN using a shared VI→EN dictionary (countries + common
     axis labels), or restores VI when toggled back
  4. Calls chart.update()
  5. Hooks into setLang() so it runs on every toggle

Idempotent — re-runs skip if the marker is already present.

Run:
    python tools/add_chart_translator.py             # all 11
    python tools/add_chart_translator.py portugal
    python tools/add_chart_translator.py --dry-run
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BROCHURES_DIR = ROOT / "Brochures html"
SKIP = {"NAC-BROCHURES-OVERVIEW.html", "NAC-RESIDENCE-INDEX.html", "turkey-cbi_8.html"}

# Marker so we can detect prior injection
MARKER = "// ── NAC chart translator ─────────────────────────────────"

TRANSLATOR_BLOCK = f"""
{MARKER}
// Translates Chart.js dataset labels / axis titles / tooltip strings
// after setLang() runs. The 11 non-Turkey brochures use legacy
// string-replace bilingual for DOM text but charts hold their labels
// in JS config — this helper walks Chart.instances and swaps them too.
(function () {{
  if (typeof Chart === 'undefined') return;
  // Use curly quotes inside strings — WP's KSES unescapes backslash-quote.
  const CHART_VI_EN = {{
    // Country names with flags (most common in chart labels)
    '🇹🇷 Thổ Nhĩ Kỳ CBI': '🇹🇷 Türkiye CBI',
    '🇹🇷 Thổ Nhĩ Kỳ': '🇹🇷 Türkiye',
    '🇬🇷 Hy Lạp GV': '🇬🇷 Greece GV',
    '🇬🇷 Hy Lạp': '🇬🇷 Greece',
    '🇵🇹 Bồ Đào Nha GV': '🇵🇹 Portugal GV',
    '🇵🇹 Bồ Đào Nha': '🇵🇹 Portugal',
    '🇪🇸 Tây Ban Nha GV': '🇪🇸 Spain GV',
    '🇪🇸 Tây Ban Nha': '🇪🇸 Spain',
    '🇦🇪 UAE GV': '🇦🇪 UAE GV',
    '🇦🇪 UAE': '🇦🇪 UAE',
    '🇲🇹 Malta QT': '🇲🇹 Malta CIT',
    '🇲🇹 Malta': '🇲🇹 Malta',
    '🇰🇳 St Kitts CBI': '🇰🇳 St Kitts CBI',
    '🇰🇳 St Kitts': '🇰🇳 St Kitts',
    '🇨🇾 Đảo Síp': '🇨🇾 Cyprus',
    '🇨🇾 Síp': '🇨🇾 Cyprus',
    '🇹🇭 Thái Lan': '🇹🇭 Thailand',
    '🇳🇿 New Zealand': '🇳🇿 New Zealand',
    '🇵🇦 Panama': '🇵🇦 Panama',
    '🇲🇾 Malaysia': '🇲🇾 Malaysia',
    '🇬🇧 Anh Quốc': '🇬🇧 United Kingdom',
    '🇬🇧 Anh': '🇬🇧 UK',
    // Country names without flags
    'Thổ Nhĩ Kỳ': 'Türkiye',
    'Hy Lạp': 'Greece',
    'Bồ Đào Nha': 'Portugal',
    'Tây Ban Nha': 'Spain',
    'Đảo Síp': 'Cyprus',
    'Thái Lan': 'Thailand',
    'Anh Quốc': 'United Kingdom',
    // Reference suffixes
    ' (tham chiếu)': ' (benchmark)',
    // Radar axes
    'Đầu tư': 'Investment',
    'Tốc độ': 'Speed',
    'Chất lượng sống': 'Quality of Life',
    'Hộ chiếu': 'Passport',
    'Thuế': 'Tax',
    'Quốc tịch': 'Citizenship',
    // Axis titles
    'Tốc độ xử lý (cao = nhanh hơn)': 'Processing speed (higher = faster)',
    'Sức mạnh hộ chiếu / tự do di chuyển': 'Passport strength / mobility',
    'Sức mạnh hộ chiếu / Tự do di chuyển': 'Passport strength / Mobility',
    'Sức mạnh hộ chiếu': 'Passport strength',
    // Dataset labels
    'Điểm NAC': 'NAC Score',
    'Điểm tổng hợp NAC': 'NAC Composite Score',
    'Tháng xử lý trung bình': 'Average processing months',
    'Tháng xử lý': 'Processing months',
  }};

  const keysByLen = Object.keys(CHART_VI_EN).sort((a, b) => b.length - a.length);

  function translate(s) {{
    if (typeof s !== 'string' || !s) return s;
    let out = s;
    for (const k of keysByLen) {{
      if (out.indexOf(k) !== -1) out = out.split(k).join(CHART_VI_EN[k]);
    }}
    return out;
  }}

  function snapshot(chart) {{
    if (chart._nacOrig) return;
    chart._nacOrig = {{
      labels: chart.data.labels ? chart.data.labels.slice() : null,
      datasetLabels: chart.data.datasets.map(d => d.label),
      scales: {{}},
    }};
    if (chart.options && chart.options.scales) {{
      for (const ax of ['x', 'y', 'r']) {{
        const sc = chart.options.scales[ax];
        if (sc && sc.title && sc.title.text) {{
          chart._nacOrig.scales[ax] = sc.title.text;
        }}
      }}
    }}
  }}

  function applyLang(chart, lang) {{
    snapshot(chart);
    const tr = lang === 'en' ? translate : (s => s);
    if (chart._nacOrig.labels) {{
      chart.data.labels = chart._nacOrig.labels.map(tr);
    }}
    chart.data.datasets.forEach((d, i) => {{
      const orig = chart._nacOrig.datasetLabels[i];
      if (orig) d.label = tr(orig);
    }});
    if (chart.options && chart.options.scales) {{
      for (const ax of ['x', 'y', 'r']) {{
        const sc = chart.options.scales[ax];
        const orig = chart._nacOrig.scales[ax];
        if (sc && sc.title && orig) sc.title.text = tr(orig);
      }}
    }}
    chart.update();
  }}

  function translateAll() {{
    const lang = (typeof currentLang === 'string') ? currentLang : 'vi';
    const insts = (Chart.instances && typeof Chart.instances === 'object')
      ? Object.values(Chart.instances) : [];
    insts.forEach(c => {{ try {{ applyLang(c, lang); }} catch (e) {{}} }});
  }}

  // Wrap setLang so the translator runs after every toggle.
  if (typeof setLang === 'function') {{
    const original = setLang;
    window.setLang = function (lang) {{
      original.apply(this, arguments);
      translateAll();
    }};
  }}
  // Also run once on load in case the page started in EN (sticky lang)
  if (document.readyState === 'loading') {{
    document.addEventListener('DOMContentLoaded', translateAll);
  }} else {{
    setTimeout(translateAll, 300);
  }}
}})();
"""


def insert_translator(text: str) -> tuple[str, bool]:
    if MARKER in text:
        return text, False
    pos = text.rfind("</body>")
    if pos < 0:
        return text, False
    wrapped = "\n<script>\n" + TRANSLATOR_BLOCK + "\n</script>\n"
    return text[:pos] + wrapped + text[pos:], True


def process_file(path: Path, dry_run: bool = False) -> bool:
    text = path.read_text(encoding="utf-8")
    new_text, changed = insert_translator(text)
    if not changed or dry_run:
        return changed
    path.write_text(new_text, encoding="utf-8")
    return True


def main() -> int:
    args = sys.argv[1:]
    dry_run = "--dry-run" in args
    args = [a for a in args if not a.startswith("--")]

    if args:
        aliases = [a.lower() for a in args]
        files = [
            p for p in sorted(BROCHURES_DIR.glob("*.html"))
            if p.name not in SKIP
            and any(p.name.lower().startswith(a) for a in aliases)
        ]
    else:
        files = [p for p in sorted(BROCHURES_DIR.glob("*.html")) if p.name not in SKIP]

    n = 0
    for f in files:
        changed = process_file(f, dry_run=dry_run)
        marker = "[dry]" if dry_run else ("✓" if changed else "·")
        print(f"  {marker} {f.name}")
        if changed:
            n += 1
    print(f"\nDone — {n} brochure(s) patched ({'dry-run' if dry_run else 'applied'})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
