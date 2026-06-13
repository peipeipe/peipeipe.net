#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
from datetime import date
from pathlib import Path


POST_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})-(.+)\.md$")
FRONT_MATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n", re.S)


SLUGS = {
    "You-re-up-and-running": "youre-up-and-running",
    "白と金に見えるか青と黒に見えるかの画像": "white-gold-or-blue-black-dress",
    "火の用心": "fire-safety",
    "カバンが欲しい": "i-want-a-bag",
    "Mac版Minecraftマルチプレイのやり方-Hamachi": "minecraft-multiplayer-on-mac-with-hamachi",
    "タイのカップヌードルには折りたたみフォークが入っていた": "folding-fork-in-thai-cup-noodles",
    "ボンバーマン": "bomberman",
    "電話機の電池替え": "replacing-phone-batteries",
    "自転車と低気圧": "bicycle-and-low-pressure",
    "車の免許をとった": "got-my-drivers-license",
    "MacBook-Airが届いたよ": "macbook-air-arrived",
    "iOS8.3にアップデート": "updated-to-ios-8-3",
    "MacBookのキーボードできらめき格子錯覚": "scintillating-grid-illusion-on-macbook-keyboard",
    "MacBook-Airを1周間使った": "using-macbook-air-for-a-week",
    "日記-指紋認証で未来を感じる": "diary-feeling-the-future-with-fingerprint-authentication",
    "沈黙交易とは": "what-is-silent-trade",
    "荷物": "luggage",
    "松伏総合公園っで釣り": "fishing-at-matsubushi-general-park",
    "Amazon-Studentお試し中": "trying-amazon-student",
    "だいぶ前だけど-足利に免許合宿言った時に軽く観光したのでメモ": "sightseeing-in-ashikaga-during-driving-school-camp",
    "モニターアーム買ったよ": "bought-a-monitor-arm",
    "吊り橋理論と警報アラーム": "suspension-bridge-effect-and-alert-alarms",
    "ゲーム機がほしい": "i-want-a-game-console",
    "ルンバがきた": "roomba-arrived",
    "Gif画像": "gif-images",
    "HHKB-Liteを買った": "bought-an-hhkb-lite",
    "amazon買取サービス使ってみた": "tried-amazon-trade-in",
    "洋楽のグローバル化": "globalization-of-western-music",
    "マンホールが丸いわけ": "why-manhole-covers-are-round",
    "WiiUを浪人生から借りた": "borrowed-a-wii-u-from-a-ronin-student",
    "スプラトゥーンを買った": "bought-splatoon",
    "Zガンダム見てる": "watching-zeta-gundam",
    "しゃっくりが出やすい日": "a-day-prone-to-hiccups",
    "バトルフィールド4を買った": "bought-battlefield-4",
    "Hulu登録した": "signed-up-for-hulu",
    "メタルギアソリッドⅤを買った": "bought-metal-gear-solid-v",
    "IngressのNIANTEC-ポケモンGoを開発": "niantic-of-ingress-develops-pokemon-go",
    "母校-高校-の文化祭に行ってきた": "visited-my-high-school-festival",
    "ガンダム展-東京-に行ってきた": "visited-the-gundam-exhibition-in-tokyo",
    "アニメを見始めた": "started-watching-anime",
    "昨日はしゃっくりの出やすい日でした": "yesterday-was-a-day-prone-to-hiccups",
    "OS-X-El-Capitanにアップデートしました": "updated-to-os-x-el-capitan",
    "今日はしゃっくりの出やすい日でした": "today-was-a-day-prone-to-hiccups",
    "最強おやじギャグキャラ-になる方法": "how-to-become-the-ultimate-dad-joke-character",
    "機動戦士ガンダムオールナイト上映に行ってきた": "went-to-an-all-night-mobile-suit-gundam-screening",
    "子供の頃は秋を感じる余裕があった気がする": "i-had-more-room-to-feel-autumn-as-a-child",
    "ヤマト運輸-クール宅急便車が届いた": "yamato-cool-delivery-truck-arrived",
    "パトレイバーがめちゃ面白かった": "patlabor-was-really-fun",
    "便利すぎると怠慢が増加する": "too-much-convenience-increases-laziness",
    "よりぬきpeipeipe-.-com": "best-of-peipeipe-com",
    "あけおめ-2016": "happy-new-year-2016",
    "光らなくてよいものもある": "some-things-do-not-need-to-glow",
    "今年の目標": "goals-for-this-year",
    "メガネを買った": "bought-glasses",
    "首都高速に乗った": "drove-on-the-shuto-expressway",
    "この日のことを覚えていますか": "do-you-remember-this-day",
    "サークル冬合宿に行ってきました": "went-to-a-club-winter-camp",
    "足立区立図書館の優越": "superiority-of-adachi-city-library",
    "Kindle-paperwhiteを買った": "bought-a-kindle-paperwhite",
    "みんなでガンプラを作った": "built-gunpla-with-everyone",
    "お花見と時計": "cherry-blossom-viewing-and-a-watch",
    "あの日-感想": "thoughts-on-that-day",
    "新型山手線E235に乗った": "rode-the-new-yamanote-line-e235",
    "小学校の時の記憶": "memories-from-elementary-school",
    "Mac版Minecraftサーバーアップデート方法": "how-to-update-a-minecraft-server-on-mac",
    "図書館司書アルバイトを始めた": "started-working-part-time-as-a-library-clerk",
    "先月読んだ本": "books-read-last-month",
    "数える": "counting",
    "はたして僕等は感嘆符をつけなければいけない関係だったのだろうか": "did-our-relationship-really-need-exclamation-marks",
    "iPhoneはゼンマイ式": "iphone-is-clockwork",
    "洗練された超鬱ツイートのような": "like-a-refined-depressing-tweet",
    "なぜ浴室に鏡があるのか": "why-there-is-a-mirror-in-the-bathroom",
    "文系大学生は電子ノートの夢を見るか": "do-liberal-arts-students-dream-of-digital-notebooks",
    "餅つき大会と拡張現実": "mochi-pounding-and-augmented-reality",
    "ふつうの日記を書く": "writing-an-ordinary-diary",
    "24時間テレビとバリバラ": "24-hour-tv-and-baribara",
    "Kindle-_Unlimitedの体験が終了した": "kindle-unlimited-trial-ended",
    "母校の文化祭に行ってきた": "visited-my-alma-mater-school-festival",
    "320円で買った安すぎるArduino互換機をMacに認識させる": "getting-a-cheap-arduino-clone-recognized-on-mac",
    "Qc30を買った-見た目編": "bought-qc30-appearance",
    "この世界の片隅に-と原作あとがき": "in-this-corner-of-the-world-and-the-original-afterword",
    "時間と共に歩いている-I-am-walking-with-time": "i-am-walking-with-time",
    "六義園に行ってきた": "visited-rikugien",
    "Raspberry-Piを買った": "bought-a-raspberry-pi",
    "バイバイ-2016年": "bye-bye-2016",
    "バイトサガシチューのねずみに全く別のことをしゃべらせる": "making-the-baito-sagashi-chu-mouse-say-something-else",
    "iPhoneのバッテリを自分で交換": "replaced-an-iphone-battery-myself",
    "Arduino-UNO": "arduino-uno",
    "iPhoneのバッテリを自分で交換-その後": "after-replacing-an-iphone-battery-myself",
    "鉄塔の模型": "transmission-tower-model",
    "模型鉄塔に航空障害灯": "aviation-obstruction-light-on-a-transmission-tower-model",
    "今日の夢": "todays-dream",
    "工場夜景を見にドライブに行くもあまり見えず": "drove-to-see-factory-night-views-but-could-not-see-much",
    "機械人間オルタ": "android-alter",
    "絵本のなかで思い出すこと": "remembering-inside-a-picture-book",
    "また夜ドライブ": "another-night-drive",
    "Amazonのアフィで儲けることはできるのか": "can-you-make-money-with-amazon-affiliate",
    "LINEモバイルにした": "switched-to-line-mobile",
    "桜と一眼レフ": "cherry-blossoms-and-a-dslr",
    "最近行ったドライブなど": "recent-drives",
    "GWも終わり": "golden-week-is-over",
    "ロングライド": "long-ride",
    "日焼け止めっていくらのを使えばいいのかしらん": "how-expensive-should-sunscreen-be",
    "レンタサイクル": "rental-bicycle",
    "チャリ買いました": "bought-a-bike",
    "事細かにログを書いてみる": "trying-to-write-detailed-logs",
    "ルンバのバッテリィ替え": "replacing-a-roomba-battery",
    "ガーミン-220j": "garmin-220j",
    "荒川サイクリングロード上": "on-the-arakawa-cycling-road",
    "夏合宿の思い出2017": "memories-of-summer-camp-2017",
    "Garmin-520jを買った": "bought-a-garmin-520j",
    "1000種類のエアコンを操作できるリモコンを手に入れた": "got-a-remote-that-controls-1000-air-conditioners",
    "6年付き合ってきたWILLCOMとさよなら": "goodbye-to-willcom-after-six-years",
    "昭和記念公園トライアスロン完走": "finished-the-showa-kinen-park-triathlon",
    "iPhone6が割れたので自分で修理": "fixed-a-cracked-iphone-6-myself",
    "ランニングシューズ変え": "changed-running-shoes",
    "You-are-listening-to-New-York": "you-are-listening-to-new-york",
    "最近は料理": "cooking-lately",
    "まにまに": "manimani",
    "東京に円を描くDraw-a-circle-in-Tokyo": "draw-a-circle-in-tokyo",
    "池袋ウエストゲートパークを愛しながら": "loving-ikebukuro-west-gate-park",
    "就活とは-仕事とは": "what-is-job-hunting-what-is-work",
    "東京大雪": "tokyo-heavy-snow",
    "ガンダムスタンプラリーの東京駅タムラのヤバさ": "tamura-at-tokyo-station-in-the-gundam-stamp-rally",
    "悪という希望": "evil-as-hope",
    "地下鉄道": "the-underground-railroad",
    "冷蔵庫の中に100-オレンジを": "put-100-percent-orange-in-the-fridge",
    "新潮2018年3月号-創る人52人日記リレー": "shincho-2018-03-52-creators-diary-relay",
    "とりあえずフル完走と感想": "finished-a-full-marathon-and-thoughts",
    "オートキャンプに行ってきた": "went-auto-camping",
    "バイクに乗りたい": "i-want-to-ride-a-motorcycle",
    "22歳になった": "turned-22",
    "今月読んだ本と22歳までのおもしろかった本リスト": "books-read-this-month-and-favorite-books-before-22",
}


