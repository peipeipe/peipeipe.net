# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Personal Astro site for `https://www.peipeipe.net/`, deployed to Cloudflare Pages. The app lives entirely under `astro/`; the repo root only holds Python automation scripts, docs, and GitHub Actions workflows. This was migrated from Jekyll/GitHub Pages — see `astro/MIGRATION.md` for cutover history if something looks like a legacy leftover.

## Commands

All Astro commands run from `astro/` and require the pinned Node version (`astro/.node-version`, currently 24.18.0):

```sh
cd astro
PATH=/home/peipeipe/.local/nodejs/current/bin:$PATH npm ci
PATH=/home/peipeipe/.local/nodejs/current/bin:$PATH npm run dev      # local dev server
PATH=/home/peipeipe/.local/nodejs/current/bin:$PATH npm run build    # astro build + finalize-public-assets.mjs
PATH=/home/peipeipe/.local/nodejs/current/bin:$PATH npm run check:legacy-slugs    # verify legacy Jekyll slugs still resolve
```

There is no single test suite. Validate changes with `npm run build` and `npm run check:legacy-slugs` — CI (`.github/workflows/cloudflare-pages.yml`) runs both plus asserts specific files exist in `dist/` before deploying.

For Python automation scripts in `scripts/`, run the specific script directly, or the focused test for Amazon link enhancement:

```sh
python scripts/test_amazon_enhancement.py
```

## Architecture

**Content is not loaded via Astro content collections.** `astro/src/lib/content.ts` reads Markdown directly from `astro/content/posts/` and `astro/content/diary/` at build time using `fast-glob`, a hand-rolled frontmatter parser, and `marked`. Key behaviors baked into that loader:

- Post/diary dates come from the filename (`YYYY-MM-DD-title.md` / `YYYY-MM-DD.md`) unless frontmatter overrides them; URLs are computed in Asia/Tokyo time via `datePartsInTokyo`.
- Standalone URLs on their own line get turned into link cards (fetches OG/Twitter meta tags at build time, 2.5s timeout, cached in-memory) — except Amazon links in posts, which render a legacy "amazlet"-style affiliate card instead, and x.com/twitter.com links, which are left alone.
- `layout` frontmatter fields on old Markdown are legacy Jekyll metadata and must not drive new rendering logic.

Other structured data (`astro/data/*.json` — activities, mountains, onsen, places, books) is generated ahead of time by the Python scripts in `scripts/` and read at build time by the matching `astro/src/lib/*.ts` module (`activity.ts`, `mountains.ts`, `checkins.ts`, `books.ts`, `composition.ts`). These JSON files are checked in and refreshed by scheduled GitHub Actions workflows (`update-strava-activities.yml`, `update-onsen-checkins.yml`, `update-books-from-booklog.yml`), not regenerated on every build.

Pages under `astro/src/pages/*-data.json.ts` expose some of this same data as JSON endpoints for client-side map/list rendering (used by `MapLayout.astro`).

`output: "static"` — the whole site is prerendered; `astro.config.mjs` excludes a few internal paths (`/cloudflare-preview/`, `/diary-post/`, `/places/`, `/search/`) from the sitemap.

### Strava data refresh (manual, from export)

The default Strava update path is the scheduled API workflow, but a manual export-based path exists for bulk backfills:

```sh
python3 scripts/generate_strava_activities_from_export.py /path/to/export_<id>.zip
python3 scripts/generate_visited_mountains.py   # if mountain data also needs updating
```

Never commit the export ZIP — it contains location data. If using the manual `Update Strava Activities From Export` workflow, only point `export_zip_url` at a short-lived URL.

### Onsen composition data (manual, Claude-in-the-loop)

`astro/data/onsen_composition.json` holds hot spring analysis sheets (温泉分析書 / 温泉成分等掲示表) transcribed from the Foursquare check-in photos in `astro/data/onsen_places.json`. There is no OCR service and no API key involved — the reading step happens inside a Claude Code session, driven by `.claude/commands/onsen-composition.md` (run `/onsen-composition`).

```sh
python3 scripts/prepare_onsen_composition.py   # 未解析写真を original 解像度で取得＋選別用シート生成
# → Claude が .cache/onsen_photos/ の画像を読んで extracted.json を書く
python3 scripts/merge_onsen_composition.py     # astro/data/onsen_composition.json に反映
```

Photo URLs are converted from Foursquare's `500x300` variant to `original` before download — the resized version is too small to read. Everything under `.cache/` is gitignored working data; only `astro/data/onsen_composition.json` gets committed. Photos that turn out not to be analysis sheets are recorded in `not_composition_photos` so the next run skips them, which is what makes the batch incremental. Re-visiting a venue and re-reading part of its posting is fine: `merge_onsen_composition.py` merges per field on `fsq_id`, so previously read values survive.

Related: `fetch_foursquare_checkins.py` keeps **every** check-in photo per venue by default. Capping it via `FOURSQUARE_CHECKIN_PHOTOS_PER_PLACE` (1 or more; empty/0 means unlimited) makes newer check-ins push older photos out of `onsen_places.json`, which would silently drop analysis sheets that were never analyzed.

`fetch_foursquare_checkins.py` re-fetches the full check-in history every run, but it **merges into the existing `places.json` / `onsen_places.json` instead of overwriting them**: a venue that no longer comes back from the API (deleted on Foursquare, or pushed past the `limit × MAX_PAGES` history window) stays in the JSON. `checkin_count`/`first_checkin_at` keep their widest values and photos accumulate, so a shrinking API response can't erase history. Foursquare renames venues (and localizes category names) from time to time — that normally just propagates, but to pin a display name add a `name_override` field to the entry in the JSON by hand; the merge preserves it and it wins over the API name.

The data renders inside `/onsen` (`onsen.astro`): a 泉質 badge on each check-in card plus a 温泉成分表 section below the map. `onsen-data.json.ts` also exposes a per-`fsq_id` summary so client-side re-rendering keeps the badges.

### Deploy

Push to `master` triggers `.github/workflows/cloudflare-pages.yml`, which builds Astro, verifies specific output files exist in `dist/`, then deploys via `wrangler pages deploy`. Production branch and project name are fixed to `peipeipe-net-astro`.

## Conventions

- Two-space indentation for Astro/HTML/YAML/JS/TS.
- Post filenames: `YYYY-MM-DD-title.md`; diary filenames: `YYYY-MM-DD.md`.
- Prefer existing Astro layouts (`BaseLayout.astro`, `MapLayout.astro`), CSS variables in `src/styles/global.css`, and existing script patterns over new abstractions.
- Do not commit credentials, webhook URLs, Cloudflare tokens, Strava secrets, or `.venv`.
