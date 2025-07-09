#!/usr/bin/env python3
"""
GitHub Issues を日記エントリに変換するスクリプト
"""

import os
import yaml
import re
import requests
import base64
import io
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlparse
from PIL import Image
import io

def escape_html(text):
    """HTMLエスケープ"""
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    text = text.replace('"', '&quot;')
    text = text.replace("'", '&#x27;')
    return text

def get_jst_now():
    """日本時間の現在時刻を取得"""
    jst = timezone(timedelta(hours=9))
    return datetime.now(jst)

def convert_to_webp(image_data, quality=85, max_width=1200):
    """画像データをWebPに変換（リサイズ・Exif削除機能付き）"""
    try:
        # バイナリデータからPIL Imageオブジェクトを作成
        image = Image.open(io.BytesIO(image_data))
        original_size = image.size
        
        # Exifデータを確認・削除
        exif_info = []
        if hasattr(image, '_getexif') and image._getexif() is not None:
            exif_dict = image._getexif()
            
            # よく含まれるExif情報をチェック
            dangerous_tags = {
                34853: 'GPS情報',  # GPSInfo
                306: '撮影日時',    # DateTime
                271: 'カメラメーカー',  # Make
                272: 'カメラモデル',   # Model
                37500: 'メーカーノート'  # MakerNote
            }
            
            for tag_id, description in dangerous_tags.items():
                if tag_id in exif_dict:
                    exif_info.append(description)
            
            if exif_info:
                print(f"⚠️  検出されたExifデータ: {', '.join(exif_info)}")
                print("🔒 これらの情報は完全に削除されます")
            else:
                print("✅ 危険なExifデータなし")
        else:
            print("✅ Exifデータなし")
        
        # 画像をリサイズ（幅が最大幅を超える場合）
        if image.width > max_width:
            # アスペクト比を保持してリサイズ
            ratio = max_width / image.width
            new_height = int(image.height * ratio)
            image = image.resize((max_width, new_height), Image.Resampling.LANCZOS)
            print(f"画像リサイズ: {original_size[0]}x{original_size[1]} -> {image.width}x{image.height}")
        
        # RGBAモードの処理（透明度対応）
        if image.mode in ('RGBA', 'LA', 'P'):
            # 透明度がある場合はそのまま保持
            pass
        elif image.mode != 'RGB':
            image = image.convert('RGB')
        
        # WebP形式でバイナリデータに変換（Exifデータは自動的に削除される）
        webp_buffer = io.BytesIO()
        image.save(webp_buffer, format='WEBP', quality=quality, optimize=True)
        webp_data = webp_buffer.getvalue()
        
        # 元のサイズと変換後のサイズを表示
        original_file_size = len(image_data)
        webp_file_size = len(webp_data)
        compression_ratio = (1 - webp_file_size / original_file_size) * 100
        
        print(f"WebP変換: {original_file_size:,} bytes -> {webp_file_size:,} bytes (-{compression_ratio:.1f}%)")
        print("🔒 プライバシー保護: Exif/GPSデータは完全に削除されました")
        
        return webp_data
        
    except Exception as e:
        print(f"WebP変換エラー: {e}")
        return image_data  # 変換に失敗した場合は元のデータを返す

def download_and_save_image(image_url, date_str, time_str):
    """GitHub画像URLから画像をダウンロードして保存"""
    try:
        print(f"画像ダウンロード開始: {image_url}")
        
        # 画像をダウンロード
        response = requests.get(image_url, timeout=30)
        response.raise_for_status()
        
        # 元の拡張子を取得（ログ用）
        parsed_url = urlparse(image_url)
        path_parts = parsed_url.path.split('.')
        original_ext = 'unknown'
        if len(path_parts) > 1:
            original_ext = path_parts[-1].lower()
        
        # WebPに変換
        webp_data = convert_to_webp(response.content)
        
        # 保存ディレクトリを作成（日付別フォルダ）
        image_dir = Path(f'images/{date_str}')
        image_dir.mkdir(parents=True, exist_ok=True)
        
        # ファイル名を生成（WebP形式で保存）
        timestamp = time_str.replace(':', '')
        filename = f"{timestamp}.webp"
        image_path = image_dir / filename
        
        # 画像を保存
        with open(image_path, 'wb') as f:
            f.write(webp_data)
        
        print(f"画像を保存しました ({original_ext} -> webp): {image_path}")
        return f"/images/{date_str}/{filename}"
        
    except Exception as e:
        print(f"画像保存エラー ({image_url}): {e}")
        return None

