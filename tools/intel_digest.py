#!/usr/bin/env python3
"""Weekly digest: aggregate 7 days of intel signals into a GitHub Issue body.

Reads the last 7 days of `.diagnostics/weekly-intel/<YYYY-MM-DD>/<alias>.json`
files, dedupes signals, compares high-confidence findings against the
current `data/<alias>_payload.json`, and emits a markdown issue body
with **checkbox tasks per proposed change**.

Each checkbox carries a machine-readable trailer that
`tools/intel_apply.py` parses when a user ticks the box:

    - [ ] turkey · hero_stats[0].num: `$400K` → `$500K`
      <!-- intel:alias=turkey;field=hero_stats;jsonpath=0.num;new=$500K -->

Run:
    python tools/intel_digest.py > /tmp/issue-body.md
    python tools/intel_digest.py --days=7 --min-authority=2
    python tools/intel_digest.py --out=.diagnostics/weekly-intel/DIGEST.md
"""
from __future__ import annotations

import datetime as dt
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from data.brochure_identity import IDENTITY  # noqa: E402
from tools.intel_sources import ALL_ALIASES, COUNTRY_SOURCES  # noqa: E402

INTEL_DIR = ROOT / '.diagnostics' / 'weekly-intel'
DATA_DIR = ROOT / 'data'


# ── Load + dedupe signals across the rolling window ──────────────────────


def load_window(days: int) -> dict[str, list[dict]]:
    """Return {alias: [signals…]} across the last `days` days."""
    cutoff = dt.date.today() - dt.timedelta(days=days - 1)
    by_alias: dict[str, list[dict]] = defaultdict(list)
    if not INTEL_DIR.exists():
        return by_alias
    for day_dir in sorted(INTEL_DIR.iterdir()):
        if not day_dir.is_dir():
            continue
        try:
            day = dt.date.fromisoformat(day_dir.name)
        except ValueError:
            continue
        if day < cutoff:
            continue
        for f in day_dir.glob('*.json'):
            alias = f.stem
            if alias not in COUNTRY_SOURCES:
                continue
            try:
                rec = json.loads(f.read_text(encoding='utf-8'))
            except Exception:
                continue
            for sig in rec.get('signals', []):
                sig['_day'] = day_dir.name
                by_alias[alias].append(sig)
    return by_alias


def dedupe(signals: list[dict]) -> list[dict]:
    """Drop signals with identical (kind, matched, url)."""
    seen: set[tuple] = set()
    out = []
    for s in signals:
        key = (s.get('kind'), s.get('matched', '').lower(), s.get('url'))
        if key in seen:
            continue
        seen.add(key)
        out.append(s)
    return out


# ── Compare signals against current Notion payload ───────────────────────


MONEY_NORM_RE = re.compile(r'[^\d]')


def normalise_money(s: str) -> int | None:
    """'$400,000' → 400000, '$500K' → 500000, 'USD 1.5M' → 1500000, else None."""
    s = s.strip().lower().replace(' ', '')
    if not s:
        return None
    mult = 1
    if s.endswith('k'):
        mult = 1_000
        s = s[:-1]
    elif s.endswith('m'):
        mult = 1_000_000
        s = s[:-1]
    digits = MONEY_NORM_RE.sub('', s)
    if not digits:
        return None
    try:
        n = int(digits) * mult
    except ValueError:
        return None
    # Filter implausible amounts for investment migration
    if n < 10_000 or n > 50_000_000:
        return None
    return n


def existing_thresholds_from_payload(payload: dict) -> dict[str, int]:
    """Pull each $-amount we can find in the payload as a normalised int.

    Returns {payload_field_locator: amount} so the digest can flag drift.
    E.g. {'hero_stats[0].num': 400000, 's02_tiers[0].amount': 400000}
    """
    out: dict[str, int] = {}

    # Plain stat
    for fld in ('hero_stats',):
        raw = payload.get(fld, '')
        try:
            arr = json.loads(raw) if isinstance(raw, str) else raw
        except Exception:
            continue
        if not isinstance(arr, list):
            continue
        for i, item in enumerate(arr):
            num = item.get('num') if isinstance(item, dict) else None
            if num:
                v = normalise_money(num)
                if v:
                    out[f'{fld}[{i}].num'] = v

    # Investment tiers
    raw = payload.get('s02_tiers', '')
    try:
        arr = json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        arr = None
    if isinstance(arr, list):
        for i, item in enumerate(arr):
            amount = item.get('amount') if isinstance(item, dict) else None
            if amount:
                v = normalise_money(amount)
                if v:
                    out[f's02_tiers[{i}].amount'] = v

    return out


