#!/usr/bin/env python3
"""Render the Live Listings spotlight section into every brochure.

Architecture:
  1. Fetch all live properties from the Property Hub worker:
       https://nac-property-hub.ray-vtt.workers.dev/properties
     (single GET — returns JSON array of all Hub Status="Live" rows from
     the [NAC - Property Listings] Notion DB).
  2. For each brochure: filter by country, sort by `entry` (price $K),
     apply Rule 1 (cheapest + priciest when > 2 candidates) and Rule 2
     (biweekly rotation biased to different hubType).
  3. For each selected listing (1-2 max): fetch its PDP page once to
     pull richer detail (data-notion="desc_vi", district, handover —
     not exposed by the worker endpoint).
  4. Render cards. Empty slots get a "Đang Cập Nhật" placeholder.

Run:
    python tools/apply_listings.py            # all brochures
    python tools/apply_listings.py turkey     # one
    python tools/apply_listings.py --offline  # placeholders only, no fetch

In CI: runs before sync_brochures.py so every deploy reflects the
current Notion data.

No third-party deps — Python stdlib only.
"""
import datetime
import html as html_lib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from data.listings import COUNTRIES  # noqa: E402

BROCHURE_DIR = ROOT / 'Brochures html'

WORKER_PROPERTIES_URL = 'https://nac-property-hub.ray-vtt.workers.dev/properties'

ALIAS_FILE = {
    'portugal':   'portugal-gv.html',
    'greece':     'greece-rbi_1_2.html',
    'cyprus':     'cyprus-rbi_3_3.html',
    'turkey':     'turkey-cbi_8.html',
    'uae':        'uae-rbi_1_7.html',
    'uk':         'uk-rbi_1 (2).html',
    'malta':      'malta-rbi_1_3.html',
    'stkitts':    'stkitts-nevis.html',
    'thailand':   'thailand-rbi_1 (2).html',
    'newzealand': 'newzealand-rbi_1 (3).html',
    'panama':     'panama-rbi_.html',
    'malaysia':   'malaysia-mm2h.html',
    'antigua':    'antigua-cbi.html',
    'italy':      'italy-investor.html',
    'spain':      'spain-gv.html',
    'montenegro': 'montenegro-rbi.html',
}

DATA_NOTION_RE = re.compile(r'data-notion="([\w_]+)"[^>]*>(.*?)</[a-zA-Z]', re.DOTALL)
HERO_BG_RE = re.compile(r'class="nac-hero-img"[^>]*background-image:url\([\'"]([^\'"]+)[\'"]')
HANDOVER_RE = re.compile(
    r'Bàn Giao</span>(?:<span data-en="">[^<]*</span>)?</span>'
    r'<span class="nac-fact-val">([^<]+)</span>'
)


# ── HTTP helpers ────────────────────────────────────────────────────────
def http_get(url, timeout=20):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'NAC-apply-listings/1.0'})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode('utf-8', errors='replace'), None
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
        return None, f'fetch failed: {e}'


def fetch_all_properties():
    doc, err = http_get(WORKER_PROPERTIES_URL)
    if err:
        print(f'! worker fetch failed: {err}', file=sys.stderr)
        return []
    try:
        return json.loads(doc)
    except ValueError as e:
        print(f'! worker returned non-JSON: {e}', file=sys.stderr)
        return []


def fetch_pdp_details(url):
    """Parse data-notion fields + hero img + handover from a PDP page."""
    doc, err = http_get(url)
    if err:
        print(f'    ! PDP fetch failed: {url} → {err}', file=sys.stderr)
        return {}
    fields = {m.group(1): m.group(2).strip() for m in DATA_NOTION_RE.finditer(doc)}
    hero_m = HERO_BG_RE.search(doc)
    if hero_m:
        fields['hero_img'] = hero_m.group(1)
    handover_m = HANDOVER_RE.search(doc)
    if handover_m:
        fields['handover'] = handover_m.group(1).replace(' (estimated)', '').strip()
    return fields


# ── Helpers ─────────────────────────────────────────────────────────────
def short_name(full):
    return re.split(r'\s+[—\-–]\s+', full, maxsplit=1)[0].strip()


def first_sentence(text, max_len=240):
    if not text:
        return ''
    period = text.find('. ')
    if 0 < period <= max_len:
        return text[: period + 1]
    if len(text) <= max_len:
        return text
    return text[:max_len].rsplit(' ', 1)[0] + '…'


