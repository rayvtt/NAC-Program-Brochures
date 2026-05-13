# NAC Brochure → WordPress Sync — Setup Guide

Brochure HTML is the source of truth in this git repo. Pushing to `main` automatically syncs all changed brochures to nomadassetcollective.com via the WordPress REST API.

```
edit brochure (Claude Code / locally / GitHub web)
   → commit & push to main
   → GitHub Action runs sync_brochures.py
   → WP REST API receives the new HTML
   → live site updates within ~30 seconds
```

---

## One-time setup

### 1. Create a WordPress Application Password

1. Go to https://nomadassetcollective.com/wp-admin/profile.php
2. Scroll to **Application Passwords**.
3. Name it `NAC Git Sync` → click **Add New Application Password**.
4. **Copy the 24-char password immediately** (looks like `abcd efgh ijkl mnop qrst uvwx`; the spaces are part of it). WordPress shows it once.

> Application Passwords are scoped to the REST API only — they can't log into wp-admin. Revoke anytime from the same page.

### 2. Add the credentials as GitHub repo Secrets

In this repo: **Settings → Secrets and variables → Actions → New repository secret**. Add two secrets:

| Name | Value |
|---|---|
| `WP_USER` | your WP username (e.g. `admin_web`) |
| `WP_APP_PASSWORD` | the 24-char password from step 1 |

These are encrypted at rest, only injected as env vars during the workflow run, never printed in logs.

### 3. Verify the workflow

After both secrets exist, go to **Actions → Sync brochures to WordPress → Run workflow** → set `dry_run` to **true** → Run. The job should print the list of brochures with sizes and "(dry-run — no PUT)" — no actual WP changes.

---

## Daily workflow

### Edit + push (the common path)

1. Edit any file under `Brochures html/`, `NAC-RESIDENCE-INDEX.html`, or `sync_brochures.py`.
2. Commit, push to `main` (typically via PR merge — `main` is branch-protected).
3. The **Sync brochures to WordPress** action triggers automatically and pushes every brochure to WP.

Pushes to other branches do NOT sync to WP — they're for previewing. Sync only happens on `main`.

### Push a single brochure manually

Sometimes you want to retry one brochure without touching the rest:

1. **Actions** tab → **Sync brochures to WordPress** → **Run workflow**.
2. `target`: enter an alias (e.g. `turkey`, `portugal`, `overview`). Default `--all` pushes everything.
3. `dry_run`: leave unchecked to push for real.
4. Run.

### Aliases

The script's `BROCHURES` dict (in `sync_brochures.py`) maps short aliases to (filename, WP page ID, slug):

| Alias | Brochure |
|---|---|
| `portugal` | Portugal Golden Visa |
| `greece` | Greece Golden Visa |
| `cyprus` | Cyprus PR |
| `turkey` | Turkey CBI |
| `uae` | UAE Golden Visa |
| `uk` | UK Innovator Founder |
| `malta` | Malta MPRP |
| `stkitts` | St. Kitts & Nevis CBI |
| `thailand` | Thailand LTR |
| `newzealand` | New Zealand Active Investor Plus |
| `panama` | Panama RBI |
| `malaysia` | Malaysia MM2H |
| `overview` | NAC-BROCHURES-OVERVIEW.html (the gateway) |
| `index` | NAC-RESIDENCE-INDEX.html (comparison index) |
| `nph` | NAC-PROPERTY-HUB.html (lives in the property hub repo) |

---

## Adding a new country brochure

1. Create the HTML locally or via Claude Code: `Brochures html/<country>-<program>.html`.
2. In WP admin, create a new empty page and publish it. Note the page ID (in the edit URL: `post=NNNN`) and slug.
3. Add to `sync_brochures.py` → `BROCHURES` dict:
   ```python
   'hungary': ('hungary-rbi.html', 12345, 'chuong-trinh-hungary-...'),
   ```
4. Add a matching `openModal()` call in `Brochures html/NAC-BROCHURES-OVERVIEW.html` so the funnel routes leads correctly (the `PROGRAM` tag must match the brochure's `var PROGRAM` exactly).
5. Commit & push to `main`. The new brochure syncs on the next run.

---

## Troubleshooting

### `HTTP 401 — rest_forbidden` / `Unauthorized`
Wrong username or password, or the App Password was revoked. Recreate it in WP (step 1 above) and update the `WP_APP_PASSWORD` secret in GitHub.

### `HTTP 403 — rest_cannot_edit`
The WP user lacks edit permission. Set the role to `Administrator` (single-site installs allow admins to post raw HTML).

### HTML got stripped after sync
WordPress's KSES filter is stripping tags. Ensure the user is `Administrator` on a single-site install. If still stripped, set `define('DISALLOW_UNFILTERED_HTML', false);` in `wp-config.php`, or install the **Disable Filtered HTML** plugin.

### Action failed with `Missing credentials`
The `WP_USER` and/or `WP_APP_PASSWORD` secret isn't set. Check **Settings → Secrets and variables → Actions**.

### A brochure didn't sync
Check that its filename in `BROCHURES` matches the actual file in `Brochures html/`. Filenames with spaces or parens (e.g. `uk-rbi_1 (2).html`) must match character-for-character.

### Need to test without touching WP
Trigger the workflow manually with `dry_run: true`. The action will print what would be pushed and exit without calling the API.

---

## Files in this setup

| File | Purpose |
|---|---|
| `sync_brochures.py` | The sync script. Runs in GitHub Actions (or locally with a `.env`). |
| `.github/workflows/wp-sync.yml` | GitHub Action — runs on push to `main` or manual dispatch. |
| `Brochures html/<brochure>.html` | Source of truth — edit these. |
| `NAC-RESIDENCE-INDEX.html` | Comparison index page (lives in repo root, synced as `index`). |
| `WP-SYNC-SETUP.md` | This file. |

---

## Local fallback (rarely needed)

`sync_brochures.py` still supports running on a laptop with a local `.env` file (`WP_USER=... / WP_APP_PASSWORD=...`). The script checks env vars first, then `.env`. **Don't commit `.env`** — it's in `.gitignore`. This is a fallback only; the GitHub Action is the primary path.
