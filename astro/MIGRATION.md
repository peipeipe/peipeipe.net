# Astro Migration

This directory contains the Astro implementation used for the Cloudflare Pages migration. The legacy Jekyll source remains at the repository root for rollback/reference.

## Current Status

- Branch: `astro-migration`
- Cloudflare Pages project: `peipeipe-net-astro`
- Preview URL: `https://peipeipe-net-astro.pages.dev/`
- Preview check page: `https://peipeipe-net-astro.pages.dev/cloudflare-preview/`
- Latest successful GitHub Actions run before the master merge: `26958949223`
- Latest pushed migration commit: `94474c5 Migrate map data pages to Astro`
- Production cutover is in progress. Repository automation now deploys Astro to Cloudflare Pages from `master`; the legacy Jekyll workflow is manual-only for rollback.

The Cloudflare Pages deploy is working. The first deploy attempt failed because root `.gitignore` ignored `astro/package.json`; that was fixed by explicitly tracking the Astro package manifest.

`master` has now been merged into `astro-migration` locally at merge commit `039eb7d`, bringing in:

- latest Foursquare/Strava data updates from `origin/master`
- diary entry `_diary/2026-06-12.md`
- the earlier old-slug normalization and dated permalink updates

Last verified locally on 2026-06-13:

```text
Astro build: success
Generated pages: 408
URL manifest: 417 URLs
Legacy invalid percent slugs: 0
Cloudflare preview HTTP status: 200 for /diary-post/, /.well-known/nostr.json, and /images/2024-03-31-mother3/0.webp
Jekyll build: not run locally; ruby/bundle are unavailable in this container
URL comparison: blocked until migration/jekyll-url-manifest.json is generated from a Jekyll _site build
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
- Builds the blog index, post detail pages, diary index, diary detail pages, diary posting page, `about`, `search`, RSS, and sitemap.
- Builds `404.html` and `robots.txt`.
- Builds `/activity/`, `/mountains/`, `/places/`, and `/onsen/` as wide map-focused data pages.
- Builds `/activity-data.json`, `/mountains-data.json`, `/places-data.json`, `/places.json`, and `/onsen-data.json`.
- Copies root static assets from `../images/`, `../.well-known/`, and `../favicon.ico` into the Astro `dist/` output during `npm run build`.
- Publishes `/.well-known/nostr.json` through a Cloudflare Pages `_redirects` rewrite to avoid direct-upload hidden directory handling.
- Builds a Cloudflare deployment check page at `/cloudflare-preview/`.
- Deploys the Astro site to Cloudflare Pages via `.github/workflows/cloudflare-pages-astro-preview.yml`.
- Keeps the legacy Jekyll GitHub Pages deploy available only through manual `workflow_dispatch` rollback.

Current content counts from `migration/astro-url-manifest.json`:

```text
posts: 356
diary entries: 41
tracked URLs: 417
```

## Verification

```sh
PATH=/home/peipeipe/.local/nodejs/current/bin:$PATH npm run build
PATH=/home/peipeipe/.local/nodejs/current/bin:$PATH npm run manifest
bundle exec jekyll build
PATH=/home/peipeipe/.local/nodejs/current/bin:$PATH npm run manifest:jekyll
PATH=/home/peipeipe/.local/nodejs/current/bin:$PATH npm run compare:urls
PATH=/home/peipeipe/.local/nodejs/current/bin:$PATH npm run check:legacy-slugs
```

Generated verification files:

- `migration/astro-url-manifest.json`
- `migration/jekyll-url-manifest.json`
- `migration/url-comparison.json`
- `migration/legacy-invalid-percent-slugs.json`

Local note: this container currently has the Astro Node runtime available, but no local `ruby`/`bundle` command. Jekyll comparison commands need a Ruby environment or a captured `_site` directory from CI/production. If `npm run compare:urls` is run before `migration/jekyll-url-manifest.json` exists, it exits with a concise instruction to run `npm run manifest:jekyll` first.

## Cloudflare Pages Preview

This site is published to Cloudflare Pages. Production traffic should be moved by attaching the custom domain to the Cloudflare Pages project.

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

This deploys `dist/` to the `peipeipe-net-astro` Pages project and should produce a `*.pages.dev` URL. The Cloudflare check page is:

```text
/cloudflare-preview/
```

Recommended Cloudflare Pages Git integration settings, if switching away from the GitHub Actions/Wrangler deploy:

```text
Root directory: astro
Build command: npm ci && npm run build
Build output directory: dist
NODE_VERSION: 22.22.3
```

Move the production custom domain to Cloudflare Pages after URL and visual checks pass. The GitHub Pages/Jekyll workflow has been disabled for automatic pushes and is retained as a manual rollback path.

### GitHub Actions Deployment

The workflow `.github/workflows/cloudflare-pages-astro-preview.yml` deploys the Astro site to Cloudflare Pages on pushes to `astro-migration`, pushes to `master`, and via manual `workflow_dispatch`.

It builds Astro, copies root static assets into `dist/`, verifies key generated files, runs the Astro URL manifest and legacy slug checks, and then deploys `dist/` with Wrangler.

Branch behavior:

- `astro-migration`: preview deployment for migration testing.
- `master`: production deployment after Cloudflare Pages production branch/custom domain cutover.

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

Ordinary blog/content updates on `master` trigger this workflow when they touch:

- `astro/**`
- `_posts/**`
- `_diary/**`
- `_data/**`
- `images/**`
- `.well-known/**`
- `favicon.ico`
- `places.json`

## Known URL Issue

The previous incomplete percent-encoded Japanese slug issue is resolved after merging `master`.

Current count:

```text
legacy invalid percent slugs: 0
```

The old Japanese/percent-encoded filenames were normalized to English slugs on `master`, and the old post frontmatter now has dated permalinks to preserve the intended public URLs.

## Next Work

1. Compare current Jekyll output with Astro output.
   - Jekyll `_site` URL manifest generation is scripted with `npm run manifest:jekyll`.
   - Compare it with `migration/astro-url-manifest.json` using `npm run compare:urls`.
   - Review `migration/url-comparison.json` and migrate or intentionally ignore any differences.
   - Current local blocker: Ruby/Bundler are not installed here, and `_site` is absent. Generate `_site` in a Ruby environment or obtain the production/CI `_site` artifact, then run `npm run manifest:jekyll` and `npm run compare:urls`.

2. Improve visual parity for the blog and diary pages.
   - Check image layout on representative long posts.

3. Migrate static root pages and special pages.
   - `404`: done
   - `/diary-post/`: done
   - `robots.txt`: done
   - `CNAME` is not copied into Astro output because Cloudflare Pages custom domains are managed in Cloudflare.

4. Migrate data/map pages.
   - `/activity/`: done, using a wide map-focused Astro layout
   - `/mountains/`: done, using the visited mountain JSON and a Leaflet marker map
   - `/places/`: done, using the check-in JSON, category filters, search, and a Leaflet marker map
   - `/onsen/`: done, using the onsen check-in JSON, search, photos, and a Leaflet marker map

5. Verify existing automation remains compatible after preview deploys.
   - Reviewed on 2026-06-07: these workflows update source files that Astro reads directly.
   - `update-strava-activities.yml`: updates `_data/strava_activities.json` and `_data/visited_mountains.json`; Cloudflare preview path filters include `_data/**`.
   - `update-onsen-checkins.yml`: updates `_data/onsen_places.json`, `_data/places.json`, and root `places.json`; Astro reads these data files for map/data routes.
   - `webhook-diary.yml`: updates `_diary/` and `images/`; Cloudflare preview path filters include both.
   - `enhance-amazon-links.yml`: updates `_posts/**/*.md`; Cloudflare preview path filters include `_posts/**`.
   - `convert-images-to-webp.yml`: updates `images/` and Markdown references; Astro serves root `images/` assets and reads posts from `_posts/`.
   - The Astro deploy workflow now also watches `master`, `places.json`, `.well-known/**`, and `favicon.ico` for cutover readiness.

6. Finish production cutover.
   - Before cutover:
     - Tag the last Jekyll production state.
     - Run Astro verification and preview checks.
     - Confirm Cloudflare Pages custom domain setup for `www.peipeipe.net` and apex handling if needed.
     - Decide whether to keep deploying from GitHub Actions/Wrangler or switch to Cloudflare Pages Git integration.
   - Cutover:
     - Point the production custom domain from GitHub Pages to Cloudflare Pages.
     - Confirm `.github/workflows/jekyll.yml` remains manual-only.
     - Confirm `master` blog updates deploy Astro production instead of Jekyll.
   - After cutover:
     - Verify `https://www.peipeipe.net`, RSS, sitemap, canonical URLs, key old post URLs, `/diary-post/`, `/images/...`, and `/.well-known/nostr.json`.
     - Confirm scheduled/data workflows still trigger a production Astro deploy after committing content/data updates.

## Rollback

After cutover, rollback is to run the manual `Legacy Jekyll deploy` workflow and move the custom domain back to GitHub Pages.

Before any production cutover, create a tag from the last Jekyll deployment commit:

```sh
git tag before-astro-migration
git push origin before-astro-migration
```
