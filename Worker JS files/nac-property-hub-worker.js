/**
 * ─────────────────────────────────────────────────────────────────────────
 *  NAC Property Hub API — Cloudflare Worker
 *  https://nac-property-hub.ray-vtt.workers.dev/
 * ─────────────────────────────────────────────────────────────────────────
 *
 *  Serves the NAC Property Hub with live data from Notion.
 *  Separate from the CRM worker (nac-notion-proxy) to keep lead-capture
 *  isolated from property-feed concerns.
 *
 *  ── Cloudflare setup ─────────────────────────────────────────────
 *    Workers → Create Worker → name: nac-property-hub
 *    Settings → Variables → add:
 *        NOTION_KEY          = secret_xxxxxxxxxxxxxxxx   (encrypt = ON)
 *        ANTHROPIC_API_KEY   = sk-ant-xxxxxxxxxxxxxxxx   (encrypt = ON)
 *    Paste this script → Save and Deploy.
 *
 *  ── Routes ──────────────────────────────────────────────────────
 *
 *  GET /properties
 *     Returns all Hub Status="Live" properties from the NAC Properties
 *     Notion DB as a JSON array in the PROPS format the Property Hub
 *     HTML expects. Cached: 2 min browser, 5 min Cloudflare edge.
 *
 *  GET /properties/:id
 *     Returns a single property by its NAC-xx Property ID number.
 *
 *  GET /scrape?url=...
 *     Server-side fetch + clean HTML → text. Used by NAC Lister regex
 *     fallback path.
 *
 *  POST /ai-extract                                       (added 2026-05-07)
 *     AI-powered structured extraction for NAC Lister.
 *     Body: { source:'url'|'paste'|'upload', url?, text?, files?, hint? }
 *     Returns the same shape as the legacy plParsePasteText() so the
 *     Lister's plRenderFields()/plMergeIntoHub() work unchanged.
 *
 *  POST /properties
 *     Create a new property in Notion (from Lister's Save flow).
 *
 *  GET /health
 *     Quick liveness check.
 *
 * ─────────────────────────────────────────────────────────────────────────
 */

const NOTION_VERSION = '2022-06-28';
const PROPERTY_DB_ID = '35848ec25e86803283acc7ad989649c9';

// Country → emoji flag + localized name
const COUNTRY_MAP = {
  'Vietnam':        { flag:'🇻🇳', vi:'Việt Nam' },
  'Thailand':       { flag:'🇹🇭', vi:'Thái Lan' },
  'Indonesia':      { flag:'🇮🇩', vi:'Indonesia' },
  'Malaysia':       { flag:'🇲🇾', vi:'Malaysia' },
  'Japan':          { flag:'🇯🇵', vi:'Nhật Bản' },
  'Singapore':      { flag:'🇸🇬', vi:'Singapore' },
  'Philippines':    { flag:'🇵🇭', vi:'Philippines' },
  'UAE':            { flag:'🇦🇪', vi:'UAE' },
  'Dubai':          { flag:'🇦🇪', vi:'Dubai' },
  'Abu Dhabi':      { flag:'🇦🇪', vi:'Abu Dhabi' },
  'Qatar':          { flag:'🇶🇦', vi:'Qatar' },
  'Saudi Arabia':   { flag:'🇸🇦', vi:'Ả Rập Xê Út' },
  'Oman':           { flag:'🇴🇲', vi:'Oman' },
  'Bahrain':        { flag:'🇧🇭', vi:'Bahrain' },
  'Turkey':         { flag:'🇹🇷', vi:'Thổ Nhĩ Kỳ' },
  'Panama':         { flag:'🇵🇦', vi:'Panama' },
  'St Kitts':       { flag:'🇰🇳', vi:'St Kitts' },
  'Antigua':        { flag:'🇦🇬', vi:'Antigua' },
  'Grenada':        { flag:'🇬🇩', vi:'Grenada' },
  'Dominica':       { flag:'🇩🇲', vi:'Dominica' },
  'St Vincent':     { flag:'🇻🇨', vi:'St Vincent' },
  'Bahamas':        { flag:'🇧🇸', vi:'Bahamas' },
  'Jamaica':        { flag:'🇯🇲', vi:'Jamaica' },
  'Trinidad':       { flag:'🇹🇹', vi:'Trinidad' },
  'Barbados':       { flag:'🇧🇧', vi:'Barbados' },
  'Portugal':       { flag:'🇵🇹', vi:'Bồ Đào Nha' },
  'Greece':         { flag:'🇬🇷', vi:'Hy Lạp' },
  'Italy':          { flag:'🇮🇹', vi:'Ý' },
  'Spain':          { flag:'🇪🇸', vi:'Tây Ban Nha' },
  'Hungary':        { flag:'🇭🇺', vi:'Hungary' },
  'Cyprus':         { flag:'🇨🇾', vi:'Đảo Síp' },
  'Malta':          { flag:'🇲🇹', vi:'Malta' },
  'Albania':        { flag:'🇦🇱', vi:'Albania' },
  'Montenegro':     { flag:'🇲🇪', vi:'Montenegro' },
  'Florida':        { flag:'🇺🇸', vi:'Florida' },
  'Texas':          { flag:'🇺🇸', vi:'Texas' },
  'Hawaii':         { flag:'🇺🇸', vi:'Hawaii' },
  'New York':       { flag:'🇺🇸', vi:'New York' },
  'Colorado':       { flag:'🇺🇸', vi:'Colorado' },
  'Vanuatu':        { flag:'🇻🇺', vi:'Vanuatu' },
  'Australia':      { flag:'🇦🇺', vi:'Úc' },
  'New Zealand':    { flag:'🇳🇿', vi:'New Zealand' },
  'Fiji':           { flag:'🇫🇯', vi:'Fiji' },
  'Samoa':          { flag:'🇼🇸', vi:'Samoa' },
  'Papua New Guinea':{ flag:'🇵🇬', vi:'Papua New Guinea' },
  'Nauru':          { flag:'🇳🇷', vi:'Nauru' },
};

