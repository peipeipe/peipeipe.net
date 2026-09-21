#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import re
import sys
from datetime import datetime, timezone

import requests

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASTRO_DIR = os.path.join(BASE_DIR, 'astro')
OUTPUT_ONSEN_JSON = os.path.join(ASTRO_DIR, 'data', 'onsen_places.json')
OUTPUT_PLACES_JSON = os.path.join(ASTRO_DIR, 'data', 'places.json')

# Foursquare v2 category IDs (see https://developer.foursquare.com/docs/categories)
HOT_SPRING_CATEGORY_ID = "4bf58dd8d48988d160941735"  # Hot Spring / 温泉
BATH_HOUSE_CATEGORY_ID = "52e81612bcbc57f1066b7a27"  # Bath House / 銭湯
SPA_CATEGORY_ID = "4bf58dd8d48988d1ed941735"  # Spa（THE SPA 西新井など）
SAUNA_CATEGORY_ID = "58daa1558bbb0b01f18ec1ae"  # Saunas / Steam Rooms

DEFAULT_ONSEN_CATEGORY_IDS = ",".join([
    HOT_SPRING_CATEGORY_ID,
    BATH_HOUSE_CATEGORY_ID,
    SPA_CATEGORY_ID,
    SAUNA_CATEGORY_ID,
])

# チェックインコメントに「成分表: 源泉A / 源泉B」と書くと、写真解析へ補助情報として渡す。
# 通常コメントと混同しないよう行頭のマーカーだけを認識する。
COMPOSITION_HINT_PATTERN = re.compile(r"^成分表[：:]\s*(.+)$", re.MULTILINE)


# カテゴリ未設定・誤分類の施設向け（チェックイン履歴内のみ）
ONSEN_VENUE_NAME_PATTERN = re.compile(
    r"(温泉|銭湯|岩盤浴|スーパー銭湯|日帰り温泉|温泉郷|の湯|湯屋|湯処|湯楽|湯快|"
    r"竜泉寺の湯|極楽湯|カプセルサウナ|サウナリゾート|サウナ&|&サウナ|スパ&サウナ)"
    r"|サウナ"
    r"|(?:THE\s+)?SPA\b"
    r"|\bSAUNA\b",
    re.IGNORECASE,
)

# 明らかに温泉でないスポットのfsq_idブラックリスト
NOT_ONSEN_FSQ_IDS = set([
    # スパニッシュダイニング Rico
    "563b327fcd109c48c629be02",
    # Bar de España EL CERO UNO
    "4dd4f99c7d8b194450ce02ed",
    # belle salle (ベルサール新宿セントラルパーク)
    "4b8db0d2f964a520ce0833e3",
    # Belle Salle Shibuya. (ベルサール渋谷ガーデン)
    "4fcaa46ee4b0f59887a4a641",
    # その他 Event Space 系
    "5192018a2fc6103965c32393",
    # 必要に応じて追加
])

ONSEN_CATEGORY_NAME_PATTERN = re.compile(
    r"温泉|銭湯|浴場|サウナ|スパ|\b(?:spa|bath(?: house)?|hot springs?|saunas?|steam rooms?)\b",
    re.IGNORECASE,
)
# コメントは補助的な判定。「温泉なし」など明示的な否定は対象にしない。
ONSEN_COMMENT_PATTERN = re.compile(r"温泉|源泉|泉質|成分表|銭湯|サウナ|岩盤浴")
ONSEN_COMMENT_NEGATIVE_PATTERN = re.compile(
    r"(?:温泉|源泉|泉質|成分表|銭湯|サウナ|岩盤浴)"
    r"\s*(?:ではない|じゃない|ではなく|じゃなく|(?:は|が)?\s*(?:なし|無し|ない|無い|ありません))"
)
LEGACY_GROUP_FIELDS = ('category_group', 'category_label', 'category_emoji', 'category_color')

