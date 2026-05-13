# Brochure Notion Database — Schema Spec

> **Database:** `[NAC - Program Brochures]`
> **Notion DB ID:** `35f48ec25e8680f69c3dc5ad538e7ca8`
> **Purpose:** Single source of truth for every program brochure's content. Generator script reads this DB and produces brochure HTML files.

This mirrors the existing `[NAC - Property Listings]` pattern for property listings (one DB, one row per listing) — but for full program brochures.

---

## Architecture (target state, end-state)

```
[NAC - Program Brochures] Notion DB                ← source of truth
            │
            ├─ Notion proxy worker exposes /brochures/<alias>
            │
            └─ tools/build_brochures.py
                 → for each row: render brochure HTML from template
                 → write to Brochures html/<filename>
                 → CI sync_brochures.py pushes to WP
                 → live site updates
```

Editing a price, paragraph, or tier → edit Notion → next deploy → all 12 brochures stay coherent.

---

## Property catalogue (~95 fields per brochure — bilingual VI + EN)

Notion property types map to (Title, Text, Number, Select, Status, URL, Date). "Text long" = Notion's Rich Text type used for paragraphs and JSON-encoded structured data.

**Bilingual columns:** every prose field has both `*_vi` and `*_en` columns. The brochure HTML's existing VI/EN toggle reads from `data-vi`/`data-en` attributes; the generator will emit both into the HTML. JSON-encoded structured fields (`s02_tiers`, `s03_timeline`, etc.) include both `*_vi` and `*_en` keys inside the JSON, so each tier/timeline-step has its bilingual content together.

### A. Identity (13 fields)

| # | Property | Notion type | Description | Turkey example |
|---|---|---|---|---|
| 1 | `alias` | **Title** | Internal short name (lowercase, no spaces). Matches keys in `sync_brochures.py` BROCHURES dict and `data/listings.py`. | `turkey` |
| 2 | `country_vi` | Text | Vietnamese country name | `Thổ Nhĩ Kỳ` |
| 3 | `country_en` | Text | English country name | `Turkey` |
| 4 | `flag` | Text | Unicode flag emoji | `🇹🇷` |
| 5 | `program_code` | Select | CBI / RBI / LTR / CIP / MM2H | `CBI` |
| 6 | `program_tag` | Text | Notion CRM multi_select tag — must match brochure JS `var PROGRAM` exactly. | `CBI · Thổ Nhĩ Kỳ` |
| 7 | `program_vi` | Text | Vietnamese program display name (used in paywall lock card heading) | `Thổ Nhĩ Kỳ CBI` |
| 8 | `source_filename` | Text | HTML filename in `Brochures html/` | `turkey-cbi_8.html` |
| 9 | `wp_page_id` | Number | WordPress page ID for REST sync | `1836` |
| 10 | `wp_slug` | Text | WP page slug (parent: `/brochures/`) | `chuong-trinh-tho-nhi-ky-cbi-citizenship-by-investment` |
| 11 | `color_primary` | Text | CSS `--country` hex | `#8B1A1A` |
| 12 | `color_secondary` | Text | CSS `--country2` hex (darker shade) | `#6e1414` |
| 13 | `status` | Status | Draft / Live / Archived | `Live` |

### B. Hero block (15 fields)

