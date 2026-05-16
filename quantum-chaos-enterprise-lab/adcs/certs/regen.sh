#!/usr/bin/env bash
# Phase 80 — Windows AD CS Scanner
# Regenerate the deterministic weak CA signing cert fixture (RSA-1024 SHA-1).
#
# Developer tool only. NOT runtime — the DER blob is committed to git so the
# lab works without OpenSSL at runtime. Re-run this script only when you need
# to refresh cert material (e.g., to extend notAfter).
#
# Usage:
#   ./regen.sh           # regenerate ca-weak.der and refresh the base64
#                        # blob embedded in ../ldif/10-ca.ldif
#
# Cert profile (per 80-CONTEXT.md / 80-RESEARCH Pattern 3):
#   ca-weak.der  RSA-1024, SHA-1 sig, CN=QUIRK-Lab-CA  -> HIGH (weak CA signing)
#
# notAfter is intentionally set far in the future so the fixture is non-expired;
# expiry-path detection is exercised by unit-test mocks in Plan 80-04, not by
# lab fixtures (keeps lab signals deterministic).

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="${HERE}/ca-weak.der"
LDIF="${HERE}/../ldif/10-ca.ldif"

# 100-year validity window — deterministic non-expired material
DAYS=36500

# Portable base64 -w0 (no line wrapping) helper. macOS base64 has no -w flag.
b64_oneline() {
  if base64 --help 2>&1 | grep -q -- '-w'; then
    base64 -w0
  else
    base64 | tr -d '\n'
  fi
}

tmpkey="$(mktemp -t "adcs_caweak_key.XXXXXX")"
trap 'rm -f "$tmpkey"' EXIT

echo "[regen] ca-weak: RSA-1024 SHA-1 -> ${OUT}"
openssl req -x509 \
  -newkey rsa:1024 \
  -sha1 \
  -keyout "${tmpkey}" \
  -out "${OUT}" \
  -outform DER \
  -days "${DAYS}" \
  -nodes \
  -subj "/CN=QUIRK-Lab-CA/O=QUIRK Chaos Lab/OU=AD CS Fixtures" \
  >/dev/null 2>&1

CA_B64="$(b64_oneline < "${OUT}")"

echo "[regen] Refreshing ${LDIF}"
# 10-ca.ldif contains a literal CA_B64_PLACEHOLDER token on first generation;
# subsequent regens rewrite the cACertificate;binary:: line in place.
if grep -q '^cACertificate;binary::' "${LDIF}" 2>/dev/null; then
  # macOS sed -i requires backup extension; portable sed -E in-place trick:
  python3 - "$LDIF" "$CA_B64" <<'PY'
import sys, pathlib, re
p = pathlib.Path(sys.argv[1])
b64 = sys.argv[2]
txt = p.read_text()
txt = re.sub(r'^cACertificate;binary::.*$', f'cACertificate;binary:: {b64}', txt, flags=re.M)
p.write_text(txt)
PY
fi

echo "[regen] Done."
echo "  ca-weak.der  : $(wc -c < "${OUT}") bytes"