API_URL = "https://api.foursquare.com/v2/users/self/checkins"


def load_env_file(filepath):
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


def get_category_filter():
    raw = os.environ.get('FOURSQUARE_CHECKIN_CATEGORY_IDS', DEFAULT_ONSEN_CATEGORY_IDS)
    return {item.strip() for item in raw.split(',') if item.strip()}


def name_match_enabled():
    return os.environ.get('FOURSQUARE_CHECKIN_NAME_MATCH', '1') != '0'


def venue_name_matches_onsen(name):
    return bool(name and ONSEN_VENUE_NAME_PATTERN.search(name))


def category_label_matches_onsen(category):
    label = f"{category.get('name', '')} {category.get('shortName', '')}"
    return bool(ONSEN_CATEGORY_NAME_PATTERN.search(label))


def venue_is_onsen(venue, category_ids):
    if venue_has_category(venue, category_ids):
        return True
    if not name_match_enabled():
        return False
    if venue_name_matches_onsen(venue.get('name', '')):
        return True
    for category in venue.get('categories', []):
        if category_label_matches_onsen(category):
            return True
    return False


def comment_matches_onsen(comment):
    comment = ONSEN_COMMENT_NEGATIVE_PATTERN.sub('', comment)
    return bool(ONSEN_COMMENT_PATTERN.search(comment))


def fetch_checkins(oauth_token, limit=250, max_pages=20):
    checkins = []
    version = os.environ.get('FOURSQUARE_V2_VERSION', '20260523')

    for page in range(max_pages):
        offset = page * limit
        params = {
            'oauth_token': oauth_token,
            'v': version,
            'limit': limit,
            'offset': offset,
        }
        # 言語未指定による施設名・カテゴリ名の英日切り替わりを防ぐ。
        # https://docs.foursquare.com/developer/reference/v2-localization
        response = requests.get(
            API_URL, params=params, headers={'Accept-Language': 'ja'}, timeout=20,
        )
        if response.status_code != 200:
            print(f"[Error] Foursquare checkins request failed: HTTP {response.status_code}", file=sys.stderr)
            print(response.text[:1000], file=sys.stderr)
            sys.exit(1)

        payload = response.json()
        meta = payload.get('meta', {})
        if meta.get('code') != 200:
            print(f"[Error] Foursquare API error: {meta}", file=sys.stderr)
            sys.exit(1)

        items = payload.get('response', {}).get('checkins', {}).get('items', [])
        if not items:
            break

        checkins.extend(items)
        if len(items) < limit:
            break

    return checkins


def venue_has_category(venue, category_ids):
    for category in venue.get('categories', []):
        if category.get('id') in category_ids:
            return True
    return False


def format_address(location):
    formatted = location.get('formattedAddress')
    if isinstance(formatted, list) and formatted:
        return ", ".join(part for part in formatted if part)
    if isinstance(formatted, str) and formatted:
        return formatted

    parts = [
        location.get('address'),
        location.get('city'),
        location.get('state'),
        location.get('postalCode'),
    ]
    return ", ".join(part for part in parts if part)


def checkin_time(checkin):
    created_at = checkin.get('createdAt')
    if not created_at:
        return None
    return datetime.fromtimestamp(created_at, tz=timezone.utc)


def photo_display_size():
    return os.environ.get('FOURSQUARE_CHECKIN_PHOTO_SIZE', '500x300')


def photos_per_place_limit():
    """1施設あたりに残す写真の枚数。既定は無制限（None）。

    枚数を絞ると古い写真が押し出され、成分表を撮った写真が
    onsen_places.json から消えて解析対象から漏れる。制限したいときだけ
    FOURSQUARE_CHECKIN_PHOTOS_PER_PLACE に1以上を設定する。
    """
    raw = os.environ.get('FOURSQUARE_CHECKIN_PHOTOS_PER_PLACE', '')
    try:
        limit = int(raw)
    except ValueError:
        return None
    return limit if limit > 0 else None


