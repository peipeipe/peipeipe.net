#!/usr/bin/env python3
"""
Overpass API から日本国内の名前付き山頂ノード（natural=peak）を取得し、
scripts/osm_peaks.json に保存するスクリプト。

出典: © OpenStreetMap contributors (ODbL)
実行頻度は低くてよい（マスターデータの更新時のみ手動実行）。
"""
import json
import os
import re
import time

import requests

OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

QUERY = """
[out:json][timeout:600];
area["ISO3166-1"="JP"][admin_level=2]->.jp;
node["natural"="peak"]["name"](area.jp);
out body;
"""


def fetch():
    last_error = None
    for endpoint in OVERPASS_ENDPOINTS:
        for attempt in range(2):
            try:
                print(f"取得中: {endpoint} (試行 {attempt + 1})...")
                res = requests.post(
                    endpoint,
                    data={"data": QUERY},
                    headers={"User-Agent": "peipeipe.net-mountains/1.0 (https://www.peipeipe.net/)"},
                    timeout=900,
                )
                res.raise_for_status()
                return res.json()
            except Exception as e:
                last_error = e
                print(f"  失敗: {e}")
                time.sleep(10)
    raise SystemExit(f"Overpass からの取得に失敗しました: {last_error}")


def parse_elevation(tags):
    """ele タグを整数メートルに正規化する。異常値は無視。"""
    raw = tags.get("ele", "").strip().replace("m", "").replace(",", "")
    if not raw:
        return None
    try:
        elev = float(raw)
    except ValueError:
        return None
    if not (0 < elev < 3800):  # 富士山より高い値・非正値はデータ不備とみなす
        return None
    return int(round(elev))


GSI_ELEVATION_API = "https://cyberjapandata2.gsi.go.jp/general/dem/scripts/getelevation.php"


def fill_missing_elevations(peaks, previous):
    """ele タグの無い峰の標高を国土地理院の標高APIで補完する。
    前回実行分（previous）に同座標の値があれば再利用してAPI呼び出しを省く。"""
    cache = {(p["lat"], p["lng"]): p["elevation"] for p in previous
             if p.get("elevation") is not None}
    targets = [p for p in peaks if p["elevation"] is None]
    for p in targets:
        cached = cache.get((p["lat"], p["lng"]))
        if cached is not None:
            p["elevation"] = cached
    remaining = [p for p in targets if p["elevation"] is None]
    print(f"標高欠損 {len(targets)}座（うちキャッシュ再利用 {len(targets) - len(remaining)}座）")

    for i, p in enumerate(remaining):
        if i % 200 == 0:
            print(f"  標高API {i}/{len(remaining)}...")
        try:
            res = requests.get(
                GSI_ELEVATION_API,
                params={"lon": p["lng"], "lat": p["lat"], "outtype": "JSON"},
                timeout=10,
            )
            res.raise_for_status()
            elev = res.json().get("elevation")
            if isinstance(elev, (int, float)):
                p["elevation"] = int(round(elev))
        except Exception:
            pass  # 取得できなかった峰は elevation: null のまま残す
        time.sleep(0.1)


def main():
    output_path = os.path.join(os.path.dirname(__file__), "osm_peaks.json")
    previous = []
    if os.path.exists(output_path):
        with open(output_path) as f:
            previous = json.load(f)

    data = fetch()
    peaks = []
    for el in data.get("elements", []):
        tags = el.get("tags", {})
        name = (tags.get("name:ja") or tags.get("name", "")).strip()
        if not name or el.get("lat") is None or el.get("lon") is None:
            continue
        # 「363M」「67.2」のような標高値だけの名前はデータ不備とみなして除外
        if re.fullmatch(r"[0-9.,\s]+m?", name, re.IGNORECASE):
            continue
        peaks.append({
            "name": name,
            "lat": round(el["lat"], 6),
            "lng": round(el["lon"], 6),
            "elevation": parse_elevation(tags),
        })

    fill_missing_elevations(peaks, previous)

    peaks.sort(key=lambda p: (p["lat"], p["lng"]))
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(peaks, f, ensure_ascii=False, indent=1)

    with_elev = sum(1 for p in peaks if p["elevation"] is not None)
    print(f"出力: {output_path}  ({len(peaks)}座, 標高あり {with_elev}座)")


if __name__ == "__main__":
    main()
