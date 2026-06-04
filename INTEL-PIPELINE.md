# Daily Intel Pipeline — policy / pricing / community

> **Purpose:** daily scrape + daily GitHub Issue with checkbox-driven approvals for the 12 brochure countries. **Tick a box → Notion + HTML + WordPress all update in one workflow run (~2 min).** No other approvals needed.

## At a glance

```
03:00 UTC daily   →  intel-daily.yml      →  1. scrape sources per country
                                                 → .diagnostics/weekly-intel/<date>/
                                              2. compose daily digest (--days=1)
                                              3. open GitHub Issue `intel-daily`
                                                 with `- [ ]` checkbox tasks
                                              4. auto-close yesterday's issue

04:00 UTC Mondays →  intel-weekly-digest.yml → roll up last 7 days
                                                open/update GitHub Issue
                                                labelled `intel-weekly`

on issue edit     →  intel-apply.yml         →  FULL END-TO-END in one run:
                 (intel-daily OR                   1. parse `- [x]` checkboxes
                  intel-weekly label)               2. PATCH Notion DB rows
                                                    3. update data/*_payload.json
                                                    4. inject EN strings → HTML
                                                    5. refresh article covers
                                                    6. commit to main
                                                    7. push HTML → WordPress
                                                    8. post ✅ comment on issue
```

### Daily flow — what you do

1. **03:00 UTC** — GitHub sends you an email: "📰 Daily program intel · 2026-05-26"
2. Open the issue. Each country has a section with checkbox tasks.
3. **Tick the boxes** you approve, then save.
4. Done. `intel-apply` does everything else — Notion, HTML, WordPress — in one run (~2 min). A ✅ comment confirms when it's live.
5. Yesterday's issue auto-closes to keep your inbox clean.

## Sources scanned per country

Configured in [`tools/intel_sources.py`](./tools/intel_sources.py). Each entry has an authority weighting (3 = official gov, 2 = industry press / agency, 1 = community).

| Tier | Authority | Examples |
|---|---|---|
| Official | 3 | DGMM (Turkey), AIMA (Portugal), Enterprise Greece, MM2H Official, Immigration NZ |
| Industry agency | 2 | Henley & Partners, Latitude World, CS Global Partners |
| Industry press | 2 | IMI Daily (HTML + RSS), Investment Migration Council |
| Community | 1 | r/iwantout, r/expats, r/AmerExit, r/GoldenVisa, r/NomadCapitalist + 2 more |

Reddit is queried via the **public JSON API** (`/search.json?q=…&restrict_sr=on&t=week`) — no auth, no scraping.

## Signal extraction

Each fetched page is HTML-stripped and scanned with three regex families:

| Kind | Pattern (case-insensitive) | Example match |
|---|---|---|
| `money` | `$400K`, `$400,000`, `USD 400,000`, `€350,000`, `£500K` | "Turkey raised the threshold to **$500,000**…" |
| `date` | `2024`–`2030`, `Q1 2026`, `Q3/2026` | "effective **2026**" |
| `trigger` | `increase`, `raised to`, `lowered to`, `suspended`, `abolished`, `new threshold`, `effective from …`, `reform`, `amended` | "Turkey **amended** its Guideline…" |

Each match is captured with ±140 chars of surrounding context for the digest.

## Digest → proposed updates

The weekly digest only surfaces a proposed update when **all** of these hold:

1. The signal is `money` (not just date/trigger/mention)
2. Authority ≥ 2 (Reddit-only money mentions are too noisy)
3. The proposed value differs from the current payload by ≥ 5%
4. At least **2 independent sources** agree on the new value

This keeps the issue body tight — community chatter is collapsed into `<details>` summary blocks rather than turned into proposals.

## Approving a change

Each proposed update is a markdown checkbox with a machine-readable trailer:

