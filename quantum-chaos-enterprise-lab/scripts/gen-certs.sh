#!/usr/bin/env bash
set -euo pipefail

mkdir -p certs

echo "==> Generating CA"
openssl genrsa -out certs/ca.key 2048
openssl req -x509 -new -nodes -key certs/ca.key -sha256 -days 3650 \
  -subj "/C=US/ST=NY/L=Lab/O=ChaosLab/OU=CA/CN=ChaosLab-RootCA" \
  -out certs/ca.crt

gen_server() {
  local name=$1
  local cn=$2
  local days=$3

  echo "==> Generating server cert: $name (days=$days)"
  openssl genrsa -out certs/${name}.key 2048
  openssl req -new -key certs/${name}.key \
    -subj "/C=US/ST=NY/L=Lab/O=ChaosLab/OU=Server/CN=${cn}" \
    -out certs/${name}.csr

  cat > certs/${name}.ext <<EOF
subjectAltName=DNS:${cn},DNS:localhost,IP:127.0.0.1
extendedKeyUsage=serverAuth
keyUsage=digitalSignature,keyEncipherment
EOF

  # Sign with our CA
  openssl x509 -req -in certs/${name}.csr \
    -CA certs/ca.crt -CAkey certs/ca.key -CAcreateserial \
    -out certs/${name}.crt -days ${days} -sha256 -extfile certs/${name}.ext
}

echo "==> Generating modern/legacy server certs"
gen_server modern "modern.chaos.local" 365
gen_server legacy "legacy.chaos.local" 365

echo "==> Generating EXPIRED cert (negative days not supported everywhere; use very short + backdate)"
# Create cert valid for 1 day, then we will *force* nginx to still serve it; for true expired,
# set your system date for testing OR regenerate with -startdate/-enddate using advanced openssl options.
# We'll still keep it as a short-lived cert to trigger "expiring soon" logic.
gen_server expired "expired.chaos.local" 1

echo "==> Generating SELFSIGNED cert"
openssl req -x509 -newkey rsa:2048 -sha256 -days 365 -nodes \
  -subj "/C=US/ST=NY/L=Lab/O=ChaosLab/OU=SelfSigned/CN=selfsigned.chaos.local" \
  -keyout certs/selfsigned.key -out certs/selfsigned.crt

echo "==> Generating client cert for mTLS"
openssl genrsa -out certs/client.key 2048
openssl req -new -key certs/client.key \
  -subj "/C=US/ST=NY/L=Lab/O=ChaosLab/OU=Client/CN=client.chaos.local" \
  -out certs/client.csr

cat > certs/client.ext <<EOF
extendedKeyUsage=clientAuth
keyUsage=digitalSignature,keyEncipherment
EOF

openssl x509 -req -in certs/client.csr \
  -CA certs/ca.crt -CAkey certs/ca.key -CAcreateserial \
  -out certs/client.crt -days 365 -sha256 -extfile certs/client.ext

echo "✅ Certs created in ./certs"
echo "NOTE: 'expired' is short-lived (1 day). For truly expired, regenerate with explicit enddate or change clock temporarily in an isolated VM."

