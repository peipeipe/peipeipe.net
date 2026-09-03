#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""温泉分析書の写真を Gemini に読ませて .cache/onsen_photos/extracted.json を書く。

/onsen-composition では Claude Code の対話セッションが担っていた「写真を読んで
書き起こす」ステップを、無料枠で動く API に置き換えるためのスクリプト。前後の
prepare_onsen_composition.py / merge_onsen_composition.py はそのまま使う。

  python3 scripts/prepare_onsen_composition.py
  GEMINI_API_KEY=... python3 scripts/extract_onsen_composition.py
  python3 scripts/merge_onsen_composition.py

施設（fsq_id）ごとに、その施設の未解析写真をまとめて1リクエストで送る。掲示内容
決定通知書・温泉分析書・別表が別々の写真に分かれていることがあり、まとめて見せた
うえで源泉ごとのデータとして組み立てるため。成分表が1枚も写っていなければ
その施設は extracted.json に出てこないので、merge 側が「成分表ではなかった写真」
として記録する。

読み取りの正しさは validate_onsen_composition.py の検算にかける。合計が合わない
エントリは confidence を下げて notes に理由を残すので、あとから
/onsen-composition で人が読み直す対象を絞り込める。
"""

import argparse
import base64
import json
import os
import sys
import time

import requests

from validate_onsen_composition import check_entry, describe

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(BASE_DIR, '.cache', 'onsen_photos')
MANIFEST_JSON = os.path.join(CACHE_DIR, 'manifest.json')
EXTRACTED_JSON = os.path.join(CACHE_DIR, 'extracted.json')

API_ROOT = 'https://generativelanguage.googleapis.com/v1beta/models'
DEFAULT_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-3.6-flash')
REQUEST_TIMEOUT = 180
MAX_RETRIES = 4
SLEEP_BETWEEN_CALLS = 2.0
MAX_PHOTOS_PER_REQUEST = 6
MAX_OUTPUT_TOKENS = 16384

PROMPT = """あなたは日本の温泉分析書を読み取る担当者です。

同じ温泉施設「{place_name}」で撮影された写真を {count} 枚渡します。各画像の直前に
「写真 #N」と番号を書いてあります。この番号をそのまま photo_indexes に使ってください。
チェックイン時に「成分表: …」として指定されたヒントも参考情報として渡します。写真の記載と矛盾する場合は必ず写真を
優先してください。

チェックインの成分表ヒント: {composition_hint}

まず、温泉分析書・温泉成分等掲示表・温泉の掲示内容決定通知書・温泉分析書別表など、
分析値や泉質が読み取れる掲示が写っている写真だけを選んでください。施設の外観・料金表・
のれん・食事・源泉名だけの看板などは対象外です。対象が1枚も無ければ
{{"is_composition": false}} だけを返してください。

対象がある場合は、同じ源泉の分析書・別表だけを1件に統合し、源泉ごとに springs の別要素で
返してください。異なる源泉名、泉質、分析日、成分値の分析書を混ぜてはいけません。守ること:

- 数値の単位は mg/kg に統一する。分析書が g/kg 表記なら 1000 倍する。
- 掲示に書かれていない項目は省く。推測で埋めない。
- 読み取りに自信が持てない値は書かない。書かないほうが、間違った値より良い。
- 温泉分析書は合計が必ず一致する。各成分の値を書いたら、それぞれの「計」と足し算が
  合うか確かめ、合わなければ読み直す。溶存物質 = 陽イオン計 + 陰イオン計 + 非解離成分計、
  成分総計 = 溶存物質 + 溶存ガス成分計。
- 元号の日付は西暦に直す（令和7年4月23日 → 2025-04-23）。
- analyzed_on は「分析終了年月日」と明記された日付だけを使う。分析書右上の発行日・作成日や、
  「調査及び試験年月日」は入れない。「分析終了年月日」が読めなければ analyzed_on を省く。
- spring_quality は泉質名（例「単純温泉」「アルカリ性単純硫黄温泉」）、
  spring_quality_class は括弧内の分類（例「低張性弱アルカリ性高温泉」）。「冷鉱泉」などが
  泉質名の行と括弧内の両方に印字されている場合は、写真どおり両方へ入れる。
- 写真が不鮮明で全体的に自信が無ければ confidence を low、多少怪しい程度なら medium にし、
  notes に理由を日本語で書く。反射や見切れで読めなかった欄があれば notes に書く。
