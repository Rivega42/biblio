#!/usr/bin/env python3
"""Dependency-free JWT (HMAC-SHA256 / HS256) for signed bearer sessions (issue #101).

The frontend sends ``Authorization: Bearer <token>`` and treats the token as an
opaque string, so issuing a signed JWT here needs NO frontend change (api.ts is
untouched). We deliberately use only the stdlib (``hmac``/``hashlib``/``base64``/
``json``) — no pip dependency (PyJWT etc.) — because disk is tight on the build box.

Claims we issue (see ``Api._new_session`` in core.py):
  sub     subject  — staff login / reader "RI=<ticket>" / "guest"
  tenant  tenant slug the session is scoped to ('public' when single-tenant/dev)
  kind    'guest' | 'reader' | 'staff'
  grants  the session's effective grants (list of {function, db, level})
  iat     issued-at  (unix seconds)
  exp     expiry     (unix seconds) — verified on every request

``encode`` signs; ``decode`` verifies the signature (constant-time) AND the exp
claim. A tampered payload/signature or an expired token raises ``JwtError`` →
the API edge maps that to 401. Only HS256 is accepted (``alg`` is pinned on
decode, so the "alg: none" downgrade attack is rejected).
"""
import base64
import hashlib
import hmac
import json
import time

_ALG = 'HS256'
_HEADER = {'alg': _ALG, 'typ': 'JWT'}


class JwtError(Exception):
    """Raised when a token fails to verify (bad signature, malformed, expired)."""


def _b64u_encode(raw):
    """URL-safe base64 without padding (JWT convention)."""
    return base64.urlsafe_b64encode(raw).rstrip(b'=').decode('ascii')


def _b64u_decode(seg):
    """Decode a URL-safe base64 segment, restoring the stripped padding."""
    pad = '=' * (-len(seg) % 4)
    return base64.urlsafe_b64decode(seg + pad)


def _sign(signing_input, secret):
    return hmac.new(_secret_bytes(secret), signing_input, hashlib.sha256).digest()


def _secret_bytes(secret):
    return secret.encode('utf-8') if isinstance(secret, str) else secret


def encode(claims, secret, ttl_seconds=43200, now=None):
    """Sign ``claims`` into a compact JWS string. Sets iat/exp if not already present.

    ``ttl_seconds`` defaults to 12h. ``now`` is injectable for tests.
    """
    now = int(now if now is not None else time.time())
    payload = dict(claims)
    payload.setdefault('iat', now)
    payload.setdefault('exp', now + int(ttl_seconds))
    h = _b64u_encode(json.dumps(_HEADER, separators=(',', ':'), sort_keys=True).encode('utf-8'))
    p = _b64u_encode(json.dumps(payload, separators=(',', ':'),
                                ensure_ascii=False, sort_keys=True).encode('utf-8'))
    signing_input = ('%s.%s' % (h, p)).encode('ascii')
    sig = _b64u_encode(_sign(signing_input, secret))
    return '%s.%s.%s' % (h, p, sig)


def decode(token, secret, now=None):
    """Verify signature + exp and return the claims dict, or raise ``JwtError``.

    - Signature is checked in constant time (``hmac.compare_digest``).
    - ``alg`` is pinned to HS256 on decode, so an attacker can't downgrade to
      ``alg: none`` or swap algorithms.
    - ``exp`` (if present) must be in the future.
    """
    if not token or not isinstance(token, str):
        raise JwtError('empty token')
    parts = token.split('.')
    if len(parts) != 3:
        raise JwtError('malformed token')
    h_seg, p_seg, sig_seg = parts
    try:
        header = json.loads(_b64u_decode(h_seg))
    except Exception:
        raise JwtError('bad header')
    if header.get('alg') != _ALG:
        raise JwtError('unexpected alg %r' % header.get('alg'))
    signing_input = ('%s.%s' % (h_seg, p_seg)).encode('ascii')
    expected = _sign(signing_input, secret)
    try:
        given = _b64u_decode(sig_seg)
    except Exception:
        raise JwtError('bad signature encoding')
    if not hmac.compare_digest(expected, given):
        raise JwtError('signature mismatch')
    try:
        claims = json.loads(_b64u_decode(p_seg))
    except Exception:
        raise JwtError('bad payload')
    exp = claims.get('exp')
    if exp is not None:
        now = int(now if now is not None else time.time())
        if now >= int(exp):
            raise JwtError('token expired')
    return claims
