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
    """Pull the emoji flag from a '🇹🇷 Thổ Nhĩ Kỳ' style string.

    Returns '' if the first token isn't a flag emoji (e.g. for legacy
    rows like 'United Kingdom' that lack the prefix). Flag emojis are
    two regional-indicator codepoints in the U+1F1E6..U+1F1FF range.
    """
    if not prop_country:
        return ''
    first = prop_country.split(maxsplit=1)[0]
    # A flag emoji is exactly 2 regional-indicator codepoints.
    if len(first) == 2 and all(0x1F1E6 <= ord(c) <= 0x1F1FF for c in first):
        return first
    return ''


def strip_country_flag(prop_country):
    """Return the country name with any leading flag emoji removed."""
    if not prop_country:
        return ''
    if extract_flag(prop_country):
        return re.sub(r'^\S+\s+', '', prop_country).strip()
    return prop_country.strip()


def ph_catalog_url(program_code, country_alias):
    return (
        'https://nomadassetcollective.com/property-hub/'
        f'?program={program_code.lower()}&country={country_alias}'
    )


# ── Selection (Rule 1 + Rule 2) ─────────────────────────────────────────
def select_pair(candidates, fortnight=None, pin=None):
    """Apply Rule 1 (cheapest+priciest) + Rule 2 (biweekly rotation).

    ≤ 2 candidates → return them all.
    > 2 candidates → card 1 = cheapest (anchor); card 2 = rotated from
        the rest, biased toward a different hubType than card 1.

    Curation override:
        If `pin` is a non-empty list of property IDs, those IDs are
        looked up in `candidates` and returned in the given order
        (up to 2). Missing IDs fall back to the auto-selected pair.
    """
    if pin:
        by_id = {p.get('id'): p for p in candidates}
        picked = [by_id[i] for i in pin if i in by_id]
        if picked:
            return picked[:2]
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
def clean(text):
    """Strip leading/trailing whitespace and undo any HTML entities present
    in the source (PDP scrape returns "Hammersmith &amp; Fulham" which would
    re-encode to "&amp;amp;" if escaped again)."""
    return html_lib.unescape((text or '').strip())


