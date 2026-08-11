#!/usr/bin/env python3
"""
Test script for Amazon link enhancement without requiring PA-API credentials.
This script validates ASIN extraction and link detection logic.
"""

import re
import sys
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent))

from enhance_amazon_links import (
    enhance_bare_amazon_urls,
    extract_asin,
    extract_title_from_page,
    find_bare_amazon_url_lines,
    find_simple_amazon_links,
    load_book_titles,
    remove_duplicate_generic_amazon_cards,
    remove_legacy_image_links_before_cards,
)


def test_asin_extraction():
    """Test ASIN extraction from various URL formats."""
    print("=" * 60)
    print("Testing ASIN Extraction")
    print("=" * 60)
    
    test_cases = [
        ('http://www.amazon.co.jp/exec/obidos/ASIN/4062737388/peipeipe-22/ref=nosim/', '4062737388'),
        ('https://www.amazon.co.jp/dp/B084MCR9KG', 'B084MCR9KG'),
        ('https://www.amazon.co.jp/dp/B084MCR9KG?linkCode=li2&tag=peipeipe-22', 'B084MCR9KG'),
        ('https://www.amazon.co.jp/gp/product/B09NVKTTM5', 'B09NVKTTM5'),
        ('http://www.amazon.co.jp/exec/obidos/asin/415209656X/peipeipe-22/', '415209656X'),
    ]
    
    passed = 0
    failed = 0
    
    for url, expected_asin in test_cases:
        extracted = extract_asin(url)
        
        if extracted == expected_asin:
            print(f"✓ PASS: {url[:50]}...")
            print(f"  Expected: {expected_asin}, Got: {extracted}")
            passed += 1
        else:
            print(f"✗ FAIL: {url[:50]}...")
            print(f"  Expected: {expected_asin}, Got: {extracted}")
            failed += 1
    
    print(f"\nResults: {passed} passed, {failed} failed\n")
    return failed == 0


def test_link_detection():
    """Test link detection in markdown content."""
    print("=" * 60)
    print("Testing Link Detection")
    print("=" * 60)
    
    test_content = """---
layout: post
title: "Test"
---

Simple markdown links (should be found):
[Product 1](https://www.amazon.co.jp/dp/B084MCR9KG)
[Product 2](http://www.amazon.co.jp/exec/obidos/ASIN/4062737388/peipeipe-22/ref=nosim/)

Generic helper link (should be skipped):
[Amazon](http://www.amazon.co.jp/exec/obidos/ASIN/4105430017/peipeipe-22/)

Legacy image link (should be skipped):
[![Product 3](https://m.media-amazon.com/images/I/product.jpg "Product 3")](https://www.amazon.co.jp/exec/obidos/ASIN/4105430017/peipeipe-22/)

Complex widget (should be skipped):
<div class="krb-amzlt-box">
  <a href="https://amzn.to/3VFbQSJ">Product</a>
</div>

Already enhanced (should be skipped):
<div class="amazon-product-card">
  <a href="https://www.amazon.co.jp/dp/XXXXXXXXXX">Product</a>
</div>
"""
    
    # Test 1: Skip detection
    print("\nTest 1: Skip logic for complex widgets")
    if re.search(r'<div class="krb-amzlt-box"', test_content):
        print("✓ PASS: Correctly detected krb-amzlt-box widget")
    else:
        print("✗ FAIL: Did not detect krb-amzlt-box widget")
    
    # Test 2: Markdown link detection
    print("\nTest 2: Markdown link detection")
    matches = find_simple_amazon_links(test_content)
    
    if len(matches) == 2:
        print(f"✓ PASS: Found {len(matches)} markdown links")
        for i, (_, link_text, _) in enumerate(matches, 1):
            print(f"  Link {i}: {link_text}")
    else:
        print(f"✗ FAIL: Expected 2 markdown links, found {len(matches)}")
        return False
    
    # Test 3: Skip already enhanced content
    print("\nTest 3: Skip already enhanced content")
    skip_pattern = r'(<div class="amazon-product-card".*?</div>\s*</div>\s*</div>|<div class="krb-amzlt-box".*?</div>)'
    if re.search(skip_pattern, test_content, re.DOTALL):
        print("✓ PASS: Correctly detected existing rich content")
    else:
        print("✗ FAIL: Did not detect existing rich content")
    
    print()
    return True


