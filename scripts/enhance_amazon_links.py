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

# Regex patterns to extract ASIN from full Amazon URLs
AMAZON_ASIN_PATTERNS = [
    r'https?://(?:www\.)?amazon\.co\.jp/(?:exec/obidos/ASIN/|dp/|gp/product/)([A-Z0-9]{10})',
    r'https?://(?:www\.)?amazon\.co\.jp/[^/\s]+/dp/([A-Z0-9]{10})',
    r'/(?:dp|gp/product)/([A-Z0-9]{10})',
]


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
        match = re.search(pattern, target_url)
        if match:
            return match.group(1)

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
        r'\[([^\]]+)\]\((https?://(?:www\.)?(?:amazon\.co\.jp|amzn\.to)[^\s\)]*)\)'
    )
    for match in pattern.finditer(content):
        # Check the 300 chars before this match for an open widget div
        start = max(0, match.start() - 300)
        context = content[start:match.start()]
        if 'krb-amzlt-box' in context or 'amazon-product-card' in context:
            continue
        links.append((match.group(0), match.group(1), match.group(2)))

    return links


def process_file(file_path: Path) -> bool:
    """Process a markdown file and replace simple Amazon links with rich cards.

    Returns True if the file was modified.
    """
    try:
        content = file_path.read_text(encoding='utf-8')
    except Exception as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)
        return False

    links = find_simple_amazon_links(content)
    if not links:
        return False

    print(f"Processing {file_path.name} — {len(links)} link(s) found")

    new_content = content
    processed_asins: set = set()
    modified = False

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
        try:
            file_path.write_text(new_content, encoding='utf-8')
            print(f"  Saved {file_path.name}")
        except Exception as e:
            print(f"Error writing {file_path}: {e}", file=sys.stderr)
            return False

    return modified


def main() -> None:
    repo_root = Path(__file__).parent.parent
    posts_dir = repo_root / '_posts'

    if not posts_dir.exists():
        print(f"Error: _posts directory not found at {posts_dir}", file=sys.stderr)
        sys.exit(1)

    md_files = sorted(posts_dir.glob('*.md'))
    print(f"Scanning {len(md_files)} post files…")

    modified_count = sum(1 for f in md_files if process_file(f))
    print(f"\nDone. {modified_count} file(s) updated.")


if __name__ == '__main__':
    main()
