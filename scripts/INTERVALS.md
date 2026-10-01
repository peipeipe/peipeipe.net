# Intervals.icu activity sync

COROS → Intervals.icu → GitHub Actions の順に同期します。Strava経由の活動はAPIの対象外です。

## 初回の実行

```bash
python3 scripts/fetch_intervals_activities.py
python3 scripts/generate_visited_mountains.py
```

APIキーは最初のコマンドの入力欄に貼り付けます（非表示）。環境変数 `INTERVALS_API_KEY` も使えます。キーはコードに保存しません。

## GitHub Actions

GitHub repository Settings → Secrets and variables → Actions で `INTERVALS_API_KEY` を登録します。
変更をpushした後、Actionsの `Update Activities From Intervals` を手動実行して確認します。
定期実行は従来どおり毎日00:30 JSTです（GitHubの実行遅延はあり得ます）。

既存のファイル名 `astro/data/strava_activities.json` は互換性のため維持しています。
過去履歴は残し、開始時刻の差5秒以内・同じ種目・距離差100mまたは3%以内の履歴を同一活動と判定します。
一致した履歴のIDは維持し、IntervalsのID・URL・GPSなどを更新します。複数候補がある場合は書き込まず失敗します。

全期間のメタデータを読み、新規活動と直近30日分のGPSを取得します。過去の編集を取り直す場合は、対象の `intervals_id` を取り除いて再実行してください。
APIから消えた活動の自動削除はしません。取得途中で失敗した場合、既存JSONは変更しません。
エクスポート用ワークフローもIntervals履歴を維持します。`--no-existing-merge` は履歴を維持しない再生成用です。

GPSのない室内活動は、従来どおりサイトの集計には含めません。