def photo_url_from_item(photo, size=None):
    """v2 checkin photo object → 表示用 URL（施設 Photos API は使わない）"""
    if not isinstance(photo, dict):
        return None

    size = size or photo_display_size()
    url = photo.get('url')
    if url:
        return url

    prefix = photo.get('prefix')
    suffix = photo.get('suffix')
    if prefix and suffix:
        return f"{prefix}{size}{suffix}"

    sizes = photo.get('sizes') or {}
    size_items = sizes.get('items') if isinstance(sizes, dict) else None
    if isinstance(size_items, list) and size_items:
        best = max(size_items, key=lambda item: item.get('width', 0) or 0)
        return best.get('url')

    return None


def normalize_checkin_photos(raw_photos, size=None):
    """checkin.photos をカード用 URL 配列に変換する"""
    size = size or photo_display_size()
    urls = []

    if isinstance(raw_photos, dict):
        raw_photos = raw_photos.get('items') or []
    if not isinstance(raw_photos, list):
        return urls

    for photo in raw_photos:
        if isinstance(photo, str):
            urls.append(photo)
            continue
        url = photo_url_from_item(photo, size=size)
        if url:
            urls.append(url)

    return urls


def extract_checkin_photos(checkin):
    return normalize_checkin_photos(checkin.get('photos'))


def extract_checkin_shout(checkin):
    """Swarm チェックイン時のコメント（API では shout）"""
    shout = checkin.get('shout')
    if not isinstance(shout, str):
        return ""
    return shout.strip()


def extract_composition_hint(shout):
    """「成分表: ...」形式のチェックインコメントから解析ヒントを取り出す。"""
    if not shout:
        return ""
    match = COMPOSITION_HINT_PATTERN.search(shout)
    return match.group(1).strip() if match else ""


def update_user_comment(place, shout, is_latest):
    """最新の shout を優先し、なければ過去チェックインから補完する"""
    if not shout:
        return
    if is_latest or not place.get('user_comment'):
        place['user_comment'] = shout


def update_composition_hint(place, shout, is_latest):
    hint = extract_composition_hint(shout)
    if hint and (is_latest or not place.get('composition_hint')):
        place['composition_hint'] = hint


def merge_photo_urls(existing, new_urls, limit, prepend=False):
    """URL の重複を除いてまとめる（limit が None なら枚数制限なし）"""
    ordered = (new_urls + existing) if prepend else (existing + new_urls)
    merged = []
    seen = set()

    for url in ordered:
        if not url or url in seen:
            continue
        seen.add(url)
        merged.append(url)
        if limit is not None and len(merged) >= limit:
            break

    return merged


def load_existing_places(path):
    """前回書き出した JSON を fsq_id 辞書で読み込む（無ければ空）"""
    if not os.path.exists(path):
        return {}

    try:
        with open(path, 'r', encoding='utf-8') as f:
            items = json.load(f)
    except (json.JSONDecodeError, OSError) as error:
        print(f"[Warn] 既存データを読めませんでした: {path} ({error})", file=sys.stderr)
        return {}

    if not isinstance(items, list):
        return {}

    return {
        item['fsq_id']: item
        for item in items
        if isinstance(item, dict) and item.get('fsq_id')
    }


def apply_name_override(place):
    """手動で name_override を書いた施設は API 側のリネームを無視する"""
    override = place.get('name_override')
    if isinstance(override, str) and override.strip():
        place['name'] = override.strip()
    return place