def test_bare_url_detection():
    """Test detection of standalone Amazon URL lines."""
    print("=" * 60)
    print("Testing Bare URL Detection")
    print("=" * 60)

    test_content = """---
title: "Test"
---

https://amzn.to/4qaqMGv

  https://www.amazon.co.jp/dp/B084MCR9KG

<https://amzn.asia/d/abcdef>

Markdown link (not bare):
[Product](https://amzn.to/3VFbQSJ)

Inline in prose (not bare): 詳しくは https://amzn.to/9999999 を見てください

Already a card (not bare):
<div class="krb-amzlt-box"><a href="https://amzn.to/3VFbQSJ">Product</a></div>

Not Amazon:
https://example.com/dp/B084MCR9KG
"""

    found = find_bare_amazon_url_lines(test_content)
    expected = [
        'https://amzn.to/4qaqMGv',
        'https://www.amazon.co.jp/dp/B084MCR9KG',
        'https://amzn.asia/d/abcdef',
    ]

    if [url for _, url in found] != expected:
        print(f"✗ FAIL: Expected {expected}")
        print(f"  Got: {[url for _, url in found]}")
        return False

    print(f"✓ PASS: Found {len(found)} bare URL(s), skipped links/cards/prose")
    print()
    return True


def test_bare_url_enhancement():
    """Test that a bare URL line becomes a card with a cover image and title."""
    print("=" * 60)
    print("Testing Bare URL Enhancement")
    print("=" * 60)

    book_titles = load_book_titles()
    if not book_titles:
        print("✗ FAIL: No book titles loaded from books.json")
        return False

    # Use real book data so the title resolves without touching the network.
    asin, title = next(iter(book_titles.items()))
    content = f"""今月読んだ本。

https://www.amazon.co.jp/dp/{asin}

> 引用

https://www.amazon.co.jp/dp/{asin}
"""

    enhanced, count = enhance_bare_amazon_urls(content, set())

    if count != 1:
        print(f"✗ FAIL: Expected 1 enhanced URL (second is a duplicate ASIN), got {count}")
        return False

    if f'https://images-na.ssl-images-amazon.com/images/P/{asin}.09.LZZZZZZZ' not in enhanced:
        print("✗ FAIL: Cover image URL missing from the card")
        return False

    if f'>{title}</a>' not in enhanced:
        print(f"✗ FAIL: Title '{title}' missing from the card")
        return False

    if '> 引用' not in enhanced:
        print("✗ FAIL: Surrounding content was damaged")
        return False

    print(f"✓ PASS: Bare URL became a card — {title[:40]}")
    print()
    return True


def test_page_title_extraction():
    """Test pulling a product title out of Amazon product page HTML."""
    print("=" * 60)
    print("Testing Product Page Title Extraction")
    print("=" * 60)

    cases = [
        (
            '<span id="productTitle" class="a-size-large">  沖縄から貧困がなくならない本当の理由  </span>',
            '沖縄から貧困がなくならない本当の理由',
        ),
        (
            '<meta property="og:title" content="Product &amp; Co." />',
            'Product & Co.',
        ),
        ('<html><body>No title here</body></html>', None),
    ]

    passed = 0
    failed = 0

    for page_html, expected in cases:
        result = extract_title_from_page(page_html)
        if result == expected:
            print(f"✓ PASS: {expected!r}")
            passed += 1
        else:
            print(f"✗ FAIL: Expected {expected!r}, got {result!r}")
            failed += 1

    print(f"\nResults: {passed} passed, {failed} failed\n")
    return failed == 0


def test_duplicate_generic_card_cleanup():
    """Test cleanup of cards created from generic [Amazon](...) helper links."""
    print("=" * 60)
    print("Testing Duplicate Generic Card Cleanup")
    print("=" * 60)

    content = """<div class="krb-amzlt-box" style="margin-bottom:0px;"><div class="krb-amzlt-image"><a href="https://www.amazon.co.jp/dp/415209656X?tag=peipeipe-22"><img src="https://images-na.ssl-images-amazon.com/images/P/415209656X.09.LZZZZZZZ"></a></div><div class="krb-amzlt-info"><div class="krb-amzlt-name"><a href="https://www.amazon.co.jp/dp/415209656X?tag=peipeipe-22">プレイバック</a></div><div class="krb-amzlt-detail"></div></div></div>
<div class="krb-amzlt-box" style="margin-bottom:0px;"><div class="krb-amzlt-image"><a href="https://www.amazon.co.jp/dp/415209656X?tag=peipeipe-22"><img src="https://images-na.ssl-images-amazon.com/images/P/415209656X.09.LZZZZZZZ"></a></div><div class="krb-amzlt-info"><div class="krb-amzlt-name"><a href="https://www.amazon.co.jp/dp/415209656X?tag=peipeipe-22">Amazon</a></div><div class="krb-amzlt-detail"></div></div></div>
"""

    cleaned, removed_count = remove_duplicate_generic_amazon_cards(content)

    if removed_count != 1:
        print(f"✗ FAIL: Expected 1 removed card, got {removed_count}")
        return False

    if ">Amazon</a></div><div class=\"krb-amzlt-detail\"" in cleaned:
        print("✗ FAIL: Generic duplicate card was not removed")
        return False

    if "プレイバック" not in cleaned:
        print("✗ FAIL: Product card was removed")
        return False

    print("✓ PASS: Removed generic duplicate card only")
    print()
    return True


