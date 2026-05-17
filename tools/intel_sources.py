"""Source configuration for the weekly investment-migration intel pipeline.

For each of the 12 brochure countries we list the URLs the daily scraper
should poll. Source authority ranking is used by the digest step to
weight signals (3 = official gov, 2 = industry press / agency, 1 = community).

Adding a country / source: append to COUNTRY_SOURCES below. Reddit subs
are listed separately because we hit them via the public JSON API
(no HTML parsing).

Each source entry: (name, url, authority, kind)
  kind ∈ {'html', 'rss', 'reddit_json'}
"""
from __future__ import annotations

# Subs that frequently surface investment-migration signals.
# We query each sub's search.json endpoint for country-specific keywords.
REDDIT_SUBS = [
    'iwantout',
    'expats',
    'AmerExit',
    'IWantToLeave',
    'NomadCapitalist',
    'henleypassportindex',
    'GoldenVisa',
]


# Generic industry press — searched per-country.
INDUSTRY_PRESS = [
    # (name, search-url-template-with-{q}, authority, kind)
    ('IMI Daily',                   'https://www.imidaily.com/?s={q}',                                  2, 'html'),
    ('IMI Daily (feed)',            'https://www.imidaily.com/feed/',                                   2, 'rss'),
    ('Investment Migration Council', 'https://investmentmigration.org/?s={q}',                          2, 'html'),
]


