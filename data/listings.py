"""Per-country listing selection for the brochure spotlight section.

Each country lists Property Hub URLs (max 2) that should appear in its
brochure's Live Listings spotlight. Stats, images, descriptions are
fetched LIVE from each Property Hub page at render time — those listings
already expose structured `data-notion="<field>"` attributes (sourced
from the upstream Notion CRM), so the brochure card always shows what
PH currently says.

Edit this file when:
  - A new listing should appear in a brochure (add its PH URL)
  - A listing should rotate out (remove its URL)

Don't edit this file for:
  - Price / yield / IRR / handover changes (live from PH)
  - Image swaps (live from PH)
  - Copy / description tweaks (live from PH — edit at the Notion source)

Then run:  python tools/apply_listings.py
"""

# alias must match keys in sync_brochures.py BROCHURES.
LISTINGS = {
    'turkey': {
        'flag':         '🇹🇷',
        'country_vi':   'Thổ Nhĩ Kỳ',
        'program_code': 'CBI',
        'urls': [
            'https://nomadassetcollective.com/property-hub-bat-dong-san/turkey/w-suite-istanbul/',
        ],
    },
    'portugal':   {'flag': '🇵🇹', 'country_vi': 'Bồ Đào Nha',      'program_code': 'RBI', 'urls': []},
    'greece':     {'flag': '🇬🇷', 'country_vi': 'Hy Lạp',           'program_code': 'RBI', 'urls': []},
    'cyprus':     {'flag': '🇨🇾', 'country_vi': 'Đảo Síp',          'program_code': 'RBI', 'urls': []},
    'uae':        {'flag': '🇦🇪', 'country_vi': 'UAE',              'program_code': 'RBI', 'urls': []},
    'uk':         {'flag': '🇬🇧', 'country_vi': 'Anh Quốc',         'program_code': 'RBI', 'urls': []},
    'malta':      {'flag': '🇲🇹', 'country_vi': 'Malta',            'program_code': 'RBI', 'urls': []},
    'stkitts':    {'flag': '🇰🇳', 'country_vi': 'St. Kitts & Nevis','program_code': 'CBI', 'urls': []},
    'thailand':   {'flag': '🇹🇭', 'country_vi': 'Thái Lan',         'program_code': 'LTR', 'urls': []},
    'newzealand': {'flag': '🇳🇿', 'country_vi': 'New Zealand',      'program_code': 'RBI', 'urls': []},
    'panama':     {'flag': '🇵🇦', 'country_vi': 'Panama',           'program_code': 'RBI', 'urls': []},
    'malaysia':   {'flag': '🇲🇾', 'country_vi': 'Malaysia',         'program_code': 'RBI', 'urls': []},
}
