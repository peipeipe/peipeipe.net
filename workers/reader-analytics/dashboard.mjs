export const dashboard = `<!doctype html>
<html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>閲覧レポート</title>
<style>body{font:16px system-ui,sans-serif;max-width:1100px;margin:40px auto;padding:0 20px;color:#222;background:#fafafa}input,button{font:inherit;padding:8px;margin:4px}table{border-collapse:collapse;width:100%;background:white}td,th{text-align:left;padding:10px;border-bottom:1px solid #ddd;overflow-wrap:anywhere}section{margin:24px 0;overflow:auto}#summary{font-size:1.2rem}small{color:#555}button{cursor:pointer}td:first-child{max-width:450px}</style>
<h1>閲覧レポート</h1>
<p>日本時間の日別集計。アクセス元は日ごとに変わるIP由来のIDです。人数・住所を示すものではありません。</p>
<form id="form"><label>管理トークン <input id="token" type="password" autocomplete="off" required></label>
<label>日付 <input id="day" type="date" required></label><button>表示</button></form>
<small>トークンはこの画面のメモリ内だけで使用します。保存されません。</small>
<p id="status" role="status"></p><p id="summary"></p>
<section><h2>アクセス元別（上位100件）</h2><p>アクセス元IDを選択すると閲覧したページを表示します。</p><table id="visitors"></table></section>
<section><h2>人気ページ（上位50件）</h2><table id="pages"></table></section>
<section><h2>選択したアクセス元の閲覧ページ</h2><table id="detail"></table></section>
<script>
const $ = (id) => document.getElementById(id);
$('day').value = new Date(Date.now()+9*3600000).toISOString().slice(0,10);
function table(id, headers, rows) {
  const head = document.createElement('tr');
  headers.forEach(text=>{const th=document.createElement('th');th.textContent=text;head.append(th);});
  $(id).replaceChildren(head);
  rows.forEach(row=>{const tr=document.createElement('tr');row.forEach(value=>{const td=document.createElement('td');if(value instanceof Node)td.append(value);else td.textContent=String(value);tr.append(td);});$(id).append(tr);});
}
async function query(visitor) {
  const params=new URLSearchParams({day:$('day').value});
  if(visitor)params.set('visitor',visitor);
  const response=await fetch('/_analytics/report?'+params,{headers:{Authorization:'Bearer '+$('token').value},cache:'no-store'});
  if(!response.ok)throw new Error(response.status===401?'管理トークンを確認してください。':'取得できませんでした。直近30日の日付と設定を確認してください。');
  return response.json();
}
$('form').addEventListener('submit',async(event)=>{
  event.preventDefault();$('status').textContent='読み込み中…';
  $('summary').textContent='';['visitors','pages','detail'].forEach(id=>$(id).replaceChildren());
  try {
    const data=await query();
    $('summary').textContent=data.day+'：'+data.pv+' PV / '+data.sources+'アクセス元 / '+data.uniquePages+'種類のページ / 大量閲覧 '+data.heavySources+'アクセス元';
    table('visitors',['アクセス元ID','PV','ページ数','推定地域'],data.visitors.map(v=>{
      const button=document.createElement('button');button.textContent=v.visitor.slice(0,12);
      button.addEventListener('click',async()=>{try{const detail=await query(v.visitor);table('detail',['ページ','PV'],detail.pages.map(p=>[p.path,p.pv]));}catch(error){$('status').textContent=error.message;}});
      return [button,v.pv,v.pages,[v.country,v.region,v.city].filter(Boolean).join(' / ')||'不明'];
    }));
    table('pages',['ページ','PV','アクセス元数'],data.pages.map(p=>[p.path,p.pv,p.sources]));
    $('status').textContent='';
  } catch(error) {$('status').textContent=error.message;}
});
</script></html>`;
