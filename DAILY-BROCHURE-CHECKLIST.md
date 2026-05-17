# Daily Live Brochure Checklist

The 7-point checklist the daily audit (`tools/daily_en_audit.py`) verifies on each live brochure. Failures get surfaced via GitHub Issue (`en-audit` label) + the sheet tracker (A28:J39 in the backlink tab).

| # | Check | What it verifies |
|---|---|---|
| 1 | **VI/EN toggle works** | `setLang` defined, both buttons (`#btn-vi`, `#btn-en`) have a click handler (inline `onclick` OR `addEventListener`), `VI_STRINGS` / `EN_STRINGS` arrays present and roughly equal-length, no `\"` KSES traps in scripts |
| 2 | **Charts + tables contain EN** | Brochure has either `buildCharts(lang)` wrapper (Turkey pattern) or post-`setLang` Chart.instances translator. Tables (`.comp-table`) covered by VI/EN array entries |
| 3 | **§01 Program Overview populated with EN** | Every prose element in the `#overview` section flips on EN click — section coverage ≥ 70% |
| 4 | **NAC Residence Index — globe + section size (MOBILE)** | Mobile uses CSS Grid `grid-template-rows: 240px auto auto`. Globe canvas 240×240 in row 1, kicker + title in rows 2–3. Tight fit; matches Turkey |
| 5 | **NAC Residence Index — globe + section size (DESKTOP)** | Banner `min-height: 360px` — gives the 300px globe a **30px breathing room each side**. No vertical bloat |
| 6 | **Article URL → specific blog PDP** | Each `<a class="article-cta-banner">` href must point to a specific blog post (e.g. `blog.nomadassetcollective.com/<slug>/`), NOT to the bare homepage `blog.nomadassetcollective.com/`. Generic blog cards (from the dedupe rule) are exempt |
| 7 | **Charts render correctly (desktop + mobile)** | All 4 canvases present: `#radarChart`, `#citizenshipChart`, `#compareChart`, `#matrixChart`. Matrix has the `aspectRatio: 1` mobile / `2` desktop swap. No `max-height` constraints below 200px |

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
