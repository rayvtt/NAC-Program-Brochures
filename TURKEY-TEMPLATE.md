# Turkey Template — Canonical Brochure Reference

> **File:** `Brochures html/turkey-cbi_8.html`
> **Status:** Master template — all 11 other brochures replicate from here.
> **Last refresh:** Q2/2026 — bilingual engine, NAC Index banner, sidebar CTA pill, Google Calendar booking routing, refreshed WhatsApp icon.

This document captures the design system and component inventory that defines Turkey. When replicating to another brochure (Portugal, Greece, Malta, etc.), this is the spec to match.

---

## 1. Bilingual engine (`data-vi` / `data-en`)

### Pattern

Every prose element carries both languages as HTML attributes:

```html
<h2 class="sec-title"
    data-vi="Quy Trình & Thời Gian"
    data-en="Process & Timeline">Quy Trình & Thời Gian</h2>
```

The `setLang(lang)` function (bottom of file) swaps `innerHTML` per the active attribute. If `data-en` is empty, VI text is left in place — graceful fallback during partial migration.

### Coverage on Turkey (~254 attributes)

- Hero title + description + 4 stats
- TOC (mobile + desktop), 10 section eyebrows, 10 titles, 10 subtitles
- Overview cards (9 × label/value/note triplet)
- Tier cards (4 × name/region/tags/badge)
- Timeline (5 × week/title/body)
- Family cards (4 × title/note)
- Tax cards (6 × label/value/note)
- Roadmap (4 steps)
- Compare table (5 columns × 5 rows)
- Pros / Cons lists
- NAC verdict box
- Listings: tagline, location, stat labels, description, CTAs, placeholder
- Article CTAs: kickers, titles, descriptions, button labels
- Footer copy

### HTML attribute escaping

For HTML inside attribute values (links, `<strong>` etc.), escape:
- `<` → `&lt;`
- `>` → `&gt;`
- `"` → `&quot;`
- `&` → `&amp;`

Example: `data-vi="&lt;strong&gt;Nguồn:&lt;/strong&gt; DGMM Thổ Nhĩ Kỳ"`

---

## 2. Chart bilingual (`buildCharts(lang)`)

Chart.js caches axis text into the canvas, so `chart.update()` doesn't reliably refresh labels. The pattern:

```js
const CHART_LBLS = {
  vi: { radarAxes: [...], speedCountries: [...], ... },
  en: { radarAxes: [...], speedCountries: [...], ... }
};
let chartInstances = { radar: null, citizenship: null, compare: null, matrix: null };

function buildCharts(lang) {
  const L = CHART_LBLS[lang] || CHART_LBLS.vi;
  Object.values(chartInstances).forEach(c => { if (c) c.destroy(); });
  chartInstances.radar = new Chart(...);
  chartInstances.citizenship = new Chart(...);
  chartInstances.compare = new Chart(...);
  chartInstances.matrix = new Chart(...);
}
buildCharts('vi');
```

`setLang(lang)` calls `buildCharts(lang)` at the end so country names switch from "Thổ Nhĩ Kỳ / Hy Lạp" → "Türkiye / Greece" cleanly.

### Matrix chart on mobile

The bubble chart uses `aspectRatio: 1` (square) on mobile, `2` on desktop — equal X/Y weighting so the bubbles spread out properly. It's wrapped in `<details id="matrixCollapse" class="chart-collapse" open>`; JS closes the details on mobile load and rebuilds charts when crossing the 600px breakpoint.

---

## 3. Article CTA banner card

Magazine-style card with cover image:

```html
<div class="article-cta">
  <a class="article-cta-banner" href="<article-url>" target="_blank"
     style="background-image:url('<cover-url>')">
    <span class="article-cta-kicker" data-vi="..." data-en="...">...</span>
    <h3 class="article-cta-title" data-vi="..." data-en="...">...</h3>
  </a>
  <div class="article-cta-body">
    <p class="article-cta-desc" data-vi="..." data-en="...">...</p>
    <a class="article-cta-btn" href="<article-url>" target="_blank"
       data-vi="Đọc Ngay →" data-en="Read Now →">Đọc Ngay →</a>
  </div>
</div>
```

