#!/bin/bash

# 仮想環境をアクティベートしてBotを起動する簡単なコマンド
# 使い方: ./run_bot.sh

cd "$(dirname "$0")"
source diary_bot_env/bin/activate
python scripts/discord_bot.py
