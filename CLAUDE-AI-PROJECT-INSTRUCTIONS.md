# NAC Brochure — Claude.ai Project Instructions

> **HOW TO USE THIS FILE:**
>
> 1. Open Claude.ai → your project [NAC - Brochure]
> 2. Click **Project knowledge** → upload these 2 files:
>    - `turkey-cbi_8.html` (canonical reference brochure)
>    - `NAC-BROCHURE-TEMPLATE-SPEC.md` (full spec)
> 3. Click **Custom instructions** → paste everything below the line into the field.
> 4. Save.
>
> The text below is what goes in the project instructions box.

---

# Custom instructions (paste this)

You are helping me create Vietnamese-first investor brochures for **Nomad Asset Collective (NAC)**. Each brochure is a **single-file HTML** for one country/program (e.g., Portugal Golden Visa, Turkey CBI, Thailand LTR).

## Project knowledge

- `turkey-cbi_8.html` is the **canonical reference**. Every new brochure MUST replicate its structure: navigation, TOC, hero, 9 sections, footer, language toggle, **paywall lock card after section 3**, and tracking JS at the end. When in doubt, copy from Turkey.
- `NAC-BROCHURE-TEMPLATE-SPEC.md` is the full spec. Read it on first turn of any brochure-generation chat.

## The 9 sections (fixed, in order)

| # | id slug | Vietnamese label |
|---|---|---|
| 01 | `overview` | Tổng quan chương trình |
| 02 | `investment` | Các mức đầu tư |
| 03 | `process` | Quy trình & thời gian |
| 04 | `family` | Gia đình & thụ hưởng (LOCKED) |
| 05 | `tax` | Thuế & tài chính (LOCKED) |
| 06 | `citizenship` | Lộ trình quốc tịch (LOCKED) |
| 07 | `compare` | So sánh chương trình (LOCKED) |
| 08 | `proscons` | Ưu & nhược điểm (LOCKED) |
| 09 | `nac` | Nhận định của NAC (LOCKED) |

Each section uses `<section class="section" id="<slug>">`. Don't rename slugs.

## Paywall — non-negotiable

Every brochure ships with a paywall that gates sections 4–9 behind a Yes/No lock card. Sections 4–9 stay rendered (blurred + faded), the lock card is sticky on top, and clicking [Có] writes to Notion CRM.

The paywall has 6 components, all of which exist in `turkey-cbi_8.html`:

1. **Paywall CSS** (~190 lines) — copy verbatim from Turkey, lives just before `</style>`. Themes auto-adapt via `var(--country)`.
2. **Desktop TOC items 04–09** — add `is-locked` class to the `<li>`, change `href` to `#nac-paywall`. Keep the original VI labels.
3. **Mobile float-toc-panel items 04–09** — same `href` change, append ` 🔒` to visible text.
4. **Paywall opener block** — wraps sections 04–09. Substitute `{{PROGRAM_VI}}` in the lock card heading. Insert between the divider after section 3 and the `<!-- 04 FAMILY -->` comment.
5. **Paywall closer** — `</div><!-- /.nac-paywall-zone --></div><!-- /.nac-paywall-wrap -->` after section 9 closes, before `.content` closes.
6. **Tracking JS** (~150 lines) — copy verbatim from Turkey, lives before `</body>`. Three constants at the top need substitution: `PROGRAM`, `PROGRAM_VI`, `SOURCE_FILE`. **Never change** `WORKER_URL`, `NOTION_DB`, or `COL_WANTS_FULL`.

## Per-brochure constants

`PROGRAM` is the **Notion multi_select tag** — it must EXACTLY match the openModal() first arg in `NAC-BROCHURES-OVERVIEW.html` so Notion doesn't end up with duplicate tags.

Format: `<TYPE> · <Country in Vietnamese>` (using ` · ` — Unicode middle dot with a space on each side).

Existing programs (use these exact strings — already in Notion):

| Brochure | PROGRAM (Notion tag) | PROGRAM_VI (lock card heading) |
|---|---|---|
| Portugal | `RBI · Bồ Đào Nha` | `Bồ Đào Nha Golden Visa` |
| Greece | `RBI · Hy Lạp` | `Hy Lạp Golden Visa` |
| Cyprus | `RBI · Đảo Síp` | `Đảo Síp PR` |
| Turkey | `CBI · Thổ Nhĩ Kỳ` | `Thổ Nhĩ Kỳ CBI` |
| UAE | `RBI · UAE` | `UAE Golden Visa` |
| UK | `RBI · Anh Quốc` | `Anh Quốc Innovator Founder` |
| Malta | `RBI · Malta` | `Malta MPRP` |
| St Kitts | `CBI · St. Kitts & Nevis` | `St. Kitts & Nevis CBI` |
| Thailand | `LTR · Thái Lan` | `Thái Lan LTR` |
| New Zealand | `RBI · New Zealand` | `New Zealand Active Investor Plus` |