def process_images_in_content(content, date_str, time_str):
    """GitHubの画像URLを見つけて、ローカルに保存し、パスを更新"""
    print("画像URLの検索と処理を開始...")
    print(f"検索対象の内容: {content[:500]}...")  # デバッグ用
    
    # GitHub画像URLのパターン（user-attachments、camo、raw.githubusercontent.com など）
    github_image_patterns = [
        r'!\[[^\]]*\]\(https://github\.com/user-attachments/assets/[^)]+\)',
        r'!\[[^\]]*\]\(https://user-images\.githubusercontent\.com/[^)]+\)',
        r'!\[[^\]]*\]\(https://camo\.githubusercontent\.com/[^)]+\)',
        r'!\[[^\]]*\]\(https://raw\.githubusercontent\.com/[^)]+\.(png|jpg|jpeg|gif|webp)\)',
        r'!\[[^\]]*\]\(https://github-production-user-asset-[^)]+\.s3\.amazonaws\.com/[^)]+\)',
        r'!\[[^\]]*\]\(https://private-user-images\.githubusercontent\.com/[^)]+\)',
        r'https://github\.com/user-attachments/assets/[^)\s]+',
        r'https://user-images\.githubusercontent\.com/[^)\s]+',
        r'https://camo\.githubusercontent\.com/[^)\s]+',
        r'https://raw\.githubusercontent\.com/[^)\s]+\.(png|jpg|jpeg|gif|webp)',
        r'https://github-production-user-asset-[^)\s]+\.s3\.amazonaws\.com/[^)\s]+'
    ]
    
    updated_content = content
    image_counter = 1
    
    for pattern in github_image_patterns:
        print(f"パターン検索中: {pattern}")  # デバッグ用
        matches = re.finditer(pattern, updated_content, re.IGNORECASE)
        for match in matches:
            image_url = match.group(0)
            print(f"GitHub画像URL発見: {image_url}")
            
            # Markdownリンクの場合はURLを抽出
            if image_url.startswith('!['):
                # ![...](URL) からURLを抽出
                url_match = re.search(r'\(([^)]+)\)', image_url)
                if url_match:
                    actual_url = url_match.group(1)
                    print(f"Markdownから抽出したURL: {actual_url}")
                else:
                    continue
            else:
                actual_url = image_url
            
            # クエリパラメータを除去
            clean_url = actual_url.split('?')[0].split('#')[0]
            
            # 画像をダウンロードして保存
            local_path = download_and_save_image(clean_url, date_str, f"{time_str}-{image_counter:02d}")
            
            if local_path:
                # 元のマッチした文字列を置換
                if image_url.startswith('!['):
                    # Markdownリンクの場合
                    updated_content = updated_content.replace(image_url, f"![画像 {image_counter}]({local_path})")
                    print(f"Markdownリンク置換: {image_url} -> ![画像 {image_counter}]({local_path})")
                else:
                    # 単純なURL置換
                    updated_content = updated_content.replace(image_url, local_path)
                    print(f"画像URL置換: {image_url} -> {local_path}")
                image_counter += 1
    
    if image_counter == 1:
        print("画像URLは見つかりませんでした")
    else:
        print(f"合計 {image_counter - 1} 個の画像を処理しました")
    
    return updated_content

def create_diary_from_issue():
    """Issueから日記エントリを作成"""
    
    # 環境変数から情報を取得
    issue_title = os.getenv('ISSUE_TITLE', '')
    issue_body = os.getenv('ISSUE_BODY', '')
    issue_number = os.getenv('ISSUE_NUMBER', '')
    issue_url = os.getenv('ISSUE_URL', '')
    issue_user = os.getenv('ISSUE_USER', 'Unknown')
    
    if not issue_body.strip():
        print("エラー: Issue内容が空です")
        return
    
    # 現在の日本時間を取得
    jst_now = get_jst_now()
    date_str = jst_now.strftime('%Y-%m-%d')
    time_str = jst_now.strftime('%H:%M')
    
    print(f"Issue から日記作成: {date_str} {time_str}")
    print(f"投稿者: {issue_user}")
    print(f"内容: {issue_body[:100]}...")
    
    # ファイルパス
    diary_dir = Path('_diary')
    diary_dir.mkdir(exist_ok=True)
    
    file_path = diary_dir / f"{date_str}.md"
    
    # 画像処理：GitHub画像URLをローカルに保存
    processed_content = process_images_in_content(issue_body.strip(), date_str, time_str)
    
    # 新しいメッセージ（Markdown形式）
    new_message = f'''## {time_str}
{processed_content}'''
    
    if file_path.exists():
        # 既存ファイルを更新
        with open(file_path, 'r', encoding='utf-8') as f:
            content_lines = f.readlines()
        
        # Front matterの終わりを見つける
        front_matter_end = -1
        front_matter_count = 0
        for i, line in enumerate(content_lines):
            if line.strip() == '---':
                front_matter_count += 1
                if front_matter_count == 2:
                    front_matter_end = i
                    break
        
        if front_matter_end == -1:
            print("エラー: Front matterが見つかりません")
            return
        
        # 新しいメッセージを追加
        content_lines.append('\n' + new_message + '\n')
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(content_lines)
        
        print(f"既存の日記ファイルを更新しました: {file_path}")
    
    else:
        # 新しいファイルを作成
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            weekday = ['月', '火', '水', '木', '金', '土', '日'][date_obj.weekday()]
            formatted_date = f"{date_obj.year}年{date_obj.month:02d}月{date_obj.day:02d}日({weekday})"
        except:
            formatted_date = date_str
        
        front_matter = {
            'layout': 'diary',
            'title': f'{formatted_date}',
            'date': f'{date_str} 00:00:00 +0900'
        }
        
        content_text = f"""---
{yaml.dump(front_matter, default_flow_style=False, allow_unicode=True)}---

{new_message}
"""
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content_text)
        
        print(f"新しい日記ファイルを作成しました: {file_path}")

if __name__ == '__main__':
    create_diary_from_issue()
