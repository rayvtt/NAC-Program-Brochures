#!/usr/bin/env python3
"""Enrich NAC-PARTNERS.html — the 2026-07-07 partner-capture build.

Adds, in one deterministic pass over the deck:
  1. Personalized greeting chip (uses name/contact now returned by /partner-access)
  2. §05 — referral earnings calculator + partner tier ladder
  3. §06 — forward-ready client snippets (copy VI/EN) + co-branded printable client pack
  4. Founder-video section slot (hidden until PG_VIDEO_URL is set)
  5. 📡 telemetry beacons → Worker POST /pg-view (section reveals, CTA/tool clicks, calc/copy/print)
  6. PROGRAM JSON dataset generated from data/*_payload.json (+ hero-stat extraction for the
     four programs whose payloads lack stats), embedded as <script id=pgPrograms>

Idempotence: refuses to run twice (checks for the pgPrograms marker).
WP-safety: no inline handlers, no double-quote escapes in JS, JSON block escapes '<'.
"""
import hashlib, json, re, sys, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HTML = ROOT / "Brochures html" / "NAC-PARTNERS.html"

html = HTML.read_text(encoding="utf-8")
if 'id="pgPrograms"' in html:
    sys.exit("already enriched — pgPrograms block present; refusing to double-insert")

# ---------------------------------------------------------------- data-copy keys
existing_keys = set(re.findall(r'data-copy="([^"]+)"', html))
def ckey(vi: str) -> str:
    base = "pg-" + hashlib.sha1(vi.encode("utf-8")).hexdigest()[:6]
    k, n = base, 1
    while k in existing_keys:
        k = f"{base}-{n}"; n += 1
    existing_keys.add(k)
    return k

def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")

def B(vi: str, en: str) -> str:
    """bilingual attribute pack: data-copy + data-vi + data-en (text content stays VI)"""
    return f'data-copy="{ckey(vi)}" data-vi="{esc(vi)}" data-en="{esc(en)}"'

# ---------------------------------------------------------------- program dataset
URLS = {
 "portugal":"https://nomadassetcollective.com/brochures/chuong-trinh-bo-dao-nha-golden-visa/",
 "greece":"https://nomadassetcollective.com/brochures/residences-chuong-trinh-hy-lap-golden-visa/",
 "cyprus":"https://nomadassetcollective.com/brochures/chuong-trinh-dao-sip-rbi-residence-by-investment/",
 "turkey":"https://nomadassetcollective.com/brochures/chuong-trinh-tho-nhi-ky-cbi-citizenship-by-investment/",
 "uae":"https://nomadassetcollective.com/brochures/chuong-trinh-uae-golden-visa-2/",
 "uk":"https://nomadassetcollective.com/brochures/chuong-trinh-uk-thuong-tru-visa-dau-tu-rbi/",
 "malta":"https://nomadassetcollective.com/brochures/chuong-trinh-malta-thuong-tru-nhan-rbi/",
 "stkitts":"https://nomadassetcollective.com/brochures/chuong-trinh-si-kitts-nevis-quoc-tich/",
 "thailand":"https://nomadassetcollective.com/brochures/chuong-trinh-thai-lan-cu-tru-dai-han-ltr-rbi/",
 "newzealand":"https://nomadassetcollective.com/brochures/chuong-trinh-new-zealand-rbi-dau-tu-di-tru/",
 "panama":"https://nomadassetcollective.com/brochures/chuong-trinh-panama-rbi-quyen-cu-tru-vinh-vien/",
 "malaysia":"https://nomadassetcollective.com/brochures/chuong-trinh-malaysia-rbi-mm2h-dau-tu-quyen-cu-tru/",
 "antigua":"https://nomadassetcollective.com/brochures/chuong-trinh-antigua-barbuda-cbi/",
 "italy":"https://nomadassetcollective.com/brochures/chuong-trinh-y-italy-rbi-qua-dau-tu-bds/",
 "montenegro":"https://nomadassetcollective.com/brochures/chuong-trinh-montenengro-rbi-qua-dau-tu-bds/",
}
# curated display order: EU → Türkiye/Gulf/UK → Caribbean CBI → Americas → APAC
ORDER = ["greece","portugal","cyprus","malta","italy","montenegro","turkey","uae","uk",
         "antigua","stkitts","panama","malaysia","thailand","newzealand"]
# approximate USD value of the entry threshold (calculator baseline; display strings stay original)
USD = {"greece":270_000,"portugal":270_000,"cyprus":324_000,"malta":197_000,"italy":270_000,
       "montenegro":108_000,"turkey":400_000,"uae":545_000,"uk":63_000,"antigua":230_000,
       "stkitts":250_000,"panama":300_000,"malaysia":150_000,"thailand":480_000,"newzealand":3_000_000}
LBL_EN = {"BĐS tối thiểu":"Min. real estate","Nhận thẻ cư trú":"Residence card in","Visa-Free":"Visa-free",
          "Đầu tư tối thiểu":"Min. investment","Ký quỹ tối thiểu":"Min. deposit","Cấp visa":"Visa issued in",
          "Cấp thị thực":"Visa issued in","Thời hạn cư trú":"Residence validity","Thành viên đầy đủ":"Full member",
          "Cấp cư trú":"Residence in","Lộ trình quốc tịch":"Citizenship path","Xử lý hồ sơ":"Processing",
          "Đóng góp tối thiểu":"Min. contribution","Quy trình cấp tốc":"Fast-track process","Quốc gia miễn visa":"Visa-free countries",
          "Nhận quốc tịch":"Citizenship in","Vốn kinh doanh":"Business capital","Visa gia hạn":"Renewable visa",
          "Visa-Free (EU)":"Visa-free (EU)","Nhận PR trực tiếp":"Direct PR in"}
