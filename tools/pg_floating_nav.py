#!/usr/bin/env python3
"""Replace the cluttered top-bar section links on NAC-PARTNERS.html with a single
frozen floating section navigator.

- The top bar keeps only the logo + language toggle (declutters it on every viewport;
  mobile previously had NO section nav at all since .nav-center was display:none).
- A fixed, always-visible round toggle sits bottom-right. Collapsed it shows the current
  section number as a badge; tapped it expands a compact list of all sections. Clicking a
  section smooth-scrolls to it and closes the menu. A scroll-spy keeps the active section
  highlighted and the badge current, so the menu doubles as a "where am I / jump up-down"
  control. Works identically on desktop and mobile.

Idempotent: refuses to run if the floating nav is already present.
WP-safe: no inline handlers, no double-quote escapes in the script.
Reuses the 7 existing nav-link data-copy keys so the ?edit=1 copy editor still edits labels.
"""
import re, sys
from pathlib import Path

HTML = Path(__file__).resolve().parent.parent / "Brochures html" / "NAC-PARTNERS.html"
html = HTML.read_text(encoding="utf-8")
if 'id="pgnav"' in html:
    sys.exit("already applied — #pgnav present; refusing to double-insert")

# ---------------------------------------------------------------- 1) CSS
css = """
/* ===== Frozen floating section navigator (replaces the crowded top-bar links) ===== */
.sec,.ctaband{scroll-margin-top:74px}
.pgnav{position:fixed;right:20px;bottom:20px;z-index:75;display:flex;flex-direction:column;align-items:flex-end;gap:10px}
.pgnav-panel{display:none;flex-direction:column;gap:2px;background:#fff;border:1px solid var(--border);border-radius:16px;box-shadow:0 18px 48px rgba(24,0,173,.20);padding:8px;min-width:214px;max-width:78vw;animation:pgnavIn .18s ease both}
.pgnav.open .pgnav-panel{display:flex}
.pgnav-head{font-size:10px;font-weight:700;letter-spacing:1.7px;text-transform:uppercase;color:var(--text4);padding:7px 11px 5px}
.pgnav-item{display:flex;align-items:center;gap:12px;padding:9px 12px;border-radius:11px;text-decoration:none;color:var(--text2);font-size:13.5px;font-weight:600;transition:background .13s,color .13s}
.pgnav-item:hover{background:var(--bg2);color:var(--text)}
.pgnav-item.active{background:rgba(24,0,173,.07);color:var(--blue)}
.pgnav-num{font-family:'Playfair Display',serif;font-size:13.5px;font-weight:700;color:var(--text4);width:23px;flex-shrink:0;text-align:center}
.pgnav-item.active .pgnav-num{color:var(--orange)}
.pgnav-ic{width:15px;flex-shrink:0;display:flex;justify-content:center;color:var(--text4)}
.pgnav-ic svg{width:15px;height:15px}
.pgnav-item.active .pgnav-ic{color:var(--orange)}
.pgnav-toggle{width:54px;height:54px;border-radius:50%;background:var(--blue);color:#fff;border:none;cursor:pointer;box-shadow:0 12px 30px rgba(24,0,173,.36);display:flex;align-items:center;justify-content:center;position:relative;transition:transform .15s,background .15s}
.pgnav-toggle:hover{background:var(--blue-dk);transform:translateY(-2px)}
.pgnav-toggle svg{width:23px;height:23px}
.pgnav-i-close{display:none}
.pgnav.open .pgnav-i-open{display:none}
.pgnav.open .pgnav-i-close{display:block}
.pgnav-badge{position:absolute;top:-3px;right:-3px;min-width:21px;height:21px;padding:0 5px;border-radius:11px;background:var(--orange);color:#fff;font-size:11px;font-weight:800;line-height:1;display:flex;align-items:center;justify-content:center;box-shadow:0 2px 8px rgba(0,0,0,.22);font-family:'Playfair Display',serif}
.pgnav.open .pgnav-badge{display:none}
@keyframes pgnavIn{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}
@media(max-width:760px){.pgnav{right:14px;bottom:14px}}
@media(prefers-reduced-motion:reduce){.pgnav-panel{animation:none}.pgnav-toggle{transition:none}}
"""
anchor = "@media(prefers-reduced-motion:reduce){.hero-orb"
assert anchor in html, "reduced-motion CSS anchor not found"
html = html.replace(anchor, css + "\n" + anchor, 1)

# ---------------------------------------------------------------- 2) empty the top-bar center
nav_block = """    <div class="nav-center">
      <a class="nav-link" href="#p1" data-copy="pg-331156" data-vi="01 · Quy Trình" data-en="01 · Process">01 · Quy Trình</a>
      <a class="nav-link" href="#p2" data-copy="pg-543209" data-vi="02 · Bộ Công Cụ" data-en="02 · Toolkit">02 · Bộ Công Cụ</a>
      <a class="nav-link" href="#p3" data-copy="pg-9d4254" data-vi="03 · Xem Trực Tiếp" data-en="03 · Live Demo">03 · Xem Trực Tiếp</a>
      <a class="nav-link" href="#p4" data-copy="pg-7711ab" data-vi="04 · Case Study" data-en="04 · Case Studies">04 · Case Study</a>
      <a class="nav-link" href="#p5" data-copy="pg-114e91" data-vi="05 · Hoa Hồng" data-en="05 · Economics">05 · Hoa Hồng</a>
      <a class="nav-link" href="#p6" data-copy="pg-8aaa88" data-vi="06 · Chia Sẻ" data-en="06 · Share">06 · Chia Sẻ</a>
      <a class="nav-link" href="#contact" data-copy="pg-4df839" data-vi="Liên Hệ" data-en="Contact">Liên Hệ</a>
    </div>"""