| # | Property | Type | Description | Turkey example |
|---|---|---|---|---|
| 14 | `hero_bg_img` | URL | Background image URL (optional; gradient otherwise) | *(empty)* |
| 15 | `hero_breadcrumb_vi` | Text | Breadcrumb text (last segment) | `Chương Trình Quốc Tịch` |
| 16 | `hero_badge_vi` | Text | Top kicker badge text | `Quốc Tịch Đầu Tư · CBI · Nhanh Nhất Khu Vực` |
| 17 | `hero_title_top_vi` | Text | First line of H1 | `Quốc Tịch` |
| 18 | `hero_title_em_vi` | Text | Second line of H1 (italicised in design) | `Thổ Nhĩ Kỳ` |
| 19 | `hero_desc_vi` | Text long | Hero paragraph (~3 sentences) | `Chương trình quốc tịch qua đầu tư nhanh nhất thế giới — nhận hộ chiếu chỉ trong 3–6 tháng với ngưỡng đầu tư $400,000 vào bất động sản. Hộ chiếu Thổ Nhĩ Kỳ cho phép miễn visa 110+ quốc gia và là chiến lược tối ưu cho gia đình ASEAN muốn có quốc tịch thứ hai ngay lập tức.` |
| 20 | `hero_stats` | Text long (JSON) | 4 stat pairs `[{num,lbl},…]` | `[{"num":"$400K","lbl":"BĐS tối thiểu"},{"num":"3–6 tháng","lbl":"Nhận quốc tịch"},{"num":"110+","lbl":"Visa-Free"},{"num":"Trọn đời","lbl":"Không cần gia hạn"}]` |
| 21 | `nac_score` | Number | Overall NAC score /100 | `74` |
| 22 | `nac_score_label_vi` | Text | Verbal label below score | `★★★ Tốt – Cửa Vào Quốc Tịch Nhanh` |
| 23 | `score_invest` | Number | Sub-score: investment attractiveness (0–10) | `7.8` |
| 24 | `score_speed` | Number | Sub-score: processing speed | `9.5` |
| 25 | `score_lifestyle` | Number | Sub-score: quality of life | `6.8` |
| 26 | `score_passport` | Number | Sub-score: passport strength | `5.5` |
| 27 | `score_tax` | Number | Sub-score: tax friendliness | `8.0` |
| 28 | `score_citizenship` | Number | Sub-score: citizenship pathway | `9.8` |

### C. Section 01 — Overview (5 fields)

| # | Property | Type | Description | Turkey example |
|---|---|---|---|---|
| 29 | `s01_subtitle_vi` | Text long | Section intro paragraph | `Turkey Citizenship by Investment (CBI) — ra mắt năm 2017, cải cách năm 2018 — là chương trình quốc tịch qua đầu tư phổ biến nhất trong tầm ngắm của nhà đầu tư Đông Nam Á…` |
| 30 | `s01_ov_cards` | Text long (JSON) | 9 overview cards `[{icon,label,value,note},…]` | `[{"icon":"🏛️","label":"Loại chương trình","value":"Quốc Tịch Trực Tiếp","note":"Không phải cư trú trước"},{"icon":"📅","label":"Ra mắt","value":"2017 (cải cách 2018)","note":"8 năm hoạt động"},…]` (9 entries) |
| 31 | `s01_factcheck_vi` | Text long | Source/datacheck note (italic box) | `**Nguồn dữ liệu:** Tổng Cục Di Trú Thổ Nhĩ Kỳ … Q2/2026 · Hộ chiếu Index: Henley & Partners 2026.` |
| 32 | `s01_article_cta_text_vi` | Text long | "Read more" CTA prose | `Đọc thêm phân tích chuyên sâu: [Hy Lạp vs Thổ Nhĩ Kỳ 2026: So Sánh Toàn Diện](https://blog.…) — Góc nhìn từ đội ngũ NAC sau hơn 5 năm xử lý hồ sơ cho gia đình Việt.` |
| 33 | `s01_article_cta_url` | URL | Destination URL for the CTA button | `https://blog.nomadassetcollective.com/hy-lap-vs-tho-nhi-ky-2026-…` |

### D. Section 02 — Investment (4 fields)

| # | Property | Type | Description | Turkey example |
|---|---|---|---|---|
| 34 | `s02_subtitle_vi` | Text long | Intro | `Thổ Nhĩ Kỳ cung cấp 4 hình thức đầu tư để đủ điều kiện…` |
| 35 | `s02_warning_box_vi` | Text long | Amber warning box content | `**Lưu ý quan trọng 2025–2026:** Nhà đầu tư phải giữ tài sản ít nhất **3 năm**…` |
| 36 | `s02_tiers` | Text long (JSON) | Investment tier cards | `[{"badge":"Phổ Biến Nhất","amount":"$400,000","name":"Đầu tư bất động sản","region":"Toàn quốc","bar_pct":50,"featured":true,"tags":["Nhà ở / Căn hộ","Văn phòng / Thương mại","Off-plan đủ điều kiện","Giữ 3 năm tối thiểu"]},…]` (4 entries) |
| 37 | `s02_nac_note_vi` | Text long | Green NAC note box | `**Nhận định NAC:** Istanbul (Beylikdüzü, Başakşehir, Kağıthane) và Antalya tiếp tục là hai thị trường BĐS…` |