def fortnight_index(today=None):
    today = today or datetime.date.today()
    iso_year, iso_week, _ = today.isocalendar()
    return iso_year * 26 + (iso_week // 2)


def country_matches(prop_country, notion_country):
    """Match prop's '🇹🇷 Thổ Nhĩ Kỳ' against config value(s)."""
    needles = notion_country if isinstance(notion_country, list) else [notion_country]
    return any(n in prop_country for n in needles)


def extract_flag(prop_country):
    """Pull the emoji flag from a '🇹🇷 Thổ Nhĩ Kỳ' style string."""
    m = re.match(r'(\S+)\s+', prop_country or '')
    return m.group(1) if m else ''


def ph_catalog_url(program_code, country_alias):
    return (
        'https://nomadassetcollective.com/property-hub/'
        f'?program={program_code.lower()}&country={country_alias}'
    )


# ── Selection (Rule 1 + Rule 2) ─────────────────────────────────────────
def select_pair(candidates, fortnight=None):
    """Apply Rule 1 (cheapest+priciest) + Rule 2 (biweekly rotation).

    ≤ 2 candidates → return them all.
    > 2 candidates → card 1 = cheapest (anchor); card 2 = rotated from
        the rest, biased toward a different hubType than card 1.
    """
    if len(candidates) <= 2:
        return candidates
    by_price = sorted(candidates, key=lambda p: p.get('entry') or 0)
    cheapest = by_price[0]
    rest = by_price[1:]
    diff_type = [p for p in rest if p.get('hubType') and p.get('hubType') != cheapest.get('hubType')]
    pool = diff_type or rest
    fortnight = fortnight if fortnight is not None else fortnight_index()
    card2 = pool[fortnight % len(pool)]
    return [cheapest, card2]


# ── Render ──────────────────────────────────────────────────────────────
def render_card(prop, pdp, country_cfg):
    program_code = country_cfg['program_code']
    flag = extract_flag(prop.get('country', ''))
    e = html_lib.escape

    # Name — prefer PDP's canonical Notion name, fall back to worker.
    name = short_name(pdp.get('property_name_vi') or prop.get('name_vi') or '')

    # Description — PDP desc_vi (rich, investment-specific) > worker excerpt_vi.
    desc = first_sentence(pdp.get('desc_vi') or prop.get('excerpt_vi') or '')

    # Tagline (small kicker) — PDP tagline_vi; falls back to hubType.
    tagline = pdp.get('tagline_vi') or prop.get('hubType', '')

    # Location — PDP district (e.g. "Şişli / Levent") + worker country.
    district = pdp.get('district', '').strip()
    country_clean = re.sub(r'^\S+\s+', '', prop.get('country', '')).strip()  # strip flag
    location_parts = [p for p in [district, country_clean] if p]

    # Stats — prefer PDP price_full (e.g. "$572,300"); fall back to worker entry × 1000.
    # Currency normalisation: per-country currency from data/listings.py — if the PDP price
    # came in with $ but the country uses € (EU programs), swap the symbol so Malta/Cyprus/
    # Portugal/Greece show € not $. PDP-side data entry is the canonical fix; this is a
    # safety net while listings are still in mixed currencies.
    currency = country_cfg.get('currency', '$')
    price_raw = pdp.get('price_full') or (f"{currency}{prop['entry']}K" if prop.get('entry') else '—')
    if currency != '$' and price_raw and price_raw != '—':
        price_raw = price_raw.replace('$', currency)
    price = price_raw
    y = pdp.get('yield_pct_unit') or (f"{prop['netYield']:.1f}%" if prop.get('netYield') else '—')
    irr = pdp.get('irr_pct_unit') or (f"{prop['irr']:.1f}%" if prop.get('irr') else '—')
    handover = pdp.get('handover') or '—'

    src_url = prop.get('listingUrl', '')
    ref = pdp.get('property_id') or (f'NAC-{prop["id"]}' if prop.get('id') else '')
    hero = pdp.get('hero_img') or prop.get('img', '')
    badge_loc = district or country_clean

    return (
        '        <article class="listing-card">\n'
        f'          <a class="listing-card-link" href="{e(src_url)}" target="_blank" rel="noopener">\n'
        '            <div class="listing-hero">\n'
        f'              <img src="{e(hero)}" alt="{e(name)}" loading="lazy">\n'
        '              <div class="listing-badges">\n'
        f'                <span class="listing-badge listing-badge-flag">{flag} {e(badge_loc)}</span>\n'
        f'                <span class="listing-badge listing-badge-eligible">✓ Đủ điều kiện {program_code}</span>\n'
        '              </div>\n'
        f'              <div class="listing-ref">{e(ref)}</div>\n'
        '            </div>\n'
        '            <div class="listing-body">\n'
        f'              <div class="listing-tagline">{e(tagline)}</div>\n'
        f'              <h3 class="listing-name">{e(name)}</h3>\n'
        f'              <div class="listing-location">📍 {e(" · ".join(location_parts))}</div>\n'
        '              <div class="listing-stats">\n'
        f'                <div class="listing-stat"><div class="listing-stat-val">{e(price)}</div><div class="listing-stat-lbl">Giá Khởi Điểm</div></div>\n'
        f'                <div class="listing-stat"><div class="listing-stat-val">{e(y)}</div><div class="listing-stat-lbl">Gross Yield</div></div>\n'
        f'                <div class="listing-stat"><div class="listing-stat-val">{e(irr)}</div><div class="listing-stat-lbl">5-Year IRR</div></div>\n'
        f'                <div class="listing-stat"><div class="listing-stat-val">{e(handover)}</div><div class="listing-stat-lbl">Bàn Giao</div></div>\n'
        '              </div>\n'
        f'              <p class="listing-desc">{e(desc)}</p>\n'
        '              <div class="listing-cta-row">\n'
        '                <span class="listing-cta-primary">Xem Chi Tiết →</span>\n'
        '              </div>\n'
        '            </div>\n'
        '          </a>\n'
        '        </article>'
    )


def render_placeholder(country_vi, program_code, catalog_url):
    return (
        '        <article class="listing-card listing-card-placeholder">\n'
        '          <div class="listing-placeholder-content">\n'
        '            <div class="listing-placeholder-icon">+</div>\n'
        '            <div class="listing-placeholder-title">Đang Cập Nhật</div>\n'
        f'            <div class="listing-placeholder-sub">Thêm BĐS {country_vi} đủ điều kiện {program_code} sẽ được công bố tại đây trong thời gian tới.</div>\n'
        f'            <a class="listing-placeholder-link" href="{catalog_url}" target="_blank" rel="noopener">Khám phá Property Hub →</a>\n'
        '          </div>\n'
        '        </article>'
    )


def render_section(alias, all_props, offline=False):
    cfg = COUNTRIES[alias]
    program_code = cfg['program_code']
    notion_country = cfg['notion_country']

    # Filter live properties by country.
    candidates = [p for p in all_props if country_matches(p.get('country', ''), notion_country)]
    selected = select_pair(candidates) if not offline else []

    # Derive Vietnamese country name for the section header / footnote.
    if selected:
        country_vi = re.sub(r'^\S+\s+', '', selected[0].get('country', '')).strip()
    elif isinstance(notion_country, list):
        country_vi = notion_country[0]
    else:
        country_vi = notion_country

    fn_url = ph_catalog_url(program_code, alias)

    cards = []
    for prop in selected:
        pdp = fetch_pdp_details(prop['listingUrl']) if prop.get('listingUrl') else {}
        cards.append(render_card(prop, pdp, cfg))
    while len(cards) < 2:
        cards.append(render_placeholder(country_vi, program_code, fn_url))

    return (
        '    <!-- LIVE LISTINGS — spotlight section between #02 and #03 (PB template; generated by tools/apply_listings.py; enumeration via Worker → Notion, detail via PDP fetch) -->\n'
        '    <section class="section section-spotlight" id="listings">\n'
        '      <div class="sec-label">Cơ Hội Đầu Tư Thực Tế</div>\n'
        f'      <h2 class="sec-title">BĐS Đủ Điều Kiện {program_code} — Đang Mở Bán</h2>\n'
        f'      <p class="sec-sub">Đây là tài sản đã được NAC thẩm định, đủ điều kiện cho hồ sơ {program_code} {country_vi} và sẵn sàng giao dịch. Bạn không cần săn tìm — chúng tôi đã chọn lọc.</p>\n'
        '\n'
        '      <div class="listings-grid">\n'
        + '\n'.join(cards) + '\n'
        '      </div>\n'
        '\n'
        '      <div class="listings-footnote">\n'
        f'        <span class="listings-fn-text">NAC chỉ giới thiệu BĐS đã được thẩm định pháp lý độc lập và xác nhận đủ điều kiện {program_code} {country_vi}.</span>\n'
        f'        <a class="listings-fn-link" href="{fn_url}" target="_blank" rel="noopener">Tất cả BĐS đủ điều kiện {program_code} →</a>\n'
        '      </div>\n'
        '    </section>'
    )


MARKER_RE = re.compile(
    r'(    <!-- LISTINGS START -->)(.*?)(    <!-- LISTINGS END -->)',
    re.DOTALL,
)


def apply_one(alias, all_props, offline=False):
    if alias not in COUNTRIES:
        return None, 'no country config'
    fname = ALIAS_FILE.get(alias)
    if not fname:
        return None, 'no filename mapping'
    path = BROCHURE_DIR / fname
    if not path.exists():
        return None, f'file not found ({fname})'

    doc = path.read_text(encoding='utf-8')
    if not MARKER_RE.search(doc):
        return None, 'no LISTINGS markers (skipped)'

    rendered = render_section(alias, all_props, offline=offline)
    new_doc = MARKER_RE.sub(
        lambda m: m.group(1) + '\n' + rendered + '\n    ' + m.group(3).lstrip(),
        doc,
    )

    if new_doc == doc:
        return False, 'no changes'
    path.write_text(new_doc, encoding='utf-8')
    return True, 'updated'


def main():
    args = [a for a in sys.argv[1:] if a != '--offline']
    offline = '--offline' in sys.argv[1:] or os.environ.get('APPLY_LISTINGS_OFFLINE') == '1'

    print(f'Fetching live properties from worker…')
    all_props = [] if offline else fetch_all_properties()
    print(f'  got {len(all_props)} live properties')

    aliases = args or list(ALIAS_FILE.keys())
    changed = 0
    for alias in aliases:
        ok, msg = apply_one(alias, all_props, offline=offline)
        marker = '✓' if ok else ('–' if ok is False else '·')
        print(f'  {marker} {alias:12s} {msg}')
        if ok:
            changed += 1
    print(f'\n{changed} brochure(s) updated.')


if __name__ == '__main__':
    main()
