# Strava export で `strava_activities.json` を再生成できるか

調査日: 2026-06-13

## 結論

Strava の月次 export ZIP だけで、現在の `_data/strava_activities.json` を再生成することは**可能**です。

ただし、`activities.csv` だけでは足りません。今の実装が要求している `summary_polyline` は CSV に入っておらず、ZIP 内の各 `activities/*.fit.gz` または `activities/*.gpx.gz` を解析して GPS 軌跡を復元する必要があります。

この変換用に `scripts/generate_strava_activities_from_export.py` を追加しました。

## 確認したこと

- 現行の取得スクリプトは Strava API から `map.summary_polyline` を読んでいます。
  - `scripts/fetch_strava_activities.py:99-118`
- 山判定スクリプトも `summary_polyline` を前提にしています。
  - `scripts/generate_visited_mountains.py:52-60`
- フロント側の型定義も `summary_polyline` を保持しています。
  - `astro/src/lib/activity.ts:5-39`
- GitHub Actions も API 経由で Strava から取得する構成です。
  - `.github/workflows/update-strava-activities.yml:31-39`

## export ZIP の中身

対象 ZIP:

- `/mnt/c/Users/peipe/Downloads/export_24176041.zip`

確認できた内容:

- `activities.csv` は存在する
- `activities.csv` のヘッダに `summary_polyline` はない
- `activities/*.fit.gz` が大量に入っている
- 一部古いアクティビティは `activities/*.gpx.gz`
- `structured_details.csv` はあるが、これは筋トレ系の詳細で、軌跡の代わりにはならない

`activities.csv` の先頭行にも軌跡情報は見当たりませんでした。

今回の ZIP では:

- `activities.csv`: 2620 行
- `fit.gz`: 2550 件
- `gpx.gz`: 3 件
- `Filename` なし: 67 件

## 重要な判断

### 1. CSV だけでは無理

現行の `_data/strava_activities.json` に必要な少なくとも以下は、CSV だけでは揃いません。

- `summary_polyline`
- `start_latlng`

### 2. FIT 解析なら復元可能性が高い

ZIP 内には各アクティビティの `*.fit.gz` が入っています。

FIT は活動の生データを持つ形式なので、これを解析して GPS レコードを抜き出せれば:

- 点列を polyline にエンコード
- `start_latlng` を先頭点から作成
- `distance` / `moving_time` / `elevation` などは CSV を主に使う

という流れで、今の JSON 互換データを作れます。

## 実装した生成フロー

1. 月1回、Strava export ZIP を手動または自動で配置する
2. `activities.csv` を読み込んでアクティビティのメタデータを得る
3. CSV の `Filename` に対応する `activities/*.fit.gz` または `activities/*.gpx.gz` を開く
4. FIT `record` メッセージまたは GPX `trkpt` から GPS 点列を抽出する
5. 点列から `summary_polyline` を生成する
6. `_data/strava_activities.json` を出力する

実行コマンド:

```sh
python3 scripts/generate_strava_activities_from_export.py /mnt/c/Users/peipe/Downloads/export_24176041.zip
python3 scripts/generate_visited_mountains.py
```

実行結果:

- GPS 付きアクティビティ: 1910 件
- `Filename` なしでスキップ: 67 件
- GPS 点なしでスキップ: 643 件
- FIT/GPX 解析失敗: 0 件
- 訪問済み山: 21 座

## 実装上の注意

- すべてのアクティビティに GPS があるとは限らない
  - indoor ワークアウトなどは polyline が空になる可能性がある
- 現行実装は `summary_polyline` がないアクティビティを捨てている
  - export 変換後も同じ方針で、GPS 点列がないアクティビティは出力しない
- FIT の解析は外部ライブラリなしで実装した
  - 必要なのは `record` message の `position_lat` / `position_long`
- CSV の `Activity Type` だけでは `TrailRun` など API の `sport_type` を完全には復元できない
  - 既存 `_data/strava_activities.json` に同じ Activity ID があれば `sport_type` を引き継ぐ

## 採用する運用方針

- 既存の API ベース scheduled workflow は変更しない
  - 通常の自動更新経路として `.github/workflows/update-strava-activities.yml` を残す
- export ZIP からの再生成は手動 workflow で行う
  - `.github/workflows/update-strava-activities-from-export.yml` を GitHub Actions から手動実行する
  - `export_zip_url` に HTTPS で取得できる ZIP URL を渡す
- ZIP はリポジトリにコミットしない
  - 位置情報を含むため、公開 URL に置く場合は短時間だけ使える URL を推奨する
- workflow 実行後は `_data/strava_activities.json` と `_data/visited_mountains.json` が更新され、差分があれば commit/push される
