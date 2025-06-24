#!/usr/bin/env python3
"""
GitHub Issues を日記エントリに変換するスクリプト
"""

import os
import yaml
import re
import requests
import base64
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlparse

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

def download_and_save_image(image_url, date_str, time_str):
    """GitHub画像URLから画像をダウンロードして保存"""
    try:
        print(f"画像ダウンロード開始: {image_url}")
        
        # 画像をダウンロード
        response = requests.get(image_url, timeout=30)
        response.raise_for_status()
        
        # ファイル拡張子を取得
        parsed_url = urlparse(image_url)
        path_parts = parsed_url.path.split('.')
        if len(path_parts) > 1:
            file_ext = path_parts[-1].lower()
            # よくある画像形式のみ許可
            if file_ext not in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
                file_ext = 'jpg'
        else:
            file_ext = 'jpg'
        
        # 保存ディレクトリを作成
        image_dir = Path('images/diary')
        image_dir.mkdir(parents=True, exist_ok=True)
        
        # ファイル名を生成（重複回避）
        timestamp = time_str.replace(':', '')
        filename = f"{date_str}-{timestamp}.{file_ext}"
        image_path = image_dir / filename
        
        # 画像を保存
        with open(image_path, 'wb') as f:
            f.write(response.content)
        
        print(f"画像を保存しました: {image_path}")
        return f"/images/diary/{filename}"
        
    except Exception as e:
        print(f"画像保存エラー ({image_url}): {e}")
        return None

def process_images_in_content(content, date_str, time_str):
    """GitHubの画像URLを見つけて、ローカルに保存し、パスを更新"""
    print("画像URLの検索と処理を開始...")
    
    # GitHub画像URLのパターン（user-attachments、camo、raw.githubusercontent.com など）
    github_image_patterns = [
        r'https://github\.com/[^/]+/[^/]+/assets/[^/]+/[^)\s]+',
        r'https://user-images\.githubusercontent\.com/[^)\s]+',
        r'https://camo\.githubusercontent\.com/[^)\s]+',
        r'https://raw\.githubusercontent\.com/[^)\s]+\.(png|jpg|jpeg|gif|webp)',
        r'https://github-production-user-asset-[^)\s]+\.s3\.amazonaws\.com/[^)\s]+'
    ]
    
    updated_content = content
    image_counter = 1
    
    for pattern in github_image_patterns:
        matches = re.finditer(pattern, updated_content, re.IGNORECASE)
        for match in matches:
            image_url = match.group(0)
            print(f"GitHub画像URL発見: {image_url}")
            
            # クエリパラメータを除去
            clean_url = image_url.split('?')[0].split('#')[0]
            
            # 画像をダウンロードして保存
            local_path = download_and_save_image(clean_url, date_str, f"{time_str}-{image_counter:02d}")
            
            if local_path:
                # Markdownリンクの場合はalt属性を設定
                if f"![]({image_url})" in updated_content:
                    updated_content = updated_content.replace(f"![]({image_url})", f"![画像 {image_counter}]({local_path})")
                    print(f"Markdownリンク（空のalt）を置換: ![画像 {image_counter}]({local_path})")
                elif f"![image]({image_url})" in updated_content:
                    updated_content = updated_content.replace(f"![image]({image_url})", f"![画像 {image_counter}]({local_path})")
                    print(f"Markdownリンク（image alt）を置換: ![画像 {image_counter}]({local_path})")
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
            'title': f'{formatted_date}の記録',
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
