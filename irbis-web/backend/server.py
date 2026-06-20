#!/usr/bin/env python3
"""P0 backend for web-IRBIS: HTTP API over the empirically-verified IrbisClient.

Stdlib only (runs on Python 3.x with no install). The IRBIS layer is transport-
agnostic, so moving to aiohttp later (per P0_BUILDKIT) only swaps this file.

Endpoints (envelope {ok, data} | {ok:false, error:{code,message}}):
  GET /api/health
  GET /api/search?db=IBIS&prefix=K&q=...&page=1&pageSize=20[&expr=...]
  GET /api/record/{db}/{mfn}
  GET /api/render/{db}/{mfn}?fmt=@brief
  GET /                      -> minimal reader demo page (search + card)
"""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from config import Config
from irbis import SessionManager
from irbis.client import IrbisError

CFG = Config()
SM = SessionManager(CFG.irbis_host, CFG.irbis_port, CFG.workstation,
                    CFG.irbis_user, CFG.irbis_pass, CFG.timeout)


def build_expr(qs):
    if qs.get('expr'):
        return qs['expr'][0]
    q = (qs.get('q', [''])[0] or '').strip().replace('"', '')
    if not q:
        return None
    prefix = (qs.get('prefix', ['K'])[0] or 'K').strip().upper()
    # author/title indices store full headings -> right-truncate for natural matching;
    # keyword index stores whole tokens -> exact term is correct.
    if prefix in ('A', 'T') and not q.endswith('$'):
        q += '$'
    return '"%s=%s"' % (prefix, q)


class Handler(BaseHTTPRequestHandler):
    server_version = 'irbis-web-p0/0.1'

    # ---- helpers ----
    def _send(self, code, payload, ctype='application/json; charset=utf-8'):
        if isinstance(payload, (dict, list)):
            body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        else:
            body = payload.encode('utf-8') if isinstance(payload, str) else payload
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(body)

    def _ok(self, data):
        self._send(200, {'ok': True, 'data': data})

    def _err(self, http_code, code, message):
        self._send(http_code, {'ok': False, 'error': {'code': code, 'message': message}})

    def log_message(self, *a):
        pass  # quiet

    def do_OPTIONS(self):
        self._send(204, b'')

    def do_GET(self):
        u = urlparse(self.path)
        path = u.path.rstrip('/') or '/'
        qs = parse_qs(u.query)
        try:
            if path == '/':
                return self._send(200, READER_HTML, 'text/html; charset=utf-8')
            if path == '/api/health':
                return self._ok({'server': '%s:%d' % (CFG.irbis_host, CFG.irbis_port),
                                 'version': SM.server_version(),
                                 'db': CFG.db_default,
                                 'maxmfn': SM.max_mfn(CFG.db_default)})
            if path == '/api/search':
                return self._search(qs)
            parts = path.strip('/').split('/')
            if len(parts) == 4 and parts[0] == 'api' and parts[1] in ('record', 'render'):
                db, mfn = parts[2], int(parts[3])
                if parts[1] == 'record':
                    return self._record(db, mfn)
                return self._render(db, mfn, qs.get('fmt', ['@brief'])[0])
            return self._err(404, 'not_found', 'unknown route')
        except IrbisError as e:
            http = 403 if e.code == -3338 else 502
            return self._err(http, e.code, 'irbis error')  # no internals to client
        except ValueError:
            return self._err(400, 'bad_request', 'invalid parameter')
        except Exception:
            return self._err(500, 'internal', 'internal error')

    # ---- endpoints ----
    def _search(self, qs):
        db = qs.get('db', [CFG.db_default])[0]
        expr = build_expr(qs)
        if not expr:
            return self._err(400, 'bad_request', 'q or expr required')
        page = max(1, int(qs.get('page', ['1'])[0]))
        page_size = min(50, max(1, int(qs.get('pageSize', ['20'])[0])))
        count, mfns = SM.search(db, expr)
        start = (page - 1) * page_size
        page_mfns = mfns[start:start + page_size]
        items = []
        for mfn in page_mfns:
            try:
                brief = SM.format_record(db, mfn, '@brief')
            except IrbisError:
                brief = ''
            items.append({'mfn': mfn, 'brief': brief})
        self._ok({'db': db, 'expr': expr, 'total': count,
                  'page': page, 'pageSize': page_size, 'items': items})

    def _record(self, db, mfn):
        rec = SM.read_record(db, mfn)
        try:
            rec['brief'] = SM.format_record(db, mfn, '@brief')
        except IrbisError:
            rec['brief'] = ''
        rec['db'] = db
        self._ok(rec)

    def _render(self, db, mfn, fmt):
        self._ok({'db': db, 'mfn': mfn, 'fmt': fmt,
                  'rendered': SM.format_record(db, mfn, fmt)})


