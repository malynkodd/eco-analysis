#!/usr/bin/env bash
# Generates a self-signed TLS cert (RSA-2048) for the NGINX gateway.
# DEV ONLY — do not use in production. In production, mount certs from
# Let's Encrypt / cert-manager / your secrets manager.
#
# Usage:  ./scripts/generate_tls.sh
# Output: nginx/ssl/cert.pem  +  nginx/ssl/key.pem

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SSL_DIR="${ROOT_DIR}/nginx/ssl"
CERT="${SSL_DIR}/cert.pem"
KEY="${SSL_DIR}/key.pem"

mkdir -p "${SSL_DIR}"

if [[ -f "${CERT}" || -f "${KEY}" ]]; then
    echo "ERROR: TLS material already exists in ${SSL_DIR}. Refusing to overwrite." >&2
    exit 1
fi

command -v openssl >/dev/null 2>&1 || {
    echo "ERROR: openssl is required." >&2
    exit 1
}

echo "==> generating self-signed cert..."
openssl req -x509 -nodes -newkey rsa:2048 \
    -keyout "${KEY}" \
    -out "${CERT}" \
    -days 365 \
    -subj "/CN=localhost/O=eco-analysis-dev" \
    -addext "subjectAltName=DNS:localhost,DNS:nginx,IP:127.0.0.1" \
    >/dev/null 2>&1

chmod 600 "${KEY}"
chmod 644 "${CERT}"

echo "==> done."
echo "    cert: ${CERT}"
echo "    key : ${KEY}"