CSS: dark gradient overlay + Playfair Display title, hover lifts card.

**Cover image** is auto-pulled from each article's `og:image` meta tag via `tools/refresh_article_covers.py`. Run whenever you publish a new article or refresh covers.

---

## 4. NAC Residence Index banner (§07)

Replaces the comparison-tool CTA with a magazine card linking to `nomadassetcollective.com/nac-residence-index/`.

### Surface
- Background: `linear-gradient(135deg, #f0eeff 0%, #f8f7ff 50%, #eef3ff 100%)` — mirrors NAC Index hero
- Dark text (kicker `#5b3aa8`, title `#1a0f5c`) with white text-shadow

### Animated globe (canvas)
Lifted verbatim from the NAC Residence Index source. Lives in a `~340-line` IIFE near the bottom of the file. Features:
- Rotating wireframe sphere with lat rings + meridians
- 27 city dots colour-coded by region (orange/purple/green/indigo)
- 14 NAC arc paths between hubs
- Tiny airplanes flying along arcs with fading dashed trails
- Pulsing HCM City dot

### Init reliability
Uses RAF retry loop instead of `setTimeout`:

```js
function init(){
  resize();
  if (W === 0 || H === 0) { requestAnimationFrame(init); return; }
  animate();
}
if (typeof ResizeObserver !== 'undefined') {
  new ResizeObserver(() => resize()).observe(canvas);
}
requestAnimationFrame(init);
```

### 12 KPI icon pills

Below the title, left half of banner, **desktop only**:

```html
<div class="nac-index-pills">
  <span class="nac-pill" style="color:#1800ad" title="Passport"><svg>…</svg></span>
  <span class="nac-pill" style="color:#16a34a" title="Tax"><svg>…</svg></span>
  ... 10 more ...
</div>
```

Each pill: 30×30, white-glass background, hover lifts. Icons lifted from the NAC Index hero (passport, tax, education, healthcare, safety, investment, speed, family, lifestyle, cost, citizenship, business).

### Mobile
- Pills hidden inside the banner (a separate mobile pill strip sits on the white body strip below)
- Description paragraph hidden
- Banner uses **CSS Grid** (`display: grid; grid-template-rows: 240px auto auto`) so the globe gets its own deterministic 240px slot at the top and the kicker + title flow below in their own rows — no overlap, no clipping, regardless of viewport quirks
- Globe canvas is **240×240** on mobile (was 300px until v2; downsized to hug the banner more tightly per design feedback)
- `.nac-index-banner::after { display: none; }` on mobile — the gradient overlay was visual noise on top of the stacked layout

```css
@media (max-width: 600px) {
  .nac-index-banner {
    display: grid !important;
    grid-template-rows: 240px auto auto;
    padding: 0 !important;
  }
  .nac-index-globe {
    position: relative !important;
    grid-row: 1;
    width: 240px !important;
    height: 240px !important;
    transform: none !important;
    margin: 0 auto;
  }
  .nac-index-banner .article-cta-kicker { grid-row: 2; margin-top: -8px; }
  .nac-index-banner .article-cta-title  { grid-row: 3; margin-bottom: 14px; }
}
```

---

## 5. Sidebar CTA pill (under Mục Lục)

Cream-glass refined pill mirroring the mobile `.nac-tools` floating bar:

```html
<div class="toc-cta-mini">
  <a class="tc-cal" href="https://calendar.app.google/gnbtNBTBDKuHUasw7"><svg>…</svg> Tư Vấn 30''</a>
  <a class="tc-wa"  href="https://wa.me/447388646000"><svg>…</svg> WhatsApp</a>
  <a class="tc-idx" href="https://nomadassetcollective.com/nac-residence-index/"><svg>…</svg> NAC Index</a>
  <a class="tc-cmp" href="https://nomadassetcollective.com/so-sanh/"><svg>…</svg> So Sánh</a>
</div>
```

### Colour palette

| Chip | Class | Colour | Target |
|---|---|---|---|
| Tư Vấn 30" | `tc-cal` | `#5b3aa8` (purple) | Google Calendar |
| WhatsApp | `tc-wa` | `#1eb955` (brand green) | `wa.me/447388646000` |
| NAC Index | `tc-idx` | `#c4922c` (amber) | NAC Residence Index |
| So Sánh | `tc-cmp` | `#d97c44` (orange) | so-sanh tool |

