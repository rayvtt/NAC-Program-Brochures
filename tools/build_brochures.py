#!/usr/bin/env python3
"""Generate brochure HTML from Notion-sourced payloads.

Reads data/<alias>_payload.json + Brochures html/turkey-cbi_8.html (the
canonical skeleton) and produces a country-specific brochure HTML by:
  - swapping CSS color vars (--country, --country2)
  - swapping JS constants (PROGRAM, PROGRAM_VI, SOURCE_FILE)
  - rendering the hero block from data
  - rendering each section (01-09) from data using helper functions
  - leaving the LISTINGS spotlight markers + paywall blocks untouched
    (those are managed by apply_listings.py and the paywall pattern)

Run:
    python tools/build_brochures.py turkey         # one alias
    python tools/build_brochures.py --all          # all 12

Outputs go to build/<filename> (NOT to Brochures html/) so existing
hand-edited files stay live until we explicitly switch over.
"""
import html as html_lib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from data.brochure_identity import IDENTITY  # noqa: E402

SKELETON_PATH = ROOT / 'Brochures html' / 'turkey-cbi_8.html'
OUT_DIR = ROOT / 'build'


def e(s):
    """HTML-escape user-supplied text (data from Notion can contain <>&)."""
    return html_lib.escape(s or '', quote=False)


def _load_payload(alias):
    path = ROOT / 'data' / f'{alias}_payload.json'
    if not path.exists():
        sys.exit(f'❌ payload not found: {path}')
    return json.loads(path.read_text(encoding='utf-8'))


def _parse_json_field(payload, key):
    """A structured field stored as JSON-in-rich-text → Python list."""
    raw = payload.get(key, '')
    if not raw:
        return []
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        print(f'  ⚠ {key}: invalid JSON, treating as empty', file=sys.stderr)
        return []


# ── Hero ────────────────────────────────────────────────────────────────
def render_hero(d):
    flag = d.get('flag', '')
    stats = _parse_json_field(d, 'hero_stats')
    stat_blocks = []
    for s in stats:
        stat_blocks.append(
            f'            <div>\n'
            f'              <div class="stat-num">{e(s.get("num", ""))}</div>\n'
            f'              <div class="stat-lbl">{e(s.get("lbl_vi", ""))}</div>\n'
            f'            </div>'
        )
    stat_html = '\n            <div class="stat-divider"></div>\n'.join(stat_blocks)

    breadcrumb = d.get('hero_breadcrumb_vi', '')
    return f'''<section class="hero">
  <div class="hero-bg" id="heroBg"></div>
  <div class="hero-overlay"></div>
  <div class="hero-content">
    <div class="hero-i">
      <div class="breadcrumb">
        <a href="https://nomadassetcollective.com/nac-residence-index/" target="_blank">NAC Index</a>
        <span>›</span>
        <a href="https://nomadassetcollective.com/brochures/">{e(breadcrumb) if breadcrumb else "Chương Trình"}</a>
        <span>›</span>
        <span>{e(d.get("country_vi", ""))}</span>
      </div>
      <div class="hero-grid">
        <div>
          <div class="hero-badge"><span class="dot"></span> {e(d.get("hero_badge_vi", ""))}</div>
          <h1>{e(d.get("hero_title_top_vi", ""))}<br><em>{e(d.get("hero_title_em_vi", ""))}</em></h1>
          <p class="hero-desc">{e(d.get("hero_desc_vi", ""))}</p>
          <div class="hero-stats">
{stat_html}
          </div>
        </div>
        <div>
          <div class="score-card">
            <div class="score-flag">{flag}</div>
            <div class="score-title">Điểm Tổng Hợp NAC</div>
            <div>
              <span class="score-big">{d.get("nac_score", 0)}</span>
              <span class="score-denom">/100</span>
            </div>
            <div class="score-label">{e(d.get("nac_score_label_vi", ""))}</div>
            <div class="score-bars">
              <div class="sbar-row"><span class="sbar-lbl">Đầu tư</span><div class="sbar-track"><div class="sbar-fill" style="width:{int((d.get("score_invest") or 0)*10)}%"></div></div><span class="sbar-val">{d.get("score_invest", 0)}</span></div>
              <div class="sbar-row"><span class="sbar-lbl">Tốc độ</span><div class="sbar-track"><div class="sbar-fill" style="width:{int((d.get("score_speed") or 0)*10)}%"></div></div><span class="sbar-val">{d.get("score_speed", 0)}</span></div>
              <div class="sbar-row"><span class="sbar-lbl">Chất lượng sống</span><div class="sbar-track"><div class="sbar-fill" style="width:{int((d.get("score_lifestyle") or 0)*10)}%"></div></div><span class="sbar-val">{d.get("score_lifestyle", 0)}</span></div>
              <div class="sbar-row"><span class="sbar-lbl">Hộ chiếu</span><div class="sbar-track"><div class="sbar-fill" style="width:{int((d.get("score_passport") or 0)*10)}%"></div></div><span class="sbar-val">{d.get("score_passport", 0)}</span></div>
              <div class="sbar-row"><span class="sbar-lbl">Thuế</span><div class="sbar-track"><div class="sbar-fill" style="width:{int((d.get("score_tax") or 0)*10)}%"></div></div><span class="sbar-val">{d.get("score_tax", 0)}</span></div>
              <div class="sbar-row"><span class="sbar-lbl">Quốc tịch</span><div class="sbar-track"><div class="sbar-fill" style="width:{int((d.get("score_citizenship") or 0)*10)}%"></div></div><span class="sbar-val">{d.get("score_citizenship", 0)}</span></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</section>'''