assert nav_block in html, "nav-center block not found verbatim"
html = html.replace(nav_block, '    <div class="nav-center"></div>', 1)

# ---------------------------------------------------------------- 3) floating nav markup (inside #nacMain)
def item(sec, num, key, vi, en, icon=""):
    numhtml = f'<span class="pgnav-num">{num}</span>' if num else f'<span class="pgnav-ic">{icon}</span>'
    return (f'      <a class="pgnav-item" href="#{sec}" data-sec="{sec}">{numhtml}'
            f'<span class="pgnav-lab" data-copy="{key}" data-vi="{vi}" data-en="{en}">{vi}</span></a>')

mail_ic = ("<svg viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='1.8' "
           "stroke-linecap='round' stroke-linejoin='round' aria-hidden='true'>"
           "<rect x='3' y='5' width='18' height='14' rx='2'/><path d='M3 7l9 6 9-6'/></svg>")
nav = f"""
  <!-- Frozen floating section navigator -->
  <nav class="pgnav" id="pgnav" aria-label="Mục lục">
    <div class="pgnav-panel" id="pgnavPanel">
      <div class="pgnav-head" data-copy="pg-navmenu" data-vi="Mục lục" data-en="Sections">Mục lục</div>
{item("p1","01","pg-331156","Quy Trình","Process")}
{item("p2","02","pg-543209","Bộ Công Cụ","Toolkit")}
{item("p3","03","pg-9d4254","Xem Trực Tiếp","Live Demo")}
{item("p4","04","pg-7711ab","Case Study","Case Studies")}
{item("p5","05","pg-114e91","Hoa Hồng","Economics")}
{item("p6","06","pg-8aaa88","Chia Sẻ","Share")}
{item("contact","","pg-4df839","Liên Hệ","Contact",mail_ic)}
    </div>
    <button class="pgnav-toggle" id="pgnavToggle" type="button" aria-expanded="false" aria-controls="pgnavPanel" aria-label="Mở mục lục">
      <svg class="pgnav-i-open" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16"/></svg>
      <svg class="pgnav-i-close" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>
      <span class="pgnav-badge" id="pgnavBadge">01</span>
    </button>
  </nav>
"""
main_end = "</div><!-- /#nacMain -->"
assert main_end in html
html = html.replace(main_end, nav + main_end, 1)

# ---------------------------------------------------------------- 4) behaviour script
script = """
<script>
/* ===== Frozen floating section navigator: toggle + scroll-spy + smooth-jump ===== */
(function(){
  var nav = document.getElementById('pgnav');
  if (!nav) return;
  var toggle = document.getElementById('pgnavToggle');
  var badge = document.getElementById('pgnavBadge');
  var items = [].slice.call(nav.querySelectorAll('.pgnav-item'));
  var ids = items.map(function(a){ return a.getAttribute('data-sec'); });

  function open(v){
    nav.classList.toggle('open', v);
    toggle.setAttribute('aria-expanded', v ? 'true' : 'false');
  }
  toggle.addEventListener('click', function(e){ e.stopPropagation(); open(!nav.classList.contains('open')); });
  document.addEventListener('click', function(e){ if (nav.classList.contains('open') && !nav.contains(e.target)) open(false); });
  document.addEventListener('keydown', function(e){ if (e.key === 'Escape') open(false); });
  items.forEach(function(a){ a.addEventListener('click', function(){ open(false); }); });

  function setActive(id){
    var found = null;
    items.forEach(function(a){
      var on = a.getAttribute('data-sec') === id;
      a.classList.toggle('active', on);
      if (on) found = a;
    });
    if (found && badge){
      var num = found.querySelector('.pgnav-num');
      if (num && /\\d/.test(num.textContent)) { badge.textContent = num.textContent.trim(); badge.style.display = ''; }
      else { badge.style.display = 'none'; }
    }
  }

  if ('IntersectionObserver' in window){
    var vis = {};
    var io = new IntersectionObserver(function(entries){
      entries.forEach(function(en){ vis[en.target.id] = en.isIntersecting ? en.intersectionRatio : 0; });
      var best = null, r = 0;
      ids.forEach(function(id){ if ((vis[id] || 0) > r){ r = vis[id]; best = id; } });
      if (best) setActive(best);
    }, { threshold: [0.12, 0.4, 0.75], rootMargin: '-58px 0px -42% 0px' });
    ids.forEach(function(id){ var el = document.getElementById(id); if (el) io.observe(el); });
  }
})();
</script>
"""
tw = "\n<!-- Twemoji:"
assert tw in html
html = html.replace(tw, "\n" + script + tw, 1)

HTML.write_text(html, encoding="utf-8")
print("floating nav injected into", HTML.name)