def proposed_money_changes(alias: str, signals: list[dict]) -> list[dict]:
    """Find money signals that don't match any threshold in the current payload.

    Returns proposals: {field_locator, current_str, current_int, new_str, new_int, evidence}
    """
    payload_path = DATA_DIR / f'{alias}_payload.json'
    if not payload_path.exists():
        return []
    try:
        payload = json.loads(payload_path.read_text(encoding='utf-8'))
    except Exception:
        return []
    current = existing_thresholds_from_payload(payload)
    if not current:
        return []

    # Bucket money signals by normalised amount; keep only high-authority
    buckets: dict[int, list[dict]] = defaultdict(list)
    for s in signals:
        if s.get('kind') != 'money':
            continue
        if s.get('authority', 0) < 2:  # ignore Reddit-only money mentions
            continue
        v = normalise_money(s.get('matched', ''))
        if v is None:
            continue
        buckets[v].append(s)

    proposals: list[dict] = []
    for current_field, current_int in current.items():
        # Find the strongest bucket that DIFFERS by more than 5% from current
        candidates = [
            (amt, evidence) for amt, evidence in buckets.items()
            if abs(amt - current_int) / max(current_int, 1) > 0.05
        ]
        if not candidates:
            continue
        # Sort by (count of evidence, authority sum) descending
        candidates.sort(
            key=lambda kv: (len(kv[1]), sum(e['authority'] for e in kv[1])),
            reverse=True,
        )
        amt, evidence = candidates[0]
        # Require at least 2 independent sources to surface as a proposal
        if len({e['source'] for e in evidence}) < 2:
            continue
        proposals.append({
            'field_locator': current_field,
            'current_str': format_money(current_int),
            'current_int': current_int,
            'new_str': format_money(amt),
            'new_int': amt,
            'evidence': evidence[:5],
        })
    return proposals


def format_money(n: int) -> str:
    """400000 → '$400K', 1500000 → '$1.5M'."""
    if n >= 1_000_000:
        v = n / 1_000_000
        return f'${v:.1f}M'.replace('.0M', 'M')
    if n >= 1_000:
        return f'${n // 1_000}K'
    return f'${n:,}'


# ── Issue body composition ────────────────────────────────────────────────


HEADER = """# 📰 Weekly Investment-Migration Intel — {today}

Window: last {days} days · {countries} countries scanned · {signals} signals · {proposals} proposed updates

**How to use**: tick a checkbox → save → the `intel-apply` workflow PATCHes
Notion + `data/<alias>_payload.json` for that field. Untick to revert is not
automatic — use the next cycle.

---
"""

NO_PROPOSALS_BLOCK = """### No high-confidence price changes detected this week

The scan ran (signals shown below per country) but nothing crossed the
2-source × ≥5% drift threshold. Tick the **"Force review"** boxes for any
country where you want to investigate manually.

---
"""


