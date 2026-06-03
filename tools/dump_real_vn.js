// Hunt for VN-only diacritics in EN render (filters out Spanish loanwords).
const { JSDOM } = require('jsdom');
const fs = require('fs');

const src = process.argv[2] || 'Brochures html/panama-rbi_.html';
let html;
if (src.startsWith('http')) {
  const { execSync } = require('child_process');
  html = execSync(`curl -sL "${src}"`, { encoding: 'utf8' });
} else {
  html = fs.readFileSync(src, 'utf8');
}

function ext(html, pred) {
  const re = /<script[^>]*>([\s\S]*?)<\/script>/g; let m;
  while ((m = re.exec(html)) !== null) if (pred(m[1])) return m[1];
  return '';
}
const eng = ext(html, s => s.includes('setLang') && s.includes('VI_STRINGS'));
const grabs = [
  /(const\s+VI_STRINGS\s*=\s*\[[\s\S]+?\]\s*;)/,
  /(const\s+EN_STRINGS\s*=\s*\[[\s\S]+?\]\s*;)/,
  /(const\s+heroText\s*=\s*\{[\s\S]+?\}\s*;)/,
  /(const\s+heroStats\s*=\s*\{[\s\S]+?\}\s*;)/,
  /(const\s+sbarVi\s*=\s*\[[\s\S]+?\]\s*;)/,
  /(const\s+sbarEn\s*=\s*\[[\s\S]+?\]\s*;)/,
  /(function\s+setLang[\s\S]+?\n\}\s*\n)/,
];
const parts = ['var currentLang = "vi";'];
for (const re of grabs) { const m = eng.match(re); if (m) parts.push(m[1]); }
parts.push('window.VI_STRINGS=VI_STRINGS;window.EN_STRINGS=EN_STRINGS;window.setLang=setLang;');

const dom = new JSDOM(html, { runScripts: 'outside-only', pretendToBeVisual: true });
dom.window.IntersectionObserver = class { observe(){} unobserve(){} disconnect(){} };
dom.window.MutationObserver = class { observe(){} disconnect(){} };
dom.window.ResizeObserver = class { observe(){} disconnect(){} };
dom.window.matchMedia = () => ({ matches: false, addEventListener: () => {} });

try { dom.window.eval(parts.join('\n')); }
catch (e) { console.log('eval err:', e.message); process.exit(1); }
dom.window.setLang('en');

// VN-ONLY chars (not in Spanish/Portuguese/Italian)
const VN_ONLY = /[ăâđêôơưĂÂĐÊÔƠƯảạắằẳẵặấầẩẫậẻẽẹếềểễệỉĩịỏõọốồổỗộớờởỡợủũụứừửữựỳỷỹỵẢÃẠẮẰẲẴẶẤẦẨẪẬẺẼẸẾỀỂỄỆỈĨỊỎÕỌỐỒỔỖỘỚỜỞỠỢỦŨỤỨỪỬỮỰỲỶỸỴ]/;
const seen = new Set();

function walk(n) {
  if (n.nodeType === 3) {
    const t = n.nodeValue.trim();
    if (t && VN_ONLY.test(t) && t.length > 4 && !seen.has(t)) {
      seen.add(t);
      // Get path
      let p = n.parentNode, path = [];
      while (p && path.length < 3) { path.push(p.tagName + (p.className ? '.' + p.className.split(' ')[0] : '')); p = p.parentNode; }
      console.log('---');
      console.log(path.reverse().join(' > '));
      console.log(t.substring(0, 300));
    }
    return;
  }
  if (n.nodeType === 1) {
    const tag = n.tagName;
    if (tag === 'SCRIPT' || tag === 'STYLE' || tag === 'HEAD') return;
    for (let c = n.firstChild; c; c = c.nextSibling) walk(c);
  }
}
walk(dom.window.document.body);
