#!/usr/bin/env python3
"""Diff the previous vs current data/sosanh_payload.json (via git) and
append a human-readable entry to SOSANH-SYNC-LOG.md — the durable record
of what the fortnightly Notion sync actually changed.

ALSO maintains the per-field freshness ledger: every country in the
payload gets an `_updated` map ({field_key: "DD/MM/YYYY"}) recording when
that field last actually changed. tools/patch_sosanh_snap.py embeds this
straight into var DB_STATIC, and NAC-SO-SANH.html renders a small hoverable
dot on every row/card showing that date — "highlighted" when it matches the
sync's own asOf (i.e. touched in the run that just landed). A field with a
real value but no prior `_updated` entry (first run after this feature
shipped, or a brand-new field) is baseline-stamped with today's date rather
than left blank — every visible row always has a real "last confirmed" date.
This is why patch_sosanh_snap.py must run AFTER this script in the pipeline,
not before — see pull-sosanh-notion.yml's step order.

Also posts the same digest to NOTIFY_WEBHOOK if that env var is set (a
Google Chat incoming-webhook URL — same shape nac-marketing-omnichannel's
scripts/notify.mjs already posts to, so Ray sees So Sánh sync activity in
the same channel as the rest of NAC's automation). Silently skipped if
the secret isn't configured — this script's job is done either way once
the log file is written; the webhook is a nice-to-have, not a dependency.

Run (from the repo root, after tools/pull_sosanh_from_notion.py has
already updated data/sosanh_payload.json on disk but BEFORE it's
committed — this script reads the pre-commit git diff, then rewrites
data/sosanh_payload.json in place to add/bump the `_updated` ledger):

    python tools/sosanh_changelog.py
"""
import datetime
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from data.sosanh_schema import NUM_FIELDS, TEXT_FIELDS  # noqa: E402

PAYLOAD_PATH = ROOT / 'data' / 'sosanh_payload.json'
LOG_PATH = ROOT / 'SOSANH-SYNC-LOG.md'

# Only fields actually rendered as a row/card in NAC-SO-SANH.html get a
# freshness dot — identity fields (code/vi/en/flag/sortOrder/bloc/…) aren't
# "data" a viewer would ask "when was this updated" about.
TRACKED_FIELDS = set(TEXT_FIELDS) | set(NUM_FIELDS)

# Human labels for the fields most worth calling out by name in the digest —
# everything else still counts toward the per-country changed-field total,
# just without an inline label (keeps the digest short even on a big sync).
NOTABLE_FIELDS = {
    'gdp': 'GDP growth', 'infl': 'inflation', 'debt': 'public debt',
    'vat': 'VAT', 'cit': 'corporate tax', 'vfree': 'visa-free count',
    'feeTotal1': 'total cost (1 applicant)', 'feeTotal2': 'total cost (2+ applicants)',
    'minCost': 'minimum investment',
}


def git_show_head(path):
    """The version of `path` as last committed (before this run's pull
    wrote the new one to disk) — '' if the file is new / has no history."""
    try:
        out = subprocess.run(
            ['git', 'show', f'HEAD:{path}'],
            cwd=ROOT, capture_output=True, text=True, check=True,
        )
        return out.stdout
    except subprocess.CalledProcessError:
        return ''


def flatten(country):
    """{'gdp': 2.2, 'r1': {'vi':'a','en':'b'}, ...} -> {'gdp': 2.2, 'r1.vi': 'a', 'r1.en': 'b'}
    Skips `_updated` — that's the freshness ledger this script itself
    maintains, not Notion content, and diffing it against itself would be
    circular (every run would "detect" its own previous stamps as changes)."""
    out = {}
    for k, v in country.items():
        if k == '_updated':
            continue
        if isinstance(v, dict) and 'vi' in v:
            out[f'{k}.vi'] = v.get('vi', '')
            out[f'{k}.en'] = v.get('en', '')
        elif isinstance(v, list):
            out[k] = ', '.join(v)
        else:
            out[k] = v
    return out


def bump_updated(old_countries, new_countries, changes, today):
    """Mutates new_countries in place, writing each country's `_updated` map:
    - a field named in `changes[code]` (this run's diff, keyed like
      'nGlobal.vi') gets its BASE key ('nGlobal') stamped with `today`
    - every other field carries forward its previous `_updated[key]` unchanged
    - a field with a real value but no previous `_updated` entry at all
      (first run after this feature shipped, or a brand-new field / country)
      is baseline-stamped with `today` — never left without a date once it
      has content to show a badge for
    Only TRACKED_FIELDS (the TEXT_FIELDS/NUM_FIELDS union — i.e. actual
    rendered rows) get an entry; identity/metadata fields never do."""
    for code, country in new_countries.items():
        old_country = old_countries.get(code, {})
        ledger = dict(old_country.get('_updated') or {})
        changed_bases = {k.split('.')[0] for k in changes.get(code, {})} & TRACKED_FIELDS
        for base in changed_bases:
            ledger[base] = today
        for key in TRACKED_FIELDS:
            val = country.get(key)
            has_value = (
                (isinstance(val, dict) and (val.get('vi') or val.get('en')))
                or (not isinstance(val, dict) and val not in (None, '', []))
            )
            if has_value and key not in ledger:
                ledger[key] = today
        country['_updated'] = ledger


