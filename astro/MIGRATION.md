# Astro Migration

This directory is a side-by-side Astro prototype. The current Jekyll site remains intact at the repository root.

## Current Status

- Branch: `astro-migration`
- Cloudflare Pages project: `peipeipe-net-astro`
- Preview URL: `https://peipeipe-net-astro.pages.dev/`
- Preview check page: `https://peipeipe-net-astro.pages.dev/cloudflare-preview/`
- Latest successful GitHub Actions run before the master merge: `26958949223`
- Latest pushed migration commit: `94474c5 Migrate map data pages to Astro`
- Production `https://www.peipeipe.net` is still served by the existing GitHub Pages/Jekyll workflow.

The Cloudflare Pages preview deploy is working. The first deploy attempt failed because root `.gitignore` ignored `astro/package.json`; that was fixed by explicitly tracking the Astro package manifest.

`master` has now been merged into `astro-migration` locally at merge commit `26c0401`, bringing in:

- `2188ea2 Normalize old post slugs`
- `bb9bce8 Add dated permalinks to old posts`

Last verified locally:

```text
Astro build: success
Generated pages: 405
URL manifest: 413 URLs
Legacy invalid percent slugs: 0
Workflow YAML parse: ok
Cloudflare preview HTTP status: 200 before the local master merge
```

Recent UI/content work on `astro-migration`:

- Ported the Jekyll-like masthead, footer links, RSS link, avatar, and metadata into Astro.
- Tightened blog and diary page spacing and typography to match the current site more closely.
- Changed list excerpts to show only the first sentence instead of a long multi-sentence snippet.
- Normalized Markdown image URLs with spaces so posts that were rendering cleanly in Jekyll also render correctly in Astro.
- Migrated the wide data/map pages for activity, mountains, places, and onsen into Astro layouts.

## Local Node

Astro 6 requires Node 22.12 or newer. This workspace was tested with Node 22.22.3 installed at:

```sh
/home/peipeipe/.local/nodejs/current/bin/node
```

Use it explicitly for now:

```sh
PATH=/home/peipeipe/.local/nodejs/current/bin:$PATH npm run build
```

## Current Scope

- Reads existing `../_posts/*.md` files without moving them.
- Reads existing `../_diary/*.md` files without moving them.
- Builds the blog index, post detail pages, diary index, diary detail pages, `about`, `search`, RSS, and sitemap.
- Builds `404.html` and `robots.txt`.
- Builds `/activity/`, `/mountains/`, `/places/`, and `/onsen/` as wide map-focused data pages.
- Builds `/activity-data.json`, `/mountains-data.json`, `/places-data.json`, `/places.json`, and `/onsen-data.json`.
- Builds a preview-only `/cloudflare-preview/` page.
- Deploys the Astro prototype to Cloudflare Pages via `.github/workflows/cloudflare-pages-astro-preview.yml`.
- Keeps the current Jekyll site deploy workflow untouched.

Current content counts from `migration/astro-url-manifest.json`:

```text
posts: 355
diary entries: 40
tracked URLs: 413
```

## Verification

```sh
PATH=/home/peipeipe/.local/nodejs/current/bin:$PATH npm run build
PATH=/home/peipeipe/.local/nodejs/current/bin:$PATH npm run manifest
PATH=/home/peipeipe/.local/nodejs/current/bin:$PATH npm run check:legacy-slugs
```

Generated verification files:

- `migration/astro-url-manifest.json`
- `migration/legacy-invalid-percent-slugs.json`

## Cloudflare Pages Preview

This prototype is published to Cloudflare Pages without touching the current GitHub Pages production deployment.

Local Wrangler is available through npm. This machine is not authenticated unless `wrangler login` has been run or `CLOUDFLARE_API_TOKEN` is set:

```sh
PATH=/home/peipeipe/.local/nodejs/current/bin:$PATH npx wrangler whoami
```

After logging in, create a Pages preview deployment:

```sh
cd astro
PATH=/home/peipeipe/.local/nodejs/current/bin:$PATH npx wrangler login
PATH=/home/peipeipe/.local/nodejs/current/bin:$PATH npm run pages:create
PATH=/home/peipeipe/.local/nodejs/current/bin:$PATH npm run pages:deploy
```

This deploys `dist/` to the `peipeipe-net-astro` Pages project and should produce a `*.pages.dev` URL. The preview-only check page is:

```text
/cloudflare-preview/
```

Recommended Cloudflare Pages Git integration settings:

```text
Root directory: astro
Build command: npm ci && npm run build
Build output directory: dist
NODE_VERSION: 22.22.3
```

Keep the production custom domain on GitHub Pages until URL and visual checks pass. After cutover, move the custom domain in Cloudflare Pages and remove or disable the GitHub Pages deploy workflow.

### GitHub Actions Preview

The workflow `.github/workflows/cloudflare-pages-astro-preview.yml` deploys the Astro prototype to Cloudflare Pages on pushes to `astro-migration` and via manual `workflow_dispatch`.

Required GitHub repository secrets:

```text
CLOUDFLARE_API_TOKEN
CLOUDFLARE_ACCOUNT_ID
```

The token needs permission to manage Cloudflare Pages for the account. The deployment target is:

```text
Project: peipeipe-net-astro
Preview URL: https://peipeipe-net-astro.pages.dev/
Check page: https://peipeipe-net-astro.pages.dev/cloudflare-preview/
```

To trigger a new preview deployment:

```sh
git push origin astro-migration
```

or run the workflow manually from GitHub Actions.

## Known URL Issue

The previous incomplete percent-encoded Japanese slug issue is resolved after merging `master`.

Current count:

```text
legacy invalid percent slugs: 0
```

The old Japanese/percent-encoded filenames were normalized to English slugs on `master`, and the old post frontmatter now has dated permalinks to preserve the intended public URLs.

## Next Work

1. Compare current Jekyll output with Astro output.
   - Generate or capture a Jekyll URL manifest from the production site or from CI.
   - Compare it with `migration/astro-url-manifest.json`.

2. Improve visual parity for the blog and diary pages.
   - Check image layout on representative long posts.

3. Migrate static root pages and special pages.
   - `404`: done
   - `robots.txt`: done
   - `CNAME` handling is not needed for preview, but matters during final cutover.

4. Migrate data/map pages.
   - `/activity/`: done, using a wide map-focused Astro layout
   - `/mountains/`: done, using the visited mountain JSON and a Leaflet marker map
   - `/places/`: done, using the check-in JSON, category filters, search, and a Leaflet marker map
   - `/onsen/`: done, using the onsen check-in JSON, search, photos, and a Leaflet marker map

5. Verify existing automation remains compatible after preview deploys.
   - `update-strava-activities.yml`
   - `update-onsen-checkins.yml`
   - `webhook-diary.yml`
   - `enhance-amazon-links.yml`
   - `convert-images-to-webp.yml`

6. Add production cutover checklist.
   - Tag the last Jekyll production state.
   - Confirm Cloudflare Pages custom domain setup.
   - Disable or replace the GitHub Pages deploy workflow only after preview checks pass.
   - Verify `https://www.peipeipe.net`, RSS, sitemap, canonical URLs, and key old post URLs.

## Rollback

Until the production deploy workflow and custom domain are changed, rollback is simply deleting or ignoring this `astro/` directory and Cloudflare preview project. The production Jekyll site is not affected.

Before any production cutover, create a tag from the last Jekyll deployment commit:

```sh
git tag before-astro-migration
git push origin before-astro-migration
```
