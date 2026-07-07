#!/usr/bin/env python3
"""Country Market Briefs on the partner gateway:
  - adds a §03 live-demo frame for the Country Market Brief (previews the Greece CLP)
  - turns the §02 Country Market Brief tool + the §03 demo's open link into a country PICKER
    (a modal grid of every live CLP) instead of dead-ending on one country

Live CLPs (verified 2026-07-07): greece cyprus turkey uae uk panama malaysia montenegro thailand vietnam.
Idempotent: refuses to run if the picker is already present. WP-safe (no inline handlers / \\" escapes).
"""
import sys
from pathlib import Path

HTML = Path(__file__).resolve().parent.parent / "Brochures html" / "NAC-PARTNERS.html"
html = HTML.read_text(encoding="utf-8")
if 'id="pgpickScrim"' in html:
    sys.exit("already applied — #pgpickScrim present")

def need(s):
    if s not in html:
        raise AssertionError("anchor not found: " + s[:80])

# ---- 1) CSS (after the VI-only rule) ----
css_anchor = 'html[lang="en"] .pg-vi-only{display:none}'
need(css_anchor)
css = css_anchor + """
/* Country Market Briefs picker */
.pgpick-scrim{position:fixed;inset:0;background:rgba(12,6,48,.55);z-index:90;display:none;align-items:center;justify-content:center;padding:20px}
.pgpick-scrim.open{display:flex}
.pgpick-modal{background:#fff;border-radius:20px;max-width:640px;width:100%;max-height:86vh;overflow:auto;padding:26px 24px;box-shadow:0 24px 60px rgba(0,0,0,.32);animation:pgnavIn .2s ease both}
.pgpick-head{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;margin-bottom:16px}
.pgpick-title{font-family:'Playfair Display',serif;font-size:22px;color:var(--text);line-height:1.2}
.pgpick-sub{font-size:13px;color:var(--text3);margin-top:4px}
.pgpick-x{background:var(--bg2);border:none;border-radius:9px;width:34px;height:34px;font-size:15px;cursor:pointer;color:var(--text2);flex-shrink:0}
.pgpick-x:hover{background:var(--bg3)}
.pgpick-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}
@media(max-width:560px){.pgpick-grid{grid-template-columns:repeat(2,1fr)}}
.pgpick-tile{display:flex;align-items:center;gap:11px;padding:12px 14px;border:1px solid var(--border);border-radius:12px;text-decoration:none;color:var(--text);font-weight:600;font-size:14px;transition:border-color .13s,background .13s}
.pgpick-tile:hover{border-color:var(--orange);background:var(--bg2)}
.pgpick-flag{font-size:22px;line-height:1;flex-shrink:0}"""
html = html.replace(css_anchor, css, 1)

# ---- 2) §02 card → opens the picker; retitle its CTA ----
card_a = '<a class="dcard" href="https://nomadassetcollective.com/property-hub-bat-dong-san/greece/" target="_blank" rel="noopener">'
need(card_a)
html = html.replace(card_a, '<a class="dcard" data-pg-picker href="https://nomadassetcollective.com/property-hub-bat-dong-san/greece/" target="_blank" rel="noopener">', 1)
cta = 'data-copy="pg-mb-go" data-vi="Mở Market Brief →" data-en="Open a Market Brief →">Mở Market Brief →'
need(cta)
html = html.replace(cta, 'data-copy="pg-mb-go" data-vi="Chọn quốc gia →" data-en="Browse by country →">Chọn quốc gia →', 1)

# ---- 3) §03 new live-demo frame (before the snap-grid closes) ----
grid_end = 'không theo cảm tính.”</div></div>\n        </div>\n      </div>'
need(grid_end)
demo = """không theo cảm tính.”</div></div>
        </div>
        <div class="snap">
          <div class="snap-frame"><iframe data-src="https://nomadassetcollective.com/property-hub-bat-dong-san/greece/" loading="lazy" title="Country Market Brief — Greece" tabindex="-1"></iframe>
            <a class="snap-open" data-pg-picker href="https://nomadassetcollective.com/property-hub-bat-dong-san/greece/" target="_blank" rel="noopener"><span data-copy="pg-058d3f-5" data-vi="Chọn quốc gia →" data-en="Browse by country →">Chọn quốc gia →</span></a></div>
          <div class="snap-cap"><h3><svg class="ni" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx='12' cy='12' r='9'/><path d='M3 12h18M12 3a15 15 0 010 18M12 3a15 15 0 000 18'/></svg><span data-copy="pg-mbd-h" data-vi="Country Market Brief" data-en="Country Market Brief">Country Market Brief</span></h3>
            <p data-copy="pg-mbd-p" data-vi="Tổng quan thị trường theo từng quốc gia — ví dụ trực tiếp: Hy Lạp." data-en="A market brief per country — live example: Greece.">Tổng quan thị trường theo từng quốc gia — ví dụ trực tiếp: Hy Lạp.</p>
            <div class="snap-pitch" data-copy="pg-mbd-q" data-vi="“Mỗi quốc gia một trang tổng quan thị trường — chính sách, giá, lợi suất và dự án tiêu biểu, cập nhật realtime.”" data-en="“One market-overview page per country — policy, pricing, yields and flagship projects, updated live.”">“Mỗi quốc gia một trang tổng quan thị trường — chính sách, giá, lợi suất và dự án tiêu biểu, cập nhật realtime.”</div></div>
        </div>
      </div>"""
