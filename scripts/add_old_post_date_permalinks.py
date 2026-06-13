#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from datetime import date
from pathlib import Path


POST_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})-(.+)\.md$")
SLUG_RE = re.compile(r"^slug:\s*['\"]?([^'\"\n]+)['\"]?\s*$", re.M)
PERMALINK_RE = re.compile(r"^permalink:\s*(.+)$", re.M)


def dated_permalink(path: Path) -> str | None:
    match = POST_RE.match(path.name)
    if not match:
        return None
    year, month, day, filename_slug = match.groups()
    post_date = date(int(year), int(month), int(day))
    content = path.read_text(encoding="utf-8")
    slug_match = SLUG_RE.search(content)
    slug = slug_match.group(1).strip() if slug_match else filename_slug
    return f"/{post_date.isoformat()}-{slug}/"


def update_content(content: str, permalink: str) -> str:
    if PERMALINK_RE.search(content):
        return PERMALINK_RE.sub(f"permalink: {permalink}", content, count=1)
    slug_match = SLUG_RE.search(content)
    if slug_match:
        insert_at = slug_match.end()
        return content[:insert_at] + f"\npermalink: {permalink}" + content[insert_at:]
    front_matter_end = content.find("\n---", 4)
    if front_matter_end == -1:
        raise ValueError("front matter not found")
    return content[:front_matter_end] + f"\npermalink: {permalink}" + content[front_matter_end:]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--posts-dir", default="astro/content/posts")
    parser.add_argument("--cutoff", default="2019-05-31")
    args = parser.parse_args()

    cutoff = date.fromisoformat(args.cutoff)
    changed = 0
    for path in sorted(Path(args.posts_dir).glob("*.md")):
        match = POST_RE.match(path.name)
        if not match:
            continue
        post_date = date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        if post_date > cutoff:
            continue
        permalink = dated_permalink(path)
        if permalink is None:
            continue
        content = path.read_text(encoding="utf-8")
        new_content = update_content(content, permalink)
        if new_content == content:
            continue
        changed += 1
        if args.apply:
            path.write_text(new_content, encoding="utf-8")
        else:
            print(f"{path}: {permalink}")

    if args.apply:
        print(f"{changed} files changed")
    else:
        print(f"{changed} files would change")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
