#!/usr/bin/env python3
"""P0 backend (stdlib transport). Thin HTTP shell over the shared Api core.
Runs on any Python 3 with no install:  py irbis-web/backend/server.py
The aiohttp variant (app_aiohttp.py) wraps the SAME core."""
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

# Запуск из любого cwd: добавить каталог backend в sys.path, чтобы локальные
# импорты (core/reader_page/static_files) резолвились и когда сервер стартуют не
# из backend/ (напр. через preview/launch.json из корня репозитория).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core import Api, Raw
from reader_page import READER_HTML
import static_files

API = Api()


def _is_product_path(path):
    """True для публичной страницы продукта /product и её подпутей (#226).

    SPA отдаётся одним index.html; внутренний роутер (main.tsx) рендерит лендинг.
    Не перехватывает /product-… как префикс другого слова — только '/product' и
    то, что под ним ('/product/…')."""
    p = (path or '').rstrip('/')
    return p == '/product' or p.startswith('/product/')


class Handler(BaseHTTPRequestHandler):
    server_version = 'irbis-web-p0/0.2'

    def log_message(self, *a):
        pass

    def _headers(self):
        return {k.lower(): v for k, v in self.headers.items()}

    def _body(self):
        n = int(self.headers.get('Content-Length', 0) or 0)
        if not n:
            return {}
        try:
            return json.loads(self.rfile.read(n).decode('utf-8'))
        except Exception:
            return {}

    def _emit(self, status, payload):
        if isinstance(payload, Raw):
            body, ctype = payload.data, payload.content_type
        elif payload is None:
            body, ctype = b'', 'text/plain'
        else:
            body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
            ctype = 'application/json; charset=utf-8'
        self.send_response(status)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.end_headers()
        if body:
            self.wfile.write(body)

    def _dispatch(self, method):
        u = urlparse(self.path)
        if method == 'GET' and (u.path.rstrip('/') or '/') == '/':
            if static_files.has_dist():
                return self._emit(200, Raw(static_files.dist_index(), 'text/html; charset=utf-8'))
            return self._emit(200, Raw(READER_HTML.encode('utf-8'), 'text/html; charset=utf-8'))
        # Публичная страница продукта (#226): отдаём тот же SPA index.html на
        # /product и подпутях; роутинг внутри SPA (main.tsx) показывает лендинг.
        if method == 'GET' and _is_product_path(u.path):
            if static_files.has_dist():
                return self._emit(200, Raw(static_files.dist_index(), 'text/html; charset=utf-8'))
            return self._emit(200, Raw(READER_HTML.encode('utf-8'), 'text/html; charset=utf-8'))
        if method == 'GET' and (u.path.startswith('/assets/') or u.path.startswith('/design/')):
            st, data, ct = static_files.serve_dist(u.path)
            return self._emit(st, Raw(data, ct))
        if method == 'GET' and u.path.rstrip('/') == '/legacy':
            return self._emit(200, Raw(READER_HTML.encode('utf-8'), 'text/html; charset=utf-8'))
        if method == 'GET' and u.path.rstrip('/') == '/app':
            self.send_response(302)
            self.send_header('Location', '/ui/app/')
            self.end_headers()
            return
        if method == 'GET' and u.path.startswith('/ui/'):
            st, data, ct = static_files.serve(u.path)
            return self._emit(st, Raw(data, ct))
        body = self._body() if method == 'POST' else None
        status, payload = API.route(method, u.path, parse_qs(u.query), body, self._headers())
        self._emit(status, payload)

    def do_GET(self):
        self._dispatch('GET')

    def do_POST(self):
        self._dispatch('POST')

    def do_OPTIONS(self):
        self._emit(204, None)


def main():
    httpd = ThreadingHTTPServer((API.cfg.app_host, API.cfg.app_port), Handler)
    print('web-IRBIS P0 (stdlib) on http://%s:%d  (IRBIS %s:%d, db %s)'
          % (API.cfg.app_host, API.cfg.app_port, API.cfg.irbis_host, API.cfg.irbis_port, API.cfg.db_default))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        API.close()


if __name__ == '__main__':
    main()