html = html.replace(grid_end, demo, 1)

# ---- 4) picker modal (inside #nacMain) ----
CLP = "https://nomadassetcollective.com/property-hub-bat-dong-san/"
COUNTRIES = [
    ("greece", "🇬🇷", "Hy Lạp", "Greece"),
    ("cyprus", "🇨🇾", "Đảo Síp", "Cyprus"),
    ("turkey", "🇹🇷", "Thổ Nhĩ Kỳ", "Türkiye"),
    ("uae", "🇦🇪", "UAE", "UAE"),
    ("uk", "🇬🇧", "Anh Quốc", "United Kingdom"),
    ("panama", "🇵🇦", "Panama", "Panama"),
    ("malaysia", "🇲🇾", "Malaysia", "Malaysia"),
    ("montenegro", "🇲🇪", "Montenegro", "Montenegro"),
    ("thailand", "🇹🇭", "Thái Lan", "Thailand"),
    ("vietnam", "🇻🇳", "Việt Nam", "Vietnam"),
]
tiles = "\n".join(
    f'        <a class="pgpick-tile" href="{CLP}{slug}/" target="_blank" rel="noopener"><span class="pgpick-flag">{flag}</span>'
    f'<span data-copy="pg-pk-{slug}" data-vi="{vi}" data-en="{en}">{vi}</span></a>'
    for slug, flag, vi, en in COUNTRIES
)
modal = f"""
  <!-- Country Market Briefs picker -->
  <div class="pgpick-scrim" id="pgpickScrim" role="dialog" aria-modal="true" aria-label="Country Market Briefs">
    <div class="pgpick-modal">
      <div class="pgpick-head">
        <div>
          <div class="pgpick-title" data-copy="pg-pick-t" data-vi="Tổng Quan Thị Trường Theo Quốc Gia" data-en="Country Market Briefs">Tổng Quan Thị Trường Theo Quốc Gia</div>
          <div class="pgpick-sub" data-copy="pg-pick-s" data-vi="Chọn một quốc gia để mở trang tổng quan thị trường tương ứng." data-en="Pick a country to open its market brief.">Chọn một quốc gia để mở trang tổng quan thị trường tương ứng.</div>
        </div>
        <button class="pgpick-x" type="button" aria-label="Đóng">✕</button>
      </div>
      <div class="pgpick-grid">
{tiles}
      </div>
    </div>
  </div>
"""
main_end = "</div><!-- /#nacMain -->"
need(main_end)
html = html.replace(main_end, modal + main_end, 1)

# ---- 5) picker behaviour script ----
script = """
<script>
/* ===== Country Market Briefs picker — open on any [data-pg-picker], close on ✕ / scrim / Esc / tile ===== */
(function(){
  var scrim = document.getElementById('pgpickScrim');
  if (!scrim) return;
  function set(v){ scrim.classList.toggle('open', v); if (v && typeof nacTwemoji === 'function') nacTwemoji(); }
  document.addEventListener('click', function(e){
    var trig = e.target.closest ? e.target.closest('[data-pg-picker]') : null;
    if (trig){ e.preventDefault(); set(true); return; }
    if (e.target === scrim || (e.target.closest && e.target.closest('.pgpick-x'))){ set(false); return; }
    if (e.target.closest && e.target.closest('.pgpick-tile')){ set(false); }
  });
  document.addEventListener('keydown', function(e){ if (e.key === 'Escape') set(false); });
})();
</script>
"""
tw = "\n<!-- Twemoji:"
need(tw)
html = html.replace(tw, "\n" + script + tw, 1)

HTML.write_text(html, encoding="utf-8")
print("country-briefs picker + §03 demo injected")
