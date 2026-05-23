#!/usr/bin/env bash
# Phase 95 — Code-Signing Certificate Inventory (LAB-01)
# Regenerate the weak code-signing cert fixture (codesign-weak.der) as a DER blob.
#
# Developer tool only. NOT runtime — DER blob is committed to git so the lab
# works without OpenSSL at runtime. Re-run this script only when you need to
# refresh cert material (e.g., to extend notAfter).
#
# Usage:
#   ./regen.sh           # regenerate codesign-weak.der + refresh codesign-users.ldif
#
# Cert profile (per 95-CONTEXT.md / 95-RESEARCH LAB-01):
#   codesign-weak.der  RSA-1024, SHA-1 sig, CodeSigning EKU -> HIGH (weak sig + weak key)
#
# Base DN: dc=chaos,dc=local (NOT dc=quirk,dc=lab — Critical Caveat 4, 95-PATTERNS.md)
#
# notAfter is intentionally set far in the future so the cert is non-expired;
# expiry-path detection is exercised by unit-test mocks, not by lab fixtures
# (keeps lab signals deterministic).

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LDIF="${HERE}/../ldif/codesign-users.ldif"

# 100 years validity window — deterministic non-expired material
DAYS=36500

# Portable base64 -w0 (no line wrapping) helper. macOS base64 has no -w flag.
b64_oneline() {
  if base64 --help 2>&1 | grep -q -- '-w'; then
    base64 -w0
  else
    base64 | tr -d '\n'
  fi
}

OUT="${HERE}/codesign-weak.der"

echo "[regen] codesign-weak: RSA-1024 -sha1 +CodeSigning EKU -> ${OUT}"

tmpkey="$(mktemp -t "codesign_weak_key.XXXXXX")"
trap 'rm -f "$tmpkey"' EXIT

# RSA-1024 / SHA-1 with extendedKeyUsage=codeSigning (OID 1.3.6.1.5.5.7.3.3)
# This exercises the full HIGH path: weak-rsa-key + weak-signing-alg + CodeSigning EKU.
openssl req -x509 \
  -newkey rsa:1024 \
  -sha1 \
  -keyout "${tmpkey}" \
  -out "${OUT}" \
  -outform DER \
  -days "${DAYS}" \
  -nodes \
  -subj "/CN=codesign-weak/O=QUIRK Chaos Lab/OU=Code-Signing Fixtures" \
  -addext "extendedKeyUsage=codeSigning" \
  >/dev/null 2>&1

echo "[regen] Refreshing ${LDIF}"

CODESIGN_B64="$(b64_oneline < "${OUT}")"

cat > "${LDIF}" <<EOF
# Phase 95 code-signing chaos lab seed — one user carrying a userCertificate
# attribute with CodeSigning EKU (OID 1.3.6.1.5.5.7.3.3) and weak RSA-1024/SHA-1.
#
# Base DN: dc=chaos,dc=local (ldaps profile — NOT dc=quirk,dc=lab).
#
# NOTE: userCertificate uses the ;binary transfer-encoding option per RFC 4523
# (LDAP syntax Certificate, OID 1.3.6.1.4.1.1466.115.121.1.8). This is correct
# and differs from userSMIMECertificate which uses base64 directly without ;binary.
#
# Re-applied via \`ldapadd -c\` (continue on already-exists). Idempotent.

dn: ou=people,dc=chaos,dc=local
objectClass: organizationalUnit
ou: people

dn: uid=codesign-weak,ou=people,dc=chaos,dc=local
objectClass: inetOrgPerson
cn: codesign-weak
sn: codesign-weak
uid: codesign-weak
userCertificate;binary:: ${CODESIGN_B64}
EOF

echo "[regen] Done."
echo "  codesign-weak.der  : $(wc -c < "${OUT}") bytes"
echo "  codesign-users.ldif: $(wc -l < "${LDIF}") lines"
