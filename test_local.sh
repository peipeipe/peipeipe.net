#!/bin/bash

# ローカルテスト用簡単スクリプト

echo "🧪 Discord日記システム - ローカルテスト"
echo ""

# 仮想環境をアクティベート
source diary_bot_env/bin/activate

echo "テスト1: 日記更新スクリプトの直接実行"
DIARY_CONTENT="テストメッセージ: $(date '+%H:%M:%S') の記録" python scripts/update_diary_webhook.py
echo "✅ 完了"
echo ""

echo "テスト2: Webhook経由でDiscordにメッセージ送信"
echo "Webhook URLを入力してください（Enter で スキップ）:"
read webhook_url

if [ ! -z "$webhook_url" ]; then
    python scripts/test_webhook.py "$webhook_url" "ローカルテスト: $(date '+%Y-%m-%d %H:%M:%S') からの投稿"
    echo "✅ Discord Webhookテスト完了"
else
    echo "⏭️ Webhookテストをスキップしました"
fi

echo ""
echo "📄 生成された日記ファイルを確認:"
ls -la _diary/
echo ""
echo "🔍 今日の日記内容（最後の5行）:"
tail -5 _diary/$(date '+%Y-%m-%d').md
