# Astro Migration

This directory contains the Astro implementation used for the Cloudflare Pages migration. The legacy Jekyll source remains at the repository root for rollback/reference.

## Current Status

- Branch: `master`
- Cloudflare Pages project: `peipeipe-net-astro`
- Production URL: `https://www.peipeipe.net/`
- Cloudflare Pages URL: `https://peipeipe-net-astro.pages.dev/`
- Cloudflare check page: `https://www.peipeipe.net/cloudflare-preview/`
- Latest successful GitHub Actions run after cutover: `27457888707`
- Latest pushed cutover commit: `4a9eff7 Set Cloudflare Pages production branch`
- Production cutover is complete. Repository automation deploys Astro to Cloudflare Pages from `master`; the legacy Jekyll workflow is manual-only for rollback.

The Cloudflare Pages deploy is working. The first deploy attempt failed because root `.gitignore` ignored `astro/package.json`; that was fixed by explicitly tracking the Astro package manifest.

The migration branch was fast-forwarded into `master`. The final cutover commits on `master` include:

- `1024e46 Prepare Astro production cutover`
- `e7758bc Fix Astro date URLs in CI`
- `4a9eff7 Set Cloudflare Pages production branch`

Last verified on 2026-06-13:

```text
Astro build: success
Generated pages: 408
URL manifest: 417 URLs
Legacy invalid percent slugs: 0
Cloudflare Pages production HTTP status: 200 for /cloudflare-preview/ and /diary/2026-06-12/ on www.peipeipe.net
Cloudflare Pages direct HTTP status: 200 for /.well-known/nostr.json on peipeipe-net-astro.pages.dev
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

## Cloudflare Pages Production

This site is published to Cloudflare Pages and served from the production custom domain.

Current Cloudflare DNS/custom-domain state:

```text
peipeipe.net.      CNAME peipeipe-net-astro.pages.dev.  proxied
www.peipeipe.net.  CNAME peipeipe-net-astro.pages.dev.  proxied
```

The old GitHub Pages apex A records were removed:

```text
185.199.108.153
185.199.109.153
185.199.110.153
185.199.111.153
```

The stale Google Domains zone NS records were also removed from the Cloudflare zone. The authoritative nameservers are:

```text
naomi.ns.cloudflare.com
sterling.ns.cloudflare.com
```

Cloudflare Redirect Rules should keep the apex canonicalized to `www`:

```text
If: Hostname equals peipeipe.net
Then: 301 redirect to concat("https://www.peipeipe.net", http.request.uri.path)
Preserve query string: on
```

Local Wrangler is available through npm. This machine is not authenticated unless `wrangler login` has been run or `CLOUDFLARE_API_TOKEN` is set:

```sh
PATH=/home/peipeipe/.local/nodejs/current/bin:$PATH npx wrangler whoami
```

After logging in, create a manual Pages deployment:

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

Recommended Cloudflare Pages Git integration settings, if switching away from the current GitHub Actions/Wrangler deploy:

```text
Root directory: astro
Build command: npm ci && npm run build
Build output directory: dist
NODE_VERSION: 22.22.3
```

The GitHub Pages/Jekyll workflow has been disabled for automatic pushes and is retained as a manual rollback path.

### GitHub Actions Deployment

The workflow `.github/workflows/cloudflare-pages-astro-preview.yml` deploys the Astro site to Cloudflare Pages on pushes to `astro-migration`, pushes to `master`, and via manual `workflow_dispatch`.

It builds Astro, copies root static assets into `dist/`, verifies key generated files, runs the Astro URL manifest and legacy slug checks, sets the Cloudflare Pages production branch to `master` on master pushes, and then deploys `dist/` with Wrangler.

Branch behavior:

- `astro-migration`: preview deployment for migration testing.
- `master`: production deployment; the workflow updates the Cloudflare Pages production branch to `master` before deploying.

Required GitHub repository secrets:

```text
CLOUDFLARE_API_TOKEN
CLOUDFLARE_ACCOUNT_ID
```

The token needs permission to manage Cloudflare Pages for the account. The deployment target is:

```text
Project: peipeipe-net-astro
Production URL: https://www.peipeipe.net/
Pages URL: https://peipeipe-net-astro.pages.dev/
Check page: https://www.peipeipe.net/cloudflare-preview/
```

To trigger a migration-branch preview deployment:

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

1. Optional: compare current Jekyll output with Astro output.
   - Jekyll `_site` URL manifest generation is scripted with `npm run manifest:jekyll`.
   - Compare it with `migration/astro-url-manifest.json` using `npm run compare:urls`.
   - Review `migration/url-comparison.json` and migrate or intentionally ignore any differences.
   - Current local blocker: Ruby/Bundler are not installed here, and `_site` is absent. Generate `_site` in a Ruby environment or obtain the production/CI `_site` artifact, then run `npm run manifest:jekyll` and `npm run compare:urls`.

2. Optional: improve visual parity for the blog and diary pages.
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

6. Post-cutover monitoring.
   - Re-check DNS after propagation stabilizes:
     - `https://peipeipe.net/` should 301 to `https://www.peipeipe.net/`
     - `https://www.peipeipe.net/` should return 200 from Cloudflare
     - `https://www.peipeipe.net/feed.xml` should return 200
     - `https://www.peipeipe.net/.well-known/nostr.json` should return 200
     - representative `/images/...` URLs should return 200
   - Confirm scheduled/data workflows still trigger a production Astro deploy after committing content/data updates.

7. Plan the Jekyll cleanup.
   - Do not delete Jekyll rollback pieces immediately; keep the manual `Legacy Jekyll deploy` workflow until the Astro production site has been stable for a short period.
   - First create a file-by-file cleanup inventory and classify each item as `delete`, `keep`, or `hold`.
   - Update repository guidance so this repository is described as an Astro site rather than primarily a Jekyll site.
   - Consider renaming `.github/workflows/cloudflare-pages-astro-preview.yml` to a production-oriented name such as `cloudflare-pages.yml`.
   - Delete candidates after rollback risk is acceptable:
     - `_layouts/`
     - `_includes/`
     - `_sass/`
     - `style.scss`
     - `_config.yml`
     - `Gemfile`
     - `Gemfile.lock`
     - Jekyll root pages that are now implemented in Astro, such as `activity.html`, `mountains.html`, `onsen.html`, `places.html`, `search.html`, and old about/static pages.
     - `.github/workflows/jekyll.yml` once GitHub Pages rollback is no longer needed.
   - Keep because Astro and automation still read them directly:
     - `_posts/`
     - `_diary/`
     - `_data/`
     - `images/`
     - `.well-known/`
     - `favicon.ico`
     - `places.json`
     - automation scripts and non-Jekyll GitHub Actions workflows.
   - Defer moving the Astro project from `astro/` to the repository root. That can be a separate cleanup after the Jekyll files are removed and deployment has stayed stable.

## Rollback

After cutover, rollback is to run the manual `Legacy Jekyll deploy` workflow and move the custom domain/DNS back to GitHub Pages. The rollback tag is already pushed:

```text
before-astro-migration -> 29ec979 Update Foursquare checkins
```
