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

**Amazon book cards are written into the Markdown, not rendered at build time.** Pushing a post triggers `.github/workflows/enhance-amazon-links.yml`, which runs `scripts/enhance_amazon_links.py` and rewrites both `[商品名](amazon_url)` markdown links and standalone Amazon URLs into the full `krb-amzlt-box` HTML, then commits and re-triggers the deploy. It resolves `amzn.to` / `amzn.asia` / `a.co` short URLs over the network to get the ASIN (the cover image URL is built from it), and for a bare URL — which carries no link text — it takes the title from `astro/data/books.json` by ASIN, falling back to the product page's own title. The `renderAmazonLinkCard` path in `content.ts` is only a fallback for posts that workflow has not rewritten yet: it reads the ASIN straight out of the URL path and follows no redirects, so a short URL renders there as a card with **no cover image**. That is what a missing book cover almost always means — the workflow did not run, not that Amazon changed something.

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

### Onsen composition data

`astro/data/onsen_composition.json` holds hot spring analysis sheets (温泉分析書 / 温泉成分等掲示表) transcribed from the Foursquare check-in photos in `astro/data/onsen_places.json`. The pipeline is three stages, and only the middle one — reading the images — has two interchangeable implementations:

```sh
python3 scripts/prepare_onsen_composition.py       # 未解析写真を original 解像度で取得＋選別用シート生成
python3 scripts/extract_onsen_composition.py       # Gemini に読ませて extracted.json を書く（要 GEMINI_API_KEY）
#   または: Claude Code のセッションで画像を読んで extracted.json を手書きする（/onsen-composition）
python3 scripts/merge_onsen_composition.py         # astro/data/onsen_composition.json に反映
python3 scripts/validate_onsen_composition.py      # 合計と泉質の整合を検算
```

`.github/workflows/update-onsen-composition.yml` runs the automated path on a schedule and opens a **pull request** rather than pushing — the transcription can be wrong, so a human confirms. Two things make a daily unattended run safe. It bails out early if a previous `onsen-composition/*` pull request is still open, because until that merges the committed data still lists those photos as unanalyzed and the run would rebuild the same PR every day. And failures are split into two kinds, because the two wrong answers are not equally bad. Anything at the HTTP level — including the 400 `API_KEY_INVALID` that an expired key returns — aborts the whole run without writing anything, so the workflow fails loudly and no state moves. Only failures in a 200 response (safety block, unparseable JSON, truncation) are attributed to the photo: those come back as `failed_photos`, and `merge_onsen_composition.py` records them under `unreadable_photos` with an attempt counter instead of filing them as `not_composition_photos`. After `MAX_READ_ATTEMPTS` (3) tries `prepare_onsen_composition.py` stops offering that photo, so a corrupt image is not retried forever; `--all` picks them back up. Erring toward "abort" is deliberate — retiring a readable sheet loses it permanently, while aborting too often just fails a workflow run. The Claude-in-the-loop path (`.claude/commands/onsen-composition.md`, run `/onsen-composition`) is still the tool for anything the automated one flags: it can crop and magnify a glared corner and reason about what a sheet *must* say, which a single API call cannot.

**The second source: what the web publishes.** Most visited facilities never got a readable analysis sheet into a check-in photo — the posting was outside the frame, or was never photographed. For those, `scripts/merge_onsen_composition_web.py` takes values transcribed from the facility's own site, the municipality's page, or a hot spring directory, and merges them into the same file by `fsq_id`:

```sh
python3 scripts/merge_onsen_composition_web.py --dry-run   # 入力は .cache/onsen_web/web_entries.json
python3 scripts/merge_onsen_composition_web.py
```

Input entries carry `name_match` (a name in `onsen_places.json`) or `fsq_id`; name/address/checkin_date are filled in from `onsen_places.json`. Because the merge is per field, adding web values to a facility that was already read from a photo does not erase the photo-derived numbers. It deliberately does not touch `not_composition_photos` / `unreadable_photos` — those are the photo pipeline's state, and a web entry says nothing about whether a photo was readable.

`confidence` carries the difference in provenance, since none of it was verified against the posting on site: `high` only for an analysis sheet the facility itself publishes (PDF or image) and that was read in full; `medium` for figures written in prose on an official or municipal page; `low` for directory sites and blogs. The source URL goes in `notes` every time. Two habits matter: when sources disagree on a value (pH 8.3 vs 8.5), leave the field out and say so in `notes` rather than picking one, and never infer a 泉質 classification word (低張性/高温泉 etc.) that the source did not print — the validator treats those words as claims to check, so a guessed one turns into a fake failure or, worse, a fake pass.

**Why validation matters more than it looks.** Analysis sheets are massively redundant — every ion total is also the sum of its rows, 溶存物質 = 陽イオン計 + 陰イオン計 + 非解離成分計, and 成分総計 = 溶存物質 + 溶存ガス成分計. `validate_onsen_composition.py` exploits that: a misread digit breaks the arithmetic and gets caught. It also checks the 泉質 name against the composition itself (硫黄泉 needs 総硫黄 ≥ 2mg/kg, 単純温泉 needs 溶存物質 < 1000mg/kg, and 低張性/中性/高温泉 etc. follow from 溶存物質・pH・泉温 under 鉱泉分析法指針). That second check exists because transcription errors cluster on text fields where glare hides the print, and those are exactly the ones arithmetic cannot catch. Entries failing either check are dropped to `confidence: low` with the reason appended to `notes`.

Rarely the *posting itself* does not add up (a printing error on the sheet). Record those as `validation_exceptions: ["陰イオン計"]` on the entry, with the evidence written into `notes` — the validator then stays quiet about that one label. Never use it to silence a suspected misreading.

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
