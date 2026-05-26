#!/usr/bin/env python3
"""
国土地理院「日本の山岳標高一覧」CSVから mountains.json を生成するスクリプト。
ソース: https://www.gsi.go.jp/KOKUJYOHO/MOUNTAIN/1003zan20260130.csv
出力: _data/mountains.json
"""
import csv, json, os, re


def main():
    base = os.path.dirname(__file__)
    csv_path = os.path.join(base, "gsi_mountains.csv")
    output_path = os.path.join(base, "..", "_data", "mountains.json")

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

    # 同一ベース名の出現回数をカウント
    from collections import Counter
    base_count = Counter(r["base_name"] for r in rows)

    result = []
    for r in rows:
        # ベース名が唯一ならシンプルな名前を使用、複数峰なら山頂名込みの名前を使用
        display_name = r["base_name"] if base_count[r["base_name"]] == 1 else r["name_raw"]
        result.append({"name": display_name, "lat": r["lat"], "lng": r["lng"],
                        "elevation": r["elevation"], "tags": []})

    result.sort(key=lambda x: -x["elevation"])
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"出力: {output_path}  ({len(result)}座)")


if __name__ == "__main__":
    main()

