#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import re
import sys
from datetime import datetime, timezone

import requests

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_JSON = os.path.join(BASE_DIR, '_data', 'onsen_places.json')

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

# カテゴリ未設定・誤分類の施設向け（チェックイン履歴内のみ）
ONSEN_VENUE_NAME_PATTERN = re.compile(
    r"(温泉|銭湯|岩盤浴|スーパー銭湯|日帰り温泉|温泉郷|の湯|湯屋|湯処|湯楽|湯快|"
    r"竜泉寺の湯|極楽湯|カプセルサウナ|サウナリゾート|サウナ&|&サウナ|スパ&サウナ)"
    r"|サウナ"
    r"|(?:THE\s+)?SPA\b"
    r"|\bSAUNA\b",
    re.IGNORECASE,
)

ONSEN_CATEGORY_NAME_HINTS = (
    "温泉", "銭湯", "サウナ", "Spa", "Bath", "Hot Spring", "Sauna", "Steam",
)

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
    return any(hint in label for hint in ONSEN_CATEGORY_NAME_HINTS)


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
        response = requests.get(API_URL, params=params, timeout=20)
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
    return max(1, int(os.environ.get('FOURSQUARE_CHECKIN_PHOTOS_PER_PLACE', '5')))


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


def merge_photo_urls(existing, new_urls, limit, prepend=False):
    """URL の重複を除き、施設ごとの上限枚数までまとめる"""
    ordered = (new_urls + existing) if prepend else (existing + new_urls)
    merged = []
    seen = set()

    for url in ordered:
        if not url or url in seen:
            continue
        seen.add(url)
        merged.append(url)
        if len(merged) >= limit:
            break

    return merged


def build_places_from_checkins(checkins, category_ids):
    places = {}
    photo_limit = photos_per_place_limit()

    for checkin in checkins:
        venue = checkin.get('venue') or {}
        venue_id = venue.get('id')
        location = venue.get('location') or {}
        lat = location.get('lat')
        lng = location.get('lng')

        if not venue_id or lat is None or lng is None:
            continue
        if not venue_is_onsen(venue, category_ids):
            continue

        visited_at = checkin_time(checkin)
        visited_iso = visited_at.isoformat() if visited_at else ""
        visited_date = visited_at.astimezone().date().isoformat() if visited_at else ""
        checkin_photos = extract_checkin_photos(checkin)

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
            if visited_iso and visited_iso < existing.get('first_checkin_at', visited_iso):
                existing['first_checkin_at'] = visited_iso
            continue

        places[venue_id] = {
            "name": venue.get('name', ''),
            "user_comment": "",
            "date": visited_date,
            "lat": lat,
            "lng": lng,
            "address": format_address(location),
            "foursquare_url": venue.get('canonicalUrl') or f"https://foursquare.com/v/{venue_id}",
            "photos": checkin_photos[:photo_limit],
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
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

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
    max_pages = int(os.environ.get('FOURSQUARE_CHECKIN_MAX_PAGES', '20'))
    category_ids = get_category_filter()

    print("=== Foursquareチェックインから温泉リストを更新 ===")
    checkins = fetch_checkins(oauth_token, limit=limit, max_pages=max_pages)
    places = build_places_from_checkins(checkins, category_ids)

    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(places, f, ensure_ascii=False, indent=2)
        f.write('\n')

    with_photos = sum(1 for place in places if place.get('photos'))

    print(f"取得チェックイン: {len(checkins)}件")
    print(f"温泉カテゴリ一致: {len(places)}件")
    print(f"写真あり: {with_photos}件")
    print(f"書き出し先: {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
