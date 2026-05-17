"""Generate a sheet-pasteable tracker of EN-coverage status per brochure.

Produces TWO outputs in .diagnostics/:

  sheet-tracker-header.tsv   — 1 row of column labels for the header.
  sheet-tracker.tsv          — 12 rows (one per brochure) with the same
                               10 columns. Designed to paste into the
                               Google Sheet "backlink" tab at A28:J39.

Columns (A-J, 10 total):

  A  Brochure
  B  Live coverage %
  C  Toggle (✓ / ✗)
  D  Section gaps (count + comma-separated list)
  E  Charts (✓ wrapper / ✓ translator / ✗ broken / n/a no charts)
  F  Text drift (# of strings where Notion has EN but HTML drifted)
  G  No-EN-available (# of strings where Notion is also empty — OK)
  H  Auto-fixable (# of gaps Notion can fill once VI text aligns)
  I  Live URL
  J  Last sync / note

Input sources:
  - .diagnostics/live-en-coverage.json (live coverage % per brochure)
  - .diagnostics/daily-en-audit.json (toggle / section / chart status)
  - .diagnostics/en-coverage.json (local-side fallback if live missing)

Idempotent — overwrites the TSV files each run.

Run:
    python tools/generate_sheet_tracker.py
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIAGNOSTICS = ROOT / ".diagnostics"

# Brochure order for the sheet (matches your A28:J39 = 12 rows)
BROCHURE_ORDER = [
    'turkey', 'portugal', 'greece', 'cyprus', 'malta', 'uae',
    'uk', 'stkitts', 'thailand', 'newzealand', 'panama', 'malaysia',
]

LIVE_URL = {
    'portugal':   'https://nomadassetcollective.com/brochures/chuong-trinh-bo-dao-nha-golden-visa/',
    'greece':     'https://nomadassetcollective.com/brochures/residences-chuong-trinh-hy-lap-golden-visa/',
    'cyprus':     'https://nomadassetcollective.com/brochures/chuong-trinh-dao-sip-rbi-residence-by-investment/',
    'turkey':     'https://nomadassetcollective.com/brochures/chuong-trinh-tho-nhi-ky-cbi-citizenship-by-investment/',
    'uae':        'https://nomadassetcollective.com/brochures/chuong-trinh-uae-golden-visa-2/',
    'uk':         'https://nomadassetcollective.com/brochures/chuong-trinh-uk-thuong-tru-visa-dau-tu-rbi/',
    'malta':      'https://nomadassetcollective.com/brochures/chuong-trinh-malta-thuong-tru-nhan-rbi/',
    'stkitts':    'https://nomadassetcollective.com/brochures/chuong-trinh-si-kitts-nevis-quoc-tich/',
    'thailand':   'https://nomadassetcollective.com/brochures/chuong-trinh-thai-lan-cu-tru-dai-han-ltr-rbi/',
    'newzealand': 'https://nomadassetcollective.com/brochures/chuong-trinh-new-zealand-rbi-dau-tu-di-tru/',
    'panama':     'https://nomadassetcollective.com/brochures/chuong-trinh-panama-rbi-quyen-cu-tru-vinh-vien/',
    'malaysia':   'https://nomadassetcollective.com/brochures/chuong-trinh-malaysia-rbi-mm2h-dau-tu-quyen-cu-tru/',
}

FLAGS = {
    'portugal': '🇵🇹', 'greece': '🇬🇷', 'cyprus': '🇨🇾', 'turkey': '🇹🇷',
    'uae': '🇦🇪', 'uk': '🇬🇧', 'malta': '🇲🇹', 'stkitts': '🇰🇳',
    'thailand': '🇹🇭', 'newzealand': '🇳🇿', 'panama': '🇵🇦', 'malaysia': '🇲🇾',
}


def load_json_if_exists(path: Path) -> dict | None:
    if not path.exists(): return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def build_rows() -> list[list[str]]:
    """Build 12 rows, one per brochure, 10 cols each."""
    live_data = load_json_if_exists(DIAGNOSTICS / 'live-en-coverage.json') or {}
    audit_data = load_json_if_exists(DIAGNOSTICS / 'daily-en-audit.json') or {}
    local_data = load_json_if_exists(DIAGNOSTICS / 'en-coverage.json') or {}

    live_by_alias = {r['alias']: r for r in live_data.get('reports', [])}
    audit_by_alias = {r['alias']: r for r in audit_data.get('reports', [])}
    local_by_alias = {r['alias']: r for r in local_data.get('reports', [])}

    rows = []
    for alias in BROCHURE_ORDER:
        live = live_by_alias.get(alias)
        audit = audit_by_alias.get(alias)
        local = local_by_alias.get(alias)

        # A: Brochure
        col_a = f"{FLAGS.get(alias, '')} {alias}".strip()

        # B: Live coverage %  (fallback to local if no live data)
        if live:
            col_b = f"{live['coverage_pct']:.1f}%"
        elif local:
            col_b = f"{local['coverage_pct']:.1f}% (local)"
        else:
            col_b = "—"

        # C: Toggle
        if audit:
            col_c = "✓" if audit['toggle']['pass'] else f"✗ {'; '.join(audit['toggle']['issues'])[:50]}"
        else:
            col_c = "—"

        # D: Section gaps
        if audit:
            low = audit['sections']['low_sections']
            if low:
                col_d = f"✗ ({len(low)}): {', '.join(low)}"
            else:
                col_d = "✓ all ≥70%"
        else:
            col_d = "—"

        # E: Charts
        if audit:
            ch = audit['charts']
            if not ch.get('has_charts'):
                col_e = "n/a"
            elif ch['pass']:
                col_e = "✓ wrapper" if ch.get('has_buildcharts') else "✓ translator"
            else:
                col_e = f"✗ {'; '.join(ch['issues'])[:50]}"
        else:
            col_e = "—"

        # F, G, H: gap reason breakdown (from live or local report)
        report = live or local
        if report:
            gap_reasons = {}
            for g in report.get('gap_samples', []):
                gap_reasons[g['reason']] = gap_reasons.get(g['reason'], 0) + 1
            col_f = str(gap_reasons.get('text_drift_vs_notion', 0))
            col_g = str(gap_reasons.get('no_en_available', 0))
            col_h = str(gap_reasons.get('notion_has_en_not_injected', 0)
                        + gap_reasons.get('text_drift_vs_notion', 0))
        else:
            col_f = col_g = col_h = "—"

        # I: Live URL
        col_i = LIVE_URL.get(alias, "")

        # J: Last sync timestamp
        if live_data.get('generated_at'):
            ts = live_data['generated_at'][:16].replace('T', ' ') + ' UTC'
            col_j = ts
        else:
            col_j = "—"

        rows.append([col_a, col_b, col_c, col_d, col_e, col_f, col_g, col_h, col_i, col_j])

    return rows


def main() -> int:
    DIAGNOSTICS.mkdir(exist_ok=True)

    header = [
        'Brochure', 'Live cov %', 'Toggle', 'Section gaps',
        'Charts', 'Text drift', 'No-EN', 'Auto-fix?',
        'Live URL', 'Last sync',
    ]
    rows = build_rows()

    # Header file (one row)
    (DIAGNOSTICS / 'sheet-tracker-header.tsv').write_text(
        '\t'.join(header) + '\n', encoding='utf-8'
    )

    # Data rows file (12 rows, no header — fits A28:J39 exactly)
    (DIAGNOSTICS / 'sheet-tracker.tsv').write_text(
        '\n'.join('\t'.join(r) for r in rows) + '\n',
        encoding='utf-8'
    )

    # Markdown version for easy human review on GitHub
    md = ['# Brochure status tracker', '',
          f'_Generated: {datetime.now(tz=timezone.utc).isoformat()[:19]}Z_', '',
          'Paste `sheet-tracker.tsv` into your Google Sheet at **A28:J39** (the "backlink" tab).',
          'Header lives in row 27 — overwrite from `sheet-tracker-header.tsv` if you want.', '']
    md.append('| ' + ' | '.join(header) + ' |')
    md.append('|' + '|'.join('---' for _ in header) + '|')
    for r in rows:
        # Truncate long URLs / long gaps for markdown table
        r_display = [c if len(c) < 80 else c[:77] + '…' for c in r]
        md.append('| ' + ' | '.join(r_display) + ' |')
    (DIAGNOSTICS / 'sheet-tracker.md').write_text('\n'.join(md) + '\n', encoding='utf-8')

    print('Wrote .diagnostics/sheet-tracker.tsv (12 rows × 10 cols)')
    print('Wrote .diagnostics/sheet-tracker-header.tsv (1 row × 10 cols)')
    print('Wrote .diagnostics/sheet-tracker.md (human-readable)')

    # Also print to stdout so workflow logs show the current state
    print('\n=== TRACKER ===')
    print('\t'.join(header))
    for r in rows:
        print('\t'.join(r[:5]))  # First 5 cols for log brevity
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
