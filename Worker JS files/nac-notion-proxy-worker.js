/**
 * ─────────────────────────────────────────────────────────────────────────
 *  NAC Notion Proxy — Cloudflare Worker
 *  https://nac-notion-proxy.ray-vtt.workers.dev/
 * ─────────────────────────────────────────────────────────────────────────
 *
 *  Forwards Notion API calls from the browser, holding the Notion
 *  integration token server-side. Backward compatible with the original
 *  CREATE-only behavior — existing pages (overview, residence-index,
 *  property-hub) keep working with no change.
 *
 *  ── Cloudflare setup ─────────────────────────────────────────────
 *    Workers → your worker → Settings → Variables → add:
 *        NOTION_KEY = secret_xxxxxxxxxxxxxxxx   (encrypt = ON)
 *    Then paste this script into the editor → Save and Deploy.
 *
 *  ── Three actions supported via the request body ────────────────
 *
 *  1) CREATE a new page  (DEFAULT — backward compatible)
 *     POST {WORKER_URL}
 *     Body:
 *       {
 *         "parent":     { "database_id": "<DB_ID>" },
 *         "properties": { ...notion props... }
 *       }
 *
 *  2) UPDATE an existing page  (NEW)
 *     POST {WORKER_URL}
 *     Body:
 *       {
 *         "_meta":      { "action": "update", "page_id": "<NOTION_PAGE_ID>" },
 *         "properties": { ...props to merge... }
 *       }
 *     Used by brochure paywall: when warm lead clicks [Có], we update the
 *     SAME row that the overview form created (matched by ?lead=<page_id>).
 *
 *  3) QUERY a database  (NEW — for lookups by email/phone)
 *     POST {WORKER_URL}
 *     Body:
 *       {
 *         "_meta":       { "action": "query" },
 *         "database_id": "<DB_ID>",
 *         "filter":      { ...notion filter... },
 *         "page_size":   10
 *       }
 *     Useful if a brochure has only ?email= and you want to find the
 *     existing lead row before deciding to update vs. create.
 *
 *  Response: whatever the Notion API returns, with CORS headers added.
 *  Errors are JSON: { error: "...", message: "..." }
 * ─────────────────────────────────────────────────────────────────────────
 */

const NOTION_VERSION = '2022-06-28';

const corsHeaders = {
  'Access-Control-Allow-Origin':  '*',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
  'Access-Control-Max-Age':       '86400',
};

function jsonResponse(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json', ...corsHeaders },
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

// Notion IDs are UUIDs (32 hex chars, optionally hyphenated).
function isValidNotionId(id) {
  if (typeof id !== 'string') return false;
  const stripped = id.replace(/-/g, '').trim();
  return /^[a-f0-9]{32}$/i.test(stripped);
}

export default {
  async fetch(request, env) {
    // ── CORS preflight ───────────────────────────────────────────────
    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: corsHeaders });
    }

    if (request.method !== 'POST') {
      return jsonResponse({ error: 'method_not_allowed', message: 'Only POST is supported.' }, 405);
    }

    // ── Sanity: NOTION_KEY must be configured ────────────────────────
    if (!env.NOTION_KEY) {
      return jsonResponse({
        error:   'worker_misconfigured',
        message: 'Set NOTION_KEY in Cloudflare Worker → Settings → Variables.',
      }, 500);
    }

    // ── Parse body ───────────────────────────────────────────────────
    let body;
    try {
      body = await request.json();
    } catch (e) {
      return jsonResponse({ error: 'invalid_json', message: e.message }, 400);
    }

    // Extract _meta routing info, then strip it before forwarding to Notion
    const meta   = body._meta || {};
    const action = (meta.action || 'create').toLowerCase();
    delete body._meta;

    try {
      let res;

      // ─────────────────────────────────────────────────────────────
      // UPDATE — PATCH /v1/pages/{page_id}
      // ─────────────────────────────────────────────────────────────
      if (action === 'update') {
        if (!isValidNotionId(meta.page_id)) {
          return jsonResponse({
            error:   'invalid_page_id',
            message: 'For action=update, _meta.page_id must be a valid Notion page ID (UUID).',
          }, 400);
        }
        res = await notionFetch(env, '/pages/' + meta.page_id, {
          method: 'PATCH',
          body:   JSON.stringify(body),
        });

      // ─────────────────────────────────────────────────────────────
      // QUERY — POST /v1/databases/{database_id}/query
      // ─────────────────────────────────────────────────────────────
      } else if (action === 'query') {
        const dbId = body.database_id;
        if (!isValidNotionId(dbId)) {
          return jsonResponse({
            error:   'invalid_database_id',
            message: 'For action=query, body.database_id must be a valid Notion DB ID.',
          }, 400);
        }
        const queryBody = { ...body };
        delete queryBody.database_id;   // it goes in the URL, not the body
        res = await notionFetch(env, '/databases/' + dbId + '/query', {
          method: 'POST',
          body:   JSON.stringify(queryBody),
        });

      // ─────────────────────────────────────────────────────────────
      // CREATE (default — backward compatible) — POST /v1/pages
      // ─────────────────────────────────────────────────────────────
      } else if (action === 'create') {
        res = await notionFetch(env, '/pages', {
          method: 'POST',
          body:   JSON.stringify(body),
        });

      } else {
        return jsonResponse({
          error:   'unknown_action',
          message: 'Supported _meta.action values: "create", "update", "query".',
        }, 400);
      }

      // Forward Notion's response (with status code) + add CORS
      const data = await res.json();
      return jsonResponse(data, res.status);

    } catch (e) {
      return jsonResponse({
        error:   'worker_exception',
        message: e.message || String(e),
      }, 502);
    }
  },
};
