#!/usr/bin/env python3
"""Parse any program brochure HTML → JSON payload for the Notion DB.

Run:
    python tools/extract_brochure.py turkey
    python tools/extract_brochure.py portugal
    python tools/extract_brochure.py --all       # all 12 brochures

Output: data/<alias>_payload.json

VI fields are extracted from the brochure HTML. EN fields are left empty
strings (fill in later via Notion UI or AI-translation pass).
"""
import html as html_lib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from data.brochure_identity import IDENTITY, alias_with_flag  # noqa: E402

BROCHURE_DIR = ROOT / 'Brochures html'
DATA_DIR = ROOT / 'data'


def squash(s):
    return re.sub(r'\s+', ' ', s).strip() if s else ''


def text_only(s):
    s = re.sub(r'<[^>]+>', '', s or '')
    s = html_lib.unescape(s)
    return squash(s)


# Tags we preserve in prose fields (info boxes, factcheck, article CTAs, etc.).
# Everything else gets stripped. <a> is normalised to <a href="..." target="_blank">.
_PROSE_ALLOWED_RE = re.compile(
    r'</?(strong|em)>|<a\s[^>]*>|</a>',
    re.IGNORECASE,
)


def prose_html(s):
    """Strip all HTML except <strong>, <em>, and <a href=…>. Unescape entities."""
    if not s:
        return ''
    stash = []

    def keep(m):
        tag = m.group(0)
        if tag.lower().startswith('<a '):
            href_m = re.search(r'href="([^"]+)"', tag)
            href = html_lib.unescape(href_m.group(1)) if href_m else ''
            tag = f'<a href="{href}" target="_blank">' if href else '<a>'
        stash.append(tag)
        return f'\0{len(stash) - 1}\0'

    stashed   = _PROSE_ALLOWED_RE.sub(keep, s)
    stripped  = re.sub(r'<[^>]+>', '', stashed)
    restored  = re.sub(r'\0(\d+)\0', lambda m: stash[int(m.group(1))], stripped)
    decoded   = html_lib.unescape(restored)
    return re.sub(r'\s+', ' ', decoded).strip()


def first_match(pattern, html, group=1, flags=re.DOTALL):
    m = re.search(pattern, html, flags)
    return m.group(group) if m else ''


def all_matches(pattern, html, flags=re.DOTALL):
    return [m.groups() for m in re.finditer(pattern, html, flags)]


