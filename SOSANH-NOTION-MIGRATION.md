# So Sánh → Notion Migration Plan

> **Tool:** `Brochures html/NAC-SO-SANH.html` — bilingual (VI/EN) residency/citizenship-by-investment comparison tool, live at `nomadassetcollective.com/so-sanh/` (WP page 145, alias `sosanh`, gate code client-side in `GATE_CODE`).
> **Current source of truth:** Google Sheet `1Jj15bdZqDOH1JiMZgKKLoaL2l7kmos8Mw-tmmJlYGp4`, tabs `Comp` (VI, gid `1064639058`) and `Comp (EN)` (fetched by tab name, no gid) — both public "anyone with link can edit", fetched client-side via unauthenticated `gviz/tq` JSONP.
> **Target source of truth:** a new Notion DB, one row per country, real typed VI/EN properties.
> **Status:** planning only — nothing in this document has been built. This is the sign-off artifact for step 1 of the rollout (§6).

This does **not** touch the `?edit=1` in-page chrome-copy editor (hero headline, CTA labels, gate text — the `var I18N = {...}` object, `tools/apply_sosanh_copy.py`, `🔀 NAC - So Sánh Copy` DB). See §7 for how the two systems relate.

---

## 1. Why

The Sheet architecture was audited this session. Two structural problems and a running list of content bugs came out of it:

**Structural:**
- `Comp` and `Comp (EN)` are matched **positionally** (`var C = {...}` maps ~68 semantic keys to 0-based column indices; a second `var EN_COL = {...}` maps a subset of those same keys to different indices in the EN tab). The offset between equivalent columns drifts across the sheet with zero warning — there is no name-based binding anywhere in the pipeline.
- The client embeds a static `var SNAP = {...}` blob (comment: "Injected at build time") as the instant-first-paint fallback before the live `gviz` fetch resolves. **No tool in this repo regenerates it** — confirmed by grepping every `.py`/`.yml`/`.js` file for `NAC-SO-SANH` and for the bare token `SNAP`: the only hits are `sync_brochures.py` (pushes the HTML file to WP verbatim, doesn't touch its contents) and the `?edit=1` copy pipeline (patches `I18N` only). `SNAP.grid` is itself a flattened, **positionally-indexed** mirror of the raw sheet rows — so even the "fallback" path carries the same column-drift risk as the live fetch. It was hand-embedded once and has had no refresh mechanism since.

**Content bugs found this session (still live as of this writing):**
- A visitor-count figure ("33.3 triệu khách") mistranslated as a GDP percentage ("33.3% of GDP") in `Comp (EN)`.
- An inheritance-tax cell (`inherit`, C-map col 32) with the **opposite polarity** from VI on 2 countries — VI says no tax applies, EN says it does. `EN_COL` deliberately omits `inherit` today (code comment: *"the 2026-07 reconciliation found a verified VI/EN meaning-flip on 2 countries there"*) — so this field is **permanently VI-only** in the live tool until someone manually re-verifies and re-adds it to `EN_COL`.
- A per-person spending figure conflated with a total-revenue figure.
- Australia's and New Zealand's `Comp (EN)` rows are cross-contaminated with each other's data (Australia's EN "currency" cell literally read `NZD`). `var EN_UNTRUSTED_COUNTRIES = ['Úc','New Zealand']` hard-excludes both countries from **every** translatable field, not just currency — so EN visitors currently see Vietnamese text for all of §01/§03/§04/§05/§06/§07/§08/§09 on those two countries, silently.
- §02 "Planning by need" (`NEED_DIMS` / `nEdu..nTax`) has **no EN handling at all** — `needsSec()` never calls `enTextFor()`, unlike every other section. This section is 100% untranslated today, not merely unreliable.
- `var FIXES = [...]` — the hand-maintained "stale value → correction → source" ledger — carries **157 entries across all 14 countries** as of this session. Every one exists because the Sheet has no changelog, so a human had to manually record what a cell *used to* say to know when it's safe to stop patching around it.
- Minor illustrative fragility: `META`'s lookup key for Portugal is `'Bổ Đào Nha'` (hỏi tone) while the same object's display value is `'Bồ Đào Nha'` (huyền tone, the correct spelling) — harmless today because the key is only used for prefix-matching, but a small live example of what happens when identity is a free-text string instead of a stable row.