READER_HTML = """<!doctype html><html lang=ru><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>web-ИРБИС · читатель (P0)</title>
<style>
 body{font:15px/1.5 system-ui,Segoe UI,Arial;margin:0;color:#1a1a1a;background:#f6f7f9}
 header{background:#1f3a5f;color:#fff;padding:14px 20px;font-weight:600}
 main{max-width:900px;margin:0 auto;padding:20px}
 .bar{display:flex;gap:8px;margin-bottom:16px}
 input,select,button{font:inherit;padding:9px 12px;border:1px solid #cdd3da;border-radius:8px}
 input{flex:1} button{background:#1f3a5f;color:#fff;border:0;cursor:pointer}
 .item{background:#fff;border:1px solid #e7eaee;border-radius:10px;padding:12px 14px;margin:8px 0;cursor:pointer}
 .item:hover{border-color:#1f3a5f}
 .mfn{color:#8a93a0;font-size:12px}
 .meta{color:#54606e;font-size:13px;margin:6px 0 14px}
 #card{background:#fff;border:1px solid #e7eaee;border-radius:10px;padding:16px;margin-top:8px;display:none}
 table{border-collapse:collapse;width:100%;font-size:13px} td{border-top:1px solid #eef1f4;padding:4px 8px;vertical-align:top}
 td.t{color:#8a93a0;width:64px;font-variant-numeric:tabular-nums}
</style></head><body>
<header>web-ИРБИС · читательский поиск <span style=opacity:.7>(P0, живой сервер)</span></header>
<main>
 <div class=bar>
  <select id=prefix>
   <option value=K>Ключевые слова</option><option value=A>Автор</option>
   <option value=T>Заглавие</option><option value=V>Вид документа</option></select>
  <input id=q placeholder="Запрос, напр. Android или Колисниченко" value="Android">

  <button onclick=doSearch()>Найти</button>
 </div>
 <div class=meta id=meta></div>
 <div id=list></div>
 <div id=card></div>
</main>
<script>
async function doSearch(){
 const p=document.getElementById('prefix').value, q=document.getElementById('q').value;
 document.getElementById('card').style.display='none';
 const r=await fetch(`/api/search?prefix=${p}&q=${encodeURIComponent(q)}&pageSize=20`);
 const j=await r.json();
 if(!j.ok){document.getElementById('meta').textContent='Ошибка'; return;}
 document.getElementById('meta').textContent=`Найдено: ${j.data.total} · показаны первые ${j.data.items.length}`;
 document.getElementById('list').innerHTML=j.data.items.map(it=>
  `<div class=item onclick="openRec('${j.data.db}',${it.mfn})"><div class=mfn>MFN ${it.mfn}</div>${esc(it.brief)||'(без описания)'}</div>`).join('');
}
async function openRec(db,mfn){
 const r=await fetch(`/api/record/${db}/${mfn}`); const j=await r.json();
 if(!j.ok)return; const d=j.data;
 const rows=d.fields.map(f=>`<tr><td class=t>${f.tag}</td><td>${esc(f.value)}</td></tr>`).join('');
 const c=document.getElementById('card');
 c.style.display='block';
 c.innerHTML=`<div class=mfn>MFN ${d.mfn} · версия ${d.version||''}</div>
  <p><b>${esc(d.brief)||''}</b></p><table>${rows}</table>`;
 c.scrollIntoView({behavior:'smooth'});
}
function esc(s){return (s||'').replace(/[&<>]/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[m]));}
doSearch();
</script></body></html>"""


def main():
    httpd = ThreadingHTTPServer((CFG.app_host, CFG.app_port), Handler)
    print('web-IRBIS P0 backend on http://%s:%d  (IRBIS %s:%d, db %s)'
          % (CFG.app_host, CFG.app_port, CFG.irbis_host, CFG.irbis_port, CFG.db_default))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        SM.close()


if __name__ == '__main__':
    main()