def render_card(prop, pdp, country_cfg):
    program_code = country_cfg['program_code']
    # Prefer the PDP's clean separated flag/country fields; fall back to
    # parsing the worker's combined "🇹🇷 Thổ Nhĩ Kỳ" string.
    flag = clean(pdp.get('flag') or extract_flag(prop.get('country', '')))
    e = html_lib.escape

    # ── Bilingual content (VI primary, EN from PDP when available) ──────
    name_vi = short_name(clean(pdp.get('property_name_vi') or prop.get('name_vi') or ''))
    name_en = short_name(clean(pdp.get('property_name_en') or prop.get('name_en') or ''))
    desc_vi = first_sentence(clean(pdp.get('desc_vi') or prop.get('excerpt_vi') or ''))
    desc_en = first_sentence(clean(pdp.get('desc_en') or prop.get('excerpt_en') or ''))
    tagline_vi = clean(pdp.get('tagline_vi') or prop.get('hubType', ''))
    tagline_en = clean(pdp.get('tagline_en') or prop.get('hubType', ''))

    # ── Location ────────────────────────────────────────────────────────
    # District is the PDP's "neighborhood" field, e.g. "Şişli / Levent".
    # Some districts have very long compound forms ("White City, Hammersmith
    # & Fulham") — keep the first comma-segment for the on-image badge so
    # it doesn't crowd against the NAC-ID, but use the full string in the
    # body location pin.
    district_full = clean(pdp.get('district', ''))
    district_short = district_full.split(',')[0].strip()
    country_clean = clean(pdp.get('country', '')) or strip_country_flag(prop.get('country', ''))
    location_parts = [p for p in [district_full, country_clean] if p]
    location_text = ' · '.join(location_parts)

    # ── Stats ───────────────────────────────────────────────────────────
    # The worker's `entry` is inconsistent: some rows store thousands (e.g. 290 = $290K),
    # others store full dollars (e.g. 1650000 = $1,650,000). Heuristic: if entry < 10_000
    # treat as thousands, otherwise as full units. Format with thousand-separator commas,
    # no compact "K" / "M" suffix (caused "€1650000K" on the new Cyprus listings).
    # Currency normalisation: per-country currency from data/listings.py — if the PDP price
    # came in with $ but the country uses € (EU programs), swap the symbol so Malta/Cyprus/
    # Portugal/Greece show € not $.
    currency = country_cfg.get('currency', '$')
    if pdp.get('price_full'):
        price_raw = pdp['price_full']
    elif prop.get('entry'):
        entry_full = prop['entry'] if prop['entry'] >= 10000 else prop['entry'] * 1000
        price_raw = f"{currency}{entry_full:,}"
    else:
        price_raw = '—'
    if currency != '$' and price_raw and price_raw != '—':
        price_raw = price_raw.replace('$', currency)
    price = price_raw
    y = pdp.get('yield_pct_unit') or (f"{prop['netYield']:.1f}%" if prop.get('netYield') else '—')
    irr = pdp.get('irr_pct_unit') or (f"{prop['irr']:.1f}%" if prop.get('irr') else '—')
    handover = pdp.get('handover') or '—'

    src_url = prop.get('listingUrl', '')
    ref = pdp.get('property_id') or (f'NAC-{prop["id"]}' if prop.get('id') else '')
    hero = pdp.get('hero_img') or prop.get('img', '')
    badge_loc = district_short or country_clean

    # ── Helper: emit a span with data-vi / data-en when EN differs ──────
    def bi(vi, en=None):
        if en and en != vi:
            return f'data-vi="{e(vi)}" data-en="{e(en)}"'
        return ''

    return (
        '        <article class="listing-card">\n'
        f'          <a class="listing-card-link" href="{e(src_url)}" target="_blank" rel="noopener">\n'
        '            <div class="listing-hero">\n'
        f'              <img src="{e(hero)}" alt="{e(name_vi)}" loading="lazy">\n'
        '              <div class="listing-badges">\n'
        f'                <span class="listing-badge listing-badge-eligible" data-vi="✓ Đủ điều kiện {program_code}" data-en="✓ {program_code} Eligible">✓ Đủ điều kiện {program_code}</span>\n'
        '              </div>\n'
        f'              <div class="listing-ref">{e(ref)}</div>\n'
        '            </div>\n'
        '            <div class="listing-body">\n'
        f'              <div class="listing-tagline" {bi(tagline_vi, tagline_en)}>{e(tagline_vi)}</div>\n'
        f'              <h3 class="listing-name" {bi(name_vi, name_en)}>{e(name_vi)}</h3>\n'
        f'              <div class="listing-location">📍 {e(location_text)}</div>\n'
        '              <div class="listing-stats">\n'
        f'                <div class="listing-stat"><div class="listing-stat-val">{e(price)}</div><div class="listing-stat-lbl" data-vi="Giá Khởi Điểm" data-en="Entry Price">Giá Khởi Điểm</div></div>\n'
        f'                <div class="listing-stat"><div class="listing-stat-val">{e(y)}</div><div class="listing-stat-lbl">Gross Yield</div></div>\n'
        f'                <div class="listing-stat"><div class="listing-stat-val">{e(irr)}</div><div class="listing-stat-lbl">5-Year IRR</div></div>\n'
        f'                <div class="listing-stat"><div class="listing-stat-val">{e(handover)}</div><div class="listing-stat-lbl" data-vi="Bàn Giao" data-en="Handover">Bàn Giao</div></div>\n'
        '              </div>\n'
        f'              <p class="listing-desc" {bi(desc_vi, desc_en)}>{e(desc_vi)}</p>\n'
        '              <div class="listing-cta-row">\n'
        '                <span class="listing-cta-primary" data-vi="Xem Chi Tiết →" data-en="View Details →">Xem Chi Tiết →</span>\n'
        '              </div>\n'
        '            </div>\n'
        '          </a>\n'
        '        </article>'
    )


def render_placeholder(country_vi, country_en, program_code, catalog_url):
    e = html_lib.escape
    sub_vi = f'Thêm BĐS {country_vi} đủ điều kiện {program_code} sẽ được công bố tại đây trong thời gian tới.'
    sub_en = f'More {program_code}-eligible {country_en} properties will be announced here soon.'
    return (
        '        <article class="listing-card listing-card-placeholder">\n'
        '          <div class="listing-placeholder-content">\n'
        '            <div class="listing-placeholder-icon">+</div>\n'
        '            <div class="listing-placeholder-title" data-vi="Đang Cập Nhật" data-en="Coming Soon">Đang Cập Nhật</div>\n'
        f'            <div class="listing-placeholder-sub" data-vi="{e(sub_vi)}" data-en="{e(sub_en)}">{e(sub_vi)}</div>\n'
        f'            <a class="listing-placeholder-link" href="{catalog_url}" target="_blank" rel="noopener" data-vi="Khám phá Property Hub →" data-en="Explore Property Hub →">Khám phá Property Hub →</a>\n'
        '          </div>\n'
        '        </article>'
    )