**What the shipped guard looks like today:** because `Comp (EN)` can't be trusted cell-for-cell, `NAC-SO-SANH.html` carries a runtime reconciliation layer that re-verifies every EN cell on every page load — `numbersWithUnits()` / `numSetsCompatible()` (locale-aware number+unit-class extraction so VI `"1.560"` thousands-separator isn't confused with a `"1.56"` decimal), `isVietnameseText()` (VN-diacritic detector to catch untranslated cells), `enTrusted()` (the hard per-country exclusion list), wired through `enTextFor()` (lines ~897–906) which every `rowTxt()`/`verdictSec()` call passes through before showing an EN string, falling back to VI on any doubt. This is real, working engineering — and it exists **only** because a sheet cell has no reliable way to declare "I am the English version of this specific VI value." A real Notion VI/EN property pair states that by construction. Once the data model enforces it, the guard has nothing left to guard against.

---

## 2. At a glance

**Current:**

```
Google Sheet "So Sánh Data"
  ├─ tab: Comp        (VI, gid 1064639058)   ┐
  └─ tab: Comp (EN)    (name-fetched)        ┘  positionally matched, no name binding

                    client-side JSONP (gviz/tq), on EVERY page load, unauthenticated
                                    │
                                    ▼
                    NAC-SO-SANH.html (browser)
                      var SNAP {...}   ← static fallback, hand-embedded once, never refreshed
                      var C {...}      ← 68-key column-index map (drift risk)
                      var META {...}   ← 14 hardcoded country identities
                      var FIXES [...]  ← 157 hand-tracked stale-value corrections
                      EN reconciliation guard (numbersWithUnits / numSetsCompatible /
                        isVietnameseText / enTrusted / enTextFor) — re-checks every EN
                        cell on every render, silently falls back to VI on any doubt
```

**Target:**

```
Notion DB "🔀 NAC - So Sánh Data" (new — one row per country, 14 rows)
  every field authored directly as a real, typed, named VI/EN Notion property pair
                                    │
              tools/pull_sosanh_from_notion.py   (cron, cadence TBD — see §5)
                                    │
                                    ▼
              surgical regex patch of var SNAP {...} in NAC-SO-SANH.html
              (same class of patch as inject_notion_en_to_html.py — never a
              full-file regenerate; see the wp-sync.yml precedent in §5)
                                    │
                                    ▼
              commit to main → inline `python sync_brochures.py sosanh` → WP page 145
                                    │
                                    ▼
              NAC-SO-SANH.html (browser) — renders straight from SNAP, no live
              fetch, no C/META/FIXES/EN-guard machinery to maintain
```

---

## 3. Proposed Notion DB schema

One row per country (14 rows today, seeded from the current `META`). Naming follows the house convention confirmed by fetching the live schema of `🔖 NAC - Brochures Meta-data` (`35f48ec25e8680f69c3dc5ad538e7ca8`) and reading `data/brochure_schema.py`: **`(VI)` / `(EN)` suffix pairs, `·` middle-dot for multi-word plain fields, circled-digit prefix (①…) for section-grouped fields, `(JSON)` suffix for structured list fields.** This is *not* the emoji-prefixed style used in the sibling Property-Hub-Listing-PDP repo (e.g. `📜 Statement VI`) — that convention does not appear anywhere in this repo's two live Notion DBs. Section numbers below (①–⑩) mirror the tool's own `secShell('§0N', ...)` calls exactly, so the DB's grouping matches what a reader already sees on the page.

### Identity (replaces `META` + `LIVE_KEYS`)

| Property | Type | Notes |
|---|---|---|
| `country (VI)` | Title | e.g. `Hy Lạp` |
| `country (EN)` | Text | e.g. `Greece` |
| `code` | Text | 2-letter, e.g. `gr` (was `META[key].code`) |
| `flag` | Text | emoji, e.g. 🇬🇷 |
| `live in picker` | Checkbox | replaces `LIVE_KEYS` array membership — ticking this is the entire "roll out a country" action, no code change |
| `sort order` | Number | Notion rows have no inherent order; the picker needs one. Optional — default to alphabetical if unset |
| `sheet key (legacy)` | Text | the old free-text prefix-match key (e.g. `'St. Nevis'`), kept only so the importer can audit-trail back to the source row. Candidate for deletion once the Sheet is retired (§6, step 6) |

### ① Overview — `bloc`, `econ`, `rank`, `gdp`, `infl`, `debt`, `polstab`, `corrupt`

