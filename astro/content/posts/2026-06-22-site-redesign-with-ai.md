---
layout: post
title:  "JekyllからAstroへの移行とページ追加"
date:   2026-06-22 21:00:00 +0900
permalink:   /:year-:month-:day-:title/
categories: site
---
サイトの構成を変えた。Activity、Books、Places、Mountains といった自分のログを見られるページを追加した。

Astroでテストページを作らせたところ[アクティビティマップ](https://www.peipeipe.net/activity/)の出来がかなり良かった。  
これを使いたいな、となり移行。GitHub PagesからCloudflare Pagesへの移行も同時に行った。

今回追加したページはこんな感じ。

- [Books](https://www.peipeipe.net/books/)
  - ブクログに個人的なメモと残しておきたい引用を書き溜めていたがそれをCSVに吐き出して、それっぽい個人的なメモをスクリプトで削除して作成している。  
- [チェックイン場所マップ](https://www.peipeipe.net/places/)
  - Foursquare APIを利用してそのまま出力。  
- [アクティビティマップ](https://www.peipeipe.net/activity/)
  - Strava APIからデータを取得してそれを描画。  
- [訪問済み山リスト](https://www.peipeipe.net/mountains/)
  - これも同じくStrava APIのpolylineから山頂に近づいたら登ったと判定している。  


それぞれAIだけあってもデータがないとできないことなのでコツコツデータを取るのは大事だなと。  

[Stravaは2026年7月1日からAPIの利用はStravaサブスクリプションが必須になるという改悪が入った](https://communityhub.strava.com/insider-journal-9/an-update-to-our-developer-program-13428)のでZIPエクスポートから同じものを作れるものを作って実装している。  
これは結構面白かったのでStravaの今まで行ったことのある軌跡を表示するサイトを同じ仕組みで作ってみた。  

https://activity.peipeipe.net/  
ナスカの地上絵のようになって大変面白かったし過去の地方マラソン大会を振り返ることができて楽しい。  

![image](/images/posts/2026-06-22-post/01.webp)
