#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""書き起こした成分表データを astro/data/onsen_composition.json に反映する。

書き起こしは extract_onsen_composition.py（Gemini）でも、Claude Code のセッション
（/onsen-composition）でもよく、どちらも .cache/onsen_photos/extracted.json を書く。
それを prepare_onsen_composition.py が用意した manifest.json と突き合わせ、写真を
次のいずれかに仕分けする:

  * extracted.json の places に出てくる → 施設ごとの成分データとして記録
  * 読ませたが採用されなかった → 成分表ではなかった写真として記録
  * 読ませたが読み取れなかった → unreadable_photos に試行回数つきで記録
  * そもそも読ませていない → 何もせず未解析のまま残す

前の3つは「解析済み」として扱われ、次回の prepare_onsen_composition.py の対象から
外れる（unreadable_photos は MAX_READ_ATTEMPTS 回に達するまで再挑戦する）。最後の
1つを取り違えると、見てもいない分析書が二度と解析されなくなるので注意。
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

# 同じ写真の書き起こしを何回まで試すか。壊れた画像や安全フィルタに引っかかる写真を
# 毎日叩き続けないための上限。到達した写真は prepare_onsen_composition.py の対象から
# 外れる（--all を付ければまた拾える）。
MAX_READ_ATTEMPTS = 3

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
    "validation_exceptions",
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

    # 書き起こし側が読めなかったと申告した写真は、判定を保留して未解析のまま残す。
    # 「成分表ではなかった」と確定させてしまうと、一時的なエラーで読めなかった分析書が
    # 二度と解析対象に戻らなくなるため。ただし何度やっても読めない写真を毎日叩き続けても
    # 仕方がないので、試行回数を数えて MAX_READ_ATTEMPTS で打ち切る。
    unreadable = {
        entry['photo_url']: entry
        for entry in current.get('unreadable_photos') or []
        if entry.get('photo_url')
    }
    # 読めるようになった写真は記録から外す
    for url in used_photo_urls:
        unreadable.pop(url, None)

    failed_urls = set()
    for failure in extracted.get('failed_photos') or []:
        photo = photos_by_index.get(failure.get('index'))
        if not photo:
            continue
        url = photo['photo_url']
        failed_urls.add(url)
        entry = unreadable.get(url) or {'photo_url': url, 'attempts': 0}
        entry['attempts'] = entry.get('attempts', 0) + 1
        entry['last_error'] = failure.get('error', '')
        entry['last_attempt_on'] = date.today().isoformat()
        unreadable[url] = entry

    if failed_urls:
        exhausted = sum(
            1 for url in failed_urls
            if unreadable[url]['attempts'] >= MAX_READ_ATTEMPTS
        )
        print(f"読み取れなかった写真: {len(failed_urls)}枚（うち{exhausted}枚は試行上限に到達）")

    # 「成分表ではなかった」と言えるのは、実際に読ませたうえで採用されなかった写真だけ。
    # extract 側が枚数上限や --limit で送らなかった写真、Claude が見なかった写真は
    # 未解析のまま残す。processed_photo_indexes が無い書き起こし（/onsen-composition で
    # 手書きしたもの）は、コンタクトシートで全部に目を通しているので manifest 全体を対象とする。
    processed = extracted.get('processed_photo_indexes')
    if processed is None:
        reviewed = manifest.get('photos', [])
    else:
        reviewed = [photos_by_index[i] for i in processed if i in photos_by_index]
        unseen = len(manifest.get('photos', [])) - len(reviewed)
        if unseen > 0:
            print(f"読ませなかった写真: {unseen}枚（未解析のまま残します）")

    not_composition = list(current.get('not_composition_photos') or [])
    for photo in reviewed:
        url = photo['photo_url']
        if url in used_photo_urls or url in not_composition or url in unreadable:
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
            "unreadable_photos": len(unreadable),
        },
        "places": places,
        "not_composition_photos": not_composition,
    }
    if unreadable:
        payload["unreadable_photos"] = sorted(
            unreadable.values(), key=lambda entry: entry['photo_url']
        )

    print("=== 成分表データを更新 ===")
    print(f"成分表のある施設: {payload['stats']['places']}件")
    print(f"成分表の写真: {payload['stats']['composition_photos']}枚")
    print(f"成分表ではなかった写真: {payload['stats']['not_composition_photos']}枚")
    if unreadable:
        stuck = sum(1 for e in unreadable.values() if e['attempts'] >= MAX_READ_ATTEMPTS)
        print(f"読めなかった写真: {len(unreadable)}枚（うち{stuck}枚は試行上限に到達し、以後は対象外）")

    if args.dry_run:
        print("--dry-run のため書き込みませんでした。")
        return

    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write('\n')

    print(f"書き出し先: {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