# ── Section helpers ────────────────────────────────────────────────────
def _ov_card(c):
    return (f'        <div class="ov-card"><div class="ov-icon">{e(c.get("icon",""))}</div>'
            f'<div class="ov-label">{e(c.get("label_vi",""))}</div>'
            f'<div class="ov-value">{e(c.get("value_vi",""))}</div>'
            f'<div class="ov-note">{e(c.get("note_vi",""))}</div></div>')


def _tier(t):
    tags = ''.join(f'<span class="ttag">{e(tag)}</span>' for tag in t.get('tags_vi', []))
    featured = t.get('featured')
    featured_cls = ' featured' if featured else ''
    badge_bg = 'var(--country)' if featured else '#374151'
    bar_bg   = 'var(--country)' if featured else 'var(--text3)'
    return (
        f'        <div class="tier{featured_cls}">\n'
        f'          <span class="tier-badge" style="background:{badge_bg};color:#fff;">{e(t.get("badge_vi",""))}</span>\n'
        f'          <div class="tier-header"><div>\n'
        f'            <div class="tier-amount">{e(t.get("amount",""))}</div>\n'
        f'            <div class="tier-name">{e(t.get("name_vi",""))}</div>\n'
        f'            <div class="tier-region">{e(t.get("region_vi",""))}</div>\n'
        f'          </div></div>\n'
        f'          <div class="tier-bar-track"><div class="tier-bar-fill" style="background:{bar_bg};width:{t.get("bar_pct",50)}%"></div></div>\n'
        f'          <div class="tier-tags">\n            {tags}\n          </div>\n'
        f'        </div>'
    )


def _timeline_step(s):
    return (
        f'        <div class="tl-item">\n'
        f'          <div class="tl-week">{e(s.get("week_vi",""))}</div>\n'
        f'          <div class="tl-title">{e(s.get("title_vi",""))}</div>\n'
        f'          <div class="tl-body">{e(s.get("body_vi",""))}</div>\n'
        f'        </div>'
    )


def _family_card(c):
    return (f'        <div class="fam-card"><div class="fam-icon">{e(c.get("icon",""))}</div>'
            f'<div><div class="fam-title">{e(c.get("title_vi",""))}</div>'
            f'<div class="fam-note">{e(c.get("note_vi",""))}</div></div></div>')