| Property | Type | Source key | VI/EN today? |
|---|---|---|---|
| `① bloc` | Multi-select | `bloc` | n/a — see rationale below |
| `① econ (VI)` / `(EN)` | Text | `econ` | yes |
| `① rank (VI)` / `(EN)` | Text | `rank` | yes |
| `① gdp` | Number (%) | `gdp` | n/a (numeric) |
| `① infl` | Number (%) | `infl` | n/a |
| `① debt` | Number (%) | `debt` | n/a |
| `① polstab` | Number (0–10) | `polstab` | n/a |
| `① corrupt` | Number (0–100) | `corrupt` | n/a |

`bloc` today is parsed by `blocBadges()` off a `¶`-delimited multi-value cell (e.g. multiple bloc memberships in one string) — a genuine multi-value field, so **Multi-select**, not Text. Not split VI/EN: bloc names in this dataset are acronyms/proper nouns (EU, NATO, Schengen, Caribbean…) that don't meaningfully translate — a single option set serves both languages.

### ② Planning by need — `nEdu, nGlobal, nMove, nHealth, nQol, nSafe, nDiv, nTax`

8 dimensions, each currently one Sheet cell holding `"<main text> 👉 Ex:<example text>"` (parsed client-side by `splitEx()` on the `👉` glyph — a delimiter hack to fit two logical values into one spreadsheet cell). Icon + VI/EN dimension *names* (🎓 Giáo dục/Education, 🌐 Toàn cầu hóa/Globalization, ✈️ Tự do đi lại/Mobility, 🏥 Y tế/Healthcare, 🌿 Chất lượng cuộc sống/Quality of life, 🛡️ Đầu tư an toàn/Investment safety, 📊 Đa dạng hóa/Diversification, 🧾 Thuế/Tax) are hardcoded UI chrome in `NEED_DIMS`, not per-country data — they stay in the JS, unchanged.

**Recommendation:** 2 properties per dimension (VI text, EN text), **not** 4 — Notion rich text supports multi-line content natively, so the "example" line can just be the second line of the same field instead of a machine-parsed `👉 Ex:` delimiter. This is a real simplification the migration unlocks, not a compromise.

| Property (×8 dims) | Type |
|---|---|
| `② need · <dim> (VI)` | Text |
| `② need · <dim> (EN)` | Text |

= 16 properties. (Fallback, if Ray wants the UI to visually distinguish main/example: 4 properties per dim = 32. Flagged, not recommended.) §02 has **zero EN content today** (confirmed — see §1) — every EN property here starts blank and needs first-time authoring, not a migration of existing data.

### ③ Economic highlights — `curr, capEcon, econChar, infra, tourism, othNews`

| Property (×6) | Type |
|---|---|
| `③ curr (VI)` / `(EN)`, `③ capEcon (VI)` / `(EN)`, `③ econChar (VI)` / `(EN)`, `③ infra (VI)` / `(EN)`, `③ tourism (VI)` / `(EN)`, `③ othNews (VI)` / `(EN)` | Text |

= 12 properties. All 6 have live EN data today (`EN_COL` covers all of them).

### ④ Tax — `vat, pit, cit, inherit, bankSafe, fx`

| Property | Type | VI/EN today? |
|---|---|---|
| `④ vat` | Number (%) | n/a |
| `④ pit (VI)` / `(EN)` | Text | **no** — `EN_COL` excludes it ("numeric-or-badge content") |
| `④ cit (VI)` / `(EN)` | Text | **no** — same reason |
| `④ inherit (VI)` / `(EN)` | Text | **no** — the verified polarity-flip bug (§1). This is the field the migration most directly fixes: once VI and EN are two independently-authored Notion properties instead of one column-position guess, there's no mechanism left for a flip to happen silently |
| `④ bankSafe (VI)` / `(EN)` | Text | yes |
| `④ fx (VI)` / `(EN)` | Text | **no** — numeric-like, `EN_COL` excludes it |

= 11 properties (1 number + 5 text pairs). Four of the five text fields are VI-only today; the migration is the opportunity to finally fill them.

### ⑤ Requirements — `prog, progInv, minCost, renew, stay, citiz, sof`

