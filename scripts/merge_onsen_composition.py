#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Claude Code が書き起こした成分表データを astro/data/onsen_composition.json に反映する。

prepare_onsen_composition.py が用意した .cache/onsen_photos/manifest.json と、
そこにある写真を読んで書き起こした .cache/onsen_photos/extracted.json を突き合わせ、

  * extracted.json に出てくる写真 → 施設ごとの成分データとして記録
  * manifest にあるのに extracted.json に出てこない写真 → 成分表ではなかった写真として記録

の2つに仕分けして保存する。どちらも「解析済み」として扱われるので、次回の
prepare_onsen_composition.py は残りの写真だけを対象にする。
"""

import argparse
import json
import os
import sys
from datetime import date

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASTRO_DIR = os.path.join(BASE_DIR, 'astro')
CACHE_DIR = os.path.join(BASE_DIR, '.cache', 'onsen_photos')
MANIFEST_JSON = os.path.join(CACHE_DIR, 'manifest.json')
EXTRACTED_JSON = os.path.join(CACHE_DIR, 'extracted.json')
ONSEN_JSON = os.path.join(ASTRO_DIR, 'data', 'onsen_places.json')
OUTPUT_JSON = os.path.join(ASTRO_DIR, 'data', 'onsen_composition.json')

# 施設ごとに保持するキーの並び（出力の見やすさのため固定）
FIELD_ORDER = [
    "fsq_id",
    "name",
    "address",
    "checkin_date",
    "confidence",
    "spring_name",
    "spring_quality",
    "spring_quality_class",
    "source_temp_c",
    "use_temp_c",
    "ph",
    "ph_lab",
    "yield_l_min",
    "evaporation_residue_mg_kg",
    "dissolved_solids_mg_kg",
    "total_ingredients_mg_kg",
    "cations",
    "cations_total_mg_kg",
    "anions",
    "anions_total_mg_kg",
    "undissociated",
    "undissociated_total_mg_kg",
    "dissolved_gas",
    "dissolved_gas_total_mg_kg",
    "treatment",
    "indications",
    "contraindications",
    "analyzed_on",
    "analyzer",
    "analyzer_registration",
    "notes",
    "source_photos",
]


def load_json(path, fallback=None):
    if not os.path.exists(path):
        return fallback
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def photo_lookup(manifest):
    return {photo['index']: photo for photo in manifest.get('photos', [])}


def order_fields(entry):
    ordered = {key: entry[key] for key in FIELD_ORDER if key in entry}
    for key, value in entry.items():
        if key not in ordered:
            ordered[key] = value
    return ordered


def build_entries(extracted, photos_by_index):
    """extracted.json の各エントリを、写真から施設情報を補って組み立てる。"""
    entries = []
    used_photo_urls = set()

    for raw in extracted.get('places', []):
        indexes = raw.get('photo_indexes') or []
        photos = [photos_by_index[i] for i in indexes if i in photos_by_index]
        missing = [i for i in indexes if i not in photos_by_index]
        if missing:
            print(f"[Warn] manifest に無い photo_index: {missing}", file=sys.stderr)
        if not photos:
            print(f"[Warn] 写真を解決できないエントリをスキップ: {indexes}", file=sys.stderr)
            continue

        entry = {key: value for key, value in raw.items() if key != 'photo_indexes'}
        entry['fsq_id'] = photos[0].get('fsq_id', '')
        entry['name'] = photos[0].get('place_name', '')
        entry['address'] = photos[0].get('address', '')
        entry['checkin_date'] = photos[0].get('date', '')
        entry['source_photos'] = [photo['photo_url'] for photo in photos]
        used_photo_urls.update(entry['source_photos'])

        entries.append(order_fields(entry))

    return entries, used_photo_urls


def merge_places(existing, incoming):
    """fsq_id をキーに既存データへマージする。

    既存エントリがある場合は差し替えではなく項目単位でマージする。再訪して掲示の
    一部だけ読み直したときに、前回読み取った成分値まで失われないようにするため。
    項目を消したいときは astro/data/onsen_composition.json を直接編集する。
    """
    by_id = {entry.get('fsq_id'): entry for entry in existing}

    for entry in incoming:
        fsq_id = entry.get('fsq_id')
        current = by_id.get(fsq_id)
        if current:
            photos = current.get('source_photos', []) + [
                url for url in entry.get('source_photos', [])
                if url not in current.get('source_photos', [])
            ]
            entry = {**current, **entry, 'source_photos': photos}
        by_id[fsq_id] = order_fields(entry)

    return list(by_id.values())


def sort_key(entry, order_by_fsq):
    return order_by_fsq.get(entry.get('fsq_id'), 10**6)


def main():
    parser = argparse.ArgumentParser(description="成分表の書き起こしをデータJSONに反映する")
    parser.add_argument(
        '--extracted',
        default=EXTRACTED_JSON,
        help=f"書き起こしJSONのパス（既定: {EXTRACTED_JSON}）",
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help="書き込まずに結果だけ表示する",
    )
    args = parser.parse_args()

    manifest = load_json(MANIFEST_JSON)
    if not manifest:
        print(f"[Error] {MANIFEST_JSON} がありません。先に prepare_onsen_composition.py を実行してください。", file=sys.stderr)
        sys.exit(1)

    extracted = load_json(args.extracted)
    if not extracted:
        print(f"[Error] {args.extracted} がありません。", file=sys.stderr)
        sys.exit(1)

    photos_by_index = photo_lookup(manifest)
    entries, used_photo_urls = build_entries(extracted, photos_by_index)

    current = load_json(OUTPUT_JSON, {}) or {}
    places = merge_places(current.get('places', []), entries)

    not_composition = list(current.get('not_composition_photos') or [])
    for photo in manifest.get('photos', []):
        url = photo['photo_url']
        if url in used_photo_urls or url in not_composition:
            continue
        not_composition.append(url)

    # 温泉一覧（新しいチェックイン順）に合わせて並べる
    onsen_places = load_json(ONSEN_JSON, []) or []
    order_by_fsq = {
        place.get('fsq_id'): index for index, place in enumerate(onsen_places)
    }
    places.sort(key=lambda entry: sort_key(entry, order_by_fsq))

    payload = {
        "generated_on": date.today().isoformat(),
        "stats": {
            "places": len(places),
            "composition_photos": sum(len(entry.get('source_photos') or []) for entry in places),
            "not_composition_photos": len(not_composition),
        },
        "places": places,
        "not_composition_photos": not_composition,
    }

    print("=== 成分表データを更新 ===")
    print(f"成分表のある施設: {payload['stats']['places']}件")
    print(f"成分表の写真: {payload['stats']['composition_photos']}枚")
    print(f"成分表ではなかった写真: {payload['stats']['not_composition_photos']}枚")

    if args.dry_run:
        print("--dry-run のため書き込みませんでした。")
        return

    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write('\n')

    print(f"書き出し先: {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
