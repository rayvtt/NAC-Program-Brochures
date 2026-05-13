#!/usr/bin/env python3
"""Validate a brochure JSON payload against the schema.

Catches:
  - missing properties (schema field with no payload entry)
  - JSON syntax errors in structured fields
  - structured array items missing expected keys (e.g. tier without 'amount')

Run:
    python tools/check_brochure_payload.py data/turkey_payload.json
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from data.brochure_schema import SCHEMA, STRUCTURED_FIELDS  # noqa: E402


def main():
    if len(sys.argv) < 2:
        sys.exit('usage: check_brochure_payload.py <payload.json>')
    path = Path(sys.argv[1])
    if not path.exists():
        sys.exit(f'❌ {path} not found')

    payload = json.loads(path.read_text(encoding='utf-8'))
    errors, warnings = [], []

    # Missing / unknown fields
    schema_keys = set(SCHEMA.keys())
    payload_keys = set(payload.keys())
    for k in schema_keys - payload_keys:
        warnings.append(f'missing field: {k}')
    for k in payload_keys - schema_keys:
        warnings.append(f'unknown field: {k} (not in SCHEMA)')

    # Structured fields: JSON parses + items have expected keys
    for field, spec in STRUCTURED_FIELDS.items():
        val = payload.get(field)
        if not val:
            continue
        try:
            items = json.loads(val) if isinstance(val, str) else val
        except json.JSONDecodeError as e:
            errors.append(f'{field}: invalid JSON — {e}')
            continue
        if not isinstance(items, list):
            errors.append(f'{field}: expected JSON array, got {type(items).__name__}')
            continue
        expected_keys = set(spec['item_keys'])
        for i, item in enumerate(items):
            if not isinstance(item, dict):
                errors.append(f'{field}[{i}]: expected object, got {type(item).__name__}')
                continue
            missing = expected_keys - set(item.keys())
            if missing:
                warnings.append(f'{field}[{i}]: missing keys {sorted(missing)}')

    # Report
    print(f'Payload: {path}')
    print(f'  fields:    {len(payload)} / {len(SCHEMA)} schema')
    print(f'  errors:    {len(errors)}')
    print(f'  warnings:  {len(warnings)}')
    for e in errors:
        print(f'  ❌ {e}')
    for w in warnings[:20]:
        print(f'  ⚠ {w}')
    if len(warnings) > 20:
        print(f'  … and {len(warnings) - 20} more warnings')

    sys.exit(1 if errors else 0)


if __name__ == '__main__':
    main()
