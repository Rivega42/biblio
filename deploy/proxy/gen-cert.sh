#!/usr/bin/env sh
# ─────────────────────────────────────────────────────────────────────────────
# Generate a self-signed TLS cert for LOCAL DEV ONLY (#207, epic #223).
#
# Produces deploy/proxy/certs/{server.crt,server.key}, mounted into the nginx
# proxy at /etc/nginx/certs. These are *.crt/*.key — gitignored, never committed.
#
# DO NOT use a self-signed cert in production. In prod, drop a real certificate
# (e.g. from your internal CA / certbot / Let's Encrypt) into the same paths and
# enable HSTS in nginx.conf. See deploy/README.md → "Prod hardening checklist"
# and docs/design/PILOT_READINESS.md → "TLS".
#
# Usage (from repo root or anywhere):
#   sh deploy/proxy/gen-cert.sh            # CN=localhost, 825 days
#   CERT_CN=biblio.local sh deploy/proxy/gen-cert.sh
# Requires: openssl.
#
# ── Cross-platform note (Linux / macOS / Windows git-bash) ───────────────────
# Earlier this script used an inline `-subj "/C=RU/O=…/CN=…"`. On Windows
# git-bash / MSYS2 the shell auto-converts arguments that *look* like Unix paths
# into Windows paths ("MSYS path mangling"). Because `-subj` starts with `/`, it
# was rewritten to e.g. 'C:/Program Files/Git/C=RU/O=Biblio Dev/CN=localhost'
# and openssl rejected it ("subject name is expected to be in the format …") —
# so NO cert was produced on Windows.
#
# Disabling conversion globally (MSYS_NO_PATHCONV=1 / MSYS2_ARG_CONV_EXCL='*')
# fixes -subj but then breaks the legitimate -keyout/-out *file* paths (openssl
# can't open a Unix-style "/c/…" path). So instead we put the subject in an
# OpenSSL **config file** ([req_distinguished_name]) — there is no `/`-prefixed
# inline argument left to mangle, the file-path args still get normal MSYS
# conversion, and the exact same script runs unchanged on Linux/macOS.
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

# Build the OpenSSL request config (subject + SAN). Using a config file instead
# of an inline -subj is what makes this cross-platform (see header note).
CONF_FILE="$CERT_DIR/.gen-cert.cnf"
trap 'rm -f "$CONF_FILE"' EXIT INT TERM
cat > "$CONF_FILE" <<EOF
[req]
distinguished_name = req_distinguished_name
x509_extensions    = v3_ext
prompt             = no

[req_distinguished_name]
C  = RU
O  = Biblio Dev
CN = $CN

[v3_ext]
subjectAltName = DNS:$CN,DNS:localhost,IP:127.0.0.1
basicConstraints = critical,CA:FALSE
keyUsage = critical,digitalSignature,keyEncipherment
extendedKeyUsage = serverAuth
EOF

echo "Generating self-signed cert (CN=$CN, ${DAYS}d) → $CERT_DIR"
openssl req -x509 -nodes -newkey rsa:2048 \
    -keyout "$CERT_DIR/server.key" \
    -out "$CERT_DIR/server.crt" \
    -days "$DAYS" \
    -config "$CONF_FILE"

# Verify both artifacts exist (guards against a silent failure / regression).
if [ ! -s "$CERT_DIR/server.crt" ] || [ ! -s "$CERT_DIR/server.key" ]; then
    echo "ERROR: openssl did not produce both server.crt and server.key." >&2
    exit 1
fi

chmod 600 "$CERT_DIR/server.key"
echo "Done. Wrote:"
echo "  $CERT_DIR/server.crt"
echo "  $CERT_DIR/server.key"
echo "Dev cert is self-signed — browsers will warn; that's expected for dev."
