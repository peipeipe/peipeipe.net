# Astro Migration

This directory is a side-by-side Astro prototype. The current Jekyll site remains intact at the repository root.

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
- Keeps the current Jekyll site deploy workflow untouched.

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

This prototype can be published to Cloudflare Pages without touching the current GitHub Pages production deployment.

Local Wrangler is available through npm, but this machine is not authenticated yet:

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

## Known URL Issue

Some older post filenames contain incomplete percent-encoded Japanese slugs. Astro cannot emit invalid percent escapes, so those URLs are escaped to safe `%25...` paths for now.

Before production cutover, compare these with the current Jekyll output and decide whether to:

- add redirects from the legacy malformed paths;
- preserve them via a custom post-build copy step;
- or accept the normalized safe URL for those old entries.

## Rollback

Until the deploy workflow is changed, rollback is simply deleting or ignoring this `astro/` directory. The production Jekyll site is not affected.

Before any production cutover, create a tag from the last Jekyll deployment commit:

```sh
git tag before-astro-migration
git push origin before-astro-migration
```