def diff_countries(old, new):
    """Returns {code: {field: (old_val, new_val)}} for every changed field,
    plus a separate list of added/removed country codes."""
    old_codes, new_codes = set(old), set(new)
    added = sorted(new_codes - old_codes)
    removed = sorted(old_codes - new_codes)
    changes = {}
    for code in sorted(old_codes & new_codes):
        old_flat, new_flat = flatten(old[code]), flatten(new[code])
        fields = {}
        for key in sorted(set(old_flat) | set(new_flat)):
            ov, nv = old_flat.get(key), new_flat.get(key)
            if ov != nv:
                fields[key] = (ov, nv)
        if fields:
            changes[code] = fields
    return changes, added, removed


def format_digest(changes, added, removed, when):
    lines = [f'## {when} — So Sánh Notion sync']
    if not changes and not added and not removed:
        lines.append('No changes — Notion content already matched the live tool.')
        return '\n'.join(lines), False

    if added:
        lines.append(f'**Countries added:** {", ".join(added)}')
    if removed:
        lines.append(f'**Countries removed:** {", ".join(removed)}')

    for code, fields in changes.items():
        notable = [k.split('.')[0] for k in fields if k.split('.')[0] in NOTABLE_FIELDS]
        notable_labels = sorted({NOTABLE_FIELDS[f] for f in notable})
        summary = f'**{code}** — {len(fields)} field(s) changed'
        if notable_labels:
            summary += f' (incl. {", ".join(notable_labels)})'
        lines.append(summary)
        # a handful of concrete before→after lines, capped so one country
        # with a big rewrite doesn't bury the rest of the digest
        for key in list(fields)[:6]:
            ov, nv = fields[key]
            ov_s = '(empty)' if ov in (None, '') else str(ov)[:60]
            nv_s = '(empty)' if nv in (None, '') else str(nv)[:60]
            lines.append(f'  - `{key}`: {ov_s} → {nv_s}')
        if len(fields) > 6:
            lines.append(f'  - …and {len(fields) - 6} more field(s)')

    return '\n'.join(lines), True


def post_webhook(digest_text, country_count, changed_count):
    url = os.environ.get('NOTIFY_WEBHOOK')
    if not url:
        print('  (NOTIFY_WEBHOOK not set — skipping announcement, log entry still written)')
        return
    card = {
        'cardsV2': [{
            'cardId': 'sosanh-sync',
            'card': {
                'header': {
                    'title': 'So Sánh — Notion sync',
                    'subtitle': f'{changed_count}/{country_count} countries updated this run',
                },
                'sections': [{
                    'widgets': [{'textParagraph': {'text': digest_text.replace(chr(10), '<br>')[:3800]}}],
                }],
            },
        }],
    }
    body = json.dumps(card).encode('utf-8')
    req = urllib.request.Request(url, data=body, method='POST', headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            print(f'  announcement posted ({r.status})')
    except Exception as e:  # noqa: BLE001 — a failed webhook must never fail the sync
        print(f'  ⚠ announcement webhook failed (non-fatal): {e}')


def main():
    old_raw = git_show_head('data/sosanh_payload.json')
    new_full = json.loads(PAYLOAD_PATH.read_text(encoding='utf-8'))

    old = json.loads(old_raw)['countries'] if old_raw else {}
    new = new_full['countries']

    changes, added, removed = diff_countries(old, new)
    now = datetime.datetime.now(datetime.timezone.utc)
    when = now.strftime('%Y-%m-%d %H:%M UTC')
    today = now.strftime('%d/%m/%Y')
    digest, has_changes = format_digest(changes, added, removed, when)

    print(digest)

    # Freshness ledger — always recomputed (even on a no-content-change run,
    # so a brand-new field/country still gets baseline-stamped on first sight).
    bump_updated(old, new, changes, today)
    new_json = json.dumps(new_full, ensure_ascii=False, indent=1)
    if chr(92) in new_json:
        sys.exit('❌ literal backslash after writing the freshness ledger — would break WP wp_unslash on the next HTML push')
    PAYLOAD_PATH.write_text(new_json, encoding='utf-8')

    if not LOG_PATH.exists():
        LOG_PATH.write_text(
            '# So Sánh Notion sync log\n\n'
            'Auto-generated by `tools/sosanh_changelog.py` on every fortnightly '
            'run of `.github/workflows/pull-sosanh-notion.yml`. Newest entries first.\n\n',
            encoding='utf-8',
        )

    if has_changes:
        existing = LOG_PATH.read_text(encoding='utf-8')
        header, _, rest = existing.partition('\n\n')
        LOG_PATH.write_text(header + '\n\n' + digest + '\n\n' + rest, encoding='utf-8')
        post_webhook(digest, len(new), len(changes) + len(added) + len(removed))
    else:
        print('  no changes — log file not touched')


if __name__ == '__main__':
    main()
