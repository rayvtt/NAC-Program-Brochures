# 🇸🇬 Singapore brochure — first-draft status

**File:** `Brochures html/singapore-gip.html` · **Parity:** 15/15

## What's done in this draft

The brochure was scaffolded from the Cyprus master and rewritten with
authoritative public-source Singapore facts in the **front-of-paywall**
sections that all visitors see:

| Section | Status | Source |
|---|---|---|
| `<title>` | ✅ Singapore GIP | rewritten |
| Color palette | ✅ Singapore red (#EE2536) + Gold | rewritten |
| Hero (badge, H1, desc, 4 stats) | ✅ GIP SGD 10M + ASEAN gateway | EDB |
| §01 Overview (9 cards + data source) | ✅ GIP + EP→PR dual pathway | EDB / MOM / ICA |
| §02 Investment (4 tiers + amber + green box) | ✅ GIP A/B/C + EP self-employed | EDB GIP factsheet |
| §03 Process timeline (5 steps + advantage box) | ✅ EOI → EDB interview → invest → ICA → PR | EDB |
| Breadcrumb | ✅ "Singapore" | auto-swap |
| Paywall heading | ✅ "Brochure Singapore PR?" | auto-swap |
| Twemoji flag fallback | ✅ wired from clone | inherited |

## What still needs editorial work (paywall §04–§09)

The sections behind the paywall still have **Cyprus-derived content**
that needs NAC editorial rewrites:

- §04 Tax — currently shows Cyprus's Non-Dom 17-year regime; Singapore is
  17% flat corporate, progressive personal, no global income tax for PR.
- §05 Family inclusion — currently shows Cyprus's "spouse + children +
  parents" rules; Singapore EP DP requires SGD 6,000/mo for spouse+kids,
  LTVP requires SGD 12,000/mo for parents.
- §06 Citizenship pathway — currently shows Cyprus's 7-year path;
  Singapore is PR → 2+ years → citizenship via ICA application.
- §07 NAC Index / radar — currently shows Cyprus's NAC composite score
  (8x/100) and radar values; Singapore needs its own score.
- §08 Comparison table — currently compares Cyprus vs Greece/Turkey/etc.;
  needs Singapore-specific competitor matrix.
- §09 Pros & Cons + NAC verdict — currently Cyprus-specific; needs
  Singapore editorial.

## What's NOT yet done (infrastructure)

- **Not registered** in `sync_brochures.py` — won't auto-deploy to WP
  on push to main. Add when ready: needs WP page ID + slug.
- **VI_STRINGS / EN_STRINGS arrays** still hold Cyprus content. If a
  visitor toggles VI/EN, the toggle may revert visible text to Cyprus
  for some elements. Behavior should be tested before going live.
- **Hero background image** is currently Cyprus's (Mediterranean
  coastline). Needs a Singapore skyline image.
- **WP page** doesn't exist yet — needs to be created with the right
  slug pattern (e.g. `chuong-trinh-singapore-gip-cu-tru-dau-tu`).

## Authoritative source facts used

- **EDB GIP factsheet** (updated 5 May 2025) — Option A SGD 10M, Option B
  SGD 25M GIP-approved fund, Option C SGD 200M AUM family office with
  SGD 50M deployed; ~12-month processing; direct PR.
- **MOM Singapore EP rules** — minimum SGD 5,600/mo (SGD 6,200 finance),
  3–8 weeks processing; PR application via PTS after 1–2 years.
- **ICA** — PR / Re-Entry Permit (REP) renewable every 5 years.
- **Henley Passport Index 2026** — Singapore citizenship passport ~190
  visa-free, top-3 globally.

## Next steps before going live

1. NAC editorial review of paywall §04–§09 — replace Cyprus content with
   Singapore-specific.
2. NAC set composite score + radar values for §01/§07.
3. Pick Singapore hero image.
4. Create WP page; add `singapore` alias to `sync_brochures.py` with
   page ID + slug.
5. Pull through VI_STRINGS / EN_STRINGS sync so both languages match the
   visible Singapore content.
6. Decide on CLP — there's already a Live CLP for Singapore in the
   Notion "🌍 NAC - Country Listings" DB (slug `sg`); listings link can
   be added to `tools/repoint_listings_to_clp.py` once approved.
