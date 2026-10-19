# iPhoneのスクリーンタイムを送信する

## 構成と公開範囲

ショートカット → `POST https://www.peipeipe.net/api/screentime`
→ Cloudflare Worker `peipeipe-screentime-ingest` → GitHub `peipeipe/peipeipe.net` の `master`
→ `astro/data/screentime/YYYY-MM-DD.json` → 既存のCloudflare Pages workflow
→ `/screentime/` と `/diary-reader/`。

アプリ名・使用時間は公開GitHub履歴とブログに掲載される。
GitHubトークンはWorkerのSecretだけに置き、iPhoneには投稿専用キーを設定する。
キーはURL、本文、コミット、チャット、共有ショートカットに含めない。
旧方式のGitHub通信エラーの原因は未特定。この方式の実機動作も手動送信で確認する。

## iPhoneの設定

**既存ショートカットを複製し、新方式が成功するまでは元のショートカットを残す。**
複製したものでは「記録」までの取得・整形はそのまま使う。
その後にあるGitHub直接送信用のBase64変換・GET・SHA・PUTは複製側から外す。

完成済みの「記録」は次の形の辞書。`apps` は辞書の配列、`minutes` は数値。

```json
{"date":"2026-10-17","device":"iPhone","apps":[{"app":"Chrome","minutes":152.482265720765}]}
```

この例は形式の説明であり、確認用データとして公開しない。
取得期間は前日0時〜翌0時、保存する `date` もその前日（`yyyy-MM-dd`）。
このiPhone 1台のアプリだけを対象にし、Webサイト時間を重ねて足さない。
旅行等でタイムゾーンが変わる場合は取得期間と日付の対応を確認する。
指標は「アプリ合計」で、Apple設定画面の総時間と一致するとは限らない。

1. すでに変数「記録」がある場合は作り直さない。まだ名前を付けていなければ、最終辞書の直後に「変数を設定」を追加し、名前を `記録`、入力を `apps` を追加した後の辞書にする。
2. 「テキスト」を追加する。本文には変数選択から **記録** だけを挿入する。手入力でJSONを組み直さない。外側の辞書全体を送信用JSONテキストにする工程であり、辞書内の `apps` は配列のまま。
3. 「変数を設定」を追加する。名前を `送信本文`、入力を直前の「テキスト」にする。
4. 「URL」を追加し、`https://www.peipeipe.net/api/screentime` と入力する。
5. 「URLの内容を取得」を追加する。URL欄は直前の「URL」、方法は **POST** にする。
6. 詳細を開き、ヘッダを2つ追加する。

   | キー | 値 |
   | --- | --- |
   | Content-Type | application/json |
   | X-Screen-Time-Key | 投稿専用キー |

   GitHubトークンや `Authorization` はここには入れない。
7. 「本文を要求」（表記によっては「要求本文」）を **ファイル** にし、ファイル欄をタップ→「変数を選択」→ **送信本文** を選ぶ。ファイルの選択画面から探す必要はない。「JSON」の単一テキスト項目に辞書全体を入れない。
8. 「変数を設定」を追加する。名前を `送信結果`、入力を直前の「URLの内容」にする。
9. 最初の手動確認では「結果を表示」を追加し、入力に **送信結果** を選ぶ。

成功例: `{"ok":true,"date":"…","result":"created","commit":"…","site":"not_verified"}`。
`result` は初回 `created`、訂正 `updated`、同じ内容の再送 `unchanged`。
いずれも**GitHubへの保存確認**であり、ブログ反映完了ではない。
`unchanged` はコミットを増やさないので、新しいデプロイも起動しない。
`site:not_verified` はAPIがサイトの反映を確認していないことを示す。
Actionsの「Deploy Astro to Cloudflare Pages」が成功してから、対象日のグラフを確認する。

手動確認ができたら「結果を表示」を以下に置き換える。

1. 「辞書の値を取得」を追加し、辞書を **送信結果**、キーを `ok` にする。
2. 「もし」を追加し、直前の「辞書の値」が真（Boolean／数値表示なら `1`）の場合にする。
3. 真の中に「通知を表示」を追加し「スクリーンタイムを保存しました。ブログ反映は処理待ちです」と入力。
4. 「その他の場合」に「通知を表示」を追加し「保存できませんでした。手動で送信結果を確認してください」と入力。

HTTPエラーや通信断では「URLの内容を取得」で止まり、後続通知まで進まない場合がある。その場合は成功扱いにしない。

## 400の内容を確認する

ショートカットで400とだけ表示される場合、URLを一時的に `https://www.peipeipe.net/api/screentime/check` に変えて手動実行する。認証と本文の検証だけを行い、GitHubへは保存しない。`ok: false` の `field` が不正な項目を示す。`ok: true` と `saved: false` なら送信形式は正しい。確認後はURLを `/api/screentime` に戻す。

## エラー

