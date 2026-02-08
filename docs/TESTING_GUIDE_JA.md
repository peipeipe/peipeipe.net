# Amazon PA-API統合のテスト方法

このドキュメントでは、Amazon PA-API統合機能をテストする方法を説明します。

## テスト方法の種類

### 1. ローカルテスト（API認証情報なし）

基本的なロジックをテストできます。API認証情報は不要です。

```bash
# テストスクリプトを実行
cd /home/runner/work/peipeipe.net/peipeipe.net
python3 scripts/test_amazon_enhancement.py
```

このテストでは以下を確認します：
- ✓ ASIN抽出ロジック
- ✓ リンク検出ロジック
- ✓ HTMLエスケープ（セキュリティ）
- ✓ マークダウンファイルの検出

### 2. ローカルテスト（API認証情報あり）

実際にAmazon PA-APIを呼び出してテストします。

#### 準備

1. Amazon PA-API認証情報を取得：
   - https://affiliate.amazon.co.jp/assoc_credentials/home
   
2. 環境変数を設定：

```bash
export AMAZON_ACCESS_KEY="your-access-key"
export AMAZON_SECRET_KEY="your-secret-key"
export AMAZON_PARTNER_TAG="peipeipe-22"
```

#### テスト実行

```bash
# 依存関係をインストール
pip install -r requirements.txt

# スクリプトを実行（実際に_posts内のファイルを処理）
python3 scripts/enhance_amazon_links.py
```

**注意**: このコマンドは実際にファイルを変更します！

#### ドライラン（ファイルを変更しない）

テスト用に小さなサンプルファイルで試すことをお勧めします：

```bash
# テスト用マークダウンファイルを作成
cat > /tmp/test_post.md << 'EOF'
---
layout: post
title: "テスト記事"
date: 2024-02-08 12:00:00 +0900
---

# テスト

[テスト商品](https://www.amazon.co.jp/dp/B084MCR9KG)
EOF

# テスト用ディレクトリを作成
mkdir -p /tmp/test_posts
cp /tmp/test_post.md /tmp/test_posts/

# スクリプトを修正してテストディレクトリを指定
# （または、enhance_amazon_links.py の posts_dir を一時的に変更）
```

### 3. GitHub Actionsでテスト

実際の運用環境でテストします。

#### ステップ1: GitHub Secretsを設定

1. GitHubリポジトリの Settings → Secrets and variables → Actions
2. 以下のシークレットを追加：
   - `AMAZON_ACCESS_KEY`: PA-API アクセスキー
   - `AMAZON_SECRET_KEY`: PA-API シークレットキー
   - `AMAZON_PARTNER_TAG`: アフィリエイトタグ（例：peipeipe-22）

#### ステップ2: ワークフローを手動実行

1. GitHub リポジトリの「Actions」タブを開く
2. 左サイドバーから「Enhance Amazon Affiliate Links」を選択
3. 「Run workflow」ボタンをクリック
4. ブランチを選択（例：main）
5. 「Run workflow」を実行

#### ステップ3: 実行結果を確認

1. ワークフローの実行ログを確認
2. 処理されたファイルの数を確認
3. エラーがないか確認
4. コミットされた変更を確認

## テスト時の確認ポイント

### ✓ 正常に処理される例

以下のようなシンプルなリンクは処理されます：

```markdown
[商品名](https://www.amazon.co.jp/dp/B084MCR9KG)
[別の商品](http://www.amazon.co.jp/exec/obidos/ASIN/4062737388/peipeipe-22/ref=nosim/)
```

### ✓ スキップされる例

以下のような既存の複雑なウィジェットはスキップされます：

```html
<div class="krb-amzlt-box">
  <!-- カエレバなどのウィジェット -->
</div>
```

### ✓ 出力フォーマット

処理後は以下のような形式に変換されます：

```html
<div class="amazon-product-card" style="...">
  <div class="amazon-product-image">
    <a href="..."><img src="商品画像URL" alt="商品タイトル"></a>
  </div>
  <div class="amazon-product-info">
    <h3><a href="...">商品タイトル</a></h3>
    <div class="amazon-product-link">
      <a href="...">Amazon.co.jpで詳細を見る</a>
    </div>
  </div>
</div>
```

## トラブルシューティング

### エラー: "AMAZON_ACCESS_KEY and AMAZON_SECRET_KEY environment variables must be set"

**原因**: API認証情報が設定されていません

**解決策**: 
- ローカル: 環境変数を設定
- GitHub Actions: リポジトリのSecretsを設定

### エラー: "Error fetching product info for ASIN"

**原因**: 
- ASINが無効
- 商品が利用できない
- APIレート制限に達した

**解決策**:
- ASINが正しいか確認
- 少し時間を置いてから再実行
- APIクォータを確認

### 変更されないファイルがある

**原因**: 
- 既に複雑なウィジェットが含まれている
- シンプルなAmazonリンクが見つからない

**解決策**:
- これは正常な動作です
- スクリプトは既存の複雑なウィジェットを保護します

## ベストプラクティス

1. **小規模なテストから始める**
   - まず1-2個のファイルでテスト
   - 結果を確認してから全体に適用

2. **バックアップを取る**
   - Gitで管理されているので、問題があれば元に戻せます
   - 重要な変更前はブランチを作成

3. **レート制限に注意**
   - Amazon PA-APIには1秒あたりのリクエスト制限があります
   - 大量のファイルを一度に処理しない

4. **定期的な実行**
   - 新しい記事を追加したときに自動実行されます
   - 手動で実行することも可能です

## 追加情報

詳細な設定方法は `docs/AMAZON_PAAPI_INTEGRATION.md` を参照してください。