// Tag display-name → short code used by Property Hub HTML
const TAG_MAP = {
  'Hot':        'hot',
  'Must Know':  'need',
  'Freehold':   'free',
  'Residency':  'res',
  'Citizenship':'pr',
};

const corsHeaders = {
  'Access-Control-Allow-Origin':  '*',
  'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
  'Access-Control-Max-Age':       '86400',
};

function jsonResponse(data, status = 200, extraHeaders = {}) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json', ...corsHeaders, ...extraHeaders },
  });
}

function notionFetch(env, path, init = {}) {
  return fetch('https://api.notion.com/v1' + path, {
    ...init,
    headers: {
      'Authorization':  'Bearer ' + env.NOTION_KEY,
      'Notion-Version': NOTION_VERSION,
      'Content-Type':   'application/json',
      ...(init.headers || {}),
    },
  });
}

// ─────────────────────────────────────────────────────────────────────
// PROPERTY TRANSFORM — Notion row → PROPS-format object
// ─────────────────────────────────────────────────────────────────────
function notionRowToProps(page) {
  const p = page.properties || {};

  const txt = (prop) => {
    if (!prop) return '';
    if (prop.type === 'title')     return (prop.title || []).map(t => t.plain_text).join('');
    if (prop.type === 'rich_text') return (prop.rich_text || []).map(t => t.plain_text).join('');
    if (prop.type === 'url')       return prop.url || '';
    return '';
  };
  const num  = (prop) => (prop && prop.type === 'number' && prop.number != null) ? prop.number : 0;
  const sel  = (prop) => (prop && prop.type === 'select' && prop.select)  ? prop.select.name : '';
  const chk  = (prop) => (prop && prop.type === 'checkbox') ? !!prop.checkbox : false;
  const ms   = (prop) => (prop && prop.type === 'multi_select') ? (prop.multi_select || []).map(o => o.name) : [];
  const uid  = (prop) => {
    if (!prop || prop.type !== 'unique_id' || !prop.unique_id) return 0;
    return prop.unique_id.number || 0;
  };

  const rawTags = ms(p['Tags']);
  const tags = rawTags.map(t => TAG_MAP[t] || t.toLowerCase()).filter(Boolean);

  // Enrich country with flag + Vietnamese name
  const rawCountry = sel(p['Country']) || '';
  const cm = COUNTRY_MAP[rawCountry] || {};
  const countryDisplay = cm.flag ? `${cm.flag} ${cm.vi || rawCountry}` : rawCountry;

  return {
    id:         uid(p['Property ID']),
    region:     sel(p['Region']) || '',
    country:    countryDisplay,
    name_vi:    txt(p['Name VI']) || txt(p['Property Name']),
    name_en:    txt(p['Property Name']),
    excerpt_vi: txt(p['Excerpt VI']),
    excerpt_en: txt(p['Excerpt EN']),
    entry:      Math.round(num(p['Purchase Price']) / 1000),   // $340000 → 340
    netYield:   +(num(p['Yield %']) * 100).toFixed(1),         // 0.052 → 5.2
    irr:        +(num(p['IRR %']) * 100).toFixed(1),           // 0.115 → 11.5
    coc:        +(num(p['Cash-on-Cash %']) * 100).toFixed(1),  // 0.068 → 6.8
    payback:    num(p['Payback Years']),
    freehold:   chk(p['Freehold']),
    tags,
    priceM2:    num(p['Price Per M2']),
    img:        txt(p['Image URL']),
    program:    sel(p['Investment Program']),
    // ── Authoritative fields (added 2026-05-07; replace client-side derivation) ──
    hubType:        sel(p['🏨 Hub Type']) || '',                  // Branded Residences/Villa/Condo/...
    immigration:    (sel(p['🛂 Immigration Type']) || 'None').toLowerCase(), // rbi / cbi / none
    branded:        chk(p['🌟 Hotel-Branded']),
    taxFriendly:    chk(p['💸 Tax-Friendly']),
  };
}

