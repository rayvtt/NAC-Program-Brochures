# 🇳🇷 Nauru brochure — rebuild brief

> **Status: BLOCKED — needs a from-scratch rebuild, not a find/replace.**
> The current `Brochures html/nauru-cbi.html` is a ~95% clone of the Antigua
> CBI brochure (178 "Antigua" refs, 9 "Nauru" refs). It was scaffolded by
> copying Antigua and the conversion was never done. **The live WP page is
> currently serving wholesale Antigua content to clients** — recommend
> taking it off live until this rebuild lands.

## Why it can't be auto-converted

A scripted clone-swap was attempted and reverted because it produced
fabrications:
- Global `Caribbean → Pacific` turned *"5 Caribbean CBI countries (St Kitts,
  Dominica, Grenada, St Lucia…)"* into *"5 **Pacific** CBI countries"* — false.
- Antigua-specific facts (resort names Hodges Bay / Tamarind Hills, the
  two-route NDF+real-estate structure, OECS price-harmonisation narrative,
  150+/UK+Schengen passport) are woven through prose, the comparison table,
  pros/cons, the process timeline, and the JS string-mirror arrays.
- The brochure carries **NAC-proprietary editorial data** that cannot be
  invented: composite score `82/100`, the score-bar values, and the radar /
  comparison chart datasets.

## Authoritative Nauru facts (public sources, June 2026)

| Field | Value |
|---|---|
| Official program | Nauru Economic & Climate Resilience Citizenship Program |
| Launched | **January 2025** (world's newest CBI) |
| Route | **Contribution only** (to the Treasury / climate-resilience fund) — **no real-estate route** |
| Contribution (single) | **USD 120,000** standard |
| Promo | **USD 95,000** ($25,000 discount) for applications filed before **30 Jun 2026** |
| Application fee | **USD 5,000** per applicant |
| Family add-ons | +USD 2,000 contribution per dependent 16+; siblings +USD 15,000 each (confirm exact tiers with agent) |
| Passport | visa-free to **~85+** countries — **Hong Kong, Singapore, UAE, South Korea**. **NOT UK, NOT Schengen.** |
| Processing | **3–4 months** |
| Residency | **None** — no physical presence / no visit to Nauru required |
| Dual citizenship | Permitted |
| Geography | Central Pacific (Micronesia); Commonwealth & Pacific Islands Forum member (not OECS) |
| Funds | climate-resilience / higher-ground relocation |

Sources: ecrcp.gov.nr (official), henleyglobal.com/citizenship-investment/nauru,
globalcitizensolutions.com, astons.com, immigrantinvest.com.

## Sections needing authored Nauru content

- `<title>`, hero (badge, H1, desc, 4 stat tiles), score card (flag + **82 score + bars = NAC to set**), breadcrumb
- Hero background image (currently an Antigua beach photo — needs a Nauru/Pacific image)
- §01 overview: 8 cards (launched, geo, residency, processing, passport, tax) + data-source line
- §02 investment: collapse two-route (NDF $230K + RE $300K) → single contribution ($120K / $95K promo); rewrite amber "2024 OECS update" box and the green "NAC insight" box (Hodges Bay/Tamarind Hills)
- §03 process timeline (CIU/St John's/oath → Nauru Program Office contribution flow)
- Comparison table row + pros/cons list (passport count, cost, timing)
- Tax §, family §, citizenship-pathway § (paywall §04–09) — not yet audited
- `radar` / comparison **chart datasets** + the `VI_STRINGS`/`EN_STRINGS` JS mirror arrays
- Footer copyright + data-source; CRM program tag

## Gaps that need NAC / you to supply

1. **NAC composite score + score-bar + radar values** for Nauru (proprietary).
2. A **Nauru hero image** URL.
3. **Exact family-member fee tiers** and any **tax** specifics for Nauru.
4. Confirm the **current visa-free count** to quote (official says "85+").