def _roadmap_step(s):
    return (f'        <div class="road-step"><div class="road-year">{e(s.get("year_vi",""))}</div>'
            f'<div class="road-dot">{e(s.get("dot",""))}</div>'
            f'<div class="road-label">{e(s.get("label_vi",""))}</div></div>')


def _compare_row(r):
    type_class = 'tag-green' if 'Quốc' in r.get('type_vi', '') else 'tag-blue'
    fill_class = 'top' if r.get('score', 0) >= 85 else 'other'
    tr_cls = ' class="highlight"' if r.get('highlight') else ''
    cls = '' if r.get('highlight') else fill_class
    return (f'          <tr{tr_cls}>\n'
            f'            <td><span class="comp-flag">{e(r.get("flag",""))}</span> {e(r.get("name_vi",""))}</td>'
            f'<td>{e(r.get("min_invest",""))}</td>'
            f'<td><span class="tag {type_class}">{e(r.get("type_vi",""))}</span></td>'
            f'<td>{e(r.get("mobility_vi",""))}</td>'
            f'<td>{e(r.get("time_vi",""))}</td>\n'
            f'            <td><div class="comp-bar"><div class="comp-track"><div class="comp-fill {cls}" style="width:{r.get("score",0)}%"></div></div><span class="comp-score-num">{r.get("score",0)}</span></div></td>\n'
            f'          </tr>')


def _info_box(content_html, css_class=''):
    cls = f'info-box {css_class}'.strip()
    icon = {'amber-box': '⚠️', 'green-box': '💡', 'gold-box': '💡'}.get(css_class, 'ℹ️')
    return (f'      <div class="{cls}">\n'
            f'        <div class="info-icon">{icon}</div>\n'
            f'        <div class="info-text">{content_html}</div>\n'
            f'      </div>')


# ── Section renderers ──────────────────────────────────────────────────
def render_overview(d):
    cards = '\n'.join(_ov_card(c) for c in _parse_json_field(d, 's01_ov_cards'))
    article_cta = ''
    if d.get('s01_article_cta_text_vi'):
        article_cta = (
            f'      <div class="article-cta">\n'
            f'        <div class="article-cta-icon">📖</div>\n'
            f'        <div class="article-cta-text">{e(d["s01_article_cta_text_vi"])}</div>\n'
            f'        <a class="article-cta-btn" href="{e(d.get("s01_article_cta_url",""))}" target="_blank">Đọc Ngay →</a>\n'
            f'      </div>'
        )
    return f'''    <section class="section" id="overview">
      <div class="sec-label">01 — Tổng Quan</div>
      <h2 class="sec-title">Chương Trình Tổng Quan</h2>
      <p class="sec-sub">{e(d.get("s01_subtitle_vi",""))}</p>

      <div class="overview-grid">
{cards}
      </div>

      <div class="factcheck-box">
        <div class="fc-icon">🔍</div>
        <div>{e(d.get("s01_factcheck_vi",""))}</div>
      </div>

      <div class="chart-box">
        <div class="chart-title">Phân tích điểm 6 tiêu chí NAC — {e(d.get("program_vi",""))}</div>
        <canvas id="radarChart" style="max-height:300px"></canvas>
      </div>
{article_cta}
    </section>'''


_INLINE_CTA_INFO = '''      <div class="cta-strip" style="margin-top:8px">
        <span class="cta-strip-label">Tìm hiểu thêm:</span>
        <a data-tip="So Sánh" class="cta-btn cta-btn-outline" href="https://nomadassetcollective.com/so-sanh/" target="_blank">⚖️ <span class="cta-text">So Sánh Chương Trình</span></a>
        <a class="cta-btn cta-btn-primary" data-tip="Tư Vấn" href="https://nomadassetcollective.com/tu-van-nhanh/" target="_blank">📅 <span class="cta-text">Tư Vấn Ngay</span></a>
      </div>'''