Container: `rgba(250,245,232,.94)` + `backdrop-filter: blur(22px)`.

---

## 6. CTA URL routing

### Header pill
```html
<a href="https://calendar.app.google/gnbtNBTBDKuHUasw7" target="_blank">📅 Tư Vấn Miễn Phí</a>
<a href="https://wa.me/447388646000" target="_blank" style="…green pill SVG…">WhatsApp</a>
```

The 💬 emoji is replaced by the proper WhatsApp brand SVG icon, brand green `#25D366` background, white fill.

### NAC consultation footer (dark CTA block)
- "Đặt Lịch Tư Vấn Miễn Phí" → `https://calendar.app.google/gnbtNBTBDKuHUasw7`
- WhatsApp icon next to it: `.nac-btn-wa` box stays dark transparent; SVG `fill: #25D366` (brand green)

### Booking funnel rule

| CTA context | Target URL |
|---|---|
| Header pill (📅 Tư Vấn Miễn Phí) | Google Calendar |
| Footer "Book a Free Consultation" / Đặt Lịch | Google Calendar |
| In-section CTAs (`Tư Vấn Ngay`, `Tư Vấn Chiến Lược`, `Tư Vấn BĐS`) | `nomadassetcollective.com/tu-van-nhanh/` |
| Calendly old URLs | Migrated → Google Calendar |

Body / mid-section soft-funnel CTAs stay on `tu-van-nhanh/`. Only the "primary booking" surfaces (header + footer) route to Google Calendar.

---

## 7. Listings spotlight (§ between 02 and 03)

`<section class="section section-spotlight" id="listings">` with `.listings-grid` of `.listing-card` items. Every prose element bilingual:

- `.listing-tagline`
- `.listing-name` (proper noun, no translation)
- `.listing-location` (📍 + city/region)
- `.listing-badge.listing-badge-eligible`
- `.listing-stat-lbl` × 4
- `.listing-desc`
- `.listing-cta-primary`
- `.listing-placeholder-title` / `.listing-placeholder-sub` / `.listing-placeholder-link`
- `.listings-fn-text` / `.listings-fn-link`

Live data comes from the Property Hub Worker; placeholder card for "Coming Soon".

---

## 8. Reusable tooling

All scripts in `tools/` are **idempotent** — safe to re-run.

| Script | Purpose |
|---|---|
| `tools/refresh_article_covers.py` | Pulls article CTA cover from each linked article's `og:image` meta tag |
| `tools/rewire_cta_links.py` | Calendly→Google migration + header pill→Google + WhatsApp 💬 emoji→SVG green pill |
| `tools/refine_sidebar_cta.py` | Cream-glass sidebar CTA pill with 4 colour-coded chips |
| `tools/refine_nac_btn.py` | NAC consultation footer Book→Google + WhatsApp icon → brand green |

### Run order (cold replication on a new brochure)

```bash
# Apply to a single brochure (e.g. portugal)
python tools/rewire_cta_links.py portugal
python tools/refine_sidebar_cta.py portugal
python tools/refine_nac_btn.py portugal
python tools/refresh_article_covers.py portugal
```

Or `--all` for every brochure at once (default no-arg behaviour). Each script reports counts; second run prints `0` if nothing changed.

---

## 9. Component checklist

For a brochure to be "at Turkey parity", verify:

- [ ] Bilingual: every prose element has `data-vi` AND `data-en` attributes
- [ ] Charts use `buildCharts(lang)` with VI/EN dictionaries; `setLang` calls it
- [ ] Matrix chart has `aspectRatio` swap for mobile
- [ ] Article CTAs use cover-banner card structure (not text-only)
- [ ] Article covers point at real `og:image`, not placeholder URLs
- [ ] §07 has NAC Index banner with embedded canvas globe + 12 KPI pills
- [ ] Sidebar CTA pill (cream-glass, 4 colour-coded chips) under Mục Lục
- [ ] Header pill: 💬 emoji replaced with green WhatsApp SVG; 📅 Tư Vấn Miễn Phí → Google Calendar
- [ ] NAC consultation footer: "Book" CTA → Google Calendar; WhatsApp icon brand green
- [ ] Mobile: matrix collapsible, globe centred, KPI pills hidden, article description hidden
- [ ] Globe init uses RAF + ResizeObserver (not `setTimeout`)

