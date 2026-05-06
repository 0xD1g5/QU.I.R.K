#!/bin/bash
# generate-zones.sh — Generate and sign DNSSEC zone files for chaos lab
#
# Run ONCE during development to regenerate signed zones. Commit the output.
# NOT called at container build time — zones are pre-committed.
#
# Requirements: dnssec-keygen and dnssec-signzone from bind9utils package
#   macOS:  brew install bind
#   Debian: apt-get install -y bind9utils bind9-dnsutils
#   Docker: docker run --rm -v $(pwd)/zones:/zones internetsystemsconsortium/bind9:9.18 bash /zones/../generate-zones.sh
#
# Usage:
#   cd quantum-chaos-enterprise-lab/bind9
#   bash generate-zones.sh

set -euo pipefail

ZONES_DIR="$(cd "$(dirname "$0")/zones" && pwd)"
WORK_DIR="$(mktemp -d)"
trap "rm -rf $WORK_DIR" EXIT

echo "Working directory: $WORK_DIR"
echo "Output directory:  $ZONES_DIR"

# ──────────────────────────────────────────────────────────────────────────────
# weak.chaos.local — RSASHA1 (algorithm 5), NSEC
# ──────────────────────────────────────────────────────────────────────────────
echo "Generating weak.chaos.local (RSASHA1 + NSEC)..."
cp "$ZONES_DIR/weak.chaos.local.zone.base" "$WORK_DIR/weak.chaos.local.zone" 2>/dev/null || \
  cp "$ZONES_DIR/weak.chaos.local.zone" "$WORK_DIR/weak.chaos.local.zone.unsigned"

cd "$WORK_DIR"

# KSK
dnssec-keygen -a RSASHA1 -b 2048 -f KSK -n ZONE weak.chaos.local
# ZSK
dnssec-keygen -a RSASHA1 -b 1024 -n ZONE weak.chaos.local

# Create unsigned zone if needed
cat > weak.chaos.local.zone << 'ZONE'
$TTL 300
$ORIGIN weak.chaos.local.
@ IN SOA ns1 admin 2024010101 3600 900 604800 300
@ IN NS ns1
ns1 IN A 127.0.0.1
@ IN A 127.0.0.1
ZONE

dnssec-signzone -o weak.chaos.local -N INCREMENT weak.chaos.local.zone
cp weak.chaos.local.zone.signed "$ZONES_DIR/weak.chaos.local.zone"

# ──────────────────────────────────────────────────────────────────────────────
# safe.chaos.local — ECDSAP256SHA256 (algorithm 13), NSEC3
# ──────────────────────────────────────────────────────────────────────────────
echo "Generating safe.chaos.local (ECDSAP256SHA256 + NSEC3)..."
cd "$WORK_DIR"

dnssec-keygen -a ECDSAP256SHA256 -f KSK -n ZONE safe.chaos.local
dnssec-keygen -a ECDSAP256SHA256 -n ZONE safe.chaos.local

cat > safe.chaos.local.zone << 'ZONE'
$TTL 300
$ORIGIN safe.chaos.local.
@ IN SOA ns1 admin 2024010101 3600 900 604800 300
@ IN NS ns1
ns1 IN A 127.0.0.1
@ IN A 127.0.0.1
ZONE

SALT=$(head -c 8 /dev/urandom | xxd -p)
dnssec-signzone -o safe.chaos.local -3 "$SALT" -N INCREMENT safe.chaos.local.zone
cp safe.chaos.local.zone.signed "$ZONES_DIR/safe.chaos.local.zone"

# ──────────────────────────────────────────────────────────────────────────────
# broken.chaos.local — ECDSAP256SHA256 with DS key_tag mismatch
# ──────────────────────────────────────────────────────────────────────────────
echo "Generating broken.chaos.local (valid DNSKEY, broken DS)..."
cd "$WORK_DIR"

dnssec-keygen -a ECDSAP256SHA256 -f KSK -n ZONE broken.chaos.local
dnssec-keygen -a ECDSAP256SHA256 -n ZONE broken.chaos.local

cat > broken.chaos.local.zone << 'ZONE'
$TTL 300
$ORIGIN broken.chaos.local.
@ IN SOA ns1 admin 2024010101 3600 900 604800 300
@ IN NS ns1
ns1 IN A 127.0.0.1
@ IN A 127.0.0.1
ZONE

dnssec-signzone -o broken.chaos.local -N INCREMENT broken.chaos.local.zone
SIGNED="broken.chaos.local.zone.signed"

# Inject a DS record with deliberately wrong key_tag (99999)
echo "broken.chaos.local. IN DS 99999 13 2 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef" >> "$SIGNED"

cp "$SIGNED" "$ZONES_DIR/broken.chaos.local.zone"

# ──────────────────────────────────────────────────────────────────────────────
# unsigned.chaos.local — no DNSSEC (plain zone)
# ──────────────────────────────────────────────────────────────────────────────
echo "Writing unsigned.chaos.local (no DNSSEC)..."
cat > "$ZONES_DIR/unsigned.chaos.local.zone" << 'ZONE'
$TTL 300
$ORIGIN unsigned.chaos.local.
@ IN SOA ns1 admin 2024010101 3600 900 604800 300
@ IN NS ns1
ns1 IN A 127.0.0.1
@ IN A 127.0.0.1
ZONE

echo ""
echo "Done. Zone files written to $ZONES_DIR/"
echo "Commit the .zone files to the repository."
