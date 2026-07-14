# peipeipe.net

Astro site for `https://www.peipeipe.net/`, deployed to Cloudflare Pages.

The Astro app lives in `astro/` and keeps site inputs inside that project:

- `astro/content/posts/`: blog posts
- `astro/content/diary/`: diary entries
- `astro/content/drafts/`: drafts
- `astro/data/`: map/check-in/activity data
- `astro/public/`: static assets copied by Astro

Build and verify:

```sh
cd astro
PATH=/home/peipeipe/.local/nodejs/current/bin:$PATH npm ci
PATH=/home/peipeipe/.local/nodejs/current/bin:$PATH npm run build
PATH=/home/peipeipe/.local/nodejs/current/bin:$PATH npm run check:legacy-slugs
```

Strava export ZIP からアクティビティデータを再生成する場合は、月次 export をローカルに置いてから使う。

- Windows でダウンロードした場合は `C:\Users\peipe\Downloads\export_<id>.zip`
- WSL からは `/mnt/c/Users/peipe/Downloads/export_<id>.zip` として参照できる
- 生成コマンドは `python3 scripts/generate_strava_activities_from_export.py /mnt/c/Users/peipe/Downloads/export_<id>.zip`
- 山データも更新するなら続けて `python3 scripts/generate_visited_mountains.py`
- ZIP 自体はコミットしない

GitHub Actions でも手動実行用の export 版 workflow を用意してあるが、既定の更新経路は API 版のまま。
ZIP を HTTPS で取得できる場所に置き、`Update Strava Activities From Export` を手動実行して `export_zip_url` に URL を渡す。
位置情報を含むため、公開 URL に置く場合は短時間だけ使える URL にする。