### E. Section 03 — Process (2 fields)

| # | Property | Type | Description | Turkey example |
|---|---|---|---|---|
| 38 | `s03_subtitle_vi` | Text long | Intro | `Đây là quy trình nhanh nhất thế giới trong nhóm CBI…` |
| 39 | `s03_timeline` | Text long (JSON) | Timeline steps | `[{"week":"Tuần 1–4","title":"Tìm kiếm & đặt cọc bất động sản","body":"NAC kết nối với luật sư và đại lý BĐS…"},…]` (5 entries; final entry has ✓ checkmark and is the "Done" step) |

### F. Section 04 — Family (LOCKED) (3 fields)

| # | Property | Type | Description | Turkey example |
|---|---|---|---|---|
| 40 | `s04_subtitle_vi` | Text long | Intro | `Thổ Nhĩ Kỳ bảo lãnh gia đình hạt nhân — đơn giản và rõ ràng…` |
| 41 | `s04_family_cards` | Text long (JSON) | Family eligibility cards | `[{"icon":"💍","title":"Vợ / Chồng hợp pháp","note":"Nhận quốc tịch cùng lúc…"},…]` (4 entries) |
| 42 | `s04_compare_note_vi` | Text long | Comparison info box | `**So sánh với Hy Lạp:** Greece Golden Visa bảo lãnh bố mẹ 2 bên và con đến 24 tuổi — phạm vi rộng hơn đáng kể…` |

### G. Section 05 — Tax (LOCKED) (4 fields)

| # | Property | Type | Description |
|---|---|---|---|
| 43 | `s05_subtitle_vi` | Text long | Intro |
| 44 | `s05_tax_cards` | Text long (JSON) | 6 tax-stat cards `[{icon,label,value,note},…]` |
| 45 | `s05_special_note_vi` | Text long | Gold info box (e.g. inflation / FX) |
| 46 | `s05_inheritance_note_vi` | Text long | Inheritance info box |

### H. Section 06 — Citizenship (LOCKED) (4 fields)

| # | Property | Type | Description |
|---|---|---|---|
| 47 | `s06_subtitle_vi` | Text long | Intro |
| 48 | `s06_roadmap` | Text long (JSON) | Roadmap steps `[{year,dot,label},…]` (last entry is the flag/✓ done step) |
| 49 | `s06_dual_citizenship_note_vi` | Text long | Dual-citizenship info box |
| 50 | `s06_nac_strategy_note_vi` | Text long | NAC strategy / combo gold box |

### I. Section 07 — Compare (LOCKED) (3 fields)

| # | Property | Type | Description |
|---|---|---|---|
| 51 | `s07_subtitle_vi` | Text long | Intro |
| 52 | `s07_compare_rows` | Text long (JSON) | Comparison table rows `[{flag,name,min_invest,type,mobility,time,score,highlight},…]` |
| 53 | `s07_cta_text_vi` | Text long | "Couldn't decide?" CTA paragraph |

### J. Section 08 — Pros / Cons (LOCKED) (4 fields)

| # | Property | Type | Description |
|---|---|---|---|
| 54 | `s08_subtitle_vi` | Text long | Intro |
| 55 | `s08_pros` | Text long (JSON) | `["Pro point 1", "Pro point 2", …]` (~9 entries) |
| 56 | `s08_cons` | Text long (JSON) | `["Con point 1", …]` (~8 entries) |
| 57 | `s08_risk_note_vi` | Text long | Amber risk-warning box |

