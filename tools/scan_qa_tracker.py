"""Daily scan of the NAC Brochures QA Tracker Google Sheet.

The tracker is a published-to-web Google Sheet (CSV format) with:
  - A matrix section: brochures × issues, each cell TRUE/FALSE
    (Sheets renders these as tickboxes once Insert→Tickbox is applied)
  - An ISSUE DETAILS section below mapping #N → human description

This script:
  1. Fetches the CSV
  2. Parses the brochure matrix (until it hits the "ISSUE DETAILS" row)
  3. Parses the issue descriptions
  4. For every unchecked cell (FALSE), records (brochure, issue#, desc)
  5. Writes a markdown report to .diagnostics/qa-status.md
  6. Exits non-zero if there are open issues (so the GitHub Action
     surfaces the failure in the run UI)

Env:
  QA_TRACKER_CSV_URL  — published-to-web CSV URL from Google Sheets

No third-party deps.
"""
import csv
import io
import os
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_FILE = ROOT / '.diagnostics' / 'qa-status.md'

TRUTHY = {'TRUE', 'true', 'True', '1', 'YES', 'yes', '✓', '☑'}
FALSY = {'FALSE', 'false', 'False', '0', 'NO', 'no', ''}
NA_VALUES = {'N/A', 'n/a', 'NA', '—', '-'}

DETAIL_SECTION_MARKER = 'ISSUE DETAILS'


def fetch_csv(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'NAC-QA-Scanner/1.0'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode('utf-8', errors='replace')


def parse_tracker(raw):
    """Returns (header_row, brochure_rows, issue_details).

    header_row: list of column labels in the matrix
    brochure_rows: list of dict {brochure, url, checks: dict[col_label]→cell}
    issue_details: dict {issue_key (e.g. '#1') → description}
    """
    reader = csv.reader(io.StringIO(raw))
    rows = list(reader)

    # Find the matrix header row — the one that starts with "Brochure"
    header_idx = None
    for i, row in enumerate(rows):
        if row and row[0].strip().lower() == 'brochure':
            header_idx = i
            break
    if header_idx is None:
        raise SystemExit('❌ Could not find "Brochure" header row in the tracker CSV.')

    header_row = rows[header_idx]
    # Identify issue columns: between "Live URL" and "Notes" (or end)
    try:
        notes_col = header_row.index('Notes')
    except ValueError:
        notes_col = len(header_row)
    issue_cols = list(range(2, notes_col))  # cols 0 (Brochure) + 1 (URL) + 2..(notes-1) issues

    # Find the ISSUE DETAILS section
    details_idx = None
    for i, row in enumerate(rows[header_idx + 1:], start=header_idx + 1):
        if row and DETAIL_SECTION_MARKER in row[0]:
            details_idx = i
            break

    matrix_end = details_idx if details_idx is not None else len(rows)

    brochure_rows = []
    for i in range(header_idx + 1, matrix_end):
        row = rows[i]
        if not row or not row[0].strip():
            continue
        brochure = row[0].strip()
        url = row[1].strip() if len(row) > 1 else ''
        checks = {}
        for col in issue_cols:
            label = header_row[col].strip() if col < len(header_row) else f'col{col}'
            value = row[col].strip() if col < len(row) else ''
            checks[label] = value
        brochure_rows.append({'brochure': brochure, 'url': url, 'checks': checks})

    issue_details = {}
    if details_idx is not None:
        for row in rows[details_idx + 1:]:
            if not row or not row[0].strip().startswith('#'):
                continue
            key = row[0].strip()
            label = row[1].strip() if len(row) > 1 else ''
            desc = row[2].strip() if len(row) > 2 else ''
            issue_details[key] = f'{label} — {desc}' if label and desc else (label or desc)

    return header_row, brochure_rows, issue_details


def status_of(value):
    """Returns 'ok' / 'open' / 'na' / 'unknown' for a cell."""
    v = (value or '').strip()
    if v in TRUTHY:
        return 'ok'
    if v in FALSY:
        return 'open'
    if v in NA_VALUES:
        return 'na'
    return 'unknown'


def build_report(brochure_rows, issue_details):
    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')
    lines = [
        '# NAC Brochures — QA Tracker Status',
        '',
        f'_Last scan: {now}_',
        '',
    ]

    # Count totals
    total_cells = 0
    open_cells = 0
    open_by_brochure = {}
    open_by_issue = {}

    for row in brochure_rows:
        for label, value in row['checks'].items():
            s = status_of(value)
            if s == 'na':
                continue
            total_cells += 1
            if s == 'open':
                open_cells += 1
                open_by_brochure.setdefault(row['brochure'], []).append(label)
                open_by_issue.setdefault(label, []).append(row['brochure'])

    if open_cells == 0:
        lines.append('## ✅ All checks passing')
        lines.append('')
        lines.append(f'Every applicable cell ({total_cells}) is ticked. No open issues.')
        lines.append('')
        return '\n'.join(lines), 0

    pct = 100 * (total_cells - open_cells) / total_cells if total_cells else 0
    lines.append(f'## 🟡 {open_cells} of {total_cells} cells still open ({pct:.1f}% done)')
    lines.append('')

    # By issue
    lines.append('### Open by issue')
    lines.append('')
    for issue, brochures in sorted(open_by_issue.items()):
        desc = issue_details.get(issue, '')
        lines.append(f'**{issue}** {desc}')
        lines.append('')
        for b in brochures:
            lines.append(f'  - {b}')
        lines.append('')

    # By brochure
    lines.append('### Open by brochure')
    lines.append('')
    for brochure, issues in sorted(open_by_brochure.items()):
        lines.append(f'**{brochure}** — {len(issues)} open')
        for issue in issues:
            short = issue_details.get(issue, '').split(' — ')[0]
            lines.append(f'  - {issue}  {short}')
        lines.append('')

    return '\n'.join(lines), open_cells


def main():
    url = os.environ.get('QA_TRACKER_CSV_URL')
    if not url:
        print('❌ QA_TRACKER_CSV_URL env var not set.', file=sys.stderr)
        sys.exit(2)

    print(f'Fetching {url[:80]}…')
    raw = fetch_csv(url)
    header, brochure_rows, issue_details = parse_tracker(raw)

    print(f'  {len(brochure_rows)} brochures, {len(issue_details)} issue definitions')

    report, open_count = build_report(brochure_rows, issue_details)

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(report)
    print(f'  → wrote {OUT_FILE.relative_to(ROOT)}')

    # Print head of the report to the workflow log too
    print('\n' + report[:1200])

    # Don't exit non-zero — we WANT the cron to keep going daily and
    # we'll commit the report file. The "open issues" signal is the
    # diff in the committed file, which the user can see in git history.
    sys.exit(0)


if __name__ == '__main__':
    main()
