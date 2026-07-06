# NAC Program Brochures — Live URLs

URL pattern: `https://nomadassetcollective.com/brochures/<slug>/` — each brochure is a child page of the `brochures` parent page (which is the `NAC-BROCHURES-OVERVIEW.html` gateway).

## Program brochures (PDP)

| Country | Alias | Page ID | Live URL |
|---|---|---|---|
| 🇵🇹 Portugal | `portugal` | 1848 | https://nomadassetcollective.com/brochures/chuong-trinh-bo-dao-nha-golden-visa/ |
| 🇬🇷 Greece | `greece` | 1827 | https://nomadassetcollective.com/brochures/residences-chuong-trinh-hy-lap-golden-visa/ |
| 🇨🇾 Cyprus | `cyprus` | 1844 | https://nomadassetcollective.com/brochures/chuong-trinh-dao-sip-rbi-residence-by-investment/ |
| 🇹🇷 Turkey | `turkey` | 1836 | https://nomadassetcollective.com/brochures/chuong-trinh-tho-nhi-ky-cbi-citizenship-by-investment/ |
| 🇦🇪 United Arab Emirates | `uae` | 1901 | https://nomadassetcollective.com/brochures/chuong-trinh-uae-golden-visa-2/ |
| 🇬🇧 United Kingdom | `uk` | 1932 | https://nomadassetcollective.com/brochures/chuong-trinh-uk-thuong-tru-visa-dau-tu-rbi/ |
| 🇲🇹 Malta | `malta` | 1924 | https://nomadassetcollective.com/brochures/chuong-trinh-malta-thuong-tru-nhan-rbi/ |
| 🇰🇳 St Kitts & Nevis | `stkitts` | 1921 | https://nomadassetcollective.com/brochures/chuong-trinh-si-kitts-nevis-quoc-tich/ |
| 🇹🇭 Thailand | `thailand` | 1926 | https://nomadassetcollective.com/brochures/chuong-trinh-thai-lan-cu-tru-dai-han-ltr-rbi/ |
| 🇳🇿 New Zealand | `newzealand` | 1944 | https://nomadassetcollective.com/brochures/chuong-trinh-new-zealand-rbi-dau-tu-di-tru/ |
| 🇵🇦 Panama | `panama` | 1996 | https://nomadassetcollective.com/brochures/chuong-trinh-panama-rbi-quyen-cu-tru-vinh-vien/ |
| 🇲🇾 Malaysia | `malaysia` | 2024 | https://nomadassetcollective.com/brochures/chuong-trinh-malaysia-rbi-mm2h-dau-tu-quyen-cu-tru/ |
| 🇦🇬 Antigua & Barbuda | `antigua` | 2158 | https://nomadassetcollective.com/brochures/chuong-trinh-antigua-barbuda-cbi/ |
| 🇮🇹 Italy | `italy` | 2165 | https://nomadassetcollective.com/brochures/chuong-trinh-y-italy-rbi-qua-dau-tu-bds/ |
| 🇪🇸 Spain (Golden Visa, closed 03/04/2025) | `spain` | 2170 | https://nomadassetcollective.com/brochures/chuong-trinh-tay-ban-nha-golden-visa-qua-dau-tu-bds/ |
| 🇲🇪 Montenegro | `montenegro` | 2167 | https://nomadassetcollective.com/brochures/chuong-trinh-montenengro-rbi-qua-dau-tu-bds/ |
| 🇦🇺 Australia | `australia` | 2213 | https://nomadassetcollective.com/brochures/chuong-trinh-uc-rbi-residency-by-investment/ |
| 🇳🇷 Nauru | `nauru` | 2215 | https://nomadassetcollective.com/brochures/chuong-trinh-nauru-quoc-tich-cbi-citizenship-by-investment/ |

## Gateway page (synced by this repo)

| Page | Alias | Page ID | Live URL |
|---|---|---|---|
| Brochures overview (funnel entry, parent of all country brochures) | `overview` | 1914 | https://nomadassetcollective.com/brochures/ |

## Partner pitch-deck (synced by this repo — pending a live page id)

| Page | Alias | Page ID | Live URL |
|---|---|---|---|
| NAC Partners — gated pitch deck for referral partners (code-entry gate, tracked in 🎯 NAC - Outreach) | `partners` | 0 (placeholder — create the WP page and set the real id in `sync_brochures.py`) | https://nomadassetcollective.com/brochures/doi-tac-partner-gateway/ (once live) |

Local source: `Brochures html/NAC-PARTNERS.html`. The gate posts to the `nac-marketing-omnichannel` command-center Worker (`POST https://nac-marketing-cc.ray-vtt.workers.dev/partner-access`), which checks the code against each prospect's "Partner Access Code" in the 🎯 NAC - Outreach Notion DB and logs the open (Access Opens / Last Access / Stage → "👀 Opened"). Assign/regenerate a partner's code from the Command Center cockpit → Outreach → open the prospect → 🔑 Generate code.

## NOT synced by this repo (hand-managed in WP)

| Page | Live URL |
|---|---|
| Residence comparison index | https://nomadassetcollective.com/nac-residence-index/ |
| Property hub *(lives in `nac---property-hub---listing-pdp` repo)* | https://nomadassetcollective.com/property-hub/ |

---

## How HTML reaches these pages

The page template renders the **ACF field `raw_html_code`** on each page — NOT the WordPress `content` field. The sync script (`sync_brochures.py`) pushes HTML into that ACF field via the REST API on push to `main` (see `WP-SYNC-SETUP.md`).

If a slug changes in WP, update the third tuple element in `sync_brochures.py` → `BROCHURES` for that alias. Page IDs are what actually drive the sync — the slugs here are just for human reference.
