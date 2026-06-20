#!/usr/bin/env python3
"""Serve the vendored frontend (irbis-web/frontend/) under /ui/. Transport-agnostic:
returns (status, bytes, content_type). Used by both server.py and app_aiohttp.py."""
import os
import posixpath

FRONTEND = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'frontend'))

_CT = {
    '.html': 'text/html; charset=utf-8',
    '.css': 'text/css; charset=utf-8',
    '.js': 'text/javascript; charset=utf-8',
    '.jsx': 'text/javascript; charset=utf-8',
    '.json': 'application/json; charset=utf-8',
    '.map': 'application/json',
    '.svg': 'image/svg+xml',
    '.md': 'text/markdown; charset=utf-8',
    '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
    '.woff2': 'font/woff2', '.woff': 'font/woff',
}


def serve(url_path):
    """url_path starts with '/ui/'. Returns (status, data_bytes, content_type)."""
    rel = url_path[len('/ui/'):] if url_path.startswith('/ui/') else url_path.lstrip('/')
    rel = posixpath.normpath('/' + rel).lstrip('/')          # block ../ traversal
    full = os.path.join(FRONTEND, *rel.split('/')) if rel else FRONTEND
    if os.path.isdir(full):
        full = os.path.join(full, 'index.html')
    if not os.path.isfile(full):
        return 404, b'not found', 'text/plain'
    ext = os.path.splitext(full)[1].lower()
    with open(full, 'rb') as f:
        return 200, f.read(), _CT.get(ext, 'application/octet-stream')
