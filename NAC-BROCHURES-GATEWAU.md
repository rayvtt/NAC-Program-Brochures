# NAC Brochure Template Spec

> Paste this into your Claude.ai project instructions (Chat → Product → NAC Brochures) so every new country brochure ships with the paywall + Notion CRM tracking already wired in.

---

## What this is

A single-file Vietnamese-first investor brochure (`<country>-<program>.html`) that:

1. Renders **9 standard sections** (Tổng quan → Đầu tư → Quy trình → Gia đình → Thuế → Quốc tịch → So sánh → Ưu/nhược → Nhận định NAC).
2. **Locks sections 4–9 behind a paywall** — first 3 sections are free; the rest are blurred with a "Có / Để sau" lock card on top.
3. **Tracks every interaction in Notion** ("NAC Lead CRM" database) via the Cloudflare Worker proxy — no Formspree, no Zapier, no API keys in client code.

---

## Required structure

Every brochure MUST have these 9 sections in this exact order, each with `<section class="section" id="<slug>">`:

| # | Slug | Vietnamese label |
|---|---|---|
| 01 | `overview`    | Tổng quan chương trình |
| 02 | `investment`  | Các mức đầu tư |
| 03 | `process`     | Quy trình & thời gian |
| 04 | `family`      | Gia đình & thụ hưởng        🔒 |
| 05 | `tax`         | Thuế & tài chính            🔒 |
| 06 | `citizenship` | Lộ trình quốc tịch          🔒 |
| 07 | `compare`     | So sánh chương trình        🔒 |
| 08 | `proscons`    | Ưu & nhược điểm             🔒 |
| 09 | `nac`         | Nhận định của NAC           🔒 |

CSS color theming uses `var(--country)` — define this at the top of the brochure's `:root` (one solid + one darker shade).

---

## Per-brochure constants

The lock card and Notion calls require 3 constants, declared at the top of the closing `<script>` block:

```js
var PROGRAM        = 'XXX · <Vietnamese country>';   // EXACT Notion multi_select tag — must match the overview form's openModal() first arg
var PROGRAM_VI     = '<friendly display name>';      // shown in lock card heading
var SOURCE_FILE    = '<filename>.html';              // for audit logs
```

`PROGRAM` is the most important. It must match the tag NAC-BROCHURES-OVERVIEW.html sends to Notion. Format: `<TYPE> · <Country in Vietnamese>`. Examples:

| Brochure | PROGRAM (Notion tag) | PROGRAM_VI (display) |
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

When adding a new country: choose the type prefix (`RBI`, `CBI`, `LTR`, etc.) + the country name in Vietnamese, joined with ` · ` (Unicode middle dot, surrounded by spaces). Then ALSO add a matching openModal() call in NAC-BROCHURES-OVERVIEW.html.

---

## Required code blocks (copy verbatim from any existing brochure)

A new brochure must include all six of these — they are byte-for-byte copyable from `turkey-cbi_8.html` (or any existing brochure):

### 1. Paywall CSS (~190 lines)

Lives between the `</style>` of the original brochure styles and `</style>`. Starts with the comment:

```css
/* ============================================================
   NAC PAYWALL — Lock sections 4+ behind email-capture form
   ============================================================ */
```

Auto-themes from `var(--country)`. No per-brochure changes needed.

### 2. Desktop TOC (sections 04–09 marked locked)

In `<ul class="toc-list" id="toc">`, items 04–09 use:

```html
<li class="toc-item is-locked"><a class="toc-link" href="#nac-paywall"><span class="toc-num">04 </span>Gia đình & thụ hưởng</a></li>
```

Two differences from items 01–03:
- `<li>` has `is-locked` class
- `href` points to `#nac-paywall` (anchors to the lock card, not the blurred section)

### 3. Mobile float-toc-panel (sections 04–09 marked locked)

In `<div class="float-toc-panel" id="floatTocPanel">`, locked items use:

```html
<a href="#nac-paywall" onclick="closeFToc()">04 · Gia đình & thụ hưởng 🔒</a>
```

Two differences:
- `href` points to `#nac-paywall`
- ` 🔒` appended to visible text

### 4. Paywall opener (HTML)

Inserted between the `<hr class="divider">` after section 03 (process) and the `<!-- 04 FAMILY -->` comment. Wraps everything from sections 04–09 in `.nac-paywall-wrap` → `.nac-paywall-zone` (blurred) and overlays `.nac-paywall-overlay` → `.nac-paywall-card` on top.

The **only per-brochure substitution** in this block is the lock card heading:

```html
<h3>Đọc trọn bộ Brochure {{PROGRAM_VI}}?</h3>
```

Replace `{{PROGRAM_VI}}` with the brochure's display name (e.g., `Thái Lan LTR`).

### 5. Paywall closer (HTML)

Inserted right after section 09's closing `</section>`, before the `</div>` that closes `.content`:

```html
      </div><!-- /.nac-paywall-zone -->
    </div><!-- /.nac-paywall-wrap -->
```

No substitutions.

### 6. JS handler (~150 lines)

Lives right before `</body>`, after all other `</script>` tags. Constants at the top of the IIFE need substitution:

```js
var PROGRAM        = '<<NOTION TAG>>';
var PROGRAM_VI     = '<<DISPLAY NAME>>';
var SOURCE_FILE    = '<<FILENAME>>';
```

Everything below is shared across all brochures and MUST NOT be edited per-brochure:

```js
var WORKER_URL     = 'https://nac-notion-proxy.ray-vtt.workers.dev/';
var NOTION_DB      = '2fe48ec25e8680efa3a3fb8113cf6657';   // NAC Lead CRM
var COL_WANTS_FULL = 'Lấy Brochure Hoàn Chỉnh ?';          // Notion multi-select column
```

