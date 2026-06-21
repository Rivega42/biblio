#!/usr/bin/env python3
"""Field-level encryption of stored ПДн at rest — audit finding **V1** / R1
(152-ФЗ ст.19; ПП-1119; ФСТЭК-21). Closes the recon gap "ПДн читателей не
зашифрованы при хранении": any reader PII this product persists in OUR store
(currently the resolved reader display name in ``reader_review.reader_name``,
category ``pii`` per SPEC_pki_keys §1.2) is written as CIPHERTEXT and decrypted
only in the handler that hands it back.

Scope (MVP Phase 3, deliberately small — this is the application-side seam, not
the full KMS).  The full key hierarchy (L0 master → per-tenant KEK → per-category
DEK envelope, rotation/revocation, certified СКЗИ provider) is specified in
``docs/design/specs/platform/SPEC_pki_keys.md`` (ADR-006, gap D2) and lands with
the ``kms`` domain.  Here we provide the **abstract crypto seam** those specs call
(``encrypt`` / ``decrypt``) with a single env-keyed category key, structured so the
backend can later be swapped for a KMS/СКЗИ provider WITHOUT touching callers.

Backends (auto-selected, strongest available wins)
--------------------------------------------------
1. **pgcrypto** (the real prod path for the PostgreSQL store) — sensitive columns
   are encrypted with ``pgp_sym_encrypt`` / decrypted with ``pgp_sym_decrypt`` IN
   THE DATABASE, keyed by the same ``PDN_KEY`` secret. See ``access/pgstore.py``;
   this module supplies the Python-side counterpart + key for the sqlite dev store
   and as a fallback.
2. **AES-256-GCM** (AEAD) via the ``cryptography`` lib when importable — the
   preferred Python-side cipher.  Key = HKDF-SHA256(PDN_KEY, info="pdn:<keyid>").
3. **dev fallback** (stdlib only, when ``cryptography`` is absent) — a clearly
   marked, keyed HMAC-SHA256 keystream-XOR transform.  It makes the stored value
   ciphertext at rest (a raw DB dump no longer reveals the name) but is **NOT an
   AEAD and NOT a certified СКЗИ** — it exists so dev/CI without ``cryptography``
   still stores ciphertext and the suite stays green.  Production uses pgcrypto
   (PG) or AES-GCM (with ``cryptography`` installed); for УЗ-2 a certified ФСТЭК
   СКЗИ provider replaces this layer (SPEC_pki_keys §4.1).

Key + rotation (env-driven; no secret in code)
----------------------------------------------
The key secret comes from the environment — ``PDN_KEY`` by default, never a
literal in the repo (BEST_PRACTICES §6; prod sources it from Vault/SOPS, not env).
Every ciphertext token embeds a **key id** so keys can be ROTATED without a bulk
re-encrypt (SPEC_pki_keys §2 "version, not replace"):

  * the active key id is ``PDN_KEY_ID`` (default ``'1'``); its secret is the env
    var ``PDN_KEY`` (or ``PDN_KEY_<id>`` for a specific version);
  * a token written under key id ``k`` is ``pdn:v1:<backend>:<k>:<payload>``;
  * ``decrypt`` reads the token's own key id and looks up ``PDN_KEY_<that id>``
    (falling back to ``PDN_KEY``), so old-version ciphertext stays readable in the
    grace window while NEW writes use the active id — lazy re-encrypt on the next
    upsert.  To rotate: set ``PDN_KEY_ID=2`` + ``PDN_KEY_2=<new secret>`` (keep
    ``PDN_KEY_1`` for reads), redeploy; rows re-wrap as they are next written.

Transparency
------------
``decrypt`` is tolerant: a value that is NOT a recognized ``pdn:`` token (e.g. a
legacy plaintext row written before this landed, or an empty string) is returned
unchanged.  ``encrypt('')`` / ``encrypt(None)`` return the input unchanged (no
point ciphering an empty PII slot).  So the cipher is transparent to callers and
safe to roll out over a store that already has plaintext rows.
"""
import base64
import hashlib
import hmac
import os

# Token wire format:  pdn:<fmt_ver>:<backend>:<key_id>:<b64payload>
_PREFIX = 'pdn'
_FMT_VER = 'v1'
_B_GCM = 'gcm'        # AES-256-GCM (cryptography lib)
_B_DEV = 'dev'        # stdlib HMAC keystream XOR (dev/CI fallback)