// ─────────────────────────────────────────────────────────────────────
// FETCH ALL PROPERTIES — paginated Notion query, Hub Status = Live
// ─────────────────────────────────────────────────────────────────────
async function fetchAllProperties(env) {
  const allRows = [];
  let hasMore = true;
  let startCursor = undefined;

  while (hasMore) {
    const queryBody = {
      filter: {
        property: 'Hub Status',
        select:   { equals: 'Live' },
      },
      page_size: 100,
    };
    if (startCursor) queryBody.start_cursor = startCursor;

    const res = await notionFetch(env, '/databases/' + PROPERTY_DB_ID + '/query', {
      method: 'POST',
      body:   JSON.stringify(queryBody),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.message || 'Notion query failed: ' + res.status);
    }

    const data = await res.json();
    allRows.push(...(data.results || []));
    hasMore     = !!data.has_more;
    startCursor = data.next_cursor;
  }

  return allRows.map(notionRowToProps);
}

// ─────────────────────────────────────────────────────────────────────
// CREATE — POST /properties → new Notion page from Lister manual form
// ─────────────────────────────────────────────────────────────────────
const TAG_REVERSE = { Hot:'Hot', 'Must Know':'Must Know', Freehold:'Freehold', Residency:'Residency', Citizenship:'Citizenship' };