7 fields × 2 = **14 properties**, all Text, all with live EN data today. Naming: `⑤ prog (VI)` / `(EN)`, `⑤ progInv (VI)` / `(EN)`, `⑤ minCost (VI)` / `(EN)`, `⑤ renew (VI)` / `(EN)`, `⑤ stay (VI)` / `(EN)`, `⑤ citiz (VI)` / `(EN)`, `⑤ sof (VI)` / `(EN)`.

### ⑥ Benefits — ownership — `sponsor, deps, addMem, heir, dual, vfree, mobility, e2`

| Property | Type |
|---|---|
| `⑥ sponsor (VI)` / `(EN)`, `⑥ deps (VI)` / `(EN)`, `⑥ addMem (VI)` / `(EN)`, `⑥ heir (VI)` / `(EN)`, `⑥ dual (VI)` / `(EN)`, `⑥ mobility (VI)` / `(EN)`, `⑥ e2 (VI)` / `(EN)` | Text |
| `⑥ vfree` | Number (count of visa-free countries) |

= 15 properties. `heir`/`dual` render today with a `{yesno:1}` styling hint (✓/✗ badge prefix) — that's presentation, not a data-type decision; keep them Text since the actual cell content is descriptive prose (e.g. "Có, cho đến đời thứ 3"), not a bare boolean. Derive the badge icon at render time from a leading "Có"/"Không" the same way the tool does today.

### ⑦ Benefits — investment — `growth, liquid, maintain`

3 fields × 2 = **6 properties**, Text: `⑦ growth (VI)` / `(EN)`, `⑦ liquid (VI)` / `(EN)`, `⑦ maintain (VI)` / `(EN)`.

### ⑧ Fees — `feeInit, feeGov, feeDD, feeAnnual, feeTotal1, feeTotal2, feeNote`

| Property | Type | VI/EN today? |
|---|---|---|
| `⑧ feeInit (VI)` / `(EN)`, `⑧ feeGov (VI)` / `(EN)`, `⑧ feeDD (VI)` / `(EN)`, `⑧ feeAnnual (VI)` / `(EN)`, `⑧ feeNote (VI)` / `(EN)` | Text | yes |
| `⑧ feeTotal1 (VI)` / `(EN)`, `⑧ feeTotal2 (VI)` / `(EN)` | Text | **no** — computed totals, `EN_COL` excludes both. Formula-property candidate — see open decision in §8 |

= 14 properties.

### ⑨ Why / verdict — `r1…r5`

Today: 5 separate columns, each one "reason" bullet, all with live EN data (`EN_COL` covers `r1`–`r5`). This is a variable-feeling but actually fixed-length list of bilingual bullets — the exact shape the Brochures DB already has a precedent for: `⑧ pros (JSON)` / `⑧ cons (JSON)` both store `[{vi, en}]`.

**Recommendation:** one JSON property, matching that precedent exactly, instead of 10 flat properties:

| Property | Type | Shape |
|---|---|---|
| `⑨ reasons (JSON)` | Text (rich text, JSON-encoded) | `[{vi, en}, {vi, en}, {vi, en}, {vi, en}, {vi, en}]` |

