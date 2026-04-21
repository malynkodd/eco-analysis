#!/usr/bin/env bash
# Generates an RSA-2048 keypair for JWT (RS256) signing/verification.
# Private key: signed by auth-service only. Public key: distributed to verifier services + NGINX.
#
# Usage:   ./scripts/generate_keys.sh
# Output:  keys/jwt_private.pem  (chmod 600)
#          keys/jwt_public.pem   (chmod 644)

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
KEYS_DIR="${ROOT_DIR}/keys"
PRIV="${KEYS_DIR}/jwt_private.pem"
PUB="${KEYS_DIR}/jwt_public.pem"

mkdir -p "${KEYS_DIR}"

if [[ -f "${PRIV}" || -f "${PUB}" ]]; then
    echo "ERROR: keys already exist at ${KEYS_DIR}. Refusing to overwrite." >&2
    echo "       Delete them first if you really want to rotate." >&2
    exit 1
fi

command -v openssl >/dev/null 2>&1 || {
    echo "ERROR: openssl is required but not installed." >&2
    exit 1
}

echo "==> generating RSA-2048 private key..."
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out "${PRIV}" >/dev/null 2>&1

echo "==> deriving public key..."
openssl rsa -in "${PRIV}" -pubout -out "${PUB}" >/dev/null 2>&1

chmod 600 "${PRIV}"
chmod 644 "${PUB}"

echo "==> done."
echo "    private: ${PRIV}"
echo "    public : ${PUB}"
