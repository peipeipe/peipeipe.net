#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""温泉成分表の更新内容をレビューしやすいPR本文にまとめる。"""

import argparse
import html
import json
import os


SUMMARY_FIELDS = [
    ("spring_quality", "泉質"),
    ("spring_quality_class", "分類"),
    ("source_temp_c", "源泉温度", "℃"),
    ("use_temp_c", "使用位置温度", "℃"),
    ("ph", "pH"),
    ("yield_l_min", "湧出量", "L/min"),
    ("dissolved_solids_mg_kg", "溶存物質", "mg/kg"),
    ("total_ingredients_mg_kg", "成分総計", "mg/kg"),
    ("analyzed_on", "分析終了日"),
    ("analyzer", "分析機関"),
]

# 値が変わったことをPRで知らせる対象。巨大なイオン配列は主要成分の表で見せる。
DIFF_LABELS = {
    "confidence": "信頼度",
    "spring_name": "源泉名",
    "spring_quality": "泉質",
    "spring_quality_class": "分類",
    "source_temp_c": "源泉温度",
    "use_temp_c": "使用位置温度",
    "ph": "pH",
    "ph_lab": "分析時pH",
    "yield_l_min": "湧出量",
    "evaporation_residue_mg_kg": "蒸発残留物",
    "dissolved_solids_mg_kg": "溶存物質",
    "total_ingredients_mg_kg": "成分総計",
    "treatment": "利用状況",
    "indications": "適応症",
    "contraindications": "禁忌症",
    "analyzed_on": "分析終了日",
    "analyzer": "分析機関",
    "analyzer_registration": "登録番号",
    "notes": "注意書き",
    "validation_exceptions": "検算例外",
}


def load_json(path):
    if not path or not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as file:
        return json.load(file)


def markdown(value):
    return str(value).replace("|", "\\|").replace("\n", " ")


def display_value(value, suffix=""):
    if value is None or value == "":
        return "—"
    return f"{markdown(value)}{suffix}"


def spring_key(spring, index):
    name = (spring.get("spring_name") or "").strip()
    return ("name", name) if name else ("index", index)


def place_changes(before, after):
    old_places = {place.get("fsq_id"): place for place in before.get("places", [])}
    changes = []
    for place in after.get("places", []):
        old_place = old_places.get(place.get("fsq_id"))
        old_springs = {
            spring_key(spring, index): spring
            for index, spring in enumerate((old_place or {}).get("springs", []))
        }
        changed_springs = []
        for index, spring in enumerate(place.get("springs", [])):
            old_spring = old_springs.get(spring_key(spring, index))
            if old_spring != spring:
                changed_springs.append((spring, old_spring))
        if old_place is None or changed_springs:
            changes.append({
                "place": place,
                "is_new_place": old_place is None,
                "springs": changed_springs,
            })
    return changes


def changed_fields(old, new):
    if old is None:
        return []
    return [
        label for key, label in DIFF_LABELS.items()
        if old.get(key) != new.get(key)
    ]


def top_ingredients(spring, key, limit=4):
    ingredients = sorted(
        spring.get(key) or [],
        key=lambda item: item.get("mg_kg") or 0,
        reverse=True,
    )
    return "、".join(
        f"{item.get('name') or item.get('symbol') or '名称不明'} {display_value(item.get('mg_kg'), 'mg/kg')}"
        for item in ingredients[:limit]
    ) or "—"


def stat_delta(before, after, key):
    old = (before.get("stats") or {}).get(key, 0)
    new = (after.get("stats") or {}).get(key, 0)
    delta = new - old
    return new, f"+{delta}" if delta >= 0 else str(delta)