def merge_place(existing, fresh, photo_limit):
    """既存レコードに今回の取得結果を重ねる（履歴側の情報は捨てない）"""
    fresh_last = fresh.get('last_checkin_at', '')
    existing_last = existing.get('last_checkin_at', '')

    # 新しいチェックインがあるときだけ表示用の属性を差し替える
    merged = dict(fresh) if fresh_last >= existing_last else dict(existing)

    merged['photos'] = merge_photo_urls(
        existing.get('photos', []),
        fresh.get('photos', []),
        photo_limit,
        prepend=fresh_last >= existing_last,
    )
    merged['checkin_count'] = max(
        fresh.get('checkin_count', 0),
        existing.get('checkin_count', 0),
    )
    firsts = [
        value
        for value in (fresh.get('first_checkin_at'), existing.get('first_checkin_at'))
        if value
    ]
    merged['first_checkin_at'] = min(firsts) if firsts else ''
    merged['last_checkin_at'] = max(fresh_last, existing_last)

    if not merged.get('user_comment'):
        merged['user_comment'] = existing.get('user_comment', '') or fresh.get('user_comment', '')
    if not merged.get('composition_hint'):
        merged['composition_hint'] = existing.get('composition_hint', '') or fresh.get('composition_hint', '')

    if existing.get('name_override'):
        merged['name_override'] = existing['name_override']

    return apply_name_override(merged)


def merge_with_existing(fresh_places, existing_by_id, photo_limit):
    """API に出てこなくなった施設を残したままマージする

    Foursquare 側の venue 削除や、チェックイン履歴のページ上限で古い訪問が
    取得範囲から外れても、一度記録した場所は JSON から消さない。
    """
    merged = {}
    kept = 0

    for place in fresh_places:
        venue_id = place['fsq_id']
        existing = existing_by_id.get(venue_id)
        merged[venue_id] = merge_place(existing, place, photo_limit) if existing else apply_name_override(place)

    for venue_id, place in existing_by_id.items():
        if venue_id in merged:
            continue
        merged[venue_id] = apply_name_override(dict(place))
        kept += 1

    for place in merged.values():
        for field in LEGACY_GROUP_FIELDS:
            place.pop(field, None)

    ordered = sorted(
        merged.values(),
        key=lambda item: item.get('last_checkin_at', ''),
        reverse=True,
    )
    return ordered, kept


def build_places_from_checkins(checkins, category_ids, onsen_only=False):
    places = {}
    photo_limit = photos_per_place_limit()
    # いずれかの訪問で温泉と分かれば、その施設の全訪問・写真を集約する。
    onsen_venue_ids = set()
    if onsen_only:
        for checkin in checkins:
            venue = checkin.get('venue') or {}
            venue_id = venue.get('id')
            if venue_id and venue_id not in NOT_ONSEN_FSQ_IDS and (
                venue_is_onsen(venue, category_ids)
                or comment_matches_onsen(extract_checkin_shout(checkin))
            ):
                onsen_venue_ids.add(venue_id)

    for checkin in checkins:
        venue = checkin.get('venue') or {}
        venue_id = venue.get('id')
        location = venue.get('location') or {}
        lat = location.get('lat')
        lng = location.get('lng')

        if not venue_id or lat is None or lng is None:
            continue

        if onsen_only and venue_id not in onsen_venue_ids:
            continue

        visited_at = checkin_time(checkin)
        visited_iso = visited_at.isoformat() if visited_at else ""
        visited_date = visited_at.astimezone().date().isoformat() if visited_at else ""
        checkin_photos = extract_checkin_photos(checkin)
        checkin_shout = extract_checkin_shout(checkin)

        existing = places.get(venue_id)
        if existing:
            existing['checkin_count'] += 1
            is_latest = visited_iso and visited_iso > existing.get('last_checkin_at', '')
            if is_latest:
                existing['last_checkin_at'] = visited_iso
                existing['date'] = visited_date
                existing['photos'] = merge_photo_urls(
                    existing.get('photos', []),
                    checkin_photos,
                    photo_limit,
                    prepend=True,
                )
            elif checkin_photos:
                existing['photos'] = merge_photo_urls(
                    existing.get('photos', []),
                    checkin_photos,
                    photo_limit,
                    prepend=False,
                )
            update_user_comment(existing, checkin_shout, is_latest)
            update_composition_hint(existing, checkin_shout, is_latest)
            if visited_iso and visited_iso < existing.get('first_checkin_at', visited_iso):
                existing['first_checkin_at'] = visited_iso
            continue

        places[venue_id] = {
            "name": venue.get('name', ''),
            "user_comment": checkin_shout,
            "date": visited_date,
            "lat": lat,
            "lng": lng,
            "address": format_address(location),
            "foursquare_url": venue.get('canonicalUrl') or f"https://foursquare.com/v/{venue_id}",
            "photos": checkin_photos[:photo_limit] if photo_limit else list(checkin_photos),
            "categories": [
                category.get('name')
                for category in venue.get('categories', [])
                if category.get('name')
            ],
            "data_source": "foursquare_checkin",
            "fsq_id": venue_id,
            "checkin_count": 1,
            "first_checkin_at": visited_iso,
            "last_checkin_at": visited_iso,
        }
        composition_hint = extract_composition_hint(checkin_shout)
        if composition_hint:
            places[venue_id]['composition_hint'] = composition_hint

    return sorted(
        places.values(),
        key=lambda item: item.get('last_checkin_at', ''),
        reverse=True,
    )


