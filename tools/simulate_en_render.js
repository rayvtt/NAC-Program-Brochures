#!/usr/bin/env node
/**
 * Browser-faithful EN-render simulator using jsdom.
 *
 * Loads a brochure HTML in jsdom (a real DOM), eval's the page's
 * VI_STRINGS / EN_STRINGS / setLang verbatim, calls setLang('en'),
 * then scans the rendered body for any remaining Vietnamese-unique
 * diacritic — those are the "patchy English" strings the user sees.
 *
 * This is what the audit should have been all along: my Python /
 * BeautifulSoup version normalized whitespace differently from the
 * browser and silently said 0 remnants while the real browser left
 * 40+. Use this one as truth.
 *
 * Usage:
 *   node tools/simulate_en_render.js <html-file> [--json]
 *   echo "<url>" | node tools/simulate_en_render.js -    # read from stdin
 */
'use strict';

// jsdom is loaded from the user's global install or via npm. The
// daily workflow `npm install jsdom` first; locally users can
// `npm install jsdom` once and the require path resolves either to
// node_modules in tools/ or in repo root.
let JSDOM;
try { JSDOM = require('jsdom').JSDOM; }
catch (_) {
  try { JSDOM = require('/tmp/node_modules/jsdom').JSDOM; }
  catch (_) {
    console.error('jsdom not installed. Run: npm install jsdom');
    process.exit(2);
  }
}

const fs = require('fs');
const path = require('path');

// Vietnamese-only diacritics. Same set as the Python tool.
const VN_UNIQUE = /[ăĂưƯơƠđĐảấầẩẫậắằẳẵặẹếềểễệỉịỏốồổỗộớờởỡợủụứừửữựỳỷỹỵẠ]/;

// Phrases that legitimately stay in original form (brand / place names).
const ALLOWED = new Set([
  'NAC – Nomad Asset Collective',
  'Nomad Asset Collective',
  'Việt Nam', 'Hồ Chí Minh', 'Hà Nội', 'Đà Nẵng',
]);

function extractScript(html, predicate) {
  const re = /<script[^>]*>([\s\S]*?)<\/script>/g;
  let m;
  while ((m = re.exec(html)) !== null) {
    if (predicate(m[1])) return m[1];
  }
  return '';
}

function buildSetlangBundle(html) {
  // Just pull out the bilingual engine. setLang is defined in one
  // <script>; we want VI_STRINGS, EN_STRINGS, heroText, heroStats,
  // and the setLang function itself.
  const engineScript = extractScript(html, s => s.includes('setLang') && s.includes('VI_STRINGS'));
  if (!engineScript) throw new Error('bilingual engine <script> not found');

  const grabs = [
    /(const\s+VI_STRINGS\s*=\s*\[[\s\S]+?\]\s*;)/,
    /(const\s+EN_STRINGS\s*=\s*\[[\s\S]+?\]\s*;)/,
    /(const\s+heroText\s*=\s*\{[\s\S]+?\}\s*;)/,
    /(const\s+heroStats\s*=\s*\{[\s\S]+?\}\s*;)/,
    // Optional module-level score-bar label arrays (some brochures
    // declare these once outside setLang and reference them inside)
    /(const\s+sbarVi\s*=\s*\[[\s\S]+?\]\s*;)/,
    /(const\s+sbarEn\s*=\s*\[[\s\S]+?\]\s*;)/,
    /(function\s+setLang[\s\S]+?\n\}\s*\n)/,
  ];
  const parts = ['var currentLang = "vi";'];
  for (const re of grabs) {
    const m = engineScript.match(re);
    if (m) parts.push(m[1]);
  }
  // Expose to window so we can call from outside the eval.
  parts.push('window.VI_STRINGS = VI_STRINGS; window.EN_STRINGS = EN_STRINGS; window.setLang = setLang;');
  return parts.join('\n');
}