async function createPropertyInNotion(env, body) {
  // Body shape comes from plReadForm() in the Lister
  // Minimal validation
  if (!body.name_en || !body.region || !body.country || !body.hub_type) {
    throw new Error('Missing required fields: name_en, region, country, hub_type');
  }

  // Map to Notion property payload
  const props = {
    'Property Name':       { title: [{ text: { content: body.name_en } }] },
    'Name VI':             body.name_vi      ? { rich_text: [{ text: { content: body.name_vi } }] }       : undefined,
    'Excerpt EN':          body.excerpt_en   ? { rich_text: [{ text: { content: body.excerpt_en } }] }    : undefined,
    'Excerpt VI':          body.excerpt_vi   ? { rich_text: [{ text: { content: body.excerpt_vi } }] }    : undefined,
    'Region':              body.region       ? { select: { name: body.region } }                          : undefined,
    'Country':             body.country      ? { select: { name: body.country } }                         : undefined,
    'Region/City':         body.city         ? { rich_text: [{ text: { content: body.city } }] }          : undefined,
    'Image URL':           body.img          ? { url: body.img }                                          : undefined,
    'Listing URL':         body.source_url   ? { url: body.source_url }                                   : undefined,
    'Hub Status':          { select: { name: body.hub_status || 'Draft' } },
    '🏨 Hub Type':         body.hub_type     ? { select: { name: body.hub_type } }                        : undefined,
    '🛂 Immigration Type': { select: { name: body.immigration || 'None' } },
    'Investment Program':  body.program      ? { select: { name: body.program } }                         : undefined,
    'Currency':            body.currency     ? { select: { name: body.currency } }                        : undefined,
    'Freehold':            { checkbox: !!body.freehold },
    '🌟 Hotel-Branded':    { checkbox: !!body.branded },
    '💸 Tax-Friendly':     { checkbox: !!body.tax_friendly },
    'Purchase Price':      typeof body.price    === 'number' ? { number: body.price }                  : undefined,
    'Price Per M2':        typeof body.price_m2 === 'number' ? { number: body.price_m2 }               : undefined,
    'Yield %':             typeof body.yield    === 'number' ? { number: body.yield / 100 }             : undefined,
    'IRR %':               typeof body.irr      === 'number' ? { number: body.irr / 100 }               : undefined,
    'Cash-on-Cash %':      typeof body.coc      === 'number' ? { number: body.coc / 100 }               : undefined,
    'Payback Years':       typeof body.payback  === 'number' ? { number: body.payback }                : undefined,
    'Tags':                Array.isArray(body.tags) && body.tags.length
                            ? { multi_select: body.tags.filter(t => TAG_REVERSE[t]).map(t => ({ name: t })) }
                            : undefined,
  };
  // Strip undefined
  Object.keys(props).forEach(k => props[k] === undefined && delete props[k]);

  const res = await notionFetch(env, '/pages', {
    method: 'POST',
    body:   JSON.stringify({
      parent: { database_id: PROPERTY_DB_ID },
      properties: props,
    }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.message || 'Notion create failed: ' + res.status);
  }
  const page = await res.json();

  // Read back the auto-incremented Property ID for the response
  const pid = page.properties && page.properties['Property ID'] && page.properties['Property ID'].unique_id
    ? page.properties['Property ID'].unique_id.number
    : null;

  return {
    success: true,
    page_id: page.id,
    notion_url: page.url,
    property_id: pid,
    hub_status: body.hub_status || 'Draft',
  };
}

// ─────────────────────────────────────────────────────────────────────
// SCRAPE HELPER — fetch a URL, strip scripts/styles/tags, return clean text.
// Shared by /scrape (regex path) and /ai-extract (AI path).
// ─────────────────────────────────────────────────────────────────────
async function fetchAndClean(target) {
  const r = await fetch(target, {
    headers: {
      'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36',
      'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
      'Accept-Language': 'en-US,en;q=0.9,vi;q=0.8',
    },
    cf: { cacheTtl: 600 },
  });
  if (!r.ok) {
    const e = new Error('Source returned ' + r.status);
    e.upstreamStatus = r.status;
    throw e;
  }
  let html = await r.text();
  html = html.replace(/<script[\s\S]*?<\/script>/gi, ' ')
             .replace(/<style[\s\S]*?<\/style>/gi, ' ')
             .replace(/<noscript[\s\S]*?<\/noscript>/gi, ' ')
             .replace(/<!--[\s\S]*?-->/g, ' ')
             .replace(/<\/(p|div|li|h[1-6]|tr|br|section|article)>/gi, '\n');
  let text = html.replace(/<[^>]+>/g, ' ')
                 .replace(/&nbsp;/g, ' ').replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&#39;/g, "'")
                 .replace(/[ \t]+/g, ' ').replace(/\n[ \t]+/g, '\n').replace(/\n{3,}/g, '\n\n').trim();
  if (text.length > 60000) text = text.slice(0, 60000) + '\n…[truncated]';
  return text;
}

// ─────────────────────────────────────────────────────────────────────
// AI EXTRACTION — Claude tool-use, returns Lister data-shape directly.
// Refactor of plParsePasteText() onto Sonnet 4.6, with multimodal
// support for PDFs and images via document/image content blocks.
// ─────────────────────────────────────────────────────────────────────
// Model routing: default to Haiku (cheap + fast). Auto-upgrade uploaded PDFs
// to Sonnet when they're visually dense — either >25 pages or >5 MB. This
// catches the program-deck / brochure case (Mercan, Henley CBI, etc.) where
// Haiku struggles with country detection and image-heavy reasoning, while
// keeping single-listing portal exports on cheap Haiku.
const AI_MODEL_HAIKU  = 'claude-haiku-4-5-20251001';
const AI_MODEL_SONNET = 'claude-sonnet-4-6';
const AI_PDF_PAGES_SONNET_THRESHOLD = 25;
const AI_PDF_BYTES_SONNET_THRESHOLD = 5 * 1024 * 1024; // 5 MB raw
const AI_MAX_TOKENS = 2048;

function pickAiModel(source, files) {
  if (source !== 'upload' || !Array.isArray(files) || !files.length) return AI_MODEL_HAIKU;
  let maxPages = 0;
  let maxBytes = 0;
  for (const f of files) {
    if (!f || f.type !== 'application/pdf') continue;
    if (typeof f.pages === 'number' && f.pages > maxPages) maxPages = f.pages;
    if (typeof f.data_b64 === 'string') {
      // base64 → bytes: length * 3/4 (close enough, ignoring padding)
      const bytes = Math.floor(f.data_b64.length * 0.75);
      if (bytes > maxBytes) maxBytes = bytes;
    }
  }
  if (maxPages > AI_PDF_PAGES_SONNET_THRESHOLD) return AI_MODEL_SONNET;
  if (maxBytes > AI_PDF_BYTES_SONNET_THRESHOLD) return AI_MODEL_SONNET;
  return AI_MODEL_HAIKU;
}

const AI_TOOL = {
  name: 'extract_property',
  description: 'Output the extracted real estate listing data in the exact NAC Lister Data Hub shape. Numeric fields are unsuffixed numbers (no $, no %).',
  input_schema: {
    type: 'object',
    properties: {
      name_en:    { type: ['string', 'null'], description: 'Property name in English. If listing language is not English, give a faithful English rendering.' },
      name_vi:    { type: ['string', 'null'], description: 'Property name in Vietnamese; mirror name_en if the listing is non-Vietnamese and no VI name is given.' },
      excerpt_en: { type: ['string', 'null'], description: '1-2 sentence English summary, ≤280 chars.' },
      excerpt_vi: { type: ['string', 'null'], description: '1-2 sentence Vietnamese summary, ≤280 chars.' },
      entry:      { type: ['number', 'null'], description: 'Asking/list price in USD THOUSANDS. e.g. $340,000 → 340; $2.5M → 2500. Convert from local currency at a sensible rate if needed.' },
      netYield:   { type: ['number', 'null'], description: 'Net rental yield as percent number (5.2 means 5.2%, NOT 0.052).' },
      irr:        { type: ['number', 'null'], description: 'IRR as percent number.' },
      coc:        { type: ['number', 'null'], description: 'Cash-on-cash return as percent number.' },
      payback:    { type: ['number', 'null'], description: 'Payback period in years.' },
      freehold:   { type: 'boolean', description: 'true if the listing explicitly indicates freehold / fee simple. false otherwise.' },
      tags:       { type: 'array', items: { type: 'string', enum: ['hot', 'free', 'res', 'need', 'pr'] }, description: 'Pick from: hot (default), free (freehold), res (residency-eligible), need (info missing), pr (citizenship/passport).' },
      priceM2:    { type: ['number', 'null'], description: 'Price per m² in USD.' },
      region:     { type: 'string', enum: ['us', 'eu', 'asia', 'me', 'pac', 'caribe'], description: 'us=North America, eu=Europe, asia=Asia, me=Middle East, pac=Oceania/Pacific, caribe=Caribbean/Central America.' },
      country:    { type: 'string', description: 'Flag emoji + country/region. e.g. "🇦🇪 Dubai, UAE" or "🇮🇩 Indonesia — Bali".' },
      address:    { type: ['string', 'null'] },
      city:       { type: ['string', 'null'] },
      mls:        { type: ['string', 'null'], description: 'MLS / reference / listing ID if shown.' },
      agent:      { type: ['string', 'null'] },
      type:       { type: ['string', 'null'], description: 'Property type — one of: Branded Residences, Villa, Condo, Resort, Townhouse, Multifamily, Estate, Land. Null if unclear.' },
      beds:       { type: ['integer', 'null'] },
      baths:      { type: ['number', 'null'] },
      sqft:       { type: ['integer', 'null'], description: 'Built area in sqft. Convert if source is m² (1 m² = 10.764 sqft).' },
      lotSqft:    { type: ['integer', 'null'], description: 'Lot/land area in sqft.' },
      yearBuilt:  { type: ['integer', 'null'] },
      annualTax:  { type: ['integer', 'null'], description: 'Annual property tax in USD.' },
      hoa:        { type: ['integer', 'null'], description: 'Monthly HOA / service charge in USD.' },
      img:        { type: ['string', 'null'], description: 'A representative image URL if visible in the source HTML.' },
      source:     { type: ['string', 'null'], description: 'Origin platform name (Zillow / Bayut / Knight Frank / etc.) or a short label.' },
      confidence: { type: 'integer', minimum: 0, maximum: 100, description: 'Self-assessed extraction confidence 0–100 based on how many key fields you could fill from the source.' },
    },
    required: ['name_en', 'region', 'country', 'tags', 'freehold', 'confidence'],
  },
};

const AI_SYSTEM_PROMPT = [
  'You are the AI extractor inside NAC (Nomad Asset Collective) Lister — a tool that ingests real estate listings, brochures, and program decks for a Vietnamese-investor-facing Data Hub.',
  '',
  'The documents you see are often:',
  '• Multi-page property brochures (PDFs) with images, floorplans, financial tables',
  '• Investment-immigration program decks (RBI / CBI / Golden Visa) that describe ONE specific real estate asset inside a country program',
  '• Listing pages from real estate portals (Zillow, Bayut, PropertyGuru, etc.)',
  '• Pasted listing text — often Vietnamese, mixed VI/EN, or other languages',
  '',
  'YOUR JOB: extract the data for the SINGLE primary investable property the document markets. Respond by calling the `extract_property` tool exactly once. No prose.',
  '',
  'EXTRACTION PROCESS (think silently, then call the tool):',
  '1. Identify the PRIMARY ASSET — the specific named property/development being sold (e.g. "Pullman Panama City Hotel & Residences"), NOT the document title (e.g. "Panama Strategic Investor Program Overview" is a doc title, not a property name).',
  '2. If a USER HINT is provided, treat it as a FOCUS DIRECTIVE. Phrases like "tìm thông tin về X", "find info on X", "focus on X", "scan for X" mean: locate X inside the document and extract data for X specifically, even if X is one section of a larger program brochure that covers many things.',
  '3. Identify the COUNTRY where the building is physically located. NOT the buyer\'s country, NOT the currency country. If a country name appears 5+ times across the document, that is almost certainly the property\'s country.',
  '4. For every numeric field, ask: "Does the document explicitly state this number?" If yes, copy it. If no, return null. Do NOT invent plausible defaults.',
  '',
  'CRITICAL — NO HALLUCINATION:',
  '• Never invent yield / IRR / cash-on-cash. If a net rental yield is not stated, netYield = null. Do not default to 6%, 8%, or "industry typical".',
  '• Never invent payback years — leave null; downstream code derives it from yield.',
  '• Never invent prices. If only a minimum-investment threshold for a residency program is shown (e.g. "$300,000 USD minimum"), that is the qualifying investment, NOT necessarily the property entry price — use it only if the document says so.',
  '• Never invent property names. If no specific name appears, use the project name from the deck; if even that is absent, use "[Brand] [City]" or "Property in [City]".',
  '• Round-number red flag: if your draft has yield=6, irr=12, coc=8 (or any all-round-numbers combo), you are guessing — set them to null instead.',
  '',
  'COUNTRY → REGION (use these exact codes):',
  '• us     = USA, Canada, Mexico',
  '• eu     = any European country (Portugal, Greece, Spain, Italy, UK, France, Cyprus, Malta, Hungary, Albania, Montenegro, etc.)',
  '• asia   = Vietnam, Thailand, Indonesia, Malaysia, Singapore, Japan, Korea, Hong Kong, Philippines, India',
  '• me     = UAE (Dubai, Abu Dhabi), Saudi Arabia, Qatar, Oman, Bahrain, Turkey, Israel',
  '• pac    = Australia, New Zealand, Fiji, Vanuatu, Samoa, Papua New Guinea, Nauru',
  '• caribe = Caribbean (St Kitts, Antigua, Dominica, Grenada, St Lucia, St Vincent, Bahamas, Jamaica, Trinidad, Barbados) AND Central America (Panama, Belize, Costa Rica, Honduras, El Salvador, Guatemala)',
  '',
  'NUMBER FORMAT:',
  '• entry: USD THOUSANDS. $340,000 → 340. $2.5M → 2500. Convert non-USD at sensible rates.',
  '• netYield / irr / coc: percent numbers. 5.2 = 5.2% (NOT 0.052). NULL if not stated.',
  '• sqft: convert m² to sqft (×10.764) if source is in m².',
  '',
  'LANGUAGE:',
  '• name_en: Property name in English. Brand names (Pullman, Marriott, Hyatt, Accor) stay in English; translate generic descriptors.',
  '• name_vi: Vietnamese name; mirror name_en when source is non-Vietnamese.',
  '• excerpt_en / excerpt_vi: tight 1–2 sentence summary in each language, ≤280 chars.',
  '• country field: flag emoji + name, e.g. "🇵🇦 Panama", "🇦🇪 Dubai, UAE", "🇮🇩 Indonesia — Bali".',
  '',
  'TAGS: always include "hot". Add "free" if freehold/fee simple. Add "res" if the property qualifies for residency/visa programs. Add "pr" if it qualifies for citizenship/passport (CBI). Add "need" only if critical data is missing.',
  '',
  'CONFIDENCE: 80+ only when price + size + location + at least one yield metric are all explicitly stated. 50–79 if partial. <50 if mostly inferred or the doc is more program-overview than property-spec.',
  '',
  'EXAMPLE OF FOCUS-DIRECTIVE HANDLING:',
  'Doc = 50-page Vietnamese brochure titled "PANAMA STRATEGIC INVESTOR — OVERVIEW" describing Mercan Group + the Panama Qualified Investor Program + a specific Pullman-branded hotel/casino/residences development on Avenida Ricardo Arias in Panama City (306 keys, 27 floors).',
  'Hint = "tìm thông tin về Pullman resort đầu tư".',
  'CORRECT extraction:',
  '  name_en = "Pullman Panama City Hotel & Residences" (or similar — pull the actual project name from the deck)',
  '  country = "🇵🇦 Panama"',
  '  region  = "caribe"',
  '  city    = "Panama City"',
  '  type    = "Branded Residences" or "Resort"',
  '  netYield/irr/coc = null (the deck doesn\'t state these explicitly — do NOT default to 6/12/8)',
  '  entry   = the qualifying investment USD amount IF the deck states the actual property price; otherwise null with a note that this is a program min-investment',
  '  tags    = ["hot", "res"] (Golden Visa / residency program)',
  '  confidence = 50–65 (location + name solid, financials missing)',
  'INCORRECT (what NOT to do): country=USA, name=doc title, yield/irr/coc filled with round defaults.',
].join('\n');

async function callClaude(env, contentBlocks, model) {
  const res = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: {
      'x-api-key': env.ANTHROPIC_API_KEY,
      'anthropic-version': '2023-06-01',
      'content-type': 'application/json',
    },
    body: JSON.stringify({
      model: model || AI_MODEL_HAIKU,
      max_tokens: AI_MAX_TOKENS,
      tools: [AI_TOOL],
      tool_choice: { type: 'tool', name: 'extract_property' },
      system: AI_SYSTEM_PROMPT,
      messages: [{ role: 'user', content: contentBlocks }],
    }),
  });
  if (!res.ok) {
    const errText = await res.text().catch(() => '');
    throw new Error('Claude API ' + res.status + ': ' + errText.slice(0, 400));
  }
  const j = await res.json();
  const tu = (j.content || []).find(b => b.type === 'tool_use' && b.name === 'extract_property');
  if (!tu) throw new Error('No extract_property tool_use in Claude response');
  return { data: tu.input || {}, usage: j.usage || null, stop_reason: j.stop_reason || null };
}

