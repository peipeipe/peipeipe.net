#!/usr/bin/env python3
"""
iOS ショートカット用のGitHub API呼び出しテストスクリプト
"""

import requests
import json
import sys
from datetime import datetime, timezone, timedelta

def trigger_github_action(github_token, repo, message):
    """GitHub repository_dispatch APIを呼び出して日記を更新"""
    
    # 日本時間を取得
    jst = timezone(timedelta(hours=9))
    now = datetime.now(jst)
    
    # GitHub API エンドポイント
    url = f"https://api.github.com/repos/{repo}/dispatches"
    
    # ペイロード
    payload = {
        "event_type": "ios_diary",
        "client_payload": {
            "content": message,
            "date": now.strftime('%Y-%m-%d'),
            "time": now.strftime('%H:%M'),
            "timestamp": now.isoformat(),
            "source": "iOS"
        }
    }
    
    # ヘッダー
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        
        if response.status_code == 204:
            print(f"✅ 日記更新をトリガーしました")
            print(f"📝 メッセージ: {message}")
            print(f"⏰ 時刻: {now.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"🔗 Actions: https://github.com/{repo}/actions")
            return True
        else:
            print(f"❌ 失敗: {response.status_code}")
            print(f"レスポンス: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ エラー: {e}")
        return False

def main():
    import os
    
    # 環境変数から取得を優先
    github_token = os.getenv('GITHUB_TOKEN')
    repo = os.getenv('GITHUB_REPO')
    
    if len(sys.argv) < 2:
        print("使い方:")
        print("  python ios_test.py <メッセージ>")
        print("")
        print("例:")
        print("  GITHUB_TOKEN='ghp_xxxx' GITHUB_REPO='peipeipe/peipeipe.net' python ios_test.py '今日はいい天気だね'")
        print("")
        print("または直接指定:")
        print("  python ios_test.py <github_token> <repo> <メッセージ>")
        return
    
    if github_token and repo and len(sys.argv) >= 2:
        # 環境変数から取得 + メッセージは引数
        message = " ".join(sys.argv[1:])
    elif len(sys.argv) >= 4:
        # 全て引数から取得
        github_token = sys.argv[1]
        repo = sys.argv[2]
        message = " ".join(sys.argv[3:])
    else:
        print("❌ GitHub TokenまたはRepo名が設定されていません")
        print("環境変数 GITHUB_TOKEN と GITHUB_REPO を設定するか、引数で指定してください")
        return
    
    if not github_token or not repo:
        print("❌ GitHub TokenまたはRepo名が設定されていません")
        return
    
    trigger_github_action(github_token, repo, message)

if __name__ == "__main__":
    main()
