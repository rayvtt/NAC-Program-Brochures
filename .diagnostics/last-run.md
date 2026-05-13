# WP Sync run — 2026-05-13T19:39:36Z

- Trigger: `push` on `refs/heads/main`
- Commit: `9a44d0e9c00ec8c8d620617147a90a483c1fd31b`
- Run: <https://github.com/rayvtt/NAC-Program-Brochures/actions/runs/25822109934>

## Pull from Notion
```
Querying 35f48ec25e8680f69c3dc5ad538e7ca8…
  fetched 1 rows
    hero_badge_vi: '🔥Quốc Tịch Đầu Tư · CBI · Nhanh Nhất Khu Vực ///updates'
  + Turkey       (new)

Summary: 1 written, 0 unchanged, 0 updated (existing).
```

## Build brochures
```
  ✓ portugal     → build/portugal-gv.html
  ✓ greece       → build/greece-rbi_1_2.html
  ✓ cyprus       → build/cyprus-rbi_3_3.html
  ✓ turkey       → build/turkey-cbi_8.html
  ✓ uae          → build/uae-rbi_1_7.html
  ✓ uk           → build/uk-rbi_1 (2).html
  ✓ malta        → build/malta-rbi_1_3.html
  ✓ stkitts      → build/stkitts-nevis.html
  ✓ thailand     → build/thailand-rbi_1 (2).html
  ✓ newzealand   → build/newzealand-rbi_1 (3).html
  ✓ panama       → build/panama-rbi_.html
  ✓ malaysia     → build/malaysia-mm2h.html
```

## Refresh listings spotlight
```
Fetching live properties from worker…
  got 22 live properties
  ✓ portugal     updated
  ✓ greece       updated
  ✓ cyprus       updated
  – turkey       no changes
  ✓ uae          updated
  ✓ uk           updated
  ✓ malta        updated
  ✓ stkitts      updated
  ✓ thailand     updated
  ✓ newzealand   updated
  ✓ panama       updated
  ✓ malaysia     updated

11 brochure(s) updated.
```

## Sync to WP
```
Trigger: push on refs/heads/main
Running: python sync_brochures.py --all 

NAC Brochure Sync — pushing all brochures
──────────────────────────────────────────────────────────────────────
  portugal  page 1848  ←  portugal-gv.html  (148KB)
    ⚠ HTTP 200 but ACF length differs: sent 152442, got 152431 — likely sanitiser stripped content
  greece  page 1827  ←  greece-rbi_1_2.html  (154KB)
    ⚠ HTTP 200 but ACF length differs: sent 158129, got 158118 — likely sanitiser stripped content
  cyprus  page 1844  ←  cyprus-rbi_3_3.html  (149KB)
    ⚠ HTTP 200 but ACF length differs: sent 152704, got 152693 — likely sanitiser stripped content
  turkey  page 1836  ←  turkey-cbi_8.html  (153KB)
    ⚠ HTTP 200 but ACF length differs: sent 157587, got 157576 — likely sanitiser stripped content
  uae  page 1901  ←  uae-rbi_1_7.html  (152KB)
    ⚠ HTTP 200 but ACF length differs: sent 156174, got 156163 — likely sanitiser stripped content
  uk  page 1932  ←  uk-rbi_1 (2).html  (151KB)
    ⚠ HTTP 200 but ACF length differs: sent 155384, got 155373 — likely sanitiser stripped content
  malta  page 1924  ←  malta-rbi_1_3.html  (151KB)
    ⚠ HTTP 200 but ACF length differs: sent 155643, got 155632 — likely sanitiser stripped content
  stkitts  page 1921  ←  stkitts-nevis.html  (152KB)
    ⚠ HTTP 200 but ACF length differs: sent 156397, got 156386 — likely sanitiser stripped content
  thailand  page 1926  ←  thailand-rbi_1 (2).html  (153KB)
    ⚠ HTTP 200 but ACF length differs: sent 156719, got 156708 — likely sanitiser stripped content
  overview  page 1914  ←  NAC-BROCHURES-OVERVIEW.html  (200KB)
    ⚠ HTTP 200 but ACF length differs: sent 205394, got 205387 — likely sanitiser stripped content
  newzealand  page 1944  ←  newzealand-rbi_1 (3).html  (150KB)
    ⚠ HTTP 200 but ACF length differs: sent 154399, got 154388 — likely sanitiser stripped content
  panama  page 1996  ←  panama-rbi_.html  (152KB)
    ⚠ HTTP 200 but ACF length differs: sent 155808, got 155797 — likely sanitiser stripped content
  ✗ nph: local file missing (NAC-PROPERTY-HUB.html)
  index  page 1800  ←  NAC-RESIDENCE-INDEX.html  (184KB)
    ⚠ HTTP 200 but ACF length differs: sent 188777, got 188459 — likely sanitiser stripped content
  malaysia  page 2024  ←  malaysia-mm2h.html  (151KB)
    ⚠ HTTP 200 but ACF length differs: sent 155062, got 155051 — likely sanitiser stripped content
──────────────────────────────────────────────────────────────────────
  done — 14 ok, 1 failed

```

