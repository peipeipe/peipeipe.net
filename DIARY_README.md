# Discord日記システム（Webhook版）

DiscordのWebhookを使って、サーバー不要で24時間動作する日記システムです。

## 必要な設定

### 1. Discord Webhook の作成

1. 日記用Discordチャンネルで右クリック
2. 「チャンネルを編集」→「連携機能」→「Webhookを作成」
3. Webhook URLをコピー

### 2. GitHub Secrets の設定

リポジトリの Settings > Secrets and variables > Actions で以下を設定：

- `DISCORD_WEBHOOK_URL`: Discord WebhookのURL

### 3. 使い方

**方法1: Discordチャンネルに直接投稿**
- 設定したチャンネルにメッセージを投稿すると自動的に日記に記録

**方法2: 手動でGitHub Actionsを実行**
1. GitHubリポジトリの「Actions」タブ
2. 「Discord Webhook to Diary」を選択
3. 「Run workflow」をクリック
4. メッセージを入力して実行

**方法3: テストスクリプトを使用**
```bash
# 仮想環境をアクティベート
source diary_bot_env/bin/activate

# パッケージをインストール
pip install -r requirements.txt

# テスト送信
python scripts/test_webhook.py "WEBHOOK_URL" "今日はいい天気だね"
```

## システム構成

1. **Discord Webhook** → メッセージが投稿されるとGitHub Actionsを自動実行
2. **GitHub Actions** → 日記ファイルを自動生成・更新
3. **Jekyll (GitHub Pages)** → 日記サイトを自動ビルド・公開

## 利点

- ✅ **サーバー不要** - 完全にクラウドで動作
- ✅ **24時間稼働** - GitHub Actionsが自動実行
- ✅ **無料** - GitHub ActionsとDiscord Webhookは無料
- ✅ **簡単** - Discordにメッセージするだけ

## ファイル構成

- `_diary/`: 日記のMarkdownファイル
- `_layouts/diary.html`: 日記ページのレイアウト
- `diary.html`: 日記一覧ページ
- `scripts/discord_bot.py`: Discord Bot
- `scripts/update_diary.py`: 日記更新スクリプト
- `.github/workflows/update-diary.yml`: GitHub Actions ワークフロー

## 今後の拡張予定

- Garmin Connect APIとの連携
- 体重・アクティビティデータの自動取得
- 写真の自動保存機能
- 検索機能
- タグ機能
