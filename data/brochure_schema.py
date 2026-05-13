"""Schema for [NAC - Program Brochures] Notion DB (id 35f48ec25e8680d38b93d369c030d159).

Single source of truth shared across:
  tools/setup_brochure_db.py     creates / updates the Notion properties
  tools/extract_turkey.py        parses turkey-cbi_8.html → payload
  tools/check_brochure_payload.py validates JSON structure
  tools/push_brochure.py         POSTs a row to the DB
  tools/build_brochures.py       (phase 2) Notion → HTML generator

Every prose field is bilingual: `<name>_vi` (Vietnamese) + `<name>_en`
(English). Structured arrays (tiers, timeline, etc.) live in rich-text
fields as JSON; their internal items contain both `_vi` and `_en` keys.

Adding a new property: append to SCHEMA below; re-run setup workflow.
Renaming a property: Notion API can't rename — delete old + add new
manually in the UI, then update SCHEMA.
"""

NOTION_DB_ID = '35f48ec25e8680f69c3dc5ad538e7ca8'

# ── Display names ──────────────────────────────────────────────────────
# Technical key (Python / JSON) → Notion property display name.
# Sections get a circled-digit prefix (①–⑨) for visual grouping; identity
# / hero / scores use plain readable labels.
NOTION_NAMES = {
    # A. Identity
    'alias':                'alias',
    'country_vi':           'country (VI)',
    'country_en':           'country (EN)',
    'flag':                 'flag',
    'program_code':         'program code',
    'program_tag':          'program tag',
    'program_vi':           'program (VI)',
    'program_en':           'program (EN)',
    'source_filename':      'source filename',
    'wp_page_id':           'wp page id',
    'wp_slug':              'wp slug',
    'color_primary':        'color · primary',
    'color_secondary':      'color · secondary',
    'pb_status':            'status',

    # B. Hero
    'hero_bg_img':          'hero · bg img',
    'hero_breadcrumb_vi':   'hero · breadcrumb (VI)',
    'hero_breadcrumb_en':   'hero · breadcrumb (EN)',
    'hero_badge_vi':        'hero · badge (VI)',
    'hero_badge_en':        'hero · badge (EN)',
    'hero_title_top_vi':    'hero · title top (VI)',
    'hero_title_top_en':    'hero · title top (EN)',
    'hero_title_em_vi':     'hero · title em (VI)',
    'hero_title_em_en':     'hero · title em (EN)',
    'hero_desc_vi':         'hero · desc (VI)',
    'hero_desc_en':         'hero · desc (EN)',
    'hero_stats':           'hero · stats (JSON)',

    # NAC scores
    'nac_score':            'NAC score',
    'nac_score_label_vi':   'NAC score label (VI)',
    'nac_score_label_en':   'NAC score label (EN)',
    'score_invest':         'score · investment',
    'score_speed':          'score · speed',
    'score_lifestyle':      'score · lifestyle',
    'score_passport':       'score · passport',
    'score_tax':            'score · tax',
    'score_citizenship':    'score · citizenship',

    # Section 01 — Overview
    's01_subtitle_vi':           '① subtitle (VI)',
    's01_subtitle_en':           '① subtitle (EN)',
    's01_ov_cards':              '① overview cards (JSON)',
    's01_factcheck_vi':          '① factcheck (VI)',
    's01_factcheck_en':          '① factcheck (EN)',
    's01_article_cta_text_vi':   '① article CTA text (VI)',
    's01_article_cta_text_en':   '① article CTA text (EN)',
    's01_article_cta_url':       '① article CTA URL',

    # Section 02 — Investment
    's02_subtitle_vi':      '② subtitle (VI)',
    's02_subtitle_en':      '② subtitle (EN)',
    's02_warning_box_vi':   '② warning box (VI)',
    's02_warning_box_en':   '② warning box (EN)',
    's02_tiers':            '② tiers (JSON)',
    's02_nac_note_vi':      '② NAC note (VI)',
    's02_nac_note_en':      '② NAC note (EN)',

    # Section 03 — Process
    's03_subtitle_vi':      '③ subtitle (VI)',
    's03_subtitle_en':      '③ subtitle (EN)',
    's03_timeline':         '③ timeline (JSON)',

    # Section 04 — Family (LOCKED)
    's04_subtitle_vi':      '④ subtitle (VI)',
    's04_subtitle_en':      '④ subtitle (EN)',
    's04_family_cards':     '④ family cards (JSON)',
    's04_compare_note_vi':  '④ compare note (VI)',
    's04_compare_note_en':  '④ compare note (EN)',

    # Section 05 — Tax (LOCKED)
    's05_subtitle_vi':              '⑤ subtitle (VI)',
    's05_subtitle_en':              '⑤ subtitle (EN)',
    's05_tax_cards':                '⑤ tax cards (JSON)',
    's05_special_note_vi':          '⑤ special note (VI)',
    's05_special_note_en':          '⑤ special note (EN)',
    's05_inheritance_note_vi':      '⑤ inheritance note (VI)',
    's05_inheritance_note_en':      '⑤ inheritance note (EN)',

    # Section 06 — Citizenship (LOCKED)
    's06_subtitle_vi':                  '⑥ subtitle (VI)',
    's06_subtitle_en':                  '⑥ subtitle (EN)',
    's06_roadmap':                      '⑥ roadmap (JSON)',
    's06_dual_citizenship_note_vi':     '⑥ dual citizenship note (VI)',
    's06_dual_citizenship_note_en':     '⑥ dual citizenship note (EN)',
    's06_nac_strategy_note_vi':         '⑥ NAC strategy note (VI)',
    's06_nac_strategy_note_en':         '⑥ NAC strategy note (EN)',

    # Section 07 — Compare (LOCKED)
    's07_subtitle_vi':      '⑦ subtitle (VI)',
    's07_subtitle_en':      '⑦ subtitle (EN)',
    's07_compare_rows':     '⑦ compare rows (JSON)',
    's07_cta_text_vi':      '⑦ CTA text (VI)',
    's07_cta_text_en':      '⑦ CTA text (EN)',

    # Section 08 — Pros / Cons (LOCKED)
    's08_subtitle_vi':      '⑧ subtitle (VI)',
    's08_subtitle_en':      '⑧ subtitle (EN)',
    's08_pros':             '⑧ pros (JSON)',
    's08_cons':             '⑧ cons (JSON)',
    's08_risk_note_vi':     '⑧ risk note (VI)',
    's08_risk_note_en':     '⑧ risk note (EN)',

    # Section 09 — NAC verdict (LOCKED)
    's09_subtitle_vi':           '⑨ subtitle (VI)',
    's09_subtitle_en':           '⑨ subtitle (EN)',
    's09_recommendation_vi':     '⑨ recommendation (VI)',
    's09_recommendation_en':     '⑨ recommendation (EN)',
    's09_cta_heading_vi':        '⑨ CTA heading (VI)',
    's09_cta_heading_en':        '⑨ CTA heading (EN)',
    's09_cta_body_vi':           '⑨ CTA body (VI)',
    's09_cta_body_en':           '⑨ CTA body (EN)',
}