// Normalise + fill defaults so the Lister's plRenderFields() never breaks.
function normaliseExtraction(d, fallbackSource) {
  const out = { ...d };
  out.source     = out.source || fallbackSource || 'AI';
  out.name_en    = out.name_en || 'Property';
  out.name_vi    = out.name_vi || out.name_en;
  out.excerpt_en = out.excerpt_en || out.excerpt_vi || '';
  out.excerpt_vi = out.excerpt_vi || out.excerpt_en || '';
  out.tags       = (Array.isArray(out.tags) && out.tags.length) ? out.tags : ['hot'];
  out.freehold   = !!out.freehold;
  out.region     = out.region || 'asia';
  out.country    = out.country || '🌍 —';
  if (typeof out.confidence !== 'number') out.confidence = 70;
  // Derive payback if missing but yield present
  if (out.payback == null && typeof out.netYield === 'number' && out.netYield > 0) {
    out.payback = parseFloat((100 / out.netYield).toFixed(1));
  }
  // Derive priceM2 if missing but entry+sqft present
  if (out.priceM2 == null && typeof out.entry === 'number' && typeof out.sqft === 'number' && out.sqft > 0) {
    // entry is USD-thousands; sqft → m² for $/m²
    const m2 = out.sqft / 10.764;
    if (m2 > 0) out.priceM2 = Math.round((out.entry * 1000) / m2);
  }
  return out;
}

