#!/usr/bin/env python3
"""
国土地理院「日本の山岳標高一覧」CSVと OpenStreetMap の山頂データ
（scripts/osm_peaks.json、fetch_osm_peaks.py で取得）をマージし、
選定リスト（scripts/mountain_selections.json、fetch_mountain_selections.py で取得）
のタグを付けて mountains.json を生成するスクリプト。
GSIソース: https://www.gsi.go.jp/KOKUJYOHO/MOUNTAIN/1003zan20260130.csv
OSMソース: © OpenStreetMap contributors (ODbL)
出力: astro/data/mountains.json
"""
import csv
import json
import math
import os
import re
from collections import Counter

# GSIの山から半径この距離以内のOSM峰は同一峰とみなして除外する
DEDUP_RADIUS_M = 300
# 名前が一致する場合は座標のずれが大きくても同一峰とみなす（測位基準の差を吸収）
DEDUP_SAME_NAME_RADIUS_M = 1000
# 選定リスト（Wikipedia由来の座標）と山を照合する際の許容距離
SELECTION_MATCH_RADIUS_M = 2000
# 記事の座標が高原の中心などを指しているケースがあるため、名前が一致する場合の許容距離
SELECTION_NAME_FALLBACK_RADIUS_M = 20000
GRID_CELL_DEG = 0.01  # 空間インデックスのセルサイズ（約1.1km）


def haversine_m(lat1, lng1, lat2, lng2):
    R = 6371000
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng/2)**2
    return R * 2 * math.asin(math.sqrt(a))


def grid_key(lat, lng):
    return (int(lat / GRID_CELL_DEG), int(lng / GRID_CELL_DEG))


