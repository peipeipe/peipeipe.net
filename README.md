# peipeipe.net

Astro site for `https://www.peipeipe.net/`, deployed to Cloudflare Pages.

The Astro app lives in `astro/` and reads root content/data/assets directly:

- `_posts/`: blog posts
- `_diary/`: diary entries
- `_data/` and `places.json`: map/check-in/activity data
- `images/`, `.well-known/`, `favicon.ico`: static assets copied into `astro/dist/`

Build and verify:

```sh
cd astro
PATH=/home/peipeipe/.local/nodejs/current/bin:$PATH npm ci
PATH=/home/peipeipe/.local/nodejs/current/bin:$PATH npm run build
PATH=/home/peipeipe/.local/nodejs/current/bin:$PATH npm run manifest
PATH=/home/peipeipe/.local/nodejs/current/bin:$PATH npm run check:legacy-slugs
```
