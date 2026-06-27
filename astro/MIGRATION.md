# Astro Migration

This directory contains the Astro implementation used for the Cloudflare Pages migration. The production site is now Astro on Cloudflare Pages; legacy Jekyll runtime files were removed after cutover.

## Current Status

- Branch: `master`
- Cloudflare Pages project: `peipeipe-net-astro`
- Production URL: `https://www.peipeipe.net/`
- Cloudflare Pages URL: `https://peipeipe-net-astro.pages.dev/`
- Cloudflare check page: `https://www.peipeipe.net/cloudflare-preview/`
- Latest successful GitHub Actions run after cutover: `27457888707`
- Latest pushed cutover commit: `4a9eff7 Set Cloudflare Pages production branch`
- Production cutover is complete. Repository automation deploys Astro to Cloudflare Pages from `master`.
- GitHub Pages branch-based legacy build was switched to `build_type: workflow` on 2026-06-13 to stop automatic Jekyll builds from parsing `astro/**/*.astro`.
- Jekyll cleanup is complete as of 2026-06-13: legacy layouts/includes/Sass/config/root pages/Gemfiles/CNAME, `.nojekyll`, `.jekyll-cache`, and the manual Jekyll rollback workflow were removed.
- Repository structure is now Astro-centered: content, data, and public assets live under `astro/`.

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
Jekyll build: removed from normal verification after cleanup
```

Recent UI/content work during migration:

- Ported the legacy masthead, footer links, RSS link, avatar, and metadata into Astro.
- Tightened blog and diary page spacing and typography to match the current site more closely.
- Changed list excerpts to show only the first sentence instead of a long multi-sentence snippet.
- Normalized Markdown image URLs with spaces so posts render correctly in Astro.
- Migrated the wide data/map pages for activity, mountains, and places into Astro layouts.

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

- Reads blog posts from `content/posts/*.md`.
- Reads diary entries from `content/diary/*.md`.
- Keeps drafts in `content/drafts/*.md`.
- Builds the blog index, post detail pages, diary index, diary detail pages, diary posting page, `about`, `search`, RSS, and sitemap.
- Builds `404.html` and `robots.txt`.
- Builds `/activity/`, `/mountains/`, and `/places/` as wide map-focused data pages.
- Builds `/activity-data.json`, `/mountains-data.json`, `/places-data.json`, and `/places.json`.
- Serves static assets from `public/`.
- Publishes `/.well-known/nostr.json` through a Cloudflare Pages `_redirects` rewrite to avoid direct-upload hidden directory handling.
- Builds a Cloudflare deployment check page at `/cloudflare-preview/`.
- Deploys the Astro site to Cloudflare Pages via `.github/workflows/cloudflare-pages.yml`.

Current content counts from `migration/astro-url-manifest.json`:

```text
posts: 356
diary entries: 42
tracked URLs: 416
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

Local note: this container currently has the Astro Node runtime available. Ruby/Jekyll is no longer part of normal local verification.

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

The old GitHub Pages legacy branch build is disabled by setting the repository Pages `build_type` to `workflow`. The local Jekyll workflow file has been removed; rollback should use the `before-astro-migration` tag if needed.

### GitHub Actions Deployment

The workflow `.github/workflows/cloudflare-pages.yml` deploys the Astro site to Cloudflare Pages on pushes to `master` and via manual `workflow_dispatch`.

It builds Astro, verifies key generated files, runs the Astro URL manifest and legacy slug checks, sets the Cloudflare Pages production branch to `master`, and then deploys `dist/` with Wrangler.

Branch behavior:

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

To trigger a deploy without a commit, run the workflow manually from GitHub Actions.

Ordinary blog/content updates on `master` trigger this workflow when they touch:

- `astro/**`
- `astro/content/**`
- `astro/data/**`
- `astro/public/**`

## Known URL Issue

The previous incomplete percent-encoded Japanese slug issue is resolved after merging `master`.

Current count:

```text
legacy invalid percent slugs: 0
```

The old Japanese/percent-encoded filenames were normalized to English slugs on `master`, and the old post frontmatter now has dated permalinks to preserve the intended public URLs.

## Next Work

1. After pushing this cleanup commit, verify the production deploy.
   - Confirm `.github/workflows/cloudflare-pages.yml` runs on `master` and deploys successfully.
   - Confirm the old `pages-build-deployment` workflow does not start a new legacy Jekyll build.
   - Check these production URLs after the deploy finishes:
     - `https://www.peipeipe.net/`
     - `https://www.peipeipe.net/feed.xml`
     - `https://www.peipeipe.net/sitemap-index.xml`
     - `https://www.peipeipe.net/.well-known/nostr.json`
     - `https://www.peipeipe.net/diary/2026-06-12/`
     - `https://www.peipeipe.net/cloudflare-preview/`
     - one representative image URL under `/images/`

2. Confirm content/data automation still chains into an Astro production deploy.
   - `update-strava-activities.yml`: updates `astro/data/strava_activities.json` and `astro/data/visited_mountains.json`.
   - `update-onsen-checkins.yml`: updates `astro/data/onsen_places.json` and `astro/data/places.json`.
   - `enhance-amazon-links.yml`: updates `astro/content/posts/**/*.md`.
   - `convert-images-to-webp.yml`: updates `astro/public/images/` and Markdown references.
   - If any workflow commits successfully but does not trigger `.github/workflows/cloudflare-pages.yml`, adjust the deploy workflow path filters.

3. Decide whether to fully disable GitHub Pages in repository settings.
   - Current state is `build_type: workflow`, which stops branch-based Jekyll builds.
   - If Cloudflare remains the only production host, consider disabling Pages entirely in repository settings after confirming no rollback path depends on it.

4. Clean up stale migration tooling after one stable deploy.
   - Review whether `astro/migration/astro-url-manifest.json` and `astro/migration/legacy-invalid-percent-slugs.json` should stay committed or become generated-only artifacts.
   - Keep `npm run manifest` and `npm run check:legacy-slugs` while old URL coverage is still useful.

5. Optional visual/content parity pass.
   - Check image layout on representative long posts.
   - Check `about`, `search`, `diary-post`, and the four map pages on mobile after the cleanup deploy.

## Completed Cleanup

1. Jekyll cleanup status.
   - Done on 2026-06-13:
     - GitHub Pages build type changed from legacy branch build to workflow build.
     - `.github/workflows/cloudflare-pages-astro-preview.yml` renamed to `.github/workflows/cloudflare-pages.yml`.
     - `.github/workflows/jekyll.yml` removed.
     - Jekyll `_layouts/`, `_includes/`, `_sass`, `style.scss`, `_config.yml`, `_config_diary.yml`, `Gemfile`, `Gemfile.lock`, `CNAME`, root Jekyll pages, `.nojekyll`, and stale `.jekyll-cache` removed.
     - `about` and `search` content moved into Astro pages before deleting the root Markdown files.
     - Content moved to `astro/content/posts/`, `astro/content/diary/`, and `astro/content/drafts/`.
     - Data moved to `astro/data/`.
     - Public assets moved to `astro/public/`.
     - Automation scripts and GitHub Actions workflows were updated for the Astro-centered paths.

## Rollback

After Jekyll cleanup, rollback is a repository rollback/redeploy from the pre-cutover tag plus moving custom domain/DNS back to GitHub Pages. The rollback tag is already pushed:

```text
before-astro-migration -> 29ec979 Update Foursquare checkins
```
