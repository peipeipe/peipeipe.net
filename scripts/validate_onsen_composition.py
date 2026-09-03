#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""成分表データの数値が内部で整合しているか検算する。

温泉分析書は合計値を何重にも書く冗長な書類で、次の関係が必ず成り立つ:

  * 陽イオン・陰イオン・非解離成分・溶存ガス成分 … 各成分の和 = その「計」
  * 溶存物質（ガス性のものを除く）= 陽イオン計 + 陰イオン計 + 非解離成分計
  * 成分総計 = 溶存物質 + 溶存ガス成分計

書き起こしで数値をひとつでも読み違えるとこの関係が崩れるので、読み取りの正しさを
機械的に確かめられる。掲示側にも丸めや微量成分の省略があるため、絶対値・相対値の
どちらかが許容範囲に収まっていれば一致とみなす。

  python3 scripts/validate_onsen_composition.py                  # 確定データを検算
  python3 scripts/validate_onsen_composition.py --extracted      # 書き起こし直後の下書きを検算
  python3 scripts/validate_onsen_composition.py --strict         # ズレがあれば終了コード1

extract 側から使うときは check_entry() を直接呼ぶ。
"""

import argparse
import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASTRO_DIR = os.path.join(BASE_DIR, 'astro')
CACHE_DIR = os.path.join(BASE_DIR, '.cache', 'onsen_photos')
COMPOSITION_JSON = os.path.join(ASTRO_DIR, 'data', 'onsen_composition.json')
EXTRACTED_JSON = os.path.join(CACHE_DIR, 'extracted.json')

# 掲示側の丸め（多くは小数第1位まで）と微量成分の省略を吸収する許容幅。
# 絶対値・相対値のどちらかに収まっていれば一致とみなす。
ABS_TOLERANCE_MG_KG = 1.0
REL_TOLERANCE = 0.005

GROUPS = [
    ('cations', 'cations_total_mg_kg', '陽イオン'),
    ('anions', 'anions_total_mg_kg', '陰イオン'),
    ('undissociated', 'undissociated_total_mg_kg', '非解離成分'),
    ('dissolved_gas', 'dissolved_gas_total_mg_kg', '溶存ガス成分'),
]

# 鉱泉分析法指針による泉質の区分。泉質名は成分値・pH・泉温から一意に決まるので、
# 合計の検算では捕まえられない「泉質名の読み違い」をここで拾う。
# 硫黄泉の判定に使う総硫黄（硫化水素イオン + チオ硫酸イオン + 遊離硫化水素）
SULFUR_COMPONENTS = [
    ('anions', ('硫化水素イオン', 'チオ硫酸イオン')),
    ('dissolved_gas', ('遊離硫化水素',)),
]
SULFUR_THRESHOLD_MG_KG = 2.0
SIMPLE_SPRING_LIMIT_MG_KG = 1000.0

# 浸透圧（溶存物質 mg/kg による）
OSMOTIC_RANGES = [('低張性', 0, 8000), ('等張性', 8000, 10000), ('高張性', 10000, None)]
# 液性（pH による）。長い語を先に見て「弱アルカリ性」を「アルカリ性」と誤認しないようにする
LIQUID_RANGES = [
    ('弱アルカリ性', 7.5, 8.5),
    ('弱酸性', 3, 6),
    ('アルカリ性', 8.5, None),
    ('酸性', None, 3),
    ('中性', 6, 7.5),
]
# 泉温（源泉温度 ℃ による）。「低温泉」は「微温泉」の古い言い方で、掲示にはどちらも出る。
TEMPERATURE_RANGES = [
    ('高温泉', 42, None),
    ('冷鉱泉', None, 25),
    ('微温泉', 25, 34),
    ('低温泉', 25, 34),
]
# 34〜42℃ の区分語は「温泉」だが、これは泉質名の末尾（「アルカリ性単純温泉」など）と
# 見分けがつかない。泉温の区分として読めるのは、他の区分語を含まない泉質別区分
# （spring_quality_class）に出てきたときだけ。
PLAIN_TEMPERATURE_RANGE = ('温泉', 34, 42)


def load_json(path, fallback=None):
    if not os.path.exists(path):
        return fallback
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def close_enough(actual, expected):
    diff = abs(actual - expected)
    if diff <= ABS_TOLERANCE_MG_KG:
        return True
    scale = max(abs(expected), abs(actual))
    return scale > 0 and diff / scale <= REL_TOLERANCE


def number(value):
    return value if isinstance(value, (int, float)) else None


def items_total(entry, key):
    """成分リストの mg_kg 合計。リスト自体が無ければ None（検算対象外）。"""
    items = entry.get(key)
    if not items:
        return None
    total = 0.0
    for item in items:
        value = number(item.get('mg_kg'))
        if value is None:
            return None
        total += value
    return total


def sulfur_total(entry):
    """総硫黄（硫黄泉の判定に使う）。成分リストが無ければ None。"""
    if not any(entry.get(items_key) for items_key, _ in SULFUR_COMPONENTS):
        return None
    total = 0.0
    for items_key, names in SULFUR_COMPONENTS:
        for item in entry.get(items_key) or []:
            if any(name in item.get('name', '') for name in names):
                total += number(item.get('mg_kg')) or 0.0
    return total


def in_range(value, low, high):
    if low is not None and value < low:
        return False
    return high is None or value < high


def check_ranges(quality, value, ranges, unit):
    """泉質名に含まれる区分語と、実測値から決まる区分が食い違っていれば理由を返す。"""
    for word, low, high in ranges:
        if word not in quality:
            continue
        if not in_range(value, low, high):
            return f"「{word}」だが{value:g}{unit}"
        return None
    return None


def check_temperature(entry, quality):
    """泉温の区分語と源泉温度が食い違っていれば理由を返す。

    「冷鉱泉」「高温泉」などは泉質名にも区分にも現れるので全体から探すが、34〜42℃ を
    指す「温泉」だけは泉質名の末尾と区別がつかないため、他の区分語を含まない
    spring_quality_class に出てきたときに限って区分語として読む。
    """
    value = number(entry.get('source_temp_c'))
    if value is None:
        return None

    reason = check_ranges(quality, value, TEMPERATURE_RANGES, '℃')
    if reason:
        return reason
    if any(word in quality for word, _, _ in TEMPERATURE_RANGES):
        return None

    quality_class = entry.get('spring_quality_class') or ''
    if PLAIN_TEMPERATURE_RANGE[0] in quality_class:
        return check_ranges(quality_class, value, [PLAIN_TEMPERATURE_RANGE], '℃')
    return None


def check_quality(entry):
    """泉質名が成分値と矛盾していないか見る。

    泉質名は鉱泉分析法指針で成分値・pH・泉温から一意に決まるため、合計の検算では
    捕まえられない「泉質名の読み違い」をここで拾える。反射などで読めない欄を
    埋めにいった書き起こしは、たいていここで矛盾する。
    """
    issues = []
    quality = (entry.get('spring_quality') or '') + (entry.get('spring_quality_class') or '')
    if not quality:
        return issues

    dissolved = number(entry.get('dissolved_solids_mg_kg'))

    if '硫黄' in quality:
        sulfur = sulfur_total(entry)
        if sulfur is not None and sulfur < SULFUR_THRESHOLD_MG_KG:
            issues.append((
                "泉質",
                f"泉質名に「硫黄」があるが総硫黄{sulfur:g}mg/kg（{SULFUR_THRESHOLD_MG_KG:g}mg/kg未満）",
            ))

    if '単純温泉' in quality and dissolved is not None and dissolved >= SIMPLE_SPRING_LIMIT_MG_KG:
        issues.append((
            "泉質",
            f"単純温泉だが溶存物質{dissolved:g}mg/kg（{SIMPLE_SPRING_LIMIT_MG_KG:g}mg/kg以上）",
        ))

    checks = [
        (dissolved, OSMOTIC_RANGES, 'mg/kg', '浸透圧'),
        (number(entry.get('ph')) if entry.get('ph') is not None else number(entry.get('ph_lab')),
         LIQUID_RANGES, '', '液性'),
    ]
    for value, ranges, unit, label in checks:
        if value is None:
            continue
        reason = check_ranges(quality, value, ranges, unit)
        if reason:
            issues.append(("泉質", f"{label}の区分が{reason}"))

    reason = check_temperature(entry, quality)
    if reason:
        issues.append(("泉質", f"泉温の区分が{reason}"))

    return issues


def check_entry(entry, ignore_exceptions=False):
    """1施設ぶんの検算結果を問題のリストとして返す。空なら整合している。

    それぞれ (ラベル, 理由) のタプル。掲示自体が自分の合計と合っていないことが
    まれにある（印字ミスや微量成分の省略）。そういう項目は施設側の
    validation_exceptions にラベルを並べておくと以後は報告しない。読み違いと
    区別がつかなくなるので、必ず notes に根拠を書いたうえで登録すること。
    """
    issues = []

    def compare(label, summed, expected):
        if not close_enough(summed, expected):
            issues.append((label, f"積み上げ{summed:g} / 掲示{expected:g}"))

    for items_key, total_key, label in GROUPS:
        total = number(entry.get(total_key))
        summed = items_total(entry, items_key)
        if total is not None and summed is not None:
            compare(f"{label}計", summed, total)

    subtotals = [number(entry.get(total_key)) for _, total_key, _ in GROUPS[:3]]
    dissolved = number(entry.get('dissolved_solids_mg_kg'))
    if dissolved is not None and all(value is not None for value in subtotals):
        compare("溶存物質", sum(subtotals), dissolved)

    gas = number(entry.get('dissolved_gas_total_mg_kg'))
    total_ingredients = number(entry.get('total_ingredients_mg_kg'))
    if dissolved is not None and total_ingredients is not None:
        compare("成分総計", dissolved + (gas or 0.0), total_ingredients)

    issues.extend(check_quality(entry))

    if not ignore_exceptions:
        known = set(entry.get('validation_exceptions') or [])
        issues = [issue for issue in issues if issue[0] not in known]

    return issues


def describe(issues):
    return '、'.join(f"{label} {reason}" for label, reason in issues)


def entry_label(place, spring, index):
    place_name = place.get('name') or f"place={index}"
    spring_name = spring.get('spring_name')
    return f"{place_name} / {spring_name}" if spring_name else place_name


def iter_springs(places):
    """新しい複数源泉形式と旧来の平坦形式をどちらも検算する。"""
    for index, place in enumerate(places):
        springs = place.get('springs')
        if not isinstance(springs, list):
            springs = [place]
        for spring in springs:
            if isinstance(spring, dict):
                yield index, place, spring


def main():
    parser = argparse.ArgumentParser(description="成分表データの合計値を検算する")
    parser.add_argument(
        '--extracted',
        action='store_true',
        help=f"確定データではなく書き起こし下書き（{EXTRACTED_JSON}）を検算する",
    )
    parser.add_argument(
        '--path',
        help="検算するJSONのパス（--extracted より優先）",
    )
    parser.add_argument(
        '--strict',
        action='store_true',
        help="ズレがひとつでもあれば終了コード1で終わる",
    )
    args = parser.parse_args()

    path = args.path or (EXTRACTED_JSON if args.extracted else COMPOSITION_JSON)
    data = load_json(path)
    if not data:
        print(f"[Error] {path} がありません。", file=sys.stderr)
        sys.exit(1)

    places = data.get('places') or []
    print("=== 成分表データの検算 ===")
    print(f"対象: {path}")

    flagged = 0
    skipped = 0
    known = 0
    spring_count = 0
    for index, place, entry in iter_springs(places):
        spring_count += 1
        issues = check_entry(entry)
        label = entry_label(place, entry, index)
        if issues:
            flagged += 1
            print(f"[NG] {label}: {describe(issues)}")
        elif not entry.get('cations') and not entry.get('anions'):
            skipped += 1
        if entry.get('validation_exceptions'):
            known += 1
            print(f"[既知] {label}: {'、'.join(entry['validation_exceptions'])}（掲示側の不整合として登録済み）")

    checked = spring_count - skipped
    print(
        f"検算できた源泉: {checked}件 / 成分値なし: {skipped}件 / "
        f"ズレあり: {flagged}件 / 既知の不整合: {known}件"
    )

    if flagged and args.strict:
        sys.exit(1)


if __name__ == "__main__":
    main()
