# NAC Program Brochures — Claude session memory

> **Repo purpose:** Single-file HTML brochures for 16 country programs (RBI / CBI / LTR). HTML is the source of truth; pushes to `main` auto-sync to WordPress via REST.
>
> **Master template:** `Brochures html/cyprus-rbi_3_3.html` — Cyprus is the current canonical reference after the May 2026 polish sweep (clean header lock, slim breadcrumb, pulsing live-tag on the listings section, mobile tax-table pill disclaimer, left-aligned chart Y-labels). Every other brochure replicates from here.
>
> Historical master: `Brochures html/turkey-cbi_8.html` (the original template that seeded the family). Turkey is still parity-compliant but the visual polish is on Cyprus.
>
> **Canonical reference:** [`TURKEY-TEMPLATE.md`](./TURKEY-TEMPLATE.md) — design system, components, replication checklist (still valid; updated diffs live in Cyprus).

---

## 1. Workloop — verify parity any time

```bash
python tools/check_brochure_parity.py              # audit all 12 brochures
python tools/check_brochure_parity.py portugal     # one brochure
python tools/check_brochure_parity.py --verbose    # show every check (passing and failing)
```

The audit runs **15 checks** per brochure, lifted from TURKEY-TEMPLATE.md:

| # | Check | What it verifies |
|---|---|---|
| 1 | WP-safety: `addEventListener` bound to lang btns | KSES doesn't strip inline `onclick`, so toggle works on WP |
| 2 | WP-safety: no `\"` in `<script>` blocks | KSES doesn't unescape `\"` → `"`, breaking JS strings |
| 3 | Sidebar CTA cream-glass pill (4 chips) | `tc-cal` / `tc-wa` / `tc-idx` / `tc-cmp` colour-coded |
| 4 | Header / sidebar booking → Google Calendar | Routes to `calendar.app.google/gnbtNBTBDKuHUasw7` |
| 5 | WhatsApp: SVG (not 💬 emoji) | Proper brand icon with `#25D366` |
| 6 | Footer Book CTA → Google Calendar | `<a class="nac-btn">` in NAC consultation footer |
| 7 | `.nac-btn-wa` icon fill `#25D366` | Icon green inside the dark transparent box |
| 8 | Bilingual `data-vi`/`data-en` coverage | ≥200 attrs = migrated; Turkey has ~254 |
| 9 | `buildCharts(lang)` wrapper | Charts switch country names VI ↔ EN |
| 10 | Matrix chart mobile aspectRatio + collapsible | Square on mobile, 2:1 on desktop, tap-to-expand |
| 11 | NAC Index banner with canvas globe | §07 banner with animated rotating globe |
| 12 | 12 KPI icon pills | Desktop (banner) + mobile (white strip) |
| 13 | Article CTA: banner-card structure | Cover-image card, not text-only |
| 14 | Article cover: real `og:image` (no Unsplash placeholder) | Pulled from each article's meta tag |
| 15 | All `<script>` blocks parse cleanly | `node --check` finds no SyntaxError |

Output: `✓ N/15` per brochure with bar chart and per-check details on failures.

---

## 2. Current state (post-session)

```
turkey-cbi_8.html        15/15  ✓
cyprus-rbi_3_3.html      15/15  ✓
greece-rbi_1_2.html      15/15  ✓
malaysia-mm2h.html       15/15  ✓
malta-rbi_1_3.html       15/15  ✓
newzealand-rbi_1 (3).html 15/15 ✓
panama-rbi_.html         15/15  ✓
portugal-gv.html         15/15  ✓
stkitts-nevis.html       15/15  ✓
thailand-rbi_1 (2).html  15/15  ✓
uae-rbi_1_7.html         15/15  ✓
uk-rbi_1 (2).html        15/15  ✓
antigua-cbi.html         15/15  ✓
italy-investor.html      15/15  ✓
spain-gv.html            15/15  ✓  (LEGACY, closed 03/04/2025 — Archived in Notion)
montenegro-rbi.html      15/15  ✓
```

**🎉 All 16 brochures at full Turkey parity, all 16 wired to WordPress.**

### What's at parity across all 16 brochures

