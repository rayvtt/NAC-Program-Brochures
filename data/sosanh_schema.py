"""Schema for [🔀 NAC - So Sánh Data] Notion DB (id 6383f817314241a1abbabee6b1be7409).

Single source of truth shared across:
  tools/pull_sosanh_from_notion.py   Notion → data/sosanh_payload.json
  tools/patch_sosanh_snap.py         payload → var DB_STATIC in NAC-SO-SANH.html

One row per country (14 today, gated by `live in picker`). Every prose
field is a real, independently-authored VI/EN pair — `<key> (VI)` /
`<key> (EN)` — no machine translation, no positional column mapping.
Numeric fields (gdp, infl, debt, vat, vfree, the rt* rating scores) are
plain Notion `number` properties, already display-scale (a field showing
"24%" in the tool is stored as the number 24, not 0.24).

Adding a country: create a page in the Notion DB with `code` set to a
new, globally-unique 2-letter identifier (checked — `code` collisions
silently overwrite one country's row with another's in the client's
findCountry() lookup) and `live in picker` ticked once its data is real.
"""

NOTION_DB_ID = '6383f817314241a1abbabee6b1be7409'

# ── Identity (no VI/EN split) ──────────────────────────────────────────
IDENTITY_NAMES = {
    'code':          'code',
    'vi':            'country (VI)',   # Notion title property
    'en':            'country (EN)',
    'flag':          'flag',
    'liveInPicker':  'live in picker',
    'sortOrder':     'sort order',
    'bloc':          '① bloc',         # multi_select
}

# ── Bilingual text fields — technical key → Notion property PREFIX ─────
# Actual Notion property names are '<prefix> (VI)' / '<prefix> (EN)'.
TEXT_FIELDS = {
    'econ':       '① econ',
    'rank':       '① rank',
    'nDiv':       '② need · div',
    'nEdu':       '② need · edu',
    'nGlobal':    '② need · global',
    'nHealth':    '② need · health',
    'nMove':      '② need · move',
    'nQol':       '② need · qol',
    'nSafe':      '② need · safe',
    'nTax':       '② need · tax',
    'curr':       '③ curr',
    'capEcon':    '③ capEcon',
    'econChar':   '③ econChar',
    'infra':      '③ infra',
    'tourism':    '③ tourism',
    'othNews':    '③ othNews',
    'pit':        '④ pit',
    'cit':        '④ cit',
    'inherit':    '④ inherit',
    'bankSafe':   '④ bankSafe',
    'fx':         '④ fx',
    'prog':       '⑤ prog',
    'progInv':    '⑤ progInv',
    'minCost':    '⑤ minCost',
    'renew':      '⑤ renew',
    'stay':       '⑤ stay',
    'citiz':      '⑤ citiz',
    'sof':        '⑤ sof',
    'sponsor':    '⑥ sponsor',
    'deps':       '⑥ deps',
    'addMem':     '⑥ addMem',
    'heir':       '⑥ heir',
    'dual':       '⑥ dual',
    'mobility':   '⑥ mobility',
    'e2':         '⑥ e2',
    'growth':     '⑦ growth',
    'liquid':     '⑦ liquid',
    'maintain':   '⑦ maintain',
    'feeInit':    '⑧ feeInit',
    'feeGov':     '⑧ feeGov',
    'feeDD':      '⑧ feeDD',
    'feeAnnual':  '⑧ feeAnnual',
    'feeTotal1':  '⑧ feeTotal1',
    'feeTotal2':  '⑧ feeTotal2',
    'feeNote':    '⑧ feeNote',
    'r1':         '⑨ r1',
    'r2':         '⑨ r2',
    'r3':         '⑨ r3',
    'r4':         '⑨ r4',
    'r5':         '⑨ r5',
}

# ── Plain number fields — technical key → Notion property name ─────────
NUM_FIELDS = {
    'gdp':       '① gdp',
    'infl':      '① infl',
    'debt':      '① debt',
    'polstab':   '① polstab',
    'corrupt':   '① corrupt',
    'vat':       '④ vat',
    'vfree':     '⑥ vfree',
    'rtCost':    '⑩ rtCost',
    'rtEdu':     '⑩ rtEdu',
    'rtGlobal':  '⑩ rtGlobal',
    'rtMove':    '⑩ rtMove',
    'rtHealth':  '⑩ rtHealth',
    'rtQol':     '⑩ rtQol',
    'rtSafe':    '⑩ rtSafe',
    'rtDiv':     '⑩ rtDiv',
    'rtTax':     '⑩ rtTax',
}

# NEED_DIMS pairs each §02 need field with its own §10 rating field —
# mirrors NEED_DIMS in NAC-SO-SANH.html exactly (must stay in sync by hand;
# the client hardcodes the dimension icons/labels, only the values move).
NEED_TO_RATING = {
    'nEdu': 'rtEdu', 'nGlobal': 'rtGlobal', 'nMove': 'rtMove', 'nHealth': 'rtHealth',
    'nQol': 'rtQol', 'nSafe': 'rtSafe', 'nDiv': 'rtDiv', 'nTax': 'rtTax',
}
