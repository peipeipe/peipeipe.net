#!/usr/bin/env python3
"""
日記投稿キューを処理するスクリプト
"""

import os
import json
import yaml
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

def process_diary_queue():
    """キューファイルを処理して日記エントリを作成"""
    
    queue_dir = Path('_queue')
    if not queue_dir.exists():
        print("キューディレクトリが存在しません")
        return
    
    json_files = list(queue_dir.glob('*.json'))
    if not json_files:
        print("処理するキューファイルがありません")
        return
    
    for queue_file in json_files:
        try:
            print(f"処理中: {queue_file}")
            
            # キューファイルを読み込み
            with open(queue_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            content = data.get('content', '')
            username = data.get('username', 'Web投稿')
            timestamp = data.get('timestamp', '')
            
            if not content.strip():
                print(f"空の内容: {queue_file}")
                queue_file.unlink()  # ファイルを削除
                continue
            
            # タイムスタンプから日時を取得
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    jst = timezone(timedelta(hours=9))
                    jst_dt = dt.astimezone(jst)
                except:
                    jst_dt = get_jst_now()
            else:
                jst_dt = get_jst_now()
            
            date_str = jst_dt.strftime('%Y-%m-%d')
            time_str = jst_dt.strftime('%H:%M')
            
            print(f"日記作成: {date_str} {time_str} - {username}")
            
            # 日記ディレクトリ
            diary_dir = Path('_diary')
            diary_dir.mkdir(exist_ok=True)
            
            file_path = diary_dir / f"{date_str}.md"
            
            # コンテンツをエスケープ
            escaped_content = escape_html(content.strip())
            
            # 新しいメッセージ
            new_message = f'''<div class="diary-message">
  <div class="diary-message-time">{time_str}</div>
  <div class="diary-message-content">{escaped_content}</div>
  <div class="diary-message-meta">🌐 {username}から投稿</div>
</div>'''
            
            if file_path.exists():
                # 既存ファイルを更新
                with open(file_path, 'r', encoding='utf-8') as f:
                    content_lines = f.readlines()
                
                # 新しいメッセージを追加
                content_lines.append('\n' + new_message + '\n')
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(content_lines)
                
                print(f"既存の日記ファイルを更新: {file_path}")
            
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
                
                print(f"新しい日記ファイルを作成: {file_path}")
            
            # 処理完了後、キューファイルを削除
            queue_file.unlink()
            print(f"キューファイルを削除: {queue_file}")
            
        except Exception as e:
            print(f"エラー処理中 {queue_file}: {e}")
            # エラーが発生してもファイルは削除（無限ループを防ぐ）
            queue_file.unlink()

if __name__ == '__main__':
    process_diary_queue()