---

## 10. File-level layout reference

```
Brochures html/turkey-cbi_8.html
├── <head> — Open Graph, JSON-LD, fonts, Chart.js CDN
├── <style> — design tokens (--country), layout, components, paywall, mobile CTA
├── <body>
│   ├── <nav> — sticky top nav with logo, links, header pill
│   ├── <section class="hero"> — hero with bilingual title + stats
│   ├── <div class="main"> — sidebar TOC + content grid
│   │   ├── <aside class="toc"> — Mục Lục + sidebar CTA pill
│   │   └── <div class="content">
│   │       ├── §01 overview
│   │       ├── §02 investment
│   │       ├── #listings spotlight
│   │       ├── §03 process
│   │       ├── PAYWALL ZONE WRAPPER
│   │       ├── §04 family ─┐
│   │       ├── §05 tax     │
│   │       ├── §06 citizenship │ blurred until [Có]
│   │       ├── §07 compare ── NAC Index banner with globe
│   │       ├── §08 proscons │
│   │       └── §09 nac     ─┘
│   ├── <footer>
│   ├── <div class="nac-tools"> — mobile floating CTA pill (bottom-center)
│   ├── <script> — Chart.js + buildCharts + matrix collapse
│   ├── <script> — floating TOC + mobile CTA tooltips
│   ├── <script> — NAC Index globe IIFE
│   └── <script> — bilingual engine + paywall handler
```

---

## 11. WordPress gotchas (live page only — preview is fine)

WP's sanitiser silently mangles inline JS in two ways. Both bit us during EN-toggle rollout; document them so they don't bite again.

### Inline `onclick=""` attributes get stripped

WordPress KSES strips inline event handlers when content is saved to ACF `raw_html_code` for XSS protection. Buttons that rely on `onclick="setLang('en')"` will appear in the HTML but the attribute is gone on live.

**Fix:** bind via `addEventListener` instead of (or in addition to) inline `onclick`. See the IIFE at the bottom of the bilingual engine script in `turkey-cbi_8.html`.

### Backslash-escaped quotes inside JS strings get unescaped

WP rewrites `\"foo\"` → `"foo"` inside `<script>` content. This breaks every string literal that contains an escaped quote. The bilingual engine's `VI_STRINGS` / `EN_STRINGS` arrays both hit this with `\"bàn đạp\"` and `\"springboard\"` — making the entire script a syntax error on live, so `setLang` is never defined and the EN toggle dies silently.

**Fix:** use Unicode curly quotes `“…”` (U+201C / U+201D) inside JS strings instead of `\"…\"`. They're typographically identical for users and survive WP intact.

**Never use** `\"` inside `<script>` content destined for WP. If you need literal straight quotes, use:
- `"` (Unicode escape — also survives WP), or
- swap outer string to single quotes: `'he said "hi"'`

### Verification recipe

```bash
# After sync, fetch the live page and run JS through node:
curl -s "<live-url>" > /tmp/live.html
python3 -c "import re; html=open('/tmp/live.html').read(); print(re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)[4])" \
  | node --check -
# If you get a SyntaxError, WP has mangled something — diff the live script #4 against the local file.
```

---

## 12. Open follow-ups

Not yet rolled out from Turkey to the other 11:
- Bilingual data-vi/data-en migration (sections 01-09 + listings)
- NAC Index banner with canvas globe in §07
- Sidebar CTA pill design
- Matrix chart square-on-mobile fix
- 12 KPI icon pills on the NAC Index banner

The sidebar CTA pill, header pill rewiring, WhatsApp icon green, and footer Book CTA → Google **have** been propagated to all 12 (via the four `tools/` scripts).

For the remaining items, ping me with "replicate Turkey § to <brochure>" and I'll run the equivalent work on the target file.
