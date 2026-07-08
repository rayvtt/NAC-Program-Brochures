#!/usr/bin/env python3
"""Apply a copy-change map to the Partner Gateway page (NAC-PARTNERS.html).

Driven by .github/workflows/apply-partner-copy.yml, which the in-page
editor (?edit=1 on the live page) dispatches with input `changes`:

    {"pg-a788c2": {"vi": "…", "en": "…", "o_vi": "…", "o_en": "…"}, …}

Keys anchor to data-copy="<key>" elements; values are written into the
data-vi / data-en attributes (setLang hydrates all text from them).
Mirrors NAC---Property-Hub/scripts/apply-homepage-copy.mjs in Python
(this repo's tooling idiom).

Hard-won behavior (2026-07-08 review — edits were being lost silently):
- An EMPTY string is a legitimate edit (the user deleted the text). Presence
  of the key in the payload is what matters, never truthiness.
- Keys are content-derived (pg-<sha1(vi)[:6]>), so a repo-side copy change
  re-keys the element while the live page still carries the old key. When a
  key is missing, fall back to locating the element by its OLD text (o_vi /
  o_en sent by the editor). Only an unambiguous single match is patched.
- A key may be SHARED by several elements (e.g. the LIVE chip on every demo
  frame) — patch every occurrence, not just the first.
- Anything skipped is reported to GITHUB_STEP_SUMMARY and recorded in
  SKIP_FILE; the workflow fails the run AFTER committing what did apply, so
  a lost edit shows up as a red run instead of a false green.

Env: CHANGES — the JSON change map. SKIP_FILE — where to record skipped keys.
"""
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILE = ROOT / 'Brochures html' / 'NAC-PARTNERS.html'
LOG = ROOT / 'PARTNER-COPY-LOG.md'
SKIP_FILE = Path(os.environ.get('SKIP_FILE') or '/tmp/copy-apply-skipped.txt')

KEY_RE = re.compile(r'^[a-z0-9_.-]+$', re.I)
TAG_RE_TPL = r'<[^>]*data-copy="%s"[^>]*>'


def esc_attr(t: str) -> str:
    return (t.replace('&', '&amp;').replace('<', '&lt;')
             .replace('>', '&gt;').replace('"', '&quot;'))


def unesc(t: str) -> str:
    return (t.replace('&quot;', '"').replace('&lt;', '<')
             .replace('&gt;', '>').replace('&amp;', '&'))


def norm(t) -> str:
    """Collapse all whitespace runs (incl. newlines from contenteditable) to
    single spaces — matches how the data-attr walker renders the value."""
    if not isinstance(t, str):
        return ''
    return re.sub(r'\s+', ' ', t).strip()


def clip(t: str, n: int) -> str:
    return t[:n] + '…' if len(t) > n else t


def show(t: str) -> str:
    return t if t else '∅ (đã xoá)'


def append_log(entries, source):
    if not entries:
        return
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M') + ' UTC'
    block = f'\n## {ts} · {source}\n\n'
    for e in entries:
        block += (f"- `{e['key']}` {e['lang'].upper()}: "
                  f"“{clip(show(e['oldVal']), 140)}” → “{clip(show(e['newVal']), 140)}”\n")
    cur = LOG.read_text(encoding='utf-8') if LOG.exists() else '# Partner Gateway Copy Log\n'
    LOG.write_text(cur + block, encoding='utf-8')


def update_inline_log(html, entries, source):
    m = re.search(r'<script type="application/json" id="copyLog">(.*?)</script>',
                  html, re.DOTALL)
    if not m:
        return html
    try:
        lst = json.loads(m.group(1))
    except (json.JSONDecodeError, ValueError):
        lst = []
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')
    add = [{'t': ts, 's': source, 'k': e['key'], 'l': e['lang'],
            'o': clip(show(e['oldVal']), 90), 'n': clip(show(e['newVal']), 90)} for e in entries]
    lst = (add + lst)[:40]
    # `<` must not appear inside a <script> block — escape as < in the JSON.
    js = json.dumps(lst, ensure_ascii=False).replace('<', '\\u003c')
    return html.replace(
        m.group(0),
        '<script type="application/json" id="copyLog">' + js + '</script>')