The JS:
- reads `?lead=<NotionPageID>` from URL
- on **Có** + leadId present → `PATCH /pages/{leadId}` adds `PROGRAM` to `Lấy Brochure Hoàn Chỉnh ?` multi-select
- on **Có** + no leadId → asks for email → `POST /pages` creates a new row in NAC Lead CRM
- on **Để sau** → silent no-op (column stays empty for that lead × that brochure)
- mailto fallback to ray@/hello@nomadassetcollective.com if Worker fails

---

## Tracking flow (end-to-end)

```
User on NAC-BROCHURES-OVERVIEW.html
   │
   │ 1. Clicks brochure card → modal opens with form
   │ 2. Fills form → submits → POST {parent: NAC Lead CRM, properties:{...}} to Worker
   │ 3. Worker creates row → returns { pageId }
   │ 4. Overview opens brochure: window.open(`<brochure>.html?lead=${pageId}`)
   ▼
Brochure JS reads ?lead= → state="ask"
   │
   │ User reads sections 1-3, scrolls into blurred zone, sees lock card
   │
   ├─ clicks [Có]
   │     ├─ tracked → PATCH /pages/{lead} adds PROGRAM to "Lấy Brochure Hoàn Chỉnh ?"
   │     └─ shows "📨 Đã nhận yêu cầu của bạn"
   │
   └─ clicks [Để sau]
         └─ silent dismiss, column untouched
```

**One Notion row per lead.** The brochure paywall *updates* the existing row — never creates a duplicate.

---

## Notion CRM schema (NAC Lead CRM)

Database ID: `2fe48ec25e8680efa3a3fb8113cf6657`

Required columns (Vietnamese names — exact match):

| Column | Type | Used by |
|---|---|---|
| Tên khách hàng | title | overview form |
| Email | email | overview form, brochure cold-flow |
| Số điện thoại | phone_number | overview form |
| Nguồn lead | select | overview form (`Lấy Brochures`) |
| Status | select | overview form (`🆕 Mới`) |
| Ngày liên hệ | date | overview form |
| Chương trình quan tâm | multi_select | overview form (the `PROGRAM` tag) |
| Ghi chú | rich_text | overview form |
| Ngân sách (USD) | number | overview form (optional) |
| Long Term | select | overview form (optional) |
| **Lấy Brochure Hoàn Chỉnh ?** | **multi_select** | **brochure paywall** ← note the space before `?` |

The brochure paywall ONLY writes to `Lấy Brochure Hoàn Chỉnh ?` (and on cold-flow, all the columns the overview form would write).

---

## Cloudflare Worker

Worker URL: `https://nac-notion-proxy.ray-vtt.workers.dev/`
Source: `nac-notion-proxy-worker.js` (in this folder)

Holds the Notion API key server-side. Three actions:
- `create` (default): `POST /v1/pages` — overview form, brochure cold-flow
- `update` (`_meta.action: "update"` + `_meta.page_id`): `PATCH /v1/pages/{id}` — brochure tracked Yes
- `query` (`_meta.action: "query"` + `database_id`): `POST /v1/databases/{id}/query` — for future lookups

---

## Admin unlock (NAC team convenience)

Every brochure has a small `Admin?` link below the disclaimer in the lock card (ASK stage). Clicking it reveals a password field. Entering **`0756419330`** removes the blur, hides the overlay, and persists `nac-paywall-unlocked` to `localStorage` so admin doesn't have to re-enter on the next visit.

⚠️ This is **NOT a security gate** — the password is hardcoded in JS, anyone who reads the source sees it. That's acceptable because the paywall itself is cosmetic (DevTools can remove the blur in 5 seconds). Treat it strictly as a UX shortcut for the NAC team previewing brochures.

The admin code lives inside the same paywall blocks (CSS + opener + JS) — when you copy from any existing brochure, admin unlock is included automatically.

---

## Checklist for a new brochure

When you ask Claude to generate a new country brochure:

- [ ] Pick `PROGRAM` tag (e.g., `RBI · Tây Ban Nha`) and add a matching openModal() call in NAC-BROCHURES-OVERVIEW.html.
- [ ] Use the 9-section structure above. Don't rename slugs.
- [ ] Define `--country` and `--country2` (darker) CSS vars at top of `:root`.
- [ ] Copy the 6 paywall blocks from any existing brochure. Substitute only:
  - `{{PROGRAM_VI}}` in the opener (lock card heading)
  - `PROGRAM`, `PROGRAM_VI`, `SOURCE_FILE` in the JS constants
- [ ] Mark TOC items 04–09 as `is-locked` with `href="#nac-paywall"` (desktop sidebar AND mobile floatTocPanel).
- [ ] After saving: open the file directly (no `?lead=`), click [Có], confirm a new row appears in NAC Lead CRM with the `PROGRAM` tag in the "Lấy Brochure Hoàn Chỉnh ?" column. Then test with `?lead=<existing-page-id>` to confirm the existing row is updated, not duplicated.

---

## Reference files in this folder

| File | Purpose |
|---|---|
| `turkey-cbi_8.html` | Canonical paywall reference (first one built) |
| `NAC-BROCHURES-OVERVIEW.html` | The funnel start — has the modal form + appends `?lead=` to brochure URLs |
| `nac-notion-proxy-worker.js` | Cloudflare Worker source code (deploy to dash.cloudflare.com → Workers) |
| `NAC-RESIDENCE-INDEX.html` | Comparison index page (uses same Worker, no paywall) |
| `NAC-PROPERTY-HUB (2).html` | Property listings (uses same Worker, no paywall) |
