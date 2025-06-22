#!/usr/bin/env python3
"""
画像付き日記投稿のテストスクリプト
"""

import requests
import json
import base64
from pathlib import Path

def test_image_diary():
    """画像付き日記投稿をテスト"""
    
    # 小さなテスト画像（1x1ピクセルの透明PNG）を作成
    test_image_base64 = """iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChAI9jU77ygAAAABJRU5ErkJggg=="""
    
    # GitHub API用のデータ
    payload = {
        "event_type": "diary_entry",
        "client_payload": {
            "content": "画像付きテスト投稿！🖼️",
            "date": "2025-06-22",
            "time": "23:00", 
            "image": f"data:image/png;base64,{test_image_base64}",
            "image_filename": "test.png"
        }
    }
    
    print("画像付き日記投稿テスト:")
    print(f"内容: {payload['client_payload']['content']}")
    print(f"画像: {payload['client_payload']['image_filename']}")
    print("\n実際の投稿にはGitHub Personal Access Tokenが必要です")
    print("iPhoneショートカットでテストしてください！")

if __name__ == '__main__':
    test_image_diary()
