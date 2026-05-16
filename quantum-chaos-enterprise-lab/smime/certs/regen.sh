#!/usr/bin/env bash
# Phase 79 — S/MIME LDAP Discovery
# Regenerate deterministic S/MIME cert fixtures (alice/bob/carol) as DER blobs.
#
# Developer tool only. NOT runtime — DER blobs are committed to git so the lab
# works without OpenSSL at runtime. Re-run this script only when you need to
# refresh cert material (e.g., to extend notAfter).
#
# Usage:
#   ./regen.sh           # regenerate all three certs + refresh users.ldif stanzas
#
# Cert profiles (per 79-CONTEXT.md D-Area-3 / 79-RESEARCH):
#   alice.der  RSA-1024, SHA-1   sig   CN=alice  -> HIGH (weak sig + weak key)
#   bob.der    RSA-1024, SHA-256 sig   CN=bob    -> HIGH (weak key only)
#   carol.der  RSA-2048, SHA-256 sig   CN=carol  -> SAFE
#
# notAfter is intentionally set far in the future so all three certs are
# non-expired; expiry-path detection is exercised by unit-test mocks in
# Plan 79-04, not by lab fixtures (keeps lab signals deterministic).

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LDIF="${HERE}/../ldif/users.ldif"

# 100 years validity window — deterministic non-expired material
DAYS=36500

# Portable base64 -w0 (no line wrapping) helper. macOS base64 has no -w flag.
b64_oneline() {
  # Read stdin, emit single line of base64 (no newlines).
  if base64 --help 2>&1 | grep -q -- '-w'; then
    base64 -w0
  else
    base64 | tr -d '\n'
  fi
}

gen_cert() {
  local name="$1"
  local bits="$2"
  local sigalg="$3"   # -sha1 | -sha256
  local out="${HERE}/${name}.der"

  echo "[regen] ${name}: RSA-${bits} ${sigalg} -> ${out}"

  # tmp key (not committed; deterministic re-gen relies on RSA key + sig date)
  local tmpkey
  tmpkey="$(mktemp -t "smime_${name}_key.XXXXXX")"
  trap 'rm -f "$tmpkey"' RETURN

  openssl req -x509 \
    -newkey "rsa:${bits}" \
    "${sigalg}" \
    -keyout "${tmpkey}" \
    -out "${out}" \
    -outform DER \
    -days "${DAYS}" \
    -nodes \
    -subj "/CN=${name}/O=QUIRK Chaos Lab/OU=S-MIME Fixtures" \
    >/dev/null 2>&1

  rm -f "${tmpkey}"
  trap - RETURN
}

gen_cert alice 1024 -sha1
gen_cert bob   1024 -sha256
gen_cert carol 2048 -sha256

echo "[regen] Refreshing ${LDIF}"

ALICE_B64="$(b64_oneline < "${HERE}/alice.der")"
BOB_B64="$(b64_oneline   < "${HERE}/bob.der")"
CAROL_B64="$(b64_oneline < "${HERE}/carol.der")"

cat > "${LDIF}" <<EOF
# Phase 79 S/MIME chaos lab seed — three deterministic users carrying
# userSMIMECertificate attributes (RFC 2798 / RFC 4523).
#
# NOTE on \`;binary\` option: RFC 4523 mandates the \`;binary\` transfer-encoding
# option for X.509 \`userCertificate\` (LDAP syntax Certificate). However,
# \`userSMIMECertificate\` (OID 2.16.840.1.113730.3.1.40, per inetOrgPerson
# schema) is defined with SYNTAX 1.3.6.1.4.1.1466.115.121.1.5 (Binary), which
# already carries octets directly — adding the \`;binary\` suboption causes
# OpenLDAP to reject the value with "option binary not supported with type"
# (Phase 79-01 deviation Rule 1, 2026-05-16). Use \`userSMIMECertificate::\`
# directly with base64 payload.
#
# Re-applied via \`ldapadd -c\` (continue on already-exists). Idempotent.

dn: ou=people,dc=quirk,dc=lab
objectClass: organizationalUnit
ou: people

dn: uid=alice,ou=people,dc=quirk,dc=lab
objectClass: inetOrgPerson
cn: alice
sn: alice
uid: alice
userSMIMECertificate:: ${ALICE_B64}

dn: uid=bob,ou=people,dc=quirk,dc=lab
objectClass: inetOrgPerson
cn: bob
sn: bob
uid: bob
userSMIMECertificate:: ${BOB_B64}

dn: uid=carol,ou=people,dc=quirk,dc=lab
objectClass: inetOrgPerson
cn: carol
sn: carol
uid: carol
userSMIMECertificate:: ${CAROL_B64}
EOF

echo "[regen] Done."
echo "  alice.der  : $(wc -c < "${HERE}/alice.der") bytes"
echo "  bob.der    : $(wc -c < "${HERE}/bob.der") bytes"
echo "  carol.der  : $(wc -c < "${HERE}/carol.der") bytes"
echo "  users.ldif : $(wc -l < "${LDIF}") lines"