_INLINE_CTA_ACTION = '''      <div class="cta-strip">
        <span class="cta-strip-label">Hành động:</span>
        <a class="cta-btn cta-btn-primary" data-tip="Tư Vấn" href="https://nomadassetcollective.com/tu-van-nhanh/" target="_blank">📅 <span class="cta-text">Tư Vấn Chiến Lược</span></a>
        <a data-tip="So Sánh" class="cta-btn cta-btn-outline" href="https://nomadassetcollective.com/so-sanh/" target="_blank">⚖️ <span class="cta-text">So Sánh Chương Trình</span></a>
        <a data-tip="WhatsApp" class="cta-btn cta-btn-wa" href="https://wa.me/447388646000" target="_blank" title="WhatsApp">💬</a>
      </div>'''


def render_investment(d):
    tiers = '\n'.join(_tier(t) for t in _parse_json_field(d, 's02_tiers'))
    warning = _info_box(e(d.get('s02_warning_box_vi', '')), 'amber-box') if d.get('s02_warning_box_vi') else ''
    nac_note = _info_box(e(d.get('s02_nac_note_vi', '')), 'green-box') if d.get('s02_nac_note_vi') else ''
    return f'''    <section class="section" id="investment">
      <div class="sec-label">02 — Đầu Tư</div>
      <h2 class="sec-title">Các Mức Đầu Tư</h2>
      <p class="sec-sub">{e(d.get("s02_subtitle_vi",""))}</p>
{warning}
      <div class="tier-list">
{tiers}
      </div>
{nac_note}
{_INLINE_CTA_INFO}
    </section>'''


def render_process(d):
    steps = '\n'.join(_timeline_step(s) for s in _parse_json_field(d, 's03_timeline'))
    return f'''    <section class="section" id="process">
      <div class="sec-label">03 — Quy Trình</div>
      <h2 class="sec-title">Quy Trình & Thời Gian</h2>
      <p class="sec-sub">{e(d.get("s03_subtitle_vi",""))}</p>

      <div class="timeline">
{steps}
      </div>
    </section>'''


def render_family(d):
    cards = '\n'.join(_family_card(c) for c in _parse_json_field(d, 's04_family_cards'))
    note = _info_box(e(d.get('s04_compare_note_vi', '')), '') if d.get('s04_compare_note_vi') else ''
    return f'''    <section class="section" id="family">
      <div class="sec-label">04 — Gia Đình</div>
      <h2 class="sec-title">Gia Đình & Đối Tượng Thụ Hưởng</h2>
      <p class="sec-sub">{e(d.get("s04_subtitle_vi",""))}</p>

      <div class="family-grid">
{cards}
      </div>
{note}
    </section>'''


def render_tax(d):
    cards = '\n'.join(_ov_card(c) for c in _parse_json_field(d, 's05_tax_cards'))
    boxes = []
    if d.get('s05_special_note_vi'):
        boxes.append(_info_box(e(d['s05_special_note_vi']), 'gold-box'))
    if d.get('s05_inheritance_note_vi'):
        boxes.append(_info_box(e(d['s05_inheritance_note_vi']), ''))
    boxes_html = '\n'.join(boxes)
    return f'''    <section class="section" id="tax">
      <div class="sec-label">05 — Thuế & Tài Chính</div>
      <h2 class="sec-title">Thuế & Lợi Thế Tài Chính</h2>
      <p class="sec-sub">{e(d.get("s05_subtitle_vi",""))}</p>

      <div class="overview-grid" style="grid-template-columns:repeat(2,1fr);margin-bottom:20px;">
{cards}
      </div>
{boxes_html}
    </section>'''