# Env knobs (overridable). PDN_KEY holds the active secret; PDN_KEY_ID names the
# active key version; PDN_KEY_<id> can hold a specific version's secret for reads.
_ENV_SECRET = 'PDN_KEY'
_ENV_KEY_ID = 'PDN_KEY_ID'
_DEFAULT_KEY_ID = '1'

# A documented dev default so the suite + a fresh dev box work with zero config.
# This is NOT a production secret: prod MUST set PDN_KEY from Vault/SOPS. The value
# being public is fine for the dev fallback (it only protects a dev sqlite file).
_DEV_DEFAULT_SECRET = 'irbis-dev-pdn-key-not-for-production'


def active_key_id():
    """The key id NEW ciphertext is written under (env ``PDN_KEY_ID``, default '1')."""
    return (os.environ.get(_ENV_KEY_ID) or _DEFAULT_KEY_ID).strip() or _DEFAULT_KEY_ID


def _secret_for(key_id):
    """Resolve the raw secret bytes for ``key_id``.

    Looks up ``PDN_KEY_<id>`` first (per-version, for rotation), then the generic
    ``PDN_KEY``, then the documented dev default.  Returns bytes."""
    val = os.environ.get('%s_%s' % (_ENV_SECRET, key_id)) or os.environ.get(_ENV_SECRET)
    if not val:
        val = _DEV_DEFAULT_SECRET
    return val.encode('utf-8')


def _derive(secret, key_id, length=32):
    """Derive a category key from the env secret bound to the key id.

    HKDF-SHA256 (RFC 5869) with ``info='pdn:<key_id>'`` so the derived key is
    domain-separated per category/version (SPEC_pki_keys §1.2 — HKDF on L2 with
    info-binding is the sanctioned use). Stdlib-only via ``hashlib``."""
    info = ('%s:%s' % (_PREFIX, key_id)).encode('utf-8')
    # HKDF-Extract then HKDF-Expand (single block: length<=32 for SHA-256).
    salt = b'\x00' * hashlib.sha256().digest_size
    prk = hmac.new(salt, secret, hashlib.sha256).digest()
    okm = hmac.new(prk, info + b'\x01', hashlib.sha256).digest()
    return okm[:length]


def _has_cryptography():
    try:
        import cryptography  # noqa: F401
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM  # noqa: F401
        return True
    except Exception:
        return False


def backend():
    """The Python-side backend that ``encrypt`` will use: 'gcm' or 'dev'.

    'gcm' (AES-256-GCM) when the ``cryptography`` lib is importable, else the
    stdlib 'dev' fallback. (The PG store additionally uses pgcrypto in-database;
    this names the in-process Python cipher.)"""
    return _B_GCM if _has_cryptography() else _B_DEV


def aead_available():
    """True iff a real AEAD (AES-GCM) backend is available in this environment.

    Tests use this to SKIP-WITH-NOTE the strong-cipher leg (and exercise the dev
    fallback instead) rather than fail CI when ``cryptography`` is not installed."""
    return _has_cryptography()


def is_token(value):
    """True iff ``value`` looks like one of our ciphertext tokens (``pdn:v1:…``)."""
    return isinstance(value, str) and value.startswith(_PREFIX + ':' + _FMT_VER + ':')


# --------------------------------------------------------------------------- #
# AES-256-GCM (AEAD) — preferred Python cipher when `cryptography` is present.
# --------------------------------------------------------------------------- #
def _gcm_encrypt(plaintext, key_id):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    key = _derive(_secret_for(key_id), key_id, 32)
    nonce = os.urandom(12)
    ct = AESGCM(key).encrypt(nonce, plaintext.encode('utf-8'), None)
    payload = base64.b64encode(nonce + ct).decode('ascii')
    return _join(_B_GCM, key_id, payload)


def _gcm_decrypt(payload, key_id):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    key = _derive(_secret_for(key_id), key_id, 32)
    raw = base64.b64decode(payload)
    nonce, ct = raw[:12], raw[12:]
    return AESGCM(key).decrypt(nonce, ct, None).decode('utf-8')


