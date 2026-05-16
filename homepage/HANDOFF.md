# NAC Homepage Revamp — Session Handoff

> Paste this whole file into the new session (with the correct repo connected) to pick up exactly where we left off.

---

## 1. The brief (verbatim from Ray)

> Full visual audit of nomadassetcollective.com and redesign so it's a pure premium feel and highlights exactly what is working well on the website rather than being hidden from the main site. The three components that look amazing are: **Brochures overview page**, **Blog (NAC Times)**, and **NAC Residence Index**. Target repo: `https://github.com/rayvtt/NAC-homepage-revamp.git` (fresh project). Pull in relevant ClaudeMD/workers from existing repos to learn the sitemap. Premium feel that fits Ray (Leo midheaven — bold, executive, charismatic, regal).

### Decisions Ray confirmed in the prior session

| Question | Answer |
|---|---|
| Repo destination | Build on branch `claude/nac-homepage-redesign-uYSus` |
| Hero treatment | **Combination of 2+3+4**: cinematic editorial + founder-led + split (globe + manifesto). Also surface **Property Hub live listings** (https://nomadassetcollective.com/property-hub-bat-dong-san/#listings, example listing https://nomadassetcollective.com/property-hub-bat-dong-san/vietnam/nobu-dn/). Scroll feel should match the Property Hub listing PDP. |
| Language | **Bilingual, VI default** (matches brochures). data-vi/data-en attribute pattern. |

---

## 2. What was built (v1)

**File:** `homepage/index.html` (single file, 2029 lines, ~254 data-vi/data-en attrs)
**Branch:** `claude/nac-homepage-redesign-uYSus` in **rayvtt/NAC-Program-Brochures**
**Commit:** `386ad56` — "Add NAC homepage v1: editorial premium redesign"
**Preview URL (GitHub Pages):** `https://rayvtt.github.io/NAC-Program-Brochures/homepage/`

### Section architecture (12 sections, modelled on Property Hub PDP scroll rhythm)

1. **Sticky condensing nav** — mark · 5 links (Brochures · NAC Index · Property Hub · NAC Times · Tools) · VI/EN pill · WhatsApp + Book 30'' CTAs
2. **Hero split** — editorial headline left + animated NAC wireframe globe right + 4 KPI pills (12 Programs · 47 BĐS · 100+ Cases · 50+ iQi Markets) + dual CTA (Get Brochures / Book 30'' with Ray)
3. **Trust strip** — IMC · iQi · RICS · UN PRI · AML/KYC (5-cell row)
4. **§01 Brochures** — all 12 country tiles, 3-col magazine grid with cream-glass NAC score badge top-right, country/program/type meta, hover-arrow CTA. Footer link → brochures gateway.
5. **§02 NAC Residence Index banner** — purple-tinted glass card with embedded purple-hue globe + 12 colour-coded KPI pills (Passport, Tax, Education, Healthcare, Safety, Investment, Speed, Family, Lifestyle, Cost, Citizenship, Business) + 2 CTAs (Explore Index / Compare).
6. **§03 Property Hub** — 3 featured listings: **Nobu Residences Da Nang** (real, links to PDP) + Athens Riviera + Address Residences Downtown Dubai (illustrative). Each card: cover image + Hot/visa badge + circular NAC score + 3 stats (Entry / IRR 5y / Yield) + hover-arrow CTA. Footer link → Property Hub.
7. **§04 NAC Times** — 5 article cards (1 feature card 3/4 ratio + 4 standard 4/5) with category eyebrow chip, magazine-style titles, reading time. 7 category chips below (Tất Cả · So Sánh · Góc Nhìn NAC · Phân Tích · Case Study · Infographic · Cập Nhật).
8. **§05 Process** — full-bleed **navy section**, 5-step horizontal stepper with gold-bordered numbered circles connected by a dashed line. Steps lifted from current homepage (Day 1 → 2-4w Docs → 2-6mo DD → ≤3mo Investment → 4w+ Issuance).
9. **§06 Founder (Ray Vũ)** — cream editorial spread, portrait pane (currently gradient placeholder, IMC Certified Expert ribbon) + copy pane with manifesto pull-quote (italic Cormorant with gold left-border) + 4 credibility badges (IMC · iQi Global · 100+ Cases · 50+ Markets) + dual CTA.
10. **§07 Tools** — 4-card strip (NAC Residence Index · So Sánh · Tư Vấn Nhanh · Property Hub) with tone-coded icon pills (gold/orange/purple/green).
11. **§08 Social proof** — pull-quote in cream-glass card (left) + 6-tile Instagram grid (right) + Follow @nac.global link.
12. **Final CTA band** — navy with gold-gradient headline + 30-min booking copy + Book + WhatsApp CTAs.
13. **Footer** — 4-col: Brand (mark + 5 socials: IG, FB, Threads, TikTok, WhatsApp) · Explore · Reading · Contact (Calendar, +44, +84, email, Sonatus HCM).
14. **Mobile floating CTA pill** — bottom-fixed cream-glass with 4 chips (Tư Vấn 30'' · WhatsApp · Index · So Sánh), mirrors the brochures' `nac-tools` pattern.

### Design DNA inherited from Turkey brochure + brochures gateway

- **Type stack:** Cormorant Garamond (display, italic for emphasis) + Inter (body) + JetBrains Mono (eyebrows/labels)
- **Palette:** cream `#fafaf7` / navy `#0f1a36` / gold `#c4922c` / orange `#d97c44` / purple `#5b3aa8` / green `#1eb955`
- **Texture:** cream-glass pills `rgba(250,245,232,.94)` + `backdrop-filter: blur(22px)` throughout
- **Globe canvas:** wireframe sphere with lat rings + 6 rotating meridians + 14 cities (HCM + Da Nang pulse) + 14 NAC hub arcs. Two instances: navy hue in hero, purple hue in §02. Uses RAF + ResizeObserver init pattern (not setTimeout).
- **Reveal animation:** `.reveal` class + IntersectionObserver (threshold 0.12, `-60px` bottom margin) fades + lifts on scroll.
- **Sticky nav:** transparent on top, condenses with `backdrop-filter` + border + reduced padding after scrollY > 32.

### WordPress safety (baked in for future WP migration)

- All language-toggle bindings use `addEventListener` — no inline `onclick=""` (KSES strips inline handlers)
- All strings inside `<script>` use Unicode curly quotes `"…"` — no `\"` escapes (KSES unescapes them, breaking JS)
- Both `<script>` blocks pass `node --check`
- Verified with: `python3 -c "import re; ..." | node --check -`

---

## 3. Source material I pulled context from

| Source | Why |
|---|---|
| `nomadassetcollective.com` (live audit) | Identified what's strong vs buried |
| `nomadassetcollective.com/brochures/` | Design system reference (gateway tiles) |
| `nomadassetcollective.com/nac-residence-index/` | Globe + 12 KPI + ranking UI |
| `blog.nomadassetcollective.com` | NAC Times categories + editorial card pattern |
| `nomadassetcollective.com/property-hub-bat-dong-san/` | Scroll feel + listings grid pattern |
| `nomadassetcollective.com/property-hub-bat-dong-san/vietnam/nobu-dn/` | Per-listing PDP scroll rhythm (this is the scroll the homepage emulates) |
| `Brochures html/turkey-cbi_8.html` | Master design system (palette, glass pills, globe, bilingual engine) |
| `TURKEY-TEMPLATE.md` | Canonical component inventory |
| `NAC-LINKS.md` | All canonical URLs (booking, WhatsApp, socials, brand assets) |
| `BROCHURE-URLS.md` | Live URLs for all 12 brochures |
| `index.html` (in repo root) | Existing 12-tile grid pattern |

### Canonical URLs used throughout the build

- Booking: `https://calendar.app.google/gnbtNBTBDKuHUasw7`
- WhatsApp: `https://wa.me/447388646000`
- Quick advisor: `https://nomadassetcollective.com/tu-van-nhanh`
- Compare: `https://nomadassetcollective.com/so-sanh`
- NAC Index: `https://nomadassetcollective.com/nac-residence-index/`
- Property Hub: `https://nomadassetcollective.com/property-hub-bat-dong-san/`
- Blog: `https://blog.nomadassetcollective.com`
- Brochures gateway: `https://nomadassetcollective.com/brochures/`
- Logos: `https://nomadassetcollective.com/wp-content/uploads/2026/05/OTG-Passport-Icons-4.png` (colour), `…/OTG-Passport-Icons-1.png` (white)
- Socials: instagram.com/nac.global · facebook.com/profile.php?id=61582793351453 · threads.net/@nac.global · tiktok.com/@nomadassetcollective

---

## 4. Known v1 placeholders / Round 2 punch list

### Replace with real content
- [ ] **Founder portrait** — currently a gradient block. Need Ray's real photo URL (suggest from `nomadassetcollective.com/wp-content/uploads/...`).
- [ ] **NAC scores per brochure tile** — illustrative numbers (74–86). Pull real values from the NAC Residence Index.
- [ ] **Property Hub listings #2 and #3** — Athens & Dubai are illustrative names/photos linking to the hub root. Need real listing URLs from the Property Hub repo.
- [ ] **Testimonial pull-quote** — illustrative. Swap in a real client quote when available.
- [ ] **Brochure cover for Turkey** — currently reuses the Greece-vs-Turkey blog cover; could fetch real og:image for the Turkey brochure page (use `tools/refresh_article_covers.py` pattern).
- [ ] **Trust strip logos** — currently text-only (IMC, iQi, RICS, UN PRI, AML/KYC). Could swap to real logos.

### Polish opportunities
- [ ] Hero photo carousel layered behind/around globe (Mediterranean, Caribbean, Dubai destinations)
- [ ] Number counter animation on hero KPIs (47 ticking up, etc.)
- [ ] Section anchors / smooth-scroll behavior already in place, but add active-section highlight on nav
- [ ] Hamburger menu drawer for mobile (currently the burger button exists but doesn't open anything)
- [ ] Instagram-feed pull from real `@nac.global` (currently uses brochure cover images as placeholders)
- [ ] Process step icons (currently just numbers) — could add subtle SVG icons per step

---

## 5. How to resume in the new session (with NAC-homepage-revamp repo connected)

```bash
# 1. Grab the file from the brochures repo
curl -L -o homepage-index.html \
  https://raw.githubusercontent.com/rayvtt/NAC-Program-Brochures/claude/nac-homepage-redesign-uYSus/homepage/index.html

# 2. Drop it into the NAC-homepage-revamp repo as index.html
mv homepage-index.html index.html

# 3. Commit
git add index.html
git commit -m "Import NAC homepage v1 from brochures repo"
git push -u origin main
```

Or if the new session has both repos available, just `cp` the file across.

### First instructions to give the new session

> Read `HANDOFF.md` and `index.html` in this repo. We're on round 2 of the NAC homepage redesign. v1 is committed; here's the round-2 punch list:
>
> [paste the "Round 2 punch list" from §4]
>
> Start with [pick one — founder portrait / real listings / hero carousel / etc.].

---

## 6. The audit (so you don't have to re-run it)

### What's working on the live nomadassetcollective.com
- Brochures CTA prominent in hero
- Instagram feed integration shows thought leadership
- Process timeline (5 steps) is clear and reassuring
- IMC/iQi/RICS credibility is visible
- Comparison tables for CBI/RBI are well-structured

### What's hurting it (the redesign fixes these)
1. **NAC Residence Index buried as a footer link** despite being the most differentiated proprietary asset → v1 promotes to §02 with full banner + globe + 12 pills
2. **Blog (NAC Times) deemphasized** — no article cards on the page, only category nav → v1 adds §04 with 5 editorial cards + 7 category chips
3. **No case studies / testimonials visible** on main page → v1 adds §08 social-proof pull quote
4. **Main nav hidden behind hamburger** → v1 surfaces 5 primary nav items
5. **Tools (Index, Compare, Quick Advisor) only as text links** → v1 adds §07 tool-card strip with colour-coded icons
6. **Footer has placeholder "Tên Công Ty"** → v1 replaces with real brand mark + sitemap + socials
7. **Single consultant suggests limited capacity** → v1 reframes Ray's section as editorial founder spread (Leo midheaven energy: authoritative manifesto + IMC ribbon + signature CTA)
8. **VI-only may alienate HNW EN audience** → v1 ships fully bilingual with VI default + EN toggle

---

## 7. File structure recap

```
NAC-Program-Brochures/  (this repo)
├── homepage/
│   ├── index.html      ← v1 build (2029 lines, bilingual, single-file)
│   └── HANDOFF.md      ← this file
├── Brochures html/     (reference — Turkey is the master)
├── tools/              (reference — idempotent Python scripts)
├── CLAUDE.md           (reference — design system rules)
├── TURKEY-TEMPLATE.md  (reference — component inventory)
├── NAC-LINKS.md        (reference — canonical URLs)
└── BROCHURE-URLS.md    (reference — all 12 live brochure URLs)
```
