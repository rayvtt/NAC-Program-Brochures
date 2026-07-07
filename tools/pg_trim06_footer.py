#!/usr/bin/env python3
"""One-off gateway edits: remove §06 (Gửi Cho Khách Của Bạn), renumber chips to /05,
drop its floating-nav entry, and make the footer fully bilingual (VI/EN).

Idempotent: each edit is guarded; re-running is a no-op once applied.
"""
import re, sys
from pathlib import Path

HTML = Path(__file__).resolve().parent.parent / "Brochures html" / "NAC-PARTNERS.html"
html = HTML.read_text(encoding="utf-8")
changed = 0

# ---- 1) remove the §06 section block ----
if 'id="p6"' in html:
    new = re.sub(r'\n  <section class="sec" id="p6".*?\n  </section>\n', '\n', html, count=1, flags=re.S)
    assert new != html, "§06 section regex did not match"
    html = new; changed += 1

# ---- 2) remove the p6 floating-nav item ----
nav_p6 = re.search(r'\n      <a class="pgnav-item" href="#p6".*?</a>', html)
if nav_p6:
    html = html[:nav_p6.start()] + html[nav_p6.end():]; changed += 1

# ---- 3) renumber the 5 remaining chips 0X / 06 -> 0X / 05 ----
for x in range(1, 6):
    a, b = f"{x:02d} / 06", f"{x:02d} / 05"
    if a in html:
        html = html.replace(a, b, 1); changed += 1

# ---- 4) footer i18n: add data-vi/data-en (+ data-copy) to every mono-lingual footer string ----
def repl(old, new, required=True):
    global html, changed
    if old in html:
        html = html.replace(old, new, 1); changed += 1
    elif required and new not in html:
        raise AssertionError("footer anchor not found: " + old[:70])

# col 1 header — was a bare duplicate of the brand name; make it a proper bilingual nav header
repl('<h3 class="nf-col-h">Nomad Asset Collective</h3>',
     '<h3 class="nf-col-h" data-copy="pg-fcol1" data-vi="Khám Phá" data-en="Explore">Khám Phá</h3>')
repl('<li><a href="https://nomadassetcollective.com/brochures/">Brochures</a></li>',
     '<li><a href="https://nomadassetcollective.com/brochures/" data-copy="pg-flbro" data-vi="Tài Liệu Chương Trình" data-en="Brochures">Tài Liệu Chương Trình</a></li>')

# col 2 — NAC tools
repl('<h3 class="nf-col-h">Công Cụ NAC</h3>',
     '<h3 class="nf-col-h" data-copy="pg-fcol2" data-vi="Công Cụ NAC" data-en="NAC Tools">Công Cụ NAC</h3>')
repl('<li><a href="https://nomadassetcollective.com/so-sanh/">Công Cụ So Sánh</a></li>',
     '<li><a href="https://nomadassetcollective.com/so-sanh/" data-copy="pg-ft1" data-vi="Công Cụ So Sánh" data-en="Comparison Tool">Công Cụ So Sánh</a></li>')
repl('<li><a href="https://nomadassetcollective.com/tu-van-nhanh/">Công Cụ Tư Vấn</a></li>',
     '<li><a href="https://nomadassetcollective.com/tu-van-nhanh/" data-copy="pg-ft2" data-vi="Công Cụ Tư Vấn" data-en="Quick Advisor">Công Cụ Tư Vấn</a></li>')
repl('<li><a href="https://nomadassetcollective.com/nac-residence-index/">Công Cụ Index</a></li>',
     '<li><a href="https://nomadassetcollective.com/nac-residence-index/" data-copy="pg-ft3" data-vi="Công Cụ Index" data-en="Index Tool">Công Cụ Index</a></li>')

# col 3 — contact
repl('<h3 class="nf-col-h">Liên Hệ</h3>',
     '<h3 class="nf-col-h" data-copy="pg-fcol3" data-vi="Liên Hệ" data-en="Contact">Liên Hệ</h3>')
repl('<address style="font-style:normal">Tòa Nhà Sonatus, Sentry, 15B Lê Thánh Tôn, TP.HCM</address>',
     '<address style="font-style:normal" data-copy="pg-faddr" data-vi="Tòa Nhà Sonatus, Sentry, 15B Lê Thánh Tôn, TP.HCM" data-en="Sonatus Building, Sentry, 15B Le Thanh Ton, District 1, HCMC">Tòa Nhà Sonatus, Sentry, 15B Lê Thánh Tôn, TP.HCM</address>')

# bottom bar
repl('<div>© <span>2026</span> Nomad Asset Collective. All rights reserved.</div>',
     '<div>© <span>2026</span> Nomad Asset Collective · <span data-copy="pg-fcopy" data-vi="Bảo lưu mọi quyền." data-en="All rights reserved.">Bảo lưu mọi quyền.</span></div>')
repl('<div class="nf-powered">Powered by <strong>NAC Global</strong></div>',
     '<div class="nf-powered"><span data-copy="pg-fpow" data-vi="Vận hành bởi" data-en="Powered by">Vận hành bởi</span> <strong>NAC Global</strong></div>')

HTML.write_text(html, encoding="utf-8")
print(f"applied ({changed} edits) →", HTML.name)
