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
turkey-cbi_8.html        15/15   ← master, fully aligned
cyprus-rbi_3_3.html      12/15
greece-rbi_1_2.html      12/15
malaysia-mm2h.html       12/15
malta-rbi_1_3.html       12/15
newzealand-rbi_1 (3).html 12/15
panama-rbi_.html         12/15
portugal-gv.html         11/15   ← has matrix chart, needs the fix
stkitts-nevis.html       12/15
thailand-rbi_1 (2).html  12/15
uae-rbi_1_7.html         12/15
uk-rbi_1 (2).html        12/15
```

### What's already at parity (11 of 11 brochures + Turkey)

✓ Sidebar CTA cream-glass pill (4 colour-coded chips)
✓ Header / sidebar booking → Google Calendar
✓ Header / sidebar WhatsApp icon as SVG (no 💬 emoji)
✓ NAC consultation footer "Book a Free Consultation" → Google Calendar
✓ `.nac-btn-wa` icon brand green
✓ **NAC Index banner with embedded canvas globe** (§07)
✓ **12 KPI icon pills** (desktop in banner, mobile in white strip)
✓ Real `og:image` covers (no Unsplash placeholders)
✓ WP-safety `addEventListener` for lang buttons
✓ No `\"` in script blocks (no KSES unescape risk)

### What's left (3 items per brochure)

| Item | Why it's blocked | Path forward |
|---|---|---|
| Bilingual `data-vi`/`data-en` migration | Needs EN translation content per brochure | Pull from Notion DB or hand-translate per brochure (~150–250 strings each) |
| `buildCharts(lang)` wrapper | Needs EN labels for chart axes/datasets/tooltips | Add VI/EN dictionary per brochure, mirror Turkey's `CHART_LBLS` |
| Article CTA banner-card structure | Existing brochures still use text-only `.article-cta` blocks | Per-brochure structural rewrite (preserve URL + title); then run `refresh_article_covers.py` |

Portugal also needs the **matrix chart aspectRatio + collapsible** fix (only Portugal has a matrix chart among the 11).

---

## 3. Reusable tools — all idempotent

```
tools/
├── check_brochure_parity.py     ← the workloop; audit any brochure against Turkey
├── install_nac_index_banner.py  ← inject NAC Index banner + globe + 12 KPI pills + WP-safety
├── refresh_article_covers.py    ← pull og:image for every article-cta-banner
├── refine_sidebar_cta.py        ← cream-glass sidebar pill with 4 colour-coded chips
├── refine_nac_btn.py            ← footer Book CTA → Google + WhatsApp icon green
└── rewire_cta_links.py          ← Calendly → Google + header pill → Google + WhatsApp emoji → SVG
```

Run with no argument to apply to all 11 (Turkey is the source-of-truth, skipped). Run with `<alias>` to target one. All scripts print counts and second-run reports `0` if no upstream change.

---

## 4. WordPress traps (live page only — preview is fine)

WP's content sanitiser mangles inline JS in two non-obvious ways. Both bit us this session.

### Trap 1: Inline `onclick=""` attributes get stripped

KSES strips inline event handlers when content is saved to ACF `raw_html_code` (XSS protection). Buttons that rely on `onclick="setLang('en')"` appear intact in source but the attribute is gone on live.

**Fix:** bind via `addEventListener` (see `install_nac_index_banner.py` and Turkey's bilingual engine).

### Trap 2: Backslash-escaped quotes inside `<script>` get unescaped

WP rewrites `\"foo\"` → `"foo"` inside `<script>` content, terminating the string early and producing a SyntaxError. The bilingual engine had `\"bàn đạp\"` and `\"springboard\"` — that was enough to crash the entire script block and silently kill the EN toggle.

**Fix:** use Unicode curly quotes `"…"` (U+201C / U+201D) inside JS strings. Looks identical, survives WP.

**Never use `\"` in `<script>` content destined for WP.**

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

The parity check (#1 and #2) catches both cases.

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
    └─→ pulled to local HTML (manually for now; future: build_brochures.py)
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

### Audit + fix everything you can

```bash
python tools/check_brochure_parity.py                 # see current state
python tools/rewire_cta_links.py                      # CTAs to Google Calendar
python tools/refine_sidebar_cta.py                    # sidebar pill
python tools/refine_nac_btn.py                        # NAC footer + WhatsApp green
python tools/install_nac_index_banner.py              # NAC Index banner + globe + pills
python tools/refresh_article_covers.py                # cover images
python tools/check_brochure_parity.py                 # verify after
```

### Bring one brochure to full Turkey parity (when EN translations are ready)

1. Run the structural scripts above on that brochure
2. Lift the bilingual data-vi/data-en attrs from Notion → patch each section by hand or via a custom slice script
3. Lift the `buildCharts(lang)` wrapper and chart label dicts from Turkey
4. Add `addEventListener` bind block (auto-installed by `install_nac_index_banner.py`)
5. Replace any `\"` in scripts with `"` U+201C / U+201D
6. Run `python tools/check_brochure_parity.py <alias>` — should show 15/15

### Watch out for

- **Inline `onclick=""`** anywhere you want JS to run on WP
- **`\"` inside `<script>`** — use Unicode curly quotes instead
- **Hardcoded country names** in chart labels — gate behind `CHART_LBLS[lang]`
- **Direct Notion API key in client code** — always proxy via the Cloudflare Worker

---

## 8. PRs shipped this session

`#28` Turkey EN hero · `#29` mobile toggle fix · `#30` JS syntax fix · `#31` TOC + eyebrows · `#32` Turkey slices 3–11 · `#33` article CTA banner · `#34` listings/charts/NAC Index banner · `#35` og:image cover script · `#36` light-bg banner · `#37` globe + matrix + cross-brochure CTA · `#38` sidebar CTA pill · `#39` NAC footer CTA + green WhatsApp · `#40` matrix mobile aspectRatio + docs · `#41` EN toggle initial fix · `#42` URGENT EN toggle real fix (KSES unescape)

---

## 9. Linked docs

- [`TURKEY-TEMPLATE.md`](./TURKEY-TEMPLATE.md) — canonical design reference (component inventory + replication checklist)
- [`BROCHURE-NOTION-SCHEMA.md`](./BROCHURE-NOTION-SCHEMA.md) — Notion DB schema for brochure content
- [`BROCHURE-URLS.md`](./BROCHURE-URLS.md) — WP slugs + page IDs for all 12
- [`NAC-LINKS.md`](./NAC-LINKS.md) — canonical URLs (booking, WhatsApp, social, etc.)
- [`WP-SYNC-SETUP.md`](./WP-SYNC-SETUP.md) — GitHub Action ↔ WP REST API plumbing
- [`PB-TEMPLATE.md`](./PB-TEMPLATE.md) — older template spec (paywall, sections, JS hooks)
- [`CLAUDE-AI-PROJECT-INSTRUCTIONS.md`](./CLAUDE-AI-PROJECT-INSTRUCTIONS.md) — instructions for the Claude.ai web project