def render_country_block(
    alias: str,
    signals: list[dict],
    proposals: list[dict],
) -> str:
    ident = IDENTITY.get(alias, {})
    flag = ident.get('flag', '🏳️')
    name = ident.get('country_en') or alias.title()
    program = ident.get('program_en') or ident.get('program_code') or ''
    out = [f'## {flag} {name} {("· " + program) if program else ""}']

    if proposals:
        out.append('\n### Proposed updates\n')
        for p in proposals:
            checkbox = (
                f"- [ ] **`{p['field_locator']}`**: "
                f"`{p['current_str']}` → `{p['new_str']}`  "
                f"*({len({e['source'] for e in p['evidence']})} sources)*\n"
            )
            # Machine-readable trailer for intel_apply.py
            field_root = p['field_locator'].split('[', 1)[0]
            json_path = (
                p['field_locator'][len(field_root):]
                .replace('[', '').replace(']', '').lstrip('.')
            )
            trailer = (
                f"  <!-- intel:alias={alias};field={field_root};"
                f"jsonpath={json_path};new={p['new_str']};kind=money -->\n"
            )
            # Evidence list (max 5)
            ev_lines = []
            for e in p['evidence'][:5]:
                ev_lines.append(
                    f"  - {e['source']}: \"{e.get('matched', '')[:80]}\""
                    + (f" — <{e['url']}>" if e.get('url') else '')
                )
            out.append(checkbox + trailer + '\n'.join(ev_lines) + '\n')
    else:
        out.append('\n_No proposed updates this week._\n')

    # Signals summary (collapsed). Helpful for review when no proposal triggers.
    triggers = [s for s in signals if s.get('kind') == 'trigger']
    mentions = [s for s in signals if s.get('kind') == 'mention']
    money = [s for s in signals if s.get('kind') == 'money']
    out.append(
        f"<details><summary>Signals: {len(money)} money · "
        f"{len(triggers)} change-triggers · {len(mentions)} community mentions</summary>\n"
    )
    for label, lst in (
        ('🚨 Change-trigger keywords', triggers[:10]),
        ('💰 Money mentions', money[:10]),
        ('💬 Community discussions', mentions[:8]),
    ):
        if not lst:
            continue
        out.append(f"\n**{label}**\n")
        for s in lst:
            url = s.get('url', '')
            src = s.get('source', '')
            ex = s.get('excerpt') or s.get('matched', '')
            ex = (ex[:200] + '…') if len(ex) > 200 else ex
            out.append(f"- *{src}*: {ex}" + (f" — <{url}>" if url else ''))
    out.append('\n</details>\n')

    # Force-review checkbox (manual override)
    out.append(
        f"- [ ] **Force review** — open Notion row for {alias} and audit manually  "
        f"<!-- intel:alias={alias};action=force_review -->\n"
    )

    return '\n'.join(out)


def build_digest(*, days: int, out_path: Path | None) -> str:
    by_alias = load_window(days)

    total_signals = 0
    total_proposals = 0
    country_blocks: list[str] = []

    for alias in ALL_ALIASES:
        signals = dedupe(by_alias.get(alias, []))
        proposals = proposed_money_changes(alias, signals)
        total_signals += len(signals)
        total_proposals += len(proposals)
        if not signals and not proposals:
            continue  # Quiet weeks: drop the country from the digest
        country_blocks.append(render_country_block(alias, signals, proposals))

    today = dt.date.today().isoformat()
    body = HEADER.format(
        today=today,
        days=days,
        countries=len(ALL_ALIASES),
        signals=total_signals,
        proposals=total_proposals,
    )
    if total_proposals == 0:
        body += NO_PROPOSALS_BLOCK
    body += '\n\n---\n\n'.join(country_blocks) if country_blocks else '_No activity this week._\n'

    # Tiny how-to-respond footer
    body += (
        '\n\n---\n\n'
        '### How responses are applied\n\n'
        '1. Tick boxes for changes you accept.\n'
        '2. The `intel-apply` workflow fires on issue edit, parses the trailers, '
        'and PATCHes Notion + `data/<alias>_payload.json`.\n'
        '3. The 10-min `pull-notion` job then propagates to WordPress.\n'
        '4. Untick = no-op (no revert). Open a new issue if you need to roll back.\n'
    )

    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(body, encoding='utf-8')
        print(f'Wrote digest → {out_path.relative_to(ROOT)}', file=sys.stderr)
    return body


def main() -> int:
    days = 7
    out_path: Path | None = None
    for a in sys.argv[1:]:
        if a.startswith('--days='):
            days = int(a.split('=', 1)[1])
        elif a.startswith('--out='):
            out_path = Path(a.split('=', 1)[1])
            if not out_path.is_absolute():
                out_path = ROOT / out_path
    body = build_digest(days=days, out_path=out_path)
    if not out_path:
        sys.stdout.write(body)
    return 0


if __name__ == '__main__':
    sys.exit(main())