function findVnRemnants(rootNode) {
  const out = [];
  const seen = new Set();
  function walk(node) {
    if (node.nodeType === 3) {
      const t = node.nodeValue.trim();
      if (!t || !VN_UNIQUE.test(t)) return;
      if (t.length < 6 || t.split(/\s+/).length < 2) return;
      if (ALLOWED.has(t)) return;
      if (seen.has(t)) return;
      seen.add(t);
      // Build short selector trail
      let p = node.parentNode;
      const trail = [];
      while (p && p.tagName && trail.length < 3) {
        let s = p.tagName.toLowerCase();
        if (typeof p.className === 'string' && p.className) s += '.' + p.className.split(' ')[0];
        trail.unshift(s);
        p = p.parentNode;
      }
      out.push({ text: t, parent: trail.join(' > ') });
      return;
    }
    if (node.nodeType === 1) {
      const tag = node.tagName;
      if (tag === 'SCRIPT' || tag === 'STYLE' || tag === 'TEMPLATE') return;
      if (tag === 'HEAD' || tag === 'TITLE' || tag === 'META' || tag === 'LINK') return;
      for (const c of node.childNodes) walk(c);
    }
  }
  walk(rootNode);
  return out;
}

function auditHtml(html) {
  const dom = new JSDOM(html, { runScripts: 'outside-only', pretendToBeVisual: true });
  // Common globals the brochure expects
  dom.window.IntersectionObserver = class { observe(){} unobserve(){} disconnect(){} };
  dom.window.MutationObserver = class { observe(){} disconnect(){} };
  dom.window.ResizeObserver = class { observe(){} disconnect(){} };
  dom.window.matchMedia = () => ({ matches: false, addEventListener: () => {} });

  const bundle = buildSetlangBundle(html);
  try {
    dom.window.eval(bundle);
  } catch (e) {
    return { error: 'eval failed: ' + e.message };
  }
  if (typeof dom.window.setLang !== 'function') return { error: 'setLang not defined after eval' };

  try { dom.window.setLang('en'); }
  catch (e) { return { error: 'setLang(en) threw: ' + e.message }; }

  const remnants = findVnRemnants(dom.window.document.body);
  return {
    pass: remnants.length === 0,
    remnant_count: remnants.length,
    vi_array_size: dom.window.VI_STRINGS.length,
    en_array_size: dom.window.EN_STRINGS.length,
    remnants: remnants.slice(0, 50),
  };
}

function loadHtmlFromArg(arg) {
  if (arg.startsWith('http://') || arg.startsWith('https://')) {
    const url = arg;
    // Sync fetch via shelling out — keeps this script dep-light.
    const { execSync } = require('child_process');
    return execSync(`curl -sL -A "NAC-Audit/1.0" "${url}"`, { encoding: 'utf8', maxBuffer: 50 * 1024 * 1024 });
  }
  return fs.readFileSync(arg, 'utf8');
}

function main() {
  const args = process.argv.slice(2);
  const jsonOut = args.includes('--json');
  const verbose = args.includes('-v') || args.includes('--verbose');
  const positional = args.filter(a => !a.startsWith('--') && a !== '-v');

  if (positional.length === 0) {
    console.error('Usage: simulate_en_render.js <file-or-url> [--json] [-v]');
    process.exit(2);
  }
  const source = positional[0];
  const html = loadHtmlFromArg(source);
  const result = auditHtml(html);
  result.source = source;

  if (jsonOut) {
    console.log(JSON.stringify(result, null, 2));
    process.exit(result.pass ? 0 : 1);
  }

  if (result.error) {
    console.error('ERROR:', result.error);
    process.exit(2);
  }
  const badge = result.pass ? '\x1b[32m✓\x1b[0m' : '\x1b[31m✗\x1b[0m';
  console.log(`${badge} ${source}: ${result.remnant_count} VN remnants `
    + `[VI=${result.vi_array_size} EN=${result.en_array_size}]`);
  if (!result.pass) {
    const byParent = new Map();
    for (const r of result.remnants) {
      const k = r.parent.split('>').pop().trim();
      if (!byParent.has(k)) byParent.set(k, []);
      byParent.get(k).push(r);
    }
    for (const [k, items] of byParent) {
      console.log(`  ── ${k}: ${items.length}`);
      const sample = verbose ? items : items.slice(0, 5);
      for (const r of sample) {
        const t = r.text.length > 100 ? r.text.slice(0, 97) + '…' : r.text;
        console.log(`     · ${t}`);
      }
      if (!verbose && items.length > 5) console.log(`     · …and ${items.length - 5} more`);
    }
  }
  process.exit(result.pass ? 0 : 1);
}

main();
