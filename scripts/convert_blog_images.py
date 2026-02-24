#!/usr/bin/env python3
"""
ブログ画像JPEG→WebP変換スクリプト
GitHub Actionsから呼ばれてJPEG画像をWebPに変換し、Markdownファイルの参照も更新する
"""

import os
import glob
import re
from pathlib import Path
import shutil
from PIL import Image
import io

def convert_to_webp(image_path, quality=85):
    """JPEG画像をWebPに変換（Exif削除機能付き）"""
    try:
        with Image.open(image_path) as image:
            original_file_size = os.path.getsize(image_path)
            
            # Exifデータを確認・削除
            exif_info = []
            if hasattr(image, '_getexif') and image._getexif() is not None:
                exif_dict = image._getexif()
                
                dangerous_tags = {
                    34853: 'GPS情報',
                    306: '撮影日時',
                    271: 'カメラメーカー',
                    272: 'カメラモデル',
                    37500: 'メーカーノート'
                }
                
                for tag_id, description in dangerous_tags.items():
                    if tag_id in exif_dict:
                        exif_info.append(description)
                
                if exif_info:
                    print(f"⚠️  検出されたExifデータ: {', '.join(exif_info)}")
                    print("🔒 これらの情報は完全に削除されます")
                else:
                    print("✅ 危険なExifデータなし")
            else:
                print("✅ Exifデータなし")
            
            # RGBAモードの処理
            if image.mode in ('RGBA', 'LA', 'P'):
                pass
            elif image.mode != 'RGB':
                image = image.convert('RGB')
            
            # WebPに変換
            webp_path = image_path.rsplit('.', 1)[0] + '.webp'
            image.save(webp_path, format='WEBP', quality=quality, optimize=True)
            
            webp_file_size = os.path.getsize(webp_path)
            compression_ratio = (1 - webp_file_size / original_file_size) * 100
            
            print(f"WebP変換完了: {os.path.basename(image_path)}")
            print(f"  サイズ: {original_file_size:,} bytes -> {webp_file_size:,} bytes (-{compression_ratio:.1f}%)")
            print("  🔒 プライバシー保護: Exif/GPSデータは完全に削除されました")
            
            return webp_path
            
    except Exception as e:
        print(f"WebP変換エラー ({image_path}): {e}")
        return None

def update_markdown_files(old_path, new_path):
    """Markdownファイル内の画像パスを更新"""
    # 相対パスに変換
    old_rel_path = old_path.replace('/home/peipeipe/peipeipe.net/', '')
    new_rel_path = new_path.replace('/home/peipeipe/peipeipe.net/', '')
    
    # URLパスに変換（サイト用）
    old_url_path = f"https://www.peipeipe.net/{old_rel_path}"
    new_url_path = f"https://www.peipeipe.net/{new_rel_path}"
    
    updated_files = []
    
    # _posts/ と _drafts/ を検索
    for markdown_dir in ['_posts', '_drafts']:
        if os.path.exists(markdown_dir):
            for md_file in glob.glob(f"{markdown_dir}/**/*.md", recursive=True):
                try:
                    with open(md_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    original_content = content
                    
                    # パターン1: 絶対URL
                    content = content.replace(old_url_path, new_url_path)
                    
                    # パターン2: 相対パス
                    content = content.replace(old_rel_path, new_rel_path)
                    
                    # パターン3: ファイル名のみ（単純な文字列置換を使用）
                    old_filename = os.path.basename(old_path)
                    new_filename = os.path.basename(new_path)
                    
                    # images/フォルダ内での参照を検索・置換
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if 'images/' in line and old_filename in line:
                            # より安全な置換方法
                            if f'images/{old_filename}' in line:
                                lines[i] = line.replace(f'images/{old_filename}', f'images/{new_filename}')
                            else:
                                # images/subfolder/filename.jpg のような場合
                                lines[i] = line.replace(old_filename, new_filename)
                    content = '\n'.join(lines)
                    
                    if content != original_content:
                        with open(md_file, 'w', encoding='utf-8') as f:
                            f.write(content)
                        updated_files.append(md_file)
                        print(f"  更新: {md_file}")
                
                except Exception as e:
                    print(f"Markdownファイル更新エラー ({md_file}): {e}")
    
    return updated_files

def find_jpeg_images():
    """imagesディレクトリ内のJPEG画像を検索"""
    jpeg_patterns = ['*.jpg', '*.jpeg', '*.JPG', '*.JPEG']
    jpeg_files = []
    
    for pattern in jpeg_patterns:
        jpeg_files.extend(glob.glob(f"images/**/{pattern}", recursive=True))
    
    return sorted(jpeg_files)

def main():
    """メイン処理"""
    print("🎯 JPEG→WebP変換処理を開始します...")
    
    # 作業ディレクトリをリポジトリルートに設定
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(script_dir)
    os.chdir(repo_root)
    
    # JPEG画像を検索
    jpeg_files = find_jpeg_images()
    
    if not jpeg_files:
        print("✅ 変換対象のJPEG画像が見つかりませんでした")
        return
    
    print(f"📸 変換対象: {len(jpeg_files)} 個のJPEG画像")
    
    converted_count = 0
    failed_count = 0
    
    for jpeg_path in jpeg_files:
        print(f"\n🔄 変換中: {jpeg_path}")
        
        # WebPに変換
        webp_path = convert_to_webp(jpeg_path)
        
        if webp_path:
            # Markdownファイルの参照を更新
            updated_files = update_markdown_files(jpeg_path, webp_path)
            
            if updated_files:
                print(f"  📝 {len(updated_files)} 個のMarkdownファイルを更新")
            
            # 元のJPEGファイルを削除
            try:
                os.remove(jpeg_path)
                print(f"  🗑️  元ファイル削除: {os.path.basename(jpeg_path)}")
                converted_count += 1
            except Exception as e:
                print(f"  ❌ 元ファイル削除エラー: {e}")
                failed_count += 1
        else:
            failed_count += 1
    
    print(f"\n✅ 変換完了!")
    print(f"  成功: {converted_count} 個")
    print(f"  失敗: {failed_count} 個")
    
    if converted_count > 0:
        print("\n🚀 変更をコミットする準備が整いました")

if __name__ == '__main__':
    main()