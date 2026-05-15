# CLAUDE.md — Working Notes

Process rules and gotchas for this repo. Read this before touching any brochure HTML, payload, or workflow.

## Repo at a glance

- **12 program brochures** as standalone HTML in [`Brochures html/`](./Brochures%20html/) (Turkey, UAE, Malta, Panama, Portugal, Greece, Cyprus, Malaysia, Thailand, NewZealand, StKitts, UK).
- **One Notion source-of-truth DB** `[NAC - Program Brochures]` — id `35f48ec25e8680f69c3dc5ad538e7ca8`. Bilingual VI + EN; EN columns are auto-translated by Perplexity inside Notion, so we typically only populate VI.
- **Two sync pipelines** (see below): a Notion ↔ DB pipeline and a DB → HTML → WordPress pipeline.

## Two-pipeline architecture

```
HTML (committed) ──extract_brochure──▶ data/<alias>_payload.json ──push_brochure──▶ Notion DB
                                                                                       │
                              ┌──pull_from_notion──────────────────────────────────────┘
                              ▼
                  data/<alias>_payload.json ──build_brochures──▶ Brochures html/  (TURKEY ONLY)
                                                                       │
                                                            apply_listings (all 12)
                                                                       │
                                                                sync_brochures
                                                                       ▼
                                                                  WordPress
```

**Critical asymmetry**: only **Turkey** is Notion-driven end-to-end. The other 11 keep their hand-crafted HTML in `Brochures html/` because country-specific themes, charts, banners, and EN toggles aren't yet covered by `build_brochures.py`. Editing Notion for non-Turkey rows updates the DB but does **not** regenerate the HTML — see `wp-sync.yml` step "Build brochure HTML from payloads (TURKEY ONLY)".

## Branch convention

- Develop everything on `claude/add-nomad-brochures-68jHG` for both this repo and `rayvtt/Nac---Property-Hub---Listing-PDP`.
- Never push to `main` from here unless explicitly asked.
- Don't open a PR unless the user asks.

## Workflows

### `.github/workflows/wp-sync.yml` (Notion → HTML → WP)
- Triggers on push to `main` or feature branch when `Brochures html/**`, `data/**`, or any sync tool changes.
- Steps: pull from Notion → build Turkey only → refresh LISTINGS on all 12 → push to WP via REST API.
- Feature branch pushes only sync Turkey (validation); `main` pushes sync `--all`.

### `.github/workflows/notion-brochure-db.yml` (HTML → Notion DB)
- Push trigger on `data/.notion-run` etc. Touch `data/.notion-run` with a one-line note to fire it.
- Runs `extract_brochure.py --all` then `push_brochure.py --all`.
- Manual dispatch supports `setup-schema`, `push-all`, `push-one <alias>` with optional `--dry-run`.

### `.github/workflows/patch-ph-catalog.yml`
- Property Hub catalogue patches (separate concern; consult `tools/patch_ph_catalog.py`).

## LISTINGS spotlight

Every brochure has a "matching listings" block between section #02 (investment) and section #03 (process), bracketed by:

```html
<!-- LISTINGS START -->
…cards…
<!-- LISTINGS END -->
```

- `tools/apply_listings.py` rewrites the content **between markers only**, never the markers themselves. Other content in the file is left intact.
- Cards are pulled live from the Property Hub catalogue worker (see `data/listings.py` for selection rules).
- If you ever need to add markers to a new brochure, drop them between the investment `<hr class="divider">` and the `#process` section.

## Notion DB schema

Full spec lives in [`BROCHURE-NOTION-SCHEMA.md`](./BROCHURE-NOTION-SCHEMA.md). Practical notes:

- ~95 fields per row, bilingual (`*_vi` + `*_en`); structured fields (`s02_tiers`, `s03_timeline`, `s05_tax_cards`, etc.) are JSON-encoded inside Notion rich_text.
- Notion display names use circled-digit section icons (`① subtitle (VI)`); the technical schema keys (e.g. `s01_subtitle_vi`) live in `data/brochure_schema.py` → `NOTION_NAMES`.
- Title column is the **alias with flag** (`🇹🇷 turkey`) via `data/brochure_identity.py::alias_with_flag()`. The bare alias still works for lookups (legacy fallback in `find_existing_row`).
- Page-level `cover` is set from `IDENTITY[alias]['cover']`.

## Key scripts

