#!/usr/bin/env python3
"""Minimal reader demo page (search + autocomplete + record card + cover).
Served by both transports at '/'. Talks to the API with a guest bearer token."""

READER_HTML = """<!doctype html><html lang=ru><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>web-ИРБИС · читатель (P0)</title>
<style>
 body{font:15px/1.5 system-ui,Segoe UI,Arial;margin:0;color:#1a1a1a;background:#f6f7f9}
 header{background:#1f3a5f;color:#fff;padding:14px 20px;font-weight:600}
 main{max-width:920px;margin:0 auto;padding:20px}
 .bar{display:flex;gap:8px;margin-bottom:16px}
 input,select,button{font:inherit;padding:9px 12px;border:1px solid #cdd3da;border-radius:8px}
 input{flex:1} button{background:#1f3a5f;color:#fff;border:0;cursor:pointer}
 .item{background:#fff;border:1px solid #e7eaee;border-radius:10px;padding:12px 14px;margin:8px 0;cursor:pointer;display:flex;gap:12px}
 .item:hover{border-color:#1f3a5f}
 .cov{width:48px;height:64px;object-fit:cover;border-radius:4px;background:#eef1f4;flex:none}
 .mfn{color:#8a93a0;font-size:12px}
 .meta{color:#54606e;font-size:13px;margin:6px 0 14px}
 #sug{position:absolute;top:46px;left:150px;right:90px;background:#fff;border:1px solid #cdd3da;border-radius:8px;max-height:240px;overflow:auto;z-index:9;display:none}
 #sug div{padding:6px 10px;cursor:pointer;font-size:13px} #sug div:hover{background:#eef3fa}
 #card{background:#fff;border:1px solid #e7eaee;border-radius:10px;padding:16px;margin-top:8px;display:none}
 table{border-collapse:collapse;width:100%;font-size:13px} td{border-top:1px solid #eef1f4;padding:4px 8px;vertical-align:top}
 td.t{color:#8a93a0;width:64px;font-variant-numeric:tabular-nums}
</style></head><body>
<header>web-ИРБИС · читательский поиск <span style=opacity:.7>(P0, живой сервер)</span></header>
<main>
 <div class=bar style=position:relative>
  <select id=prefix>
   <option value=K>Ключевые слова</option><option value=A>Автор</option>
   <option value=T>Заглавие</option><option value=V>Вид документа</option></select>
  <input id=q placeholder="Запрос" value="Android" autocomplete=off
     oninput=suggest() onkeydown="if(event.key==='Enter')doSearch()">
  <button onclick=doSearch()>Найти</button>
  <div id=sug></div>
 </div>
 <div class=meta id=meta></div>
 <div id=list></div>
 <div id=card></div>
</main>
<script>
let TOKEN=null;
const H=()=>({'Authorization':'Bearer '+TOKEN});
async function init(){ const r=await fetch('/api/auth/guest',{method:'POST'}); TOKEN=(await r.json()).data.token; doSearch(); }
async function doSearch(){
 hideSug();
 const p=document.getElementById('prefix').value, q=document.getElementById('q').value;
 document.getElementById('card').style.display='none';
 const r=await fetch(`/api/search?prefix=${p}&q=${encodeURIComponent(q)}&pageSize=20`,{headers:H()});
 const j=await r.json();
 if(!j.ok){document.getElementById('meta').textContent='Ошибка'; return;}
 document.getElementById('meta').textContent=`Найдено: ${j.data.total} · показаны первые ${j.data.items.length}`;
 document.getElementById('list').innerHTML=j.data.items.map(it=>
  `<div class=item onclick="openRec('${j.data.db}',${it.mfn})">
     <img class=cov src="/api/cover/${j.data.db}/${it.mfn}" onerror="this.style.visibility='hidden'">
     <div><div class=mfn>MFN ${it.mfn}</div>${esc(it.brief)||'(без описания)'}</div></div>`).join('');
}
let sugTimer;
function suggest(){
 clearTimeout(sugTimer);
 const p=document.getElementById('prefix').value, q=document.getElementById('q').value.trim();
 if(q.length<2){hideSug();return;}
 sugTimer=setTimeout(async()=>{
  const r=await fetch(`/api/terms?start=${encodeURIComponent(p+'='+q.toUpperCase())}&count=8`,{headers:H()});
  const j=await r.json(); if(!j.ok)return;
  const box=document.getElementById('sug');
  box.innerHTML=j.data.terms.filter(t=>t.term.startsWith(p+'=')).map(t=>
    `<div onclick="pick('${esc(t.term).replace(/'/g,'')}')">${esc(t.term.slice(p.length+1))} <span class=mfn>(${t.count})</span></div>`).join('');
  box.style.display=box.innerHTML?'block':'none';
 },180);
}
function pick(term){ document.getElementById('q').value=term.slice(term.indexOf('=')+1); hideSug(); doSearch(); }
function hideSug(){document.getElementById('sug').style.display='none';}
async function openRec(db,mfn){
 const r=await fetch(`/api/record/${db}/${mfn}`,{headers:H()}); const j=await r.json();
 if(!j.ok)return; const d=j.data;
 const rows=d.fields.map(f=>`<tr><td class=t>${f.tag}</td><td>${esc(f.value)}</td></tr>`).join('');
 const c=document.getElementById('card'); c.style.display='block';
 c.innerHTML=`<div class=mfn>MFN ${d.mfn} · версия ${d.version||''}</div>
  <p><b>${esc(d.brief)||''}</b></p>
  ${d.hasCover?`<img src="/api/cover/${db}/${mfn}" style="max-height:180px;border-radius:6px;margin:6px 0">`:''}
  <table>${rows}</table>`;
 c.scrollIntoView({behavior:'smooth'});
}
function esc(s){return (s||'').replace(/[&<>]/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[m]));}
init();
</script></body></html>"""
