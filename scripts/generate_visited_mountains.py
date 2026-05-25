#!/usr/bin/env python3
"""
Stravaアクティビティのポリラインと mountains.json を照合して
visited_mountains.json を生成するスクリプト。
"""
import json, math, os

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

THRESHOLD_M = 600  # 山頂から600m以内を通過で「訪問」とみなす

base = os.path.dirname(__file__)
mountains_path = os.path.join(base, "..", "_data", "mountains.json")
activities_path = os.path.join(base, "..", "_data", "strava_activities.json")
output_path = os.path.join(base, "..", "_data", "visited_mountains.json")

with open(mountains_path) as f:
    mountains = json.load(f)
with open(activities_path) as f:
    activities = json.load(f)

print(f"山: {len(mountains)}座, アクティビティ: {len(activities)}件")

# 山ごとに訪問アクティビティを記録
visited = {}  # name -> {mountain info + activities[]}

total = len(activities)
for idx, act in enumerate(activities):
    if not act.get("summary_polyline"):
        continue
    if idx % 100 == 0:
        print(f"  処理中 {idx}/{total}...")
    
    try:
        coords = decode_polyline(act["summary_polyline"])
    except Exception:
        continue
    
    # 間引き（4点に1点）で高速化
    step = max(1, len(coords) // 200)
    sampled = coords[::step]
    
    for mountain in mountains:
        mlat, mlng = mountain["lat"], mountain["lng"]
        
        # まず緯度差の粗いフィルタ（0.01度 ≈ 1.1km）
        if not any(abs(p[0] - mlat) < 0.015 and abs(p[1] - mlng) < 0.015 for p in sampled):
            continue
        
        # 精密な距離計算
        min_dist = min(haversine_m(p[0], p[1], mlat, mlng) for p in coords[::max(1, len(coords)//500)])
        
        if min_dist <= THRESHOLD_M:
            name = mountain["name"]
            if name not in visited:
                visited[name] = {
                    "name": name,
                    "lat": mlat,
                    "lng": mlng,
                    "elevation": mountain["elevation"],
                    "tags": mountain["tags"],
                    "visit_count": 0,
                    "activities": [],
                    "first_visit": None,
                    "last_visit": None,
                }
            v = visited[name]
            v["visit_count"] += 1
            date = act.get("start_date", "")[:10]
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