- indications / contraindications は泉質別適応症・泉質別禁忌症を列挙する。

出力は次の形の JSON だけを返してください。掲示に無いキーは省いてください（null や 0 で
埋めないこと）。

{{
  "is_composition": true,
  "springs": [{{
    "photo_indexes": [1],
    "confidence": "high",
    "spring_name": "4号源泉",
    "spring_quality": "アルカリ性単純硫黄温泉",
    "spring_quality_class": "低張性アルカリ性高温泉",
    "source_temp_c": 50.4,
    "use_temp_c": 42.0,
    "ph": 8.86,
    "ph_lab": 8.5,
    "yield_l_min": 60.2,
    "evaporation_residue_mg_kg": 283.0,
    "dissolved_solids_mg_kg": 287.8,
    "total_ingredients_mg_kg": 287.9,
    "cations": [{{"name": "ナトリウムイオン", "symbol": "Na+", "mg_kg": 70.3}}],
    "cations_total_mg_kg": 84.1,
    "anions": [{{"name": "硫酸イオン", "symbol": "SO42-", "mg_kg": 82.0}}],
    "anions_total_mg_kg": 155.7,
    "undissociated": [{{"name": "メタケイ酸", "symbol": "H2SiO3", "mg_kg": 46.2}}],
    "undissociated_total_mg_kg": 48.0,
    "dissolved_gas": [{{"name": "遊離硫化水素", "symbol": "H2S", "mg_kg": 0.1}}],
    "dissolved_gas_total_mg_kg": 0.1,
    "treatment": {{
      "kasui": {{"applied": false, "reason": "加水はしていません。"}},
      "kaon": {{"applied": true, "reason": "…"}},
      "junkan": {{"applied": true, "reason": "…"}},
      "shodoku": {{"applied": true, "reason": "…"}},
      "nyuyokuzai": {{"applied": false, "reason": "…"}}
    }},
    "indications": ["自律神経不安定症", "不眠症", "うつ状態"],
    "contraindications": [],
    "analyzed_on": "2024-06-07",
    "analyzer": "一般社団法人 上田薬剤師会",
    "analyzer_registration": "長野県第7号",
    "notes": "反射で源泉名が読めなかった"
  }}]
}}
"""

# 応答から採用するキー。response_schema による制約付きデコードは、掲示に無い数値項目で
# 桁が延々と伸びる縮退を起こしたため使っていない。代わりにプロンプトで形を示し、
# 受け取った側でキーを絞る。
ALLOWED_KEYS = {
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
}


def load_json(path, fallback=None):
    if not os.path.exists(path):
        return fallback
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def group_by_place(photos):
    """写真を施設ごとにまとめる（manifest の並び順を保つ）。"""
    groups = []
    index_by_fsq = {}
    for photo in photos:
        fsq_id = photo.get('fsq_id', '')
        if fsq_id not in index_by_fsq:
            index_by_fsq[fsq_id] = len(groups)
            groups.append({
                'fsq_id': fsq_id,
                'name': photo.get('place_name', ''),
                'composition_hint': photo.get('composition_hint', ''),
                'photos': [],
            })
        groups[index_by_fsq[fsq_id]]['photos'].append(photo)
    return groups


def build_parts(group):
    parts = [{"text": PROMPT.format(
        place_name=group['name'],
        count=len(group['photos']),
        composition_hint=group.get('composition_hint') or '（なし）',
    )}]
    for photo in group['photos']:
        with open(photo['file'], 'rb') as f:
            encoded = base64.b64encode(f.read()).decode('ascii')
        parts.append({"text": f"写真 #{photo['index']}"})
        parts.append({"inline_data": {"mime_type": "image/jpeg", "data": encoded}})
    return parts


class InfrastructureError(RuntimeError):
    """認証切れ・レート超過・通信断など、写真の中身とは無関係な失敗。

    どの写真を送っても同じように起きるので、試行回数には数えず実行ごと中止する。
    数えてしまうと、キーが切れている数日のあいだに読めるはずの写真まで
    「読めない写真」として引退してしまう。
    """


class ContentError(RuntimeError):
    """その写真を送る限り繰り返すとみられる失敗（安全フィルタ・不正なJSONなど）。

    試行回数に数え、上限に達したら以後は対象から外す。

    HTTPエラーはここに分類しない。鍵が無効なときの応答も 400 INVALID_ARGUMENT で、
    画像が不正なときと区別がつかないため。取り違えた場合の損害が非対称で、
    読めるはずの写真を引退させると永久に失われるのに対し、中止しすぎても
    ワークフローが目立って失敗するだけなので、安全な側に倒している。
    """


def call_gemini(api_key, model, parts):
    url = f"{API_ROOT}/{model}:generateContent"
    payload = {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {
            "temperature": 0,
            "response_mime_type": "application/json",
            "maxOutputTokens": MAX_OUTPUT_TOKENS,
        },
    }

    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(
                url,
                params={"key": api_key},
                json=payload,
                timeout=REQUEST_TIMEOUT,
            )
        except requests.RequestException as exc:
            last_error = str(exc)
        else:
            if response.status_code == 200:
                return response.json()

            last_error = f"HTTP {response.status_code}: {response.text[:300]}"
            # 429 と 5xx は一時的な混雑なので待って投げ直す。それ以外（鍵・モデル名・
            # 不正なリクエスト）は投げ直しても直らないので即座に中止する。
            if response.status_code != 429 and response.status_code < 500:
                raise InfrastructureError(last_error)

        wait = SLEEP_BETWEEN_CALLS * (2 ** attempt)
        print(f"  [Retry] {last_error} — {wait:.0f}秒待って再試行", file=sys.stderr)
        time.sleep(wait)

    raise InfrastructureError(last_error or "Gemini API 呼び出しに失敗しました")


def parse_response(body):
    candidates = body.get('candidates') or []
    if not candidates:
        feedback = body.get('promptFeedback') or {}
        raise ContentError(f"応答に candidates がありません: {feedback}")

    texts = [
        part['text']
        for part in (candidates[0].get('content') or {}).get('parts') or []
        if 'text' in part
    ]
    if not texts:
        finish = candidates[0].get('finishReason')
        raise ContentError(f"応答にテキストがありません（finishReason={finish}）")

    try:
        return json.loads(''.join(texts))
    except json.JSONDecodeError as exc:
        raise ContentError(f"応答をJSONとして読めません: {exc}") from exc


def clean_spring(raw, group):
    """API の源泉1件を extracted.json の形式に整える。"""
    valid_indexes = {photo['index'] for photo in group['photos']}
    indexes = [i for i in (raw.get('photo_indexes') or []) if i in valid_indexes]
    if not indexes:
        # 番号を返してこなかった場合は、その施設の写真すべてを出典として扱う
        indexes = sorted(valid_indexes)

    entry = {'photo_indexes': indexes}
    for key, value in raw.items():
        if key not in ALLOWED_KEYS:
            continue
        if value is None or value == [] or value == {} or value == '':
            continue
        entry[key] = value

    entry.setdefault('confidence', 'medium')
    return entry


def clean_springs(result, group):
    """複数源泉形式を採用し、旧来の単一源泉応答も受け入れる。"""
    raw_springs = result.get('springs')
    if not isinstance(raw_springs, list):
        raw_springs = [result]
    return [clean_spring(raw, group) for raw in raw_springs if isinstance(raw, dict)]


def apply_validation(entry, label):
    """検算に通らなければ confidence を下げて notes に理由を残す。"""
    issues = check_entry(entry)
    if not issues:
        return False

    reason = f"自動検算で合計が一致しませんでした（{describe(issues)}）。要再確認。"
    entry['confidence'] = 'low'
    entry['notes'] = f"{entry['notes']} {reason}" if entry.get('notes') else reason
    print(f"  [NG] {label}: {describe(issues)} → confidence を low にしました")
    return True


def main():
    parser = argparse.ArgumentParser(description="温泉分析書の写真を Gemini で書き起こす")
    parser.add_argument('--model', default=DEFAULT_MODEL, help=f"使用するモデル（既定: {DEFAULT_MODEL}）")
    parser.add_argument('--limit', type=int, help="先頭から指定件数の施設だけ処理する")
    parser.add_argument('--only', help="この fsq_id の施設だけ処理する")
    parser.add_argument('--output', default=EXTRACTED_JSON, help=f"書き出し先（既定: {EXTRACTED_JSON}）")
    parser.add_argument('--dry-run', action='store_true', help="書き込まずに結果だけ表示する")
    args = parser.parse_args()

    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        print("[Error] 環境変数 GEMINI_API_KEY が設定されていません。", file=sys.stderr)
        sys.exit(1)

    manifest = load_json(MANIFEST_JSON)
    if not manifest:
        print(f"[Error] {MANIFEST_JSON} がありません。先に prepare_onsen_composition.py を実行してください。", file=sys.stderr)
        sys.exit(1)

    photos = manifest.get('photos') or []
    # manifest の downloaded は「今回新たに取得したか」で、キャッシュ済みの写真は False。
    # 使えるかどうかはファイルの有無だけで判断する。
    photos = [photo for photo in photos if os.path.exists(photo.get('file') or '')]
    if not photos:
        print("[Error] manifest に使える写真がありません。prepare_onsen_composition.py を実行し直してください。", file=sys.stderr)
        sys.exit(1)
    groups = group_by_place(photos)
    if args.only:
        groups = [group for group in groups if group['fsq_id'] == args.only]
    if args.limit:
        groups = groups[:args.limit]

    print("=== 成分表を書き起こす ===")
    print(f"モデル: {args.model}")
    print(f"対象: {len(groups)}施設 / {sum(len(g['photos']) for g in groups)}枚")

    places = []
    skipped = 0
    flagged = 0
    failed_photos = []
    processed_indexes = []

    for position, group in enumerate(groups, start=1):
        head = f"[{position}/{len(groups)}] {group['name']}"

        if len(group['photos']) > MAX_PHOTOS_PER_REQUEST:
            print(f"{head} → 写真が多いため先頭{MAX_PHOTOS_PER_REQUEST}枚だけ送ります")
            group = {**group, 'photos': group['photos'][:MAX_PHOTOS_PER_REQUEST]}

        # 実際にモデルへ送った写真だけを申し送る。送らなかった写真まで merge が
        # 「成分表ではなかった」と確定させると、見てもいない分析書が失われる。
        indexes = [photo['index'] for photo in group['photos']]
        processed_indexes.extend(indexes)
        head = f"{head} (#{', #'.join(str(i) for i in indexes)})"

        try:
            body = call_gemini(api_key, args.model, build_parts(group))
            result = parse_response(body)
        except InfrastructureError as exc:
            # 鍵やモデル名、回線の問題。他の施設を試しても同じなので、書き込まずに中止する。
            print(f"{head} → 中止: {exc}", file=sys.stderr)
            print("[Error] API 側の問題とみられるため、extracted.json は更新しません。", file=sys.stderr)
            sys.exit(1)
        except ContentError as exc:
            failed_photos.extend({"index": index, "error": str(exc)[:200]} for index in indexes)
            print(f"{head} → 失敗: {exc}", file=sys.stderr)
            continue

        if not result.get('is_composition'):
            skipped += 1
            print(f"{head} → 成分表なし")
        else:
            springs = clean_springs(result, group)
            if not springs:
                skipped += 1
                print(f"{head} → 成分表なし")
                continue
            for spring in springs:
                quality = spring.get('spring_quality') or '泉質不明'
                spring_name = spring.get('spring_name') or '源泉名不明'
                print(f"{head} → {spring_name}: {quality}（confidence: {spring.get('confidence')}）")
                if apply_validation(spring, f"{group['name']} / {spring_name}"):
                    flagged += 1
            places.append({'springs': springs})

        if position < len(groups):
            time.sleep(SLEEP_BETWEEN_CALLS)

    failed = len(failed_photos)
    spring_count = sum(len(place['springs']) for place in places)
    print(f"成分表あり: {len(places)}施設・{spring_count}源泉 / 成分表なし: {skipped}施設 / 読めなかった写真: {failed}枚")
    if flagged:
        print(f"うち検算が合わなかったもの: {flagged}源泉（confidence: low）")

    payload = {"places": places, "processed_photo_indexes": sorted(set(processed_indexes))}
    if failed_photos:
        # merge 側がこの写真を「成分表ではなかった」と確定させないための申し送り。
        # merge が試行回数を数え、上限に達したら以後の対象から外す。
        payload["failed_photos"] = failed_photos

    if args.dry_run:
        print("--dry-run のため書き込みませんでした。")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write('\n')

    print(f"書き出し先: {args.output}")


if __name__ == "__main__":
    main()
