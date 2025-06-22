#!/usr/bin/env python3
"""
Webhook用日記更新スクリプト
GitHub Actionsから呼ばれてMarkdownファイルを更新する
"""

import os
import yaml
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

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

def update_diary_entry():
    """日記エントリを更新する"""
    
    # 環境変数から情報を取得
    content = os.getenv('DIARY_CONTENT', '') or os.getenv('MANUAL_CONTENT', '')
    date_str = os.getenv('DIARY_DATE', '')
    time_str = os.getenv('DIARY_TIME', '')
    timestamp = os.getenv('DIARY_TIMESTAMP', '')
    username = os.getenv('MANUAL_USERNAME', '')
    
    if not content.strip():
        print("エラー: メッセージ内容が空です")
        return
    
    # 日時の処理
    if not date_str or not time_str:
        # 現在の日本時間を使用
        jst_now = get_jst_now()
        date_str = jst_now.strftime('%Y-%m-%d')
        time_str = jst_now.strftime('%H:%M')
        print(f"日時を自動設定: {date_str} {time_str}")
    
    print(f"日記更新: {date_str} {time_str} - {content}")
    if username:
        print(f"投稿者: {username}")
    
    # ファイルパス
    diary_dir = Path('_diary')
    diary_dir.mkdir(exist_ok=True)
    
    file_path = diary_dir / f"{date_str}.md"
    
    # 新しいメッセージ（Markdown形式）
    new_message = f'''
## {time_str}
{content.strip()}'''
    
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
        
        # 新しいメッセージを追加（時系列順に挿入）
        # 簡単のため、ファイルの最後に追加
        content_lines.append('\n' + new_message + '\n')
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(content_lines)
        
        print(f"既存の日記ファイルを更新しました: {file_path}")
    
    else:
        # 新しいファイルを作成
        # 日付をパース
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
    update_diary_entry()
