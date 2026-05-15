"""Per-brochure nav-right link configuration.

The nav-right region on each brochure shows the link items between the
brand mark and the language toggle. Turkey has its own set; the other
11 share a default. To change a link across all brochures, edit DEFAULT
below and run `python tools/apply_nav.py`.

Pairs are (label, href). Order is the display order in the nav.
"""

NAC_INDEX    = ('NAC Index',    'https://nomadassetcollective.com/nac-residence-index/')
SO_SANH      = ('So Sánh',      'https://nomadassetcollective.com/so-sanh/')
PROPERTY_HUB = ('Property Hub', 'https://nomadassetcollective.com/property-hub/')
BLOG         = ('Blog',         'https://blog.nomadassetcollective.com/')

DEFAULT = [NAC_INDEX, PROPERTY_HUB, BLOG]

LINKS_BY_ALIAS = {
    'portugal':   DEFAULT,
    'greece':     DEFAULT,
    'cyprus':     DEFAULT,
    'uae':        DEFAULT,
    'uk':         DEFAULT,
    'malta':      DEFAULT,
    'stkitts':    DEFAULT,
    'thailand':   DEFAULT,
    'newzealand': DEFAULT,
    'panama':     DEFAULT,
    'malaysia':   DEFAULT,
    'turkey':     [NAC_INDEX, SO_SANH, PROPERTY_HUB],
}
