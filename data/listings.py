"""Per-country live listings data for the brochure spotlight section.

Edit this file, then run:
    python tools/apply_listings.py

The script re-renders <!-- LISTINGS START --> ... <!-- LISTINGS END --> in
every brochure under Brochures html/. Each country gets up to 2 cards.
Empty `listings` list = both cards are placeholders. 1 listing = real
card + placeholder. 2 listings = two real cards (max).
"""

# alias must match keys in sync_brochures.py BROCHURES dict.
LISTINGS = {
    'turkey': {
        'flag':         '🇹🇷',
        'country_vi':   'Thổ Nhĩ Kỳ',
        'program_code': 'CBI',
        'listings': [
            {
                'ref':         'NAC-79',
                'url':         'https://nomadassetcollective.com/property-hub-bat-dong-san/turkey/w-suite-istanbul/',
                'image':       'https://nomadassetcollective.com/wp-content/uploads/2026/05/W1.webp',
                'image_alt':   'W Suite Istanbul — căn hộ dịch vụ branded tại trung tâm Istanbul',
                'badge_city':  'Istanbul',
                'brand':       'W Hotels',
                'brand_owner': 'Marriott International',
                'name':        'W Suite Istanbul',
                'location':    '📍 Şişli / Levent · CBD mới · Istanbul, Thổ Nhĩ Kỳ',
                'price':       '$572,300',
                'yield_pct':   '11.0%',
                'irr_pct':     '20.0%',
                'handover':    'Q4 2026',
                'desc':        'Căn hộ dịch vụ 5 sao do W Hotels vận hành tại CBD mới của Istanbul. 77–90m², revenue pool, 15 ngày sử dụng cá nhân/năm. Đủ điều kiện CBI từ $400,000.',
            },
        ],
    },
    'portugal':   {'flag': '🇵🇹', 'country_vi': 'Bồ Đào Nha',     'program_code': 'RBI', 'listings': []},
    'greece':     {'flag': '🇬🇷', 'country_vi': 'Hy Lạp',          'program_code': 'RBI', 'listings': []},
    'cyprus':     {'flag': '🇨🇾', 'country_vi': 'Đảo Síp',         'program_code': 'RBI', 'listings': []},
    'uae':        {'flag': '🇦🇪', 'country_vi': 'UAE',             'program_code': 'RBI', 'listings': []},
    'uk':         {'flag': '🇬🇧', 'country_vi': 'Anh Quốc',        'program_code': 'RBI', 'listings': []},
    'malta':      {'flag': '🇲🇹', 'country_vi': 'Malta',           'program_code': 'RBI', 'listings': []},
    'stkitts':    {'flag': '🇰🇳', 'country_vi': 'St. Kitts & Nevis','program_code': 'CBI', 'listings': []},
    'thailand':   {'flag': '🇹🇭', 'country_vi': 'Thái Lan',        'program_code': 'LTR', 'listings': []},
    'newzealand': {'flag': '🇳🇿', 'country_vi': 'New Zealand',     'program_code': 'RBI', 'listings': []},
    'panama':     {'flag': '🇵🇦', 'country_vi': 'Panama',          'program_code': 'RBI', 'listings': []},
    'malaysia':   {'flag': '🇲🇾', 'country_vi': 'Malaysia',        'program_code': 'RBI', 'listings': []},
}
