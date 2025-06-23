# iPhone日記システム（GitHub API版）

iPhoneショートカットからGitHub APIを使って、サーバー不要で24時間動作する日記システムです。

## 必要な設定

### 1. GitHub Personal Access Token の作成

1. GitHub Settings > Developer settings > Personal access tokens > Fine-grained tokens
2. 「Generate new token」をクリック
3. Repository access: Only select repositories → このリポジトリを選択
4. Permissions:
   - Contents: Read and write
   - Metadata: Read
   - Actions: Write（repository_dispatch用）
5. トークンをコピーして保存

### 2. iPhoneショートカットの設定

#### テキスト投稿用ショートカット

1. **URL**: `https://api.github.com/repos/[ユーザー名]/[リポジトリ名]/dispatches`
2. **Method**: POST
3. **Headers**:
   ```
   Authorization: Bearer [YOUR_GITHUB_TOKEN]
   Accept: application/vnd.github.v3+json
   Content-Type: application/json
   ```
4. **Request Body**:
   ```json
   {
     "event_type": "diary_post",
     "client_payload": {
       "content": "今日は良い天気でした"
     }
   }
   ```

#### 画像投稿用ショートカット

同じ設定で、Request Bodyに画像データを追加：
```json
{
  "event_type": "diary_post",
  "client_payload": {
    "content": "写真付きの投稿です",
    "image_data": "[Base64エンコードされた画像データ]",
    "image_filename": "photo.jpg"
  }
}
```

注意：
- `image_filename`は省略可能です（altテキストとしてのみ使用）
- 実際のファイル名は日時で自動生成されます
- 画像形式は自動判定されます（jpg, png, gif対応）

### 3. 使い方

**方法1: iPhoneショートカットから投稿**
- ショートカットアプリで作成したショートカットを実行
- テキストや画像を選択して投稿

**方法2: 手動でGitHub Actionsを実行**
1. GitHubリポジトリの「Actions」タブ
2. 「Webhook Diary Post」を選択
3. 「Run workflow」をクリック
4. メッセージを入力して実行

**方法3: テストスクリプトを使用**
```bash
# テスト送信
python scripts/test_image_diary.py
```

## システム構成

1. **iPhoneショートカット** → GitHub API（repository_dispatch）を呼び出し
2. **GitHub Actions** → 日記ファイルを自動生成・更新（画像保存機能付き）
3. **Jekyll (GitHub Pages)** → 日記サイトを自動ビルド・公開

## 利点

- ✅ **サーバー不要** - 完全にクラウドで動作
- ✅ **24時間稼働** - GitHub Actionsが自動実行
- ✅ **無料** - GitHub ActionsとGitHub APIは無料
- ✅ **簡単** - iPhoneから手軽に投稿
- ✅ **画像対応** - 写真付き投稿が可能
- ✅ **AIネイティブ** - AIが読みやすいMarkdown形式

## ファイル構成

- `_diary/`: 日記のMarkdownファイル
- `images/diary/`: 日記用画像ファイル
- `_layouts/diary.html`: 日記ページのレイアウト
- `diary.html`: 日記一覧ページ
- `scripts/update_diary_webhook.py`: 日記更新スクリプト
- `scripts/test_image_diary.py`: テスト用スクリプト
- `.github/workflows/webhook-diary.yml`: GitHub Actions ワークフロー（メイン）
- `.github/workflows/update-diary.yml`: 手動実行用ワークフロー
- `.github/workflows/jekyll.yml`: サイトビルド用ワークフロー

## 日記の形式

### AIネイティブなMarkdown形式

```markdown
# 2024-12-22

## 09:30
朝のコーヒーが美味しい。今日も一日頑張ろう。

## 14:25
![写真](images/diary/2024-12-22-1425.jpg)
ランチで美味しいパスタを食べました。

## 21:00
今日も充実した一日でした。明日は早起きして散歩に行きたい。
```

- 見出し（`## 時間`）で時系列を整理
- AIが理解しやすい構造
- 画像は自動的に適切なパスで保存・リンク

## 画像機能の詳細

### 画像ファイル名について

- **入力**: `image_filename`パラメータ（省略可能）
- **実際のファイル名**: `YYYY-MM-DD-HHMM.{拡張子}`で自動生成
- **用途**: 
  - 拡張子の判定（Base64ヘッダーがない場合）
  - altテキストの生成
- **例**: `2024-12-22-0930.jpg`

### 対応形式

- JPEG (.jpg, .jpeg)
- PNG (.png)
- GIF (.gif)
- Base64データの自動判定
- デフォルト: JPEG

## 今後の拡張予定

- 位置情報の自動追加
- 体重・健康データの連携
- 検索機能の強化
- タグ機能
- 月次・年次レポート機能
