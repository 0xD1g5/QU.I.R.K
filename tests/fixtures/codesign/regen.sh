#!/usr/bin/env bash
# Phase 95 — Code-Signing Certificate Inventory
# Regenerate deterministic code-signing cert fixtures as DER blobs.
#
# Developer tool only. NOT runtime — DER blobs are committed to git so the
# test suite works without OpenSSL at runtime. Re-run this script only when
# you need to refresh cert material (e.g., to extend notAfter).
#
# Usage:
#   ./regen.sh           # regenerate all four DER fixtures
#
# Cert profiles (per 95-CONTEXT.md decisions / 95-RESEARCH):
#   codesign_rsa1024_sha1.der          RSA-1024, SHA-1  sig, CodeSigning EKU  → HIGH
#   codesign_ec192.der                 EC prime192v1,  SHA-256 sig, CodeSigning EKU → HIGH (weak-ec-key)
#   codesign_rsa2048_sha256.der        RSA-2048, SHA-256 sig, CodeSigning EKU → SAFE (filtered)
#   codesign_rsa2048_sha256_noncoding.der  RSA-2048, SHA-256 sig, NO EKU      → SAFE (filtered)
#
# notAfter is intentionally set far in the future (100 years) so all certs
# are non-expired; expiry-path detection is exercised by unit-test mocks,
# not by lab fixtures (keeps lab signals deterministic).

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 100 years validity window — deterministic non-expired material
DAYS=36500

gen_cert_rsa() {
  local name="$1"
  local bits="$2"
  local sigalg="$3"    # -sha1 | -sha256
  local codesign="$4"  # "yes" | "no"
  local out="${HERE}/${name}.der"

  echo "[regen] ${name}: RSA-${bits} ${sigalg} codesign=${codesign} -> ${out}"

  local tmpkey
  tmpkey="$(mktemp -t "codesign_${name}_key.XXXXXX")"
  trap 'rm -f "$tmpkey"' RETURN

  if [ "$codesign" = "yes" ]; then
    openssl req -x509 \
      -newkey "rsa:${bits}" \
      "${sigalg}" \
      -keyout "${tmpkey}" \
      -out "${out}" \
      -outform DER \
      -days "${DAYS}" \
      -nodes \
      -subj "/CN=${name}/O=QUIRK Chaos Lab/OU=CodeSign Fixtures" \
      -addext "extendedKeyUsage=codeSigning" \
      >/dev/null 2>&1
  else
    openssl req -x509 \
      -newkey "rsa:${bits}" \
      "${sigalg}" \
      -keyout "${tmpkey}" \
      -out "${out}" \
      -outform DER \
      -days "${DAYS}" \
      -nodes \
      -subj "/CN=${name}/O=QUIRK Chaos Lab/OU=CodeSign Fixtures" \
      >/dev/null 2>&1
  fi

  rm -f "${tmpkey}"
  trap - RETURN
}

gen_cert_ec() {
  local name="$1"
  local curve="$2"   # prime192v1 | prime256v1
  local sigalg="$3"  # -sha256
  local codesign="$4"
  local out="${HERE}/${name}.der"

  echo "[regen] ${name}: EC ${curve} ${sigalg} codesign=${codesign} -> ${out}"

  local tmpkey
  tmpkey="$(mktemp -t "codesign_${name}_key.XXXXXX")"
  trap 'rm -f "$tmpkey"' RETURN

  if [ "$codesign" = "yes" ]; then
    openssl req -x509 \
      -newkey "ec" \
      -pkeyopt "ec_paramgen_curve:${curve}" \
      "${sigalg}" \
      -keyout "${tmpkey}" \
      -out "${out}" \
      -outform DER \
      -days "${DAYS}" \
      -nodes \
      -subj "/CN=${name}/O=QUIRK Chaos Lab/OU=CodeSign Fixtures" \
      -addext "extendedKeyUsage=codeSigning" \
      >/dev/null 2>&1
  else
    openssl req -x509 \
      -newkey "ec" \
      -pkeyopt "ec_paramgen_curve:${curve}" \
      "${sigalg}" \
      -keyout "${tmpkey}" \
      -out "${out}" \
      -outform DER \
      -days "${DAYS}" \
      -nodes \
      -subj "/CN=${name}/O=QUIRK Chaos Lab/OU=CodeSign Fixtures" \
      >/dev/null 2>&1
  fi

  rm -f "${tmpkey}"
  trap - RETURN
}

# RSA-1024, SHA-1, WITH CodeSigning EKU → HIGH (weak-signing-alg + weak-rsa-key)
gen_cert_rsa codesign_rsa1024_sha1 1024 -sha1 yes

# EC prime192v1 (192-bit), SHA-256, WITH CodeSigning EKU → HIGH (weak-ec-key)
gen_cert_ec codesign_ec192 prime192v1 -sha256 yes

# RSA-2048, SHA-256, WITH CodeSigning EKU → SAFE (no finding)
gen_cert_rsa codesign_rsa2048_sha256 2048 -sha256 yes

# RSA-2048, SHA-256, WITHOUT CodeSigning EKU → filtered out (no finding)
gen_cert_rsa codesign_rsa2048_sha256_noncoding 2048 -sha256 no

echo "[regen] Done."
echo "  codesign_rsa1024_sha1.der          : $(wc -c < "${HERE}/codesign_rsa1024_sha1.der") bytes"
echo "  codesign_ec192.der                 : $(wc -c < "${HERE}/codesign_ec192.der") bytes"
echo "  codesign_rsa2048_sha256.der        : $(wc -c < "${HERE}/codesign_rsa2048_sha256.der") bytes"
echo "  codesign_rsa2048_sha256_noncoding.der: $(wc -c < "${HERE}/codesign_rsa2048_sha256_noncoding.der") bytes"
