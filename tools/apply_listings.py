#!/usr/bin/env python3
"""Render the Live Listings spotlight section into every brochure.

Stats / images / descriptions are fetched LIVE from each Property Hub
listing page (data-notion="<field>" attributes — sourced from the
upstream Notion CRM). Static config (which URLs each brochure shows)
lives in data/listings.py.

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
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from data.listings import LISTINGS  # noqa: E402

BROCHURE_DIR = ROOT / 'Brochures html'

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
}

# Parse <foo data-notion="key">value</foo>. Multi-line desc fields use DOTALL.
DATA_NOTION_RE = re.compile(r'data-notion="([\w_]+)"[^>]*>(.*?)</[a-zA-Z]', re.DOTALL)
HERO_BG_RE = re.compile(
    r'class="nac-hero-img"[^>]*background-image:url\([\'"]([^\'"]+)[\'"]'
)
HANDOVER_RE = re.compile(
    r'Bàn Giao</span>(?:<span data-en="">[^<]*</span>)?</span>'
    r'<span class="nac-fact-val">([^<]+)</span>'
)


def fetch_listing(url, timeout=20):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'NAC-apply-listings/1.0'})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            doc = r.read().decode('utf-8', errors='replace')
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
        return None, f'fetch failed: {e}'

    fields = {m.group(1): m.group(2).strip() for m in DATA_NOTION_RE.finditer(doc)}

    hero_m = HERO_BG_RE.search(doc)
    if hero_m:
        fields['hero_img'] = hero_m.group(1)

    handover_m = HANDOVER_RE.search(doc)
    if handover_m:
        fields['handover'] = handover_m.group(1).replace(' (estimated)', '').strip()

    return fields, None


def short_name(full):
    """Strip everything after the first em-dash or en-dash separator."""
    return re.split(r'\s+[—\-–]\s+', full, maxsplit=1)[0].strip()


def first_sentence(text, max_len=240):
    """First sentence (up to max_len chars). Falls back to a clean truncate."""
    if not text:
        return ''
    period = text.find('. ')
    if 0 < period <= max_len:
        return text[: period + 1]
    if len(text) <= max_len:
        return text
    cut = text[:max_len].rsplit(' ', 1)[0]
    return cut + '…'


def parse_price(price_str):
    """'$572,300' → 572300; '$1.2M' → 1200000; '$400K' → 400000.

    Returns None when the input doesn't parse. Used for cheapest/priciest sort.
    """
    if not price_str:
        return None
    s = price_str.strip().replace('$', '').replace(' ', '').replace(',', '')
    mult = 1
    if s.upper().endswith('M'):
        s, mult = s[:-1], 1_000_000
    elif s.upper().endswith('K'):
        s, mult = s[:-1], 1_000
    try:
        return int(float(s) * mult)
    except ValueError:
        return None


def fortnight_index(today=None):
    """Deterministic 0..N index that increments every 2 weeks (ISO week / 2).

    Used to seed Rule 2 rotation so the same listings show all fortnight,
    different ones next fortnight.
    """
    today = today or datetime.date.today()
    iso_year, iso_week, _ = today.isocalendar()
    return iso_year * 26 + (iso_week // 2)


def select_pair(fetched, fortnight=None):
    """Apply Rule 1 + Rule 2 to a list of fetched listings.

    Rule 1: when > 2 candidates, anchor on cheapest + priciest.
    Rule 2: when > 2 candidates, every 2 weeks rotate which mid-priced
            listing fills card 2 (so users see variety over time but the
            cheapest anchor stays — TODO: confirm with user; current
            interpretation = "card 1 = cheapest always, card 2 rotates
            among priciest-and-above-median, biased to different hub_type
            from card 1 when possible").
    """
    if len(fetched) <= 2:
        return fetched

    with_price = [(parse_price(f.get('price_full', '')) or 0, f) for f in fetched]
    with_price.sort(key=lambda x: x[0])

    cheapest = with_price[0][1]
    # Card 2 pool = everything above the cheapest. Try to favour a different
    # hub_type for variety.
    pool = [f for _, f in with_price[1:]]
    different_type = [f for f in pool if f.get('hub_type') and f.get('hub_type') != cheapest.get('hub_type')]
    candidates = different_type or pool

    # Deterministic rotation: pick from `candidates` based on fortnight index.
    fortnight = fortnight if fortnight is not None else fortnight_index()
    card2 = candidates[fortnight % len(candidates)]
    return [cheapest, card2]


def ph_catalog_url(program_code, country_alias):
    """Build the 'see all listings' URL. Uses ?program=X&country=Y params.

    NOTE: the PH catalog at /property-hub/ is currently a pure client-side
    SPA — it does NOT yet read URL params, so the link lands on the catalog
    unfiltered. Adding URL-param support to PH is a follow-up in the
    property-hub repo. The params are harmless until then.
    """
    return (
        'https://nomadassetcollective.com/property-hub/'
        f'?program={program_code.lower()}&country={country_alias}'
    )


def render_card(fields, src_url, country):
    flag         = country['flag']
    country_vi   = country['country_vi']
    program_code = country['program_code']

    name = short_name(fields.get('property_name_vi') or fields.get('property_name_en', 'Property'))
    desc = first_sentence(fields.get('desc_vi', ''))
    tagline = fields.get('tagline_vi', '')
    district = fields.get('district', '').strip()
    location_parts = [p for p in [district, country_vi] if p]

    e = html_lib.escape

    return (
        '        <article class="listing-card">\n'
        f'          <a class="listing-card-link" href="{e(src_url)}" target="_blank" rel="noopener">\n'
        '            <div class="listing-hero">\n'
        f'              <img src="{e(fields.get("hero_img", ""))}" alt="{e(name)}" loading="lazy">\n'
        '              <div class="listing-badges">\n'
        f'                <span class="listing-badge listing-badge-flag">{flag} {e(district or country_vi)}</span>\n'
        f'                <span class="listing-badge listing-badge-eligible">✓ Đủ điều kiện {program_code}</span>\n'
        '              </div>\n'
        f'              <div class="listing-ref">{e(fields.get("property_id", ""))}</div>\n'
        '            </div>\n'
        '            <div class="listing-body">\n'
        f'              <div class="listing-tagline">{e(tagline)}</div>\n'
        f'              <h3 class="listing-name">{e(name)}</h3>\n'
        f'              <div class="listing-location">📍 {e(" · ".join(location_parts))}</div>\n'
        '              <div class="listing-stats">\n'
        f'                <div class="listing-stat"><div class="listing-stat-val">{e(fields.get("price_full", "—"))}</div><div class="listing-stat-lbl">Giá Khởi Điểm</div></div>\n'
        f'                <div class="listing-stat"><div class="listing-stat-val">{e(fields.get("yield_pct_unit", "—"))}</div><div class="listing-stat-lbl">Gross Yield</div></div>\n'
        f'                <div class="listing-stat"><div class="listing-stat-val">{e(fields.get("irr_pct_unit", "—"))}</div><div class="listing-stat-lbl">5-Year IRR</div></div>\n'
        f'                <div class="listing-stat"><div class="listing-stat-val">{e(fields.get("handover", "—"))}</div><div class="listing-stat-lbl">Bàn Giao</div></div>\n'
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


def render_section(alias, offline=False):
    country = LISTINGS[alias]
    program_code = country['program_code']
    country_vi   = country['country_vi']

    # Fetch all candidates, then apply Rule 1 + Rule 2 to pick max 2.
    fetched = []
    for url in country.get('urls', []):
        if offline:
            print(f'    · {alias}: offline mode, skipping fetch of {url}', file=sys.stderr)
            continue
        fields, err = fetch_listing(url)
        if err:
            print(f'    ! {alias}: {url} → {err}', file=sys.stderr)
            continue
        fields['_source_url'] = url
        fetched.append(fields)

    selected = select_pair(fetched)

    fn_url = ph_catalog_url(program_code, alias)

    cards = [render_card(f, f['_source_url'], country) for f in selected]
    while len(cards) < 2:
        cards.append(render_placeholder(country_vi, program_code, fn_url))

    return (
        '    <!-- LIVE LISTINGS — spotlight section between #02 and #03 (PB template; generated by tools/apply_listings.py; stats fetched live from Property Hub) -->\n'
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


def apply_one(alias, offline=False):
    if alias not in LISTINGS:
        return None, 'no data'
    fname = ALIAS_FILE.get(alias)
    if not fname:
        return None, 'no filename mapping'
    path = BROCHURE_DIR / fname
    if not path.exists():
        return None, f'file not found ({fname})'

    doc = path.read_text(encoding='utf-8')
    if not MARKER_RE.search(doc):
        return None, 'no LISTINGS markers (skipped)'

    rendered = render_section(alias, offline=offline)
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
    aliases = args or list(ALIAS_FILE.keys())
    changed = 0
    for alias in aliases:
        ok, msg = apply_one(alias, offline=offline)
        marker = '✓' if ok else ('–' if ok is False else '·')
        print(f'  {marker} {alias:12s} {msg}')
        if ok:
            changed += 1
    print(f'\n{changed} brochure(s) updated.')


if __name__ == '__main__':
    main()