TIME_EN = [("tháng","months"),("năm","years"),("ngày","days"),("tuần","weeks")]

GAPS = {  # programs whose payloads carry no hero_stats — stats lifted from the live brochure HTML
 "antigua":{"nv":"Antigua & Barbuda CBI","ne":"Antigua & Barbuda CBI","f":"🇦🇬","c":"CBI",
   "st":[{"n":"$230K","lv":"NDF tối thiểu","le":"Min. NDF contribution"},{"n":"3–6 tháng","lv":"Nhận quốc tịch","le":"Citizenship in"},{"n":"150+","lv":"Visa-Free (UK + EU)","le":"Visa-free (UK + EU)"}],
   "dv":"Quốc tịch Caribbean cho cả gia đình trong 3–6 tháng qua đóng góp NDF — hộ chiếu miễn visa hơn 150 quốc gia gồm UK và Schengen.",
   "de":"Caribbean citizenship for the whole family in 3–6 months via the NDF contribution — a passport with visa-free access to 150+ countries including the UK and Schengen."},
 "malta":{"nv":"Malta Thường Trú Nhân","ne":"Malta Permanent Residence","f":"🇲🇹","c":"RBI",
   "st":[{"n":"€182K","lv":"Tổng tối thiểu (thuê)","le":"Total minimum (rent route)"},{"n":"6–12 tháng","lv":"Thời gian xử lý","le":"Processing time"},{"n":"Vĩnh viễn","lv":"Thời hạn cư trú","le":"Residence validity"}],
   "dv":"Thường trú nhân vĩnh viễn tại Malta — thành viên EU — qua lộ trình thuê hoặc mua bất động sản kèm đóng góp, đi lại tự do khối Schengen.",
   "de":"Permanent residence in Malta — an EU member state — via a rent-or-buy route with a contribution, with visa-free Schengen mobility."},
 "italy":{"nv":"Visa Đầu Tư Ý","ne":"Italy Investor Visa","f":"🇮🇹","c":"RBI",
   "st":[{"n":"€250K","lv":"Mức đầu tư tối thiểu","le":"Min. investment"},{"n":"2 năm","lv":"Visa cư trú ban đầu","le":"Initial residence visa"},{"n":"10 năm","lv":"Đường đến quốc tịch","le":"Path to citizenship"}],
   "dv":"Visa đầu tư Ý từ €250K vào doanh nghiệp hoặc startup — cư trú EU + Schengen với lộ trình quốc tịch 10 năm.",
   "de":"Italy's investor visa from €250K into a company or startup — EU + Schengen residence with a 10-year path to citizenship."},
 "montenegro":{"nv":"Cư Trú Montenegro","ne":"Montenegro Residence","f":"🇲🇪","c":"RBI",
   "st":[{"n":"€100K","lv":"Mức thực tế","le":"Practical entry level"},{"n":"1 năm","lv":"Visa cư trú (gia hạn)","le":"Renewable residence visa"},{"n":"10 năm","lv":"Đường quốc tịch","le":"Path to citizenship"}],
   "dv":"Cư trú Montenegro qua sở hữu bất động sản từ khoảng €100K — quốc gia ứng viên EU với chi phí vào thấp nhất châu Âu.",
   "de":"Montenegro residence through property ownership from around €100K — an EU-candidate country with Europe's lowest entry cost."},
}

def first_sentence(s, cap=185):
    s = re.sub(r"<[^>]+>", "", s or "").strip()
    if not s: return s
    m = re.match(r"^(.{40,%d}?[.!?…])\s" % cap, s + " ")
    out = m.group(1) if m else s[:cap].rsplit(" ", 1)[0] + "…"
    return out

def time_en(s):
    out = s
    for vi, en in TIME_EN: out = out.replace(vi, en)
    return out

programs = []
for k in ORDER:
    u = URLS[k]
    if k in GAPS:
        g = GAPS[k]
        st = g["st"]
        p = {"k":k,"f":g["f"],"c":g["c"],"nv":g["nv"],"ne":g["ne"],"dv":g["dv"],"de":g["de"],"st":st}
    else:
        d = json.loads((ROOT / "data" / f"{k}_payload.json").read_text(encoding="utf-8"))
        raw = d.get("hero_stats") or []
        if isinstance(raw, str): raw = json.loads(raw)
        st = []
        for x in raw[:3]:
            lv = x.get("lbl_vi") or x.get("lbl") or ""
            le = x.get("lbl_en") or LBL_EN.get(lv, lv)
            st.append({"n": x.get("num",""), "lv": lv, "le": le})
        p = {"k":k,"f":d.get("flag",""),"c":d.get("program_code",""),
             "nv":d.get("program_vi") or d.get("program_en"),"ne":d.get("program_en") or d.get("program_vi"),
             "dv":first_sentence(d.get("hero_desc_vi")),"de":first_sentence(d.get("hero_desc_en")),"st":st}
    p["min"] = st[0]["n"] if st else ""
    p["tv"]  = st[1]["n"] if len(st) > 1 else ""
    p["te"]  = time_en(p["tv"])
    p["usd"] = USD[k]
    p["u"]   = u
    programs.append(p)