# Per-country source list. The keywords feed Reddit + industry-press searches.
# `official` and `agency` are direct page polls (no search).
COUNTRY_SOURCES = {
    'turkey': {
        'keywords': ['turkey CBI', 'turkish citizenship', 'turkey investor visa'],
        'reddit_terms': ['turkey CBI', 'turkish citizenship'],
        'official': [
            ('Turkish DGMM', 'https://en.goc.gov.tr/turkish-citizenship', 3, 'html'),
        ],
        'agency': [
            ('Henley · Turkey',     'https://www.henleyglobal.com/citizenship-investment/turkey', 2, 'html'),
            ('Latitude · Turkey',   'https://latitudeworld.com/global-residence-and-citizenship/turkey-citizenship-by-investment/', 2, 'html'),
            ('CS Global · Turkey',  'https://csglobalpartners.com/programmes/turkey-citizenship-by-investment/', 2, 'html'),
        ],
    },
    'portugal': {
        'keywords': ['portugal golden visa', 'portugal D7', 'portugal ARI'],
        'reddit_terms': ['portugal golden visa', 'portugal D7'],
        'official': [
            ('AIMA · Portugal',     'https://aima.gov.pt/en/viver/autorizacao-de-residencia/para-investidores-ari', 3, 'html'),
        ],
        'agency': [
            ('Henley · Portugal',   'https://www.henleyglobal.com/residence-investment/portugal', 2, 'html'),
            ('Latitude · Portugal', 'https://latitudeworld.com/global-residence-and-citizenship/portugal-golden-residence-permit/', 2, 'html'),
            ('Get Golden Visa',     'https://getgoldenvisa.com/portugal-golden-visa', 2, 'html'),
        ],
    },
    'greece': {
        'keywords': ['greece golden visa', 'greece residence permit investor'],
        'reddit_terms': ['greece golden visa'],
        'official': [
            ('Enterprise Greece',   'https://www.enterprisegreece.gov.gr/en/golden-visa-en', 3, 'html'),
        ],
        'agency': [
            ('Henley · Greece',     'https://www.henleyglobal.com/residence-investment/greece', 2, 'html'),
            ('Latitude · Greece',   'https://latitudeworld.com/global-residence-and-citizenship/greece-golden-visa-program/', 2, 'html'),
        ],
    },
    'cyprus': {
        'keywords': ['cyprus residence permit investor', 'cyprus PR investment'],
        'reddit_terms': ['cyprus residence', 'cyprus PR'],
        'official': [
            ('Cyprus Migration Dept', 'https://www.moi.gov.cy/moi/CRMD/CRMD.nsf/page04_en/page04_en?OpenDocument', 3, 'html'),
        ],
        'agency': [
            ('Henley · Cyprus',     'https://www.henleyglobal.com/residence-investment/cyprus', 2, 'html'),
            ('Latitude · Cyprus',   'https://latitudeworld.com/global-residence-and-citizenship/cyprus-residency-by-investment/', 2, 'html'),
        ],
    },
    'uae': {
        'keywords': ['UAE golden visa', 'dubai investor visa', 'abu dhabi residency'],
        'reddit_terms': ['UAE golden visa', 'dubai investor visa'],
        'official': [
            ('UAE Government Portal', 'https://u.ae/en/information-and-services/visa-and-emirates-id/types-of-visa/long-term-visa-options', 3, 'html'),
        ],
        'agency': [
            ('Henley · UAE',        'https://www.henleyglobal.com/residence-investment/united-arab-emirates', 2, 'html'),
            ('Latitude · UAE',      'https://latitudeworld.com/global-residence-and-citizenship/united-arab-emirates-uae-golden-visa/', 2, 'html'),
        ],
    },
    'uk': {
        'keywords': ['UK innovator founder visa', 'UK investor visa'],
        'reddit_terms': ['UK innovator founder', 'UK investor visa'],
        'official': [
            ('UK Gov · Innovator Founder', 'https://www.gov.uk/innovator-founder-visa', 3, 'html'),
        ],
        'agency': [
            ('Henley · UK',         'https://www.henleyglobal.com/residence-investment/united-kingdom', 2, 'html'),
            ('Latitude · UK',       'https://latitudeworld.com/global-residence-and-citizenship/united-kingdom-investor-visa/', 2, 'html'),
        ],
    },
    'malta': {
        'keywords': ['malta MPRP', 'malta permanent residence programme'],
        'reddit_terms': ['malta MPRP', 'malta residence'],
        'official': [
            ('Residency Malta',     'https://residencymalta.gov.mt/the-malta-permanent-residence-programme/', 3, 'html'),
        ],
        'agency': [
            ('Henley · Malta',      'https://www.henleyglobal.com/residence-investment/malta', 2, 'html'),
            ('Latitude · Malta',    'https://latitudeworld.com/global-residence-and-citizenship/malta-permanent-residency-programme/', 2, 'html'),
            ('CS Global · Malta',   'https://csglobalpartners.com/programmes/malta-permanent-residency/', 2, 'html'),
        ],
    },
    'stkitts': {
        'keywords': ['st kitts CBI', 'saint kitts citizenship', 'SKN CBI'],
        'reddit_terms': ['st kitts CBI', 'saint kitts citizenship'],
        'official': [
            ('St Kitts CIU',        'https://www.ciu.gov.kn/', 3, 'html'),
        ],
        'agency': [
            ('Henley · St Kitts',   'https://www.henleyglobal.com/citizenship-investment/st-kitts-nevis', 2, 'html'),
            ('Latitude · St Kitts', 'https://latitudeworld.com/global-residence-and-citizenship/st-kitts-nevis-citizenship-by-investment/', 2, 'html'),
            ('CS Global · St Kitts', 'https://csglobalpartners.com/programmes/st-kitts-nevis-citizenship-by-investment/', 2, 'html'),
        ],
    },
    'thailand': {
        'keywords': ['thailand LTR visa', 'thailand long term resident'],
        'reddit_terms': ['thailand LTR', 'thailand long term resident'],
        'official': [
            ('Thailand BOI · LTR',  'https://ltr.boi.go.th/', 3, 'html'),
        ],
        'agency': [
            ('Henley · Thailand',   'https://www.henleyglobal.com/residence-investment/thailand', 2, 'html'),
            ('Latitude · Thailand', 'https://latitudeworld.com/global-residence-and-citizenship/thailand-long-term-resident-visa/', 2, 'html'),
        ],
    },
    'newzealand': {
        'keywords': ['new zealand active investor plus', 'new zealand investor visa'],
        'reddit_terms': ['new zealand active investor', 'new zealand investor visa'],
        'official': [
            ('Immigration NZ · AIP', 'https://www.immigration.govt.nz/new-zealand-visas/apply-for-a-visa/about-visa/active-investor-plus-visa', 3, 'html'),
        ],
        'agency': [
            ('Henley · NZ',         'https://www.henleyglobal.com/residence-investment/new-zealand', 2, 'html'),
            ('Latitude · NZ',       'https://latitudeworld.com/global-residence-and-citizenship/new-zealand-active-investor-plus-visa/', 2, 'html'),
        ],
    },
    'panama': {
        'keywords': ['panama friendly nations', 'panama investor visa', 'panama qualified investor'],
        'reddit_terms': ['panama investor visa', 'panama friendly nations'],
        'official': [
            ('Panama Migration',    'https://www.migracion.gob.pa/inicio/permisos-y-visas', 3, 'html'),
        ],
        'agency': [
            ('Henley · Panama',     'https://www.henleyglobal.com/residence-investment/panama', 2, 'html'),
            ('Latitude · Panama',   'https://latitudeworld.com/global-residence-and-citizenship/panama-qualified-investor-program/', 2, 'html'),
        ],
    },
    'malaysia': {
        'keywords': ['malaysia MM2H', 'malaysia my second home', 'malaysia premium visa'],
        'reddit_terms': ['malaysia MM2H', 'malaysia premium visa'],
        'official': [
            ('MM2H Official',       'https://mm2h.gov.my/', 3, 'html'),
        ],
        'agency': [
            ('Henley · Malaysia',   'https://www.henleyglobal.com/residence-investment/malaysia', 2, 'html'),
            ('Latitude · Malaysia', 'https://latitudeworld.com/global-residence-and-citizenship/malaysia-my-second-home-mm2h/', 2, 'html'),
        ],
    },
}


# Sanity: keys here must match `data/<alias>_payload.json` filenames.
ALL_ALIASES = list(COUNTRY_SOURCES.keys())
