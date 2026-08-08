#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ネット公開情報から書き起こした成分表を astro/data/onsen_composition.json に反映する。

写真から読む merge_onsen_composition.py と違い、こちらは施設の公式サイト・自治体
ページ・温泉紹介サイトに載っている値を入力にする。チェックイン写真に分析書が
写っていない施設（そもそも撮っていない、掲示が画角の外）でも成分表を持てるように
するための経路で、写真側のパイプラインとは独立して動く。

入力は .cache/onsen_web/web_entries.json（--input で変更可）:

    {"places": [{"fsq_id": "...", "spring_quality": "...", ...}, ...]}

name / address / checkin_date は astro/data/onsen_places.json から補完するので
書かなくてよい。fsq_id の代わりに name_match（onsen_places.json 上の施設名）でも
引ける。

写真経路と同じ fsq_id 単位のフィールドマージなので、写真から読んだ値がある施設に
ネット由来の値を足しても、既存の値は消えない（同じキーがあればネット側で上書き）。
not_composition_photos / unreadable_photos は写真経路の状態なので手を触れない。

信頼度の目安（confidence）:

    high   … 施設が公開している温泉分析書そのもの（PDF・画像）を読んだもの
    medium … 公式サイトや自治体ページが本文に書いている泉質・pH・泉温など
    low    … 温泉紹介サイトや個人サイトなど二次情報しかないもの

いずれも現地掲示を目で見たわけではないので、出典を notes に必ず書くこと。
"""

import argparse
import json
import os
import sys
from datetime import date

from merge_onsen_composition import (
    ONSEN_JSON,
    OUTPUT_JSON,
    load_json,
    merge_places,
    order_fields,
    sort_key,
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_CACHE_DIR = os.path.join(BASE_DIR, '.cache', 'onsen_web')
WEB_ENTRIES_JSON = os.path.join(WEB_CACHE_DIR, 'web_entries.json')


def build_entries(raw_places, onsen_places):
    """入力エントリに施設情報（名前・住所・チェックイン日）を補う。"""
    by_fsq = {place.get('fsq_id'): place for place in onsen_places}
    by_name = {place.get('name'): place for place in onsen_places}

    entries = []
    for raw in raw_places:
        entry = {key: value for key, value in raw.items() if key != 'name_match'}
        place = by_fsq.get(entry.get('fsq_id')) or by_name.get(raw.get('name_match'))
        if not place:
            print(
                f"[Warn] onsen_places.json に無い施設をスキップ: "
                f"{entry.get('fsq_id') or raw.get('name_match')}",
                file=sys.stderr,
            )
            continue
        entry['fsq_id'] = place['fsq_id']
        entry.setdefault('name', place.get('name', ''))
        entry.setdefault('address', place.get('address', ''))
        entry.setdefault('checkin_date', place.get('date', ''))
        entries.append(order_fields(entry))
    return entries


def main():
    parser = argparse.ArgumentParser(description="ネット由来の成分表データを反映する")
    parser.add_argument(
        '--input',
        default=WEB_ENTRIES_JSON,
        help=f"入力JSONのパス（既定: {WEB_ENTRIES_JSON}）",
    )
    parser.add_argument('--dry-run', action='store_true', help="書き込まずに結果だけ表示する")
    args = parser.parse_args()

    incoming = load_json(args.input)
    if not incoming:
        print(f"[Error] {args.input} がありません。", file=sys.stderr)
        sys.exit(1)

    onsen_places = load_json(ONSEN_JSON, []) or []
    current = load_json(OUTPUT_JSON, {}) or {}
    existing = current.get('places', [])
    known_ids = {entry.get('fsq_id') for entry in existing}

    entries = build_entries(incoming.get('places') or [], onsen_places)
    places = merge_places(existing, entries)

    order_by_fsq = {place.get('fsq_id'): index for index, place in enumerate(onsen_places)}
    places.sort(key=lambda entry: sort_key(entry, order_by_fsq))

    payload = dict(current)
    payload['generated_on'] = date.today().isoformat()
    payload['places'] = places
    stats = dict(current.get('stats') or {})
    stats['places'] = len(places)
    stats['composition_photos'] = sum(len(entry.get('source_photos') or []) for entry in places)
    payload['stats'] = stats

    added = [entry for entry in entries if entry['fsq_id'] not in known_ids]
    updated = [entry for entry in entries if entry['fsq_id'] in known_ids]

    print("=== ネット由来の成分表を反映 ===")
    print(f"新規: {len(added)}件 / 既存に追記: {len(updated)}件 / 合計: {len(places)}件")
    for entry in added:
        print(f"  + {entry.get('name')}（{entry.get('confidence', '-')}）")
    for entry in updated:
        print(f"  ~ {entry.get('name')}（{entry.get('confidence', '-')}）")

    if args.dry_run:
        print("--dry-run のため書き込みませんでした。")
        return

    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print(f"書き出し先: {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