def extract(alias):
    if alias not in IDENTITY:
        sys.exit(f'❌ unknown alias: {alias}')
    meta = IDENTITY[alias]
    src = BROCHURE_DIR / meta['source_filename']
    if not src.exists():
        sys.exit(f'❌ brochure HTML not found: {src}')

    html = src.read_text(encoding='utf-8')
    payload = {
        # Identity (from IDENTITY table)
        'alias':           alias_with_flag(alias),
        'country_vi':      meta['country_vi'],
        'country_en':      meta['country_en'],
        'flag':            meta['flag'],
        'program_code':    meta['program_code'],
        'program_tag':     meta['program_tag'],
        'program_vi':      meta['program_vi'],
        'program_en':      meta['program_en'],
        'source_filename': meta['source_filename'],
        'wp_page_id':      meta['wp_page_id'],
        'wp_slug':         meta['wp_slug'],
        'pb_status':       'Live',
    }

    # Color theme from :root CSS vars
    payload['color_primary']   = first_match(r'--country:\s*(#[0-9a-fA-F]+)', html) or '#1f2937'
    payload['color_secondary'] = first_match(r'--country2:\s*(#[0-9a-fA-F]+)', html) or '#111827'

    # ── Hero ──
    payload['hero_bg_img'] = ''  # Most brochures use CSS gradient
    # Breadcrumb: second <a> inside .breadcrumb (first is "NAC Index")
    bc = first_match(r'<div class="breadcrumb">(.*?)</div>', html)
    bc_links = re.findall(r'<a[^>]*>([^<]+)</a>', bc)
    payload['hero_breadcrumb_vi'] = squash(bc_links[1]) if len(bc_links) > 1 else ''
    payload['hero_breadcrumb_en'] = ''
    payload['hero_badge_vi']   = prose_html(first_match(r'<div class="hero-badge"[^>]*>(.*?)</div>', html))
    payload['hero_badge_en']   = ''
    payload['hero_title_top_vi'] = squash(first_match(r'<h1>([^<]+)<br>', html))
    payload['hero_title_top_en'] = ''
    payload['hero_title_em_vi']  = squash(first_match(r'<em>([^<]+)</em></h1>', html))
    payload['hero_title_em_en']  = ''
    payload['hero_desc_vi']      = prose_html(first_match(r'<p class="hero-desc">(.*?)</p>', html))
    payload['hero_desc_en']      = ''

    stats = []
    for num, lbl in all_matches(r'<div class="stat-num">([^<]+)</div>\s*<div class="stat-lbl">([^<]+)</div>', html):
        stats.append({'num': squash(num), 'lbl_vi': squash(lbl), 'lbl_en': ''})
    payload['hero_stats'] = json.dumps(stats[:4], ensure_ascii=False)

    # NAC scores
    payload['nac_score']          = int(first_match(r'<span class="score-big">(\d+)</span>', html) or 0)
    payload['nac_score_label_vi'] = squash(first_match(r'<div class="score-label">([^<]+)</div>', html))
    payload['nac_score_label_en'] = ''

    def sub_score(lbl):
        v = first_match(rf'<span class="sbar-lbl">{re.escape(lbl)}</span>.*?<span class="sbar-val">([\d.]+)</span>', html)
        return float(v) if v else 0.0
    payload['score_invest']       = sub_score('Đầu tư')
    payload['score_speed']        = sub_score('Tốc độ')
    payload['score_lifestyle']    = sub_score('Chất lượng sống')
    payload['score_passport']     = sub_score('Hộ chiếu')
    payload['score_tax']          = sub_score('Thuế')
    payload['score_citizenship']  = sub_score('Quốc tịch')

    # ── Section 01 — Overview ──
    s01 = first_match(r'<section class="section" id="overview">(.*?)</section>', html)
    payload['s01_subtitle_vi'] = prose_html(first_match(r'<p class="sec-sub">(.*?)</p>', s01))
    payload['s01_subtitle_en'] = ''

    ov_cards = []
    for icon, label, value, note in all_matches(
        r'<div class="ov-card"><div class="ov-icon">([^<]+)</div>'
        r'<div class="ov-label">([^<]+)</div>'
        r'<div class="ov-value">([^<]+)</div>'
        r'<div class="ov-note">([^<]+)</div></div>',
        s01,
    ):
        ov_cards.append({
            'icon': squash(icon),
            'label_vi': html_lib.unescape(squash(label)), 'label_en': '',
            'value_vi': html_lib.unescape(squash(value)), 'value_en': '',
            'note_vi':  html_lib.unescape(squash(note)),  'note_en': '',
        })
    payload['s01_ov_cards'] = json.dumps(ov_cards, ensure_ascii=False)
    payload['s01_factcheck_vi']        = prose_html(first_match(r'<div class="factcheck-box">.*?<div>(.*?)</div>\s*</div>', s01))
    payload['s01_factcheck_en']        = ''
    payload['s01_article_cta_text_vi'] = prose_html(first_match(r'<div class="article-cta-text">(.*?)</div>', s01))
    payload['s01_article_cta_text_en'] = ''
    payload['s01_article_cta_url']     = first_match(r'<a class="article-cta-btn" href="([^"]+)"', s01)

    # ── Section 02 — Investment ──
    s02 = first_match(r'<section class="section" id="investment">(.*?)</section>', html)
    payload['s02_subtitle_vi'] = prose_html(first_match(r'<p class="sec-sub">(.*?)</p>', s02))
    payload['s02_subtitle_en'] = ''
    info_boxes = re.findall(r'<div class="info-box ([^"]*box)"[^>]*>.*?<div class="info-text">(.*?)</div>\s*</div>', s02, re.DOTALL)
    payload['s02_warning_box_vi'] = next((prose_html(t) for cls, t in info_boxes if 'amber' in cls), '')
    payload['s02_warning_box_en'] = ''
    payload['s02_nac_note_vi']    = next((prose_html(t) for cls, t in info_boxes if 'green' in cls), '')
    payload['s02_nac_note_en']    = ''

    tiers = []
    tier_list_html = first_match(r'<div class="tier-list">(.*)', s02)
    # Split into tier chunks using each `<div class="tier"`/`<div class="tier featured"`
    # marker as a delimiter; everything until the next marker (or end) is one tier.
    matches = list(re.finditer(r'<div class="tier(\s+featured)?">', tier_list_html))
    for i, m in enumerate(matches):
        featured = bool(m.group(1))
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(tier_list_html)
        chunk = tier_list_html[start:end]
        badge  = squash(first_match(r'<span class="tier-badge"[^>]*>([^<]+)</span>', chunk))
        amount = squash(first_match(r'<div class="tier-amount">([^<]+)</div>', chunk))
        name   = squash(first_match(r'<div class="tier-name">([^<]+)</div>', chunk))
        region = squash(first_match(r'<div class="tier-region">([^<]+)</div>', chunk))
        bar    = first_match(r'tier-bar-fill[^"]*"\s*style="[^"]*width:(\d+)%', chunk)
        tags_vi = [squash(t) for t in re.findall(r'<span class="ttag">([^<]+)</span>', chunk)]
        if amount or name:
            tiers.append({
                'badge_vi': badge, 'badge_en': '',
                'amount': amount,
                'name_vi': name, 'name_en': '',
                'region_vi': region, 'region_en': '',
                'bar_pct': int(bar) if bar else 0,
                'featured': featured,
                'tags_vi': tags_vi, 'tags_en': [],
            })
    payload['s02_tiers'] = json.dumps(tiers, ensure_ascii=False)

    # ── Section 03 — Process ──
    s03 = first_match(r'<section class="section" id="process">(.*?)</section>', html)
    payload['s03_subtitle_vi'] = prose_html(first_match(r'<p class="sec-sub">(.*?)</p>', s03))
    payload['s03_subtitle_en'] = ''
    timeline = []
    for week, title, body in all_matches(
        r'<div class="tl-week">([^<]+)</div>\s*'
        r'<div class="tl-title">([^<]+)</div>\s*'
        r'<div class="tl-body">(.*?)</div>',
        s03,
    ):
        timeline.append({
            'week_vi': squash(week), 'week_en': '',
            'title_vi': squash(title), 'title_en': '',
            'body_vi': prose_html(body), 'body_en': '',
        })
    payload['s03_timeline'] = json.dumps(timeline, ensure_ascii=False)

    # ── Section 04 — Family ──
    s04 = first_match(r'<section class="section" id="family">(.*?)</section>', html)
    payload['s04_subtitle_vi'] = prose_html(first_match(r'<p class="sec-sub">(.*?)</p>', s04))
    payload['s04_subtitle_en'] = ''
    fam = []
    for icon, title, note in all_matches(
        r'<div class="fam-icon">([^<]+)</div>\s*<div>\s*'
        r'<div class="fam-title">([^<]+)</div>\s*'
        r'<div class="fam-note">(.*?)</div>',
        s04,
    ):
        fam.append({
            'icon': squash(icon),
            'title_vi': html_lib.unescape(squash(title)), 'title_en': '',
            'note_vi': prose_html(note), 'note_en': '',
        })
    payload['s04_family_cards']   = json.dumps(fam, ensure_ascii=False)
    payload['s04_compare_note_vi'] = prose_html(first_match(r'<div class="info-box">.*?<div class="info-text">(.*?)</div>\s*</div>', s04))
    payload['s04_compare_note_en'] = ''

    # ── Section 05 — Tax ──
    s05 = first_match(r'<section class="section" id="tax">(.*?)</section>', html)
    payload['s05_subtitle_vi'] = prose_html(first_match(r'<p class="sec-sub">(.*?)</p>', s05))
    payload['s05_subtitle_en'] = ''
    tax_cards = []
    for icon, label, value, note in all_matches(
        r'<div class="ov-card"><div class="ov-icon">([^<]+)</div>'
        r'<div class="ov-label">([^<]+)</div>'
        r'<div class="ov-value">([^<]+)</div>'
        r'<div class="ov-note">([^<]+)</div></div>',
        s05,
    ):
        tax_cards.append({
            'icon': squash(icon),
            'label_vi': html_lib.unescape(squash(label)), 'label_en': '',
            'value_vi': html_lib.unescape(squash(value)), 'value_en': '',
            'note_vi':  html_lib.unescape(squash(note)),  'note_en': '',
        })
    payload['s05_tax_cards'] = json.dumps(tax_cards, ensure_ascii=False)
    s05_boxes = re.findall(r'<div class="info-box(?:\s+[^"]*)?"[^>]*>.*?<div class="info-text">(.*?)</div>\s*</div>', s05, re.DOTALL)
    payload['s05_special_note_vi']     = prose_html(s05_boxes[0]) if len(s05_boxes) > 0 else ''
    payload['s05_special_note_en']     = ''
    payload['s05_inheritance_note_vi'] = prose_html(s05_boxes[1]) if len(s05_boxes) > 1 else ''
    payload['s05_inheritance_note_en'] = ''

    # ── Section 06 — Citizenship ──
    s06 = first_match(r'<section class="section" id="citizenship">(.*?)</section>', html)
    payload['s06_subtitle_vi'] = prose_html(first_match(r'<p class="sec-sub">(.*?)</p>', s06))
    payload['s06_subtitle_en'] = ''
    roadmap = []
    for year, dot, label in all_matches(
        r'<div class="road-year">([^<]+)</div>\s*'
        r'<div class="road-dot"[^>]*>([^<]+)</div>\s*'
        r'<div class="road-label">([^<]+)</div>',
        s06,
    ):
        roadmap.append({
            'year_vi': squash(year), 'year_en': '',
            'dot': squash(dot),
            'label_vi': squash(label), 'label_en': '',
        })
    payload['s06_roadmap'] = json.dumps(roadmap, ensure_ascii=False)
    s06_boxes = re.findall(r'<div class="info-box(?:\s+[^"]*)?"[^>]*>.*?<div class="info-text">(.*?)</div>\s*</div>', s06, re.DOTALL)
    payload['s06_dual_citizenship_note_vi'] = prose_html(s06_boxes[0]) if len(s06_boxes) > 0 else ''
    payload['s06_dual_citizenship_note_en'] = ''
    payload['s06_nac_strategy_note_vi']     = prose_html(s06_boxes[1]) if len(s06_boxes) > 1 else ''
    payload['s06_nac_strategy_note_en']     = ''

    # ── Section 07 — Compare ──
    s07 = first_match(r'<section class="section" id="compare">(.*?)</section>', html)
    payload['s07_subtitle_vi'] = prose_html(first_match(r'<p class="sec-sub">(.*?)</p>', s07))
    payload['s07_subtitle_en'] = ''
    compare_rows = []
    for row_html in re.findall(r'<tr(?:\s+class="highlight")?>(.*?)</tr>', s07, re.DOTALL):
        flag    = squash(first_match(r'<span class="comp-flag">([^<]+)</span>', row_html))
        name    = prose_html(first_match(r'<span class="comp-flag">[^<]+</span>\s*(.*?)</td>', row_html))
        cells   = re.findall(r'<td[^>]*>(.*?)</td>', row_html, re.DOTALL)
        if len(cells) < 5 or not flag:
            continue
        score = first_match(r'<span class="comp-score-num">(\d+)</span>', row_html)
        compare_rows.append({
            'flag': flag,
            'name_vi': name, 'name_en': '',
            'min_invest': prose_html(cells[1]),
            'type_vi': prose_html(cells[2]), 'type_en': '',
            'mobility_vi': prose_html(cells[3]), 'mobility_en': '',
            'time_vi': prose_html(cells[4]), 'time_en': '',
            'score': int(score) if score else 0,
            'highlight': 'highlight' in row_html[:40],
        })
    payload['s07_compare_rows'] = json.dumps(compare_rows, ensure_ascii=False)
    payload['s07_cta_text_vi']  = prose_html(first_match(r'<div class="article-cta-text">(.*?)</div>', s07))
    payload['s07_cta_text_en']  = ''

    # ── Section 08 — Pros / Cons ──
    s08 = first_match(r'<section class="section" id="proscons">(.*?)</section>', html)
    payload['s08_subtitle_vi'] = prose_html(first_match(r'<p class="sec-sub">(.*?)</p>', s08))
    payload['s08_subtitle_en'] = ''
    pros = re.findall(r'<div class="pros">.*?<ul>(.*?)</ul>', s08, re.DOTALL)
    cons = re.findall(r'<div class="cons">.*?<ul>(.*?)</ul>', s08, re.DOTALL)
    pros_items = [{'vi': prose_html(li), 'en': ''} for li in re.findall(r'<li>(.*?)</li>', pros[0] if pros else '', re.DOTALL)]
    cons_items = [{'vi': prose_html(li), 'en': ''} for li in re.findall(r'<li>(.*?)</li>', cons[0] if cons else '', re.DOTALL)]
    payload['s08_pros'] = json.dumps(pros_items, ensure_ascii=False)
    payload['s08_cons'] = json.dumps(cons_items, ensure_ascii=False)
    payload['s08_risk_note_vi'] = prose_html(first_match(r'<div class="info-box amber-box">.*?<div class="info-text">(.*?)</div>', s08))
    payload['s08_risk_note_en'] = ''

    # ── Section 09 — NAC ──
    s09 = first_match(r'<section class="section" id="nac">(.*?)</section>', html)
    payload['s09_subtitle_vi'] = prose_html(first_match(r'<p class="sec-sub">(.*?)</p>', s09))
    payload['s09_subtitle_en'] = ''
    s09_first = first_match(r'<div class="info-box"[^>]*>.*?<div class="info-text">(.*?)</div>\s*</div>', s09)
    payload['s09_recommendation_vi'] = prose_html(s09_first)
    payload['s09_recommendation_en'] = ''
    payload['s09_cta_heading_vi']    = squash(first_match(r'<div class="nac-box">\s*<h3>([^<]+)</h3>', s09))
    payload['s09_cta_heading_en']    = ''
    payload['s09_cta_body_vi']       = prose_html(first_match(r'<div class="nac-box">\s*<h3>[^<]+</h3>\s*<p>(.*?)</p>', s09))
    payload['s09_cta_body_en']       = ''

    return payload


def write_payload(alias):
    payload = extract(alias)
    out = DATA_DIR / f'{alias}_payload.json'
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')

    # Quick stats
    n_empty = sum(1 for v in payload.values() if v == '' or v == 0 or v == '[]')
    n_structured = sum(
        len(json.loads(payload[k])) for k in [
            'hero_stats', 's01_ov_cards', 's02_tiers', 's03_timeline',
            's04_family_cards', 's05_tax_cards', 's06_roadmap',
            's07_compare_rows', 's08_pros', 's08_cons',
        ] if payload.get(k)
    )
    print(f'  ✓ {alias:12s}  {len(payload):3d} fields · {n_empty:2d} empty · {n_structured:3d} items in arrays')


def main():
    args = sys.argv[1:]
    if not args:
        sys.exit('usage: extract_brochure.py <alias|--all>')
    if args[0] == '--all':
        aliases = list(IDENTITY.keys())
    else:
        aliases = [args[0]]

    for a in aliases:
        write_payload(a)


if __name__ == '__main__':
    main()
