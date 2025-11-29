#!/usr/bin/env python3
"""
既存JPEG画像一括WebP変換スクリプト
既存の123個のJPEG画像をすべてWebPに変換し、対応するMarkdownファイルも更新
"""

import os
import sys
import subprocess

def run_conversion():
    """一括変換を実行"""
    print("🚀 既存JPEG画像の一括WebP変換を開始します...")
    print("⚠️  この処理により、以下が実行されます:")
    print("   - 全JPEG画像をWebPに変換")
    print("   - 元のJPEGファイルを削除")
    print("   - 対応するMarkdownファイルを更新")
    print()
    
    # 確認プロンプト
    response = input("続行しますか？ (y/N): ").strip().lower()
    if response not in ['y', 'yes']:
        print("❌ 処理を中止しました")
        return
    
    # convert_blog_images.py を実行
    script_path = os.path.join(os.path.dirname(__file__), 'convert_blog_images.py')
    
    try:
        print("\n📸 変換スクリプトを実行中...")
        result = subprocess.run([sys.executable, script_path], 
                              capture_output=True, text=True, encoding='utf-8')
        
        if result.returncode == 0:
            print(result.stdout)
            print("\n✅ 一括変換が完了しました!")
            print("\n🔄 次の手順:")
            print("   1. git add -A")
            print("   2. git commit -m \"Convert all existing JPEG images to WebP\"")
            print("   3. git push")
        else:
            print(f"❌ 変換中にエラーが発生しました:")
            print(result.stderr)
            
    except Exception as e:
        print(f"❌ スクリプト実行エラー: {e}")

if __name__ == '__main__':
    # 作業ディレクトリをリポジトリルートに設定
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(script_dir)
    os.chdir(repo_root)
    
    run_conversion()