pg_json = json.dumps(programs, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
print(f"dataset: {len(programs)} programs")

# ---------------------------------------------------------------- 1) CSS
css = """
/* ===== Partner-capture build (greeting · §05 calc+tiers · §06 share+pack · video) ===== */
.pg-greet{display:inline-flex;align-items:center;gap:8px;background:rgba(255,255,255,.13);border:1px solid rgba(255,255,255,.28);border-radius:999px;padding:7px 18px;color:#fff;font-size:13px;font-weight:600;margin-bottom:16px;animation:heroUp .7s cubic-bezier(.2,.7,.3,1) both}
.pg-video-wrap{position:relative;max-width:840px;margin:0 auto;border-radius:18px;overflow:hidden;box-shadow:0 18px 50px rgba(24,0,173,.16);aspect-ratio:16/9;background:#0c0630}
.pg-video-wrap iframe{position:absolute;inset:0;width:100%;height:100%;border:0}
.pgc-grid{display:grid;grid-template-columns:1fr 1fr;gap:24px;align-items:stretch;margin-top:26px}
.pgc-card{background:#fff;border:1px solid var(--border);border-radius:var(--r);padding:28px}
.pgc-lab{font-size:11px;font-weight:700;letter-spacing:1.6px;text-transform:uppercase;color:var(--text3);margin:18px 0 7px}
.pgc-lab:first-child{margin-top:0}
.pgc-select{width:100%;padding:12px 14px;border:1.5px solid var(--border);border-radius:11px;font-family:inherit;font-size:14.5px;font-weight:600;color:var(--text);background:#fff;cursor:pointer}
.pgc-select:focus{outline:none;border-color:var(--orange)}
.pgc-range{width:100%;accent-color:var(--orange);cursor:pointer}
.pgc-val{font-size:14px;font-weight:700;color:var(--blue)}
.pgc-out{background:linear-gradient(160deg,var(--blue),var(--blue-dk));border-radius:var(--r);padding:30px 28px;color:#fff;display:flex;flex-direction:column;justify-content:center;text-align:center}
.pgc-big{font-family:'Playfair Display',serif;font-size:46px;font-weight:700;line-height:1.05;margin:6px 0 4px}
.pgc-sub{font-size:12.5px;color:rgba(255,255,255,.75)}
.pgc-3x{margin-top:18px;padding-top:16px;border-top:1px solid rgba(255,255,255,.2);font-size:13.5px;color:rgba(255,255,255,.9)}
.pgc-note{font-size:11.5px;color:var(--text4);margin-top:14px;line-height:1.55;text-align:center}
.pg-tiers{display:grid;grid-template-columns:repeat(3,1fr);gap:20px;margin-top:26px}
.pg-tier{background:#fff;border:1.5px solid var(--border);border-radius:16px;padding:26px 24px;display:flex;flex-direction:column}
.pg-tier.gold{border-color:#d9a418;box-shadow:0 10px 34px rgba(217,164,24,.14)}
.pg-tier-medal{font-size:30px;line-height:1;margin-bottom:10px}
.pg-tier h4{font-family:'Playfair Display',serif;font-size:21px;color:var(--text);margin-bottom:2px}
.pg-tier-req{font-size:12px;font-weight:700;letter-spacing:.6px;text-transform:uppercase;color:var(--orange);margin-bottom:14px}
.pg-tier ul{list-style:none;display:flex;flex-direction:column;gap:9px;font-size:13.5px;color:var(--text2)}
.pg-tier li{display:flex;gap:9px;align-items:flex-start}
.pg-tier li::before{content:'✓';color:var(--green);font-weight:700;flex-shrink:0}
.pg-share-pre{background:var(--bg2);border:1px solid var(--border);border-radius:12px;padding:16px 18px;font-size:13.5px;line-height:1.7;color:var(--text2);white-space:pre-wrap;word-break:break-word;min-height:150px;margin-bottom:12px}
.pg-share-btns{display:flex;gap:8px;flex-wrap:wrap}
.pg-btn2{display:inline-flex;align-items:center;gap:7px;background:var(--blue);color:#fff;border:none;border-radius:10px;padding:11px 18px;font-size:13px;font-weight:700;cursor:pointer;font-family:inherit;transition:background .15s}
.pg-btn2:hover{background:var(--blue-dk)}
.pg-btn2.alt{background:var(--bg3);color:var(--text)}
.pg-btn2.alt:hover{background:var(--border)}
.pg-btn2.orange{background:var(--orange)}
.pg-btn2.orange:hover{background:var(--orange-dk)}
#pgPack{display:none}
@media(max-width:760px){.pgc-grid{grid-template-columns:1fr}.pg-tiers{grid-template-columns:1fr}.pgc-big{font-size:38px}}
@media print{
  body.pg-printing > *:not(#pgPack){display:none!important}
  body.pg-printing #pgPack{display:block!important;font-family:'Be Vietnam Pro',sans-serif;color:#1c1c1a;padding:14mm 12mm}
  .pgk-cobrand{display:flex;justify-content:space-between;align-items:baseline;border-bottom:2.5px solid #1800ad;padding-bottom:8px;margin-bottom:20px}
  .pgk-brand{font-weight:800;letter-spacing:2.4px;font-size:13px;color:#1800ad}
  .pgk-firm{font-size:11.5px;color:#6b7280;font-weight:600}
  .pgk-h1{font-family:'Playfair Display',serif;font-size:30px;margin:2px 0 16px}
  .pgk-stats{display:flex;gap:26px;margin-bottom:18px}
  .pgk-stat b{display:block;font-family:'Playfair Display',serif;font-size:23px;color:#1800ad}
  .pgk-stat span{font-size:10.5px;text-transform:uppercase;letter-spacing:1px;color:#6b7280}
  .pgk-desc{font-size:13px;line-height:1.7;margin-bottom:18px}
  .pgk-steps{margin:0 0 20px 0;padding:0;list-style:none;font-size:12.5px}
  .pgk-steps li{margin-bottom:6px}
  .pgk-steps b{color:#1800ad}
  .pgk-contact{border-top:1.5px solid #e5e7eb;padding-top:12px;font-size:12px;line-height:1.8}
  .pgk-foot{margin-top:14px;font-size:10px;color:#9ca3af;line-height:1.6}
}
"""
anchor = "@media(prefers-reduced-motion:reduce){"
assert anchor in html
html = html.replace(anchor, css + "\n" + anchor, 1)

# ---------------------------------------------------------------- 2) nav + chips
nav_anchor = '<a class="nav-link" href="#contact"'
assert nav_anchor in html
html = html.replace(nav_anchor,
  f'<a class="nav-link" href="#p5" {B("05 · Hoa Hồng","05 · Economics")}>05 · Hoa Hồng</a>\n'
  f'      <a class="nav-link" href="#p6" {B("06 · Chia Sẻ","06 · Share")}>06 · Chia Sẻ</a>\n'
  f'      {nav_anchor}', 1)
for i in range(1, 5):
    old, new = f">0{i} / 04<", f">0{i} / 06<"
    assert old in html, old
    html = html.replace(old, new, 1)

# ---------------------------------------------------------------- 3) greeting chip
greet_anchor = '<div class="hero-eyebrow"'
assert greet_anchor in html
html = html.replace(greet_anchor,
  '<div class="pg-greet" id="pgGreet" style="display:none">👋 <span id="pgGreetTxt"></span></div>\n      ' + greet_anchor, 1)

# ---------------------------------------------------------------- 4) video section (after hero)
video = f"""
  <!-- Founder video — hidden until PG_VIDEO_URL is set in the pgEnrich script below -->
  <section class="sec" id="pgVideo" style="display:none">
    <div class="wrap">
      <div class="sec-title" {B("Lời Chào Từ Nhà Sáng Lập","A Word From Our Founder")}>Lời Chào Từ Nhà Sáng Lập</div>
      <div class="sec-sub" {B("90 giây về NAC, mô hình hợp tác và cam kết với đối tác — từ Ray Vũ.","Ninety seconds on NAC, the partnership model, and our commitment to partners — from Ray Vu.")}>90 giây về NAC, mô hình hợp tác và cam kết với đối tác — từ Ray Vũ.</div>
      <div class="pg-video-wrap" id="pgVideoWrap"></div>
    </div>
  </section>
"""
hero_end = '  </section>\n\n  <!-- ═══════════ PAGE 01'
assert hero_end in html
html = html.replace(hero_end, '  </section>\n' + video + '\n  <!-- ═══════════ PAGE 01', 1)

# ---------------------------------------------------------------- 5) §05 + §06
sec5 = f"""
  <section class="sec" id="p5">
    <div class="wrap">
      <div style="text-align:center"><span class="pnum-chip">05 / 06</span></div>
      <div class="sec-title" {B("Hoa Hồng & Lộ Trình Đối Tác","Referral Economics & The Partner Track")}>Hoa Hồng & Lộ Trình Đối Tác</div>
      <div class="sec-sub" {B("Ước tính nhanh thu nhập giới thiệu theo từng chương trình — và lộ trình quyền lợi khi đồng hành dài hạn cùng NAC.","A quick estimate of referral income per program — and how benefits grow as we work together long-term.")}>Ước tính nhanh thu nhập giới thiệu theo từng chương trình — và lộ trình quyền lợi khi đồng hành dài hạn cùng NAC.</div>
      <div class="pgc-grid">
        <div class="pgc-card">
          <div class="pgc-lab" {B("Chọn chương trình","Choose a program")}>Chọn chương trình</div>
          <select class="pgc-select" id="pgcProg"></select>
          <div class="pgc-lab"><span {B("Giá trị đầu tư của khách","Client investment amount")}>Giá trị đầu tư của khách</span> · <span class="pgc-val" id="pgcTicketVal"></span></div>
          <input type="range" class="pgc-range" id="pgcTicket" min="0" max="100" value="0">
          <div class="pgc-lab"><span {B("Mức phí giới thiệu","Referral fee rate")}>Mức phí giới thiệu</span> · <span class="pgc-val" id="pgcRateVal"></span></div>
          <input type="range" class="pgc-range" id="pgcRate" min="50" max="200" step="25" value="100">
          <div class="pgc-note" {B("Con số minh họa để tham khảo — mức phí thực tế tùy chương trình và được chốt trong thỏa thuận hợp tác.","Illustrative figures — actual rates vary by program and are set in the partnership agreement.")}>Con số minh họa để tham khảo — mức phí thực tế tùy chương trình và được chốt trong thỏa thuận hợp tác.</div>
        </div>
        <div class="pgc-out">
          <div class="pgc-sub" {B("Thu nhập giới thiệu ước tính","Estimated referral income")}>Thu nhập giới thiệu ước tính</div>
          <div class="pgc-big" id="pgcOut">$0</div>
          <div class="pgc-sub" {B("cho mỗi khách hàng hoàn tất đầu tư","per client who completes an investment")}>cho mỗi khách hàng hoàn tất đầu tư</div>
          <div class="pgc-3x"><span {B("Giới thiệu 3 khách một năm","Refer 3 clients a year")}>Giới thiệu 3 khách một năm</span> ≈ <b id="pgcOut3">$0</b></div>
        </div>
      </div>
      <div class="pgc-lab" style="margin-top:34px;text-align:center" {B("Lộ trình quyền lợi","The partner track")}>Lộ trình quyền lợi</div>
      <div class="pg-tiers" id="pgTiers">
        <div class="pg-tier">
          <div class="pg-tier-medal">🥉</div>
          <h4 {B("Đối Tác Đồng","Bronze Partner")}>Đối Tác Đồng</h4>
          <div class="pg-tier-req" {B("Mọi đối tác mới","Every new partner")}>Mọi đối tác mới</div>
          <ul>
            <li><span {B("Truy cập toàn bộ cổng đối tác & bộ công cụ","Full gateway & toolkit access")}>Truy cập toàn bộ cổng đối tác & bộ công cụ</span></li>
            <li><span {B("Tài liệu song ngữ sẵn sàng gửi khách hàng","Bilingual client-ready materials")}>Tài liệu song ngữ sẵn sàng gửi khách hàng</span></li>
            <li><span {B("NAC đồng hành trực tiếp thương vụ đầu tiên","Hands-on NAC support on your first deal")}>NAC đồng hành trực tiếp thương vụ đầu tiên</span></li>
          </ul>
        </div>
        <div class="pg-tier">
          <div class="pg-tier-medal">🥈</div>
          <h4 {B("Đối Tác Bạc","Silver Partner")}>Đối Tác Bạc</h4>
          <div class="pg-tier-req" {B("Từ 3 khách giới thiệu / năm","From 3 referrals a year")}>Từ 3 khách giới thiệu / năm</div>
          <ul>
            <li><span {B("Mức phí giới thiệu ưu đãi hơn","Improved referral rate")}>Mức phí giới thiệu ưu đãi hơn</span></li>
            <li><span {B("Ưu tiên xử lý hồ sơ khách hàng","Priority client processing")}>Ưu tiên xử lý hồ sơ khách hàng</span></li>
            <li><span {B("Co-marketing: webinar & bài viết chung","Co-marketing: joint webinars & articles")}>Co-marketing: webinar & bài viết chung</span></li>
          </ul>
        </div>
        <div class="pg-tier gold">
          <div class="pg-tier-medal">🥇</div>
          <h4 {B("Đối Tác Vàng","Gold Partner")}>Đối Tác Vàng</h4>
          <div class="pg-tier-req" {B("Từ 10 khách giới thiệu / năm","From 10 referrals a year")}>Từ 10 khách giới thiệu / năm</div>
          <ul>
            <li><span {B("Mức chia sẻ cao nhất","The highest revenue share")}>Mức chia sẻ cao nhất</span></li>
            <li><span {B("Chuyên viên NAC riêng cho đối tác","A dedicated NAC specialist")}>Chuyên viên NAC riêng cho đối tác</span></li>
            <li><span {B("Sự kiện khách hàng đồng tổ chức","Co-hosted client events")}>Sự kiện khách hàng đồng tổ chức</span></li>
          </ul>
        </div>
      </div>
      <div class="pgc-note" {B("Lộ trình 2026 — quyền lợi chính thức được xác nhận trong thỏa thuận hợp tác.","The 2026 track — formal benefits are confirmed in the partnership agreement.")}>Lộ trình 2026 — quyền lợi chính thức được xác nhận trong thỏa thuận hợp tác.</div>
    </div>
  </section>

  <section class="sec" id="p6" style="background:var(--bg2)">
    <div class="wrap">
      <div style="text-align:center"><span class="pnum-chip">06 / 06</span></div>
      <div class="sec-title" {B("Gửi Cho Khách Của Bạn","Send To Your Client")}>Gửi Cho Khách Của Bạn</div>
      <div class="sec-sub" {B("Chọn chương trình — đoạn giới thiệu song ngữ sẵn sàng chuyển tiếp qua Zalo/WhatsApp, và hồ sơ in mang tên công ty của bạn.","Pick a program — a forward-ready bilingual snippet for Zalo/WhatsApp, and a printable client pack carrying your firm's name.")}>Chọn chương trình — đoạn giới thiệu song ngữ sẵn sàng chuyển tiếp qua Zalo/WhatsApp, và hồ sơ in mang tên công ty của bạn.</div>
      <div style="max-width:520px;margin:24px auto 0">
        <select class="pgc-select" id="pgsProg"></select>
      </div>
      <div class="pgc-grid">
        <div class="pgc-card">
          <div class="pgc-lab" {B("Đoạn giới thiệu chuyển tiếp","Forward-ready snippet")}>Đoạn giới thiệu chuyển tiếp</div>
          <div class="pg-share-pre" id="pgsPre"></div>
          <div class="pg-share-btns">
            <button class="pg-btn2" id="pgsCopyVi" type="button">⧉ <span {B("Sao chép bản VI","Copy VI")}>Sao chép bản VI</span></button>
            <button class="pg-btn2 alt" id="pgsCopyEn" type="button">⧉ <span {B("Sao chép bản EN","Copy EN")}>Sao chép bản EN</span></button>
          </div>
        </div>
        <div class="pgc-card">
          <div class="pgc-lab" {B("Hồ sơ khách hàng — in chung thương hiệu","Client pack — co-branded")}>Hồ sơ khách hàng — in chung thương hiệu</div>
          <p style="font-size:13.5px;color:var(--text2);line-height:1.7;margin-bottom:16px" {B("Một trang A4 gọn: chương trình, con số chính, quy trình 5 bước và liên hệ NAC — kèm dòng ghi nhận công ty của bạn. In hoặc lưu PDF ngay từ trình duyệt.","One tidy A4 page: the program, its key figures, the 5-step process and NAC contacts — carrying your firm's name. Print or save as PDF straight from the browser.")}>Một trang A4 gọn: chương trình, con số chính, quy trình 5 bước và liên hệ NAC — kèm dòng ghi nhận công ty của bạn. In hoặc lưu PDF ngay từ trình duyệt.</p>
          <button class="pg-btn2 orange" id="pgsPack" type="button">🖨 <span {B("Tạo hồ sơ khách hàng","Generate client pack")}>Tạo hồ sơ khách hàng</span></button>
          <div class="pgc-note" style="text-align:left" {B("Mẹo: trong hộp thoại in, chọn 'Save as PDF' để gửi file cho khách qua email hoặc Zalo.","Tip: in the print dialog choose 'Save as PDF' to email or Zalo the file to your client.")}>Mẹo: trong hộp thoại in, chọn 'Save as PDF' để gửi file cho khách qua email hoặc Zalo.</div>
        </div>
      </div>
    </div>
  </section>
"""
cta_anchor = '  <section class="ctaband" id="contact">'
assert cta_anchor in html
html = html.replace(cta_anchor, sec5 + "\n" + cta_anchor, 1)

# ---------------------------------------------------------------- 6) print pack skeleton (direct child of body)
pack = """
<!-- Co-branded client pack — print-only; filled by pgEnrich just before window.print() -->
<div id="pgPack">
  <div class="pgk-cobrand"><span class="pgk-brand">NOMAD ASSET COLLECTIVE</span><span class="pgk-firm" id="pgkFirm"></span></div>
  <div class="pgk-h1" id="pgkTitle"></div>
  <div class="pgk-stats" id="pgkStats"></div>
  <div class="pgk-desc" id="pgkDesc"></div>
  <ol class="pgk-steps" id="pgkSteps"></ol>
  <div class="pgk-contact" id="pgkContact"></div>
  <div class="pgk-foot" id="pgkFoot"></div>
</div>
"""
main_end = "</div><!-- /#nacMain -->"
assert main_end in html
html = html.replace(main_end, main_end + "\n" + pack, 1)

# ---------------------------------------------------------------- 7) persist partner meta inside the gate IIFE
va = "if (res.status === 200 && res.data && res.data.ok){ try{ localStorage.setItem(LS_KEY, code); }catch(e){} unlock(); return true; }"
assert va in html
html = html.replace(va, "if (res.status === 200 && res.data && res.data.ok){ try{ localStorage.setItem(LS_KEY, code); localStorage.setItem('nac-partner-meta', JSON.stringify({n: res.data.name || '', c: res.data.contact || ''})); }catch(e){} unlock(); return true; }", 1)
vb = "try{ localStorage.setItem(LS_KEY, res.data.code); }catch(e){}"
assert vb in html
html = html.replace(vb, "try{ localStorage.setItem(LS_KEY, res.data.code); localStorage.setItem('nac-partner-meta', JSON.stringify({n: res.data.name || '', c: res.data.contact || ''})); }catch(e){}", 1)

# ---------------------------------------------------------------- 8) data + behaviour script
script = """
<script type="application/json" id="pgPrograms">__PG_JSON__</script>
<script>
/* ===== Partner-capture behaviours: greeting · calculator · shareables · pack · video · telemetry ===== */
(function(){
  var PG_WORKER = 'https://nac-marketing-cc.ray-vtt.workers.dev';
  var PG_VIDEO_URL = ''; // ← paste a YouTube-embed or Cloudflare Stream iframe URL to reveal the founder-video section
  var PROGS = [];
  try { PROGS = JSON.parse(document.getElementById('pgPrograms').textContent || '[]'); } catch(e) {}
  function byKey(k){ for (var i = 0; i < PROGS.length; i++) if (PROGS[i].k === k) return PROGS[i]; return PROGS[0]; }
  function lang(){ return document.documentElement.lang === 'en' ? 'en' : 'vi'; }
  function fmt(n){ try { return '$' + new Intl.NumberFormat('en-US').format(Math.round(n)); } catch(e) { return '$' + Math.round(n); } }
  function meta(){ try { return JSON.parse(localStorage.getItem('nac-partner-meta') || 'null'); } catch(e) { return null; } }
  function code(){ try { return (localStorage.getItem('nac-partner-code') || '').toUpperCase(); } catch(e) { return ''; } }

  /* ---- telemetry: queue + batched flush, fail-silent, once per event per visit ---- */
  var sent = {}, q = [], timer = null;
  function ev(name, again){
    if (!code()) return;
    if (!again && sent[name]) return;
    sent[name] = 1;
    q.push(name);
    if (!timer) timer = setTimeout(flush, 3500);
  }
  function flush(){
    timer = null;
    if (!q.length) return;
    var body = JSON.stringify({ code: code(), evs: q.splice(0) });
    try {
      if (navigator.sendBeacon) navigator.sendBeacon(PG_WORKER + '/pg-view', new Blob([body], {type: 'text/plain'}));
      else fetch(PG_WORKER + '/pg-view', { method: 'POST', body: body, keepalive: true }).catch(function(){});
    } catch(e) {}
  }
  window.addEventListener('pagehide', flush);

  /* ---- greeting chip ---- */
  function greet(){
    var m = meta();
    if (!m || !m.n) return;
    var el = document.getElementById('pgGreet'), txt = document.getElementById('pgGreetTxt');
    if (!el || !txt) return;
    var vi, en;
    if (m.c && m.c !== m.n) {
      vi = 'Chào ' + m.c + ' — cổng này được chuẩn bị riêng cho ' + m.n + '.';
      en = 'Welcome ' + m.c + ' — this gateway is prepared for ' + m.n + '.';
    } else {
      vi = 'Chào ' + m.n + ' — cổng này được chuẩn bị riêng cho bạn.';
      en = 'Welcome ' + m.n + ' — this gateway is prepared for you.';
    }
    txt.setAttribute('data-vi', vi);
    txt.setAttribute('data-en', en);
    txt.textContent = lang() === 'en' ? en : vi;
    el.style.display = '';
  }

  /* ---- video slot ---- */
  function video(){
    if (!PG_VIDEO_URL) return;
    var sec = document.getElementById('pgVideo'), wrap = document.getElementById('pgVideoWrap');
    if (!sec || !wrap) return;
    var f = document.createElement('iframe');
    f.src = PG_VIDEO_URL;
    f.setAttribute('allow', 'accelerometer; autoplay; encrypted-media; picture-in-picture; fullscreen');
    f.setAttribute('allowfullscreen', '');
    f.setAttribute('loading', 'lazy');
    wrap.appendChild(f);
    sec.style.display = '';
  }

  /* ---- calculator ---- */
  var cProg = document.getElementById('pgcProg'), cTicket = document.getElementById('pgcTicket'), cRate = document.getElementById('pgcRate');
  function fillSelects(){
    [cProg, document.getElementById('pgsProg')].forEach(function(sel){
      if (!sel) return;
      var keep = sel.value;
      sel.innerHTML = '';
      PROGS.forEach(function(p){
        var o = document.createElement('option');
        o.value = p.k;
        o.textContent = p.f + '  ' + (lang() === 'en' ? p.ne : p.nv) + ' · ' + p.min;
        sel.appendChild(o);
      });
      if (keep) sel.value = keep;
    });
  }
  function calc(){
    if (!cProg || !cProg.value) return;
    var p = byKey(cProg.value);
    var ticket = p.usd * (1 + 5 * (Number(cTicket.value) / 100)); // min .. 6× min
    var rate = Number(cRate.value) / 10000;                        // 0.50% .. 2.00%
    document.getElementById('pgcTicketVal').textContent = '≈ ' + fmt(ticket);
    document.getElementById('pgcRateVal').textContent = (Number(cRate.value) / 100).toFixed(2) + '%';
    document.getElementById('pgcOut').textContent = fmt(ticket * rate);
    document.getElementById('pgcOut3').textContent = fmt(ticket * rate * 3);
  }
  if (cProg) {
    [cProg, cTicket, cRate].forEach(function(el){
      el.addEventListener('input', function(){ calc(); ev('calc'); });
    });
  }

  /* ---- shareables ---- */
  var sProg = document.getElementById('pgsProg'), sPre = document.getElementById('pgsPre');
  function snippet(p, l){
    var m = meta();
    var lines = l === 'en'
      ? [p.f + ' ' + p.ne + ' — ' + p.de, '', '• Investment from ' + p.min + (p.te ? ' · ' + p.te : ''), '• Details: ' + p.u]
      : [p.f + ' ' + p.nv + ' — ' + p.dv, '', '• Đầu tư từ ' + p.min + (p.tv ? ' · ' + p.tv : ''), '• Chi tiết: ' + p.u];
    if (m && m.n) lines.push(l === 'en' ? '— shared by ' + m.n + ' × NAC' : '— chia sẻ bởi ' + m.n + ' × NAC');
    return lines.join('\\n');
  }
  function renderShare(){
    if (!sProg || !sProg.value) return;
    sPre.textContent = snippet(byKey(sProg.value), lang());
  }
  function copyText(t, btn){
    function done(){
      var old = btn.innerHTML;
      btn.innerHTML = '✓ <span>' + (lang() === 'en' ? 'Copied' : 'Đã sao chép') + '</span>';
      setTimeout(function(){ btn.innerHTML = old; }, 1600);
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(t).then(done, function(){ fallback(); });
    } else fallback();
    function fallback(){
      var ta = document.createElement('textarea');
      ta.value = t; ta.style.position = 'fixed'; ta.style.opacity = '0';
      document.body.appendChild(ta); ta.select();
      try { document.execCommand('copy'); done(); } catch(e) {}
      document.body.removeChild(ta);
    }
  }
  if (sProg) {
    sProg.addEventListener('input', renderShare);
    document.getElementById('pgsCopyVi').addEventListener('click', function(){ copyText(snippet(byKey(sProg.value), 'vi'), this); ev('share-copy'); });
    document.getElementById('pgsCopyEn').addEventListener('click', function(){ copyText(snippet(byKey(sProg.value), 'en'), this); ev('share-copy'); });
  }

  /* ---- co-branded client pack ---- */
  var STEPS = {
    vi: ['<b>Tư vấn định hướng</b> — xác định mục tiêu cư trú, thuế và gia đình', '<b>Chọn chương trình & tài sản</b> — đối chiếu NAC Index và danh mục BĐS tuyển chọn', '<b>Chuẩn bị hồ sơ</b> — cùng luật sư di trú được NAC thẩm định', '<b>Nộp & theo dõi</b> — NAC cập nhật tiến độ từng bước cho bạn và khách hàng', '<b>Nhận kết quả & đồng hành</b> — hỗ trợ sau khi có thẻ cư trú / quốc tịch'],
    en: ['<b>Orientation consult</b> — clarify residency, tax and family goals', '<b>Program & asset selection</b> — matched against the NAC Index and curated listings', '<b>File preparation</b> — with NAC-vetted immigration counsel', '<b>Submission & tracking</b> — NAC reports progress to you and your client at every step', '<b>Approval & beyond</b> — support continues after the card or passport arrives']
  };
  function pack(){
    if (!sProg || !sProg.value) return;
    var p = byKey(sProg.value), l = lang(), m = meta();
    document.getElementById('pgkFirm').textContent = (m && m.n) ? ((l === 'en' ? 'in partnership with ' : 'phối hợp cùng ') + m.n) : '';
    document.getElementById('pgkTitle').textContent = p.f + ' ' + (l === 'en' ? p.ne : p.nv);
    document.getElementById('pgkStats').innerHTML = (p.st || []).map(function(s){
      return '<div class=pgk-stat><b>' + s.n + '</b><span>' + (l === 'en' ? s.le : s.lv) + '</span></div>';
    }).join('');
    document.getElementById('pgkDesc').textContent = l === 'en' ? p.de : p.dv;
    document.getElementById('pgkSteps').innerHTML = STEPS[l].map(function(s, i){ return '<li>' + (i + 1) + '. ' + s + '</li>'; }).join('');
    document.getElementById('pgkContact').innerHTML = (l === 'en' ? '<b>Talk to NAC</b>' : '<b>Liên hệ NAC</b>') + '<br>nomadassetcollective.com · hello@nomadassetcollective.com<br>WhatsApp +44 7388 646000 · ' + (l === 'en' ? 'Book a consult: ' : 'Đặt lịch tư vấn: ') + 'calendar.app.google/gnbtNBTBDKuHUasw7';
    var today = new Date().toLocaleDateString(l === 'en' ? 'en-GB' : 'vi-VN');
    document.getElementById('pgkFoot').textContent = (l === 'en'
      ? 'Prepared ' + today + (m && m.n ? ' by ' + m.n + ' with Nomad Asset Collective. ' : ' by Nomad Asset Collective. ') + 'For reference only — not legal or tax advice. Figures follow official program sources and may change.'
      : 'Chuẩn bị ngày ' + today + (m && m.n ? ' bởi ' + m.n + ' phối hợp cùng Nomad Asset Collective. ' : ' bởi Nomad Asset Collective. ') + 'Thông tin tham khảo — không phải tư vấn pháp lý hay thuế. Số liệu theo nguồn chính thức của chương trình và có thể thay đổi.');
    document.body.classList.add('pg-printing');
    ev('pack-print');
    flush();
    window.print();
  }
  window.addEventListener('afterprint', function(){ document.body.classList.remove('pg-printing'); });
  var packBtn = document.getElementById('pgsPack');
  if (packBtn) packBtn.addEventListener('click', pack);

  /* ---- section + CTA + tool telemetry ---- */
  function observe(){
    if (!('IntersectionObserver' in window)) return;
    var map = { p1: 'p1', p2: 'p2', p3: 'p3', p4: 'p4', p5: 'p5', p6: 'p6', pgVideo: 'video' };
    var io = new IntersectionObserver(function(es){
      es.forEach(function(e){
        if (!e.isIntersecting) return;
        ev(map[e.target.id]);
        io.unobserve(e.target);
      });
    }, { threshold: 0.25 });
    Object.keys(map).forEach(function(id){
      var el = document.getElementById(id);
      if (el && el.style.display !== 'none') io.observe(el);
    });
    var tiers = document.getElementById('pgTiers');
    if (tiers) {
      var io2 = new IntersectionObserver(function(es){
        es.forEach(function(e){ if (e.isIntersecting) { ev('tiers'); io2.unobserve(e.target); } });
      }, { threshold: 0.35 });
      io2.observe(tiers);
    }
  }
  document.addEventListener('click', function(e){
    var a = e.target && e.target.closest ? e.target.closest('a[href]') : null;
    if (!a) return;
    var h = a.getAttribute('href') || '';
    if (h.indexOf('calendar.app.google') >= 0) ev('cta-call', true);
    else if (h.indexOf('wa.me') >= 0) ev('cta-wa', true);
    else if (h.indexOf('property-hub') >= 0) ev('tool:hub');
    else if (h.indexOf('tu-van-nhanh') >= 0) ev('tool:quiz');
    else if (h.indexOf('nac-residence-index') >= 0) ev('tool:index');
    else if (h.indexOf('/so-sanh') >= 0) ev('tool:compare');
    else if (h.indexOf('/brochures/') >= 0 && h.indexOf('doi-tac') < 0) ev('tool:brochure');
  });

  /* ---- language re-render (selects + snippet are built in JS, outside the data-attr walker) ---- */
  new MutationObserver(function(){ fillSelects(); renderShare(); calc(); }).observe(document.documentElement, { attributes: true, attributeFilter: ['lang'] });

  /* ---- boot: everything meaningful starts when the gate opens #nacMain ---- */
  var booted = false;
  function boot(){
    if (booted) return;
    booted = true;
    ev('unlock', true);
    greet();
    video();
    fillSelects();
    calc();
    renderShare();
    observe();
  }
  var main = document.getElementById('nacMain');
  if (main) {
    if (main.style.display === 'block') boot();
    new MutationObserver(function(){ if (main.style.display === 'block') boot(); })
      .observe(main, { attributes: true, attributeFilter: ['style'] });
  }
})();
</script>
"""
script = script.replace("__PG_JSON__", pg_json)
gate_end = "})();\n</script>\n\n<!-- Twemoji:"
assert gate_end in html
html = html.replace(gate_end, "})();\n</script>\n" + script + "\n<!-- Twemoji:", 1)

HTML.write_text(html, encoding="utf-8")
print("written:", HTML)
print("new data-copy keys:", len(existing_keys) - len(set(re.findall(r'data-copy=\"([^\"]+)\"', HTML.read_text(encoding='utf-8')))) if False else "ok")