def render_citizenship(d):
    steps = '\n'.join(_roadmap_step(s) for s in _parse_json_field(d, 's06_roadmap'))
    boxes = []
    if d.get('s06_dual_citizenship_note_vi'):
        boxes.append(_info_box(e(d['s06_dual_citizenship_note_vi']), ''))
    boxes.append(f'      <div class="chart-box">\n        <div class="chart-title">So sánh tốc độ — {e(d.get("country_vi",""))} vs các chương trình hàng đầu (tháng)</div>\n        <canvas id="citizenshipChart" style="max-height:220px"></canvas>\n      </div>')
    if d.get('s06_nac_strategy_note_vi'):
        boxes.append(_info_box(e(d['s06_nac_strategy_note_vi']), 'gold-box'))
    boxes_html = '\n'.join(boxes)
    return f'''    <section class="section" id="citizenship">
      <div class="sec-label">06 — Quốc Tịch</div>
      <h2 class="sec-title">Lộ Trình Đến Quốc Tịch</h2>
      <p class="sec-sub">{e(d.get("s06_subtitle_vi",""))}</p>

      <div class="road">
{steps}
      </div>
{boxes_html}
{_INLINE_CTA_ACTION}
    </section>'''


def render_compare(d):
    rows = '\n'.join(_compare_row(r) for r in _parse_json_field(d, 's07_compare_rows'))
    cta = ''
    if d.get('s07_cta_text_vi'):
        cta = (f'      <div class="article-cta" style="margin-top:16px">\n'
               f'        <div class="article-cta-icon">⚖️</div>\n'
               f'        <div class="article-cta-text">{e(d["s07_cta_text_vi"])}</div>\n'
               f'        <a class="article-cta-btn" href="https://nomadassetcollective.com/so-sanh/" target="_blank">So <span class="cta-text">Sánh →</span></a>\n'
               f'      </div>')
    return f'''    <section class="section" id="compare">
      <div class="sec-label">07 — So Sánh</div>
      <h2 class="sec-title">So Sánh Chương Trình</h2>
      <p class="sec-sub">{e(d.get("s07_subtitle_vi",""))}</p>

      <div class="chart-box" style="margin-bottom:20px">
        <div class="chart-title">Điểm tổng hợp NAC — Top chương trình (2026)</div>
        <canvas id="compareChart" style="max-height:260px"></canvas>
      </div>

      <table class="comp-table">
        <thead>
          <tr><th>Chương trình</th><th>Đầu tư tối thiểu</th><th>Loại</th><th>Di chuyển</th><th>Thời gian</th><th>Điểm NAC</th></tr>
        </thead>
        <tbody>
{rows}
        </tbody>
      </table>
{cta}
    </section>'''


def render_proscons(d):
    pros = '\n'.join(f'            <li>{e(p.get("vi",""))}</li>' for p in _parse_json_field(d, 's08_pros'))
    cons = '\n'.join(f'            <li>{e(c.get("vi",""))}</li>' for c in _parse_json_field(d, 's08_cons'))
    risk = _info_box(e(d.get('s08_risk_note_vi', '')), 'amber-box') if d.get('s08_risk_note_vi') else ''
    return f'''    <section class="section" id="proscons">
      <div class="sec-label">08 — Ưu & Nhược</div>
      <h2 class="sec-title">Ưu & Nhược Điểm</h2>
      <p class="sec-sub">{e(d.get("s08_subtitle_vi",""))}</p>
      <div class="pros-cons">
        <div class="pros">
          <h4>✓ Ưu Điểm</h4>
          <ul>
{pros}
          </ul>
        </div>
        <div class="cons">
          <h4>✗ Nhược Điểm</h4>
          <ul>
{cons}
          </ul>
        </div>
      </div>
{risk}
    </section>'''


