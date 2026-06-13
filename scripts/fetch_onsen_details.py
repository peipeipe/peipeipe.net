#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import argparse
from datetime import datetime, timezone

import yaml
import requests

# パスの定義
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_YML = os.path.join(BASE_DIR, 'astro', 'data', 'onsen_list.yml')
OUTPUT_JSON = os.path.join(BASE_DIR, 'astro', 'data', 'onsen_places.json')

# カテゴリで絞ると施設名検索を取り逃すことがあるため、デフォルトでは使わない。
# 必要な場合は FOURSQUARE_CATEGORIES にカンマ区切りのカテゴリIDを設定する。
DEFAULT_NEAR = "Japan"
PLACES_API_VERSION = "2025-02-05"
HOT_SPRING_CATEGORY_ID = "4bf58dd8d48988d160941735"
SEARCH_FIELDS = ",".join([
    "fsq_place_id",
    "name",
    "latitude",
    "longitude",
    "location",
    "link",
    "categories",
])

SEARCH_AREAS = [
    {"name": "札幌", "ll": "43.0618,141.3545", "radius": 90000},
    {"name": "函館", "ll": "41.7687,140.7288", "radius": 90000},
    {"name": "仙台", "ll": "38.2682,140.8694", "radius": 90000},
    {"name": "福島", "ll": "37.7608,140.4747", "radius": 90000},
    {"name": "東京", "ll": "35.6812,139.7671", "radius": 90000},
    {"name": "箱根・伊豆", "ll": "35.2335,139.1069", "radius": 90000},
    {"name": "長野", "ll": "36.6513,138.1810", "radius": 90000},
    {"name": "新潟", "ll": "37.9161,139.0364", "radius": 90000},
    {"name": "名古屋", "ll": "35.1815,136.9066", "radius": 90000},
    {"name": "金沢", "ll": "36.5613,136.6562", "radius": 90000},
    {"name": "大阪", "ll": "34.6937,135.5023", "radius": 90000},
    {"name": "鳥取", "ll": "35.5011,134.2351", "radius": 90000},
    {"name": "広島", "ll": "34.3853,132.4553", "radius": 90000},
    {"name": "松山", "ll": "33.8392,132.7657", "radius": 90000},
    {"name": "高知", "ll": "33.5597,133.5311", "radius": 90000},
    {"name": "福岡", "ll": "33.5902,130.4017", "radius": 90000},
    {"name": "熊本", "ll": "32.8031,130.7079", "radius": 90000},
    {"name": "鹿児島", "ll": "31.5966,130.5571", "radius": 90000},
    {"name": "沖縄", "ll": "26.2124,127.6809", "radius": 90000},
]

# APIキーがない場合のモック/フォールバックデータ
MOCK_COORDINATES = {
    "JFA夢フィールド 幕張温泉 湯楽の里": {
        "lat": 35.6372,
        "lng": 140.0381,
        "address": "千葉県千葉市美浜区美浜11",
        "foursquare_url": "https://foursquare.com/v/5ef9b0a701dfaa00085ec303",
        "photos": []
    },
    "ほったらかし温泉": {
        "lat": 35.7176,
        "lng": 138.6234,
        "address": "山梨県山梨市矢坪1669-18",
        "foursquare_url": "https://foursquare.com/v/4b79c3bdf964a520440b2fe3",
        "photos": []
    }
}

def load_env_file(filepath):
    """Load simple KEY=VALUE pairs from .env without overwriting existing env vars."""
    if not os.path.exists(filepath):
        return

    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue

            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value

def load_yaml(filepath):
    """YAMLファイルを読み込む"""
    if not os.path.exists(filepath):
        print(f"[Error] YAML file not found: {filepath}", file=sys.stderr)
        return []
    with open(filepath, 'r', encoding='utf-8') as f:
        try:
            return yaml.safe_load(f) or []
        except yaml.YAMLError as e:
            print(f"[Error] Failed to parse YAML: {e}", file=sys.stderr)
            return []

def load_existing_json(filepath):
    """既存のJSONキャッシュを読み込む"""
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # リスト形式を名前キーの辞書に変換してキャッシュとして使いやすくする
                return {item['name']: item for item in data if 'name' in item}
        except Exception as e:
            print(f"[Warning] Failed to load existing JSON cache: {e}", file=sys.stderr)
    return {}

