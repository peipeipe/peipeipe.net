#!/bin/bash

# Discord 日記ボット起動スクリプト

echo "🤖 Discord 日記ボットを起動しています..."

# 現在のディレクトリをスクリプトのディレクトリに変更
cd "$(dirname "$0")"

# .envファイルの存在確認
if [ ! -f ".env" ]; then
    echo "❌ .envファイルが見つかりません。"
    echo "   .envファイルを作成して以下の内容を設定してください："
    echo ""
    echo "   DISCORD_TOKEN=your_discord_bot_token_here"
    echo "   DISCORD_CHANNEL_ID=your_channel_id_here"
    echo "   GITHUB_TOKEN=your_github_token_here"
    echo "   GITHUB_REPO=your_username/peipeipe.net"
    echo ""
    exit 1
fi

# 仮想環境の確認と作成
if [ ! -d "diary_bot_env" ]; then
    echo "📦 Python仮想環境を作成しています..."
    python3 -m venv diary_bot_env
fi

# 仮想環境をアクティベート
echo "🔧 仮想環境をアクティベートしています..."
source diary_bot_env/bin/activate

# 必要なパッケージのインストール確認
if ! python -c "import discord" 2>/dev/null; then
    echo "📦 必要なパッケージをインストールしています..."
    pip install -r requirements.txt
fi

# ボットを起動
echo "✅ 設定ファイルを読み込み完了"
echo "🚀 Botを起動します... (Ctrl+C で停止)"
echo ""

python scripts/discord_bot.py
