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
 *        NOTION_KEY = secret_xxxxxxxxxxxxxxxx   (encrypt = ON)
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
