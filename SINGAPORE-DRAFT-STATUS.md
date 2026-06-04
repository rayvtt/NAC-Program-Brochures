# 🇸🇬 Singapore brochure — first-draft status

**File:** `Brochures html/singapore-gip.html` · **Parity:** 15/15
**WP page:** [2408 → /brochures/chuong-trinh-singapore-gip-dau-tu-quyen-cu-tru/](https://nomadassetcollective.com/brochures/chuong-trinh-singapore-gip-dau-tu-quyen-cu-tru/)
**Notion entry:** [singapore (Draft)](https://app.notion.com/p/37548ec25e86811b89eed62e5420e9de)

## What's wired up

- ✅ **Brochure HTML** — Cyprus master clone with identity swap + Singapore color
  (#EE2536 red + gold). Hero image set to the Goway Marina-Bay-at-night photo.
- ✅ **sync_brochures.py** — `singapore` alias registered → WP page **2408**,
  slug `chuong-trinh-singapore-gip-dau-tu-quyen-cu-tru`. Merge to `main`
  triggers wp-sync.
- ✅ **Notion DB entry** — `singapore` page created in 🔖 NAC - Brochures
  Meta-data with status `Draft`. Identity + hero + §01 overview + §02
  investment tiers + §03 timeline fully populated in both VI and EN.

## What's accurate as of this draft (visible front-of-paywall)

| Section | Source / accuracy |
|---|---|
| `<title>`, color palette | rewritten |
| Hero (badge / H1 / desc / 4 stats) | EDB factsheet |
| §01 Overview (9 cards + data source) | EDB / MOM / ICA / Henley |
| §02 Investment (4 tiers + warning + NAC note) | EDB GIP factsheet (5 May 2025) |
| §03 Process timeline (5 steps + GIP advantage box) | EDB |
| Breadcrumb / paywall heading / Twemoji | auto-swapped clean |

## What still needs NAC editorial input (paywall §04–§09)

The HTML paywall sections still hold **Cyprus content** that the wp-sync
will push verbatim if the brochure goes live as-is. These fields are
**empty in the Notion entry** — fill them in to override:

| Notion field | Singapore-specific content needed |
|---|---|
| `④ family cards (JSON)` / `④ subtitle (VI/EN)` / `④ compare note` | EP DP rules (SGD 6,000/mo for spouse+kids); LTVP for parents (SGD 12,000/mo) |
| `⑤ tax cards (JSON)` / `⑤ subtitle` / `⑤ inheritance note` / `⑤ special note` | 17% flat corp; progressive personal up to 24%; no global income tax for PR; no inheritance tax |
| `⑥ roadmap (JSON)` / `⑥ subtitle` / `⑥ dual citizenship note` / `⑥ NAC strategy note` | PR → 2+ yrs → ICA citizenship application; SG requires renouncing prior citizenship |
| `⑦ compare rows (JSON)` / `⑦ subtitle` / `⑦ CTA text` | Compare vs UAE / Malaysia / Thailand / Hong Kong |
| `⑧ pros (JSON)` / `⑧ cons (JSON)` / `⑧ subtitle` / `⑧ risk note` | GIP raise to SGD 10M; ABSD on property; NS for boys; passport upside |
| `⑨ CTA heading / body / recommendation / subtitle` | Who Singapore PR is best for (UHNW with Asia-Pacific business) |

Plus the NAC composite + radar:

| Field | What |
|---|---|
| `NAC score` (0–100) | NAC composite score |
| `NAC score label (VI)` / `(EN)` | e.g. "★★★★★ Xuất Sắc — Trung Tâm Tài Chính Á" / "★★★★★ Excellent — Asian Financial Hub" |
| `score · speed` / `investment` / `passport` / `lifestyle` / `tax` / `citizenship` (0–10 each) | Radar values |
| `① article CTA URL` | Singapore PR analysis post on blog.nomadassetcollective.com |

## Workflow once Notion is filled in

1. Update fields in the [Notion page](https://app.notion.com/p/37548ec25e86811b89eed62e5420e9de)
2. Set `status` from **Draft** → **Live**
3. Next cron tick (every 10 min via `.github/workflows/pull-notion.yml`) runs:
   - `tools/pull_from_notion.py` → `data/singapore_payload.json`
   - `tools/inject_notion_en_to_html.py` → merges into `singapore-gip.html`
   - `tools/refresh_article_covers.py` → pulls article og:image
   - `sync_brochures.py --all` → PUTs `singapore-gip.html` to WP page 2408
4. Live page updates at https://nomadassetcollective.com/brochures/chuong-trinh-singapore-gip-dau-tu-quyen-cu-tru/

## ⚠️ Caveat: Cyprus content will go live if merged as-is

The HTML paywall §04–§09 currently holds Cyprus-derived content. If this
PR is merged before the Notion fields are filled in for those sections,
the wp-sync will push the Cyprus content to WP page 2408. Two options:

- **(A) Hold the merge** until NAC editorial finishes the Notion paywall fields,
  then status → Live, then merge.
- **(B) Merge now** to get the front-of-paywall live (the public-facing
  sections); the paywall stays Cyprus-flavoured until Notion is filled in.

## TODO: hero image hosting via Cloudflare

The hero `background-image` URL currently points directly at the Goway
production CDN:
```
https://images.goway.com/production/featured_images/Aerial%20view%20...
```
Per your note, this should be re-hosted via Cloudflare DNS (R2 bucket /
custom-domain proxy / Worker). I haven't done this autonomously — needs
clarification on:
- Which Cloudflare zone (e.g. `cdn.nomadassetcollective.com`)?
- R2 bucket (existing or new)?
- Or a Worker that proxies + caches images?

Once decided, I'll: upload the asset, set the DNS record, and swap the
`background-image` URL in the brochure HTML to the new origin.
