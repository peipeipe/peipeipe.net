#!/usr/bin/env python3
"""
Script to enhance Amazon affiliate links in markdown files using Amazon PA-API.
Replaces simple Amazon links with rich product information (image, title, affiliate link).
"""

import os
import re
import sys
import requests
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from amazon.paapi import AmazonAPI

# Amazon PA-API credentials (from environment variables)
ACCESS_KEY = os.environ.get('AMAZON_ACCESS_KEY', '')
SECRET_KEY = os.environ.get('AMAZON_SECRET_KEY', '')
PARTNER_TAG = os.environ.get('AMAZON_PARTNER_TAG', 'peipeipe-22')
COUNTRY = 'JP'

# Regex patterns to find Amazon links
AMAZON_URL_PATTERNS = [
    r'https?://(?:www\.)?amazon\.co\.jp/(?:exec/obidos/ASIN/|dp/|gp/product/)([A-Z0-9]{10})',
    r'https?://amzn\.to/[a-zA-Z0-9]+',  # Short links - need to resolve
    r'https?://(?:www\.)?amazon\.co\.jp/[^/]+/dp/([A-Z0-9]{10})',
]

# Pattern to match existing rich Amazon content (to avoid double processing)
EXISTING_RICH_PATTERN = r'(<div class="amazon-product-card".*?</div>\s*</div>|<div class="krb-amzlt-box".*?</div>)'


def extract_asin_from_url(url: str) -> Optional[str]:
    """Extract ASIN from Amazon URL."""
    # First, try direct ASIN extraction
    for pattern in AMAZON_URL_PATTERNS:
        match = re.search(pattern, url)
        if match and len(match.groups()) > 0:
            return match.group(1)
    
    # For short URLs (amzn.to), follow redirects to get the full URL
    if 'amzn.to' in url:
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, allow_redirects=True, timeout=10, headers=headers)
            full_url = response.url
            # Try extracting ASIN from the full URL
            for pattern in AMAZON_URL_PATTERNS:
                match = re.search(pattern, full_url)
                if match and len(match.groups()) > 0:
                    return match.group(1)
            # Try /dp/ anywhere in the resolved URL
            asin_match = re.search(r'/(?:dp|gp/product)/([A-Z0-9]{10})', full_url)
            if asin_match:
                return asin_match.group(1)
        except Exception as e:
            print(f"  Warning: Could not resolve short URL {url}: {e}", file=sys.stderr)
    
    # Try to extract ASIN from query parameters
    asin_match = re.search(r'[?&]a=([A-Z0-9]{10})', url)
    if asin_match:
        return asin_match.group(1)
    
    # Try to extract from /dp/ or /gp/product/ anywhere in URL
    asin_match = re.search(r'/(?:dp|gp/product)/([A-Z0-9]{10})', url)
    if asin_match:
        return asin_match.group(1)
    
    return None


def get_product_info(asin: str, api: AmazonAPI) -> Optional[Dict]:
    """Fetch product information from Amazon PA-API."""
    try:
        # Use GetItems operation to fetch product details
        items = api.get_items(
            item_ids=[asin],
            resources=[
                'Images.Primary.Large',
                'Images.Primary.Medium',
                'ItemInfo.Title',
                'ItemInfo.Features',
                'Offers.Listings.Price',
            ]
        )
        
        if items and len(items) > 0:
            item = items[0]
            
            # Extract product information
            title = item.item_info.title.display_value if item.item_info and item.item_info.title else None
            image_url = None
            
            if item.images and item.images.primary:
                if item.images.primary.large:
                    image_url = item.images.primary.large.url
                elif item.images.primary.medium:
                    image_url = item.images.primary.medium.url
            
            detail_page_url = item.detail_page_url if item.detail_page_url else None
            
            if title and detail_page_url:
                return {
                    'asin': asin,
                    'title': title,
                    'image_url': image_url,
                    'url': detail_page_url,
                }
        
    except Exception as e:
        print(f"Error fetching product info for ASIN {asin}: {e}", file=sys.stderr)
    
    return None


def create_rich_html(product: Dict) -> str:
    """Create rich HTML for Amazon product."""
    html = f'''<div class="amazon-product-card" style="border: 1px solid #ddd; border-radius: 8px; padding: 16px; margin: 16px 0; display: flex; gap: 16px; align-items: flex-start;">
  <div class="amazon-product-image" style="flex-shrink: 0;">
    <a href="{product['url']}" target="_blank" rel="nofollow noopener">
      <img src="{product['image_url']}" alt="{product['title']}" style="width: 160px; height: auto; border-radius: 4px;" loading="lazy">
    </a>
  </div>
  <div class="amazon-product-info" style="flex-grow: 1;">
    <h3 style="margin: 0 0 12px 0; font-size: 1.1em;">
      <a href="{product['url']}" target="_blank" rel="nofollow noopener" style="text-decoration: none; color: #0066c0;">
        {product['title']}
      </a>
    </h3>
    <div class="amazon-product-link">
      <a href="{product['url']}" target="_blank" rel="nofollow noopener" style="display: inline-block; background-color: #ff9900; color: white; padding: 8px 16px; border-radius: 4px; text-decoration: none; font-weight: bold;">
        Amazon.co.jpで詳細を見る
      </a>
    </div>
  </div>
</div>'''
    return html