async function aiExtract(env, body) {
  const source = body.source || 'paste';
  const hint = (body.hint || '').toString().trim();
  let blocks = [];
  let fallbackSource = 'AI';

  if (source === 'url') {
    const target = (body.url || '').toString().trim();
    if (!/^https?:\/\//i.test(target)) {
      const e = new Error('Provide url=https://...'); e.code = 'bad_url'; throw e;
    }
    let scraped = '';
    try {
      scraped = await fetchAndClean(target);
    } catch (e) {
      const ee = new Error('Could not fetch source URL: ' + e.message);
      ee.code = 'scrape_failed'; throw ee;
    }
    if (!scraped || scraped.length < 50) {
      const e = new Error('Source returned too little text (' + scraped.length + ' chars) — likely bot-blocked.');
      e.code = 'scrape_thin'; throw e;
    }
    fallbackSource = 'AI: ' + (new URL(target)).hostname;
    blocks.push({
      type: 'text',
      text: 'LISTING URL: ' + target + '\n\nSCRAPED PAGE TEXT (cleaned):\n' + scraped.slice(0, 50000)
            + (hint ? '\n\nUSER HINT: ' + hint : ''),
    });
  } else if (source === 'paste') {
    const text = (body.text || '').toString();
    if (!text.trim()) {
      const e = new Error('No paste text provided.'); e.code = 'no_text'; throw e;
    }
    fallbackSource = 'AI: Paste';
    blocks.push({
      type: 'text',
      text: 'PASTED LISTING TEXT:\n' + text.slice(0, 50000) + (hint ? '\n\nUSER HINT: ' + hint : ''),
    });
  } else if (source === 'upload') {
    const files = Array.isArray(body.files) ? body.files : [];
    if (!files.length) {
      const e = new Error('No files provided.'); e.code = 'no_files'; throw e;
    }
    fallbackSource = 'AI: ' + files.map(f => f.name).join(', ').slice(0, 60);
    blocks.push({
      type: 'text',
      text: 'UPLOADED LISTING DOCUMENT(S):\n' + files.map(f => '- ' + f.name + ' (' + f.type + ')').join('\n')
            + (hint ? '\n\nUSER HINT: ' + hint : '')
            + '\n\nExtract the property data from the attached file(s).',
    });
    for (const f of files) {
      if (!f || !f.data_b64) continue;
      const mt = f.type || '';
      if (mt === 'application/pdf') {
        blocks.push({ type: 'document', source: { type: 'base64', media_type: 'application/pdf', data: f.data_b64 } });
      } else if (/^image\/(png|jpe?g|webp|gif)$/i.test(mt)) {
        const norm = mt.toLowerCase() === 'image/jpg' ? 'image/jpeg' : mt.toLowerCase();
        blocks.push({ type: 'image', source: { type: 'base64', media_type: norm, data: f.data_b64 } });
      } else if (/^text\//.test(mt) && f.data_b64) {
        // Plain text file — decode and append to the intro text block
        try {
          const decoded = atob(f.data_b64);
          blocks[0].text += '\n\n--- ' + (f.name || 'file') + ' ---\n' + decoded.slice(0, 20000);
        } catch (_) { /* ignore */ }
      }
    }
  } else {
    const e = new Error('Unknown source: ' + source); e.code = 'bad_source'; throw e;
  }

  const model = pickAiModel(source, body.files);
  const { data, usage } = await callClaude(env, blocks, model);
  const normalised = normaliseExtraction(data, fallbackSource);
  return { data: normalised, usage, model };
}