def build_report(before, after, validation=""):
    changes = place_changes(before, after)
    new_places = sum(change["is_new_place"] for change in changes)
    new_springs = sum(
        old is None for change in changes for _, old in change["springs"]
    )
    updated_springs = sum(
        old is not None for change in changes for _, old in change["springs"]
    )
    low_confidence = sum(
        spring.get("confidence") in {"low", "medium"}
        for change in changes for spring, _ in change["springs"]
    )

    if not changes:
        title = "温泉写真の解析結果（成分表なし）"
    elif len(changes) == 1:
        title = f"温泉成分表を更新: {changes[0]['place'].get('name', '1施設')}"
    else:
        title = f"温泉成分表を更新（{len(changes)}施設）"

    composition_photos, composition_delta = stat_delta(before, after, "composition_photos")
    rejected_photos, rejected_delta = stat_delta(before, after, "not_composition_photos")
    unreadable_photos, unreadable_delta = stat_delta(before, after, "unreadable_photos")

    if changes:
        introduction = [
            "新しいチェックイン写真から温泉分析書を自動で読み取りました。",
            "数値の整合性は自動検算済みですが、写真と照らして文字・小数点・単位を確認してください。",
        ]
    else:
        introduction = [
            "新しいチェックイン写真を解析しましたが、追加・更新できる温泉分析書はありませんでした。",
            "写真の判定結果だけが更新されています。",
        ]

    lines = [
        *introduction,
        "",
        "## 今回の更新",
        "",
        "| 内容 | 件数 |",
        "| --- | ---: |",
        f"| 新規施設 | {new_places} |",
        f"| 新規源泉 | {new_springs} |",
        f"| 更新した既存源泉 | {updated_springs} |",
        f"| 要注意（信頼度 medium / low） | {low_confidence} |",
        f"| 成分表写真 | {composition_photos}（{composition_delta}） |",
        f"| 成分表ではなかった写真 | {rejected_photos}（{rejected_delta}） |",
        f"| 読み取れなかった写真 | {unreadable_photos}（{unreadable_delta}） |",
        "",
    ]

    for change in changes:
        place = change["place"]
        status = "新規" if change["is_new_place"] else "更新"
        lines.extend([
            f"## {status}: {markdown(place.get('name') or '名称不明')}",
            "",
            f"- 所在地: {markdown(place.get('address') or '—')}",
            f"- チェックイン日: {markdown(place.get('checkin_date') or '—')}",
            f"- Foursquare ID: `{markdown(place.get('fsq_id') or '—')}`",
            "",
        ])
        for spring, old_spring in change["springs"]:
            spring_name = spring.get("spring_name") or "源泉名なし"
            confidence = spring.get("confidence") or "未設定"
            warning = " ⚠️" if confidence in {"low", "medium"} else ""
            lines.extend([
                f"### {markdown(spring_name)}{warning}",
                "",
                f"信頼度: **{markdown(confidence)}**",
                "",
                "| 項目 | 読み取り結果 |",
                "| --- | --- |",
            ])
            for field in SUMMARY_FIELDS:
                key, label, *suffix = field
                lines.append(
                    f"| {label} | {display_value(spring.get(key), suffix[0] if suffix else '')} |"
                )
            lines.extend([
                f"| 主な陽イオン | {markdown(top_ingredients(spring, 'cations'))} |",
                f"| 主な陰イオン | {markdown(top_ingredients(spring, 'anions'))} |",
                "",
            ])

            fields = changed_fields(old_spring, spring)
            if fields:
                lines.extend([f"変更項目: {markdown('、'.join(fields))}", ""])
            if spring.get("notes"):
                lines.extend([f"> 注意: {markdown(spring['notes'])}", ""])
            if spring.get("validation_exceptions"):
                exceptions = spring["validation_exceptions"]
                if isinstance(exceptions, list):
                    exceptions = "、".join(map(str, exceptions))
                lines.extend([f"> 検算例外: {markdown(exceptions)}", ""])

            photos = list(dict.fromkeys(spring.get("source_photos") or []))
            if photos:
                lines.extend(["<details open>", "<summary>根拠写真</summary>", ""])
                for photo_no, url in enumerate(photos, start=1):
                    safe_url = html.escape(str(url), quote=True)
                    safe_alt = html.escape(f"{place.get('name', '')} {spring_name} 根拠写真 {photo_no}", quote=True)
                    lines.append(f'<a href="{safe_url}"><img src="{safe_url}" alt="{safe_alt}" width="640"></a>')
                lines.extend(["", "</details>", ""])

    lines.extend([
        "## レビューチェックリスト",
        "",
        "- [ ] 写真と泉質名・源泉名が一致している",
        "- [ ] 数値の小数点と単位が一致している",
        "- [ ] `medium` / `low` の項目と注意書きを確認した",
        "- [ ] 同じ施設の別源泉として分ける／まとめる判断が正しい",
        "",
        "## 自動検算",
        "",
        "<details>",
        "<summary>検算ログを表示</summary>",
        "",
        "```text",
        validation.strip() or "検算ログなし",
        "```",
        "",
        "</details>",
        "",
        "読み直しが必要なら、ローカルで `/onsen-composition` を実行してください。",
        "データ全体は [`astro/data/onsen_composition.json`](../../blob/HEAD/astro/data/onsen_composition.json) で確認できます。",
    ])
    return title, "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description="温泉成分表更新PRのタイトルと本文を生成する")
    parser.add_argument("--before", required=True, help="更新前のJSON")
    parser.add_argument("--after", required=True, help="更新後のJSON")
    parser.add_argument("--validation", help="検算ログ")
    parser.add_argument("--body-output", default="pr-body.md")
    parser.add_argument("--title-output", default="pr-title.txt")
    args = parser.parse_args()

    before = load_json(args.before)
    after = load_json(args.after)
    validation = ""
    if args.validation and os.path.exists(args.validation):
        with open(args.validation, encoding="utf-8") as file:
            validation = file.read()
    title, body = build_report(before, after, validation)
    with open(args.body_output, "w", encoding="utf-8") as file:
        file.write(body)
    with open(args.title_output, "w", encoding="utf-8") as file:
        file.write(title + "\n")
    print(f"PRタイトル: {title}")
    print(f"PR本文: {args.body_output}")


if __name__ == "__main__":
    main()
