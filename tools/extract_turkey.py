#!/usr/bin/env python3
"""Parse Brochures html/turkey-cbi_8.html → JSON payload for the Notion DB.

Output goes to data/turkey_payload.json by default. Run:
    python tools/extract_turkey.py
    python tools/extract_turkey.py --stdout    # print to stdout

The payload only fills VI fields (the brochure HTML is VI-first). EN
fields are left empty strings — fill in via Notion UI later or run an
AI-translation pass.

This is a one-shot extractor for Turkey, not a general HTML→Notion
parser. Subsequent brochures will be authored in Notion directly.
"""
import html as html_lib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'Brochures html' / 'turkey-cbi_8.html'
OUT = ROOT / 'data' / 'turkey_payload.json'


def squash(s):
    """Collapse internal whitespace, strip ends."""
    return re.sub(r'\s+', ' ', s).strip() if s else ''


def text_only(s):
    """Strip HTML tags from a fragment (best-effort, sufficient for our content)."""
    s = re.sub(r'<[^>]+>', '', s)
    s = html_lib.unescape(s)
    return squash(s)


def first_match(pattern, html, group=1, flags=re.DOTALL):
    m = re.search(pattern, html, flags)
    return m.group(group) if m else ''


def all_matches(pattern, html, flags=re.DOTALL):
    return [m.groups() for m in re.finditer(pattern, html, flags)]


