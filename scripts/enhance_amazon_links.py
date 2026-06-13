#!/usr/bin/env python3
"""
Script to enhance Amazon affiliate links in markdown files.
Replaces simple [text](amazon_url) markdown links with rich krb-amzlt-box cards.
No PA-API credentials required.

Usage in blog post - just write a standard markdown link:
  [商品名](https://amzn.to/xxx)
  or
  [商品名](https://www.amazon.co.jp/dp/XXXXXXXXXX)

The link text becomes the product title.
Image URL is constructed from the ASIN.
affiliate tag is appended if not already present.
"""

import os
import re
import sys
import requests
import html
from pathlib import Path
from typing import Optional, List, Tuple

PARTNER_TAG = os.environ.get('AMAZON_PARTNER_TAG', 'peipeipe-22')
GENERIC_AMAZON_LINK_TEXTS = {'Amazon', 'Amazon.co.jpで詳細を見る'}

# Regex patterns to extract ASIN from full Amazon URLs
AMAZON_ASIN_PATTERNS = [
    r'https?://(?:www\.)?amazon\.co\.jp/(?:exec/obidos/(?:ASIN|asin)/|dp/|gp/product/)([A-Z0-9]{10})',
    r'https?://(?:www\.)?amazon\.co\.jp/[^/\s]+/dp/([A-Z0-9]{10})',
    r'/(?:dp|gp/product)/([A-Z0-9]{10})',
]

LEGACY_IMAGE_LINK_BEFORE_CARD_PATTERN = re.compile(
    r'(?m)^\s*\[!\[[^\]\n]*\]\([^\n]*\)\]\('
    r'https?://(?:www\.)?amazon\.co\.jp/exec/obidos/(?:ASIN|asin)/([A-Z0-9]{10})/?[^\)\n]*'
    r'\)[ \t]*\n+'
    r'(?=<div class="krb-amzlt-box"[^\n]*(?:/dp/\1|/P/\1\.))',
    re.IGNORECASE,
)


