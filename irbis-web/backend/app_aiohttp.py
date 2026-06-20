#!/usr/bin/env python3
"""aiohttp transport over the SAME Api core (Python 3.12: `py -3.12 -m pip install aiohttp`).
Run:  py -3.12 irbis-web/backend/app_aiohttp.py

Blocking IRBIS sockets and sqlite calls run in a thread executor so the event loop
is never blocked. Logic/authz/audit live entirely in core.Api — this file is transport."""
import asyncio
import json
from aiohttp import web

from core import Api, Raw
from reader_page import READER_HTML
import static_files

API = Api()
CORS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
}


def _query(request):
    mq = request.rel_url.query
    return {k: mq.getall(k) for k in mq.keys()}


async def handle(request):
    if request.method == 'GET' and (request.path.rstrip('/') or '/') == '/':
        if static_files.has_dist():
            return web.Response(body=static_files.dist_index(), content_type='text/html', charset='utf-8', headers=CORS)
        return web.Response(text=READER_HTML, content_type='text/html', headers=CORS)
    if request.method == 'GET' and request.path.startswith('/assets/'):
        st, data, ct = static_files.serve_dist(request.path)
        return web.Response(status=st, body=data, content_type=ct.split(';')[0], headers=CORS)
    if request.method == 'GET' and request.path.rstrip('/') == '/app':
        return web.Response(status=302, headers={'Location': '/ui/app/'})
    if request.method == 'GET' and request.path.startswith('/ui/'):
        st, data, ct = static_files.serve(request.path)
        ctype = ct.split(';')[0]
        return web.Response(status=st, body=data, content_type=ctype, headers=CORS)
    if request.method == 'OPTIONS':
        return web.Response(status=204, headers=CORS)
    body = None
    if request.method == 'POST' and request.can_read_body:
        try:
            body = await request.json()
        except Exception:
            body = {}
    headers = {k.lower(): v for k, v in request.headers.items()}
    loop = asyncio.get_running_loop()
    status, payload = await loop.run_in_executor(
        None, API.route, request.method, request.path, _query(request), body, headers)
    if isinstance(payload, Raw):
        return web.Response(status=status, body=payload.data,
                            content_type=payload.content_type, headers=CORS)
    if payload is None:
        return web.Response(status=status, headers=CORS)
    return web.Response(status=status, headers=CORS, content_type='application/json',
                        text=json.dumps(payload, ensure_ascii=False))


def build_app():
    app = web.Application()
    app.router.add_route('*', '/{tail:.*}', handle)
    return app


if __name__ == '__main__':
    print('web-IRBIS P0 (aiohttp) on http://%s:%d' % (API.cfg.app_host, API.cfg.app_port))
    web.run_app(build_app(), host=API.cfg.app_host, port=API.cfg.app_port, print=None)
