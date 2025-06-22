#!/usr/bin/env python3
"""
Discord日記ボット
Discordメッセージを受信してGitHub Actionsをトリガーする
"""

import discord
import asyncio
import aiohttp
import json
import os
from datetime import datetime, timezone, timedelta
from typing import Optional
from pathlib import Path

# .envファイルを読み込む関数
def load_env():
    """Load environment variables from .env file"""
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    os.environ[key] = value
    else:
        print(f".env file not found at {env_path}")

# .envファイルを読み込み
load_env()

class DiaryBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        
        # GitHub設定
        self.github_token = os.getenv('GITHUB_TOKEN')
        self.github_repo = os.getenv('GITHUB_REPO', 'username/peipeipe.net')  # あなたのリポジトリに変更
        self.webhook_url = f"https://api.github.com/repos/{self.github_repo}/dispatches"
        
        # 対象チャンネルID（環境変数から取得）
        self.target_channel_id = int(os.getenv('DISCORD_CHANNEL_ID', '0'))
        
        # 日本時間のタイムゾーン
        self.jst = timezone(timedelta(hours=9))

    async def on_ready(self):
        print(f'{self.user}としてログインしました')
        print(f'対象チャンネルID: {self.target_channel_id}')

    async def on_message(self, message):
        # ボット自身のメッセージは無視
        if message.author == self.user:
            return
        
        # 指定されたチャンネル以外は無視
        if message.channel.id != self.target_channel_id:
            return
        
        # メッセージが空の場合は無視
        if not message.content.strip():
            return
        
        print(f"日記メッセージを受信: {message.content}")
        
        # GitHub Actionsをトリガー
        await self.trigger_github_action(message)
        
        # 確認リアクション
        await message.add_reaction('📝')

    async def trigger_github_action(self, message: discord.Message):
        """GitHub Actionsワークフローをトリガーする"""
        
        # 日本時間で現在時刻を取得
        jst_time = datetime.now(self.jst)
        
        payload = {
            'event_type': 'diary_entry',
            'client_payload': {
                'content': message.content,
                'timestamp': jst_time.isoformat(),
                'date': jst_time.strftime('%Y-%m-%d'),
                'time': jst_time.strftime('%H:%M'),
                'author': str(message.author),
                'channel': str(message.channel)
            }
        }
        
        headers = {
            'Authorization': f'token {self.github_token}',
            'Accept': 'application/vnd.github.v3+json',
            'Content-Type': 'application/json'
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    headers=headers,
                    data=json.dumps(payload)
                ) as response:
                    if response.status == 204:
                        print("GitHub Actionsを正常にトリガーしました")
                    else:
                        print(f"GitHub Actionsのトリガーに失敗: {response.status}")
                        print(await response.text())
        except Exception as e:
            print(f"エラーが発生しました: {e}")

def main():
    # 環境変数チェック
    discord_token = os.getenv('DISCORD_TOKEN')
    if not discord_token:
        print("エラー: DISCORD_TOKEN環境変数が設定されていません")
        return
    
    github_token = os.getenv('GITHUB_TOKEN')
    if not github_token:
        print("エラー: GITHUB_TOKEN環境変数が設定されていません")
        return
    
    channel_id = os.getenv('DISCORD_CHANNEL_ID')
    if not channel_id:
        print("エラー: DISCORD_CHANNEL_ID環境変数が設定されていません")
        return
    
    # ボットを実行
    bot = DiaryBot()
    bot.run(discord_token)

if __name__ == '__main__':
    main()
