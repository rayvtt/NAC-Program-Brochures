"""Fetch the Overview deck card rows from Notion and regenerate the
card markup + cardMeta in NAC-BROCHURES-OVERVIEW.html.

DB: 🎴 NAC - Overview Deck (id ae0d5fde-52e6-4a1a-b66e-43533f06c25d).
Schema documented in data/overview_schema.py — kept in sync there.

Idempotent. Replaces content between marker pairs:
  <!-- OVERVIEW-DECK-CARDS START --> … <!-- OVERVIEW-DECK-CARDS END -->
  /* OVERVIEW-CARDMETA START */     … /* OVERVIEW-CARDMETA END */

Stdlib-only (Python 3.11+). Requires env: NOTION_KEY.
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OVERVIEW_FILE = ROOT / 'Brochures html' / 'NAC-BROCHURES-OVERVIEW.html'
# Parent database id. We query the classic /databases/{id}/query endpoint with
# Notion-Version 2022-06-28 (same as tools/pull_from_notion.py). The newer
# /data_sources/{id}/query endpoint only exists on Notion-Version 2025-09-03+,
# so calling it under 2022-06-28 returns HTTP 400 invalid_request_url.
DATABASE_ID = '26d8e7b69c4840f19adbac784d257330'
DATA_SOURCE_ID = 'ae0d5fde-52e6-4a1a-b66e-43533f06c25d'  # data source under DATABASE_ID (kept for reference)
NOTION_BASE = 'https://api.notion.com/v1'

CARD_START = '<!-- OVERVIEW-DECK-CARDS START -->'
CARD_END = '<!-- OVERVIEW-DECK-CARDS END -->'
META_START = '/* OVERVIEW-CARDMETA START */'
META_END = '/* OVERVIEW-CARDMETA END */'


def http(method, url, *, token, body=None):
    req = urllib.request.Request(url, method=method)
    req.add_header('Authorization', f'Bearer {token}')
    req.add_header('Notion-Version', '2022-06-28')
    req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req, data=body.encode() if body else None, timeout=30) as r:
            return r.status, r.read().decode('utf-8')
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8', errors='replace')


def decode_prop(prop):
    if not prop:
        return ''
    t = prop['type']
    if t == 'title':
        return ''.join(rt['plain_text'] for rt in prop['title'])
    if t == 'rich_text':
        return ''.join(rt['plain_text'] for rt in prop['rich_text'])
    if t == 'number':
        return prop.get('number')
    if t == 'select':
        sel = prop.get('select')
        return sel['name'] if sel else ''
    if t == 'url':
        return prop.get('url') or ''
    return ''


def query_all_rows(token):
    rows = []
    cursor = None
    while True:
        body = json.dumps({'page_size': 100, **({'start_cursor': cursor} if cursor else {})})
        status, resp = http(
            'POST', f'{NOTION_BASE}/databases/{DATABASE_ID}/query',
            token=token, body=body,
        )
        if status != 200:
            sys.exit(f'❌ HTTP {status} querying overview DB: {resp[:500]}')
        data = json.loads(resp)
        rows.extend(data.get('results', []))
        if not data.get('has_more'):
            break
        cursor = data.get('next_cursor')
    return rows


def to_card_dict(row):
    p = row['properties']
    return {
        'order': decode_prop(p.get('order')) or 0,
        'alias': decode_prop(p.get('alias')),
        'flag': decode_prop(p.get('flag')),
        'country_vi': decode_prop(p.get('country (VI)')),
        'country_en': decode_prop(p.get('country (EN)')),
        'prog_vi': decode_prop(p.get('prog (VI)')),
        'prog_en': decode_prop(p.get('prog (EN)')),
        'badge_vi': decode_prop(p.get('badge text (VI)')),
        'badge_en': decode_prop(p.get('badge text (EN)')),
        'badge_color': decode_prop(p.get('badge color')) or '#999',
        'photo': decode_prop(p.get('photo URL')),
        'status': decode_prop(p.get('status')) or 'Coming',
        'score': decode_prop(p.get('score')),
        'tag': decode_prop(p.get('tag')) or 'cheap',
        'price': decode_prop(p.get('price display')),
        'wp_url': decode_prop(p.get('WP URL')),
        'modal': decode_prop(p.get('modal title')),
    }


# ── Star rendering ──────────────────────────────────────────────────────
EYE_SVG = (
    '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="2.5" style="flex-shrink:0">'
    '<path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7z"/><circle cx="12" cy="12" r="3"/></svg>'
)
STAR_POLY = (
    '<polygon points="10,1 12.9,7 19.5,7.6 14.5,12 16.2,18.5 10,15 3.8,18.5 5.5,12 0.5,7.6 7.1,7"/>'
)


def render_stars(score, idx):
    """0-100 → 5 stars. Half-star buckets at 10% increments."""
    if score is None:
        return ''
    out_of_5 = max(0, min(5, score / 20))
    full = int(out_of_5)
    half = (out_of_5 - full) >= 0.25
    if half and full < 5:
        empty = 5 - full - 1
    else:
        half = False
        empty = 5 - full
    parts = []
    for _ in range(full):
        parts.append(f'<svg class="st-star st-full" viewBox="0 0 20 20">{STAR_POLY}</svg>')
    if half:
        parts.append(
            f'<svg class="st-star st-half" viewBox="0 0 20 20">'
            f'<defs><linearGradient id="hg{idx:02d}">'
            f'<stop offset="50%" stop-color="currentColor"/>'
            f'<stop offset="50%" stop-color="transparent"/>'
            f'</linearGradient></defs>'
            f'<polygon points="10,1 12.9,7 19.5,7.6 14.5,12 16.2,18.5 10,15 3.8,18.5 5.5,12 0.5,7.6 7.1,7" class="st-empty"/>'
            f'<polygon points="10,1 12.9,7 19.5,7.6 14.5,12 16.2,18.5 10,15 3.8,18.5 5.5,12 0.5,7.6 7.1,7" fill="url(#hg{idx:02d})"/>'
            f'</svg>'
        )
    for _ in range(empty):
        parts.append(f'<svg class="st-star st-empty" viewBox="0 0 20 20">{STAR_POLY}</svg>')
    return ''.join(parts)


# ── Card rendering ─────────────────────────────────────────────────────
def render_card(idx, c):
    photo = c['photo'] or ''
    cls = 'card coming' if c['status'] == 'Coming' else 'card'
    url_attr = c['wp_url'] if c['status'] != 'Coming' else ''

    badge_vi = c['badge_vi'] or ''
    badge_en = c['badge_en'] or badge_vi
    country_vi = c['country_vi'] or ''
    country_en = c['country_en'] or country_vi
    prog_vi = c['prog_vi'] or ''
    prog_en = c['prog_en'] or prog_vi

    parts = [
        f'    <!-- CARD {idx}: {country_en} -->',
        f'    <div class="{cls}" data-index="{idx}" data-url="{url_attr}">',
        f'      <div class="card-photo" style="background-image:url(\'{photo}\')"></div>',
        '      <div class="card-grad"></div>',
        '      <div class="card-body">',
        (
            f'        <div class="card-badge">'
            f'<span class="bdot" style="background:{c["badge_color"]}"></span>'
            f'<span data-vi="{escape_attr(badge_vi)}" data-en="{escape_attr(badge_en)}">{badge_vi}</span>'
            f'</div>'
        ),
        f'        <div class="card-flag">{c["flag"]}</div>',
        (
            f'        <div class="card-country" data-vi="{escape_attr(country_vi)}" data-en="{escape_attr(country_en)}">{country_vi}</div>'
        ),
        (
            f'        <div class="card-prog" data-vi="{escape_attr(prog_vi)}" data-en="{escape_attr(prog_en)}">{prog_vi}</div>'
        ),
    ]

    if c['status'] == 'Coming':
        parts.append(
            '        <div class="card-coming" data-vi="Sắp Ra Mắt" data-en="Coming Soon">Sắp Ra Mắt</div>'
        )
    elif c['status'] == 'Closed':
        # Closed = legacy reference (Spain). Show CTA but no score section.
        modal = c['modal'] or f'{badge_vi}'
        parts.append(
            f'        <div class="card-cta-wrap"><a class="card-cta" href="#" '
            f"onclick=\"event.stopPropagation();openModal('{escape_js(modal)}','{c['wp_url']}');return false;\">"
            f'{EYE_SVG}<span data-vi="Đọc Tài Liệu" data-en="Read Reference">Đọc Tài Liệu</span></a></div>'
        )
    else:  # Live
        score = c.get('score')
        if score is not None:
            parts.append(
                '        <div class="card-score-section">'
                '<div class="card-score-lbl" data-vi="Thang Điểm NAC (INDEX)" data-en="NAC Score (INDEX)">Thang Điểm NAC (INDEX)</div>'
                f'<div class="card-score-row"><span class="card-snum">{int(score)}</span><span class="card-sden">/100</span></div>'
                f'<div class="card-stars">{render_stars(score, idx)}</div></div>'
            )
        modal = c['modal'] or f'{badge_vi}'
        parts.append(
            f'        <div class="card-cta-wrap"><a class="card-cta" href="#" '
            f"onclick=\"event.stopPropagation();openModal('{escape_js(modal)}','{c['wp_url']}');return false;\">"
            f'{EYE_SVG}<span data-vi="Đọc Brochure" data-en="Read Brochure">Đọc Brochure</span></a></div>'
        )

    parts.extend(['      </div>', '    </div>'])
    return '\n'.join(parts)


def escape_attr(s):
    return (s or '').replace('&', '&amp;').replace('"', '&quot;')


def escape_js(s):
    return (s or '').replace('\\', '\\\\').replace("'", "\\'")


# ── Main ───────────────────────────────────────────────────────────────
def main():
    token = os.environ.get('NOTION_KEY')
    if not token:
        sys.exit('❌ NOTION_KEY env var missing')

    print('Querying overview deck DB…')
    rows = query_all_rows(token)
    print(f'  fetched {len(rows)} rows')

    cards = sorted((to_card_dict(r) for r in rows), key=lambda c: c['order'] or 0)
    # Drop any all-empty rows (Notion sometimes shows a blank template row)
    cards = [c for c in cards if c['country_vi'] or c['flag']]
    if not cards:
        sys.exit('❌ no cards found in overview DB (or query returned nothing)')

    # Re-index 0..N for HTML data-index and cardMeta keys.
    card_html = '\n'.join(render_card(i, c) for i, c in enumerate(cards))
    meta_lines = []
    for i, c in enumerate(cards):
        tag = c.get('tag') or 'cheap'
        price = (c.get('price') or '').replace("'", "\\'")
        country = c.get('country_en') or c.get('country_vi') or '?'
        meta_lines.append(f"  {i}:  {{ tag:'{tag}', price:'{price}' }},   // {country}")
    meta_block = (
        'const cardMeta = {\n' + '\n'.join(meta_lines) + '\n};'
    )

    doc = OVERVIEW_FILE.read_text()

    new_doc = re.sub(
        rf'{re.escape(CARD_START)}.*?{re.escape(CARD_END)}',
        f'{CARD_START}\n{card_html}\n    {CARD_END}',
        doc,
        count=1,
        flags=re.DOTALL,
    )
    new_doc = re.sub(
        rf'{re.escape(META_START)}.*?{re.escape(META_END)}',
        f'{META_START}\n{meta_block}\n{META_END}',
        new_doc,
        count=1,
        flags=re.DOTALL,
    )

    if new_doc == doc:
        print('✓ No changes (overview already in sync with Notion).')
        return

    if CARD_START not in doc or META_START not in doc:
        sys.exit(
            '❌ marker(s) missing in NAC-BROCHURES-OVERVIEW.html — add\n'
            f'  {CARD_START} … {CARD_END}\n'
            f'  {META_START} … {META_END}\n'
            'around the existing card deck and cardMeta block.'
        )

    OVERVIEW_FILE.write_text(new_doc)
    print(f'✓ Wrote {len(cards)} cards → NAC-BROCHURES-OVERVIEW.html')


if __name__ == '__main__':
    main()
