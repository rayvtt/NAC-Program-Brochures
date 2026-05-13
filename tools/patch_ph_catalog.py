#!/usr/bin/env python3
"""One-off / idempotent patch: inject URL-param filter init into the live
Property Hub catalog (WP page 1999, ACF field `raw_html_code`).

Why: brochure footnote links use ?program=cbi&country=turkey (etc.) to
pre-filter the PH catalog. The catalog is a client-side SPA that does
not currently read URL params. This script injects ~25 lines of JS just
before </body> that maps URL params → filter UI state and triggers
fpApply().

This script is idempotent — if the marker comment is already present in
raw_html_code, no changes are made.

This is a stop-gap while the catalog is NOT versioned in git (it lives
in WP hand-edited). Long-term: version the catalog in the PH repo and
patch via PR there.

Run:
    python tools/patch_ph_catalog.py              # apply
    python tools/patch_ph_catalog.py --dry-run    # preview only
"""
import base64
import json
import os
import sys
import urllib.error
import urllib.request

WP_BASE = 'https://nomadassetcollective.com/wp-json/wp/v2'
PAGE_ID = 1999  # Property Hub catalog
ACF_FIELD = 'raw_html_code'

MARKER = 'BROCHURE_DEEPLINK_INIT_v1'

INIT_SNIPPET = f'''
<script>
/* ============================================================
   {MARKER} — read ?program=&country=&region= from URL, pre-set
   filter UI state, trigger fpApply(). Idempotent: re-running
   patch_ph_catalog.py won't double-inject (keyed off this marker).
   ============================================================ */
(function() {{
  var p = new URLSearchParams(location.search);
  var program = (p.get('program') || '').toLowerCase();
  var country = (p.get('country') || '').toLowerCase();
  var region  = (p.get('region')  || '').toLowerCase();
  if (!program && !country && !region) return;

  function apply() {{
    var dirty = false;
    var progMap = {{ cbi: 'fpCBI', rbi: 'fpRBI', freehold: 'fpFreehold', branded: 'fpBranded', tax: 'fpTax' }};
    if (progMap[program]) {{
      var cb = document.getElementById(progMap[program]);
      if (cb && !cb.checked) {{ cb.checked = true; dirty = true; }}
    }}
    if (region && region !== 'all') {{
      var pill = document.querySelector('.fp-pill[data-region="' + region + '"]');
      if (pill && !pill.classList.contains('active')) {{
        document.querySelectorAll('.fp-pill').forEach(function(b) {{ b.classList.remove('active'); }});
        pill.classList.add('active');
        dirty = true;
      }}
    }}
    if (country) {{
      var sel = document.getElementById('fpCountries');
      if (sel) {{
        for (var i = 0; i < sel.options.length; i++) {{
          var v = (sel.options[i].value || '').toLowerCase();
          var t = (sel.options[i].text  || '').toLowerCase();
          if (v.indexOf(country) !== -1 || t.indexOf(country) !== -1) {{
            sel.selectedIndex = i;
            if (typeof fpCountryChange === 'function') fpCountryChange(sel);
            dirty = true;
            break;
          }}
        }}
      }}
    }}
    if (dirty && typeof fpApply === 'function') fpApply();
  }}

  if (document.readyState === 'loading') {{
    document.addEventListener('DOMContentLoaded', apply);
  }} else {{
    apply();
  }}
}})();
</script>
'''


def http(method, url, *, headers=None, body=None):
    req = urllib.request.Request(url, method=method)
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    data = body.encode('utf-8') if isinstance(body, str) else body
    try:
        with urllib.request.urlopen(req, data=data, timeout=60) as r:
            return r.status, r.read().decode('utf-8', errors='replace')
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8', errors='replace')


def load_creds():
    u, p = os.environ.get('WP_USER'), os.environ.get('WP_APP_PASSWORD')
    if not (u and p):
        sys.exit('❌ Missing WP_USER / WP_APP_PASSWORD env vars.')
    return u, p


def main():
    dry = '--dry-run' in sys.argv

    user, pwd = load_creds()
    auth = 'Basic ' + base64.b64encode(f'{user}:{pwd}'.encode()).decode()

    print(f'GET page {PAGE_ID} from WP…')
    status, body = http('GET', f'{WP_BASE}/pages/{PAGE_ID}?_fields=id,acf,modified')
    if status != 200:
        sys.exit(f'❌ HTTP {status} fetching page: {body[:200]}')
    page = json.loads(body)
    catalog = (page.get('acf') or {}).get(ACF_FIELD) or ''
    if not catalog:
        sys.exit(f'❌ Page {PAGE_ID} acf.{ACF_FIELD} is empty — wrong field name?')
    print(f'  fetched {len(catalog):,} chars (modified {page.get("modified")})')

    if MARKER in catalog:
        print(f'✓ marker "{MARKER}" already present — no-op')
        return

    # Inject before </body>; if missing, append at end.
    if '</body>' in catalog:
        patched = catalog.replace('</body>', INIT_SNIPPET + '\n</body>', 1)
    else:
        patched = catalog + INIT_SNIPPET
    diff = len(patched) - len(catalog)
    print(f'  +{diff:,} chars injected')

    if dry:
        print('--dry-run — not pushing.')
        return

    print(f'POST page {PAGE_ID} back to WP…')
    payload = json.dumps({'acf': {ACF_FIELD: patched}}, ensure_ascii=False)
    status, body = http(
        'POST',
        f'{WP_BASE}/pages/{PAGE_ID}',
        headers={'Authorization': auth, 'Content-Type': 'application/json; charset=utf-8'},
        body=payload,
    )
    if status == 200:
        result = json.loads(body)
        written = (result.get('acf') or {}).get(ACF_FIELD, '')
        if MARKER in written:
            print(f'✓ patched — modified: {result.get("modified")}')
        else:
            print(f'⚠ HTTP 200 but marker not in response — verify on live page')
    else:
        sys.exit(f'❌ HTTP {status} pushing: {body[:300]}')


if __name__ == '__main__':
    main()
