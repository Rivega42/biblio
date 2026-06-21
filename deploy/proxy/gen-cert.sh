#!/usr/bin/env sh
# ─────────────────────────────────────────────────────────────────────────────
# Generate a self-signed TLS cert for LOCAL DEV ONLY (#207, epic #223).
#
# Produces deploy/proxy/certs/{server.crt,server.key}, mounted into the nginx
# proxy at /etc/nginx/certs. These are *.crt/*.key — gitignored, never committed.
#
# DO NOT use a self-signed cert in production. In prod, drop a real certificate
# (e.g. from your internal CA / certbot / Let's Encrypt) into the same paths and
# enable HSTS in nginx.conf. See deploy/README.md → "Prod hardening checklist".
#
# Usage (from repo root or anywhere):
#   sh deploy/proxy/gen-cert.sh            # CN=localhost, 825 days
#   CERT_CN=biblio.local sh deploy/proxy/gen-cert.sh
# Requires: openssl.
# ─────────────────────────────────────────────────────────────────────────────
set -eu

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
CERT_DIR="$SCRIPT_DIR/certs"
CN="${CERT_CN:-localhost}"
DAYS="${CERT_DAYS:-825}"

mkdir -p "$CERT_DIR"

if [ -f "$CERT_DIR/server.crt" ] && [ -f "$CERT_DIR/server.key" ]; then
    echo "Cert already exists at $CERT_DIR — delete server.crt/server.key to regenerate."
    exit 0
fi

echo "Generating self-signed cert (CN=$CN, ${DAYS}d) → $CERT_DIR"
openssl req -x509 -nodes -newkey rsa:2048 \
    -keyout "$CERT_DIR/server.key" \
    -out "$CERT_DIR/server.crt" \
    -days "$DAYS" \
    -subj "/C=RU/O=Biblio Dev/CN=$CN" \
    -addext "subjectAltName=DNS:$CN,DNS:localhost,IP:127.0.0.1"

chmod 600 "$CERT_DIR/server.key"
echo "Done. Dev cert is self-signed — browsers will warn; that's expected for dev."