| HTTP | error | 対処 |
| --- | --- | --- |
| 400 | invalid_record | date、device=iPhone、apps配列、数値minutes、重複アプリを確認 |
| 401 | unauthorized | 投稿専用キーを確認 |
| 413 | body_too_large | 本文128 KiB超。不要な項目が混ざっていないか確認 |
| 415 | json_required | Content-Typeを確認 |
| 409 | save_conflict_retry | 少し待って同じ記録を再送 |
| 502 | github_read_failed / github_write_failed | 管理者側でGitHubトークンの期限・Contents権限・ブランチ保護を確認 |
| 502 | upstream_unavailable / github_invalid_response | 保存済みの可能性もある。同じ記録を再送して確認 |
| 503 | not_configured | WorkerのSecrets設定が未完了 |

APIは日付を検証し、固定リポジトリ・固定ブランチの固定ディレクトリへだけ書く。
同日再送は置換であり加算しない。同時更新時は最新SHAで最大3回試行し、最後に成功した書き込みが残る。
複数の異なる訂正を同時送信しない。古い記録を後で再送するとその内容に置き換わる。

## 毎朝の実行

手動で初回保存・同日の再送・ブログ反映を確認してから設定する。

1. ショートカット → オートメーション → 新規 → 時刻。
2. 午前8時、毎日、**すぐに実行** を指定。
3. 「ショートカットを実行」を追加し、確認済みの新ショートカットを選ぶ。
4. 「結果を表示」・Quick Look・確認ダイアログは本番経路から外し、必要なアクセス許可は手動実行時に済ませる。
5. 翌朝、ロック中にも送信できたか、GitHubの日付別ファイルとActions、ブログで確認する。

**ロック中の無操作実行は未確認。** 取得できなかった日は0分にせず欠測とする。
空の `apps` は実測0分なので、取得失敗の代わりに送らない。
7日平均は7日分そろった場合のみ表示する。
後日補完する場合は取得期間と `date` の両方を対象日に変える。

## 管理者: 設定・デプロイ

```sh
cd /home/peipeipe/peipeipe.net/workers/screentime-ingest
export PATH=/home/peipeipe/.local/nodejs/current/bin:$PATH
npm ci
npm test
npm run check
npx wrangler login
npx wrangler secret put GITHUB_TOKEN
npx wrangler secret put INGEST_KEY
npm run deploy
```

Secrets:

- `GITHUB_TOKEN`: GitHub fine-grained PAT。対象は `peipeipe/peipeipe.net`、Contents: Read and write。有効期限を管理する。入力はWranglerの非表示欄で行う。`/user` の成功だけでは書き込み権限の証明にならず、実際の初回保存で確認する。
- `INGEST_KEY`: 推測困難なランダム値（32文字以上）。iPhoneの `X-Screen-Time-Key` と一致させる。GitHubトークンとは別の値。更新時はiPhone側も更新する。

今回の投稿専用キーのローカル保存先は `/home/peipeipe/.config/peipeipe-screentime/ingest-key.txt`（所有者だけ読み書き可能、リポジトリ外）。PCのローカルエディタで開き、iPhoneに安全に転記する。チャットに貼らない。

既存Cloudflare OAuth認証でデプロイ可能。Workerの再デプロイは既存Secretsを維持する。
GitHub Actionsの既存Cloudflare Secretは読み出せず、Worker用GitHubトークンの代用にはならない。
Pagesの既存workflowは `astro/data/**` のpushで起動する。PAT経由のコミットで動かす（Actionsの `GITHUB_TOKEN` では後続workflowの起動が抑制される）。
Worker変更のCIは `.github/workflows/screentime-ingest.yml` でテスト・dry runを行う。Worker本番更新は上記 `npm run deploy`。
表示コードは `master` に反映し、既存Pages workflowで公開する。APIのデプロイと表示コードの公開は別。

ログは一般的なエラーコードだけとし、本文・トークン・アプリ名・上流応答を出力しない。
自動のリクエストログとトレースは無効。128 KiBは実際の受信ストリームでも検査する。
GitHubリクエストは10秒でタイムアウト。失敗時の再送でも同日ファイルが増えない。

```sh
cd /home/peipeipe/peipeipe.net/astro
PATH=/home/peipeipe/.local/nodejs/current/bin:$PATH node --test src/lib/screentime.test.mjs ../workers/screentime-ingest/test.mjs
PATH=/home/peipeipe/.local/nodejs/current/bin:$PATH npm run build
PATH=/home/peipeipe/.local/nodejs/current/bin:$PATH npm run check:legacy-slugs
```

資料: [GitHub Contents API](https://docs.github.com/en/rest/repos/contents#create-or-update-file-contents)、[Cloudflare Secrets](https://developers.cloudflare.com/workers/configuration/secrets/)、[Workers設定](https://developers.cloudflare.com/workers/wrangler/configuration/)。
