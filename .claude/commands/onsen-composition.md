---
description: 温泉チェックイン写真から成分表を読み取り、astro/data/onsen_composition.json を更新する
---

温泉チェックイン写真に写っている温泉分析書・温泉成分等掲示表を読み取り、
`astro/data/onsen_composition.json` を更新します。画像の判読はこの対話の中で行うので、
API キーや外部サービスは不要です。

以下の手順を順番に実行してください。

## 1. 未解析の写真を集める

```sh
python3 scripts/prepare_onsen_composition.py
```

`astro/data/onsen_places.json` の写真を original 解像度で `.cache/onsen_photos/photos/` に落とし、
選別用のコンタクトシート `.cache/onsen_photos/sheets/sheet-NN.jpg` と
`.cache/onsen_photos/manifest.json` を作ります。すでに解析済みの写真（成分表だったもの・
そうでなかったもの、どちらも）は自動でスキップされるので、通常は新しいチェックイン分だけが対象になります。

「新しく解析する写真はありません。」と出たら、そこで終了して構いません。

## 2. コンタクトシートで成分表を選別する

`.cache/onsen_photos/sheets/` の各シートを Read で開き、**温泉分析書・温泉成分等掲示表・
温泉分析書別表が写っているコマの番号**を書き出します。各コマの左下に `#12` のような番号が
焼き込んであり、これが manifest の `index` に対応します。

対象になるのは分析値や泉質が読み取れる掲示物だけです。施設の外観・料金表・のれん・
食事・源泉名だけの看板などは対象外にします。

## 3. 該当画像を精読する

選んだ番号の画像を `.cache/onsen_photos/photos/` から Read で開き、記載内容を読み取ります。
manifest の `file` にパスが入っています。小さくて読めない場合は Pillow でその部分を
クロップ・拡大してから読み直してください。

読み取る項目（掲示にあるものだけでよい）:

- 源泉名、泉質、泉質の分類（低張性/等張性/高張性・酸性/中性/アルカリ性・冷鉱泉/温泉/高温泉）
- 源泉温度、使用位置温度、湧出量、pH（湧出地・試験室の両方あれば両方）
- 蒸発残留物、溶存物質、成分総計
- 陽イオン・陰イオン・非解離成分・溶存ガス成分の各値と合計
- 加水・加温・循環ろ過・消毒の有無とその理由
- 泉質別適応症・泉質別禁忌症
- 分析年月日（西暦に直す）、登録分析機関とその登録番号

## 4. 書き起こしを JSON にする

`.cache/onsen_photos/extracted.json` に次の形式で書きます。既存の同ファイルがあれば
今回のぶんで置き換えて構いません（確定データは `astro/data/onsen_composition.json` 側にあります）。

```json
{
  "places": [
    {
      "photo_indexes": [1],
      "confidence": "high",
      "spring_name": "…",
      "spring_quality": "単純温泉",
      "spring_quality_class": "低張性中性高温泉",
      "source_temp_c": 47.0,
      "ph": 7.1,
      "total_ingredients_mg_kg": 713.4,
      "cations": [{ "name": "ナトリウムイオン", "symbol": "Na+", "mg_kg": 146.5 }],
      "cations_total_mg_kg": 174.0,
      "treatment": { "kasui": { "applied": true, "reason": "…" } },
      "indications": ["…"],
      "analyzed_on": "2025-04-23",
      "analyzer": "長野県薬剤師会"
    }
  ]
}
```

守ること:

- 数値の単位は **mg/kg に統一**する（分析書が g/kg なら 1000 倍する）。
- 同じ施設の成分表が複数枚あるときは `photo_indexes` にまとめて並べる。
- 施設名・住所・fsq_id は manifest から自動で埋まるので書かなくてよい。
- 読み取りが怪しい値は**書かずに省く**。写真が不鮮明で全体的に自信がないときは
  `"confidence": "low"`（多少怪しい程度なら `"medium"`）にして、`notes` に理由を書く。
- 掲示が別表だけで成分値が無い場合も、泉質と適応症だけのエントリとして登録してよい。
- **すでに登録済みの施設**を再訪して撮り直した場合は、変わった項目だけ書けばよい。
  `astro/data/onsen_composition.json` の同じ `fsq_id` へ項目単位でマージされるので、
  前回読み取った値は残り、今回書いた値だけが上書きされる。項目を消したいときだけ
  `astro/data/onsen_composition.json` を直接編集する。

## 5. データに反映する

```sh
python3 scripts/merge_onsen_composition.py
```

`extracted.json` に出てこなかった写真は「成分表ではなかった写真」として記録され、
次回の `prepare_onsen_composition.py` の対象から外れます。

## 6. 検算する

```sh
python3 scripts/validate_onsen_composition.py
```

合計の足し算（陽イオン計・陰イオン計・非解離成分計・溶存物質・成分総計）と、
泉質名が成分値と矛盾していないかを機械的に確かめます。`[NG]` が出たら
その施設の写真を読み直してください。数値の読み違いはほぼここで捕まります。

掲示そのものが自分の合計と合っていないと確認できた場合だけ、その施設に
`"validation_exceptions": ["陰イオン計"]` を足し、根拠を `notes` に書きます。
読み違いの疑いを黙らせるために使ってはいけません。

## 7. 確認する

```sh
cd astro
PATH=/home/peipeipe/.local/nodejs/current/bin:$PATH npm run build
```

`/onsen` ページ下部の「温泉成分表」セクションと、温泉一覧カードの泉質バッジに
反映されていることを確認します。`.cache/` は gitignore 済みなので、コミット対象は
`astro/data/onsen_composition.json` だけです。
