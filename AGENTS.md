# Repository Guidelines

## Project Structure & Module Organization

This repository is primarily a Jekyll site. Blog posts live in `_posts/`, diary entries in `_diary/`, layouts in `_layouts/`, includes in `_includes/`, and shared styles in `_sass/` plus `style.scss`. Static assets are under `images/`; data files such as map/check-in sources are in `_data/`, `places.json`, and related root HTML pages (`activity.html`, `mountains.html`, `onsen.html`, `places.html`).

Automation and data refresh scripts live in `scripts/`. GitHub Actions workflows are in `.github/workflows/`. The `astro/` directory is a side-by-side Astro migration prototype; see `astro/MIGRATION.md` before changing it.

## Build, Test, and Development Commands

- `bundle install`: install Ruby/Jekyll dependencies.
- `bundle exec jekyll serve`: run the current Jekyll site locally.
- `bundle exec jekyll build`: build the production Jekyll output.
- `./test_local.sh`: exercise the diary webhook flow locally; it may prompt for a Discord webhook.
- `cd astro && PATH=/home/peipeipe/.local/nodejs/current/bin:$PATH npm run build`: build the Astro prototype with the required Node version.
- `cd astro && npm run manifest && npm run check:legacy-slugs`: verify Astro URL coverage and legacy slug handling.

## Coding Style & Naming Conventions

Use two-space indentation for HTML, Liquid, YAML, JavaScript, and TypeScript. Keep Markdown frontmatter explicit: `layout`, `title`, `date`, `permalink` when needed, and relevant categories. Post filenames follow `YYYY-MM-DD-title.md`; diary filenames follow `YYYY-MM-DD.md`. Prefer existing Liquid includes, Sass variables, and script patterns over new abstractions.

## Testing Guidelines

There is no single full test suite. Validate Jekyll changes with `bundle exec jekyll build`. Validate Astro migration changes with `npm run build`, `npm run manifest`, and `npm run check:legacy-slugs` from `astro/`. For Python automation, run the specific script or focused helper test, for example `python scripts/test_amazon_enhancement.py`.

## Commit & Pull Request Guidelines

Commit history uses short imperative summaries such as `Fix duplicated Amazon link cards` and `Normalize old post slugs`. Keep commits focused and avoid mixing generated content with unrelated code changes. PRs should describe the affected site area, list verification commands run, note any URL or feed impact, and include screenshots for visual changes.

## Security & Configuration Tips

Do not commit credentials, webhook URLs, Cloudflare tokens, Strava secrets, or local virtual environments. Keep production GitHub Pages/Jekyll deployment separate from the Astro Cloudflare Pages preview until migration checks pass.