def render_nac(d):
    recommendation = ''
    if d.get('s09_recommendation_vi'):
        recommendation = _info_box(e(d['s09_recommendation_vi']), '') + '\n'
    return f'''    <section class="section" id="nac">
      <div class="sec-label">09 — Nhận Định NAC</div>
      <h2 class="sec-title">Nhận Định & Khuyến Nghị</h2>
      <p class="sec-sub">{e(d.get("s09_subtitle_vi",""))}</p>

{recommendation}
      <div class="chart-box" style="margin-bottom:20px">
        <div class="chart-title">Ma trận giá trị — Tốc độ vs Sức mạnh hộ chiếu</div>
        <canvas id="matrixChart" style="max-height:260px"></canvas>
      </div>

      <div class="nac-box">
        <h3>{e(d.get("s09_cta_heading_vi",""))}</h3>
        <p>{e(d.get("s09_cta_body_vi",""))}</p>
        <div class="nac-btns">
          <a class="nac-btn" href="https://nomadassetcollective.com/tu-van-nhanh/" target="_blank">Đặt Lịch Tư Vấn Miễn Phí →</a>
          <a class="nac-btn-wa" href="https://wa.me/447388646000" target="_blank" title="WhatsApp NAC">💬</a>
        </div>
      </div>
    </section>'''


SECTION_RENDERERS = {
    'overview':   render_overview,
    'investment': render_investment,
    'process':    render_process,
    'family':     render_family,
    'tax':        render_tax,
    'citizenship': render_citizenship,
    'compare':    render_compare,
    'proscons':   render_proscons,
    'nac':        render_nac,
}


def replace_section(html, section_id, renderer, data):
    new = renderer(data)
    pattern = re.compile(
        rf'    <section class="section[^"]*" id="{section_id}">.*?</section>',
        re.DOTALL,
    )
    if not pattern.search(html):
        print(f'  ⚠ section "{section_id}" not found in skeleton', file=sys.stderr)
        return html
    return pattern.sub(new, html, count=1)


def replace_hero(html, data):
    new = render_hero(data)
    pattern = re.compile(r'<section class="hero">.*?</section>', re.DOTALL)
    return pattern.sub(new, html, count=1)


def replace_css_colors(html, data):
    primary   = data.get('color_primary',   '#1f2937')
    secondary = data.get('color_secondary', '#111827')
    html = re.sub(r'(--country:\s*)#[0-9a-fA-F]+',  rf'\g<1>{primary}',   html, count=1)
    html = re.sub(r'(--country2:\s*)#[0-9a-fA-F]+', rf'\g<1>{secondary}', html, count=1)
    return html


def replace_js_constants(html, data):
    html = re.sub(r"(var\s+PROGRAM\s*=\s*)'[^']*'",
                  rf"\g<1>'{data.get('program_tag','')}'", html, count=1)
    html = re.sub(r"(var\s+PROGRAM_VI\s*=\s*)'[^']*'",
                  rf"\g<1>'{data.get('program_vi','')}'", html, count=1)
    html = re.sub(r"(var\s+SOURCE_FILE\s*=\s*)'[^']*'",
                  rf"\g<1>'{data.get('source_filename','')}'", html, count=1)
    return html


def build(alias):
    data = _load_payload(alias)
    html = SKELETON_PATH.read_text(encoding='utf-8')

    html = replace_css_colors(html, data)
    html = replace_js_constants(html, data)
    html = replace_hero(html, data)
    for section_id, renderer in SECTION_RENDERERS.items():
        html = replace_section(html, section_id, renderer, data)

    banner = (
        f'<!--\n'
        f'  Generated by tools/build_brochures.py from Notion DB.\n'
        f'  Alias: {alias}\n'
        f'  DO NOT EDIT — changes will be overwritten on next build.\n'
        f'  Edit the source: [NAC - Program Brochures] in Notion.\n'
        f'-->\n'
    )
    if html.startswith('<!DOCTYPE'):
        html = html.replace('<!DOCTYPE html>', banner + '<!DOCTYPE html>', 1)
    else:
        html = banner + html

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / IDENTITY[alias]['source_filename']
    out.write_text(html, encoding='utf-8')
    print(f'  ✓ {alias:12s} → {out.relative_to(ROOT)}')


def main():
    args = sys.argv[1:]
    if not args:
        sys.exit('usage: build_brochures.py <alias|--all>')
    aliases = list(IDENTITY.keys()) if args[0] == '--all' else [args[0]]
    for a in aliases:
        build(a)


if __name__ == '__main__':
    main()