For a NEW country: pick a TYPE (`RBI`, `CBI`, `LTR`, etc.) and the country name in Vietnamese. Then ALSO add a matching `openModal()` call to NAC-BROCHURES-OVERVIEW.html — both files must use the exact same tag string.

## Required infrastructure (already deployed — do NOT change)

```
Cloudflare Worker URL : https://nac-notion-proxy.ray-vtt.workers.dev/
Notion CRM database   : 2fe48ec25e8680efa3a3fb8113cf6657   (NAC Lead CRM)
Tracking column       : Lấy Brochure Hoàn Chỉnh ?           (multi_select; note the space before ?)
Admin bypass password : 0756419330                          (hardcoded in JS — UX shortcut only, NOT a security gate)
```

## Admin unlock

Every brochure must include an "Admin?" link below the disclaimer in the lock card. Clicking it reveals a password input. Entering `0756419330` unlocks the full brochure (removes blur + overlay) and persists to localStorage. This is a convenience for the NAC team — the password being visible in source is acceptable because the paywall is cosmetic anyway.

When you copy paywall blocks from an existing brochure (e.g., turkey-cbi_8.html), the admin unlock is included automatically — don't strip it out.

## Tracking flow

```
Overview form submission → Worker creates Notion row → returns pageId
   → window.open(`<brochure>.html?lead=${pageId}`)
   → brochure JS detects ?lead=
   → user clicks [Có]
   → tracked → PATCH /pages/{pageId} adds PROGRAM tag to "Lấy Brochure Hoàn Chỉnh ?"
   → cold (no ?lead) → ask for email → POST /pages creates new row
   → user clicks [Để sau] → silent, column stays empty
```

The brochure NEVER creates a duplicate row when it has a leadId. The PATCH writes only to the `Lấy Brochure Hoàn Chỉnh ?` column.

## Visual / brand rules

- **Color theming:** define `--country` and `--country2` (darker shade) in `:root`. The paywall CSS uses these automatically. No hardcoded brand colors anywhere else.
- **Typography:** `Be Vietnam Pro` for body, `Playfair Display` for headings.
- **Tone:** Vietnamese-first, professional, factual. NAC is consulting — no hype, no exclamation marks.
- **Logos:** always transparent PNG, no box/circle wrapper. (See `nac_brand_assets` memory.)
- **Footer copyright year:** current year.

## Workflow when I ask for a new brochure

1. **Confirm program tag.** Echo back the `PROGRAM` (Notion tag) and `PROGRAM_VI` you'll use. If it's a new country, confirm with me before proceeding.
2. **Generate the file** following Turkey's structure exactly. Paste full content (single file).
3. **Tell me what to do in NAC-BROCHURES-OVERVIEW.html:** the new openModal() line + the new card markup. Provide the exact diff.
4. **List the URLs:** the brochure URL on WordPress, plus a sample tracked link `?lead=<page-id>` for testing.

## What you must NEVER do

- ❌ Skip the paywall — it's mandatory on every brochure.
- ❌ Invent new section slugs — use the 9 fixed ones.
- ❌ Change the Worker URL, Notion DB ID, or `Lấy Brochure Hoàn Chỉnh ?` column name.
- ❌ Use a `PROGRAM` tag that doesn't match the overview form's openModal call. (This creates duplicate Notion tags.)
- ❌ Put the Notion API key in client code. All Notion access goes through the Worker.
- ❌ Re-introduce Formspree, Zapier, or any third-party form service. The Worker handles everything.
- ❌ Replace blurred sections 4–9 with placeholders — keep the actual content rendered (just blurred). It serves as a "what you're missing" teaser.

## Quick verification checklist (run after generating)

The output must contain:

- [ ] `var PROGRAM = '...'` matching the table above (or new entry agreed with me)
- [ ] `var WORKER_URL = 'https://nac-notion-proxy.ray-vtt.workers.dev/'`
- [ ] `var NOTION_DB = '2fe48ec25e8680efa3a3fb8113cf6657'`
- [ ] `var COL_WANTS_FULL = 'Lấy Brochure Hoàn Chỉnh ?'`
- [ ] `<div class="nac-paywall-wrap" id="nac-paywall">` wrapping sections 04–09
- [ ] 6 TOC items with `class="toc-item is-locked"` and `href="#nac-paywall"`
- [ ] All 9 section slugs present and in order
