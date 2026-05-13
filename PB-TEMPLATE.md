# PB Template — Program Brochure Template System

Single source of truth for what every NAC program brochure must contain and how cross-brochure changes get made. **Never hand-edit a pattern in one brochure without templating it here first.**

---

## Principle

Each cross-brochure pattern has three artefacts:

| Artefact | Lives in | Role |
|---|---|---|
| **Data** | `data/<thing>.py` | Per-country values — the only place you edit when content changes |
| **Generator** | `tools/apply_<thing>.py` | Renders data into HTML; no hand-edits to brochure HTML |
| **Markers** | `<!-- THING START -->` / `<!-- THING END -->` inside each brochure | Where the generator writes |

**Workflow for any cross-brochure change:**
1. Edit `data/<thing>.py`
2. `python tools/apply_<thing>.py` (locally)
3. `git diff` to review
4. Commit & push
5. CI syncs all changed brochures to WP

Never `sed`/find-replace across brochures. Never hand-tune one brochure to look different from the others.

---

## Active patterns

### 1. Live Listings spotlight section

**What:** A "BĐS Đủ Điều Kiện — Đang Mở Bán" section between section #02 (Investment) and #03 (Process) on every program brochure. Shows up to 2 listing cards; empty slots get a "Đang Cập Nhật" placeholder.

**Architecture:** Listings are **dynamically fetched** from Property Hub at deploy time. PH listing pages expose `data-notion="<field>"` attributes (price_full, yield_pct_unit, irr_pct_unit, desc_vi, hero_img via background-image, etc.) — these come from the upstream Notion CRM, so the brochure card always reflects what PH currently says.

**Artefacts:**
- Data: `data/listings.py` — just URLs per country (which listings to show; max 2)
- Generator: `tools/apply_listings.py` — fetches each PH URL, parses `data-notion` fields + hero bg-image + handover, renders the card
- Markers: `<!-- LISTINGS START -->` / `<!-- LISTINGS END -->` in each brochure
- CSS: lives in each brochure's `<style>` block (~140 lines, **byte-for-byte identical across all brochures** — like the paywall CSS pattern). Don't drift them.
- TOC entry: `<li class="toc-item toc-item-spotlight">` between items 02 and 03 — also identical text across brochures (Vietnamese is country-agnostic here: "BĐS đang mở bán").
- CI: `.github/workflows/wp-sync.yml` runs `apply_listings.py` before `sync_brochures.py`, so every deploy re-fetches.

**To add a listing for any country:**
1. Make sure the listing exists in Property Hub first (PH owns the data — price, yield, image, copy, etc.).
2. Open `data/listings.py`, append its URL to that country's `urls: []` (max 2):
   ```python
   'turkey': {
       ...,
       'urls': [
           'https://nomadassetcollective.com/property-hub-bat-dong-san/turkey/<slug>/',
       ],
   },
   ```
3. Run `python tools/apply_listings.py turkey` — fetches PH, re-renders the brochure HTML.
4. `git diff` to inspect.
5. Commit + push. The CI workflow will refetch on deploy (so even if PH changes between now and deploy, the live brochure will be current).

**Fields parsed from PH:**
| Brochure field | PH source |
|---|---|
| `listing-ref` | `data-notion="property_id"` (e.g. NAC-79) |
| Card title | `data-notion="property_name_vi"` (stripped after first em-dash) |
| Tagline (kicker) | `data-notion="tagline_vi"` |
| Description | `data-notion="desc_vi"` (first sentence) |
| Location badge | `data-notion="district"` + country flag from data file |
| Hero image | `background-image:url(...)` inside `.nac-hero-img` (`data-notion-bg="hero_img"`) |
| Price | `data-notion="price_full"` |
| Yield | `data-notion="yield_pct_unit"` |
| IRR | `data-notion="irr_pct_unit"` |
| Handover | `.nac-fact-val` adjacent to "Bàn Giao" label (no `data-notion` on this one) |

**To run offline (skip fetch, all placeholders):**
```
APPLY_LISTINGS_OFFLINE=1 python tools/apply_listings.py
```
Useful when iterating on CSS or for environments without network access.

#### Selection rules (when a country has more candidates than cards)

`data/listings.py` may list more than 2 URLs per country. The generator applies these rules to pick the 2 that actually render:

| # of candidates | What renders |
|---|---|
| 0 | 2 placeholders |
| 1 | 1 card + 1 placeholder |
| 2 | both cards |
| ≥3 | **Cheapest + one rotating card** (see below) |

**Rule 1 — Anchor on cheapest.** With 3+ candidates, card 1 is always the cheapest (sorted by `data-notion="price_full"` parsed to a number).

**Rule 2 — Rotate card 2 every 2 weeks.** Card 2 is picked from the remaining pool using a deterministic fortnight index (ISO year × 26 + ISO week ÷ 2). Bias: prefer a candidate whose `data-notion="hub_type"` differs from card 1's, so users see variety in property type. Within fortnight the selection is stable (no flicker between page loads); across fortnights it shifts.