# --------------------------------------------------------------------------- #
# Dev fallback (stdlib only) — keyed HMAC-SHA256 keystream XOR. NOT an AEAD and
# NOT a certified СКЗИ; makes the stored value ciphertext-at-rest so a raw dump
# does not reveal the name, and keeps dev/CI green without `cryptography`.
# --------------------------------------------------------------------------- #
def _dev_keystream(key, nonce, n):
    """CTR-style keystream: HMAC-SHA256(key, nonce||counter) blocks, truncated."""
    out = bytearray()
    counter = 0
    while len(out) < n:
        block = hmac.new(key, nonce + counter.to_bytes(8, 'big'), hashlib.sha256).digest()
        out.extend(block)
        counter += 1
    return bytes(out[:n])


def _dev_encrypt(plaintext, key_id):
    key = _derive(_secret_for(key_id), key_id, 32)
    data = plaintext.encode('utf-8')
    nonce = os.urandom(16)
    ks = _dev_keystream(key, nonce, len(data))
    ct = bytes(a ^ b for a, b in zip(data, ks))
    # Bind a keyed tag over (nonce||ct) so tampering/empty payloads are detected
    # on decrypt (tamper-evident, though not a true AEAD).
    tag = hmac.new(key, nonce + ct, hashlib.sha256).digest()[:16]
    payload = base64.b64encode(nonce + tag + ct).decode('ascii')
    return _join(_B_DEV, key_id, payload)


def _dev_decrypt(payload, key_id):
    key = _derive(_secret_for(key_id), key_id, 32)
    raw = base64.b64decode(payload)
    nonce, tag, ct = raw[:16], raw[16:32], raw[32:]
    expect = hmac.new(key, nonce + ct, hashlib.sha256).digest()[:16]
    if not hmac.compare_digest(tag, expect):
        raise ValueError('pdn dev-cipher tag mismatch (wrong key or tampered)')
    ks = _dev_keystream(key, nonce, len(ct))
    return bytes(a ^ b for a, b in zip(ct, ks)).decode('utf-8')


# --------------------------------------------------------------------------- #
# Public seam.
# --------------------------------------------------------------------------- #
def _join(b, key_id, payload):
    return ':'.join((_PREFIX, _FMT_VER, b, key_id, payload))


def _split(token):
    """Parse ``pdn:v1:<backend>:<key_id>:<payload>`` → (backend, key_id, payload)."""
    parts = token.split(':', 4)
    if len(parts) != 5 or parts[0] != _PREFIX or parts[1] != _FMT_VER:
        raise ValueError('not a pdn token')
    return parts[2], parts[3], parts[4]


def encrypt(plaintext):
    """Encrypt a PII string to a self-describing ciphertext token.

    Empty / None passes through unchanged (no point ciphering an empty slot, and
    it keeps NULL columns NULL). Uses AES-GCM when available, else the dev
    fallback; the active key id is embedded for rotation. Idempotent-safe: an
    already-encrypted token is returned as-is (never double-wrapped)."""
    if plaintext is None or plaintext == '':
        return plaintext
    if is_token(plaintext):
        return plaintext
    key_id = active_key_id()
    if _has_cryptography():
        return _gcm_encrypt(plaintext, key_id)
    return _dev_encrypt(plaintext, key_id)


def decrypt(value):
    """Decrypt a ciphertext token back to plaintext (transparent for non-tokens).

    A value that is not a recognized ``pdn:`` token (legacy plaintext, empty,
    None) is returned unchanged, so callers can decrypt unconditionally and roll
    out over a store that still holds plaintext rows. The token's own key id +
    backend select the secret/cipher, so rotated/old-version ciphertext still
    reads."""
    if not is_token(value):
        return value
    b, key_id, payload = _split(value)
    if b == _B_GCM:
        return _gcm_decrypt(payload, key_id)
    if b == _B_DEV:
        return _dev_decrypt(payload, key_id)
    raise ValueError('unknown pdn backend %r' % b)


# pgcrypto SQL fragments for the PostgreSQL store (the real prod at-rest path).
# The PG store wraps the sensitive column with these so ciphertext never leaves
# the database in the clear; the key is the SAME PDN_KEY env secret, passed as a
# bound parameter (never interpolated). ``pgcrypto`` ships with PostgreSQL
# (CREATE EXTENSION pgcrypto) — the store creates it best-effort.
def pg_key():
    """The symmetric key string handed to pgcrypto pgp_sym_encrypt/decrypt.

    Bound to the active key id via the same env secret so PG and Python agree on
    which secret protects a tenant's PII column."""
    key_id = active_key_id()
    return _secret_for(key_id).decode('utf-8')
