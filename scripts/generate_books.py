#!/usr/bin/env python3
"""Generate Astro books data from a Booklog CSV export."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path


DEFAULT_INPUT = "/mnt/c/Users/peipe/Downloads/booklog20260615223359.csv"
DEFAULT_OUTPUT = "astro/data/books.json"


@dataclass
class QuoteCandidate:
    text: str
    confidence: str
    reason: str


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", nargs="?", default=DEFAULT_INPUT)
    parser.add_argument("-o", "--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    rows = read_booklog_csv(Path(args.csv))
    books = [book_from_row(row, index) for index, row in enumerate(rows)]
    books.sort(key=lambda item: (item["readDate"] or "", item["registeredAt"] or ""), reverse=True)

    payload = {
        "source": "booklog",
        "generatedFrom": str(args.csv),
        "stats": {
            "books": len(books),
            "withNotes": sum(1 for row in rows if cell(row, 8)),
            "withQuotes": sum(1 for book in books if book["quotes"]),
            "quotes": sum(len(book["quotes"]) for book in books),
            "personalNotesDropped": sum(book["droppedPersonalNoteCount"] for book in books),
        },
        "books": books,
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {output} ({payload['stats']})")


def read_booklog_csv(path: Path) -> list[list[str]]:
    for encoding in ("utf-8-sig", "cp932"):
        try:
            with path.open(encoding=encoding, newline="") as file:
                return list(csv.reader(file))
        except UnicodeDecodeError:
            continue
    raise UnicodeError(f"Could not decode {path}")


def book_from_row(row: list[str], index: int) -> dict:
    note = cell(row, 8)
    quotes, dropped = extract_quotes(note)
    title = cell(row, 11)
    author = cell(row, 12)
    asin = cell(row, 1)
    isbn13 = cell(row, 2)
    stable_key = isbn13 or asin or f"{title}-{author}-{index}"

    return {
        "id": slugify(stable_key),
        "asin": asin,
        "isbn13": isbn13,
        "format": cell(row, 3),
        "rating": parse_int(cell(row, 4)),
        "status": cell(row, 5),
        "tags": split_tags(cell(row, 7)),
        "registeredAt": date_only(cell(row, 9)),
        "readDate": date_only(cell(row, 10)),
        "title": title,
        "author": author,
        "publisher": cell(row, 13),
        "publishedYear": cell(row, 14),
        "media": cell(row, 15),
        "pages": parse_int(cell(row, 16)),
        "quotes": [quote.__dict__ for quote in quotes],
        "droppedPersonalNoteCount": len(dropped),
    }


def extract_quotes(note: str) -> tuple[list[QuoteCandidate], list[str]]:
    text = normalize_newlines(note)
    if not text:
        return [], []

    marker = re.search(r"以下引用(?:[＋+].*)?|^引用$", text, flags=re.MULTILINE)
    kindle_mode = "黄色のハイライト" in text
    if not marker and not kindle_mode:
        return [], []

    working = text[marker.end() :] if marker else text
    lines = [line.rstrip() for line in working.splitlines()]
    blocks: list[list[str]] = []
    current: list[str] = []
    current_reason = "after-marker"
    reasons: list[str] = []

    for raw_line in lines:
        line = raw_line.strip()
        if is_metadata_line(line):
            flush_block(blocks, reasons, current, current_reason)
            current_reason = "highlight"
            continue
        if is_quote_marker(line):
            flush_block(blocks, reasons, current, current_reason)
            current_reason = "explicit-quote"
            continue
        if not line:
            flush_block(blocks, reasons, current, current_reason)
            current_reason = "after-marker"
            continue
        current.append(line)
    flush_block(blocks, reasons, current, current_reason)

    quotes: list[QuoteCandidate] = []
    dropped: list[str] = []
    for block, reason in zip(blocks, reasons):
        cleaned = clean_quote_block("\n".join(block))
        if not cleaned:
            continue
        if is_personal_note(cleaned):
            dropped.append(cleaned)
            continue
        confidence = "high" if reason in {"explicit-quote", "highlight"} else "medium"
        if reason == "after-marker" and len(cleaned) < 12:
            dropped.append(cleaned)
            continue
        quotes.append(QuoteCandidate(cleaned, confidence, reason))

    return dedupe_quotes(quotes), dropped


def flush_block(blocks: list[list[str]], reasons: list[str], current: list[str], reason: str) -> None:
    if current:
        blocks.append(current[:])
        reasons.append(reason)
        current.clear()


def clean_quote_block(value: str) -> str:
    value = re.sub(r"\n?中略\n?", "\n", value)
    value = re.sub(r"^[\s　]+", "", value, flags=re.MULTILINE)
    return re.sub(r"\n{3,}", "\n\n", value).strip()


def is_quote_marker(line: str) -> bool:
    return bool(re.fullmatch(r"(以下)?引用(?:[＋+].*)?|引用メモ", line))


def is_metadata_line(line: str) -> bool:
    if not line:
        return False
    return bool(
        re.fullmatch(r"黄色のハイライト\s*\|\s*位置:\s*[\d,]+", line)
        or re.fullmatch(r"\d{4}-\d{2}-\d{2}", line)
        or line.startswith("http://")
        or line.startswith("https://")
    )


def is_personal_note(value: str) -> bool:
    first_line = value.splitlines()[0].strip()
    if re.match(r"^[ー―\-－]", first_line):
        return True
    if first_line.startswith("メモ"):
        return True
    personal_phrases = (
        "なるほど",
        "わかる",
        "そうそう",
        "グッと",
        "すばらしい",
        "好きだった",
        "好きだ",
        "と思った",
        "気がする",
        "使えそう",
        "やってみよう",
        "最高",
        "笑ってしまった",
        "よかった",
    )
    if len(value) <= 80 and any(phrase in value for phrase in personal_phrases):
        return True
    if len(value) <= 50 and re.search(r"(表現|メモ|セリフ|ラスト)$", value):
        return True
    return False


def dedupe_quotes(quotes: list[QuoteCandidate]) -> list[QuoteCandidate]:
    seen: set[str] = set()
    result: list[QuoteCandidate] = []
    for quote in quotes:
        key = re.sub(r"\s+", "", quote.text)
        digest = hashlib.sha1(key.encode("utf-8")).hexdigest()
        if digest in seen:
            continue
        seen.add(digest)
        result.append(quote)
    return result


def cell(row: list[str], index: int) -> str:
    return row[index].strip() if len(row) > index else ""


def parse_int(value: str) -> int | None:
    return int(value) if value.isdigit() else None


def split_tags(value: str) -> list[str]:
    return [tag.strip() for tag in value.split(",") if tag.strip()]


def date_only(value: str) -> str:
    return value[:10] if re.match(r"\d{4}-\d{2}-\d{2}", value) else ""


def normalize_newlines(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n").strip()


def slugify(value: str) -> str:
    normalized = re.sub(r"[^0-9A-Za-z]+", "-", value).strip("-").lower()
    if normalized:
        return normalized
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:12]


if __name__ == "__main__":
    main()