def apply_overrides(html, overrides):
    """Merge an OVERRIDES map into the #copyStyles JSON block. Mirrors
    apply-homepage-copy.mjs::applyOverrides. Per key: shallow merge, with the
    `style` sub-object deep-merged (empty/null props pruned) and
    img/anim/align/href/hidden clearable via null. A key set to null is deleted
    (reset); array / non-object values (e.g. __order) are set directly.
    Returns (html, count). Idempotent."""
    m = re.search(
        r'<script type="application/json" id="copyStyles">(.*?)</script>',
        html, re.DOTALL)
    if not m:
        return html, 0
    try:
        cur = json.loads(m.group(1) or '{}') or {}
    except (json.JSONDecodeError, ValueError):
        cur = {}
    if not isinstance(cur, dict):
        cur = {}
    count = 0
    for key, val in overrides.items():
        if val is None:
            if key in cur:
                del cur[key]
                count += 1
            continue
        if isinstance(val, list) or not isinstance(val, dict):
            cur[key] = val
            count += 1
            continue
        prev = cur.get(key) or {}
        if not isinstance(prev, dict):
            prev = {}
        nxt = dict(prev)
        nxt.update(val)
        if val.get('style') is not None and isinstance(val.get('style'), dict):
            merged = dict(prev.get('style') or {})
            merged.update(val['style'])
            for sk in list(merged.keys()):
                if merged[sk] is None or merged[sk] == '':
                    del merged[sk]
            if merged:
                nxt['style'] = merged
            else:
                nxt.pop('style', None)
        # Only an EXPLICIT null clears the field (missing key leaves it alone).
        for f in ('img', 'anim', 'align', 'href', 'hidden'):
            if f in val and val[f] is None:
                nxt.pop(f, None)
        cur[key] = nxt
        count += 1
    # `<` must not appear raw inside a <script> block — escape as its unicode
    # escape (same as the copyLog block does).
    out = json.dumps(cur, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')
    built = '<script type="application/json" id="copyStyles">' + out + '</script>'
    html = html[:m.start()] + built + html[m.end():]
    return html, count


def find_tags(html, key):
    return [m.group(0) for m in re.finditer(TAG_RE_TPL % re.escape(key), html)]


def attr_of(tag, lang):
    m = re.search(r'data-' + lang + r'="([^"]*)"', tag)
    return m.group(1) if m else None


def fallback_by_old_text(html, o_vi, o_en):
    """Key drifted (content-derived keys re-key on repo edits) — locate the
    element by its previous text instead. Only a single unambiguous hit counts."""
    hits = []
    for m in re.finditer(TAG_RE_TPL % '[^"]+', html):
        tag = m.group(0)
        tvi = attr_of(tag, 'vi')
        ten = attr_of(tag, 'en')
        if (o_vi and tvi is not None and norm(unesc(tvi)) == o_vi) or \
           (o_en and ten is not None and norm(unesc(ten)) == o_en):
            hits.append(tag)
    uniq = list(dict.fromkeys(hits))
    return uniq if len(uniq) == 1 else []


def patch_tag(tag, lang, new_val):
    """Write data-<lang>="new" into the tag; returns the patched tag (adds the
    attribute if the element never had it)."""
    esc = esc_attr(new_val)
    if attr_of(tag, lang) is not None:
        return re.sub(r'data-' + lang + r'="[^"]*"',
                      lambda _: f'data-{lang}="{esc}"', tag, count=1)
    return tag[:-1] + f' data-{lang}="{esc}">'


def step_summary(lines):
    path = os.environ.get('GITHUB_STEP_SUMMARY')
    if not path:
        return
    with open(path, 'a', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')


def main():
    changes = json.loads(os.environ.get('CHANGES') or '{}')
    overrides = json.loads(os.environ.get('OVERRIDES') or '{}')
    html = FILE.read_text(encoding='utf-8')
    changed = 0
    log_entries = []
    applied_keys = []
    skipped = []  # (key, reason)

    for key, val in changes.items():
        if not KEY_RE.match(key):
            skipped.append((key, 'invalid key'))
            continue
        # Presence decides, not truthiness — '' is a deletion, a real edit.
        vi = norm(val['vi']) if isinstance(val.get('vi'), str) else None
        en = norm(val['en']) if isinstance(val.get('en'), str) else None
        if vi is None and en is None:
            skipped.append((key, 'no vi/en value in payload'))
            continue
        tags = find_tags(html, key)
        via = 'key'
        if not tags:
            o_vi = norm(val.get('o_vi'))
            o_en = norm(val.get('o_en'))
            tags = fallback_by_old_text(html, o_vi, o_en)
            via = 'old-text fallback (key drifted)'
            if not tags:
                skipped.append((key, 'key not found and old-text fallback had no unique match'))
                continue
        first = tags[0]
        old_vi = attr_of(first, 'vi') or ''
        old_en = attr_of(first, 'en') or ''
        if vi is not None and esc_attr(vi) != old_vi:
            log_entries.append({'key': key, 'lang': 'vi', 'oldVal': unesc(old_vi), 'newVal': vi})
        if en is not None and esc_attr(en) != old_en:
            log_entries.append({'key': key, 'lang': 'en', 'oldVal': unesc(old_en), 'newVal': en})
        # Patch EVERY occurrence — keys may be shared across sibling elements.
        any_change = False
        for tag in dict.fromkeys(tags):
            new_tag = tag
            if vi is not None:
                new_tag = patch_tag(new_tag, 'vi', vi)
            if en is not None:
                new_tag = patch_tag(new_tag, 'en', en)
            if new_tag != tag:
                html = html.replace(tag, new_tag)
                any_change = True
        if any_change:
            changed += 1
            applied_keys.append(f'{key} ({via})')
            print(f'✎ {key} [{via}] × {len(tags)} element(s)')
        else:
            skipped.append((key, 'value identical to current — nothing to change'))

    # element style / layout / image / animation overrides (#copyStyles block)
    style_count = 0
    if overrides:
        html, style_count = apply_overrides(html, overrides)
        for k, v in overrides.items():
            # Quote-free summary: this string lands in the copyLog JSON block,
            # and a literal " there would be escaped as \" — which WP's
            # wp_unslash would then corrupt. Strip quotes to stay WP-safe.
            new_val = '∅ (reset)' if v is None else clip(
                json.dumps(v, ensure_ascii=False).replace('"', ''), 120)
            log_entries.append({'key': k, 'lang': 'style',
                                'oldVal': '', 'newVal': new_val})

    if changed or style_count:
        html = update_inline_log(html, log_entries, 'in-page editor')
        FILE.write_text(html, encoding='utf-8')
        append_log(log_entries, 'in-page editor')
        print(f'Applied {changed} text + {style_count} style change(s).')
    else:
        print('Nothing to apply.')

    # Loud, visible reporting — a silently lost edit is the worst outcome.
    summary = [f'## Partner copy apply — {changed} applied, {len(skipped)} skipped']
    for k in applied_keys:
        summary.append(f'- ✅ `{k}`')
    real_failures = []
    for k, why in skipped:
        icon = '⚪' if why.startswith('value identical') else '❌'
        summary.append(f'- {icon} `{k}` — {why}')
        if icon == '❌':
            real_failures.append(f'{k}: {why}')
            print(f'⚠ SKIPPED {k}: {why}', file=sys.stderr)
    step_summary(summary)
    SKIP_FILE.parent.mkdir(parents=True, exist_ok=True)
    SKIP_FILE.write_text('\n'.join(real_failures), encoding='utf-8')


if __name__ == '__main__':
    main()
