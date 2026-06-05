#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
from datetime import date
from pathlib import Path
from urllib.parse import unquote


POST_RE = re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})-(.+)\.md$")
DATE_PREFIX_RE = re.compile(r"^\d{4}-\d{1,2}-\d{1,2}-")
FRONT_MATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n", re.S)


def parse_post_name(path: Path) -> tuple[date, str] | None:
    match = POST_RE.match(path.name)
    if not match:
        return None
    year, month, day, slug = match.groups()
    try:
        return date(int(year), int(month), int(day)), slug
    except ValueError:
        return None


def clean_slug(slug: str) -> str:
    while DATE_PREFIX_RE.match(slug):
        slug = DATE_PREFIX_RE.sub("", slug, count=1)
    slug = unquote(slug)
    slug = slug.replace("/", "-").replace("\\", "-").strip()
    slug = re.sub(r"\s+", " ", slug)
    return slug or "post"


def front_matter(content: str) -> str | None:
    match = FRONT_MATTER_RE.match(content)
    if not match:
        return None
    return match.group(1)


def clean_title_value(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
    return value.strip()


def first_content_line(content: str) -> str | None:
    match = FRONT_MATTER_RE.match(content)
    body = content[match.end() :] if match else content
    for line in body.splitlines():
        line = line.strip()
        if not line or line.startswith("[gallery]"):
            continue
        line = re.sub(r"<[^>]+>", "", line)
        line = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", line)
        line = line.strip()
        if line:
            return line[:48]
    return None


def usable_title(title: str | None) -> bool:
    if not title:
        return False
    return re.fullmatch(r"\d{4}-\d{1,2}-\d{1,2}-?", title) is None


def title_from_content(content: str) -> str | None:
    matter = front_matter(content)
    if matter is None:
        return None
    lines = matter.splitlines()
    for index, line in enumerate(lines):
        if not line.startswith("title:"):
            continue

        value = line.split(":", 1)[1].strip()
        if value in {">-", ">", "|", "|-"}:
            parts: list[str] = []
            for next_line in lines[index + 1 :]:
                if next_line.startswith(" ") or next_line.startswith("\t") or next_line == "":
                    parts.append(next_line.strip())
                    continue
                break
            return clean_title_value(" ".join(parts))
        return clean_title_value(value)

    return None


def clean_filename_title(title: str) -> str:
    title = title.replace("/", "-").replace("\\", "-").strip()
    title = re.sub(r"^\d{4}-\d{1,2}-\d{1,2}-?", "", title)
    title = re.sub(r"[#?%*:|\"<>`'!！?？,，、。()\[\]{}【】「」『』]+", "-", title)
    title = re.sub(r"\s+", "-", title)
    title = re.sub(r"-+", "-", title)
    title = title.strip("-. ")
    return title or "post"


def quote_yaml(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def replace_slug(content: str, slug: str) -> str:
    match = FRONT_MATTER_RE.match(content)
    if not match:
        return content

    front = match.group(1).splitlines()
    output: list[str] = []
    index = 0
    replaced = False

    while index < len(front):
        line = front[index]
        if line.startswith("slug:"):
            output.append(f"slug: {quote_yaml(slug)}")
            replaced = True
            index += 1
            if line.rstrip() == "slug: >-":
                while index < len(front):
                    next_line = front[index]
                    if next_line.startswith(" ") or next_line.startswith("\t") or next_line == "":
                        index += 1
                        continue
                    break
            continue

        output.append(line)
        index += 1

    if not replaced:
        insert_at = 0
        for index, line in enumerate(output):
            if line.startswith("title:"):
                insert_at = index + 1
                break
        output.insert(insert_at, f"slug: {quote_yaml(slug)}")

    newline = "\n"
    return "---\n" + newline.join(output) + "\n---\n" + content[match.end() :]


def plan(posts_dir: Path, cutoff: date) -> list[tuple[Path, Path, str]]:
    existing = {path.name for path in posts_dir.glob("*.md")}
    planned_names: set[str] = set()
    moves: list[tuple[Path, Path, str]] = []

    for source in sorted(posts_dir.glob("*.md")):
        parsed = parse_post_name(source)
        if parsed is None:
            continue

        post_date, raw_slug = parsed
        if post_date > cutoff:
            continue

        content = source.read_text(encoding="utf-8")
        title = title_from_content(content)
        if not usable_title(title):
            title = first_content_line(content)
        slug = clean_filename_title(title) if title else clean_slug(raw_slug)
        date_prefix = post_date.isoformat()
        candidate_slug = slug
        counter = 2

        while True:
            target_name = f"{date_prefix}-{candidate_slug}.md"
            occupied_by_other_file = target_name in existing and target_name != source.name
            occupied_by_plan = target_name in planned_names
            if not occupied_by_other_file and not occupied_by_plan:
                break
            candidate_slug = f"{slug}-{counter}"
            counter += 1

        planned_names.add(target_name)
        target = source.with_name(target_name)
        moves.append((source, target, candidate_slug))

    return moves


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--posts-dir", default="_posts")
    parser.add_argument("--cutoff", default="2019-05-31")
    args = parser.parse_args()

    posts_dir = Path(args.posts_dir)
    cutoff = date.fromisoformat(args.cutoff)
    moves = plan(posts_dir, cutoff)

    changed = 0
    for source, target, slug in moves:
        needs_move = source.name != target.name
        content = source.read_text(encoding="utf-8")
        new_content = replace_slug(content, slug)
        needs_content = content != new_content
        if not needs_move and not needs_content:
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
