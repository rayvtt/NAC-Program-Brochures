#!/usr/bin/env python3
"""
NAC Brochure Sync — push local HTML files to WordPress via REST API.

Usage:
  python sync_brochures.py                  # show status of all brochures
  python sync_brochures.py turkey           # push one to WP
  python sync_brochures.py --all            # push every brochure
  python sync_brochures.py turkey --dry-run # preview only, no PUT
  python sync_brochures.py overview         # also push the overview page

Setup (one-time):
  1. WP Admin → Users → Profile → "Application Passwords" section
     → name it "NAC Sync" → click "Add New Application Password"
     → copy the 24-char password (with spaces — they're part of the password)
  2. Create .env file next to this script:
       WP_USER=your-wp-username
       WP_APP_PASSWORD=xxxx xxxx xxxx xxxx xxxx xxxx
  3. Test:  python sync_brochures.py turkey --dry-run
  4. Real run:  python sync_brochures.py --all

No third-party deps — uses Python stdlib only.
"""

import os
import sys
import json
import base64
import urllib.request
import urllib.error

# ── Config ─────────────────────────────────────────────────────────────
WP_BASE  = 'https://nomadassetcollective.com/wp-json/wp/v2'
# Imunify360 on the WP host intermittently blanket-blocks GitHub Actions runner IPs (first seen
# 2026-07-06: all 20 pages rejected with "Access denied by Imunify360 bot-protection"). Cloudflare
# Worker egress passes, so on that specific failure we retry once through the nac-marketing-cc
# Worker's /wp-relay (fixed-host, pages-endpoint-only forwarder; auth still enforced by WP itself).
WP_RELAY_BASE = os.environ.get('WP_RELAY_BASE', 'https://nac-marketing-cc.ray-vtt.workers.dev/wp-relay/wp/v2')
def _waf_blocked(status, data):
    blob = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False) if isinstance(data, dict) else str(data)
    return 'Imunify360' in blob or 'being verified' in blob or 'One moment' in blob
# Each brochure page renders an ACF field (the page template echoes this raw).
# We write the full HTML into this field via the WP REST API (ACF must be
# REST-exposed, which it is on nomadassetcollective.com).
ACF_FIELD = 'raw_html_code'
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Brochure HTML files live in this subfolder (reorganised 2026-05-07).
# Tool-pages (NPH, Residence Index) sit in SCRIPT_DIR, so we look in both.
BROCHURE_DIR = os.path.join(SCRIPT_DIR, 'Brochures html')

def resolve_local(fname):
    """Look for fname in Brochures html/ first, then in SCRIPT_DIR."""
    primary = os.path.join(BROCHURE_DIR, fname)
    if os.path.exists(primary):
        return primary
    fallback = os.path.join(SCRIPT_DIR, fname)
    return fallback  # may not exist; caller checks os.path.exists()

