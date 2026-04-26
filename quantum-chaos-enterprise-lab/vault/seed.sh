#!/bin/sh
# Phase 30 chaos lab seed: VAULT-01/02/03 RED finding paths.
# Token auth is automatically present in dev mode (HIGH unconditional, D-05).
set -e

export VAULT_ADDR="${VAULT_ADDR:-http://vault-30:8200}"
export VAULT_TOKEN="${VAULT_DEV_ROOT_TOKEN_ID:-root}"

echo "=== Waiting for Vault to be ready ==="
until vault status > /dev/null 2>&1; do sleep 1; done
sleep 2

# ----- VAULT-01: Transit keys (D-01 + D-02) -----
echo "=== Enabling transit secrets engine ==="
vault secrets enable transit 2>/dev/null || true

echo "=== Creating non-exportable RSA-2048 transit key (D-01 — classification only, no severity) ==="
vault write -f transit/keys/rsa-2048-classification type=rsa-2048

echo "=== Creating exportable RSA-2048 transit key (D-02 — MEDIUM severity) ==="
vault write transit/keys/rsa-2048-exportable type=rsa-2048 exportable=true

# ----- VAULT-02: PKI mount with weak root CA (D-03 — RSA-2048 → HIGH) -----
echo "=== Enabling PKI secrets engine ==="
vault secrets enable pki 2>/dev/null || true

echo "=== Generating RSA-2048 root CA (HIGH finding path) ==="
vault write -field=certificate pki/root/generate/internal \
    common_name="quirk-vault-lab.local" \
    key_type="rsa" key_bits=2048 \
    ttl=8760h > /dev/null

# ----- VAULT-03: Auth methods (D-05 token always-fires + D-06 userpass MEDIUM) -----
echo "=== Enabling userpass auth method (D-06 — MEDIUM finding) ==="
vault auth enable userpass 2>/dev/null || true
vault write auth/userpass/users/labuser password=labpass policies=default

# Token auth is automatically present in dev mode → D-05 always-fires HIGH
echo "=== Vault seed complete ==="
echo "Expected scanner findings:"
echo "  - transit/rsa-2048-classification (severity=None — D-01)"
echo "  - transit/rsa-2048-exportable     (severity=MEDIUM — D-02)"
echo "  - PKI/pki                         (severity=HIGH — D-03 RSA-2048)"
echo "  - auth/token                      (severity=HIGH — D-05 always-fires)"
echo "  - auth/userpass                   (severity=MEDIUM — D-06)"