def load_gsi(csv_path):
    rows = []
    with open(csv_path, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            name_raw = row["山名＜山頂名＞"].strip()
            lat_str = row["緯度"].strip().replace(" ", "")
            lng_str = row["経度"].strip().replace(" ", "")
            elev_str = row["標高値(m)"].strip().replace(" ", "")
            if not name_raw or not lat_str or not lng_str or not elev_str:
                continue
            try:
                lat = round(float(lat_str), 6)
                lng = round(float(lng_str), 6)
                elev = int(float(elev_str))
            except ValueError:
                continue
            base_name = re.sub(r"＜.*?＞", "", name_raw).strip()
            rows.append({"name_raw": name_raw, "base_name": base_name,
                         "lat": lat, "lng": lng, "elevation": elev})

    # ベース名が唯一ならシンプルな名前を使用、複数峰なら山頂名込みの名前を使用
    base_count = Counter(r["base_name"] for r in rows)
    result = []
    for r in rows:
        display_name = r["base_name"] if base_count[r["base_name"]] == 1 else r["name_raw"]
        # OSMとの名寄せ用エイリアス（ベース名・山頂名・「（別名）」の各表記）
        aliases = {display_name, r["base_name"]}
        peak = re.search(r"＜(.*?)＞", r["name_raw"])
        if peak:
            aliases.add(peak.group(1))
        for alias in list(aliases):
            aliases.update(a for a in re.split(r"[（）()]", alias) if a)
        result.append({
            "name": display_name, "lat": r["lat"], "lng": r["lng"],
            "elevation": r["elevation"], "tags": [],
            "aliases": aliases,
        })
    return result


def selection_names(sel):
    """選定リストのエントリから名寄せ用の名前候補を作る。
    表示名・記事名に加え、「（別名）」「 (曖昧さ回避)」を除いた形も含める。"""
    names = {sel["name"], sel["title"]}
    for name in list(names):
        names.update(n.strip() for n in re.split(r"[（）()]", name) if n.strip())
        names.add(re.sub(r"\s*[（(].*?[）)]\s*", "", name).strip())
    return {n for n in names if n}


def apply_selection_tags(mountains, selections):
    """選定リストの各山を座標（無ければ名前+標高）で山リストに照合してタグを付ける。"""
    grid = {}
    for m in mountains:
        grid.setdefault(grid_key(m["lat"], m["lng"]), []).append(m)
    by_alias = {}
    for m in mountains:
        for alias in m["aliases"]:
            by_alias.setdefault(alias, []).append(m)

    unmatched, added = [], []
    for sel in selections:
        names = selection_names(sel)
        target = None
        if sel["lat"] is not None:
            ci, cj = grid_key(sel["lat"], sel["lng"])
            candidates = [
                (haversine_m(sel["lat"], sel["lng"], m["lat"], m["lng"]), m)
                for di in (-3, -2, -1, 0, 1, 2, 3) for dj in (-3, -2, -1, 0, 1, 2, 3)
                for m in grid.get((ci + di, cj + dj), ())
            ]
            candidates = [c for c in candidates if c[0] <= SELECTION_MATCH_RADIUS_M]
            # 半径内に名前の一致する峰があれば優先し、無ければ最寄りの峰に付ける
            named = [c for c in candidates if names & c[1]["aliases"]]
            pool = named or candidates
            if pool:
                target = min(pool, key=lambda c: c[0])[1]

        if target is None:
            # 名前で照合（座標なし、または記事の座標が山頂から外れているケース）
            candidates = {id(m): m for n in names for m in by_alias.get(n, ())}.values()
            if sel["lat"] is not None:
                nearby = [
                    (haversine_m(sel["lat"], sel["lng"], m["lat"], m["lng"]), m)
                    for m in candidates
                ]
                nearby = [c for c in nearby if c[0] <= SELECTION_NAME_FALLBACK_RADIUS_M]
                if nearby:
                    target = min(nearby, key=lambda c: c[0])[1]
            elif candidates and sel.get("elevation") is not None:
                target = min(candidates, key=lambda m: abs(m["elevation"] - sel["elevation"]))
            elif candidates:
                target = next(iter(candidates))

        if target is None and sel["lat"] is not None:
            # どのデータ源にも無い峰は選定リストの座標で新規エントリとして追加する
            target = {
                "name": sel["name"], "lat": sel["lat"], "lng": sel["lng"],
                "elevation": sel.get("elevation") or 0,
                "tags": [], "aliases": names,
            }
            mountains.append(target)
            grid.setdefault(grid_key(target["lat"], target["lng"]), []).append(target)
            for alias in names:
                by_alias.setdefault(alias, []).append(target)
            added.append(f"{sel['tag']}:{sel['name']}")

        if target is None:
            unmatched.append(f"{sel['tag']}:{sel['name']}")
        elif sel["tag"] not in target["tags"]:
            target["tags"].append(sel["tag"])

    if added:
        print(f"選定リストから新規追加した山: {added}")
    if unmatched:
        print(f"照合できなかった選定リストの山: {unmatched}")


def main():
    base = os.path.dirname(__file__)
    gsi = load_gsi(os.path.join(base, "gsi_mountains.csv"))

    osm_path = os.path.join(base, "osm_peaks.json")
    with open(osm_path) as f:
        osm_peaks = json.load(f)

    # GSIの山を空間インデックス化し、近接するOSM峰を重複として除外
    grid = {}
    for m in gsi:
        grid.setdefault(grid_key(m["lat"], m["lng"]), []).append(m)

    combined = list(gsi)
    dropped = 0
    for p in osm_peaks:
        ci, cj = grid_key(p["lat"], p["lng"])
        near_gsi = [
            m for di in (-2, -1, 0, 1, 2) for dj in (-2, -1, 0, 1, 2)
            for m in grid.get((ci + di, cj + dj), ())
        ]
        duplicate = any(
            haversine_m(p["lat"], p["lng"], m["lat"], m["lng"])
            <= (DEDUP_SAME_NAME_RADIUS_M if p["name"] in m["aliases"] else DEDUP_RADIUS_M)
            for m in near_gsi
        )
        if duplicate:
            dropped += 1
            continue
        combined.append({
            "name": p["name"], "lat": p["lat"], "lng": p["lng"],
            "elevation": p["elevation"] if p["elevation"] is not None else 0,
            "tags": [],
            "aliases": {n.strip() for n in re.split(r"[（）()]", p["name"]) if n.strip()} | {p["name"]},
        })

    selections_path = os.path.join(base, "mountain_selections.json")
    with open(selections_path) as f:
        selections = json.load(f)
    apply_selection_tags(combined, selections)
    tagged = sum(1 for m in combined if m["tags"])

    result = [{k: v for k, v in m.items() if k != "aliases"} for m in combined]
    result.sort(key=lambda x: -x["elevation"])
    output_path = os.path.join(base, "..", "astro", "data", "mountains.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"GSI {len(gsi)}座 + OSM {len(osm_peaks)}座（重複除外 {dropped}座）")
    print(f"選定リスト {len(selections)}件 → タグ付き {tagged}座")
    print(f"出力: {output_path}  ({len(result)}座)")


if __name__ == "__main__":
    main()
