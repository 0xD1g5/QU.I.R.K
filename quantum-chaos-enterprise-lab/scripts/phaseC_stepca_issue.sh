#!/usr/bin/env bash
set -euo pipefail

STEPCA_CONTAINER="chaoslab-step-ca-1"
OUT_DIR="certs/stepca"
TMP_DIR="${OUT_DIR}/_tmp"

mkdir -p "$OUT_DIR" "$TMP_DIR"
echo "==> Output directory: $OUT_DIR"

echo "==> Checking step-ca container..."
docker ps --format '{{.Names}}' | grep -q "$STEPCA_CONTAINER" || {
  echo "step-ca container not running: $STEPCA_CONTAINER"
  echo "Start identity profile first: PROFILE_ARGS='--profile identity' ./lab.sh up"
  exit 1
}

echo "==> Verifying host openssl..."
command -v openssl >/dev/null
openssl version

echo "==> Copying CA material from step-ca container to temp dir..."
docker exec "$STEPCA_CONTAINER" sh -lc 'cat /home/step/certs/root_ca.crt' > "$OUT_DIR/root_ca.crt"
docker exec "$STEPCA_CONTAINER" sh -lc 'cat /home/step/certs/intermediate_ca.crt' > "$TMP_DIR/intermediate_ca.crt"
docker exec "$STEPCA_CONTAINER" sh -lc 'cat /home/step/secrets/intermediate_ca_key' > "$TMP_DIR/intermediate_ca_key"
docker exec "$STEPCA_CONTAINER" sh -lc 'cat /home/step/secrets/password' > "$TMP_DIR/password"
ls -la "$OUT_DIR/root_ca.crt" "$TMP_DIR/intermediate_ca.crt" "$TMP_DIR/intermediate_ca_key" "$TMP_DIR/password"

echo "==> Decrypting intermediate CA key (host-side, temp plaintext key)..."
openssl pkey -in "$TMP_DIR/intermediate_ca_key" -passin "file:$TMP_DIR/password" -out "$TMP_DIR/intermediate_ca_key_plain"

# ---- Server cert (mtls-stepca.chaos.local), 24h ----
echo "==> Issuing server certificate for mtls-stepca.chaos.local (24h)..."
openssl genrsa -out "$TMP_DIR/server.key" 2048
openssl req -new -key "$TMP_DIR/server.key" \
  -subj "/C=US/ST=NY/L=Lab/O=ChaosLab/OU=Server/CN=mtls-stepca.chaos.local" \
  -out "$TMP_DIR/server.csr"

cat > "$TMP_DIR/server.ext" <<'EOT'
subjectAltName=DNS:mtls-stepca.chaos.local,DNS:localhost,IP:127.0.0.1
extendedKeyUsage=serverAuth
keyUsage=digitalSignature,keyEncipherment
EOT

openssl x509 -req -in "$TMP_DIR/server.csr" \
  -CA "$TMP_DIR/intermediate_ca.crt" -CAkey "$TMP_DIR/intermediate_ca_key_plain" -CAcreateserial \
  -out "$OUT_DIR/mtls-stepca.crt" -days 1 -sha256 -extfile "$TMP_DIR/server.ext"

# Write server full chain (leaf + intermediate) for clients that require it
cat "$OUT_DIR/mtls-stepca.crt" "$TMP_DIR/intermediate_ca.crt" > "$OUT_DIR/mtls-stepca-fullchain.crt"

cp "$TMP_DIR/server.key" "$OUT_DIR/mtls-stepca.key"

# ---- Client cert (client1), 24h ----
echo "==> Issuing client certificate client1 (24h)..."
openssl genrsa -out "$TMP_DIR/client1.key" 2048
openssl req -new -key "$TMP_DIR/client1.key" \
  -subj "/C=US/ST=NY/L=Lab/O=ChaosLab/OU=Client/CN=client1" \
  -out "$TMP_DIR/client1.csr"

cat > "$TMP_DIR/client1.ext" <<'EOT'
extendedKeyUsage=clientAuth
keyUsage=digitalSignature,keyEncipherment
EOT

openssl x509 -req -in "$TMP_DIR/client1.csr" \
  -CA "$TMP_DIR/intermediate_ca.crt" -CAkey "$TMP_DIR/intermediate_ca_key_plain" -CAcreateserial \
  -out "$OUT_DIR/client1.crt" -days 1 -sha256 -extfile "$TMP_DIR/client1.ext"

cp "$TMP_DIR/client1.key" "$OUT_DIR/client1.key"

# ---- Client chain (leaf + intermediate) for mTLS clients ----
echo "==> Writing intermediate CA and chained client cert..."
docker exec "$STEPCA_CONTAINER" sh -lc 'cat /home/step/certs/intermediate_ca.crt' > "$OUT_DIR/intermediate_ca.crt"
cat "$OUT_DIR/client1.crt" "$OUT_DIR/intermediate_ca.crt" > "$OUT_DIR/client1-chain.crt"

# CA bundle for verifying server chains (root + intermediate)
cat "$OUT_DIR/root_ca.crt" "$OUT_DIR/intermediate_ca.crt" > "$OUT_DIR/ca-bundle.crt"

ls -la "$OUT_DIR/intermediate_ca.crt" "$OUT_DIR/client1-chain.crt"

echo "✅ Phase C artifacts ready:"
ls -la "$OUT_DIR/root_ca.crt" "$OUT_DIR/intermediate_ca.crt" "$OUT_DIR/mtls-stepca.crt" "$OUT_DIR/mtls-stepca-fullchain.crt" "$OUT_DIR/mtls-stepca.key" "$OUT_DIR/client1.crt" "$OUT_DIR/client1.key" "$OUT_DIR/client1-chain.crt" "$OUT_DIR/ca-bundle.crt"
echo "==> Cleaning temp secrets..."
rm -f "$TMP_DIR/intermediate_ca_key" "$TMP_DIR/password" "$TMP_DIR/intermediate_ca_key_plain" \
  "$TMP_DIR/server.key" "$TMP_DIR/server.csr" "$TMP_DIR/server.ext" "$TMP_DIR/intermediate_ca.srl" \
  "$TMP_DIR/client1.key" "$TMP_DIR/client1.csr" "$TMP_DIR/client1.ext" "$TMP_DIR/intermediate_ca.srl" || true
rmdir "$TMP_DIR" 2>/dev/null || true
echo "✅ Done."