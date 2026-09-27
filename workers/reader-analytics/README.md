# 読者の閲覧解析

GAとは独立した、Cloudflare Workers + D1の解析です。公開ページをブラウザで表示した際に `/_analytics/collect` へPOSTします。サイト本体は従来どおりPagesで配信され、解析が停止してもページ表示を妨げません。

## 機能と初期設定

- 日本時間の日別PV、閲覧された異なるページ数、IP由来のアクセス元数。
- アクセス元別の閲覧ページ内訳と、国・都道府県・都市の推定。
- 毎朝9時以降の最初のCronで前日のPV、アクセス元数、大量閲覧アクセス元数、人気ページ上位5件をDiscordへ送信。0PVの日も送信。
- 100PVまたは30種類のページに達すると大量閲覧通知。同じアクセス元への通知は1日1回。通常は検知から5分以内に送信開始。
- `PV_MODE=each` なら日次レポートに加え、個々のPVも通知。5分ごとに最大10通を送るため、集中時は遅延します。大量アクセスのサイトでは `daily` を使ってください。
- `/_analytics/` が管理画面。管理トークンを入力して閲覧します。集計APIはトークン必須で、トークンはブラウザに永続保存しません。
- 生IPは保存せず、秘密鍵付きHMACで日ごとに変わるIDへ変換。Cookie、永続的なブラウザID、検索クエリ、URLのfragment、ページタイトル、参照元は保存しません。
- 直近30日を保持。5分ごとに古い集計行・通知行をそれぞれ最大500件削除します。大量のバックログやCron障害時は削除が遅れることがあります。Discord上の送信済みメッセージは自動削除しません。
- 投稿画面、下書き閲覧画面、Cloudflareプレビュー、404のパスを除外。ローカル・pages.devでは送信しません。DNT/GPCを尊重します。

IP由来のアクセス元数は人数ではありません。同じネットワークの読者はまとめられ、IPが変われば別のアクセス元になります。地域は住所を表しません。広告ブロッカー・JS無効・送信失敗・DNT/GPCなどによりGAと数値が異なります。ブラウザの戻る操作でBFCacheから復元した表示は重複計上せず、再読み込みは新しいPVとして数えます。JSを実行するボットを完全には除外できません。

## 本番セットアップ（既存のGitHub Webhook Secretを再利用）

1. CloudflareでWorkers Freeを利用していることを確認し、D1に `peipeipe-reader-analytics` を作成してdatabase IDを控える。
2. GitHub repository secretsに以下を用意する。
   - 既存の `DISCORD_WEBHOOK_URL` をそのまま再利用。
   - 既存の `CLOUDFLARE_ACCOUNT_ID` と `CLOUDFLARE_API_TOKEN`。トークンに対象アカウントのD1編集・Workers Scripts編集、対象ゾーンのWorkers Routes編集と必要な読み取り権限を付与する。Pagesだけの権限では不足する。
   - `READER_ANALYTICS_IP_HASH_SECRET`: パスワードマネージャー等で生成した32文字以上のランダム文字列。
   - `READER_ANALYTICS_ADMIN_TOKEN`: 上記とは別の32文字以上のランダム文字列。管理画面へのログインに使う。
3. この変更をGitHubへ反映後、Actionsの **Deploy reader analytics** を手動実行。database IDと通知モードを指定する。D1マイグレーション、Workerデプロイ、既存Webhookを含むSecretの設定を実施する。
4. `https://www.peipeipe.net/_analytics/` を開き、管理トークンで0PVのレポートを取得できることを確認。
5. GitHub repository **variable** `PUBLIC_READER_ANALYTICS_ENABLED` を `true` にし、通常の **Deploy Astro to Cloudflare Pages** を実行する。これが計測開始のスイッチ。
6. 公開ページを1回開き、管理画面のPV増加を確認。Discordの日次レポートは翌朝9時以降。`each` では個々のPVが通常5分以内に届く。

Webhook URLはコード・コミット・管理画面に含めません。GitHubの既存Secretはローカルに読み出す必要がありません。本番のDiscordへの通知テストは、このセットアップ後に行ってください。

## ローカルCLIで設定する場合

必要ならNodeを指定します。

```sh
export PATH=/home/peipeipe/.local/nodejs/current/bin:$PATH
cd workers/reader-analytics
npm ci
npx wrangler login
npx wrangler d1 create peipeipe-reader-analytics
```

作成結果の `database_id` を `wrangler.jsonc` のD1 bindingに追加してから実行します。

```sh
npx wrangler d1 migrations apply peipeipe-reader-analytics --remote
npm run deploy
npx wrangler secret put IP_HASH_SECRET
npx wrangler secret put ADMIN_TOKEN
npx wrangler secret put DISCORD_WEBHOOK_URL
```

Secretは対話プロンプトに入力します。Webhookは既存のものを使用できます。Workers Routeは `www.peipeipe.net/_analytics/*` のみで、Pages側の配信設定を変更しません。

## 開発と検証

```sh
npm ci
npm test
npm run check
npx wrangler d1 migrations apply peipeipe-reader-analytics --local
npm run dev -- --test-scheduled
```

ローカルでは `.dev.vars` に `IP_HASH_SECRET` と `ADMIN_TOKEN` を設定できます。実際のWebhookを入れるとローカルCronでも通知するため、テストは原則としてモックを使用します。`npm test` はNodeのSQLiteを使って集計・通知の重複防止/再送・認証・地域情報・日付境界・ブラウザ送信を検証します。

Astro検証:

```sh
cd ../../astro
PUBLIC_READER_ANALYTICS_ENABLED=true npm run build
npm run check:legacy-slugs
```

## 運用と制約

- `HEAVY_PV` / `HEAVY_PAGES` を `wrangler.jsonc` で変更し再デプロイすると通知閾値を変えられます。
- 通知はD1 outboxに保存し、Discordの429や一時障害で再送。送信成功済みの通知は通常再送しません。ただし送信成功直後にWorkerが停止すると再送で重複する可能性があります（Discord Webhookに冪等キーがないため）。Cron再実行中は2分のリースで二重送信を抑えます。
- 日次レポートは前日分のみ。1日以上の停止中の日報を自動でさかのぼって送ることはありません。集計は管理画面で確認できます。
- 管理画面の上位アクセス元100件、人気ページ50件、アクセス元詳細500件という表示上限があります。全体PV・アクセス元数・大量閲覧数は全件集計です。
- Origin検証は他サイトからのブラウザ送信を抑えますが、任意HTTPクライアントによる偽のPVを防ぐ認証ではありません。不審なアクセスはCloudflare側で制限してください。
- 無料枠はアカウント共有。Workersは1日10万リクエスト、D1は1日500万行読み取り・10万行書き込み・合計5GB。PVごとの書き込みに加え、5分ごとの検知、管理画面、通知、削除も枠を使います。閲覧データを繰り返し集計するため、無料PV数の保証はできません。D1のRows read/writtenを確認してください。
- 無料枠上限や障害時は計測が欠けることがありますが、静的サイトの配信は解析Workerを経由しません。
- 停止する場合は `PUBLIC_READER_ANALYTICS_ENABLED` を `false` にしてサイトを再ビルド。Cronも停止するならWorkerのCron Triggersを解除してください。

公式資料: [Workers limits](https://developers.cloudflare.com/workers/platform/limits/)、[D1 pricing](https://developers.cloudflare.com/d1/platform/pricing/)、[Cron Triggers](https://developers.cloudflare.com/workers/configuration/cron-triggers/)、[Discord Webhooks](https://docs.discord.com/developers/resources/webhook)。
