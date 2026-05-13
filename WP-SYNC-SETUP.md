# NAC Brochure → WordPress Sync — Setup Guide

Push edits from local HTML files straight to WordPress in 1 command. No more copy-pasting into the WP editor, no Elementor/Gutenberg block fiddling.

---

## Prerequisites

- **Python 3** installed (you can check by running `python --version` or `python3 --version` — needs ≥3.7).
- Admin access to nomadassetcollective.com WP.

---

## One-time setup (~3 minutes)

### Step 1 — Create an Application Password in WordPress

1. Go to: https://nomadassetcollective.com/wp-admin/profile.php
2. Scroll to the **Application Passwords** section near the bottom.
3. Name it `NAC Sync` (or anything memorable).
4. Click **Add New Application Password**.
5. **Copy the 24-char password immediately** — looks like:
   ```
   abcd efgh ijkl mnop qrst uvwx
   ```
   The spaces are part of the password. WordPress shows it ONCE, so save it now.

> 💡 An Application Password is scoped to the REST API only — it can't log into the admin UI. Safe to revoke anytime if you suspect a leak.

### Step 2 — Create `.env` file

In this folder (`NAC-brochures-reviewed/`), create a file named `.env` with two lines:

```
WP_USER=your-wp-username
WP_APP_PASSWORD=abcd efgh ijkl mnop qrst uvwx
```

Replace `your-wp-username` with your actual WP username (the one you log into wp-admin with), and paste the App Password from Step 1.

> ⚠️ **DO NOT commit `.env` to git or share it publicly.** Add `.env` to `.gitignore` if you have one.

### Step 3 — Test connection (no changes pushed)

```
python sync_brochures.py
```

You should see a status table like:

```
NAC Brochure Sync — status
──────────────────────────────────────────────────────────────────────
  alias        page     local  wp_modified
──────────────────────────────────────────────────────────────────────
  portugal     1848     124KB  2026-05-06T12:34:00
  greece       1827     119KB  2026-05-06T12:35:11
  cyprus       1844     128KB  2026-05-06T12:36:22
  turkey       1836     132KB  2026-05-06T15:57:16
  uae          1901     115KB  2026-05-06T12:38:00
  uk           1932     117KB  2026-05-06T12:39:11
  malta        1924     130KB  2026-05-06T12:40:22
  stkitts      1921     112KB  2026-05-06T12:41:33
  thailand     1926     122KB  2026-05-06T12:42:44
──────────────────────────────────────────────────────────────────────
```

If you see HTTP errors here, the .env credentials are wrong or the WP REST API isn't reachable from your network.

### Step 4 — Dry-run a single brochure

```
python sync_brochures.py turkey --dry-run
```

This previews what would be pushed without actually changing WP. If output shows the right local file size, you're ready.

### Step 5 — Push for real

```
python sync_brochures.py turkey
```

Output:
```
  turkey  page 1836  ←  turkey-cbi_8.html  (132KB)
    ✓ pushed · modified: 2026-05-06T17:23:00
```

Refresh the live URL in your browser — you should see the updated content.

---

## Daily workflow

1. Edit local HTML in `NAC-brochures-reviewed/` folder (in your editor of choice, or via Cowork/Claude Code).
2. Save.
3. Run `python sync_brochures.py <alias>` to push that one, or `python sync_brochures.py --all` to push everything.

Done. The brochure on WordPress reflects local within ~2 seconds.

---

## Common scenarios

### "I added a new country brochure (e.g., Hungary). How do I include it?"

1. Create the HTML file locally (e.g., `hungary-rbi.html`).
2. Publish a new WP page with that HTML pasted in (one-time, via WP admin).
3. Note the page ID (visible in the URL when editing: `post=12345`).
4. Open `sync_brochures.py` → add to `BROCHURES` dict:
   ```python
   'hungary': ('hungary-rbi.html', 12345, 'chuong-trinh-hungary-...'),
   ```
5. Save script. Now `python sync_brochures.py hungary` works.

### "I want to also sync NAC-BROCHURES-OVERVIEW.html"

1. Find that page's ID in WP.
2. Add to `BROCHURES`:
   ```python
   'overview': ('NAC-BROCHURES-OVERVIEW.html', <page_id>, '<slug>'),
   ```

### "Sync fails with HTTP 401 — Unauthorized"

- Wrong username, wrong App Password, OR App Password got revoked.
- Recreate the App Password in WP (Step 1) and update `.env`.

### "Sync fails with HTTP 403 — rest_cannot_edit"

- Your WP user doesn't have permission to edit pages. Make sure the user has `Administrator` or `Editor` role.

### "Some HTML got stripped after sync"

- WordPress has KSES (HTML sanitizer) for non-admin roles. Make sure your user is `Administrator` — admins on single-site installs can post any HTML (including `<script>` and `<style>`).
- If still stripped, install the **"Disable Filtered HTML"** plugin or set `define('DISALLOW_UNFILTERED_HTML', false);` in `wp-config.php`.

### "I want to backup the live WP version before pushing"

Add this command before the sync (one-liner):
```
curl -s 'https://nomadassetcollective.com/wp-json/wp/v2/pages/1836' > backup-turkey-$(date +%Y%m%d).json
```

---

## Files in this setup

| File | Purpose |
|---|---|
| `sync_brochures.py` | The sync script. Runs locally. |
| `.env` | Your WP credentials (DO NOT share/commit). |
| `WP-SYNC-SETUP.md` | This file. |
| `<brochure>.html` | Local source of truth — edit these. |

---

## Going further

If you want full git-based versioning of brochures, just `git init` the folder, add `.env` to `.gitignore`, and you'll have rollbacks + diff history. Each `python sync_brochures.py --all` becomes "deploy from main".
