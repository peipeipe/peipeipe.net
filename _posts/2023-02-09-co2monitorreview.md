---
layout: post
title:  "二酸化炭素濃度計(ZGm27)を一週間使ってわかったこと"
date:   2023-02-09 22:01:00 +0900
permalink:   /:year-:month-:day-:title/
categories: gadget
image: https://pbs.twimg.com/media/FoXbferacAAut_3?format=jpg&name=large
---
高精度の二酸化炭素濃度系を買った。


<div class="krb-amzlt-box" style="margin-bottom:0px;"><div class="krb-amzlt-image" style="float:left;margin:0px 12px 1px 0px;"><a href="https://www.amazon.co.jp/dp/B091JM1TBJ?&linkCode=li2&tag=peipeipe-22&linkId=90be8c1d5c85ced4762066f7400173fb&language=ja_JP&ref_=as_li_ss_il" target="_blank" rel="nofollow" rel="nofollow"><img border="0" src="//ws-fe.amazon-adsystem.com/widgets/q?_encoding=UTF8&ASIN=B091JM1TBJ&Format= _SL250_&ID=AsinImage&MarketPlace=JP&ServiceVersion=20070822&WS=1&tag=peipeipe-22&language=ja_JP" ></a><img src="https://ir-jp.amazon-adsystem.com/e/ir?t=peipeipe-22&language=ja_JP&l=li2&o=9&a=B091JM1TBJ" width="1" height="1" border="0" alt="" style="border:none !important; margin:0px !important;" /></div><div class="krb-amzlt-info" style="line-height:120%; margin-bottom: 10px"><div class="krb-amzlt-name" style="margin-bottom:10px;line-height:120%"><a href="https://www.amazon.co.jp/dp/B091JM1TBJ?&linkCode=li2&tag=peipeipe-22&linkId=90be8c1d5c85ced4762066f7400173fb&language=ja_JP&ref_=as_li_ss_il" name="amazletlink" target="_blank" rel="nofollow" rel="nofollow">Radiant 二酸化炭素濃度測定器 ZGm27 ホワイト</a><div class="krb-amzlt-powered-date" style="font-size:80%;margin-top:5px;line-height:120%">posted with <a href="https://kaereba.com/wind/" title="amazlet" target="_blank" rel="nofollow" rel="nofollow">カエレバ</a></div></div><div class="krb-amzlt-detail"></div><div class="krb-amzlt-sub-info" style="float: left;"><div class="krb-amzlt-link" style="margin-top: 5px"><a href="https://www.amazon.co.jp/dp/B091JM1TBJ?&linkCode=li2&tag=peipeipe-22&linkId=90be8c1d5c85ced4762066f7400173fb&language=ja_JP&ref_=as_li_ss_il" name="amazletlink" target="_blank" rel="nofollow" rel="nofollow">Amazon.co.jpで詳細を見る</a></div></div></div><div class="krb-amzlt-footer" style="clear: left"></div></div>
在宅勤務をする上でずっと換気タイミングについて気になっていたし、集中力が落ちる原因が二酸化炭素の濃度だとしたら改善したいと思っていた。


二酸化炭素濃度計は安いのから高いのまであるが、安いやつは精度が悪く実用性がないらしい。


実際、[MH-Z19](https://amzn.to/3jNBGVa)というセンサーを買い、M5Stackで計測してみたがまともな数値はでなかったので安物買いの銭失いになってしまった。今回、1万円以上というお金をはたいて正確な値が図れるようになったのでわかったことを書く。


![](https://i.imgur.com/wqISq5Q.jpg)

- 6.5畳の部屋だと締め切った状態で生活すると20分くらいで1400ppmを超える(1000ppmを超えると換気推奨らしい)
- そのまま一時間くらい換気せずに作業すると2000ppmを超える
- 2000ppmを超えても数字を見なければ特に息苦しいなどは感じない。感覚で換気したほうが良いなと感じるのは3000ppmあたりのように思う。
- 数字を見ると息苦しく思う
- 1500ppmを越えたあたりから集中力などに影響がでるように思う。
- 1000ppmを超えないようにするには10分おきくらいの換気、またはずっと窓を開けるなどが必要
- 今の時期(冬)などに10分おきに換気をするのは気温、湿度の損失があり非常に厳しい
- 同様に夏や、春の花粉の時期も厳しいと考えられる
- 今回購入した機種には1400ppmを超えると画面が赤くなるというアラーム機能がついているが普通に生活していると常にアラームモードなので非常にストレスに感じる
- なので切った
- 睡眠時は起床時より二酸化炭素濃度の上昇が穏やかだが、締め切った部屋で寝て起床すると2000ppmは当たり前に超える
- 睡眠時に二酸化炭素濃度を下げることで体の回復を早めることができるのではないかと思ったが、窓を開けると音のせいで睡眠スコアがさがるので二酸化炭素濃度のみを下げることができていない。



## 二酸化炭素濃度計の購入について
湿度や温度計と同じように二酸化炭素濃度を数値で見ることができるのは非常に面白い。


が、高いのが悪い状態というのを知っているので常に表示されるとストレスになる人もいると思う。。温度や湿度くらいの感覚で、今日暑いなくらいに思うのが良いと思う。


よほど広い家に住んでいる、換気機能がしっかりしている、隙間風が吹き込むなどの環境でなければほとんどの部屋が同じような環境である(10分くらいすると1400ppmを超える)と思うので、換気の目安だけを知りたい人には不要。10分置きに換気しないとだめ。


自分の体の状態が思った以上に環境に左右されるものだということを知るには面白い買い物であった。


換気は増えたが基準となる値を一般的な1000ppmあたりにすると辛いことになるので1500ppmあたりを基準にしている。


また、花粉症の時期が来たので換気のために空気清浄機を購入することにした。二酸化炭素濃度を気にした結果、いろいろものが増えてしまった。


## 濃度計の機種について
経年劣化が少なく精度がでるNDIR方式かつ、強制補正がない、かつバッテリー駆動でない機種を選ぶとかなり選択肢が狭まってくる。ZGm27は価格以外は優れている点が多く満足している。特に24hの過去のグラフが見れるのが良い。おかげで睡眠中の二酸化炭素濃度の上がり方などを知ることができた。



<blockquote class="twitter-tweet"><p lang="ja" dir="ltr">買った！（すでに値が高い） <a href="https://t.co/zsLhnku6dH">pic.twitter.com/zsLhnku6dH</a></p>&mdash; ぺいぺいぺ (@peipeipe) <a href="https://twitter.com/peipeipe/status/1620709204020588544?ref_src=twsrc%5Etfw">February 1, 2023</a></blockquote> <script async src="https://platform.twitter.com/widgets.js" charset="utf-8"></script>


このブログは二酸化炭素濃度を1200ppmから1722ppmに上げることで書くことができた。