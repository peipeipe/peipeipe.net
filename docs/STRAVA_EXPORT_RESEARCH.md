# Strava export で `strava_activities.json` を再生成できるか

調査日: 2026-06-13

## 結論

Strava の月次 export ZIP だけで、現在の `_data/strava_activities.json` を再生成することは**可能性が高い**です。

ただし、`activities.csv` だけでは足りません。今の実装が要求している `summary_polyline` は CSV に入っておらず、ZIP 内の各 `activities/*.fit.gz` を解析して GPS 軌跡を復元する必要があります。

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
- `structured_details.csv` はあるが、これは筋トレ系の詳細で、軌跡の代わりにはならない

`activities.csv` の先頭行にも軌跡情報は見当たりませんでした。

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

## 想定する新しい生成フロー

1. 月1回、Strava export ZIP を手動または自動で配置する
2. `activities.csv` を読み込んでアクティビティのメタデータを得る
3. 対応する `activities/<Activity ID>.fit.gz` を開く
4. FIT から `record` メッセージの GPS 点列を抽出する
5. 点列から `summary_polyline` を生成する
6. `_data/strava_activities.json` を出力する

## 実装上の注意

- すべてのアクティビティに GPS があるとは限らない
  - indoor ワークアウトなどは polyline が空になる可能性がある
- 現行実装は `summary_polyline` がないアクティビティを捨てている
  - 置き換え後も同じ方針にするか、`null` を許すか決める必要がある
- FIT の解析には専用パーサが必要
  - この環境では既存ライブラリが入っていなかったため、実装時に依存追加か自前パーサが必要

## 次の作業候補

- `activities.csv` + `activities/*.fit.gz` から `_data/strava_activities.json` を作るスクリプトを追加する
- 既存の `scripts/fetch_strava_activities.py` を export ベースに差し替える
- GitHub Actions を API ベースから export ベースに変更する