```markdown
- [ ] **`hero_stats[0].num`**: `$400K` → `$500K`  *(3 sources)*
  <!-- intel:alias=turkey;field=hero_stats;jsonpath=0.num;new=$500K;kind=money -->
  - IMI Daily: "$500,000" — <https://imidaily.com/…>
  - Henley · Turkey: "$500K" — <https://henleyglobal.com/…>
  - CS Global · Turkey: "USD 500,000" — <https://csglobalpartners.com/…>
```

Workflow:

1. Edit the issue body and change `- [ ]` to `- [x]` on the rows you accept.
2. Save the issue.
3. `intel-apply.yml` fires on the `edited` event and does everything in one run: parses ticked boxes → PATCHes Notion → updates payload JSON → injects EN strings into HTML → pushes to WordPress → commits to main → posts ✅ comment. Live in ~2 minutes.

**Untick is not a revert** — the apply step is forward-only. Roll back via a follow-up issue or direct Notion edit.

## Force-review escape hatch

Every country block ends with a "Force review" checkbox:

```markdown
- [ ] **Force review** — open Notion row for turkey and audit manually
  <!-- intel:alias=turkey;action=force_review -->
```

Ticking this records an audit-trail entry in the apply summary but writes nothing — use it when the digest's signals warrant human attention without a specific field-level patch.

## WhatsApp delivery (follow-up)

The user-facing request is for the weekly digest to land on WhatsApp with the same checkbox semantics. The plan:

1. **Outbound** — extend `Worker JS files/nac-notion-proxy-worker.js` (or add a sibling worker) with a Twilio WhatsApp Business send endpoint. A new step in `intel-weekly-digest.yml` POSTs the issue URL + a condensed list of country headlines to the worker; worker formats it for WhatsApp template messages.
2. **Inbound** — Twilio inbound webhook → worker parses `tick turkey hero_stats[0].num` style replies, calls GitHub API to edit the issue body (replacing `- [ ]` with `- [x]` for matching trailers). The existing `intel-apply.yml` then fires on the resulting issue edit event.

This is **not implemented yet** — it needs a Twilio (or Meta Cloud API) account + WhatsApp Business sender provisioned. The GitHub-Issue flow above works standalone in the meantime.

## Manual operations

```bash
# Scrape one country right now (helpful while tuning sources)
python tools/intel_gather.py turkey

# Re-build the digest from existing snapshots
python tools/intel_digest.py --days=7

# Preview what `apply` would do without writing to Notion
python tools/intel_apply.py --body-file=path/to/issue.md --dry-run
```

## Files added

| Path | Role |
|---|---|
| `tools/intel_sources.py` | Per-country source config (Reddit subs, official agencies, industry press) |
| `tools/intel_gather.py` | Daily scraper — writes per-day signal JSON |
| `tools/intel_digest.py` | Weekly digest composer — emits checkbox markdown |
| `tools/intel_apply.py` | Reads issue body, applies ticked boxes to Notion + payloads |
| `.github/workflows/intel-daily.yml` | Cron @ 03:00 UTC daily |
| `.github/workflows/intel-weekly-digest.yml` | Cron @ 04:00 UTC Mondays |
| `.github/workflows/intel-apply.yml` | Tick-to-live: issue edit → Notion → HTML → WordPress (one run) |
| `INTEL-PIPELINE.md` | This file |

## Required secrets

Already in repo for the existing pull-notion pipeline; the intel-apply workflow reuses them.

| Secret | Used by | Purpose |
|---|---|---|
| `NOTION_KEY` | `intel-apply.yml` | PATCH `properties` on Notion DB rows |
| `WP_USER` | `intel-apply.yml` | WordPress REST API auth (also used by wp-sync) |
| `WP_APP_PASSWORD` | `intel-apply.yml` | WordPress app password (also used by wp-sync) |
| `GITHUB_TOKEN` | all three workflows | Push commits, manage issues |

## Adding a country / source

1. Edit `tools/intel_sources.py` — add the country block to `COUNTRY_SOURCES`, and any new Reddit sub to `REDDIT_SUBS`.
2. Make sure `data/<alias>_payload.json` exists for that country.
3. Manually trigger `intel-daily.yml` with the country alias to verify.