def _country_names_for(alias, notion_country, selected):
    """Best-effort VI + EN country labels for the section header/footnote."""
    # Identity registry has clean VI + EN strings keyed by alias.
    try:
        from data.brochure_identity import IDENTITY
        ident = IDENTITY.get(alias, {})
        return ident.get('country_vi', ''), ident.get('country_en', '')
    except Exception:
        pass
    # Fallback: derive VI from the worker prop; EN ≡ VI if we have nothing else.
    if selected:
        vi = clean(re.sub(r'^\S+\s+', '', selected[0].get('country', '')) or '')
    elif isinstance(notion_country, list):
        vi = notion_country[0]
    else:
        vi = notion_country
    return vi, vi


def render_section(alias, all_props, offline=False):
    cfg = COUNTRIES[alias]
    program_code = cfg['program_code']
    notion_country = cfg['notion_country']
    e = html_lib.escape

    # Filter live properties by country.
    candidates = [p for p in all_props if country_matches(p.get('country', ''), notion_country)]
    selected = select_pair(candidates, pin=cfg.get('pin')) if not offline else []

    country_vi, country_en = _country_names_for(alias, notion_country, selected)
    fn_url = ph_catalog_url(program_code, alias)

    cards = []
    for prop in selected:
        pdp = fetch_pdp_details(prop['listingUrl']) if prop.get('listingUrl') else {}
        cards.append(render_card(prop, pdp, cfg))
    while len(cards) < 2:
        cards.append(render_placeholder(country_vi, country_en, program_code, fn_url))

    # ── Section header (bilingual) ──────────────────────────────────────
    title_vi = f'BĐS Đủ Điều Kiện {program_code}'
    title_en = f'{program_code}-Eligible Properties'
    live_tag_vi = 'Đang Mở Bán'
    live_tag_en = 'Now Live'
    sub_vi = f'Đây là tài sản đã được NAC thẩm định, đủ điều kiện cho hồ sơ {program_code} {country_vi} và sẵn sàng giao dịch. Bạn không cần săn tìm — chúng tôi đã chọn lọc.'
    sub_en = f"These are properties NAC has vetted, eligible for the {country_en} {program_code} program and ready to transact. You don't need to hunt — we've curated them."
    fn_text_vi = f'NAC chỉ giới thiệu BĐS đã được thẩm định pháp lý độc lập và xác nhận đủ điều kiện {program_code} {country_vi}.'
    fn_text_en = f'NAC only features properties that have undergone independent legal due diligence and are confirmed eligible for the {country_en} {program_code} program.'
    fn_link_vi = f'Tất cả BĐS đủ điều kiện {program_code} →'
    fn_link_en = f'All {program_code}-eligible properties →'

    return (
        '    <!-- LIVE LISTINGS — spotlight section between #02 and #03 (PB template; generated by tools/apply_listings.py; enumeration via Worker → Notion, detail via PDP fetch) -->\n'
        '    <section class="section section-spotlight" id="listings">\n'
        '      <div class="sec-label" data-vi="Cơ Hội Đầu Tư Thực Tế" data-en="Real Investment Opportunities">Cơ Hội Đầu Tư Thực Tế</div>\n'
        f'      <h2 class="sec-title" data-vi="{e(title_vi)}" data-en="{e(title_en)}">{e(title_vi)}</h2>\n'
        f'      <div class="sec-live-tag"><span class="sec-live-dot" aria-hidden="true"></span><span data-vi="{e(live_tag_vi)}" data-en="{e(live_tag_en)}">{e(live_tag_vi)}</span></div>\n'
        f'      <p class="sec-sub" data-vi="{e(sub_vi)}" data-en="{e(sub_en)}">{e(sub_vi)}</p>\n'
        '\n'
        '      <div class="listings-grid">\n'
        + '\n'.join(cards) + '\n'
        '      </div>\n'
        '\n'
        '      <div class="listings-footnote">\n'
        f'        <span class="listings-fn-text" data-vi="{e(fn_text_vi)}" data-en="{e(fn_text_en)}">{e(fn_text_vi)}</span>\n'
        f'        <a class="listings-fn-link" href="{fn_url}" target="_blank" rel="noopener" data-vi="{e(fn_link_vi)}" data-en="{e(fn_link_en)}">{e(fn_link_vi)}</a>\n'
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
