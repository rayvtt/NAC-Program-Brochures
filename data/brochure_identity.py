"""Per-brochure identity metadata for the Notion DB.

Single source of truth for: WP page/slug, flag, country names, program
classification, color theme, Notion page cover. Used by extract / push
tools to populate fields that are NOT extractable from the brochure HTML
itself (or that exist in the HTML but are noisy to parse).

Color values can be overridden here per country, but the extract script
will also parse :root --country / --country2 from the HTML and use
those when this dict's color fields are empty.
"""

IDENTITY = {
    'portugal': {
        'flag':            '🇵🇹',
        'country_vi':      'Bồ Đào Nha',
        'country_en':      'Portugal',
        'program_code':    'RBI',
        'program_tag':     'RBI · Bồ Đào Nha',
        'program_vi':      'Bồ Đào Nha Golden Visa',
        'program_en':      'Portugal Golden Visa',
        'source_filename': 'portugal-gv.html',
        'wp_page_id':      1848,
        'wp_slug':         'chuong-trinh-bo-dao-nha-golden-visa',
        'cover':           'https://images.unsplash.com/photo-1555881400-74d7acaacd8b?w=1500&q=80',  # Lisbon
    },
    'greece': {
        'flag':            '🇬🇷',
        'country_vi':      'Hy Lạp',
        'country_en':      'Greece',
        'program_code':    'RBI',
        'program_tag':     'RBI · Hy Lạp',
        'program_vi':      'Hy Lạp Golden Visa',
        'program_en':      'Greece Golden Visa',
        'source_filename': 'greece-rbi_1_2.html',
        'wp_page_id':      1827,
        'wp_slug':         'residences-chuong-trinh-hy-lap-golden-visa',
        'cover':           'https://images.unsplash.com/photo-1503152394-c571994fd383?w=1500&q=80',  # Santorini
    },
    'cyprus': {
        'flag':            '🇨🇾',
        'country_vi':      'Đảo Síp',
        'country_en':      'Cyprus',
        'program_code':    'RBI',
        'program_tag':     'RBI · Đảo Síp',
        'program_vi':      'Đảo Síp PR',
        'program_en':      'Cyprus PR',
        'source_filename': 'cyprus-rbi_3_3.html',
        'wp_page_id':      1844,
        'wp_slug':         'chuong-trinh-dao-sip-rbi-residence-by-investment',
        'cover':           'https://images.unsplash.com/photo-1571989569010-b76a8b3eed95?w=1500&q=80',  # Cyprus coast
    },
    'turkey': {
        'flag':            '🇹🇷',
        'country_vi':      'Thổ Nhĩ Kỳ',
        'country_en':      'Turkey',
        'program_code':    'CBI',
        'program_tag':     'CBI · Thổ Nhĩ Kỳ',
        'program_vi':      'Thổ Nhĩ Kỳ CBI',
        'program_en':      'Turkey CBI',
        'source_filename': 'turkey-cbi_8.html',
        'wp_page_id':      1836,
        'wp_slug':         'chuong-trinh-tho-nhi-ky-cbi-citizenship-by-investment',
        'cover':           'https://images.unsplash.com/photo-1541432901042-2d8bd64b4a9b?w=1500&q=80',  # Istanbul
    },
    'uae': {
        'flag':            '🇦🇪',
        'country_vi':      'UAE',
        'country_en':      'United Arab Emirates',
        'program_code':    'RBI',
        'program_tag':     'RBI · UAE',
        'program_vi':      'UAE Golden Visa',
        'program_en':      'UAE Golden Visa',
        'source_filename': 'uae-rbi_1_7.html',
        'wp_page_id':      1901,
        'wp_slug':         'chuong-trinh-uae-golden-visa-2',
        'cover':           'https://images.unsplash.com/photo-1512453979798-5ea266f8880c?w=1500&q=80',  # Dubai Burj
    },
    'uk': {
        'flag':            '🇬🇧',
        'country_vi':      'Anh Quốc',
        'country_en':      'United Kingdom',
        'program_code':    'RBI',
        'program_tag':     'RBI · Anh Quốc',
        'program_vi':      'Anh Quốc Innovator Founder',
        'program_en':      'UK Innovator Founder',
        'source_filename': 'uk-rbi_1 (2).html',
        'wp_page_id':      1932,
        'wp_slug':         'chuong-trinh-uk-thuong-tru-visa-dau-tu-rbi',
        'cover':           'https://images.unsplash.com/photo-1513635269975-59663e0ac1ad?w=1500&q=80',  # London
    },
    'malta': {
        'flag':            '🇲🇹',
        'country_vi':      'Malta',
        'country_en':      'Malta',
        'program_code':    'RBI',
        'program_tag':     'RBI · Malta',
        'program_vi':      'Malta MPRP',
        'program_en':      'Malta MPRP',
        'source_filename': 'malta-rbi_1_3.html',
        'wp_page_id':      1924,
        'wp_slug':         'chuong-trinh-malta-thuong-tru-nhan-rbi',
        'cover':           'https://images.unsplash.com/photo-1583509711473-c1bfa5dfba2c?w=1500&q=80',  # Valletta
    },
    'stkitts': {
        'flag':            '🇰🇳',
        'country_vi':      'St. Kitts & Nevis',
        'country_en':      'St. Kitts & Nevis',
        'program_code':    'CBI',
        'program_tag':     'CBI · St. Kitts & Nevis',
        'program_vi':      'St. Kitts & Nevis CBI',
        'program_en':      'St. Kitts & Nevis CBI',
        'source_filename': 'stkitts-nevis.html',
        'wp_page_id':      1921,
        'wp_slug':         'chuong-trinh-si-kitts-nevis-quoc-tich',
        'cover':           'https://images.unsplash.com/photo-1535320903710-d993d3d77d29?w=1500&q=80',  # Caribbean
    },
    'thailand': {
        'flag':            '🇹🇭',
        'country_vi':      'Thái Lan',
        'country_en':      'Thailand',
        'program_code':    'LTR',
        'program_tag':     'LTR · Thái Lan',
        'program_vi':      'Thái Lan LTR',
        'program_en':      'Thailand LTR',
        'source_filename': 'thailand-rbi_1 (2).html',
        'wp_page_id':      1926,
        'wp_slug':         'chuong-trinh-thai-lan-cu-tru-dai-han-ltr-rbi',
        'cover':           'https://images.unsplash.com/photo-1508009603885-50cf7c579365?w=1500&q=80',  # Bangkok
    },
    'newzealand': {
        'flag':            '🇳🇿',
        'country_vi':      'New Zealand',
        'country_en':      'New Zealand',
        'program_code':    'RBI',
        'program_tag':     'RBI · New Zealand',
        'program_vi':      'New Zealand Active Investor Plus',
        'program_en':      'New Zealand Active Investor Plus',
        'source_filename': 'newzealand-rbi_1 (3).html',
        'wp_page_id':      1944,
        'wp_slug':         'chuong-trinh-new-zealand-rbi-dau-tu-di-tru',
        'cover':           'https://images.unsplash.com/photo-1469854523086-cc02fe5d8800?w=1500&q=80',  # NZ Wanaka
    },
    'panama': {
        'flag':            '🇵🇦',
        'country_vi':      'Panama',
        'country_en':      'Panama',
        'program_code':    'RBI',
        'program_tag':     'RBI · Panama',
        'program_vi':      'Panama RBI',
        'program_en':      'Panama RBI',
        'source_filename': 'panama-rbi_.html',
        'wp_page_id':      1996,
        'wp_slug':         'chuong-trinh-panama-rbi-quyen-cu-tru-vinh-vien',
        'cover':           'https://images.unsplash.com/photo-1554486007-bd17f7af6f04?w=1500&q=80',  # Panama City
    },
    'malaysia': {
        'flag':            '🇲🇾',
        'country_vi':      'Malaysia',
        'country_en':      'Malaysia',
        'program_code':    'RBI',
        'program_tag':     'RBI · Malaysia',
        'program_vi':      'Malaysia MM2H',
        'program_en':      'Malaysia MM2H',
        'source_filename': 'malaysia-mm2h.html',
        'wp_page_id':      2024,
        'wp_slug':         'chuong-trinh-malaysia-rbi-mm2h-dau-tu-quyen-cu-tru',
        'cover':           'https://images.unsplash.com/photo-1596422846543-75c6fc197f07?w=1500&q=80',  # KL Twin Towers
    },
    'antigua': {
        'flag':            '🇦🇬',
        'country_vi':      'Antigua & Barbuda',
        'country_en':      'Antigua & Barbuda',
        'program_code':    'CBI',
        'program_tag':     'CBI · Antigua & Barbuda',
        'program_vi':      'Antigua & Barbuda CBI',
        'program_en':      'Antigua & Barbuda CBI',
        'source_filename': 'antigua-cbi.html',
        'wp_page_id':      2158,
        'wp_slug':         'chuong-trinh-antigua-barbuda-cbi',
        'cover':           'https://images.unsplash.com/photo-1559827260-dc66d52bef19?w=1500&q=80',  # Caribbean coastline
    },
}


def alias_with_flag(alias_key):
    """Computed alias title value: '🇹🇷 turkey' style."""
    flag = IDENTITY[alias_key]['flag']
    return f'{flag} {alias_key}'