def main():
    html = SRC.read_text(encoding='utf-8')

    payload = {
        # ── Identity ──
        'alias':           'turkey',
        'country_vi':      'Thổ Nhĩ Kỳ',
        'country_en':      'Turkey',
        'flag':            '🇹🇷',
        'program_code':    'CBI',
        'program_tag':     'CBI · Thổ Nhĩ Kỳ',
        'program_vi':      'Thổ Nhĩ Kỳ CBI',
        'program_en':      'Turkey CBI',
        'source_filename': 'turkey-cbi_8.html',
        'wp_page_id':      1836,
        'wp_slug':         'chuong-trinh-tho-nhi-ky-cbi-citizenship-by-investment',
        'color_primary':   '#8B1A1A',
        'color_secondary': '#6e1414',
        'pb_status':       'Live',
    }

    # ── Hero ──
    payload['hero_bg_img'] = ''  # CSS gradient in turkey; no explicit URL
    payload['hero_breadcrumb_vi'] = squash(first_match(r'<span>([^<]+)</span>\s*</div>\s*<div class="hero-grid">', html))
    payload['hero_breadcrumb_en'] = ''
    payload['hero_badge_vi'] = text_only(first_match(r'<div class="hero-badge"[^>]*>(.*?)</div>', html))
    payload['hero_badge_en'] = ''
    payload['hero_title_top_vi'] = squash(first_match(r'<h1>([^<]+)<br>', html))
    payload['hero_title_top_en'] = ''
    payload['hero_title_em_vi']  = squash(first_match(r'<em>([^<]+)</em></h1>', html))
    payload['hero_title_em_en']  = ''
    payload['hero_desc_vi']      = text_only(first_match(r'<p class="hero-desc">(.*?)</p>', html))
    payload['hero_desc_en']      = ''

    # Hero stats: 4 pairs
    stats = []
    for num, lbl in all_matches(r'<div class="stat-num">([^<]+)</div>\s*<div class="stat-lbl">([^<]+)</div>', html):
        stats.append({'num': squash(num), 'lbl_vi': squash(lbl), 'lbl_en': ''})
    payload['hero_stats'] = json.dumps(stats[:4], ensure_ascii=False)

    # NAC scores
    payload['nac_score']           = int(first_match(r'<span class="score-big">(\d+)</span>', html) or 0)
    payload['nac_score_label_vi']  = squash(first_match(r'<div class="score-label">([^<]+)</div>', html))
    payload['nac_score_label_en']  = ''
    # Sub-scores: extract by label
    def sub_score(lbl):
        v = first_match(rf'<span class="sbar-lbl">{re.escape(lbl)}</span>.*?<span class="sbar-val">([\d.]+)</span>', html)
        return float(v) if v else 0.0
    payload['score_invest']        = sub_score('Đầu tư')
    payload['score_speed']         = sub_score('Tốc độ')
    payload['score_lifestyle']     = sub_score('Chất lượng sống')
    payload['score_passport']      = sub_score('Hộ chiếu')
    payload['score_tax']           = sub_score('Thuế')
    payload['score_citizenship']   = sub_score('Quốc tịch')

    # ── Section 01 — Overview ──
    s01_block = first_match(r'<section class="section" id="overview">(.*?)</section>', html)
    payload['s01_subtitle_vi'] = text_only(first_match(r'<p class="sec-sub">(.*?)</p>', s01_block))
    payload['s01_subtitle_en'] = ''

    ov_cards = []
    for icon, label, value, note in all_matches(
        r'<div class="ov-card"><div class="ov-icon">([^<]+)</div>'
        r'<div class="ov-label">([^<]+)</div>'
        r'<div class="ov-value">([^<]+)</div>'
        r'<div class="ov-note">([^<]+)</div></div>',
        s01_block,
    ):
        ov_cards.append({
            'icon': squash(icon),
            'label_vi': html_lib.unescape(squash(label)), 'label_en': '',
            'value_vi': html_lib.unescape(squash(value)), 'value_en': '',
            'note_vi':  html_lib.unescape(squash(note)),  'note_en': '',
        })
    payload['s01_ov_cards'] = json.dumps(ov_cards, ensure_ascii=False)

    payload['s01_factcheck_vi'] = text_only(first_match(r'<div class="factcheck-box">.*?<div>(.*?)</div>\s*</div>', s01_block))
    payload['s01_factcheck_en'] = ''
    payload['s01_article_cta_text_vi'] = text_only(first_match(r'<div class="article-cta-text">(.*?)</div>', s01_block))
    payload['s01_article_cta_text_en'] = ''
    payload['s01_article_cta_url']     = first_match(r'<a class="article-cta-btn" href="([^"]+)"', s01_block)

    # ── Section 02 — Investment ──
    s02_block = first_match(r'<section class="section" id="investment">(.*?)</section>', html)
    payload['s02_subtitle_vi'] = text_only(first_match(r'<p class="sec-sub">(.*?)</p>', s02_block))
    payload['s02_subtitle_en'] = ''
    info_boxes = re.findall(r'<div class="info-box ([^"]*box)"[^>]*>.*?<div class="info-text">(.*?)</div>\s*</div>', s02_block, re.DOTALL)
    warn = next((text_only(t) for cls, t in info_boxes if 'amber' in cls), '')
    nac = next((text_only(t) for cls, t in info_boxes if 'green' in cls), '')
    payload['s02_warning_box_vi'] = warn
    payload['s02_warning_box_en'] = ''
    payload['s02_nac_note_vi']    = nac
    payload['s02_nac_note_en']    = ''

    tiers = []
    for tier_html in re.findall(r'<div class="tier(?: featured)?">(.*?)</div>\s*</div>', s02_block, re.DOTALL):
        # ^ this regex is forgiving; we extract inside
        badge  = squash(first_match(r'<span class="tier-badge"[^>]*>([^<]+)</span>', tier_html))
        amount = squash(first_match(r'<div class="tier-amount">([^<]+)</div>', tier_html))
        name   = squash(first_match(r'<div class="tier-name">([^<]+)</div>', tier_html))
        region = squash(first_match(r'<div class="tier-region">([^<]+)</div>', tier_html))
        bar_pct_str = first_match(r'tier-bar-fill[^"]*"\s*style="[^"]*width:(\d+)%', tier_html)
        bar_pct = int(bar_pct_str) if bar_pct_str else 0
        tags_vi = [squash(t) for t in re.findall(r'<span class="ttag">([^<]+)</span>', tier_html)]
        featured = 'featured' in (tier_html[:50] or '')
        if amount or name:
            tiers.append({
                'badge_vi': badge, 'badge_en': '',
                'amount': amount,
                'name_vi': name, 'name_en': '',
                'region_vi': region, 'region_en': '',
                'bar_pct': bar_pct,
                'featured': featured,
                'tags_vi': tags_vi, 'tags_en': [],
            })
    # Mark the first tier as featured if header was lost in regex
    if tiers and not any(t['featured'] for t in tiers):
        tiers[0]['featured'] = True
    payload['s02_tiers'] = json.dumps(tiers, ensure_ascii=False)

    # ── Section 03 — Process ──
    s03_block = first_match(r'<section class="section" id="process">(.*?)</section>', html)
    payload['s03_subtitle_vi'] = text_only(first_match(r'<p class="sec-sub">(.*?)</p>', s03_block))
    payload['s03_subtitle_en'] = ''
    timeline = []
    for week, title, body in all_matches(
        r'<div class="tl-week">([^<]+)</div>\s*'
        r'<div class="tl-title">([^<]+)</div>\s*'
        r'<div class="tl-body">(.*?)</div>',
        s03_block,
    ):
        timeline.append({
            'week_vi': squash(week), 'week_en': '',
            'title_vi': squash(title), 'title_en': '',
            'body_vi': text_only(body), 'body_en': '',
        })
    payload['s03_timeline'] = json.dumps(timeline, ensure_ascii=False)

    # ── Section 04 — Family ──
    s04_block = first_match(r'<section class="section" id="family">(.*?)</section>', html)
    payload['s04_subtitle_vi'] = text_only(first_match(r'<p class="sec-sub">(.*?)</p>', s04_block))
    payload['s04_subtitle_en'] = ''
    fam = []
    for icon, title, note in all_matches(
        r'<div class="fam-icon">([^<]+)</div>\s*<div>\s*'
        r'<div class="fam-title">([^<]+)</div>\s*'
        r'<div class="fam-note">(.*?)</div>',
        s04_block,
    ):
        fam.append({
            'icon': squash(icon),
            'title_vi': html_lib.unescape(squash(title)), 'title_en': '',
            'note_vi': text_only(note), 'note_en': '',
        })
    payload['s04_family_cards'] = json.dumps(fam, ensure_ascii=False)
    s04_info = first_match(r'<div class="info-box">.*?<div class="info-text">(.*?)</div>\s*</div>', s04_block)
    payload['s04_compare_note_vi'] = text_only(s04_info)
    payload['s04_compare_note_en'] = ''

    # ── Section 05 — Tax ──
    s05_block = first_match(r'<section class="section" id="tax">(.*?)</section>', html)
    payload['s05_subtitle_vi'] = text_only(first_match(r'<p class="sec-sub">(.*?)</p>', s05_block))
    payload['s05_subtitle_en'] = ''
    tax_cards = []
    for icon, label, value, note in all_matches(
        r'<div class="ov-card"><div class="ov-icon">([^<]+)</div>'
        r'<div class="ov-label">([^<]+)</div>'
        r'<div class="ov-value">([^<]+)</div>'
        r'<div class="ov-note">([^<]+)</div></div>',
        s05_block,
    ):
        tax_cards.append({
            'icon': squash(icon),
            'label_vi': html_lib.unescape(squash(label)), 'label_en': '',
            'value_vi': html_lib.unescape(squash(value)), 'value_en': '',
            'note_vi':  html_lib.unescape(squash(note)),  'note_en': '',
        })
    payload['s05_tax_cards'] = json.dumps(tax_cards, ensure_ascii=False)
    s05_info_boxes = re.findall(r'<div class="info-box(?:\s+[^"]*)?"[^>]*>.*?<div class="info-text">(.*?)</div>\s*</div>', s05_block, re.DOTALL)
    payload['s05_special_note_vi']     = text_only(s05_info_boxes[0]) if len(s05_info_boxes) > 0 else ''
    payload['s05_special_note_en']     = ''
    payload['s05_inheritance_note_vi'] = text_only(s05_info_boxes[1]) if len(s05_info_boxes) > 1 else ''
    payload['s05_inheritance_note_en'] = ''

    # ── Section 06 — Citizenship ──
    s06_block = first_match(r'<section class="section" id="citizenship">(.*?)</section>', html)
    payload['s06_subtitle_vi'] = text_only(first_match(r'<p class="sec-sub">(.*?)</p>', s06_block))
    payload['s06_subtitle_en'] = ''
    roadmap = []
    for year, dot, label in all_matches(
        r'<div class="road-year">([^<]+)</div>\s*'
        r'<div class="road-dot"[^>]*>([^<]+)</div>\s*'
        r'<div class="road-label">([^<]+)</div>',
        s06_block,
    ):
        roadmap.append({
            'year_vi': squash(year), 'year_en': '',
            'dot': squash(dot),
            'label_vi': squash(label), 'label_en': '',
        })
    payload['s06_roadmap'] = json.dumps(roadmap, ensure_ascii=False)
    s06_info_boxes = re.findall(r'<div class="info-box(?:\s+[^"]*)?"[^>]*>.*?<div class="info-text">(.*?)</div>\s*</div>', s06_block, re.DOTALL)
    payload['s06_dual_citizenship_note_vi'] = text_only(s06_info_boxes[0]) if len(s06_info_boxes) > 0 else ''
    payload['s06_dual_citizenship_note_en'] = ''
    payload['s06_nac_strategy_note_vi']     = text_only(s06_info_boxes[1]) if len(s06_info_boxes) > 1 else ''
    payload['s06_nac_strategy_note_en']     = ''

    # ── Section 07 — Compare ──
    s07_block = first_match(r'<section class="section" id="compare">(.*?)</section>', html)
    payload['s07_subtitle_vi'] = text_only(first_match(r'<p class="sec-sub">(.*?)</p>', s07_block))
    payload['s07_subtitle_en'] = ''
    compare_rows = []
    for row_html in re.findall(r'<tr(?:\s+class="highlight")?>(.*?)</tr>', s07_block, re.DOTALL):
        flag    = squash(first_match(r'<span class="comp-flag">([^<]+)</span>', row_html))
        name    = text_only(first_match(r'<span class="comp-flag">[^<]+</span>\s*(.*?)</td>', row_html))
        cells   = re.findall(r'<td[^>]*>(.*?)</td>', row_html, re.DOTALL)
        if len(cells) < 5 or not flag:
            continue
        type_txt = text_only(cells[2])
        mobility = text_only(cells[3])
        time_txt = text_only(cells[4])
        score    = first_match(r'<span class="comp-score-num">(\d+)</span>', row_html)
        compare_rows.append({
            'flag': flag,
            'name_vi': name, 'name_en': '',
            'min_invest': text_only(cells[1]),
            'type_vi': type_txt, 'type_en': '',
            'mobility_vi': mobility, 'mobility_en': '',
            'time_vi': time_txt, 'time_en': '',
            'score': int(score) if score else 0,
            'highlight': 'highlight' in row_html[:40],
        })
    payload['s07_compare_rows'] = json.dumps(compare_rows, ensure_ascii=False)
    payload['s07_cta_text_vi'] = text_only(first_match(r'<div class="article-cta-text">(.*?)</div>', s07_block))
    payload['s07_cta_text_en'] = ''

    # ── Section 08 — Pros / Cons ──
    s08_block = first_match(r'<section class="section" id="proscons">(.*?)</section>', html)
    payload['s08_subtitle_vi'] = text_only(first_match(r'<p class="sec-sub">(.*?)</p>', s08_block))
    payload['s08_subtitle_en'] = ''
    pros = re.findall(r'<div class="pros">.*?<ul>(.*?)</ul>', s08_block, re.DOTALL)
    cons = re.findall(r'<div class="cons">.*?<ul>(.*?)</ul>', s08_block, re.DOTALL)
    pros_items = [{'vi': text_only(li), 'en': ''} for li in re.findall(r'<li>(.*?)</li>', pros[0] if pros else '', re.DOTALL)]
    cons_items = [{'vi': text_only(li), 'en': ''} for li in re.findall(r'<li>(.*?)</li>', cons[0] if cons else '', re.DOTALL)]
    payload['s08_pros'] = json.dumps(pros_items, ensure_ascii=False)
    payload['s08_cons'] = json.dumps(cons_items, ensure_ascii=False)
    s08_risk = first_match(r'<div class="info-box amber-box">.*?<div class="info-text">(.*?)</div>', s08_block)
    payload['s08_risk_note_vi'] = text_only(s08_risk)
    payload['s08_risk_note_en'] = ''

    # ── Section 09 — NAC ──
    s09_block = first_match(r'<section class="section" id="nac">(.*?)</section>', html)
    payload['s09_subtitle_vi'] = text_only(first_match(r'<p class="sec-sub">(.*?)</p>', s09_block))
    payload['s09_subtitle_en'] = ''
    s09_first_info = first_match(r'<div class="info-box"[^>]*>.*?<div class="info-text">(.*?)</div>\s*</div>', s09_block)
    payload['s09_recommendation_vi'] = text_only(s09_first_info)
    payload['s09_recommendation_en'] = ''
    payload['s09_cta_heading_vi'] = squash(first_match(r'<div class="nac-box">\s*<h3>([^<]+)</h3>', s09_block))
    payload['s09_cta_heading_en'] = ''
    payload['s09_cta_body_vi']    = text_only(first_match(r'<div class="nac-box">\s*<h3>[^<]+</h3>\s*<p>(.*?)</p>', s09_block))
    payload['s09_cta_body_en']    = ''

    # ── Write / print ──
    if '--stdout' in sys.argv:
        json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
        print()
    else:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f'✓ wrote {OUT} ({len(payload)} fields)')

        # Quick sanity report
        empty = [k for k, v in payload.items() if v == '' or v == '[]' or v == 0]
        if empty:
            print(f'  empty fields ({len(empty)}): {", ".join(empty[:8])}{"…" if len(empty) > 8 else ""}')


if __name__ == '__main__':
    main()
