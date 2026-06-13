---

title: 320円で買った安すぎるArduino互換機をMacに認識させる
slug: "getting-a-cheap-arduino-clone-recognized-on-mac"
permalink: /2016-10-08-getting-a-cheap-arduino-clone-recognized-on-mac/
id: 164
date: '2016-10-08 06:00:07'
layout: post
categories:
  - arduino
  - Gadget
  - nano
---

買ったのはこれです。  



<div class="krb-amzlt-box" style="margin-bottom:0px;"><div class="krb-amzlt-image" style="float:left;margin:0px 12px 1px 0px;"><a href="https://www.amazon.co.jp/dp/B01CZQANN0?tag=peipeipe-22"><img width="160px" src="https://images-na.ssl-images-amazon.com/images/P/B01CZQANN0.09.LZZZZZZZ"></a></div><div class="krb-amzlt-info" style="line-height:120%; margin-bottom: 10px"><div class="krb-amzlt-name" style="margin-bottom:10px;line-height:120%"><a href="https://www.amazon.co.jp/dp/B01CZQANN0?tag=peipeipe-22" name="amazletlink" target="_blank" rel="nofollow" rel="nofollow">HiLetgo Mini USB Nano V3.0 ATmega328P CH340G 5V 16M マイクロコントローラーボード Arduinoと互換</a></div><div class="krb-amzlt-detail"></div><div class="krb-amzlt-sub-info" style="float: left;"><div class="krb-amzlt-link" style="margin-top: 5px"><a href="https://www.amazon.co.jp/dp/B01CZQANN0?tag=peipeipe-22" name="amazletlink" target="_blank" rel="nofollow" rel="nofollow">Amazon.co.jpで詳細を見る</a></div></div></div><div class="krb-amzlt-footer" style="clear: left"></div></div>

posted with [amazlet](http://www.amazlet.com/ "amazlet") at 16.10.08



HiLetgo  
売り上げランキング: 89  











![image](https://cdn-ak.f.st-hatena.com/images/fotolife/p/peipeipe/20190630/20190630171532.webp)

ダメ元で買ったら案の定[Mac](http://d.hatena.ne.jp/keyword/Mac)が認識しない。

[Arduino](http://d.hatena.ne.jp/keyword/Arduino) [IDE](http://d.hatena.ne.jp/keyword/IDE)のシリアルポートにも表示されない。

![image](https://cdn-ak.f.st-hatena.com/images/fotolife/p/peipeipe/20190630/20190630171339.webp)

検索してみると、[Arduino](http://d.hatena.ne.jp/keyword/Arduino)互換機は使っているUSBシリアルチップが違うのでUSBドライバが必要らしい。

USBドライバがここにありました。

[http://kig.re/2014/12/31/how-to-use-arduino-nano-mini-pro-with-CH340G-on-mac-osx-yosemite.html](http://kig.re/2014/12/31/how-to-use-arduino-nano-mini-pro-with-CH340G-on-mac-osx-yosemite.html)  

[Mac](http://d.hatena.ne.jp/keyword/Mac)用のものをダウンロードしてインストール、再起動。

無事に使えるようになりました。

![image](https://cdn-ak.f.st-hatena.com/images/fotolife/p/peipeipe/20190630/20190630172136.webp)

おしまい。

![image](https://cdn-ak.f.st-hatena.com/images/fotolife/p/peipeipe/20190630/20190630170622.webp)