def find_amazon_links_in_markdown(content: str) -> List[Tuple[str, str]]:
    """Find Amazon links in markdown content.
    Returns list of (match_text, url) tuples.
    Only returns simple links, not complex HTML structures.
    """
    links = []
    
    # Skip content that has complex Amazon widgets
    if re.search(r'<div class="krb-amzlt-box"', content):
        return links  # Don't process files with existing complex widgets
    
    # Pattern 1: Markdown link format [text](url) - most common and safest
    md_link_pattern = r'\[([^\]]+)\]\((https?://(?:www\.)?(?:amazon\.co\.jp|amzn\.to)[^\)]+)\)'
    for match in re.finditer(md_link_pattern, content):
        links.append((match.group(0), match.group(2)))
    
    # Pattern 2: Simple HTML anchor tags (not part of complex divs)
    # Only match single-line anchors
    html_link_pattern = r'<a[^>]+href="(https?://(?:www\.)?(?:amazon\.co\.jp|amzn\.to)[^"]+)"[^>]*>[^<]+</a>'
    for match in re.finditer(html_link_pattern, content):
        # Check if this anchor is not part of a complex structure
        start = max(0, match.start() - 200)
        context = content[start:match.start()]
        if '<div class="krb-amzlt' not in context and '<div class="amazon-product' not in context:
            links.append((match.group(0), match.group(1)))
    
    # Pattern 3: Bare URLs (uncommon but possible)
    bare_url_pattern = r'(?<!["\(\[])(https?://(?:www\.)?(?:amazon\.co\.jp|amzn\.to)/[^\s\)<>]+)'
    for match in re.finditer(bare_url_pattern, content):
        links.append((match.group(0), match.group(1)))
    
    return links


def process_markdown_file(file_path: Path, api: AmazonAPI, dry_run: bool = False) -> bool:
    """Process a single markdown file to enhance Amazon links.
    Returns True if file was modified.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Skip if already has rich Amazon content
        if re.search(EXISTING_RICH_PATTERN, content):
            print(f"Skipping {file_path} - already has rich Amazon content")
            return False
        
        # Find all Amazon links
        links = find_amazon_links_in_markdown(content)
        
        if not links:
            return False
        
        print(f"Processing {file_path} - found {len(links)} Amazon links")
        
        modified = False
        new_content = content
        processed_asins = set()
        
        for match_text, url in links:
            # Extract ASIN
            asin = extract_asin_from_url(url)
            
            if not asin:
                print(f"  Could not extract ASIN from: {url}")
                continue
            
            # Skip if already processed this ASIN in this file
            if asin in processed_asins:
                continue
            
            processed_asins.add(asin)
            
            # Get product info
            product = get_product_info(asin, api)
            
            if not product:
                print(f"  Could not fetch product info for ASIN: {asin}")
                continue
            
            # Create rich HTML
            rich_html = create_rich_html(product)
            
            # Replace only the first occurrence of this link
            # This avoids replacing multiple references to the same product
            new_content = new_content.replace(match_text, rich_html, 1)
            modified = True
            
            print(f"  Enhanced: {product['title'][:50]}...")
        
        # Write back to file if modified and not dry run
        if modified and not dry_run:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"✓ Updated {file_path}")
        
        return modified
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}", file=sys.stderr)
        return False


def main():
    """Main function."""
    # Check for required credentials
    if not ACCESS_KEY or not SECRET_KEY:
        print("Error: AMAZON_ACCESS_KEY and AMAZON_SECRET_KEY environment variables must be set", file=sys.stderr)
        sys.exit(1)
    
    # Initialize Amazon API
    try:
        api = AmazonAPI(ACCESS_KEY, SECRET_KEY, PARTNER_TAG, COUNTRY)
    except Exception as e:
        print(f"Error initializing Amazon PA-API: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Get repository root
    repo_root = Path(__file__).parent.parent
    posts_dir = repo_root / '_posts'
    
    if not posts_dir.exists():
        print(f"Error: Posts directory not found: {posts_dir}", file=sys.stderr)
        sys.exit(1)
    
    # Process all markdown files
    markdown_files = list(posts_dir.glob('*.md'))
    print(f"Found {len(markdown_files)} markdown files")
    
    modified_count = 0
    for md_file in markdown_files:
        if process_markdown_file(md_file, api):
            modified_count += 1
    
    print(f"\n✓ Processing complete. Modified {modified_count} files.")


if __name__ == '__main__':
    main()