# alias → (local filename, WP page id, slug)
BROCHURES = {
    'portugal': ('portugal-gv.html',           1848, 'chuong-trinh-bo-dao-nha-golden-visa'),
    'greece':   ('greece-rbi_1_2.html',        1827, 'residences-chuong-trinh-hy-lap-golden-visa'),
    'cyprus':   ('cyprus-rbi_3_3.html',        1844, 'chuong-trinh-dao-sip-rbi-residence-by-investment'),
    'turkey':   ('turkey-cbi_8.html',          1836, 'chuong-trinh-tho-nhi-ky-cbi-citizenship-by-investment'),
    'uae':      ('uae-rbi_1_7.html',           1901, 'chuong-trinh-uae-golden-visa-2'),
    'uk':       ('uk-rbi_1 (2).html',          1932, 'chuong-trinh-uk-thuong-tru-visa-dau-tu-rbi'),
    'malta':    ('malta-rbi_1_3.html',         1924, 'chuong-trinh-malta-thuong-tru-nhan-rbi'),
    'stkitts':  ('stkitts-nevis.html',         1921, 'chuong-trinh-si-kitts-nevis-quoc-tich'),
    'thailand': ('thailand-rbi_1 (2).html',    1926, 'chuong-trinh-thai-lan-cu-tru-dai-han-ltr-rbi'),
    'overview':    ('NAC-BROCHURES-OVERVIEW.html', 1914, 'brochures'),
    'newzealand':  ('newzealand-rbi_1 (3).html',    1944, 'chuong-trinh-new-zealand-rbi-dau-tu-di-tru'),
    'panama':      ('panama-rbi_.html',             1996, 'chuong-trinh-panama-rbi-quyen-cu-tru-vinh-vien'),
    'malaysia':    ('malaysia-mm2h.html',            2024, 'chuong-trinh-malaysia-rbi-mm2h-dau-tu-quyen-cu-tru'),
    'antigua':     ('antigua-cbi.html',               2158, 'chuong-trinh-antigua-barbuda-cbi'),
    'italy':       ('italy-investor.html',            2165, 'chuong-trinh-y-italy-rbi-qua-dau-tu-bds'),
    'spain':       ('spain-gv.html',                  2170, 'chuong-trinh-tay-ban-nha-golden-visa-qua-dau-tu-bds'),
    'montenegro':  ('montenegro-rbi.html',            2167, 'chuong-trinh-montenengro-rbi-qua-dau-tu-bds'),
    'australia':   ('australia-rbi.html',          2213, 'chuong-trinh-uc-rbi-residency-by-investment'),
    'nauru':       ('nauru-cbi.html',              2215, 'chuong-trinh-nauru-quoc-tich-cbi-citizenship-by-investment'),
    # 'nph' (property-hub) intentionally omitted — managed in the
    # NAC---Property-Hub repo, not here. Re-adding it would overwrite that
    # repo's deploys on every CI run.
    # 'index' re-adopted 2026-07-07: local copy verified byte-identical to the
    # live ACF content first, then KSES-proofed (all static inline on* handlers
    # converted to the data-nac-act delegation binder) so REST pushes can't
    # strip its interactivity. The repo file is the source of truth again.
    'index':       ('NAC-RESIDENCE-INDEX.html',       1800, 'nac-residence-index'),
    # 'partners': gated partner pitch-deck (code-entry gate → 🎯 NAC - Outreach via the
    # command-center Worker's /partner-access).
    'partners':    ('NAC-PARTNERS.html',              2493, 'doi-tac-partner-gateway'),
    # 'quiz': bilingual Quick Quiz (Tư Vấn Nhanh). Page 1115 historically rendered an
    # iframe wrapper around an uploaded static file; syncing here converts it to the
    # ACF raw-html pattern (see PAGE_TEMPLATE below, which switches the WP template).
    'quiz':        ('nac-quiz-tu-van.html',           1115, 'tu-van-nhanh'),
}

# alias → WP page template to enforce on push. Pages listed here did not start life
# on the NAC Residence Index raw-HTML template, so the sync sets `template` in the
# same POST that writes the ACF field (idempotent — WP ignores a no-op value).
PAGE_TEMPLATE = {
    'quiz': 'nac-residence-index.php',
}

# ── Color helpers ──────────────────────────────────────────────────────
def _c(s, code):  return f'\033[{code}m{s}\033[0m' if sys.stdout.isatty() else s
def red(s):    return _c(s, '31')
def green(s):  return _c(s, '32')
def yellow(s): return _c(s, '33')
def blue(s):   return _c(s, '34;1')
def gray(s):   return _c(s, '90')