def quote_yaml(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def replace_slug(content: str, slug: str) -> str:
    match = FRONT_MATTER_RE.match(content)
    if not match:
        return content
    lines = match.group(1).splitlines()
    out: list[str] = []
    replaced = False
    for line in lines:
        if line.startswith("slug:"):
            out.append(f"slug: {quote_yaml(slug)}")
            replaced = True
        else:
            out.append(line)
    if not replaced:
        insert_at = 0
        for index, line in enumerate(out):
            if line.startswith("title:"):
                insert_at = index + 1
                break
        out.insert(insert_at, f"slug: {quote_yaml(slug)}")
    return "---\n" + "\n".join(out) + "\n---\n" + content[match.end() :]


def monthly_slug(current_slug: str, post_date: date) -> str | None:
    ym = post_date.strftime("%Y-%m")
    if current_slug in {"今月読んだ本", "先月読んだ本"}:
        return f"books-read-in-{ym}"
    if current_slug == "今月のアクティビティ":
        return f"activities-in-{ym}"
    if re.fullmatch(r"\d{4}年\d{1,2}月に読んだ本", current_slug):
        year, month = re.match(r"(\d{4})年(\d{1,2})月に読んだ本", current_slug).groups()
        return f"books-read-in-{year}-{int(month):02d}"
    if re.fullmatch(r"今月読んだ本\d{4}年\d{1,2}月", current_slug):
        year, month = re.match(r"今月読んだ本(\d{4})年(\d{1,2})月", current_slug).groups()
        return f"books-read-in-{year}-{int(month):02d}"
    if re.fullmatch(r"今月読んだ本\d{4}-\d{2}", current_slug):
        year, month = re.match(r"今月読んだ本(\d{4})-(\d{2})", current_slug).groups()
        return f"books-read-in-{year}-{month}"
    if re.fullmatch(r"今月-\d{4}-\d{2}-に読んだ本", current_slug):
        year, month = re.match(r"今月-(\d{4})-(\d{2})-に読んだ本", current_slug).groups()
        return f"books-read-in-{year}-{month}"
    if re.fullmatch(r"今読んだ本\d{4}-\d{1,2}", current_slug):
        year, month = re.match(r"今読んだ本(\d{4})-(\d{1,2})", current_slug).groups()
        return f"books-read-in-{year}-{int(month):02d}"
    if re.fullmatch(r"先月\d{4}-\d{2}に読んだ本", current_slug):
        year, month = re.match(r"先月(\d{4})-(\d{2})に読んだ本", current_slug).groups()
        return f"books-read-in-{year}-{month}"
    return None


def english_slug(current_slug: str, post_date: date) -> str:
    if current_slug.isascii() and re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", current_slug):
        return current_slug
    slug = monthly_slug(current_slug, post_date)
    if slug:
        return slug
    if current_slug.startswith("サイボーグになりたい-"):
        number = current_slug.rsplit("-", 1)[1]
        if number.isdigit():
            return f"want-to-be-a-cyborg-{number}"
    if current_slug == "サイボーグになりたい-4-pebble-time":
        return "want-to-be-a-cyborg-4-pebble-time"
    if current_slug in SLUGS:
        return SLUGS[current_slug]
    raise KeyError(current_slug)


def plan(posts_dir: Path, cutoff: date) -> list[tuple[Path, Path, str]]:
    moves = []
    used_names: set[str] = set()
    used_slugs: set[str] = set()
    for path in posts_dir.glob("*.md"):
        match = POST_RE.match(path.name)
        if not match:
            continue
        year, month, day, current_slug = match.groups()
        post_date = date(int(year), int(month), int(day))
        if post_date > cutoff:
            used_slugs.add(current_slug)

    for source in sorted(posts_dir.glob("*.md")):
        match = POST_RE.match(source.name)
        if not match:
            continue
        year, month, day, current_slug = match.groups()
        post_date = date(int(year), int(month), int(day))
        if post_date > cutoff:
            continue
        base_slug = english_slug(current_slug, post_date)
        slug = base_slug
        if slug in used_slugs:
            slug = f"{base_slug}-{post_date.isoformat()}"
        counter = 2
        while slug in used_slugs:
            slug = f"{base_slug}-{post_date.isoformat()}-{counter}"
            counter += 1
        used_slugs.add(slug)

        target_name = f"{post_date.isoformat()}-{slug}.md"
        if target_name in used_names:
            raise RuntimeError(f"duplicate target: {target_name}")
        used_names.add(target_name)
        moves.append((source, source.with_name(target_name), slug))
    return moves


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--posts-dir", default="astro/content/posts")
    parser.add_argument("--cutoff", default="2019-05-31")
    args = parser.parse_args()

    moves = plan(Path(args.posts_dir), date.fromisoformat(args.cutoff))
    changed = 0
    for source, target, slug in moves:
        content = source.read_text(encoding="utf-8")
        new_content = replace_slug(content, slug)
        needs_content = new_content != content
        needs_move = source.name != target.name
        if not needs_content and not needs_move:
            continue
        changed += 1
        print(f"{source.name} -> {target.name}")
        if args.apply:
            if needs_content:
                source.write_text(new_content, encoding="utf-8")
            if needs_move:
                os.rename(source, target)
    print(f"{changed} files would change" if not args.apply else f"{changed} files changed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
