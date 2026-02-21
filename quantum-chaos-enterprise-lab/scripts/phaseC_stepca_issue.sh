#!/usr/bin/env bash
set -euo pipefail

# -----------------------------
# Rotation automation options
# -----------------------------
ROTATE_LOOP=0
ROTATE_EVERY_MINUTES=0
RECREATE_GATEWAY=1
PROJECT_NAME="chaoslab"

usage() {
  cat <<'USAGE'
Usage:
  ./scripts/phaseC_stepca_issue.sh
      One-shot: (re)issue certs into certs/stepca AND restart mtls-stepca-gateway.

  ./scripts/phaseC_stepca_issue.sh --recreate 0
      One-shot but do not restart the gateway.

  ./scripts/phaseC_stepca_issue.sh --loop --every-min 60
      Loop: re-issue certs every N minutes and restart gateway each cycle.

Options:
  --project <name>     Compose project name (default: chaoslab)

Notes:
  - Gateway restart uses:
      docker compose -p <project> --profile identity --profile pki up -d --force-recreate mtls-stepca-gateway
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --loop) ROTATE_LOOP=1; shift ;;
    --every-min) ROTATE_EVERY_MINUTES="${2:-0}"; shift 2 ;;
    --recreate) RECREATE_GATEWAY="${2:-1}"; shift 2 ;;
    --project) PROJECT_NAME="${2:-chaoslab}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1"; usage; exit 2 ;;
  esac
done

if [[ "${ROTATE_LOOP}" -eq 1 && "${ROTATE_EVERY_MINUTES}" -le 0 ]]; then
  echo "ERROR: --loop requires --every-min <minutes> (e.g., --every-min 60)"
  exit 2
fi

issue_once() {
  local STEPCA_CONTAINER="chaoslab-step-ca-1"
  local OUT_DIR="certs/stepca"
  local TMP_DIR="${OUT_DIR}/_tmp"

  mkdir -p "$OUT_DIR" "$TMP_DIR"
  echo "==> Output directory: $OUT_DIR"

  echo "==> Checking step-ca container..."
  docker ps --format '{{.Names}}' | grep -q "^${STEPCA_CONTAINER}$" || {
    echo "step-ca container not running: $STEPCA_CONTAINER"
    echo "Start identity profile first:"
    echo "  docker compose -p ${PROJECT_NAME} --profile identity up -d"
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

  # Server fullchain (leaf + intermediate) for clients
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

  # Intermediate + client chain + CA bundle
  echo "==> Writing intermediate CA, client chain, and CA bundle..."
  docker exec "$STEPCA_CONTAINER" sh -lc 'cat /home/step/certs/intermediate_ca.crt' > "$OUT_DIR/intermediate_ca.crt"
  cat "$OUT_DIR/client1.crt" "$OUT_DIR/intermediate_ca.crt" > "$OUT_DIR/client1-chain.crt"
  cat "$OUT_DIR/root_ca.crt" "$OUT_DIR/intermediate_ca.crt" > "$OUT_DIR/ca-bundle.crt"

  echo "✅ Phase C artifacts ready:"
  ls -la "$OUT_DIR/root_ca.crt" "$OUT_DIR/intermediate_ca.crt" \
    "$OUT_DIR/mtls-stepca.crt" "$OUT_DIR/mtls-stepca-fullchain.crt" "$OUT_DIR/mtls-stepca.key" \
    "$OUT_DIR/client1.crt" "$OUT_DIR/client1.key" "$OUT_DIR/client1-chain.crt" "$OUT_DIR/ca-bundle.crt"

  echo "==> Cleaning temp secrets..."
  rm -f "$TMP_DIR/intermediate_ca_key" "$TMP_DIR/password" "$TMP_DIR/intermediate_ca_key_plain" \
    "$TMP_DIR/server.key" "$TMP_DIR/server.csr" "$TMP_DIR/server.ext" "$TMP_DIR/intermediate_ca.srl" \
    "$TMP_DIR/client1.key" "$TMP_DIR/client1.csr" "$TMP_DIR/client1.ext" "$TMP_DIR/intermediate_ca.srl" || true
  rmdir "$TMP_DIR" 2>/dev/null || true
}

restart_gateway_and_verify() {
  if [[ "${RECREATE_GATEWAY}" -eq 1 ]]; then
    echo "==> Restarting Phase C gateway (mtls-stepca-gateway) to pick up new certs..."
    docker compose -p "${PROJECT_NAME}" --profile identity --profile pki up -d --force-recreate mtls-stepca-gateway

    echo "==> Served cert dates/serial:"
    openssl s_client -connect 127.0.0.1:17443 -servername mtls-stepca.chaos.local </dev/null 2>/dev/null \
      | openssl x509 -noout -dates -serial || true
  else
    echo "==> Skipping gateway restart (--recreate 0)"
  fi
}

# -----------------------------
# Execute
# -----------------------------
if [[ "${ROTATE_LOOP}" -eq 1 ]]; then
  echo "🔁 Rotation loop enabled: every ${ROTATE_EVERY_MINUTES} minute(s) (Ctrl+C to stop)"
  while true; do
    issue_once
    restart_gateway_and_verify
    echo "==> Sleeping for ${ROTATE_EVERY_MINUTES} minute(s)..."
    sleep $((ROTATE_EVERY_MINUTES * 60))
  done
else
  issue_once
  restart_gateway_and_verify
fi