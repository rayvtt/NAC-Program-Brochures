#!/usr/bin/env python3
"""Diff the previous vs current data/sosanh_payload.json (via git) and
append a human-readable entry to SOSANH-SYNC-LOG.md — the durable record
of what the fortnightly Notion sync actually changed.

Also posts the same digest to NOTIFY_WEBHOOK if that env var is set (a
Google Chat incoming-webhook URL — same shape nac-marketing-omnichannel's
scripts/notify.mjs already posts to, so Ray sees So Sánh sync activity in
the same channel as the rest of NAC's automation). Silently skipped if
the secret isn't configured — this script's job is done either way once
the log file is written; the webhook is a nice-to-have, not a dependency.

Run (from the repo root, after tools/pull_sosanh_from_notion.py has
already updated data/sosanh_payload.json on disk but BEFORE it's
committed — this script reads the pre-commit git diff):

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
PAYLOAD_PATH = ROOT / 'data' / 'sosanh_payload.json'
LOG_PATH = ROOT / 'SOSANH-SYNC-LOG.md'

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
    """{'gdp': 2.2, 'r1': {'vi':'a','en':'b'}, ...} -> {'gdp': 2.2, 'r1.vi': 'a', 'r1.en': 'b'}"""
    out = {}
    for k, v in country.items():
        if isinstance(v, dict) and 'vi' in v:
            out[f'{k}.vi'] = v.get('vi', '')
            out[f'{k}.en'] = v.get('en', '')
        elif isinstance(v, list):
            out[k] = ', '.join(v)
        else:
            out[k] = v
    return out


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
    new_raw = PAYLOAD_PATH.read_text(encoding='utf-8')

    old = json.loads(old_raw)['countries'] if old_raw else {}
    new = json.loads(new_raw)['countries']

    changes, added, removed = diff_countries(old, new)
    when = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    digest, has_changes = format_digest(changes, added, removed, when)

    print(digest)

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