def search_foursquare_place(name, api_key, item=None):
    """Foursquare Places API を使用して場所を検索する"""
    categories = os.environ.get('FOURSQUARE_CATEGORIES', '').strip()
    url = "https://places-api.foursquare.com/places/search"
    params = {
        "query": name,
        "limit": 1,
        "fields": SEARCH_FIELDS,
    }
    lat_hint, lng_hint = get_location_hint(name, item or {})
    if lat_hint is not None and lng_hint is not None:
        params["ll"] = f"{lat_hint},{lng_hint}"
        params["radius"] = 10000
    else:
        params["near"] = DEFAULT_NEAR

    if categories:
        params["categoryId"] = categories
    
    try:
        response = request_foursquare(url, api_key, params=params)
        if response.status_code == 200:
            payload = response.json()
            results = payload.get('results') or payload.get('places') or payload.get('venues') or []
            if results:
                place = results[0]
                address = format_location(place.get('location', {}))
                
                fsq_id = place.get('fsq_place_id') or place.get('fsq_id')
                foursquare_url = normalize_foursquare_url(
                    place.get('link') or (f"https://foursquare.com/v/{fsq_id}" if fsq_id else "")
                )
                
                return {
                    "fsq_id": fsq_id,
                    "lat": place.get('latitude'),
                    "lng": place.get('longitude'),
                    "address": address,
                    "foursquare_url": foursquare_url,
                    "photos": normalize_photos(place.get('photos', []))
                }
        else:
            print(f"[Warning] Foursquare Place Search failed for '{name}': HTTP {response.status_code}", file=sys.stderr)
            if response.status_code == 401:
                print(
                    "          新しいPlaces APIではService API Keyが必要です。"
                    "Foursquare Developer ConsoleでService API Keyを作成してFOURSQUARE_API_KEYに設定してください。",
                    file=sys.stderr
                )
    except Exception as e:
        print(f"[Warning] Foursquare API Request failed: {e}", file=sys.stderr)
    
    return None

def search_foursquare_area(api_key, query, area, limit=20, category_ids=""):
    """指定エリア内のFoursquare検索結果を一覧用データとして返す"""
    url = "https://places-api.foursquare.com/places/search"
    params = {
        "query": query,
        "ll": area["ll"],
        "radius": area["radius"],
        "limit": limit,
        "fields": SEARCH_FIELDS,
    }
    if category_ids:
        params["categoryId"] = category_ids

    try:
        response = request_foursquare(url, api_key, params=params)
        if response.status_code == 200:
            return response.json().get('results', [])

        print(
            f"[Warning] Foursquare area search failed for {area['name']}: HTTP {response.status_code}",
            file=sys.stderr
        )
        if response.status_code == 429:
            print("          API credits/rate limitに達しています。取得済み分だけ保存します。", file=sys.stderr)
    except Exception as e:
        print(f"[Warning] Foursquare area search failed for {area['name']}: {e}", file=sys.stderr)

    return []

def fetch_foursquare_onsen_list(api_key, query="温泉", per_area_limit=20, category_ids=HOT_SPRING_CATEGORY_ID):
    """Foursquare検索から全国の温泉候補一覧を生成する"""
    places_by_id = {}
    category_filter = {
        category_id.strip()
        for category_id in (category_ids or "").split(',')
        if category_id.strip()
    }

    for area in SEARCH_AREAS:
        print(f"検索中: {area['name']} ...")
        for place in search_foursquare_area(api_key, query, area, limit=per_area_limit, category_ids=category_ids):
            fsq_id = place.get('fsq_place_id') or place.get('fsq_id')
            lat = place.get('latitude')
            lng = place.get('longitude')
            if not fsq_id or lat is None or lng is None:
                continue
            if category_filter and not place_has_category(place, category_filter):
                continue

            name = place.get('name') or ""
            address = format_location(place.get('location', {}))
            places_by_id[fsq_id] = {
                "name": name,
                "user_comment": "",
                "date": "",
                "lat": lat,
                "lng": lng,
                "address": address,
                "foursquare_url": normalize_foursquare_url(place.get('link') or f"/places/{fsq_id}"),
                "photos": [],
                "categories": [
                    category.get('name')
                    for category in place.get('categories', [])
                    if isinstance(category, dict) and category.get('name')
                ],
                "data_source": "foursquare_search",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }

    return sorted(
        places_by_id.values(),
        key=lambda item: (item.get('address', ''), item.get('name', ''))
    )

def place_has_category(place, category_filter):
    """API側のcategoryId指定が効かない場合に備え、レスポンス側でも絞り込む"""
    for category in place.get('categories', []):
        if not isinstance(category, dict):
            continue
        category_id = category.get('fsq_category_id') or category.get('id')
        if category_id in category_filter:
            return True
    return False

