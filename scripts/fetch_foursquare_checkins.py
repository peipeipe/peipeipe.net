#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import sys
from datetime import datetime, timezone

import requests

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_JSON = os.path.join(BASE_DIR, '_data', 'onsen_places.json')

HOT_SPRING_CATEGORY_ID = "4bf58dd8d48988d160941735"
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
    raw = os.environ.get('FOURSQUARE_CHECKIN_CATEGORY_IDS', HOT_SPRING_CATEGORY_ID)
    return {item.strip() for item in raw.split(',') if item.strip()}


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


def build_places_from_checkins(checkins, category_ids):
    places = {}

    for checkin in checkins:
        venue = checkin.get('venue') or {}
        venue_id = venue.get('id')
        location = venue.get('location') or {}
        lat = location.get('lat')
        lng = location.get('lng')

        if not venue_id or lat is None or lng is None:
            continue
        if not venue_has_category(venue, category_ids):
            continue

        visited_at = checkin_time(checkin)
        visited_iso = visited_at.isoformat() if visited_at else ""
        visited_date = visited_at.astimezone().date().isoformat() if visited_at else ""

        existing = places.get(venue_id)
        if existing:
            existing['checkin_count'] += 1
            if visited_iso and visited_iso > existing.get('last_checkin_at', ''):
                existing['last_checkin_at'] = visited_iso
                existing['date'] = visited_date
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
            "photos": [],
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

    print(f"取得チェックイン: {len(checkins)}件")
    print(f"温泉カテゴリ一致: {len(places)}件")
    print(f"書き出し先: {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
