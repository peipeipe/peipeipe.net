# Repository Guidelines

## Project Structure & Module Organization

This repository is an Astro site deployed from `astro/` to Cloudflare Pages. Blog posts live in `_posts/`, diary entries in `_diary/`, data files in `_data/` plus root `places.json`, and static assets under `images/`, `.well-known/`, and `favicon.ico`. Astro reads those root content/data/assets directly while page templates, styles, and build scripts live under `astro/`.

Automation and data refresh scripts live in `scripts/`. GitHub Actions workflows are in `.github/workflows/`. See `astro/MIGRATION.md` for migration history and deployment notes.

## Build, Test, and Development Commands

- `./test_local.sh`: exercise the diary webhook flow locally; it may prompt for a Discord webhook.
- `cd astro && PATH=/home/peipeipe/.local/nodejs/current/bin:$PATH npm ci`: install Astro dependencies with the required Node version.
- `cd astro && PATH=/home/peipeipe/.local/nodejs/current/bin:$PATH npm run build`: build the production Astro site.
- `cd astro && PATH=/home/peipeipe/.local/nodejs/current/bin:$PATH npm run manifest && PATH=/home/peipeipe/.local/nodejs/current/bin:$PATH npm run check:legacy-slugs`: verify Astro URL coverage and legacy slug handling.

## Coding Style & Naming Conventions

Use two-space indentation for Astro, HTML, YAML, JavaScript, and TypeScript. Keep Markdown frontmatter explicit: `title`, `date`, `permalink` when needed, and relevant categories. Existing `layout` fields in old Markdown content are legacy metadata and should not drive new code. Post filenames follow `YYYY-MM-DD-title.md`; diary filenames follow `YYYY-MM-DD.md`. Prefer existing Astro layouts, CSS variables, and script patterns over new abstractions.

## Testing Guidelines

There is no single full test suite. Validate site changes with `npm run build`, `npm run manifest`, and `npm run check:legacy-slugs` from `astro/` using the required Node path. For Python automation, run the specific script or focused helper test, for example `python scripts/test_amazon_enhancement.py`.

## Commit & Pull Request Guidelines

Commit history uses short imperative summaries such as `Fix duplicated Amazon link cards` and `Normalize old post slugs`. Keep commits focused and avoid mixing generated content with unrelated code changes. PRs should describe the affected site area, list verification commands run, note any URL or feed impact, and include screenshots for visual changes.

## Security & Configuration Tips

Do not commit credentials, webhook URLs, Cloudflare tokens, Strava secrets, or local virtual environments. Production deploys go through Cloudflare Pages; GitHub Pages/Jekyll rollback state is historical and should not be reintroduced without an explicit rollback plan.