def get_location_hint(name, item):
    """YAMLまたはフォールバック座標から検索範囲のヒントを得る"""
    lat = item.get('lat')
    lng = item.get('lng')
    if lat is not None and lng is not None:
        return lat, lng

    mock = MOCK_COORDINATES.get(name)
    if mock:
        return mock.get('lat'), mock.get('lng')

    return None, None

def format_location(location):
    """Foursquareのlocationオブジェクトから表示用住所を組み立てる"""
    if not isinstance(location, dict):
        return ""

    for key in ('formatted_address', 'formattedAddress'):
        value = location.get(key)
        if isinstance(value, str) and value:
            return value
        if isinstance(value, list) and value:
            return " ".join(str(part) for part in value if part)

    parts = [
        location.get('address'),
        location.get('address_extended'),
        location.get('locality'),
        location.get('region'),
        location.get('postcode'),
    ]
    return " ".join(str(part) for part in parts if part)

def normalize_photos(raw_photos, size="500x300"):
    """Foursquare写真レスポンスをカード用URL配列に変換する"""
    photos = []
    if isinstance(raw_photos, dict):
        raw_photos = raw_photos.get('items') or raw_photos.get('photos') or raw_photos.get('results') or []
    if not isinstance(raw_photos, list):
        return photos

    for photo in raw_photos:
        if isinstance(photo, str):
            photos.append(photo)
            continue
        if not isinstance(photo, dict):
            continue

        url = photo.get('url')
        prefix = photo.get('prefix')
        suffix = photo.get('suffix')
        if url:
            photos.append(url)
        elif prefix and suffix:
            photos.append(f"{prefix}{size}{suffix}")

    return photos

def normalize_foursquare_url(url):
    """APIの相対リンクをブラウザで開けるURLに変換する"""
    if not url:
        return ""
    if url.startswith("http://") or url.startswith("https://"):
        return url
    if url.startswith("/"):
        return f"https://foursquare.com{url}"
    return url

def fetch_place_photos(fsq_id, api_key, limit=3):
    """Foursquare Places API から場所の写真を取得する"""
    if not fsq_id:
        return []
        
    url = f"https://places-api.foursquare.com/places/{fsq_id}"
    params = {
        "fields": "photos"
    }
    
    try:
        response = request_foursquare(url, api_key, params=params)
        if response.status_code == 200:
            photos = normalize_photos(response.json().get('photos', []))
            return photos[:limit]
        else:
            print(f"[Warning] Foursquare Photos failed for ID {fsq_id}: HTTP {response.status_code}", file=sys.stderr)
            if response.status_code == 429:
                print(
                    "          写真はPremium/有料枠の対象になっている可能性があります。"
                    "位置情報のみ保存して続行します。",
                    file=sys.stderr
                )
    except Exception as e:
        print(f"[Warning] Foursquare Photos Request failed: {e}", file=sys.stderr)
        
    return []

def request_foursquare(url, api_key, params=None):
    """新APIのService API Key形式を優先し、旧形式キーもフォールバックで試す。"""
    base_headers = {
        "accept": "application/json",
        "X-places-api-version": PLACES_API_VERSION
    }
    auth_values = [f"Bearer {api_key}", api_key]
    response = None

    for authorization in auth_values:
        headers = dict(base_headers)
        headers["Authorization"] = authorization
        response = requests.get(url, headers=headers, params=params, timeout=10)
        if response.status_code != 401:
            return response

    return response

def build_parser():
    parser = argparse.ArgumentParser(
        description="Foursquare APIから温泉の位置情報と写真を取得してサイト用data JSONを生成します。"
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="既存のJSONキャッシュがあってもFoursquare APIから再取得します。"
    )
    parser.add_argument(
        "--limit-photos",
        type=int,
        default=3,
        help="各温泉で取得する写真枚数。デフォルトは3枚です。"
    )
    parser.add_argument(
        "--source",
        choices=("yaml", "foursquare"),
        default="yaml",
        help="yaml: astro/data/onsen_list.ymlを補完します。foursquare: Foursquare検索から一覧を生成します。"
    )
    parser.add_argument(
        "--query",
        default="温泉",
        help="--source foursquare で使う検索語。デフォルトは「温泉」です。"
    )
    parser.add_argument(
        "--category-ids",
        default=os.environ.get('FOURSQUARE_CATEGORIES', HOT_SPRING_CATEGORY_ID),
        help="--source foursquare で残すFoursquareカテゴリID。デフォルトはHot Springです。空文字ならカテゴリで絞りません。"
    )
    parser.add_argument(
        "--per-area-limit",
        type=int,
        default=20,
        help="--source foursquare で各エリアから取得する最大件数。デフォルトは20件です。"
    )
    return parser

