"""Live EN translation coverage — fetch each brochure's WordPress page
and run the same coverage check as on local HTML.

Compares LIVE state (what users actually see) vs LOCAL state (what's
committed to the repo). Discrepancies usually mean wp-sync hasn't
propagated yet (rare) or WP/KSES mangled the HTML in transit (the
\\\" trap, attribute stripping, etc.).

Output:
  - Per-brochure live coverage (translated / gap / skip counts)
  - Drift detection: live vs local coverage delta
  - JSON report to .diagnostics/live-en-coverage.json (committed
    by the daily workflow for trend tracking)

Run:
    python tools/check_live_en_coverage.py             # all 12
    python tools/check_live_en_coverage.py portugal    # one alias
"""
from __future__ import annotations

import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIAGNOSTICS = ROOT / ".diagnostics"

sys.path.insert(0, str(ROOT / "tools"))
from check_en_translation_coverage import (
    check_translation_coverage,
    ALIAS_TO_FILENAME,
)

# Alias → live WP URL slug
LIVE_SLUG = {
    'portugal':   'chuong-trinh-bo-dao-nha-golden-visa',
    'greece':     'residences-chuong-trinh-hy-lap-golden-visa',
    'cyprus':     'chuong-trinh-dao-sip-rbi-residence-by-investment',
    'turkey':     'chuong-trinh-tho-nhi-ky-cbi-citizenship-by-investment',
    'uae':        'chuong-trinh-uae-golden-visa-2',
    'uk':         'chuong-trinh-uk-thuong-tru-visa-dau-tu-rbi',
    'malta':      'chuong-trinh-malta-thuong-tru-nhan-rbi',
    'stkitts':    'chuong-trinh-si-kitts-nevis-quoc-tich',
    'thailand':   'chuong-trinh-thai-lan-cu-tru-dai-han-ltr-rbi',
    'newzealand': 'chuong-trinh-new-zealand-rbi-dau-tu-di-tru',
    'panama':     'chuong-trinh-panama-rbi-quyen-cu-tru-vinh-vien',
    'malaysia':   'chuong-trinh-malaysia-rbi-mm2h-dau-tu-quyen-cu-tru',
    'antigua':    'chuong-trinh-antigua-barbuda-cbi',
    'italy':      'chuong-trinh-y-italy-rbi-qua-dau-tu-bds',
    'spain':      'chuong-trinh-tay-ban-nha-golden-visa-qua-dau-tu-bds',
    'montenegro': 'chuong-trinh-montenengro-rbi-qua-dau-tu-bds',
    'australia':  'chuong-trinh-uc-australia-rbi-dau-tu',
    'nauru':      'chuong-trinh-nauru-cbi-quoc-tich',
}
LIVE_BASE = 'https://nomadassetcollective.com/brochures'

UA = (
    "Mozilla/5.0 (compatible; nac-coverage-bot/1.0; +https://github.com/rayvtt/NAC-Program-Brochures)"
)

# Colors
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
GRAY = "\033[90m"
BOLD = "\033[1m"
RESET = "\033[0m"


def fetch_live(alias: str) -> Path:
    """Fetch the live brochure HTML, save to a temp file, return the path."""
    slug = LIVE_SLUG.get(alias)
    if not slug:
        raise ValueError(f'no live slug for {alias}')
    url = f'{LIVE_BASE}/{slug}/?nc={int(datetime.now(tz=timezone.utc).timestamp())}'
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        body = r.read()
    tmp = Path(f'/tmp/live_{alias}.html')
    tmp.write_bytes(body)
    return tmp


def main() -> int:
    args = sys.argv[1:]
    aliases = args if args else list(LIVE_SLUG.keys())

    print(f"\n{BOLD}Live EN Translation Coverage Report{RESET}")
    print(f"{GRAY}{'─' * 70}{RESET}")

    # Load local coverage report for comparison (if exists)
    local_path = DIAGNOSTICS / 'en-coverage.json'
    local_by_alias = {}
    if local_path.exists():
        try:
            for r in json.loads(local_path.read_text())['reports']:
                local_by_alias[r['alias']] = r['coverage_pct']
        except Exception:
            pass

    reports = []
    for alias in aliases:
        if alias not in LIVE_SLUG:
            print(f"  ? unknown alias: {alias}")
            continue
        try:
            html_path = fetch_live(alias)
        except Exception as e:
            print(f"  ✗ {alias}: fetch failed — {e}")
            continue

        payload_path = ROOT / 'data' / f'{alias}_payload.json'
        try:
            r = check_translation_coverage(alias, html_path, payload_path)
        except Exception as e:
            print(f"  ✗ {alias}: check failed — {e}")
            continue
        reports.append(r)

        cov = r['coverage_pct']
        local_cov = local_by_alias.get(alias)
        delta = ''
        if local_cov is not None:
            d = cov - local_cov
            if d > 0.5:
                delta = f' {GREEN}(+{d:.1f} vs local){RESET}'
            elif d < -0.5:
                delta = f' {RED}({d:.1f} vs local){RESET}'
            else:
                delta = f' {GRAY}(in sync){RESET}'

        color = GREEN if cov >= 95 else (YELLOW if cov >= 70 else RED)
        print(f"  {BOLD}{alias:12s}{RESET} {color}{cov:>5.1f}%{RESET} "
              f"{GRAY}({r['translated']} translated / {r['gap']} gap){RESET}{delta}")

    if not reports:
        return 1

    print(f"\n{GRAY}{'─' * 70}{RESET}")
    avg = sum(r['coverage_pct'] for r in reports) / len(reports)
    full = sum(1 for r in reports if r['coverage_pct'] >= 95)
    partial = sum(1 for r in reports if 70 <= r['coverage_pct'] < 95)
    low = sum(1 for r in reports if r['coverage_pct'] < 70)
    print(f"{BOLD}Summary:{RESET}  avg {avg:.1f}%  ·  "
          f"{GREEN}{full} ≥95%{RESET}  ·  "
          f"{YELLOW}{partial} 70-94%{RESET}  ·  "
          f"{RED}{low} <70%{RESET}")

    # Write JSON report
    DIAGNOSTICS.mkdir(exist_ok=True)
    out = DIAGNOSTICS / 'live-en-coverage.json'
    out.write_text(json.dumps({
        'generated_at': datetime.now(tz=timezone.utc).isoformat(),
        'source': 'live WordPress fetched HTML',
        'reports': reports,
    }, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"  → JSON report: {out.relative_to(ROOT)}")

    return 0 if all(r['coverage_pct'] >= 70 for r in reports) else 1


if __name__ == '__main__':
    raise SystemExit(main())