# ── Auth + HTTP ────────────────────────────────────────────────────────
def load_env():
    # Env vars win (used by CI / GitHub Actions). Fall back to local .env file.
    user = os.environ.get('WP_USER')
    pwd  = os.environ.get('WP_APP_PASSWORD')
    if user and pwd:
        return user, pwd
    env_path = os.path.join(SCRIPT_DIR, '.env')
    if not os.path.exists(env_path):
        sys.exit(red('❌ Missing credentials. Set WP_USER + WP_APP_PASSWORD env vars, or create a .env file. See header of this script for setup.'))
    creds = {}
    with open(env_path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            k, v = line.split('=', 1)
            creds[k.strip()] = v.strip().strip('"').strip("'")
    user = creds.get('WP_USER')
    pwd  = creds.get('WP_APP_PASSWORD')
    if not user or not pwd:
        sys.exit(red('❌ .env must define WP_USER and WP_APP_PASSWORD.'))
    return user, pwd

def auth_header(user, pwd):
    token = base64.b64encode(f'{user}:{pwd}'.encode('utf-8')).decode()
    return f'Basic {token}'

def http(method, url, *, headers=None, body=None):
    req = urllib.request.Request(url, method=method)
    # Browser-like User-Agent. Some bot/WAF layers serve a JS "verify your
    # request" challenge to non-browser clients (the default Python-urllib UA),
    # returning HTTP 200 with a challenge page instead of the REST API JSON —
    # which silently breaks the sync. A real UA slips past UA-based gates.
    req.add_header('User-Agent', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')
    req.add_header('Accept', 'application/json')
    if headers:
        for k, v in headers.items(): req.add_header(k, v)
    data = body.encode('utf-8') if isinstance(body, str) else body
    try:
        with urllib.request.urlopen(req, data=data, timeout=60) as r:
            raw = r.read().decode('utf-8', errors='replace')
            try:    return r.status, json.loads(raw)
            except: return r.status, raw
    except urllib.error.HTTPError as e:
        try:    err = json.loads(e.read().decode('utf-8'))
        except: err = {'message': str(e)}
        return e.code, err
    except Exception as e:
        return 0, {'message': f'connection error: {e}'}

# ── WP operations ──────────────────────────────────────────────────────
def fetch_page_meta(page_id):
    status, data = http('GET', f'{WP_BASE}/pages/{page_id}?_fields=id,slug,modified,title,link')
    if _waf_blocked(status, data):
        status, data = http('GET', f'{WP_RELAY_BASE}/pages/{page_id}?_fields=id,slug,modified,title,link')
    return status, data

def push_page_content(page_id, content, auth, template=None):
    # WP REST runs wp_unslash on the request body: EVERY backslash in the ACF
    # value loses one level (\n -> n, \' -> ', \/ -> /), silently corrupting JS
    # inside <script> blocks (verified live 2026-07-07 on the quiz/index/deck
    # pages). Pre-double all backslashes so the stored value round-trips intact
    # — same fix the Property Hub repo uses in sync-html-to-wordpress.yml.
    # The response's acf field contains the stored (un-slashed) value, so
    # callers keep comparing against the ORIGINAL content.
    payload = {'acf': {ACF_FIELD: content.replace('\\', '\\\\')}}
    if template:
        payload['template'] = template
    body = json.dumps(payload, ensure_ascii=False)
    status, data = http('POST', f'{WP_BASE}/pages/{page_id}',
        headers={'Authorization': auth, 'Content-Type': 'application/json; charset=utf-8'},
        body=body)
    if _waf_blocked(status, data):
        print(yellow('    ⚠ WAF blocked direct push — retrying via Cloudflare relay'))
        status, data = http('POST', f'{WP_RELAY_BASE}/pages/{page_id}',
            headers={'Authorization': auth, 'Content-Type': 'application/json; charset=utf-8', 'x-nac-sync': '1'},
            body=body)
    return status, data

# ── Commands ───────────────────────────────────────────────────────────
def cmd_status():
    print(blue('\nNAC Brochure Sync — status'))
    print(gray('─' * 70))
    print(f'  {"alias":10s}  {"page":>5s}  {"local":>8s}  wp_modified')
    print(gray('─' * 70))
    for alias, (fname, pid, _) in BROCHURES.items():
        local = resolve_local(fname)
        size = (os.path.getsize(local) // 1024) if os.path.exists(local) else None
        size_str = f'{size}KB' if size else red('MISSING')
        if pid == 0:
            wp_mod = yellow('placeholder (id=0)')
        else:
            status, meta = fetch_page_meta(pid)
            wp_mod = meta.get('modified', 'n/a') if status == 200 else red(f'HTTP {status}')
        print(f'  {alias:10s}  {pid:>5d}  {size_str:>8s}  {wp_mod}')
    print(gray('─' * 70))
    print(gray('  push one:    python sync_brochures.py <alias>'))
    print(gray('  push all:    python sync_brochures.py --all'))
    print(gray('  preview:     python sync_brochures.py <alias> --dry-run'))
    print()

def cmd_sync(alias, auth=None, dry_run=False):
    if alias not in BROCHURES:
        print(red(f'  unknown alias: {alias}'))
        return False
    fname, pid, _ = BROCHURES[alias]
    if pid == 0:
        print(yellow(f'  ⤬ {alias}: wp_page_id=0 placeholder — skipping (set real id in BROCHURES dict to enable sync)'))
        return True
    local = resolve_local(fname)
    if not os.path.exists(local):
        print(red(f'  ✗ {alias}: local file missing ({fname})'))
        return False
    with open(local, 'r', encoding='utf-8') as f:
        content = f.read()
    print(f'  {blue(alias):s}  page {pid}  ←  {fname}  ({len(content) // 1024}KB)')
    if dry_run:
        print(gray(f'    (dry-run — no PUT)'))
        return True
    status, data = push_page_content(pid, content, auth, template=PAGE_TEMPLATE.get(alias))
    if status == 200 and isinstance(data, dict) and data.get('id'):
        # Verify ACF round-tripped — catches REST-exposure misconfig or
        # WYSIWYG sanitisers silently stripping the HTML.
        written = (data.get('acf') or {}).get(ACF_FIELD)
        if written is None:
            print(yellow(f'    ⚠ HTTP 200 but acf.{ACF_FIELD} missing from response — verify on live page'))
        elif len(written) != len(content):
            print(yellow(f'    ⚠ HTTP 200 but ACF length differs: sent {len(content)}, got {len(written)} — likely sanitiser stripped content'))
        else:
            print(green(f'    ✓ pushed · modified: {data.get("modified")}'))
        return True
    if not isinstance(data, dict):
        # Non-JSON body on HTTP 200 = a bot/WAF "verify your request" challenge
        # intercepted the REST call. Flag it clearly instead of dumping the HTML.
        blob = str(data)
        if 'being verified' in blob or 'One moment' in blob or '<!DOCTYPE' in blob.lstrip()[:60]:
            print(red(f'    ✗ failed (HTTP {status}) — blocked by bot/WAF challenge page (REST API not reached)'))
        else:
            print(red(f'    ✗ failed (HTTP {status}): {blob[:160]}'))
        return False
    msg = data.get('message')
    code = data.get('code', '')
    print(red(f'    ✗ failed (HTTP {status}) {code}: {msg}'))
    return False

def cmd_sync_all(dry_run=False):
    print(blue('\nNAC Brochure Sync — pushing all brochures'))
    print(gray('─' * 70))
    auth = None if dry_run else auth_header(*load_env())
    ok = fail = 0
    for alias in BROCHURES:
        if cmd_sync(alias, auth=auth, dry_run=dry_run):
            ok += 1
        else:
            fail += 1
    print(gray('─' * 70))
    msg = f'  done — {ok} ok, {fail} failed'
    print((green if fail == 0 else yellow)(msg))
    print()
    return fail


# ── Entry ──────────────────────────────────────────────────────────────
def main():
    args = sys.argv[1:]
    dry_run = '--dry-run' in args
    args = [a for a in args if a != '--dry-run']

    if not args:
        cmd_status()
        return
    target = args[0]
    if target == '--all':
        fail = cmd_sync_all(dry_run=dry_run)
        # Exit non-zero so CI fails loudly instead of masking a total push
        # failure (e.g. every page blocked by a bot/WAF challenge) as success.
        if fail:
            sys.exit(red(f'❌ {fail} page(s) failed to sync — see errors above.'))
    elif target in BROCHURES:
        auth = None if dry_run else auth_header(*load_env())
        ok = cmd_sync(target, auth=auth, dry_run=dry_run)
        print()
        if not ok:
            sys.exit(1)
    else:
        sys.exit(red(f'unknown target: {target}\nvalid: {", ".join(BROCHURES)} | --all'))

if __name__ == '__main__':
    main()