# Property name → Notion API type config.
# Notion API docs: https://developers.notion.com/reference/property-object
SCHEMA = {
    # ── A. Identity ────────────────────────────────────────────────────
    'alias':                {'title': {}},
    'country_vi':           {'rich_text': {}},
    'country_en':           {'rich_text': {}},
    'flag':                 {'rich_text': {}},
    'program_code':         {'select': {'options': [
        {'name': 'CBI', 'color': 'green'},
        {'name': 'RBI', 'color': 'blue'},
        {'name': 'LTR', 'color': 'purple'},
        {'name': 'CIP', 'color': 'pink'},
        {'name': 'MM2H', 'color': 'orange'},
    ]}},
    'program_tag':          {'rich_text': {}},
    'program_vi':           {'rich_text': {}},
    'program_en':           {'rich_text': {}},
    'source_filename':      {'rich_text': {}},
    'wp_page_id':           {'number': {'format': 'number'}},
    'wp_slug':              {'rich_text': {}},
    'color_primary':        {'rich_text': {}},
    'color_secondary':      {'rich_text': {}},
    'pb_status':            {'select': {'options': [
        {'name': 'Draft', 'color': 'gray'},
        {'name': 'Live', 'color': 'green'},
        {'name': 'Archived', 'color': 'red'},
    ]}},

    # ── B. Hero ────────────────────────────────────────────────────────
    'hero_bg_img':          {'url': {}},
    'hero_breadcrumb_vi':   {'rich_text': {}},
    'hero_breadcrumb_en':   {'rich_text': {}},
    'hero_badge_vi':        {'rich_text': {}},
    'hero_badge_en':        {'rich_text': {}},
    'hero_title_top_vi':    {'rich_text': {}},
    'hero_title_top_en':    {'rich_text': {}},
    'hero_title_em_vi':     {'rich_text': {}},
    'hero_title_em_en':     {'rich_text': {}},
    'hero_desc_vi':         {'rich_text': {}},
    'hero_desc_en':         {'rich_text': {}},
    'hero_stats':           {'rich_text': {}},   # JSON: [{num,lbl_vi,lbl_en},…]

    # ── B2. NAC scores ────────────────────────────────────────────────
    'nac_score':            {'number': {'format': 'number'}},
    'nac_score_label_vi':   {'rich_text': {}},
    'nac_score_label_en':   {'rich_text': {}},
    'score_invest':         {'number': {'format': 'number'}},
    'score_speed':          {'number': {'format': 'number'}},
    'score_lifestyle':      {'number': {'format': 'number'}},
    'score_passport':       {'number': {'format': 'number'}},
    'score_tax':            {'number': {'format': 'number'}},
    'score_citizenship':    {'number': {'format': 'number'}},

    # ── C. Section 01 — Overview ──────────────────────────────────────
    's01_subtitle_vi':      {'rich_text': {}},
    's01_subtitle_en':      {'rich_text': {}},
    's01_ov_cards':         {'rich_text': {}},   # JSON: [{icon,label_vi,label_en,value_vi,value_en,note_vi,note_en}]
    's01_factcheck_vi':     {'rich_text': {}},
    's01_factcheck_en':     {'rich_text': {}},
    's01_article_cta_text_vi': {'rich_text': {}},
    's01_article_cta_text_en': {'rich_text': {}},
    's01_article_cta_url':  {'url': {}},

    # ── D. Section 02 — Investment ────────────────────────────────────
    's02_subtitle_vi':      {'rich_text': {}},
    's02_subtitle_en':      {'rich_text': {}},
    's02_warning_box_vi':   {'rich_text': {}},
    's02_warning_box_en':   {'rich_text': {}},
    's02_tiers':            {'rich_text': {}},   # JSON: [{badge_vi,badge_en,amount,name_vi,name_en,region_vi,region_en,bar_pct,featured,tags_vi[],tags_en[]}]
    's02_nac_note_vi':      {'rich_text': {}},
    's02_nac_note_en':      {'rich_text': {}},

    # ── E. Section 03 — Process ───────────────────────────────────────
    's03_subtitle_vi':      {'rich_text': {}},
    's03_subtitle_en':      {'rich_text': {}},
    's03_timeline':         {'rich_text': {}},   # JSON: [{week_vi,week_en,title_vi,title_en,body_vi,body_en}]

    # ── F. Section 04 — Family (LOCKED) ───────────────────────────────
    's04_subtitle_vi':      {'rich_text': {}},
    's04_subtitle_en':      {'rich_text': {}},
    's04_family_cards':     {'rich_text': {}},   # JSON: [{icon,title_vi,title_en,note_vi,note_en}]
    's04_compare_note_vi':  {'rich_text': {}},
    's04_compare_note_en':  {'rich_text': {}},

    # ── G. Section 05 — Tax (LOCKED) ──────────────────────────────────
    's05_subtitle_vi':      {'rich_text': {}},
    's05_subtitle_en':      {'rich_text': {}},
    's05_tax_cards':        {'rich_text': {}},   # JSON: [{icon,label_vi,label_en,value_vi,value_en,note_vi,note_en}]
    's05_special_note_vi':  {'rich_text': {}},
    's05_special_note_en':  {'rich_text': {}},
    's05_inheritance_note_vi': {'rich_text': {}},
    's05_inheritance_note_en': {'rich_text': {}},

    # ── H. Section 06 — Citizenship (LOCKED) ──────────────────────────
    's06_subtitle_vi':      {'rich_text': {}},
    's06_subtitle_en':      {'rich_text': {}},
    's06_roadmap':          {'rich_text': {}},   # JSON: [{year_vi,year_en,dot,label_vi,label_en}]
    's06_dual_citizenship_note_vi': {'rich_text': {}},
    's06_dual_citizenship_note_en': {'rich_text': {}},
    's06_nac_strategy_note_vi':     {'rich_text': {}},
    's06_nac_strategy_note_en':     {'rich_text': {}},

    # ── I. Section 07 — Compare (LOCKED) ──────────────────────────────
    's07_subtitle_vi':      {'rich_text': {}},
    's07_subtitle_en':      {'rich_text': {}},
    's07_compare_rows':     {'rich_text': {}},   # JSON: [{flag,name_vi,name_en,min_invest,type_vi,type_en,mobility_vi,mobility_en,time_vi,time_en,score,highlight}]
    's07_cta_text_vi':      {'rich_text': {}},
    's07_cta_text_en':      {'rich_text': {}},

    # ── J. Section 08 — Pros / Cons (LOCKED) ──────────────────────────
    's08_subtitle_vi':      {'rich_text': {}},
    's08_subtitle_en':      {'rich_text': {}},
    's08_pros':             {'rich_text': {}},   # JSON: [{vi,en}]
    's08_cons':             {'rich_text': {}},   # JSON: [{vi,en}]
    's08_risk_note_vi':     {'rich_text': {}},
    's08_risk_note_en':     {'rich_text': {}},

    # ── K. Section 09 — NAC verdict (LOCKED) ──────────────────────────
    's09_subtitle_vi':      {'rich_text': {}},
    's09_subtitle_en':      {'rich_text': {}},
    's09_recommendation_vi': {'rich_text': {}},
    's09_recommendation_en': {'rich_text': {}},
    's09_cta_heading_vi':   {'rich_text': {}},
    's09_cta_heading_en':   {'rich_text': {}},
    's09_cta_body_vi':      {'rich_text': {}},
    's09_cta_body_en':      {'rich_text': {}},
}

