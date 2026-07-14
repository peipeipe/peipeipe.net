#!/usr/bin/env python3
"""
Wikipedia日本語版から山の選定リスト（日本百名山・日本二百名山・日本三百名山・
信州百名山）を取得し、scripts/mountain_selections.json に保存するスクリプト。
generate_mountains.py が mountains.json のタグ付けに使う。
実行頻度は低くてよい（リスト自体はほぼ変わらないため手動実行のみ）。
"""
import json
import os
import re
import urllib.parse

import requests

API = "https://ja.wikipedia.org/w/api.php"
HEADERS = {"User-Agent": "peipeipe.net-mountains/1.0 (https://www.peipeipe.net/)"}


def fetch_wikitext(page):
    res = requests.get(API, params={
        "action": "parse", "page": page, "prop": "wikitext",
        "format": "json", "formatversion": 2,
    }, headers=HEADERS, timeout=30)
    res.raise_for_status()
    return res.json()["parse"]["wikitext"]


def parse_hyakumeizan(text):
    """日本百名山: sortableテーブルの各行から記事名・表示名・標高を抜き出す。
    座標は記事側にしかないので後で座標APIで補う。"""
    entries = []
    for line in text.splitlines():
        m = re.match(
            r"\|\s*\d+\s*\|\|\s*'''\[\[([^\]|]+)(?:\|([^\]]+))?\]\][^']*'''\s*\|\|.*?\|\|\s*([\d.]+)\s*\|\|",
            line,
        )
        if not m:
            continue
        title, display, elev = m.group(1), m.group(2) or m.group(1), m.group(3)
        entries.append({"name": display.strip(), "title": title.strip(),
                        "elevation": int(float(elev)), "lat": None, "lng": None})
    return entries


def parse_sangaku_ichiran(text):
    """日本二百名山・三百名山: {{Module|山岳一覧|...}} の行を解析する。
    行形式: 山名/よみ[/記事名],経度/緯度,画像,標高,都道府県"""
    entries = []
    block = re.search(r"\{\{Module\|山岳一覧\|(.*?)\}\}", text, re.DOTALL)
    if not block:
        return entries
    for line in block.group(1).splitlines():
        line = line.strip().rstrip(",")
        if not line:
            continue
        fields = line.split(",")
        if len(fields) < 4:
            continue
        name_part = fields[0].split("/")
        name = name_part[0].strip()
        title = name_part[2].strip() if len(name_part) > 2 else name
        coord = re.match(r"\s*([\d.]+)/([\d.]+)", fields[1])
        elev = re.match(r"\s*([\d.]+)", fields[-2])
        if not name or not coord:
            continue
        entries.append({
            "name": name, "title": urllib.parse.unquote(title.replace("_", " ")),
            "elevation": int(float(elev.group(1))) if elev else None,
            "lat": round(float(coord.group(2)), 6),
            "lng": round(float(coord.group(1)), 6),
        })
    return entries


def parse_shinshu(text):
    """信州百名山: {{mtlist_number |t=[[記事名|表示名]] |h=標高 |lon=…|lat=…}} を解析する。"""
    entries = []
    for block in re.findall(r"\{\{mtlist_number\b(.*?)\n\}\}", text, re.DOTALL):
        t = re.search(r"\|t=\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", block)
        lon = re.search(r"\|lon=([\d.]+)", block)
        lat = re.search(r"\|lat=([\d.]+)", block)
        h = re.search(r"\|h=([\d.]+)", block)
        if not t or not lon or not lat:
            continue
        title = t.group(1).strip()
        entries.append({
            "name": (t.group(2) or t.group(1)).strip(), "title": title,
            "elevation": int(float(h.group(1))) if h else None,
            "lat": round(float(lat.group(1)), 6),
            "lng": round(float(lon.group(1)), 6),
        })
    return entries


def fill_coordinates(entries):
    """座標が無いエントリの座標をWikipedia記事の座標APIで補う。"""
    missing = [e for e in entries if e["lat"] is None]
    for i in range(0, len(missing), 50):
        batch = missing[i:i + 50]
        res = requests.get(API, params={
            "action": "query", "prop": "coordinates", "redirects": 1,
            "titles": "|".join(e["title"] for e in batch),
            "coprimary": "all", "colimit": "max",
            "format": "json", "formatversion": 2,
        }, headers=HEADERS, timeout=30)
        res.raise_for_status()
        data = res.json()["query"]
        # リダイレクト・正規化を辿って元のタイトルに引き当てる
        rename = {}
        for r in data.get("normalized", []) + data.get("redirects", []):
            rename[r["from"]] = r["to"]
        coords = {}
        for page in data.get("pages", []):
            if page.get("coordinates"):
                c = page["coordinates"][0]
                coords[page["title"]] = (round(c["lat"], 6), round(c["lon"], 6))
        for e in batch:
            resolved = e["title"]
            while resolved in rename:
                resolved = rename[resolved]
            if resolved in coords:
                e["lat"], e["lng"] = coords[resolved]


def main():
    selections = [
        ("百名山", "日本百名山", parse_hyakumeizan),
        ("二百名山", "日本二百名山", parse_sangaku_ichiran),
        ("三百名山", "日本三百名山", parse_sangaku_ichiran),
        ("信州百名山", "信州百名山", parse_shinshu),
    ]
    result = []
    for tag, page, parser in selections:
        entries = parser(fetch_wikitext(page))
        fill_coordinates(entries)
        no_coord = [e["name"] for e in entries if e["lat"] is None]
        print(f"{tag}: {len(entries)}座（座標なし {len(no_coord)}座 {no_coord}）")
        for e in entries:
            e["tag"] = tag
        result.extend(entries)

    output_path = os.path.join(os.path.dirname(__file__), "mountain_selections.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    print(f"出力: {output_path}  ({len(result)}件)")


if __name__ == "__main__":
    main()
