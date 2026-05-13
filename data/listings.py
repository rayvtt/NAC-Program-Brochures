"""Per-country mapping for the brochure spotlight section.

All listing data now comes live from Notion via the public Property Hub
worker endpoint:
    https://nac-property-hub.ray-vtt.workers.dev/properties

This file only maps each brochure alias to which Notion country it
should filter on, and its program code (CBI / RBI / LTR). The generator
takes care of:
  - enumerating listings for that country
  - applying Rule 1 (cheapest + priciest when > 2 candidates)
  - applying Rule 2 (biweekly rotation, biased to different hub_type)
  - fetching the PDP page for each selected listing (rich detail like
    desc_vi, district, handover)

To add curation overrides (e.g. force a specific NAC-XX to appear in a
brochure), append a `pin` list of integer IDs.
"""

COUNTRIES = {
    'turkey':     {'notion_country': 'Thổ Nhĩ Kỳ',                 'program_code': 'CBI'},
    'portugal':   {'notion_country': 'Bồ Đào Nha',                 'program_code': 'RBI'},
    'greece':     {'notion_country': 'Hy Lạp',                     'program_code': 'RBI'},
    'cyprus':     {'notion_country': 'Đảo Síp',                    'program_code': 'RBI'},
    'uae':        {'notion_country': ['UAE', 'Dubai', 'Abu Dhabi'],'program_code': 'RBI'},
    'uk':         {'notion_country': 'Anh Quốc',                   'program_code': 'RBI'},
    'malta':      {'notion_country': 'Malta',                      'program_code': 'RBI'},
    'stkitts':    {'notion_country': 'St Kitts',                   'program_code': 'CBI'},
    'thailand':   {'notion_country': 'Thái Lan',                   'program_code': 'LTR'},
    'newzealand': {'notion_country': 'New Zealand',                'program_code': 'RBI'},
    'panama':     {'notion_country': 'Panama',                     'program_code': 'RBI'},
    'malaysia':   {'notion_country': 'Malaysia',                   'program_code': 'RBI'},
}
