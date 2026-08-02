#!/usr/bin/env python3
"""
fetch_osm_peaks.py の実行前後で scripts/osm_peaks.json がどう変わったかを要約する。

- 標準出力とGitHubのステップサマリに人間向けの差分を出す
- Discord webhook に投げるためのペイロードJSONを書き出す（--payload）
- Overpass が部分応答を返したときの保険として、大幅に件数が減っていたら異常終了する

峰の同一性は座標 (lat, lng) で判定する。OSM上でノードが移動した場合は
「削除＋追加」として現れるが、実用上その方が見落としが少ない。
"""
import argparse
import json
import os
import subprocess
import sys

MAX_LISTED = 15  # 1セクションに列挙する最大件数
SHRINK_LIMIT_PCT = 10  # 前回比でこの割合以上減っていたら異常とみなす


def load_new(path):
    with open(path) as f:
        return json.load(f)


def load_base(path, base):
    """git のリビジョンから前回分を読む。取得できなければ None。"""
    rel = os.path.relpath(path, start=os.path.join(os.path.dirname(__file__), ".."))
    res = subprocess.run(["git", "show", f"{base}:{rel}"], capture_output=True, text=True)
    if res.returncode != 0:
        return None
    return json.loads(res.stdout)


def key_of(peak):
    return (peak["lat"], peak["lng"])


def fmt(peak):
    elev = peak.get("elevation")
    return f"{peak['name']} ({elev}m)" if elev is not None else f"{peak['name']} (標高不明)"


def diff(old, new):
    old_map = {key_of(p): p for p in old}
    new_map = {key_of(p): p for p in new}

    added = [new_map[k] for k in new_map.keys() - old_map.keys()]
    removed = [old_map[k] for k in old_map.keys() - new_map.keys()]
    renamed, re_elevated = [], []
    for k in old_map.keys() & new_map.keys():
        o, n = old_map[k], new_map[k]
        if o["name"] != n["name"]:
            renamed.append((o, n))
        if o.get("elevation") != n.get("elevation"):
            re_elevated.append((o, n))

    added.sort(key=lambda p: -(p.get("elevation") or 0))
    removed.sort(key=lambda p: -(p.get("elevation") or 0))
    renamed.sort(key=lambda t: -(t[1].get("elevation") or 0))
    re_elevated.sort(key=lambda t: -(t[1].get("elevation") or 0))
    return added, removed, renamed, re_elevated


def section(title, items, render):
    if not items:
        return []
    lines = [f"**{title} {len(items)}座**"]
    lines += [f"- {render(x)}" for x in items[:MAX_LISTED]]
    if len(items) > MAX_LISTED:
        lines.append(f"- …他 {len(items) - MAX_LISTED}座")
    lines.append("")
    return lines


def build_summary(old, new):
    added, removed, renamed, re_elevated = diff(old, new)
    delta = len(new) - len(old)
    lines = [f"{len(old)}座 → {len(new)}座（{delta:+d}）", ""]
    lines += section("追加", added, fmt)
    lines += section("削除", removed, fmt)
    lines += section("改称", renamed, lambda t: f"{t[0]['name']} → {fmt(t[1])}")
    lines += section(
        "標高更新", re_elevated,
        lambda t: f"{t[1]['name']}: {t[0].get('elevation') or '不明'}m → {t[1].get('elevation') or '不明'}m")
    changed = bool(added or removed or renamed or re_elevated)
    if not changed:
        lines.append("座標・名称・標高の変化はありません。")
    return "\n".join(lines).rstrip(), changed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="HEAD", help="比較元のgitリビジョン")
    parser.add_argument("--payload", help="Discord webhook 用ペイロードの書き出し先")
    args = parser.parse_args()

    path = os.path.join(os.path.dirname(__file__), "osm_peaks.json")
    new = load_new(path)
    old = load_base(path, args.base)
    if old is None:
        print(f"{args.base} に osm_peaks.json が無いため差分の比較をスキップします（{len(new)}座）")
        return

    summary, changed = build_summary(old, new)
    print(summary)

    step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary:
        with open(step_summary, "a", encoding="utf-8") as f:
            f.write(f"## OSM山頂データ 更新\n\n{summary}\n")

    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as f:
            f.write(f"changed={'true' if changed else 'false'}\n")

    # 山頂の中身に変化が無ければ通知用ペイロードを作らない
    if args.payload and changed:
        repo = os.environ.get("GITHUB_REPOSITORY", "")
        run_id = os.environ.get("GITHUB_RUN_ID", "")
        body = summary
        if len(body) > 4000:  # Discord の embed description 上限（4096）に対する余裕
            body = body[:4000].rstrip() + "\n…（省略）"
        embed = {
            "title": "⛰️ OSM山頂データを更新しました",
            "description": body,
            "color": 0x2E7D32,
        }
        if repo and run_id:
            embed["url"] = f"https://github.com/{repo}/actions/runs/{run_id}"
        with open(args.payload, "w", encoding="utf-8") as f:
            json.dump({"embeds": [embed]}, f, ensure_ascii=False)

    if len(new) < len(old) * (1 - SHRINK_LIMIT_PCT / 100):
        sys.exit(f"取得件数が前回より{SHRINK_LIMIT_PCT}%以上減少しました。中止します。")


if __name__ == "__main__":
    main()
