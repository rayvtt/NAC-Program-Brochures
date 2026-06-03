# Daily Live Brochure Checklist

The 8-point checklist the daily audit (`tools/daily_en_audit.py`) verifies on each live brochure. Failures get surfaced via GitHub Issue (`en-audit` label) + the sheet tracker (A28:J39 in the backlink tab).

| # | Check | What it verifies |
|---|---|---|
| 1 | **VI/EN toggle works** | `setLang` defined, both buttons (`#btn-vi`, `#btn-en`) have a click handler (inline `onclick` OR `addEventListener`), `VI_STRINGS` / `EN_STRINGS` arrays present and roughly equal-length, no `\"` KSES traps in scripts |
| 2 | **Charts + tables contain EN** | Brochure has either `buildCharts(lang)` wrapper (Turkey pattern) or post-`setLang` Chart.instances translator. Tables (`.comp-table`) covered by VI/EN array entries |
| 3 | **§01 Program Overview populated with EN** | Every prose element in the `#overview` section flips on EN click — section coverage ≥ 70% |
| 4 | **NAC Residence Index — globe + section size (MOBILE)** | Mobile uses CSS Grid `grid-template-rows: 240px auto auto`. Globe canvas 240×240 in row 1, kicker + title in rows 2–3. Tight fit; matches Turkey |
| 5 | **NAC Residence Index — globe + section size (DESKTOP)** | Banner `min-height: 300px` — fits the 300px globe exactly, no extra vertical space. Globe sits at `right: -6%` (slight overflow for watermark feel). Gradient is the original `linear-gradient(135deg, #f0eeff 0%, #f8f7ff 50%, #eef3ff 100%)`. **Turkey is the canonical template — locked. Don't touch these values; align other brochures to Turkey.** |
| 6 | **Article URL → specific blog PDP** | Each `<a class="article-cta-banner">` href must point to a specific blog post (e.g. `blog.nomadassetcollective.com/<slug>/`), NOT to the bare homepage `blog.nomadassetcollective.com/`. Generic blog cards (from the dedupe rule) are exempt. **Bare-homepage fallback:** `tools/refresh_article_covers.py` substitutes a deterministic-per-(alias, fortnight) random PDP from the NAC blog categories Góc Nhìn NAC + Phân Tích — picking a real article URL, og:title, and og:image — whenever a banner ships pointing at the bare blog homepage. See `tools/pick_random_blog_article.py`. |
| 7 | **Charts render correctly (desktop + mobile)** | All 4 canvases present: `#radarChart`, `#citizenshipChart`, `#compareChart`, `#matrixChart`. Matrix has the `aspectRatio: 1` mobile / `2` desktop swap. No `max-height` constraints below 200px |
| 8 | **English version actually displays on EN click** | Replays `setLang('en')` in a real DOM (jsdom) and checks **no Vietnamese remnants remain** visible. Catches: DOM strings not in arrays, empty EN slots, whitespace / `<br>` / inline-style drift between DOM and arrays, missing selectors, KSES mangling. Failure = the user sees mixed VN+EN after clicking English. Run via `node tools/simulate_en_render.js "Brochures html/<file>.html"` (or pass a URL) for a per-string breakdown. The Python `simulate_en_render.py` is DEPRECATED — it normalizes HTML differently from a real browser and silently passes broken pages. **Note (Q2/2026):** the simulator's `VN_UNIQUE` regex was widened in `#76` to catch single-mark vowels (`á à ã ạ ó ò ô è í ú ý`) — earlier "0 remnants" results may have hidden real bleeds. Re-run after that PR for ground truth. |

## Automation

- **Every 10 min** — `pull-notion.yml` syncs Notion → live → updates `sheet-tracker.tsv`
- **Daily 02:00 UTC** — `daily-en-audit.yml` runs this 7-point checklist on live pages
- Failures → GitHub Issue (`en-audit` label) with concrete per-brochure breakdown
- All-passing → existing issue auto-closes

## Where to look

| Source | What it shows |
|---|---|
| `.diagnostics/daily-en-audit.json` | Raw audit data (machine-readable) |
| `.diagnostics/sheet-tracker.tsv` | Paste-ready row for Google Sheet A28:J39 |
| `.diagnostics/sheet-tracker.md` | Same data, human-readable on GitHub |
| GitHub Issues w/ `en-audit` label | Current failing items, surfaces via mobile push + email |

## How to manually run the audit

```bash
python tools/daily_en_audit.py             # fetch all live brochures, run all 7 checks
python tools/daily_en_audit.py portugal    # one brochure
python tools/daily_en_audit.py --local     # use local HTML files (skip live fetch)
```