✓ Sidebar CTA cream-glass pill (4 colour-coded chips)
✓ Header / sidebar booking → Google Calendar
✓ Header / sidebar WhatsApp icon as SVG (no 💬 emoji)
✓ NAC consultation footer "Book a Free Consultation" → Google Calendar
✓ `.nac-btn-wa` icon brand green
✓ **NAC Index banner with embedded canvas globe** (§07)
✓ **12 KPI icon pills** (desktop in banner, mobile in white strip)
✓ **Article CTA banner-card structure** (cover-image banner cards)
✓ Real `og:image` covers (no Unsplash placeholders)
✓ WP-safety `addEventListener` for lang buttons
✓ No `\"` in script blocks (no KSES unescape risk)
✓ Bilingual support (legacy `VI_STRINGS`/`EN_STRINGS` arrays on the 11; Turkey uses the more robust `data-vi`/`data-en` attrs)
✓ Matrix chart mobile fix (Portugal, the only one with this chart)

### What's left

**Bleeding VI in EN version** — UAE, UK, St Kitts still have Vietnamese text visible in non-listing sections when EN is toggled. This is the legacy `VI_STRINGS/EN_STRINGS` coverage gap (not a regression). Requires the full EN audit loop per brochure (§7 recipe). The listing section itself is now fully bilingual via `data-vi`/`data-en` + the Pass-0 data-attr walker (PR #128).

**WP cache lag** — some CSS changes (breadcrumb lock, tax-table mobile) are in the HTML source but take time to appear on live WP pages. Hard-refresh or wait for the next cron tick.

### How chart bilingual works on the 11

Turkey uses `buildCharts(lang)` that destroys and recreates charts on toggle. The 11 others use a lighter-weight approach (a post-`setLang` translator script that was injected into each brochure's HTML during initial replication):

- Walks `Chart.instances` (Chart.js v4 global)
- Snapshots original VI labels on first run
- Translates dataset labels / axis titles / chart labels using a shared VI→EN dictionary (countries + common axis terms)
- Attaches a click listener to `#btn-vi` / `#btn-en` that re-runs the translation on every toggle

This avoids rewriting each brochure's chart code while still flipping country names from "Thổ Nhĩ Kỳ" → "Türkiye" etc. when EN is clicked. The translator is checked by `daily_en_audit.py` (check #3).

### Pass-0 data-attr walker (PR #128)

All 16 brochures now have a "Pass 0" in setLang that runs BEFORE the legacy VI_STRINGS replacement:

```javascript
document.querySelectorAll('[data-vi][data-en]').forEach(function(el) {
  var val = el.getAttribute('data-' + lang);
  if (val.indexOf('<') >= 0) el.innerHTML = val;
  else el.textContent = val;
});
```

This means any element with `data-vi`/`data-en` attributes (listings section, live-tag, section headers, footnotes) toggles cleanly without needing VI_STRINGS/EN_STRINGS entries. Future `apply_listings.py` renders are automatically picked up.

---

## 3. Reusable tools — all idempotent

```
tools/
├── check_brochure_parity.py            ← audit any brochure against Turkey (15 checks)
├── check_en_translation_coverage.py    ← static EN coverage on local HTML
├── check_live_en_coverage.py           ← fetch live WP, run coverage
├── daily_en_audit.py                   ← daily 8-check audit (incl. jsdom EN-render)
├── simulate_en_render.js               ← jsdom truth: setLang('en') in real DOM, count VN remnants
├── simulate_en_render.py               ← DEPRECATED (BS4 normalizes differently from browser, lies about remnants)
├── add_translation_pairs.py            ← inject manual {vi: en} pairs into VI_STRINGS/EN_STRINGS
├── check_brochure_payload.py           ← JSON schema validator for data/*_payload.json
├── pull_from_notion.py                 ← Notion → data/<alias>_payload.json
├── inject_notion_en_to_html.py         ← payload → VI_STRINGS/EN_STRINGS in HTML
├── refresh_article_covers.py           ← pull og:image for every article-cta-banner
├── apply_listings.py                   ← refresh Live Listings spotlight from Property Hub (bilingual, pin curation)
├── build_preview_index.py              ← regenerate index.html for GitHub Pages preview
├── pull_overview_from_notion.py        ← 🎴 NAC - Overview Deck DB → regenerate overview card deck
├── scan_qa_tracker.py                  ← ✅ NAC - QA Tracker DB → .diagnostics/qa-status.md
├── inject_data_attr_walker.py          ← add Pass-0 data-vi/data-en walker to all legacy setLang
├── inject_twemoji.py                   ← inject Twemoji flag-image fallback (Windows/Android show codes)
├── repoint_listings_to_clp.py          ← repoint "All RBI properties →" link to /property-hub-bat-dong-san/<slug>/ CLP
├── lock_header_style.py                ← global header style lock (Greece template values)
├── lock_breadcrumb_v2.py               ← breadcrumb typography lock (high specificity)
├── sec_live_tag_css.py                 ← pulsing "● ĐANG MỞ BÁN" live-tag CSS
├── tax_table_mobile_v2.py              ← hide tax notes column on mobile + pill disclaimer
├── chart_y_left_align.py               ← left-align Y-axis labels on horizontal bar charts
├── listing_ref_top_small.py            ← NAC-ID pill small + top-right
├── header_lang_only_right.py           ← hide nav-links, lang toggle only
├── widen_nac_tools_breakpoint.py       ← CTA pill visible on iPad/tablet (720→1024px)
└── patch_ph_catalog.py                 ← Property Hub catalog patcher
```

Run with no argument to apply to all 16 (or all relevant). Run with `<alias>` to target one. All scripts print counts and second-run reports `0` if no upstream change.

### Workflows

```
.github/workflows/
├── pull-notion.yml             ← cron */10 — Notion → HTML → listings → overview deck → coverage → WP push
├── daily-en-audit.yml          ← cron daily 02:00 UTC — toggle/sections/charts → GitHub Issue
├── intel-daily.yml             ← cron daily 03:00 UTC — scrape policy/pricing/community → daily digest Issue
├── intel-weekly-digest.yml     ← cron Mon 04:00 UTC — rollup → GitHub Issue with checkbox tasks
├── intel-apply.yml             ← on issue edit — ticked boxes → Notion + HTML + WordPress (tick-to-live)
├── qa-tracker-scan.yml         ← cron daily 09:00 UTC — scan Notion QA tracker → .diagnostics/qa-status.md
├── wp-sync.yml                 ← on push to main — apply_listings + sync_brochures to WP
└── patch-ph-catalog.yml        ← manual dispatch — Property Hub catalog patches
```

### Weekly investment-migration intel (Notion auto-updates)

See [`INTEL-PIPELINE.md`](./INTEL-PIPELINE.md). Daily sweep of policy / pricing / Reddit / industry press for the 12 countries → daily digest GitHub Issue with `- [ ]` checkboxes per proposed Notion update → ticking a box runs the tick-to-live workflow (PATCH Notion + payload → inject HTML → push WordPress in one run). WhatsApp delivery is documented as a follow-up (needs Twilio / Meta Cloud API).

```
tools/
├── intel_sources.py    ← per-country sources (official, agency, industry press, Reddit terms)
├── intel_gather.py     ← daily scraper → .diagnostics/weekly-intel/<date>/<alias>.json
├── intel_digest.py     ← weekly aggregator → issue markdown with machine-readable trailers
└── intel_apply.py      ← parses [x] checkboxes from issue body → PATCH Notion DB

### Notion DBs (3 total)

| DB | ID | Purpose |
|---|---|---|
| 🔖 NAC - Brochures Meta-data | `35f48ec25e8680f69c3dc5ad538e7ca8` | Per-brochure content (hero, sections, scores) |
| 🎴 NAC - Overview Deck | `26d8e7b69c4840f19adbac784d257330` | Cards on the overview page (editable → 10min sync) |
| ✅ NAC - QA Tracker | `92318d9b81604764b8f620f64bcce83e` | Live QA checklist with native checkboxes + daily cron scan |

---

## 4. WordPress traps (live page only — preview is fine)

WP's content sanitiser mangles inline JS in two non-obvious ways. Both bit us this session.

### Trap 1: Inline `onclick=""` attributes get stripped

KSES strips inline event handlers when content is saved to ACF `raw_html_code` (XSS protection). Buttons that rely on `onclick="setLang('en')"` appear intact in source but the attribute is gone on live.

**Fix:** bind via `addEventListener` (already present in every brochure's bilingual engine + verified by `daily_en_audit.py` check #1).

### Trap 2: WP strips ONE LEVEL OF ALL BACKSLASHES from the pushed content (wp_unslash)

**Root cause identified 2026-07-07:** it is not just `\"`. WP REST runs `wp_unslash`
on the request body, so EVERY backslash in the ACF value loses one level:
`\"` → `"`, `\'` → `'`, `\/` → `/`, `\n` → `n`, `\s` → `s`. Verified live: the
quiz page's `NQ.pick(\''+…)`, the index page's `icon:'<svg width=\'20\'…'`, and
a `\/` inside a deck regex all arrived corrupted and killed their script blocks
with SyntaxErrors. Brochure `\n` escapes in EN_STRINGS had been silently landing
as a stray `n` for months. (Same behavior the Property Hub repo documents for
its own WP sync.)

**Fix (systemic, in `sync_brochures.py::push_page_content`):** all backslashes
are pre-doubled (`content.replace('\\', '\\\\')`) before the POST, so the
stored value round-trips intact. The response's `acf` field contains the
un-slashed (original) value, so the length verification still compares against
the original content.

Historical workaround (still fine, no longer required): Unicode curly quotes
`"…"` (U+201C / U+201D) inside JS strings instead of `\"`.

### Trap 3: Multi-line string literals inside VI_STRINGS / EN_STRINGS arrays

A literal newline inside `"..."` is a SyntaxError. UAE shipped with one — a bullet-point list typed verbatim into a `"..."` string. Because the bilingual engine, the chart constructors, and the score-bar translator all live in the same `<script>` block, the parse error silently killed EN toggle, all 5 charts, and the score bars on live.

**Fix (HTML):** join to a single line with `\n` escapes. Verified by the parity check #15 (`node --check` on every `<script>` block).

**Fix (root cause, May 2026):** `tools/inject_notion_en_to_html.py`'s `js_escape_string` now also escapes literal `\n` / `\r` / `\t` as JS escape sequences before wrapping in quotes — so a Notion bullet-list field with embedded newlines lands as `"…\n…\n…"` in the array, not as a raw multi-line literal. KSES does NOT strip `\n` inside `<script>` (only `\"`), so this is safe on WordPress. If this regresses, the smoke test is: after running the injector, every brochure's parity check #15 must pass.

**If a brochure's audit shows EN toggle + charts both broken at once, look for a multi-line string literal first — it's almost always the cause.** This bit us on Malta + UAE + Panama in May 2026 when a new Notion bullet-list field hit all 3 in a single cron tick.

### Verification recipe

```bash
curl -s "<live-url>" > /tmp/live.html
python3 -c "
import re; html=open('/tmp/live.html').read()
scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
print(scripts[4])  # bilingual engine is usually script #4
" | node --check -
# If SyntaxError → WP has mangled something. Diff against local.
```

The parity check (#1, #2, #15) catches all three traps.

---

## 5. Git workflow

```
edit brochure (or run tooling)
   → commit on a feature branch (claude/...)
   → push, open PR
   → mcp__github__merge_pull_request (squash)
   → GitHub Action `wp-sync` triggers on push to main
   → live WP page updates within ~30s
```

`Brochures html/*.html` is the source of truth. Pushes to non-`main` branches do NOT sync to WP — they're for the GitHub Pages preview at `rayvtt.github.io/NAC-Program-Brochures/`.

---

## 6. Architecture cheat sheet

```
[NAC Brochures DB]    Notion (35f48ec25e8680f69c3dc5ad538e7ca8)
    │
    └─→ pulled into data/*_payload.json by tools/pull_from_notion.py
        (cron every 10 min via .github/workflows/pull-notion.yml)
        │
        └─→ Brochures html/<file>.html  ← source of truth
            │
            ├─→ GitHub Pages preview (every branch)
            └─→ sync_brochures.py → ACF raw_html_code → WP page (main only)
                    │
                    └─→ nomadassetcollective.com/brochures/<slug>
```

URL pattern: `https://nomadassetcollective.com/brochures/<wp-slug>/` — see `BROCHURE-URLS.md`.

WP-sync setup: `WP-SYNC-SETUP.md`. Notion schema: `BROCHURE-NOTION-SCHEMA.md`.

---

## 7. Quick recipes

### Status / audit

```bash
python tools/check_brochure_parity.py                 # structural parity vs Turkey (15 checks)
python tools/check_en_translation_coverage.py         # local EN coverage report
python tools/check_live_en_coverage.py                # fetch live, run coverage
python tools/daily_en_audit.py                        # 3-check audit (toggle / sections / charts)
python tools/check_brochure_payload.py data/turkey_payload.json  # validate one payload
```

### Manual Notion → live (force a sync now)

```bash
python tools/pull_from_notion.py             # refresh data/*_payload.json
python tools/inject_notion_en_to_html.py     # merge into VI_STRINGS / EN_STRINGS
python tools/refresh_article_covers.py       # pull article og:images
python sync_brochures.py --all               # push to WordPress
```

This is what the `pull-notion.yml` cron does automatically every 10 minutes.

### Bring one brochure to full Turkey parity (when EN translations are ready)

The auto-sync covers most of it. Manual fallback steps:

1. Ensure the brochure has the structural parity (cron handles this — see `check_brochure_parity.py` for 15-check audit)
2. Add EN translations in Notion (the `*_en` fields per section). The next cron tick picks them up.
3. If text drift exists between Notion VI and HTML DOM (flagged by `check_en_translation_coverage.py`), align either side
4. Run `python tools/check_brochure_parity.py <alias>` and `python tools/daily_en_audit.py <alias>` — both should pass

### Per-brochure EN audit loop (the Portugal → Greece → Cyprus → UAE workflow)

When a brochure's live EN toggle is patchy or charts are missing, this is the loop:

```bash
# 1. Truth — what does a real browser actually see on EN click?
node tools/simulate_en_render.js "Brochures html/<file>.html"
node tools/simulate_en_render.js "https://nomadassetcollective.com/brochures/<slug>/"
```

If eval fails → look for a syntax error in the bilingual engine (Trap 3 above).
If many VN remnants → run setLang upgrade + add translation pairs:

```bash
# 2. Make sure setLang has descending-length sort + Pass 2 universal walker
#    (Cyprus is the reference — copy its setLang body if needed)

# 3. For each remaining VN remnant, write a {vi: en} pair using the
#    ORIGINAL DOM text (not the post-replacement form the simulator shows).
#    DOM has "Hy Lạp", simulator shows "Greece" — use "Hy Lạp" as the key.
echo '{ "<original VI from DOM>": "<EN translation>" }' > /tmp/pairs.json
python tools/add_translation_pairs.py <alias> /tmp/pairs.json

# 4. Re-simulate. Iterate until 0 remnants.
node tools/simulate_en_render.js "Brochures html/<file>.html"

# 5. Verify all 8 audit checks pass
python tools/daily_en_audit.py <alias> --local

# 6. Commit → PR → squash-merge → wp-sync fires → verify on live
```

**Gotchas learned:**
- WordPress sanitiser strips `$` followed by digits in some contexts. If your translation key uses `$500K`, the DOM might have `00K` — match the DOM-corrupted form.
- Short pairs like `"UAE"→"United Arab Emirates"` or `"Đầu tư"→"Investment"` cause partial replacements inside longer Vietnamese sentences. The descending-length sort + adding the full-sentence pair fixes this. Or change the short pair to a no-op (`"UAE"→"UAE"`).
- `innerHTML` returns `&amp;` for `&` in attribute and text content. Your translation key has to match the encoded form for elements where Pass 1 reads `innerHTML`.

### Watch out for

- **Inline `onclick=""`** anywhere you want JS to run on WP
- **`\"` inside `<script>`** — use Unicode curly quotes instead
- **Hardcoded country names** in chart labels — gate behind `CHART_LBLS[lang]`
- **Direct Notion API key in client code** — always proxy via the Cloudflare Worker

---

## 8. PRs shipped this session

`#28` Turkey EN hero · `#29` mobile toggle fix · `#30` JS syntax fix · `#31` TOC + eyebrows · `#32` Turkey slices 3–11 · `#33` article CTA banner · `#34` listings/charts/NAC Index banner · `#35` og:image cover script · `#36` light-bg banner · `#37` globe + matrix + cross-brochure CTA · `#38` sidebar CTA pill · `#39` NAC footer CTA + green WhatsApp · `#40` matrix mobile aspectRatio + docs · `#41` EN toggle initial fix · `#42` URGENT EN toggle real fix (KSES unescape) · `#43` Turkey replication: NAC Index banner + globe + KPI pills to 11 brochures + parity workloop + `CLAUDE.md` · `#44` Article CTA banner-card migration across 11 + Portugal matrix chart fix · `#45` parity check recognizes legacy bilingual · `#46` chart translator → all 12 at 15/15 · `#47` non-invasive chart translator + bigger globe banner · `#48` dedupe duplicate article CTA URLs · `#49` globe mobile stack layout · `#50` globe CSS Grid bulletproof · `#51` tighten globe banner fit · `#72` NAC Index banner specificity (300px lock across all 12) · `#73` UAE multi-line string SyntaxError + 147 EN pairs (charts + toggle restored) · `#75` UK setLang upgrade + 87 EN pairs + chart translator (0 VN remnants) · `#76` UK mop-up bleeds (So Sánh CTA + tax cells) + widened simulator regex

### May 2026 polish sweep (PRs #94–#130)

`#94` Italy / Spain / Montenegro brochures + hero/listings/tax fixes · `#95–#96` mobile header: only "NAC BROCHURE 2026" · `#97` Cyprus listings refresh · `#98` listings pin curation (Cyprus Del Mar + Blu Marine) · `#99` header tagline only (all viewports) · `#100` drop "K" suffix from listing prices · `#101` header tagline 9px · `#102` UK listings + auto-refresh on 10-min cron · `#103` UK pin White City Living + London Dock · `#104` overview live cards IT/ES/MG · `#105` listings full EN translation + flag fix + `&amp;amp;` fix · `#106` remove listing location pill · `#107` Montenegro Perast image · `#108` Notion overview deck DB + cron sync · `#109` header right = lang toggle only · `#110` header global style lock (Greece template) · `#111` breadcrumb typography lock · `#112` tax table mobile (hide notes col + pill disclaimer) · `#113` §01 title VI word order · `#114` §01 card labels rephrased · `#115` radar chart title unified · `#116` NAC-ID pill top-right small · `#117` tax pill disclaimer upgrade · `#118` chart Y-axis left-align · `#119` pulsing live-tag badge · `#120` breadcrumb V2 + Cyprus master in CLAUDE.md · `#121` checklist gaps (Bảo Lãnh + radar labels + live-tag gap) · `#122` daily QA tracker scan (Google Sheets) · `#123` QA tracker migration to Notion · `#124` QA cache refresh · `#125` live-tag gap 20px · `#127` Twemoji flag emojis on overview · `#128` Pass-0 data-attr walker for listing VI bleed fix · `#129` live-tag dot structural margin fix · `#130` live-tag dot gap halved + centered

## 8a. Per-brochure EN audit progress (jsdom-verified, 0 VN remnants)

| Brochure | Status | Notes |
|---|---|---|
| Portugal | partial | live still shows VN remnants (user accepted, deprioritised) |
| Greece | ✓ | ~95% per user; minor bleed in chart legends + tax table |
| Cyprus | ✓ | 8/8, verified live |
| UAE | ✓ | 8/8 locally; live has minor CTA/chart bleed per user (acceptable) |
| UK | ✓ | 7/8 locally (only #6 is Notion data gap — `s01_article_cta_url` empty); 308 VI/EN pairs; user confirmed ~95% live then mop-up via #76 closed the rest |
| Malta | ✓ | 8/8, verified live (Trap 3 fixed at root in injector via PR #80) |
| St Kitts | ✓ | 8/8 locally; 141 VI/EN pairs added (155 → 0 VN remnants); setLang upgraded to Cyprus reference (desc-length sort + Pass 2 universal walker); 3 low-coverage sections flagged in Notion but those are VI/HTML text-drift, not user-visible remnants |
| Thailand | ✓ | 8/8 fully passing locally (no section gaps); 197 VI/EN pairs added (182 → 0 VN remnants in 4 rounds); setLang upgraded; included EN translation for the random article title pushed by PR #79's fallback |
| Panama | ✓ | 7/8 locally — Panama needed an extra round (PR #86) after user spotted bleeds the simulator's false-positive filter had hidden: `<strong>không</strong>` inside §01 info-text + a bilingual disclaimer header. Fixed with full Pass-1 innerHTML pair + EN-only disclaimer. `tools/dump_real_vn.js` (added in #86) filters to VN-only diacritics so Spanish loanwords don't drown out real bleeds. 132 VI/EN pairs added total; setLang upgraded. |
| Malaysia | ✓ | 8/8 locally (no section gaps after final round); 160 VI/EN pairs added (163 → 0 VN remnants in 3 rounds); setLang upgraded; round 2 fixed 5 sec-sub/info-text/tl-body pairs where I had assumed truncated `dump_real_vn` output rather than checking the actual DOM (lesson: always grep the brochure for full text, not the diagnostic's first 300 chars). PR #88 also added 2 missing chart-axis CHART_VI_EN keys (`Tháng đến cư trú/quốc tịch`, `Thuế thu nhập cá nhân tối đa (%)`) — chart bleeds are a separate audit pass since the simulator doesn't see canvas-rendered text |
| New Zealand | ✓ | 8/8 fully passing locally (no section gaps); 171 VI/EN pairs added (168 → 0 VN remnants in 2 rounds); setLang upgraded; chart-axis CHART_VI_EN keys added at the same time as the DOM pairs (lesson from Malaysia: bundle chart-label fixes into the main audit pass) |
| Turkey | ✓ | 8/8 fully passing locally. Turkey is the master template — uses `data-vi`/`data-en` attribute pattern, not legacy `VI_STRINGS`. 22 stale paywall/tier/comp-table elements had been migrated without their attrs; added them inline. **All 12 brochures now at ✓** (Portugal still partial per user decision). |

### Simulator regex gotcha (fixed in #76)

The jsdom simulator's `VN_UNIQUE` regex used to match only "uniquely Vietnamese" diacritics (`ạ ậ ặ ế ề ể ễ ệ` etc.) and silently skipped common single-mark vowels (`á à ã ạ ó ò ô è í ú ý`). Strings like "So Sánh UK vs Hy Lạp" and "VN: 2% trên giá bán" passed the audit while leaving visible VN on the live page. The widened regex in `#76` covers all Vietnamese diacritics — earlier "verified" brochures (Greece, Cyprus, UAE) may have latent bleeds that the next daily-en-audit run will surface. False positives on Spanish/Portuguese names are still filtered via the `ALLOWED` set + 2-word minimum.

---

## 8b. Partner Gateway in-page copy editor (?edit=1)

`Brochures html/NAC-PARTNERS.html` (WP page 2493, `/brochures/doi-tac-partner-gateway/`) carries the same UX/UI copy-edit module as the Homepage V2 (`NAC---Property-Hub`):

- Every bilingual element has a stable `data-copy="pg-<sha1(vi)[:6]>"` key (108 editable). Open the live page with **`?edit=1`** → click text to edit (the VI/EN toggle switches which language you're editing) → **Publish**.
- Publish dispatches `.github/workflows/apply-partner-copy.yml` via the GitHub API with a fine-grained PAT (localStorage key `nac_gh_token`, **shared with the homepage editor**; the PAT's Repository access must include `NAC-Program-Brochures` with Actions: Read and write, or Publish 404s).
- The workflow runs `tools/apply_partner_copy.py` — patches `data-vi`/`data-en` by key, appends the `PARTNER-COPY-LOG.md` ledger, prepends the inline `<script id="copyLog">` JSON block (cap 40, powers the 📜 history panel). Commit to `main` → `wp-sync.yml` → live in ~2 min.
- WP-safety: no inline handlers, no `\"` in scripts; the copyLog JSON escapes the `<` character as its unicode escape (u003c) so it can't close the script block. Keep parity check #15 green after any editor change.

## 8c. So Sánh comparison tool — Notion-backed data + fortnightly sync

`Brochures html/NAC-SO-SANH.html` (WP page 145, `/brochures/so-sanh/`) is a gated,
standalone 3-way country-comparison tool — access-code landing page (`#gate`),
then pick up to 3 of the 14 live countries and compare economics, immigration
terms, tax, costs, and NAC's own ratings side by side. It does **not** belong to
the 16-brochure parity family (§1–§2 above don't apply to it) and is not part of
the generic brochure `tools/pull_from_notion.py` pipeline — it has its own
Notion DB, its own payload shape, and its own sync tooling:

- **Notion DB**: 🔀 NAC - So Sánh Data — id `6383f817314241a1abbabee6b1be7409`. One
  row per country; schema (identity fields, bilingual `<key> (VI)`/`(EN)` text
  field prefixes, plain-number fields) is the single source of truth in
  [`data/sosanh_schema.py`](./data/sosanh_schema.py) — shared by the pull + patch
  tools below so the two never drift apart. Adding a country: create a Notion
  row with a new, globally-unique 2-letter `code` and tick `live in picker`
  once its data is real (`code` collisions silently overwrite one country's
  lookup with another's in the client's `findCountry()`).
- **Data flow**: Notion → `data/sosanh_payload.json` (semantic shape:
  `{asOf, countries:{<code>:{...}}}`) → regex-patched into `var DB_STATIC = {...};`
  inside `NAC-SO-SANH.html`. The client reads everything by `code` + field key —
  no positional column indexing (that fragility, plus the old Google-Sheet
  `FIXES` override ledger, was retired when this moved off the Sheet).
- **Tools** (mirror the brochure family's `pull_from_notion.py` →
  `inject_notion_en_to_html.py` two-step, adapted for So Sánh's own schema):
  - `tools/pull_sosanh_from_notion.py` — Notion → `data/sosanh_payload.json`.
    Hard-fails on a duplicate `code` or on any literal backslash in the output
    (would corrupt on the next WP push — see §4 Trap 2). `--dry-run` prints
    without writing.
  - `tools/patch_sosanh_snap.py` — payload → `var DB_STATIC` in the HTML via a
    single surgical regex replace (never a full-file regenerate). Re-validates
    zero backslashes on the *patched HTML*, not just the payload. `--dry-run`
    validates without writing.
  - `tools/sosanh_changelog.py` — diffs the git-committed payload against the
    freshly-pulled one on disk (must run **after** the pull, **before** the
    commit), appends a human-readable digest to `SOSANH-SYNC-LOG.md` (newest
    first — the durable "what changed this sync" record), and optionally posts
    the same digest to `NOTIFY_WEBHOOK` (a Google Chat incoming-webhook URL,
    same `cardsV2` shape `nac-marketing-omnichannel`'s `scripts/notify.mjs`
    already posts to) if that secret is set. A missing secret or a failed POST
    is non-fatal — the log entry is the durable record either way.
- **Workflow**: `.github/workflows/pull-sosanh-notion.yml` — cron `0 3 1,15 * *`
  (fortnightly: 1st + 15th of every month, 03:00 UTC) + `workflow_dispatch` with
  a `dry_run` input. Chains pull → patch → changelog → commit → **inline**
  `python sync_brochures.py sosanh` (the `sosanh` alias targets this one page).
  The inline WP push is required, not optional — same GITHUB_TOKEN-commits-
  don't-cascade-trigger-`wp-sync.yml` limitation documented in §4/§5 for
  `pull-notion.yml`.
- **Two independent write paths into the same HTML file, by design**: the
  `?edit=1` in-page copy editor (`apply-sosanh-copy.yml`, §8b's sibling —
  patches the `var I18N = {...}` chrome-copy object literal: hero, nav labels,
  gate strings) and this fortnightly Notion sync (patches `var DB_STATIC`, the
  country data blob) touch disjoint regions of the file, so they never
  conflict structurally — but both commit straight to `main`, so a real git
  merge conflict is still possible if both land in the same short window (seen
  once — resolved by taking whichever side changed the I18N chrome strings,
  since `?edit=1` edits are Ray's explicit live-editor actions).
- **Gate page** (`#gate`): access-code landing screen, styled with a slowly
  twinkling starfield backdrop, an orbiting-dot ring around the "N·A·C" seal
  (spinning conic-gradient ring + a slower counter-rotating dashed ring), and a
  breathing brand-orange radial glow — all `prefers-reduced-motion`-aware
  (animations disabled, falls back to a static seal).

## 9. Linked docs

- [`TURKEY-TEMPLATE.md`](./TURKEY-TEMPLATE.md) — canonical design reference (component inventory + replication checklist)
- [`BROCHURE-NOTION-SCHEMA.md`](./BROCHURE-NOTION-SCHEMA.md) — Notion DB schema for brochure content
- [`BROCHURE-URLS.md`](./BROCHURE-URLS.md) — WP slugs + page IDs for all 12
- [`NAC-LINKS.md`](./NAC-LINKS.md) — canonical URLs (booking, WhatsApp, social, etc.)
- [`WP-SYNC-SETUP.md`](./WP-SYNC-SETUP.md) — GitHub Action ↔ WP REST API plumbing
- [`PB-TEMPLATE.md`](./PB-TEMPLATE.md) — older template spec (paywall, sections, JS hooks)
- [`CLAUDE-AI-PROJECT-INSTRUCTIONS.md`](./CLAUDE-AI-PROJECT-INSTRUCTIONS.md) — instructions for the Claude.ai web project
