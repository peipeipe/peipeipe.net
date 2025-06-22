#!/usr/bin/env python3
"""
Discord Webhook経由で日記を更新するテストスクリプト
"""

import requests
import json
import sys
from datetime import datetime, timezone, timedelta

def send_to_webhook(webhook_url, message):
    """Discord Webhookにメッセージを送信"""
    
    # 日本時間を取得
    jst = timezone(timedelta(hours=9))
    now = datetime.now(jst)
    
    # Discordに送信するペイロード
    payload = {
        "content": message,
        "username": "日記ボット",
        "avatar_url": "https://cdn.discordapp.com/embed/avatars/0.png"
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(webhook_url, data=json.dumps(payload), headers=headers)
        if response.status_code == 204:
            print(f"✅ メッセージを送信しました: {message}")
            print(f"⏰ 時刻: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print(f"❌ 送信失敗: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ エラー: {e}")

def main():
    # Webhook URLを環境変数または引数から取得
    webhook_url = None
    
    if len(sys.argv) >= 3:
        webhook_url = sys.argv[1]
        message = " ".join(sys.argv[2:])
    else:
        print("使い方:")
        print("  python test_webhook.py <webhook_url> <メッセージ>")
        print("")
        print("例:")
        print("  python test_webhook.py 'https://discord.com/api/webhooks/...' '今日はいい天気だね'")
        return
    
    send_to_webhook(webhook_url, message)

if __name__ == "__main__":
    main()
