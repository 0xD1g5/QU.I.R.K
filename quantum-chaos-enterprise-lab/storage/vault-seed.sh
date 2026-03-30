#!/bin/sh
set -e

export VAULT_ADDR="http://vault:8200"
export VAULT_TOKEN="${VAULT_DEV_ROOT_TOKEN_ID:-root}"

echo "=== Waiting for Vault to be ready ==="
until vault status > /dev/null 2>&1; do
  echo "Waiting for Vault..."
  sleep 2
done
sleep 3  # Extra buffer after initial readiness

echo "=== Enabling transit secrets engine ==="
vault secrets enable transit 2>/dev/null || echo "Transit already enabled"

echo "=== Creating transit engine keys ==="
vault write -f transit/keys/rsa-2048 type=rsa-2048
vault write -f transit/keys/rsa-1024 type=rsa-1024
vault write -f transit/keys/aes256 type=aes256-gcm96
vault write -f transit/keys/ecdsa-p256 type=ecdsa-p256

echo "=== Enabling KV secrets engine ==="
vault secrets enable -version=2 kv 2>/dev/null || echo "KV already enabled"

echo "=== Writing KV secrets (simulates hardcoded secrets finding) ==="
vault kv put secret/crypto-lab \
  api_key="hardcoded-secret-12345" \
  rsa_private_key="-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA...\n-----END RSA PRIVATE KEY-----" \
  weak_hmac_secret="short"

echo "=== Vault seed complete ==="
vault secrets list