// ─────────────────────────────────────────────────────────────────────
// ROUTER
// ─────────────────────────────────────────────────────────────────────
export default {
  async fetch(request, env) {
    // CORS preflight
    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: corsHeaders });
    }

    const url = new URL(request.url);
    const path = url.pathname;

    // ── POST /properties — create new property in Notion (from NAC Lister) ──
    if (request.method === 'POST' && path === '/properties') {
      if (!env.NOTION_KEY) {
        return jsonResponse({ error: 'worker_misconfigured', message: 'Set NOTION_KEY in Worker Variables.' }, 500);
      }
      try {
        const body = await request.json();
        const created = await createPropertyInNotion(env, body);
        return jsonResponse(created, 201);
      } catch (e) {
        return jsonResponse({ error: 'create_failed', message: e.message }, 500);
      }
    }

    // ── POST /ai-extract — Claude-powered structured extraction for NAC Lister ──
    if (request.method === 'POST' && path === '/ai-extract') {
      if (!env.ANTHROPIC_API_KEY) {
        return jsonResponse({ error: 'worker_misconfigured', message: 'Set ANTHROPIC_API_KEY in Worker Variables.' }, 500);
      }
      try {
        const body = await request.json();
        const { data, usage, model } = await aiExtract(env, body);
        return jsonResponse({ success: true, data, usage, model }, 200);
      } catch (e) {
        const code = e.code || 'ai_extract_failed';
        const status = (code === 'bad_url' || code === 'no_text' || code === 'no_files' || code === 'bad_source') ? 400
                     : (code === 'scrape_failed' || code === 'scrape_thin') ? 502
                     : 500;
        return jsonResponse({ error: code, message: e.message }, status);
      }
    }

    if (request.method !== 'GET') {
      return jsonResponse({ error: 'method_not_allowed', message: 'GET / POST only.' }, 405);
    }

    // ── Health check ─────────────────────────────────────────────────
    if (path === '/health') {
      return jsonResponse({ status: 'ok', worker: 'nac-property-hub', ts: new Date().toISOString() });
    }

    // ── GET /scrape?url=... — fetches a listing URL server-side, returns clean text ──
    // Used by the NAC Lister regex fallback path. The AI path uses fetchAndClean
    // internally inside aiExtract().
    if (path === '/scrape') {
      const target = url.searchParams.get('url');
      if (!target || !/^https?:\/\//i.test(target)) {
        return jsonResponse({ error: 'bad_url', message: 'Provide ?url=https://...' }, 400);
      }
      try {
        const text = await fetchAndClean(target);
        return jsonResponse({ success: true, url: target, length: text.length, text }, 200, {
          'Cache-Control': 'public, max-age=300, s-maxage=600',
        });
      } catch (e) {
        const status = e.upstreamStatus ? 502 : 502;
        return jsonResponse({ error: 'scrape_error', message: e.message, upstream_status: e.upstreamStatus || null }, status);
      }
    }

    // ── NOTION_KEY check ─────────────────────────────────────────────
    if (!env.NOTION_KEY) {
      return jsonResponse({ error: 'worker_misconfigured', message: 'Set NOTION_KEY in Worker Variables.' }, 500);
    }

    // ── GET /properties — full list ──────────────────────────────────
    if (path === '/properties') {
      try {
        const props = await fetchAllProperties(env);
        props.sort((a, b) => a.id - b.id);
        return jsonResponse(props, 200, {
          'Cache-Control': 'public, max-age=120, s-maxage=300',
        });
      } catch (e) {
        return jsonResponse({ error: 'fetch_failed', message: e.message }, 502);
      }
    }

    // ── GET /properties/:id — single property ────────────────────────
    const singleMatch = path.match(/^\/properties\/(\d+)$/);
    if (singleMatch) {
      try {
        const targetId = parseInt(singleMatch[1], 10);
        const props = await fetchAllProperties(env);
        const found = props.find(p => p.id === targetId);
        if (!found) return jsonResponse({ error: 'not_found', message: 'Property NAC-' + targetId + ' not found or not Live.' }, 404);
        return jsonResponse(found, 200, {
          'Cache-Control': 'public, max-age=120, s-maxage=300',
        });
      } catch (e) {
        return jsonResponse({ error: 'fetch_failed', message: e.message }, 502);
      }
    }

    // ── 404 fallback ─────────────────────────────────────────────────
    return jsonResponse({ error: 'not_found', message: 'Routes: GET /properties, GET /properties/:id, GET /health, GET /scrape?url=..., POST /properties, POST /ai-extract' }, 404);
  },
};
