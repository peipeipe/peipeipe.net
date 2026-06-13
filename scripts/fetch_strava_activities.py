#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Strava API からアクティビティを取得し、astro/data/strava_activities.json に保存するスクリプト。

必要な環境変数:
  STRAVA_CLIENT_ID      - Strava API のクライアントID
  STRAVA_CLIENT_SECRET  - Strava API のクライアントシークレット
  STRAVA_REFRESH_TOKEN  - Strava API の長期リフレッシュトークン

Strava API アプリ登録: https://www.strava.com/settings/api
リフレッシュトークンの取得方法については README を参照してください。
"""

import json
import os
import sys
from datetime import datetime, timezone

import requests

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_JSON = os.path.join(BASE_DIR, "astro", "data", "strava_activities.json")

STRAVA_TOKEN_URL = "https://www.strava.com/oauth/token"
STRAVA_ACTIVITIES_URL = "https://www.strava.com/api/v3/athlete/activities"

# ヒートマップに含めるスポーツタイプ（None の場合はすべて含める）
# 例: {"Run", "TrailRun", "Ride", "GravelRide", "Walk", "Hike"}
INCLUDE_SPORT_TYPES = None

# 1回のリクエストで取得する件数（最大200）
PER_PAGE = 200


def load_env_file(filepath):
    """ローカル開発用: .env ファイルから環境変数を読み込む"""
    if not os.path.exists(filepath):
        return
    with open(filepath, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


def refresh_access_token(client_id, client_secret, refresh_token):
    """リフレッシュトークンを使ってアクセストークンを取得する"""
    resp = requests.post(
        STRAVA_TOKEN_URL,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if "access_token" not in data:
        print(f"Error: Unexpected token response: {data}", file=sys.stderr)
        sys.exit(1)
    return data["access_token"]


def fetch_all_activities(access_token):
    """全アクティビティをページネーションで取得する"""
    activities = []
    page = 1
    headers = {"Authorization": f"Bearer {access_token}"}

    while True:
        print(f"  Fetching page {page}...")
        resp = requests.get(
            STRAVA_ACTIVITIES_URL,
            headers=headers,
            params={"page": page, "per_page": PER_PAGE},
            timeout=30,
        )
        resp.raise_for_status()
        batch = resp.json()

        if not batch:
            break

        for activity in batch:
            sport_type = activity.get("sport_type") or activity.get("type", "")

            # フィルタリング
            if INCLUDE_SPORT_TYPES and sport_type not in INCLUDE_SPORT_TYPES:
                continue

            # ポリラインがないアクティビティはスキップ
            summary_polyline = (activity.get("map") or {}).get("summary_polyline", "")
            if not summary_polyline:
                continue

            activities.append(
                {
                    "id": activity["id"],
                    "name": activity["name"],
                    "sport_type": sport_type,
                    "distance": activity.get("distance", 0),
                    "moving_time": activity.get("moving_time", 0),
                    "elapsed_time": activity.get("elapsed_time", 0),
                    "total_elevation_gain": activity.get("total_elevation_gain", 0),
                    "start_date": activity.get("start_date", ""),
                    "start_latlng": activity.get("start_latlng") or [],
                    "average_speed": activity.get("average_speed", 0),
                    "max_speed": activity.get("max_speed", 0),
                    "summary_polyline": summary_polyline,
                }
            )

        print(f"  -> Got {len(batch)} activities (cumulative: {len(activities)} with polylines)")

        if len(batch) < PER_PAGE:
            break

        page += 1

    return activities


def main():
    # ローカル開発用に .env を読み込む
    load_env_file(os.path.join(BASE_DIR, ".env"))

    client_id = os.environ.get("STRAVA_CLIENT_ID")
    client_secret = os.environ.get("STRAVA_CLIENT_SECRET")
    refresh_token = os.environ.get("STRAVA_REFRESH_TOKEN")

    if not all([client_id, client_secret, refresh_token]):
        print(
            "Error: STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET, STRAVA_REFRESH_TOKEN が必要です。",
            file=sys.stderr,
        )
        sys.exit(1)

    print("Strava アクセストークンを取得中...")
    access_token = refresh_access_token(client_id, client_secret, refresh_token)

    print("アクティビティを取得中...")
    activities = fetch_all_activities(access_token)

    print(f"合計 {len(activities)} 件のアクティビティを取得しました（ポリライン付き）")

    # 日付降順でソート
    activities.sort(key=lambda x: x.get("start_date", ""), reverse=True)

    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(activities, f, ensure_ascii=False, indent=2)

    print(f"保存完了: {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
