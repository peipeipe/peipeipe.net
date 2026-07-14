# Repository Guidelines

## Project Structure & Module Organization

This repository is an Astro site deployed from `astro/` to Cloudflare Pages. Blog posts live in `astro/content/posts/`, diary entries in `astro/content/diary/`, drafts in `astro/content/drafts/`, data files in `astro/data/`, and static assets under `astro/public/`. Page templates, styles, and build scripts also live under `astro/`.

Automation and data refresh scripts live in `scripts/`. GitHub Actions workflows are in `.github/workflows/`. See `astro/MIGRATION.md` for migration history and deployment notes.

## Build, Test, and Development Commands

- `cd astro && PATH=/home/peipeipe/.local/nodejs/current/bin:$PATH npm ci`: install Astro dependencies with the required Node version.
- `cd astro && PATH=/home/peipeipe/.local/nodejs/current/bin:$PATH npm run build`: build the production Astro site.
- `cd astro && PATH=/home/peipeipe/.local/nodejs/current/bin:$PATH npm run check:legacy-slugs`: verify legacy slug handling.

## Coding Style & Naming Conventions

Use two-space indentation for Astro, HTML, YAML, JavaScript, and TypeScript. Keep Markdown frontmatter explicit: `title`, `date`, `permalink` when needed, and relevant categories. Existing `layout` fields in old Markdown content are legacy metadata and should not drive new code. Post filenames follow `YYYY-MM-DD-title.md`; diary filenames follow `YYYY-MM-DD.md`. Prefer existing Astro layouts, CSS variables, and script patterns over new abstractions.

## Testing Guidelines

There is no single full test suite. Validate site changes with `npm run build` and `npm run check:legacy-slugs` from `astro/` using the required Node path. For Python automation, run the specific script or focused helper test, for example `python scripts/test_amazon_enhancement.py`.

## Commit & Pull Request Guidelines

Commit history uses short imperative summaries such as `Fix duplicated Amazon link cards` and `Normalize old post slugs`. Keep commits focused and avoid mixing generated content with unrelated code changes. PRs should describe the affected site area, list verification commands run, note any URL or feed impact, and include screenshots for visual changes.

## Security & Configuration Tips

Do not commit credentials, webhook URLs, Cloudflare tokens, Strava secrets, or local virtual environments. Production deploys go through Cloudflare Pages; GitHub Pages/Jekyll rollback state is historical and should not be reintroduced without an explicit rollback plan.
