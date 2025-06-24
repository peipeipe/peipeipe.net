#!/usr/bin/env python3
"""
実際の画像ダウンロードテスト
"""

import requests
import io
from pathlib import Path
from PIL import Image

def test_image_download():
    image_url = "https://github.com/user-attachments/assets/a47409a1-4cb9-43b1-9022-afed68c8354f"
    
    try:
        print(f"画像ダウンロード開始: {image_url}")
        
        # 画像をダウンロード
        response = requests.get(image_url, timeout=30)
        response.raise_for_status()
        
        print(f"ダウンロード成功: {len(response.content)} bytes")
        
        # PILで画像を開いてみる
        image = Image.open(io.BytesIO(response.content))
        print(f"画像サイズ: {image.size}")
        print(f"画像モード: {image.mode}")
        
        # WebPに変換
        webp_buffer = io.BytesIO()
        image.save(webp_buffer, format='WEBP', quality=85, optimize=True)
        webp_data = webp_buffer.getvalue()
        
        print(f"WebP変換成功: {len(webp_data)} bytes")
        
        # 保存テスト
        test_dir = Path('images/2025-06-24')
        test_dir.mkdir(parents=True, exist_ok=True)
        
        test_path = test_dir / 'test.webp'
        with open(test_path, 'wb') as f:
            f.write(webp_data)
        
        print(f"保存成功: {test_path}")
        
    except Exception as e:
        print(f"エラー: {e}")

if __name__ == '__main__':
    test_image_download()