> ⚠️ The Rule 2 interpretation here is "cheapest stays, second card rotates by property type." If the desired behaviour is different (e.g. both cards rotate, or rotation by yield instead of property type), tell me and I'll adjust `select_pair()` in `tools/apply_listings.py`.

**Rule 3 — "All eligible" link goes to a pre-filtered PH catalog.** The footnote link (and placeholder card link) lands on:
```
https://nomadassetcollective.com/property-hub/?program=<code>&country=<alias>
```
e.g. `?program=cbi&country=turkey`, `?program=rbi&country=portugal`. The country/program comes from the brochure's data file entry.

> ⚠️ **PH-side gap:** as of this writing, the PH catalog (`/property-hub/`) is a pure client-side SPA that does NOT read URL params — clicking the link currently lands users on the unfiltered catalog. The params are harmless until then. Making them work is a cross-repo change in `rayvtt/nac---property-hub---listing-pdp` (~20 lines of JS to read `URLSearchParams` and pre-set filter state on init). Worth doing as a follow-up; the brochure already speaks the right URL.

**To add the section to a brochure that doesn't have it yet (rolling out beyond turkey):**
1. Manually add the CSS block (copy from `Brochures html/turkey-cbi_8.html` — search for `LIVE LISTINGS — Spotlight`)
2. Manually add the TOC item between #02 and #03 (copy from turkey, search for `toc-item-spotlight`)
3. Manually add the START/END markers between section #02's closing `</section>` + `<hr>` and section #03's opening comment:
   ```html
       <hr class="divider">

       <!-- LISTINGS START -->
       <!-- LISTINGS END -->

       <hr class="divider">

       <!-- 03 PROCESS -->
   ```
4. Run `python tools/apply_listings.py <alias>` (or just `tools/apply_listings.py` for all). The script renders into the markers.

**Verifying images:** Image URLs in `data/listings.py` must return HTTP 200. Quick check: `curl -sI <URL> | head -1`. The WordPress `og:image` meta sometimes points at filenames that don't actually exist (e.g. `w-suite-istanbul.webp` returned 404 — `W1.webp` was the real file).

---

### 2. Nav menu items

**Status:** Documented here, **not yet templated** — currently a per-brochure hand-edit. Should be templated before rolling out further changes.

**What:** The top-right nav strip on every brochure: `NAC Index · So Sánh · Property Hub` plus the lang toggle and the "Tư Vấn Ngay" CTA.

**Current state:** Only turkey has the `Property Hub` link; the other 11 still show `Blog`.

**To templatise (todo):**
- Build `data/nav.py` with the menu items as a list of `(label, href)` tuples
- Build `tools/apply_nav.py` that finds `<div class="nav-right">...</div>` in each brochure and re-renders contents from data
- Add `<!-- NAV START -->` / `<!-- NAV END -->` markers
- Run, commit, push

Until that exists, **don't change the nav in any single brochure** — wait until the templatisation is done, then do all 12 in one commit.

---

### 3. Paywall (existing, pre-template)

The paywall (CSS + TOC items 04–09 + opener/closer + JS) is already byte-for-byte copyable per `CLAUDE-AI-PROJECT-INSTRUCTIONS.md` and `NAC-BROCHURES-GATEWAU.md`. It's **not** generator-based yet — it predates this system. If we change the paywall, the right move is to retrofit it into this template system (data file + generator) rather than hand-editing 12 files.

---

## When to add a new pattern to this system

You're hand-editing the same block of HTML in more than one brochure → stop, template it first.

Templating cost: ~30 min upfront (data file + generator + markers). Avoided cost: every future change to that block is a single edit instead of 12.

---

## File layout

```
NAC-Program-Brochures/
├── Brochures html/                  # 13 brochure HTMLs (the deployment artefacts)
├── data/
│   └── listings.py                  # per-country listing data
├── tools/
│   └── apply_listings.py            # generator for Live Listings
├── sync_brochures.py                # WP REST API push (CI)
├── .github/workflows/wp-sync.yml    # CI: git → WP
├── BROCHURE-URLS.md                 # live URL reference per country
├── NAC-LINKS.md                     # canonical links & brand assets
├── CLAUDE-AI-PROJECT-INSTRUCTIONS.md # brochure spec (sections, paywall, tracking)
├── NAC-BROCHURES-GATEWAU.md         # paywall spec detail
├── WP-SYNC-SETUP.md                 # how the WP sync works
└── PB-TEMPLATE.md                   # THIS FILE — template system
```

---

## Verification checklist before commit

After running any generator:

- [ ] `git diff` shows changes in expected brochures, no rogue edits elsewhere
- [ ] Image URLs (if changed): `curl -sI <URL>` returns 200
- [ ] HTML still parses: no broken tags from misformatted template strings (`python -c 'import html.parser; ...'` or just open in browser locally)
- [ ] The change you made in `data/<thing>.py` reflects in `git diff` of brochure HTMLs

If anything's off, revert the brochure changes (`git checkout -- "Brochures html/"`) and fix the generator/data first.