### K. Section 09 — NAC verdict (LOCKED) (4 fields)

| # | Property | Type | Description |
|---|---|---|---|
| 58 | `s09_subtitle_vi` | Text long | Intro |
| 59 | `s09_recommendation_vi` | Text long | Main "Best for" recommendation box |
| 60 | `s09_cta_heading_vi` | Text | Final CTA card heading | `Sẵn sàng khởi động hồ sơ Thổ Nhĩ Kỳ?` |
| 61 | `s09_cta_body_vi` | Text long | Final CTA card body |

### L. Optional / future

- `listings` — Relation → `[NAC - Property Listings]` DB. Manual pin overrides. Default behaviour (auto cheapest+priciest by country) needs no relation.
- `last_synced` — Date. Set by the generator on each deploy; useful for staleness alerts.

---

## Total: ~55 properties

That's a lot but it's the actual data footprint of a brochure today. The alternative (split into multiple databases with sub-relations) trades width for depth and is harder to maintain.

---

## Why JSON-in-Text for tables / lists / timelines

Notion's relation/database features don't compose well with **N-rows-per-row** (e.g. "this brochure has 4 investment tiers; each tier is a row with its own properties"). The clean way is to introduce a child DB per nested type (Tiers DB, Timeline DB, etc.) — but that's 6+ additional databases to maintain.

JSON-in-rich-text is the pragmatic v1:
- Single DB to edit
- Generator parses JSON arrays into HTML
- Schema can be evolved without DB migrations
- Trade-off: editors must respect JSON syntax. We can validate with `tools/check_brochure_payload.py` before push.

Phase 2 — if the JSON editing UX is too painful — split the heaviest fields (`s02_tiers`, `s03_timeline`, `s07_compare_rows`) into their own relation DBs.

---

## Editorial workflow (when Notion is the source of truth)

1. Add a new brochure or edit an existing one in `[NAC - Program Brochures]`.
2. Set `status = Live`.
3. CI workflow `wp-sync` runs every push to `main` (or hourly cron):
   - `python tools/build_brochures.py` — reads Notion → renders HTML files into `Brochures html/`
   - `python tools/apply_listings.py` — re-renders Live Listings spotlight per brochure
   - `python sync_brochures.py --all` — pushes each HTML to its WP page
4. Live site reflects within ~30s of the workflow finishing.

The current `Brochures html/*.html` files become **build artefacts**, not source. Edits there are wiped on next deploy. (We'd add a `# generated by build_brochures.py — DO NOT EDIT` banner to the top of each file.)

---

## Migration phases

This is a one-way door (going to Notion-driven) — but we can stage it:

**Phase 1 (now):** Stand up the Notion schema. Populate Turkey only. Build extraction script that produces a Notion-API payload from `turkey-cbi_8.html`. **Don't change the live site.**

**Phase 2:** Build `tools/build_brochures.py` — Notion → HTML generator. Test by re-generating Turkey and diffing against the current hand-edited file. Once diff is ≤ minor whitespace, ship it.

**Phase 3:** Migrate the other 11 brochures by populating them in Notion. Each migration = extract → review → commit. Once a brochure is in Notion, the hand-edited file gets the `DO NOT EDIT` banner.

**Phase 4:** Decommission the hand-edit path. All brochure content lives in Notion.

---

## Open questions

1. **Bilingual fields:** schema currently `*_vi` only. Add parallel `*_en` columns now (cleaner) or phase 2 (less typing today)?
2. **Notion integration access:** the brochures DB (`35f48ec25e86…`) needs the `nac-notion-proxy` Worker's integration shared with it. Verify in Notion → DB → Connections → add the `NAC Notion Proxy` integration.
3. **Property creation:** create the ~55 properties manually in Notion UI, or have me drive it via the Notion API (`PATCH /databases/{id}`)?
4. **JSON validation:** want a `tools/check_brochure_payload.py` linter that warns on malformed JSON in `s02_tiers` etc. before push?

Tell me your preferences on these, and I'll execute Phase 1 (extraction script + Turkey populate).
