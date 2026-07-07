#!/usr/bin/env python3
"""Subtly showcase Ray's IMC certificate on the partner gateway:
  - a small framed cert thumbnail + caption inside the footer's IMC credibility block
  - click → a lightbox of the full certificate
The image is served from the repo's GitHub Pages (fetched only when the lightbox opens).
Idempotent. WP-safe (no inline handlers / \\" escapes).
"""
import sys
from pathlib import Path

HTML = Path(__file__).resolve().parent.parent / "Brochures html" / "NAC-PARTNERS.html"
CERT = "https://rayvtt.github.io/NAC-Program-Brochures/assets/ray-imc-cert.jpg"
html = HTML.read_text(encoding="utf-8")
if 'id="pgCertLb"' in html:
    sys.exit("already applied — #pgCertLb present")

def need(s):
    if s not in html:
        raise AssertionError("anchor not found: " + s[:70])

# 1) CSS — appended after the VI-only / picker CSS block
anchor = ".pgpick-flag{font-size:22px;line-height:1;flex-shrink:0}"
need(anchor)
css = anchor + """
/* Founder IMC certificate — subtle footer showcase + lightbox */
.nf-cert{display:inline-flex;align-items:center;gap:13px;margin-top:18px;background:none;border:none;padding:0;cursor:pointer;text-align:left;font-family:inherit}
.nf-cert-frame{flex-shrink:0;width:48px;height:66px;border-radius:4px;overflow:hidden;border:1px solid var(--border);box-shadow:0 3px 10px rgba(15,26,54,.12);background:#fff;transition:transform .18s,box-shadow .18s}
.nf-cert:hover .nf-cert-frame{transform:translateY(-2px);box-shadow:0 8px 20px rgba(24,0,173,.16)}
.nf-cert-frame img{width:100%;height:100%;object-fit:cover;object-position:top;display:block}
.nf-cert-meta{display:flex;flex-direction:column;gap:1px}
.nf-cert-t{font-size:12.5px;font-weight:700;color:var(--text)}
.nf-cert-s{font-size:11.5px;color:var(--text3);line-height:1.42}
.nf-cert-v{font-size:11.5px;font-weight:600;color:var(--blue);margin-top:2px}
.nf-cert:hover .nf-cert-v{color:var(--orange)}
.pg-certlb{position:fixed;inset:0;z-index:96;background:rgba(10,8,34,.86);display:none;align-items:center;justify-content:center;padding:28px}
.pg-certlb.open{display:flex}
.pg-certlb img{max-width:min(560px,92vw);max-height:90vh;width:auto;height:auto;border-radius:6px;box-shadow:0 30px 80px rgba(0,0,0,.5);background:#fff}
.pg-certlb-x{position:absolute;top:18px;right:20px;width:40px;height:40px;border-radius:50%;background:rgba(255,255,255,.14);border:1px solid rgba(255,255,255,.3);color:#fff;font-size:16px;cursor:pointer}
.pg-certlb-x:hover{background:rgba(255,255,255,.24)}"""
html = html.replace(anchor, css, 1)

# 2) footer cert chip — inserted right before the contact line, under the IMC block
contact_line = '<p class="nf-contact-line" data-copy="pg-03b79a"'
need(contact_line)
chip = ('<button class="nf-cert" type="button" data-pg-cert aria-label="View founder IMC certificate">'
        f'<span class="nf-cert-frame"><img src="{CERT}" alt="IMC Certification in Investment Migration — Thanh Tu (Ray) Vu" loading="lazy"></span>'
        '<span class="nf-cert-meta">'
        '<span class="nf-cert-t" data-copy="pg-cert-t" data-vi="Nhà sáng lập Ray Vũ" data-en="Founder — Ray Vũ">Nhà sáng lập Ray Vũ</span>'
        '<span class="nf-cert-s" data-copy="pg-cert-s" data-vi="Chứng nhận IMC về Đầu tư Định cư · Geneva 2026" data-en="IMC-Certified in Investment Migration · Geneva 2026">Chứng nhận IMC về Đầu tư Định cư · Geneva 2026</span>'
        '<span class="nf-cert-v" data-copy="pg-cert-v" data-vi="Xem chứng chỉ →" data-en="View certificate →">Xem chứng chỉ →</span>'
        '</span></button>\n        ')
html = html.replace(contact_line, chip + contact_line, 1)

# 3) lightbox (inside #nacMain)
main_end = "</div><!-- /#nacMain -->"
need(main_end)
lb = (f'\n  <div class="pg-certlb" id="pgCertLb" role="dialog" aria-modal="true" aria-label="IMC Certificate — Ray Vu">'
      f'<button class="pg-certlb-x" type="button" aria-label="Đóng">✕</button>'
      f'<img src="{CERT}" alt="IMC Certification in Investment Migration — Thanh Tu (Ray) Vu, Geneva 2026" loading="lazy"></div>\n')
html = html.replace(main_end, lb + main_end, 1)

# 4) behaviour script
script = """
<script>
/* ===== Founder IMC certificate lightbox ===== */
(function(){
  var lb = document.getElementById('pgCertLb');
  if (!lb) return;
  function set(v){ lb.classList.toggle('open', v); }
  document.addEventListener('click', function(e){
    if (e.target.closest && e.target.closest('[data-pg-cert]')){ e.preventDefault(); set(true); return; }
    if (e.target === lb || (e.target.closest && e.target.closest('.pg-certlb-x'))){ set(false); }
  });
  document.addEventListener('keydown', function(e){ if (e.key === 'Escape') set(false); });
})();
</script>
"""
tw = "\n<!-- Twemoji:"
need(tw)
html = html.replace(tw, "\n" + script + tw, 1)

HTML.write_text(html, encoding="utf-8")
print("founder cert showcase + lightbox injected")