= 1 property (validated the same way `check_brochure_payload.py` validates the Brochures DB's JSON fields).

### ⑩ NAC Fit ratings — `rtCost, rtEdu, rtGlobal, rtMove, rtHealth, rtQol, rtSafe, rtDiv, rtTax`

9 numeric 0–10-ish dimensions. Dimension *labels* (Chi phí đầu tư/Entry cost, Giáo dục/Education, Toàn cầu hóa/Global access, Tự do đi lại/Mobility, Y tế/Healthcare, Chất lượng cuộc sống/Quality of life, Đầu tư an toàn/Investment safety, Đa dạng hóa danh mục/Diversification, Tối ưu thuế/Tax efficiency) are hardcoded in `RT_DIMS`, unchanged by this migration — only the 9 per-country values move.

**Recommendation: 9 separate Number properties, not one JSON blob or a rollup** — matching the Brochures DB's own precedent for its 6 `score · *` fields (plain `number` type, `show_as: bar`). Reasons: (a) it's a fixed, known, small set, not a variable list; (b) Ray gets Notion's native bar/gauge display for free, same as the Brochures DB already uses; (c) native number properties are filterable/sortable in Notion views ("which countries score ≥8 on tax efficiency") — a JSON blob forfeits that for no benefit here.

| Property (×9) | Type |
|---|---|
| `⑩ rtCost`, `⑩ rtEdu`, `⑩ rtGlobal`, `⑩ rtMove`, `⑩ rtHealth`, `⑩ rtQol`, `⑩ rtSafe`, `⑩ rtDiv`, `⑩ rtTax` | Number, `show_as: bar` |

= 9 properties. (Aside, not in scope: the picker's "NAC Fit" badge (`fitOf()`) is a client-computed average of these 9 — not stored anywhere today. Could become a Notion **formula** property (`average(rtCost, rtEdu, …)`) for free once all 9 are real number properties, same pattern as the `feeTotal1/2` formula question in §8 — flagging, not recommending, since it's outside what was asked.)

### Total

| Group | Properties |
|---|---|
| Identity | 7 |
| ① Overview | 10 |
| ② Planning by need | 16 |
| ③ Economic highlights | 12 |
| ④ Tax | 11 |
| ⑤ Requirements | 14 |
| ⑥ Benefits — ownership | 15 |
| ⑦ Benefits — investment | 6 |
| ⑧ Fees | 14 |
| ⑨ Why / verdict | 1 (JSON) |
| ⑩ NAC Fit ratings | 9 |
| **Total** | **~115** |

That's wide, but it's the real data footprint — the same conclusion the Brochures DB's own schema doc reached at ~95 properties for a similarly-shaped single-DB design ("*That's a lot but it's the actual data footprint of a brochure today. The alternative … trades width for depth and is harder to maintain.*"). A knob exists if Ray wants fewer, wider fields: bundle each section's text fields into one `(JSON)` blob per section (like `⑨ reasons` already does), trading ~115 properties for roughly a dozen — at the cost of Ray editing JSON strings instead of plain Notion cells for 90% of the data, which defeats a large part of the point of leaving the Sheet. Not recommended as the default; noted as available.

### What retires outright

- **`FIXES`** — the entire stale-value-tracking ledger is retired. Corrections get typed directly into the real Notion cell; there's no second copy of the value to keep in sync, so there's nothing to "self-retire" against.
- **The EN reconciliation guard** (`numbersWithUnits`, `numSetsCompatible`, `isVietnameseText`, `enTrusted`, `enTextFor`, `EN_COL`, `EN_UNTRUSTED_COUNTRIES`, `DB_EN`) — its entire job was verifying that an EN cell actually corresponds to its VI counterpart, a question that doesn't exist once VI and EN are two named properties on the same row instead of two guesses at the same column offset.

### Residual validation worth keeping

Not the same machinery, much lighter: a **completeness check**, analogous to how the sibling Property-Hub-Listing-PDP repo's `listing-status.html` dashboard flags incomplete fields. Concretely: does this row have both `(VI)` and `(EN)` filled for every non-numeric property? That's a simple presence check the pull script (§5) can run and log (or write into a `.diagnostics/sosanh-completeness.md` file, matching this repo's existing `.diagnostics/` convention) — not a data-quality guess, just "is anything still blank." No unit/locale/diacritic checking survives, because there's no positional ambiguity left to check for.

---

## 4. One-time import script

**`tools/migrate_sosanh_to_notion.py`** — one-time, safe to re-run (idempotent).

### Inputs

- `NOTION_KEY` env var — matches `pull_from_notion.py`'s convention. (Note: this repo actually has **two** different Notion secret names in use — `NOTION_KEY` in `pull_from_notion.py`/`intel_apply.py`/`qa-tracker-scan.py`, and `NOTION_TOKEN` in `apply_sosanh_copy.py` alone. New scripts in this plan standardize on `NOTION_KEY` to match the majority/"pull" convention; doesn't require touching the existing `apply_sosanh_copy.py`.)
- `--dry-run` — matches `pull_from_notion.py`'s flag; prints the full trusted/blank EN report without writing to Notion.

### Steps

1. **Fetch both tabs.** No authenticated Google Sheets access exists anywhere in this repo (checked — no `sheets.googleapis`, `GOOGLE_SERVICE_ACCOUNT`, or `gspread` reference anywhere). Use the same public, unauthenticated `gviz/tq` endpoint the live tool already uses, just fetched server-side with `urllib` instead of injected as a client `<script>` tag:
   - VI: `https://docs.google.com/spreadsheets/d/{SHEET.id}/gviz/tq?gid={SHEET.gid}` (mirrors `loadFeed()`, line ~802)
   - EN: `https://docs.google.com/spreadsheets/d/{SHEET.id}/gviz/tq?sheet=Comp%20(EN)` (mirrors `loadFeedEn()`, line ~916)
   - Both responses are JSONP-wrapped (`google.visualization.Query.setResponse({...})`); strip the wrapper with a regex, `json.loads()` the remainder. Port `parseGviz()` (~line 751) to read `table.rows[].c[].v`.
2. **Apply `FIXES` once, in-memory, while porting.** Port `fixFor()`/`valOf()` (~lines 735–748) exactly: for each VI cell, if a `FIXES` entry matches `{country, col, ifOld}`, substitute `use` instead of the raw cell. This is the *last* time `FIXES` does anything — the corrected value lands directly in Notion's VI property, and the 157-entry ledger becomes dead weight afterward (delete `var FIXES` from the HTML at cutover, §5).
3. **Decide which EN cells are trustworthy**, porting `numbersWithUnits()` / `numSetsCompatible()` / `isVietnameseText()` / `enTrusted()` / `enTextFor()` **1:1 from `NAC-SO-SANH.html` (~lines 840–906) — the reference implementation, not reinvented.** Same logic, same guard order: country not in `EN_UNTRUSTED_COUNTRIES` → key present in `EN_COL` → cell non-empty and not Vietnamese-diacritic text → VI/EN number-sets compatible. A cell that fails any check is **left blank** in Notion, not seeded with a guessed value — writing an untrustworthy value "because it's better than nothing" would just reintroduce the exact bug this migration exists to fix. §02 (no `EN_COL` entries at all) seeds 100% blank on the EN side, honestly reflecting that this content doesn't exist yet.
4. **Upsert into the new Notion DB**, one page per `code` (matching `pull_from_notion.py`'s pattern, adapted from "diff local JSON before write" to "query Notion before write" since the target is Notion pages, not a local file): query by `code`, patch existing page if found, create if not. Only write fields that differ from current Notion content, so re-running after Ray has started hand-editing in Notion doesn't clobber his edits with stale Sheet values.
5. **Print a per-country report**: for every field, `seeded (trusted)` / `left blank (untrusted or no EN_COL entry)` / `left blank (empty in sheet)`. This is what step 3 of the rollout (§6) reviews before anything goes live.

---

## 5. Ongoing sync design

Notion has no public unauthenticated read endpoint — unlike the Sheet's `gviz` — so the client's `loadFeed()`/`loadFeedEn()` can't simply be re-pointed at a new URL. This has to become a **build-time pull**, same shape as the existing brochure pipeline.

### Pull script — `tools/pull_sosanh_from_notion.py`

Matches `pull_from_notion.py` house style: `NOTION_KEY` env, plain `urllib` POST to `/v1/databases/{id}/query`, `next_cursor` pagination, a `decode_property()`-style per-type decoder. Two additions needed beyond the existing decoder (which only handles `title`/`rich_text`/`number`/`select`/`status`/`url`): **`checkbox`** (for `live in picker`) and **`multi_select`** (for `bloc`). Writes one file per country — `data/sosanh_<code>_payload.json` — mirroring the existing `data/<alias>_payload.json` pattern, diffing against the existing file and only writing on change (same unchanged/updated/new counters `pull_from_notion.py` prints).

### Patch script — `tools/patch_sosanh_snap.py`

**This is not a rename of `inject_notion_en_to_html.py`** — that script's regex targets are `VI_STRINGS`/`EN_STRINGS` array literals, a shape specific to the legacy brochure bilingual engine that So Sánh doesn't use. This is a new, sibling script following the same conventions: surgical regex patch of one named object literal, never a full-file rewrite, idempotent (no-op commit if nothing changed), and it must respect the WP-safety constraint already documented *inside `NAC-SO-SANH.html` itself* (~line 850): *"a backslash anywhere in this file is silently stripped by WP's `wp_unslash` on every push"* — so whatever this script emits into the HTML must, like the rest of the file, contain zero backslashes (no `\"`, no `\n` escapes — use the same quote-picking approach `js_escape_string()` uses in `inject_notion_en_to_html.py`, or the curly-apostrophe substitution `apply_sosanh_copy.py`'s `to_js_single_quoted()` already uses for this exact file).

**Important design choice — don't just refill the existing `SNAP.grid` shape.** As noted in §1, today's `SNAP.grid` is itself a positionally-indexed mirror of the raw sheet rows. Patching new values into that same shape would leave positional risk alive in the fallback path even after Notion becomes the source of truth upstream — a half-migration. Two options:

- **Option A (minimal):** regenerate `SNAP.grid` in its current positional shape from the Notion pull. Less rendering-layer rework, but `cellOf`/`C` (column-index lookups) survive in the renderer, and *some* "which index is which field" bookkeeping survives with them.
- **Option B (recommended):** replace `SNAP` with a semantic shape — `[{code, vi:{...named fields...}, en:{...named fields...}}, …]`, keyed identically to the Notion schema in §3 — and rewrite `cellOf()`/`valOf()`/`numOf()`/`rowTxt()`/`rowNum()`/`rowBadges()` to read by field name instead of column index. More one-time rendering-layer work, but it's the only option that actually delivers "no column position to drift from" everywhere, not just upstream of the Sheet. It's also the only option under which `var C` (the 68-key column map) can be deleted entirely, not just left unused.

This plan recommends **Option B** as the target for step 4 of the rollout (§6); Option A is the fallback if timeline pressure forces a faster interim cutover.

### Workflow — `.github/workflows/pull-sosanh-notion.yml`

Mirrors `pull-notion.yml`: `cron: '*/10 * * * *'` + `workflow_dispatch` (with a `dry_run` boolean input), `concurrency: {group: pull-sosanh-notion, cancel-in-progress: false}`, `permissions: contents: write`. Steps: checkout `main` → setup-python 3.11 → run the pull script → run the patch script → commit.

**One inherited gotcha to carry forward deliberately:** `pull-notion.yml` documents in its own comments that *"commits made by GITHUB_TOKEN don't trigger other workflows"* and works around it by inlining `sync_brochures.py --all` directly in the same job rather than relying on `wp-sync.yml`'s `on: push` trigger to cascade. This new workflow should do the same: after committing the `SNAP` patch, run `python sync_brochures.py sosanh` inline in the same job, rather than assuming the push to `Brochures html/NAC-SO-SANH.html` will cascade-trigger `wp-sync.yml` on its own. (`apply-sosanh-copy.yml`'s own header comment claims its push *does* cascade-trigger `wp-sync.yml` — that may or may not hold given the GITHUB_TOKEN restriction; not this plan's problem to resolve, but reason enough to use the proven-safe inline pattern here rather than copy the untested assumption.)

**Cadence:** `*/10` matches `pull-notion.yml` for consistency and because 14 rows is nowhere near any Notion API rate limit. Confirm with Ray (§8) — comparison data changes far less often than blog/listing content, so `*/30` or hourly would also be defensible if Ray would rather see fewer diagnostic commits.

### What this deletes from the client-side script

Once cutover is verified (§6, step 5): `loadFeed`, `loadFeedEn`, `window.NACSS_FEED`, `window.NACSS_FEED_EN`, `var SHEET`, `numbersWithUnits`, `numSetsCompatible`, `normNum`, `isVietnameseText`, `VN_DIACRITIC_RE`, `UNIT_WORD_CLASS`, `NUM_UNIT_RE`, `enTrusted`, `enTextFor`, `EN_COL`, `EN_UNTRUSTED_COUNTRIES`, `DB_EN`, `var FIXES`, `fixFor` — and, under Option B, `var C` and the index-based branches of `cellOf`. That's roughly the entire data-plumbing middle of the file (~lines 750–920, plus the 35KB `FIXES` literal and the column-map region) — a substantial simplification, leaving `render()` and the section builders (`secShell`, `rowTxt`, `rowNum`, `rowBadges`, `verdictSec`, `ratingsSec`, `needsSec`) as the surviving logic, now reading named fields instead of column offsets.

---

## 6. Phased rollout plan

1. **Confirm schema with Ray** — walk through §3 of this doc plus the open decisions in §8.
2. **Build the DB** — create `🔀 NAC - So Sánh Data` (or Ray's preferred name/icon, §8) with the properties in §3. Add a matching `data/sosanh_schema.py` module (`SCHEMA` dict of Notion API property-type payloads + `NOTION_NAMES` dict of technical-key → display-name + a `set(SCHEMA) == set(NOTION_NAMES)` sanity assert), mirroring `data/brochure_schema.py` exactly — used by both the importer (§4) and the ongoing puller (§5).
3. **Dry-run the importer** (`migrate_sosanh_to_notion.py --dry-run`), review the per-country trusted/blank EN report, then run for real. **Spot-check 3 countries** (suggest one clean case with full `EN_COL` coverage, e.g. Turkey; one `EN_UNTRUSTED_COUNTRIES` case, e.g. Australia; one thin-data case, e.g. Nauru) side-by-side against the live tool's current rendering.
4. **Build the pull + patch scripts and the new workflow** (§5, Option B recommended). Test on a feature branch — this repo's `Brochures html/*.html` is served via GitHub Pages preview on every branch, so a branch push is enough to verify rendering before touching `main`.
5. **Cut over**: merge, verify live at `nomadassetcollective.com/so-sanh/` (WP page 145) — both VI and EN, no console errors, all 10 sections populated, gate code still works.
6. **Decide the old Sheet's fate** (Ray's call, §8) — recommend freezing it read-only for one release cycle as a rollback safety net, then archiving.
7. **Update this repo's `CLAUDE.md`** — add `🔀 NAC - So Sánh Data` to the "Notion DBs" table in §3, add `migrate_sosanh_to_notion.py` / `pull_sosanh_from_notion.py` / `patch_sosanh_snap.py` to the tools list, add `pull-sosanh-notion.yml` to the workflows list, and a short new numbered section describing the pipeline end-to-end — modeled on the brevity of the existing "§8b. Partner Gateway in-page copy editor" subsection (prose + bullets + file pointers, not a full re-explanation of everything in this doc).

---

## 7. Relationship to the `?edit=1` chrome-copy editor

Different system, different data, no overlap:

| | `🔀 NAC - So Sánh Copy` (existing) | `🔀 NAC - So Sánh Data` (this plan) |
|---|---|---|
| Row = | one edit event | one country |
| Cardinality | unbounded, append-only | fixed, 14 |
| Direction | write-only audit mirror — `apply_sosanh_copy.py`'s `notion_upsert()` writes on every `?edit=1` publish; **nothing reads it back into the tool** (confirmed by reading the script — the live page never queries this DB) | read **and** written — the whole point is the tool renders from it |
| Content | ~50 `I18N` chrome strings (hero headline, CTA labels, gate text, footnotes) | ~68 per-country comparison fields × 14 countries |
| Patches | `var I18N = {...}` object literal | `var SNAP = {...}` object literal |

**Recommendation: sibling DB, not a merge or a repurpose of the Copy DB** — the shapes don't compose (changelog vs. live dataset), and merging would force the audit-trail DB to also carry live comparison data it was never designed to hold. Aside: the Copy DB's `Nguồn` select property already has a `"Notion sync"` option defined alongside `"in-page editor"`/`"seed"`, currently unused (`apply_sosanh_copy.py` always writes `"in-page editor"`) — someone anticipated a Notion-authored *copy*-editing flow at some point. That's unrelated to this migration and doesn't need touching.

The `?edit=1` editor itself stays exactly as-is — out of scope, no changes proposed. It solves a different problem (marketing-chrome tweaks by Ray, in-browser) than this migration (structural per-country data integrity).

---

## 8. Open decisions for Ray

1. **DB name + icon.** Proposing `🔀 NAC - So Sánh Data` (same 🔀 as the Copy DB, for the obvious family resemblance) — Ray's call.
2. **The 4 thin-data countries** — Panama, St. Kitts & Nevis, Nauru, Mỹ (EB-5) — seed as empty placeholder rows now (so the schema and picker wiring are ready the moment data lands) or add them only when real data is ready? Doesn't block the other 10.
3. **Sync cadence** — `*/10` proposed to match `pull-notion.yml`; confirm or widen.
4. **Parallel-run window vs. immediate cutover** — run Sheet-fed and Notion-fed versions side by side for a transition period (e.g. a `?src=notion` query param on a staging branch) to compare output before flipping `main`, or cut straight over after the step-3 spot-check passes?
5. **`feeTotal1`/`feeTotal2` as Notion formula properties** — possible, but only clean if `feeInit`/`feeGov`/`feeDD`/`feeAnnual` *also* become real Number properties first (they're currently free-text ranges/prose with currency symbols in the sheet, e.g. not directly summable as-is). If Ray wants true auto-computed totals, that's a bigger schema change than just the two total fields — otherwise all fee fields stay Text and totals stay manually entered, same as today.