def test_legacy_image_link_cleanup():
    """Test cleanup of duplicated old Hatena image links."""
    print("=" * 60)
    print("Testing Legacy Image Link Cleanup")
    print("=" * 60)

    content = """Before

[![我が父サリンジャー](https://m.media-amazon.com/images/I/41JAX769Y1L._SL300_.jpg "我が父サリンジャー")](https://www.amazon.co.jp/exec/obidos/ASIN/4105430017/peipeipe-22/)


<div class="krb-amzlt-box" style="margin-bottom:0px;"><div class="krb-amzlt-image"><a href="https://www.amazon.co.jp/dp/4105430017?tag=peipeipe-22"><img src="https://images-na.ssl-images-amazon.com/images/P/4105430017.09.LZZZZZZZ"></a></div></div>

 [![](https://cdn-ak.f.st-hatena.com/images/fotolife/p/peipeipe/20190630/20190630171113.webp)](http://www.amazon.co.jp/exec/obidos/asin/415209656X/peipeipe-22/)

<div class="krb-amzlt-box" style="margin-bottom:0px;"><div class="krb-amzlt-image"><a href="https://www.amazon.co.jp/dp/415209656X?tag=peipeipe-22"><img src="https://images-na.ssl-images-amazon.com/images/P/415209656X.09.LZZZZZZZ"></a></div></div>

[![Different product](https://example.com/image.jpg)](https://www.amazon.co.jp/exec/obidos/ASIN/B000000000/peipeipe-22/)

After
"""

    cleaned, removed_count = remove_legacy_image_links_before_cards(content)

    if removed_count != 2:
        print(f"✗ FAIL: Expected 2 removed links, got {removed_count}")
        return False

    if "我が父サリンジャー" in cleaned:
        print("✗ FAIL: Duplicate legacy image link was not removed")
        return False

    if "20190630171113.webp" in cleaned:
        print("✗ FAIL: Lowercase /asin/ legacy image link was not removed")
        return False

    if "Different product" not in cleaned:
        print("✗ FAIL: Non-duplicated legacy image link was removed")
        return False

    print("✓ PASS: Removed only the duplicated legacy image link")
    print()
    return True


def test_html_escaping():
    """Test HTML escaping for security."""
    print("=" * 60)
    print("Testing HTML Escaping")
    print("=" * 60)
    
    import html
    
    test_cases = [
        ('<script>alert("xss")</script>', '&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;'),
        ('Product & Co.', 'Product &amp; Co.'),
        ('Book "Title"', 'Book &quot;Title&quot;'),
    ]
    
    passed = 0
    failed = 0
    
    for input_str, expected in test_cases:
        result = html.escape(input_str)
        if result == expected:
            print(f"✓ PASS: '{input_str}' -> '{result}'")
            passed += 1
        else:
            print(f"✗ FAIL: '{input_str}'")
            print(f"  Expected: {expected}")
            print(f"  Got: {result}")
            failed += 1
    
    print(f"\nResults: {passed} passed, {failed} failed\n")
    return failed == 0


def test_markdown_files():
    """Test finding markdown files in the Astro posts directory."""
    print("=" * 60)
    print("Testing Markdown File Discovery")
    print("=" * 60)
    
    repo_root = Path(__file__).parent.parent
    posts_dir = repo_root / 'astro' / 'content' / 'posts'
    
    if not posts_dir.exists():
        print(f"✗ FAIL: Posts directory not found: {posts_dir}")
        return False
    
    markdown_files = list(posts_dir.glob('*.md'))
    print(f"✓ Found {len(markdown_files)} markdown files in {posts_dir}")
    
    # Show first 5 files
    for i, md_file in enumerate(markdown_files[:5], 1):
        print(f"  {i}. {md_file.name}")
    
    if len(markdown_files) > 5:
        print(f"  ... and {len(markdown_files) - 5} more")
    
    print()
    return True


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("Amazon PA-API Integration - Test Suite")
    print("=" * 60 + "\n")
    
    results = []
    
    results.append(("ASIN Extraction", test_asin_extraction()))
    results.append(("Link Detection", test_link_detection()))
    results.append(("Bare URL Detection", test_bare_url_detection()))
    results.append(("Bare URL Enhancement", test_bare_url_enhancement()))
    results.append(("Product Page Title Extraction", test_page_title_extraction()))
    results.append(("Legacy Image Cleanup", test_legacy_image_link_cleanup()))
    results.append(("Duplicate Generic Card Cleanup", test_duplicate_generic_card_cleanup()))
    results.append(("HTML Escaping", test_html_escaping()))
    results.append(("File Discovery", test_markdown_files()))
    
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n✓ All tests passed!")
        return 0
    else:
        print("\n✗ Some tests failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