| Script | Direction | Notes |
|---|---|---|
| `tools/extract_brochure.py` | HTML → payload JSON | Regex-based HTML scraping. Tolerates info-box class variants (green/amber/gold), CSS- or inline-style hero backgrounds, breadcrumb in `<nav>` or `<div>`, fam-card with or without inner `<div>`, nac-box `<p>` fallback when no info-box. |
| `tools/push_brochure.py` | payload → Notion DB | POST for new rows, PATCH for existing. **Known bug** below. |
| `tools/pull_from_notion.py` | Notion DB → payload JSON | Used by `wp-sync.yml` step 1. |
| `tools/build_brochures.py` | payload → HTML | Turkey-only in CI; can run other aliases locally but output goes to `build/` and is **not** copied over. |
| `tools/apply_listings.py` | live catalogue → HTML | Only rewrites between `<!-- LISTINGS START/END -->`. Use `--offline` carefully — it can wipe real listing cards if the catalogue fetch fails (see Turkey wipe incident). |
| `sync_brochures.py` | HTML → WordPress | REST API push via `WP_USER` + `WP_APP_PASSWORD` secrets. |
| `tools/setup_brochure_db.py` | one-shot | Creates/aligns the Notion DB schema. |
| `tools/check_brochure_payload.py` | local lint | Validates payload JSON shape before push. |

## Known issues / gotchas

### `push_brochure.py` POST path is broken
The PATCH path (existing row) works; the POST path (new row) silently fails — request returns non-200 but no usable error and the row never appears. Hypothesis confirmed during the v7 backfill:

- Notion's multi-source databases (any DB created or migrated recently) require:
  - `Notion-Version: 2025-09-03` header
  - `parent: {"data_source_id": "35f48ec2-5e86-8008-bf9f-000bb83b3392"}` instead of `database_id`
  - `find_existing_row` must query `/v1/data_sources/{id}/query` instead of `/v1/databases/{id}/query`

We **did not** apply this fix yet — bumping `NOTION_VERSION` affects the working PATCH path too, so it needs testing in isolation. Workaround for now: create new rows via the Notion MCP (`notion-create-pages`), then re-run the workflow to PATCH the full payload in. Eight of the 12 rows were created this way (May 14 backfill).

### Build does not cover 11 brochures
`build_brochures.py` currently only emits Turkey. Editing the Notion row for, say, Portugal does **not** regenerate `portugal-gv.html`. If a non-Turkey brochure's prose changes in Notion, the change has to be hand-mirrored into the HTML until the builder is generalised.

### Genuine HTML gaps surfaced by the extractor
After the v6 extractor fixes, the remaining empty VI fields are real HTML omissions, not regex misses:
- `s05_tax_cards` — 11/12 brochures use `<table class="tax-table">`; only 1 uses `ov-card` markup the extractor knows.
- `s01_article_cta` missing in Panama.
- `s05_inheritance_note_vi` missing in 5 brochures.
- `s06_nac_strategy_note_vi` missing in Cyprus, Malaysia.
- `s07_cta_text_vi` missing in Portugal, Panama.
- `s08_risk_note_vi` missing in NewZealand.

Don't "fix" the extractor for these — fix the source HTML if the content is genuinely required.

### Line endings
`stkitts-nevis.html` arrived with CRLF and at least one tool will silently rewrite the whole file when normalising to LF. If you must touch it, preserve the original line endings or commit a one-time LF conversion as its own commit so the diff is reviewable.

### Don't trash hand-crafted Turkey listings
`apply_listings.py --offline` falls back to placeholder cards if the live fetch fails; this once overwrote the W Suites Istanbul card. Always run with live network, and if you see a listings diff that shrinks content, revert before committing.

## `data/.notion-run` versioning

This file is the trigger for `notion-brochure-db.yml`. Bump the version comment when you touch it so the commit log has a one-liner explaining the run:

```
# v7 — re-PATCH all 12 rows after the 8-row MCP backfill
```

## Workflow

- Develop on `claude/add-nomad-brochures-68jHG`.
- For Notion DB changes: edit payload/code → touch `data/.notion-run` (bump version) → push → workflow runs `extract-and-push-all`.
- For HTML/WP changes: edit `Brochures html/<file>.html` → push → `wp-sync.yml` runs.
- Never amend pushed commits; never `--no-verify`; never force-push to `main`.
- Don't open a PR unless asked.