def main():
    load_env_file(os.path.join(BASE_DIR, '.env'))
    oauth_token = os.environ.get('FOURSQUARE_OAUTH_TOKEN')
    if not oauth_token:
        print("[Error] FOURSQUARE_OAUTH_TOKEN is required.", file=sys.stderr)
        sys.exit(1)

    limit = int(os.environ.get('FOURSQUARE_CHECKIN_LIMIT', '250'))
    max_pages = int(os.environ.get('FOURSQUARE_CHECKIN_MAX_PAGES', '40'))
    category_ids = get_category_filter()
    photo_limit = photos_per_place_limit()

    print("=== Foursquareチェックインから温泉リストを更新 ===")
    checkins = fetch_checkins(oauth_token, limit=limit, max_pages=max_pages)
    if len(checkins) >= limit * max_pages:
        print(
            f"[Warn] 取得件数がページ上限({limit * max_pages}件)に達しました。"
            "FOURSQUARE_CHECKIN_MAX_PAGES を増やしてください。",
            file=sys.stderr,
        )

    places, kept_places = merge_with_existing(
        build_places_from_checkins(checkins, category_ids, onsen_only=False),
        load_existing_places(OUTPUT_PLACES_JSON),
        photo_limit,
    )
    onsen_places, kept_onsen = merge_with_existing(
        build_places_from_checkins(checkins, category_ids, onsen_only=True),
        load_existing_places(OUTPUT_ONSEN_JSON),
        photo_limit,
    )

    os.makedirs(os.path.dirname(OUTPUT_PLACES_JSON), exist_ok=True)
    with open(OUTPUT_PLACES_JSON, 'w', encoding='utf-8') as f:
        json.dump(places, f, ensure_ascii=False, indent=2)
        f.write('\n')

    with open(OUTPUT_ONSEN_JSON, 'w', encoding='utf-8') as f:
        json.dump(onsen_places, f, ensure_ascii=False, indent=2)
        f.write('\n')

    with_photos = sum(1 for place in onsen_places if place.get('photos'))
    with_comments = sum(1 for place in onsen_places if place.get('user_comment'))

    print(f"取得チェックイン: {len(checkins)}件")
    print(f"全スポット: {len(places)}件（うち今回のAPIに無く既存から保持: {kept_places}件）")
    print(f"温泉対象: {len(onsen_places)}件（うち既存から保持: {kept_onsen}件）")
    print(f"温泉写真あり: {with_photos}件")
    print(f"温泉コメントあり: {with_comments}件")
    print(f"書き出し先: {OUTPUT_PLACES_JSON}")
    print(f"書き出し先: {OUTPUT_ONSEN_JSON}")


if __name__ == "__main__":
    main()