def main():
    args = build_parser().parse_args()
    load_env_file(os.path.join(BASE_DIR, '.env'))
    api_key = os.environ.get('FOURSQUARE_API_KEY')

    print("=== 温泉詳細情報の取得スクリプト実行 ===")

    if args.source == "foursquare":
        if not api_key:
            print("[Error] --source foursquare には FOURSQUARE_API_KEY が必要です。", file=sys.stderr)
            sys.exit(1)

        results = fetch_foursquare_onsen_list(
            api_key,
            query=args.query,
            per_area_limit=args.per_area_limit,
            category_ids=args.category_ids,
        )
        os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
        with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"\n完了! Foursquare検索から {len(results)}件の温泉データを {OUTPUT_JSON} に書き出しました。")
        return
    
    # 1. データの読み込み
    yml_data = load_yaml(INPUT_YML)
    if not yml_data:
        print("[Error] 対象の温泉リストがありません。処理を終了します。", file=sys.stderr)
        sys.exit(1)
        
    cache = load_existing_json(OUTPUT_JSON)
    results = []
    
    if not api_key:
        print("[Notice] FOURSQUARE_API_KEY が環境変数に設定されていません。")
        print("         キャッシュまたはモックデータを使用してフォールバックデータを生成します。")
        
    # 2. 各温泉のデータを構築
    for item in yml_data:
        name = item.get('name')
        if not name:
            continue
            
        print(f"処理中: {name} ...")
        
        cached = cache.get(name)
        should_use_cache = (
            cached
            and not args.refresh
            and (not api_key or cached.get('data_source') == 'foursquare')
        )

        # 既存のキャッシュがあれば再利用（API呼び出しを節約）
        if should_use_cache:
            # ユーザーのコメントや日付が更新されている可能性があるのでマージする
            place_info = cached
            place_info['user_comment'] = item.get('comment', '')
            place_info['date'] = str(item.get('date', ''))
            print("  -> キャッシュからデータを復元しました。")
            results.append(place_info)
            continue
            
        place_data = {
            "name": name,
            "user_comment": item.get('comment', ''),
            "date": str(item.get('date', ''))
        }
        
        # Foursquare API を使って検索
        success = False
        if api_key:
            search_result = search_foursquare_place(name, api_key, item)
            if search_result:
                place_data.update({
                    "lat": search_result["lat"],
                    "lng": search_result["lng"],
                    "address": search_result["address"],
                    "foursquare_url": search_result["foursquare_url"]
                })
                
                # 写真も取得
                photos = search_result.get("photos", [])
                if len(photos) < args.limit_photos:
                    photos = photos + fetch_place_photos(search_result["fsq_id"], api_key, limit=args.limit_photos)
                photos = list(dict.fromkeys(photos))[:args.limit_photos]
                place_data["photos"] = photos
                place_data["data_source"] = "foursquare"
                place_data["updated_at"] = datetime.now(timezone.utc).isoformat()
                print(f"  -> Foursquare APIからデータを取得しました (写真: {len(photos)}枚)")
                success = True
                
        # APIキーがない、またはAPI取得に失敗した場合はモックデータかダミーでフォールバック
        if not success:
            if name in MOCK_COORDINATES:
                mock = MOCK_COORDINATES[name]
                place_data.update({
                    "lat": mock["lat"],
                    "lng": mock["lng"],
                    "address": mock["address"],
                    "foursquare_url": mock["foursquare_url"],
                    "photos": mock["photos"],
                    "data_source": "sample"
                })
                print("  -> サンプル・モックデータでフォールバックしました。")
            else:
                place_data.update({
                    "lat": None,
                    "lng": None,
                    "address": "住所情報なし（APIキーを設定して取得してください）",
                    "foursquare_url": "",
                    "photos": [],
                    "data_source": "missing"
                })
                print("  -> APIキー未設定または取得失敗のため、位置情報なしで保存しました。")
                
        results.append(place_data)
        
    # 3. JSONファイルへ書き出し
    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
        
    print(f"\n完了! {len(results)}件の温泉データを {OUTPUT_JSON} に書き出しました。")

if __name__ == "__main__":
    main()
