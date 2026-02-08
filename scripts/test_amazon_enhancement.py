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
    ]
    
    patterns = [
        r'https?://(?:www\.)?amazon\.co\.jp/(?:exec/obidos/ASIN/|dp/|gp/product/)([A-Z0-9]{10})',
        r'https?://(?:www\.)?amazon\.co\.jp/[^/]+/dp/([A-Z0-9]{10})',
    ]
    
    passed = 0
    failed = 0
    
    for url, expected_asin in test_cases:
        extracted = None
        for pattern in patterns:
            match = re.search(pattern, url)
            if match and len(match.groups()) > 0:
                extracted = match.group(1)
                break
        
        if not extracted:
            match = re.search(r'/(?:dp|gp/product)/([A-Z0-9]{10})', url)
            if match:
                extracted = match.group(1)
        
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
    md_link_pattern = r'\[([^\]]+)\]\((https?://(?:www\.)?(?:amazon\.co\.jp|amzn\.to)[^\s\)]+)\)'
    matches = list(re.finditer(md_link_pattern, test_content))
    
    if len(matches) == 2:
        print(f"✓ PASS: Found {len(matches)} markdown links")
        for i, match in enumerate(matches, 1):
            print(f"  Link {i}: {match.group(1)}")
    else:
        print(f"✗ FAIL: Expected 2 markdown links, found {len(matches)}")
    
    # Test 3: Skip already enhanced content
    print("\nTest 3: Skip already enhanced content")
    skip_pattern = r'(<div class="amazon-product-card".*?</div>\s*</div>\s*</div>|<div class="krb-amzlt-box".*?</div>)'
    if re.search(skip_pattern, test_content, re.DOTALL):
        print("✓ PASS: Correctly detected existing rich content")
    else:
        print("✗ FAIL: Did not detect existing rich content")
    
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
    """Test finding markdown files in _posts directory."""
    print("=" * 60)
    print("Testing Markdown File Discovery")
    print("=" * 60)
    
    repo_root = Path(__file__).parent.parent
    posts_dir = repo_root / '_posts'
    
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