# Sanity: every SCHEMA key has a display name and vice versa.
assert set(SCHEMA.keys()) == set(NOTION_NAMES.keys()), (
    f'NOTION_NAMES drift: missing {set(SCHEMA) - set(NOTION_NAMES)}, '
    f'extra {set(NOTION_NAMES) - set(SCHEMA)}'
)


# Fields that hold JSON-encoded arrays (validated by check_brochure_payload.py)
STRUCTURED_FIELDS = {
    'hero_stats':       {'item_keys': ['num', 'lbl_vi', 'lbl_en']},
    's01_ov_cards':     {'item_keys': ['icon', 'label_vi', 'label_en', 'value_vi', 'value_en', 'note_vi', 'note_en']},
    's02_tiers':        {'item_keys': ['badge_vi', 'badge_en', 'amount', 'name_vi', 'name_en', 'region_vi', 'region_en', 'bar_pct', 'featured', 'tags_vi', 'tags_en']},
    's03_timeline':     {'item_keys': ['week_vi', 'week_en', 'title_vi', 'title_en', 'body_vi', 'body_en']},
    's04_family_cards': {'item_keys': ['icon', 'title_vi', 'title_en', 'note_vi', 'note_en']},
    's05_tax_cards':    {'item_keys': ['icon', 'label_vi', 'label_en', 'value_vi', 'value_en', 'note_vi', 'note_en']},
    's06_roadmap':      {'item_keys': ['year_vi', 'year_en', 'dot', 'label_vi', 'label_en']},
    's07_compare_rows': {'item_keys': ['flag', 'name_vi', 'name_en', 'min_invest', 'type_vi', 'type_en', 'mobility_vi', 'mobility_en', 'time_vi', 'time_en', 'score', 'highlight']},
    's08_pros':         {'item_keys': ['vi', 'en']},
    's08_cons':         {'item_keys': ['vi', 'en']},
}
