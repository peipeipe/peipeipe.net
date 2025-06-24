#!/usr/bin/env python3
"""
画像URL検出のテスト
"""

import re

def test_image_detection():
    # テスト用の文字列（実際の投稿内容）
    test_content = "猫![image](https://github.com/user-attachments/assets/a47409a1-4cb9-43b1-9022-afed68c8354f)"
    
    print(f"テスト内容: {test_content}")
    print("=" * 50)
    
    # パターンリスト
    patterns = [
        r'!\[[^\]]*\]\(https://github\.com/user-attachments/assets/[^)]+\)',
        r'!\[[^\]]*\]\(https://user-images\.githubusercontent\.com/[^)]+\)',
        r'https://github\.com/user-attachments/assets/[^)\s]+',
    ]
    
    for i, pattern in enumerate(patterns):
        print(f"パターン {i+1}: {pattern}")
        matches = re.finditer(pattern, test_content, re.IGNORECASE)
        
        found_matches = list(matches)
        if found_matches:
            for match in found_matches:
                print(f"  ✅ マッチ: {match.group(0)}")
                
                # Markdownの場合、URLを抽出
                if match.group(0).startswith('!['):
                    url_match = re.search(r'\(([^)]+)\)', match.group(0))
                    if url_match:
                        print(f"  📎 抽出URL: {url_match.group(1)}")
        else:
            print(f"  ❌ マッチなし")
        print()

if __name__ == '__main__':
    test_image_detection()
