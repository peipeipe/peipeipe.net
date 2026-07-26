#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""温泉チェックイン写真を成分表解析用にダウンロードして並べる。

Foursquare のチェックイン写真には温泉分析書（成分表）の掲示を撮ったものが混ざっている。
このスクリプトは解析そのものはせず、Claude Code の対話セッションで読ませるための
素材だけを用意する:

  1. astro/data/onsen_places.json の写真URLを original 解像度に変換してダウンロード
  2. astro/data/onsen_composition.json に記録済みの写真はスキップ（増分実行）
  3. 一覧レビュー用のコンタクトシート（番号入りタイル画像）を生成

出力はすべて .cache/onsen_photos/ 以下（gitignore 済み）。
"""

import argparse
import hashlib
import json
import os
import sys

import requests
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASTRO_DIR = os.path.join(BASE_DIR, 'astro')
ONSEN_JSON = os.path.join(ASTRO_DIR, 'data', 'onsen_places.json')
COMPOSITION_JSON = os.path.join(ASTRO_DIR, 'data', 'onsen_composition.json')
CACHE_DIR = os.path.join(BASE_DIR, '.cache', 'onsen_photos')
PHOTO_DIR = os.path.join(CACHE_DIR, 'photos')
SHEET_DIR = os.path.join(CACHE_DIR, 'sheets')
MANIFEST_JSON = os.path.join(CACHE_DIR, 'manifest.json')

# コンタクトシートの体裁
SHEET_COLUMNS = 4
SHEET_ROWS = 5
CELL_WIDTH = 460
CELL_HEIGHT = 345
LABEL_HEIGHT = 34


def original_url(url):
    """Foursquare のリサイズ済みURLをオリジナル解像度に変換する。

    例: .../img/general/500x300/41463109_xxx.jpg -> .../img/general/original/41463109_xxx.jpg
    """
    for size in ('/500x300/', '/300x300/', '/original/'):
        if size in url:
            return url.replace(size, '/original/')

    parts = url.split('/img/general/')
    if len(parts) == 2:
        tail = parts[1].split('/', 1)
        if len(tail) == 2:
            return f"{parts[0]}/img/general/original/{tail[1]}"

    return url


def photo_key(url):
    return hashlib.sha1(url.encode('utf-8')).hexdigest()[:16]


def load_json(path, fallback):
    if not os.path.exists(path):
        return fallback
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def analyzed_photo_urls():
    """解析済み（成分表だった／成分表でなかった、どちらも）の写真URL集合。"""
    data = load_json(COMPOSITION_JSON, None)
    if not data:
        return set()

    analyzed = set(data.get('not_composition_photos') or [])
    for entry in data.get('places') or []:
        for url in entry.get('source_photos') or []:
            analyzed.add(url)
    return analyzed


def collect_targets(places, skip_urls):
    targets = []
    for place in places:
        for url in place.get('photos') or []:
            if url in skip_urls:
                continue
            targets.append({
                "place_name": place.get('name', ''),
                "fsq_id": place.get('fsq_id', ''),
                "date": place.get('date', ''),
                "address": place.get('address', ''),
                "photo_url": url,
                "original_url": original_url(url),
            })
    return targets


def download(target, session, force=False):
    key = photo_key(target['photo_url'])
    path = os.path.join(PHOTO_DIR, f"{key}.jpg")
    target['key'] = key
    target['file'] = path

    if os.path.exists(path) and os.path.getsize(path) > 0 and not force:
        target['downloaded'] = False
        return True

    try:
        response = session.get(target['original_url'], timeout=30)
    except requests.RequestException as exc:
        print(f"[Warn] ダウンロード失敗 {target['original_url']}: {exc}", file=sys.stderr)
        return False

    if response.status_code != 200 or not response.content:
        print(
            f"[Warn] ダウンロード失敗 HTTP {response.status_code}: {target['original_url']}",
            file=sys.stderr,
        )
        return False

    with open(path, 'wb') as f:
        f.write(response.content)
    target['downloaded'] = True
    return True


def label_font(size):
    for candidate in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ):
        if os.path.exists(candidate):
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default(size=size)


def build_contact_sheets(targets):
    """番号を焼き込んだタイル画像を作る。番号は manifest の index と一致する。"""
    per_sheet = SHEET_COLUMNS * SHEET_ROWS
    font = label_font(24)
    sheets = []

    for sheet_no, start in enumerate(range(0, len(targets), per_sheet), start=1):
        chunk = targets[start:start + per_sheet]
        rows = (len(chunk) + SHEET_COLUMNS - 1) // SHEET_COLUMNS
        sheet = Image.new(
            'RGB',
            (SHEET_COLUMNS * CELL_WIDTH, rows * (CELL_HEIGHT + LABEL_HEIGHT)),
            (24, 24, 27),
        )
        draw = ImageDraw.Draw(sheet)

        for offset, target in enumerate(chunk):
            col = offset % SHEET_COLUMNS
            row = offset // SHEET_COLUMNS
            x = col * CELL_WIDTH
            y = row * (CELL_HEIGHT + LABEL_HEIGHT)

            try:
                with Image.open(target['file']) as img:
                    thumb = img.convert('RGB')
                    thumb.thumbnail((CELL_WIDTH - 8, CELL_HEIGHT - 8))
                    sheet.paste(
                        thumb,
                        (x + (CELL_WIDTH - thumb.width) // 2, y + (CELL_HEIGHT - thumb.height) // 2),
                    )
            except OSError as exc:
                print(f"[Warn] 画像を開けません {target['file']}: {exc}", file=sys.stderr)

            draw.text(
                (x + 10, y + CELL_HEIGHT + 4),
                f"#{target['index']}",
                fill=(255, 214, 102),
                font=font,
            )

        path = os.path.join(SHEET_DIR, f"sheet-{sheet_no:02d}.jpg")
        sheet.save(path, quality=88)
        sheets.append(path)
        print(f"コンタクトシート: {path} (#{chunk[0]['index']}〜#{chunk[-1]['index']})")

    return sheets


def main():
    parser = argparse.ArgumentParser(description="温泉写真を成分表解析用に準備する")
    parser.add_argument(
        '--all',
        action='store_true',
        help="解析済みの写真も含めて全件を対象にする（既定は未解析のみ）",
    )
    parser.add_argument(
        '--force-download',
        action='store_true',
        help="キャッシュ済みの画像も再ダウンロードする",
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=0,
        help="対象写真の上限枚数（0で無制限）",
    )
    args = parser.parse_args()

    os.makedirs(PHOTO_DIR, exist_ok=True)
    os.makedirs(SHEET_DIR, exist_ok=True)

    places = load_json(ONSEN_JSON, [])
    skip_urls = set() if args.all else analyzed_photo_urls()
    targets = collect_targets(places, skip_urls)

    total_photos = sum(len(place.get('photos') or []) for place in places)
    print("=== 温泉成分表の解析素材を準備 ===")
    print(f"温泉施設: {len(places)}件 / 写真: {total_photos}枚")
    print(f"解析済み写真: {len(skip_urls)}枚")
    print(f"今回の対象: {len(targets)}枚")

    if args.limit:
        targets = targets[:args.limit]
        print(f"--limit により {len(targets)}枚に制限")

    if not targets:
        print("新しく解析する写真はありません。")
        return

    session = requests.Session()
    session.headers.update({"User-Agent": "peipeipe.net onsen composition prep"})

    downloaded = []
    for target in targets:
        if download(target, session, force=args.force_download):
            downloaded.append(target)

    for index, target in enumerate(downloaded, start=1):
        target['index'] = index

    new_files = sum(1 for target in downloaded if target.get('downloaded'))
    print(f"取得成功: {len(downloaded)}枚（新規ダウンロード {new_files}枚）")

    build_contact_sheets(downloaded)

    manifest = {
        "generated_from": os.path.relpath(ONSEN_JSON, BASE_DIR),
        "photo_count": len(downloaded),
        "photos": downloaded,
    }
    with open(MANIFEST_JSON, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
        f.write('\n')

    print(f"マニフェスト: {MANIFEST_JSON}")
    print(f"画像キャッシュ: {PHOTO_DIR}")


if __name__ == "__main__":
    main()