def resolve_short_url(url: str) -> Optional[str]:
    """Follow redirects to resolve amzn.to short URLs to full Amazon URL."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, allow_redirects=True, timeout=10, headers=headers)
        return response.url
    except Exception as e:
        print(f"  Warning: Could not resolve short URL {url}: {e}", file=sys.stderr)
        return None


def extract_asin(url: str) -> Optional[str]:
    """Extract ASIN from an Amazon URL (full or amzn.to short)."""
    # Resolve short URLs first
    target_url = url
    if 'amzn.to' in url:
        resolved = resolve_short_url(url)
        if resolved:
            target_url = resolved

    for pattern in AMAZON_ASIN_PATTERNS:
        match = re.search(pattern, target_url, re.IGNORECASE)
        if match:
            return match.group(1).upper()

    return None


def build_affiliate_url(original_url: str, asin: str) -> str:
    """Return affiliate URL. Keep amzn.to as-is; add tag to amazon.co.jp URLs."""
    if 'amzn.to' in original_url:
        return original_url
    # Strip existing tag parameter and add ours
    base = re.sub(r'[?&]tag=[^&]+', '', f"https://www.amazon.co.jp/dp/{asin}")
    return f"{base}?tag={PARTNER_TAG}"


def create_krb_html(title: str, asin: str, affiliate_url: str) -> str:
    """Create a krb-amzlt-box card matching the existing post format."""
    safe_title = html.escape(title)
    safe_url = html.escape(affiliate_url)
    image_url = f"https://images-na.ssl-images-amazon.com/images/P/{asin}.09.LZZZZZZZ"

    return (
        f'<div class="krb-amzlt-box" style="margin-bottom:0px;">'
        f'<div class="krb-amzlt-image" style="float:left;margin:0px 12px 1px 0px;">'
        f'<a href="{safe_url}"><img width="160px" src="{image_url}"></a>'
        f'</div>'
        f'<div class="krb-amzlt-info" style="line-height:120%; margin-bottom: 10px">'
        f'<div class="krb-amzlt-name" style="margin-bottom:10px;line-height:120%">'
        f'<a href="{safe_url}" name="amazletlink" target="_blank" rel="nofollow" rel="nofollow">'
        f'{safe_title}'
        f'</a>'
        f'</div>'
        f'<div class="krb-amzlt-detail"></div>'
        f'<div class="krb-amzlt-sub-info" style="float: left;">'
        f'<div class="krb-amzlt-link" style="margin-top: 5px">'
        f'<a href="{safe_url}" name="amazletlink" target="_blank" rel="nofollow" rel="nofollow">'
        f'Amazon.co.jpで詳細を見る'
        f'</a>'
        f'</div></div></div>'
        f'<div class="krb-amzlt-footer" style="clear: left"></div></div>'
    )


def find_simple_amazon_links(content: str) -> List[Tuple[str, str, str]]:
    """Find markdown links [text](amazon_url) that are NOT already inside a widget.

    Returns list of (full_match, link_text, url) tuples.
    """
    links = []
    pattern = re.compile(
        r'(?<!!)\[([^\]]+)\]\((https?://(?:www\.)?(?:amazon\.co\.jp|amzn\.to)[^\s\)]*)\)'
    )
    for match in pattern.finditer(content):
        link_text = match.group(1).strip()
        if link_text in GENERIC_AMAZON_LINK_TEXTS:
            continue
        # Check the 300 chars before this match for an open widget div
        start = max(0, match.start() - 300)
        context = content[start:match.start()]
        if 'krb-amzlt-box' in context or 'amazon-product-card' in context:
            continue
        links.append((match.group(0), link_text, match.group(2)))

    return links


def remove_legacy_image_links_before_cards(content: str) -> Tuple[str, int]:
    """Remove old Hatena image Amazon links when a rich card already follows."""
    new_content, removed_count = LEGACY_IMAGE_LINK_BEFORE_CARD_PATTERN.subn('', content)
    return new_content, removed_count


def remove_duplicate_generic_amazon_cards(content: str) -> Tuple[str, int]:
    """Remove cards created from generic old [Amazon](...) helper links."""
    lines = content.splitlines(keepends=True)
    seen_asins: set = set()
    kept_lines = []
    removed_count = 0

    for line in lines:
        if '<div class="krb-amzlt-box"' not in line:
            kept_lines.append(line)
            continue

        asins = set(re.findall(r'(?:/dp/|/P/)([A-Z0-9]{10})', line, re.IGNORECASE))
        normalized_asins = {asin.upper() for asin in asins}
        is_generic_card = any(
            f'>{text}</a></div><div class="krb-amzlt-detail"' in line
            for text in GENERIC_AMAZON_LINK_TEXTS
        )

        if is_generic_card and normalized_asins & seen_asins:
            removed_count += 1
            continue

        seen_asins.update(normalized_asins)
        kept_lines.append(line)

    return ''.join(kept_lines), removed_count


def process_file(file_path: Path) -> bool:
    """Process a markdown file and replace simple Amazon links with rich cards.

    Returns True if the file was modified.
    """
    try:
        content = file_path.read_text(encoding='utf-8')
    except Exception as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)
        return False

    new_content, removed_legacy_count = remove_legacy_image_links_before_cards(content)
    new_content, removed_generic_card_count = remove_duplicate_generic_amazon_cards(new_content)
    links = find_simple_amazon_links(new_content)
    if not links:
        if removed_legacy_count or removed_generic_card_count:
            try:
                file_path.write_text(new_content, encoding='utf-8')
                print(
                    f"Cleaned {file_path.name} — removed "
                    f"{removed_legacy_count} legacy image link(s), "
                    f"{removed_generic_card_count} generic duplicate card(s)"
                )
            except Exception as e:
                print(f"Error writing {file_path}: {e}", file=sys.stderr)
                return False
            return True
        return False

    print(f"Processing {file_path.name} — {len(links)} link(s) found")
    if removed_legacy_count:
        print(f"  Removed {removed_legacy_count} legacy image link(s)")
    if removed_generic_card_count:
        print(f"  Removed {removed_generic_card_count} generic duplicate card(s)")

    processed_asins: set = set()
    modified = removed_legacy_count > 0 or removed_generic_card_count > 0

    for full_match, link_text, url in links:
        asin = extract_asin(url)
        if not asin:
            print(f"  Skipped (no ASIN): {url}")
            continue
        if asin in processed_asins:
            print(f"  Skipped duplicate ASIN {asin}")
            continue

        processed_asins.add(asin)
        affiliate_url = build_affiliate_url(url, asin)
        rich_html = create_krb_html(link_text, asin, affiliate_url)

        new_content = new_content.replace(full_match, rich_html, 1)
        modified = True
        print(f"  ✓ {link_text[:60]}")

    if modified:
        new_content, additional_removed_count = remove_legacy_image_links_before_cards(new_content)
        if additional_removed_count:
            print(f"  Removed {additional_removed_count} legacy image link(s)")
        new_content, additional_generic_card_count = remove_duplicate_generic_amazon_cards(new_content)
        if additional_generic_card_count:
            print(f"  Removed {additional_generic_card_count} generic duplicate card(s)")
        try:
            file_path.write_text(new_content, encoding='utf-8')
            print(f"  Saved {file_path.name}")
        except Exception as e:
            print(f"Error writing {file_path}: {e}", file=sys.stderr)
            return False

    return modified


def main() -> None:
    repo_root = Path(__file__).parent.parent
    posts_dir = repo_root / 'astro' / 'content' / 'posts'

    if not posts_dir.exists():
        print(f"Error: posts directory not found at {posts_dir}", file=sys.stderr)
        sys.exit(1)

    md_files = sorted(posts_dir.glob('*.md'))
    print(f"Scanning {len(md_files)} post files…")

    modified_count = sum(1 for f in md_files if process_file(f))
    print(f"\nDone. {modified_count} file(s) updated.")


if __name__ == '__main__':
    main()
