#!/usr/bin/env bash
set -euo pipefail

BASE="certs/scenarios"
mkdir -p "$BASE"

# Helper: create a CA
make_ca() {
  local name="$1"
  local days="$2"
  mkdir -p "$BASE/$name"
  openssl genrsa -out "$BASE/$name/ca.key" 2048
  openssl req -x509 -new -nodes -key "$BASE/$name/ca.key" -sha256 -days "$days" \
    -subj "/C=US/ST=NY/L=Lab/O=ChaosLab/OU=CA/CN=${name}-CA" \
    -out "$BASE/$name/ca.crt"
}

# Helper: issue a leaf cert signed by a given CA (optionally with custom key size & signature)
issue_leaf() {
  local scen="$1"
  local cn="$2"
  local ca_dir="$3"
  local days="$4"
  local key_bits="$5"
  local sig_alg="$6"   # e.g. "sha256" or "sha1"

  mkdir -p "$BASE/$scen"

  openssl genrsa -out "$BASE/$scen/leaf.key" "$key_bits"
  openssl req -new -key "$BASE/$scen/leaf.key" \
    -subj "/C=US/ST=NY/L=Lab/O=ChaosLab/OU=Server/CN=${cn}" \
    -out "$BASE/$scen/leaf.csr"

  cat > "$BASE/$scen/leaf.ext" <<EXT
subjectAltName=DNS:${cn},DNS:localhost,IP:127.0.0.1
extendedKeyUsage=serverAuth
keyUsage=digitalSignature,keyEncipherment
EXT

  openssl x509 -req -in "$BASE/$scen/leaf.csr" \
    -CA "$BASE/$ca_dir/ca.crt" -CAkey "$BASE/$ca_dir/ca.key" -CAcreateserial \
    -out "$BASE/$scen/leaf.crt" -days "$days" -"${sig_alg}" -extfile "$BASE/$scen/leaf.ext"
}

echo "==> Generating root CA for scenarios"
make_ca "scenario-root" 3650

echo "==> Scenario: missing intermediate (we'll serve only leaf, not chain)"
# We’ll mimic "missing intermediate" by having an intermediate CA, but nginx only serves the leaf cert.
# Root -> Intermediate -> Leaf, but only Leaf is presented.
mkdir -p "$BASE/missing-intermediate"
# Intermediate
openssl genrsa -out "$BASE/missing-intermediate/intermediate.key" 2048
openssl req -new -key "$BASE/missing-intermediate/intermediate.key" \
  -subj "/C=US/ST=NY/L=Lab/O=ChaosLab/OU=CA/CN=MissingIntermediate-ICA" \
  -out "$BASE/missing-intermediate/intermediate.csr"
openssl x509 -req -in "$BASE/missing-intermediate/intermediate.csr" \
  -CA "$BASE/scenario-root/ca.crt" -CAkey "$BASE/scenario-root/ca.key" -CAcreateserial \
  -out "$BASE/missing-intermediate/intermediate.crt" -days 3650 -sha256

# Leaf signed by intermediate
openssl genrsa -out "$BASE/missing-intermediate/leaf.key" 2048
openssl req -new -key "$BASE/missing-intermediate/leaf.key" \
  -subj "/C=US/ST=NY/L=Lab/O=ChaosLab/OU=Server/CN=missing-intermediate.chaos.local" \
  -out "$BASE/missing-intermediate/leaf.csr"
cat > "$BASE/missing-intermediate/leaf.ext" <<EXT
subjectAltName=DNS:missing-intermediate.chaos.local,DNS:localhost,IP:127.0.0.1
extendedKeyUsage=serverAuth
keyUsage=digitalSignature,keyEncipherment
EXT
openssl x509 -req -in "$BASE/missing-intermediate/leaf.csr" \
  -CA "$BASE/missing-intermediate/intermediate.crt" -CAkey "$BASE/missing-intermediate/intermediate.key" -CAcreateserial \
  -out "$BASE/missing-intermediate/leaf.crt" -days 365 -sha256 -extfile "$BASE/missing-intermediate/leaf.ext"

echo "==> Scenario: RSA 1024 leaf (weak key size)"
issue_leaf "rsa1024" "rsa1024.chaos.local" "scenario-root" 365 1024 sha256

echo "==> Scenario: SHA1 signed leaf (legacy signature)"
issue_leaf "sha1" "sha1.chaos.local" "scenario-root" 365 2048 sha1

echo "✅ PhaseA scenario certs generated under $BASE"
echo "   Note: Some clients may treat SHA1 as legacy/unacceptable; that's intended for detection."