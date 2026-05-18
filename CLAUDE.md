# NAC Program Brochures — Claude session memory

> **Repo purpose:** Single-file HTML brochures for 12 country programs (RBI / CBI / LTR). HTML is the source of truth; pushes to `main` auto-sync to WordPress via REST.
>
> **Master template:** `Brochures html/turkey-cbi_8.html` — every other brochure replicates from here.
>
> **Canonical reference:** [`TURKEY-TEMPLATE.md`](./TURKEY-TEMPLATE.md) — design system, components, replication checklist.

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
```

**🎉 All 12 brochures at full Turkey parity.**

### What's at parity across all 12 brochures

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

Nothing critical. The 11 non-Turkey brochures still use the legacy `VI_STRINGS`/`EN_STRINGS` string-replace pattern instead of Turkey's newer `data-vi`/`data-en` attribute pattern. Both work; data-attr is just more robust to text edits. Translation content is already complete in the legacy arrays — future migration to data-attr is mechanical.

### How chart bilingual works on the 11

Turkey uses `buildCharts(lang)` that destroys and recreates charts on toggle. The 11 others use a lighter-weight approach (a post-`setLang` translator script that was injected into each brochure's HTML during initial replication):

- Walks `Chart.instances` (Chart.js v4 global)
- Snapshots original VI labels on first run
- Translates dataset labels / axis titles / chart labels using a shared VI→EN dictionary (countries + common axis terms)
- Attaches a click listener to `#btn-vi` / `#btn-en` that re-runs the translation on every toggle

This avoids rewriting each brochure's chart code while still flipping country names from "Thổ Nhĩ Kỳ" → "Türkiye" etc. when EN is clicked. The translator is checked by `daily_en_audit.py` (check #3).

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
├── apply_listings.py                   ← refresh Live Listings spotlight from Property Hub
├── build_preview_index.py              ← regenerate index.html for GitHub Pages preview
└── patch_ph_catalog.py                 ← Property Hub catalog patcher
```

Run with no argument to apply to all 12 (or all relevant). Run with `<alias>` to target one. All scripts print counts and second-run reports `0` if no upstream change.

### Workflows

```
.github/workflows/
├── pull-notion.yml         ← cron */10 — Notion → HTML → coverage → WP push → live snapshot
├── daily-en-audit.yml      ← cron daily 02:00 UTC — toggle/sections/charts → GitHub Issue
├── wp-sync.yml             ← on push to main — apply_listings + sync_brochures to WP
└── patch-ph-catalog.yml    ← manual dispatch — Property Hub catalog patches
```

---

## 4. WordPress traps (live page only — preview is fine)

WP's content sanitiser mangles inline JS in two non-obvious ways. Both bit us this session.

### Trap 1: Inline `onclick=""` attributes get stripped

KSES strips inline event handlers when content is saved to ACF `raw_html_code` (XSS protection). Buttons that rely on `onclick="setLang('en')"` appear intact in source but the attribute is gone on live.

**Fix:** bind via `addEventListener` (already present in every brochure's bilingual engine + verified by `daily_en_audit.py` check #1).

### Trap 2: Backslash-escaped quotes inside `<script>` get unescaped

WP rewrites `\"foo\"` → `"foo"` inside `<script>` content, terminating the string early and producing a SyntaxError. The bilingual engine had `\"bàn đạp\"` and `\"springboard\"` — that was enough to crash the entire script block and silently kill the EN toggle.

**Fix:** use Unicode curly quotes `"…"` (U+201C / U+201D) inside JS strings. Looks identical, survives WP.

**Never use `\"` in `<script>` content destined for WP.**

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

## 8a. Per-brochure EN audit progress (jsdom-verified, 0 VN remnants)

| Brochure | Status | Notes |
|---|---|---|
| Portugal | partial | live still shows VN remnants (user accepted, deprioritised) |
| Greece | ✓ | ~95% per user; minor bleed in chart legends + tax table |
| Cyprus | ✓ | 8/8, verified live |
| UAE | ✓ | 8/8 locally; live has minor CTA/chart bleed per user (acceptable) |
| UK | ✓ | 7/8 locally (only #6 is Notion data gap — `s01_article_cta_url` empty); 308 VI/EN pairs; user confirmed ~95% live then mop-up via #76 closed the rest |
| Remaining 7 | not yet audited via jsdom | malaysia, malta, newzealand, panama, stkitts, thailand, turkey |

### Simulator regex gotcha (fixed in #76)

The jsdom simulator's `VN_UNIQUE` regex used to match only "uniquely Vietnamese" diacritics (`ạ ậ ặ ế ề ể ễ ệ` etc.) and silently skipped common single-mark vowels (`á à ã ạ ó ò ô è í ú ý`). Strings like "So Sánh UK vs Hy Lạp" and "VN: 2% trên giá bán" passed the audit while leaving visible VN on the live page. The widened regex in `#76` covers all Vietnamese diacritics — earlier "verified" brochures (Greece, Cyprus, UAE) may have latent bleeds that the next daily-en-audit run will surface. False positives on Spanish/Portuguese names are still filtered via the `ALLOWED` set + 2-word minimum.

---

## 9. Linked docs

- [`TURKEY-TEMPLATE.md`](./TURKEY-TEMPLATE.md) — canonical design reference (component inventory + replication checklist)
- [`BROCHURE-NOTION-SCHEMA.md`](./BROCHURE-NOTION-SCHEMA.md) — Notion DB schema for brochure content
- [`BROCHURE-URLS.md`](./BROCHURE-URLS.md) — WP slugs + page IDs for all 12
- [`NAC-LINKS.md`](./NAC-LINKS.md) — canonical URLs (booking, WhatsApp, social, etc.)
- [`WP-SYNC-SETUP.md`](./WP-SYNC-SETUP.md) — GitHub Action ↔ WP REST API plumbing
- [`PB-TEMPLATE.md`](./PB-TEMPLATE.md) — older template spec (paywall, sections, JS hooks)
- [`CLAUDE-AI-PROJECT-INSTRUCTIONS.md`](./CLAUDE-AI-PROJECT-INSTRUCTIONS.md) — instructions for the Claude.ai web project
