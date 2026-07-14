#!/usr/bin/env python3
"""
Stravaアクティビティのポリラインと mountains.json を照合して
visited_mountains.json を生成するスクリプト。
"""
import json, math, os
from datetime import datetime
from zoneinfo import ZoneInfo

def decode_polyline(s):
    coords, i, lat, lng = [], 0, 0, 0
    while i < len(s):
        result, shift = 0, 0
        while True:
            b = ord(s[i]) - 63; i += 1
            result |= (b & 0x1f) << shift; shift += 5
            if b < 0x20: break
        lat += ~(result >> 1) if result & 1 else result >> 1
        result, shift = 0, 0
        while True:
            b = ord(s[i]) - 63; i += 1
            result |= (b & 0x1f) << shift; shift += 5
            if b < 0x20: break
        lng += ~(result >> 1) if result & 1 else result >> 1
        coords.append((lat/1e5, lng/1e5))
    return coords

def haversine_m(lat1, lng1, lat2, lng2):
    """2点間の距離をメートルで返す"""
    R = 6371000
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng/2)**2
    return R * 2 * math.asin(math.sqrt(a))

def activity_local_date(activity):
    """StravaのUTC開始時刻を日本時間の日付に変換する。"""
    local_start = activity.get("start_date_local", "")
    if local_start:
        return local_start[:10]

    start_date = activity.get("start_date", "")
    if not start_date:
        return ""

    try:
        utc_start = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
    except ValueError:
        return start_date[:10]

    return utc_start.astimezone(ZoneInfo("Asia/Tokyo")).date().isoformat()

THRESHOLD_M = 300  # 山頂から300m以内を通過で「訪問」とみなす
MIN_ELEVATION_M = 100  # 市街地の丘（公園の築山など）を除外するための標高下限
GRID_CELL_DEG = 0.01  # 空間インデックスのセルサイズ（約1.1km、しきい値より十分大きい）
# 車道・リフト経由の誤検出を避けるため、徒歩系のアクティビティのみ判定に使う
FOOT_SPORTS = {"Hike", "TrailRun", "Run", "Walk", "Snowshoe"}

def grid_key(lat, lng):
    return (int(lat / GRID_CELL_DEG), int(lng / GRID_CELL_DEG))

base = os.path.dirname(__file__)
mountains_path = os.path.join(base, "..", "astro", "data", "mountains.json")
activities_path = os.path.join(base, "..", "astro", "data", "strava_activities.json")
output_path = os.path.join(base, "..", "astro", "data", "visited_mountains.json")

with open(mountains_path) as f:
    mountains = json.load(f)
with open(activities_path) as f:
    activities = json.load(f)

print(f"山: {len(mountains)}座, アクティビティ: {len(activities)}件")

# 山を空間インデックス化（セル -> 山リスト）。低すぎる丘は訪問判定の対象外
grid = {}
for mountain in mountains:
    if mountain["elevation"] < MIN_ELEVATION_M:
        continue
    grid.setdefault(grid_key(mountain["lat"], mountain["lng"]), []).append(mountain)

# 山ごとに訪問アクティビティを記録。同名の別峰を区別するため座標込みでキーにする
visited = {}  # (name, lat, lng) -> {mountain info + activities[]}

total = len(activities)
for idx, act in enumerate(activities):
    if not act.get("summary_polyline"):
        continue
    if act.get("sport_type") not in FOOT_SPORTS:
        continue
    if idx % 100 == 0:
        print(f"  処理中 {idx}/{total}...")

    try:
        coords = decode_polyline(act["summary_polyline"])
    except Exception:
        continue

    # 軌跡上の各点の近傍セルにある山だけを距離計算の対象にする
    matched = {}  # (name, lat, lng) -> mountain
    for lat, lng in coords:
        ci, cj = grid_key(lat, lng)
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                for mountain in grid.get((ci + di, cj + dj), ()):
                    key = (mountain["name"], mountain["lat"], mountain["lng"])
                    if key in matched:
                        continue
                    if haversine_m(lat, lng, mountain["lat"], mountain["lng"]) <= THRESHOLD_M:
                        matched[key] = mountain

    date = activity_local_date(act)
    for key, mountain in matched.items():
        if key not in visited:
            visited[key] = {
                "name": mountain["name"],
                "lat": mountain["lat"],
                "lng": mountain["lng"],
                "elevation": mountain["elevation"],
                "tags": mountain["tags"],
                "visit_count": 0,
                "activities": [],
                "first_visit": None,
                "last_visit": None,
            }
        v = visited[key]
        v["visit_count"] += 1
        v["activities"].append({
            "id": act["id"],
            "name": act["name"],
            "date": date,
            "sport_type": act["sport_type"],
            "distance_km": round(act.get("distance", 0) / 1000, 1),
        })
        if v["first_visit"] is None or date < v["first_visit"]:
            v["first_visit"] = date
        if v["last_visit"] is None or date > v["last_visit"]:
            v["last_visit"] = date

result = sorted(visited.values(), key=lambda x: (x.get("first_visit") or ""))

print(f"\n訪問済み: {len(result)}座")
for m in result:
    tags_str = ", ".join(m["tags"])
    print(f"  {m['name']} ({m['elevation']}m) [{tags_str}] {m['visit_count']}回 最初:{m['first_visit']}")

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print(f"\n出力: {output_path}")
