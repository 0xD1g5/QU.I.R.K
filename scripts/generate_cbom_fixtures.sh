#!/usr/bin/env bash
#
# generate_cbom_fixtures.sh
#
# Regenerates the four canonical sample CBOM fixtures under examples/cbom/.
#
# Background:
#   The fixtures are deterministic, diff-friendly CycloneDX 1.6 CBOM JSON files
#   used as v4.10 "what does QU.I.R.K. output actually look like" reference
#   data. They are checked into the repo so a prospective adopter can cat them
#   without standing up the chaos lab.
#
# Source data:
#   Per-profile CryptoEndpoint synthesizers under tests/_cbom_profiles.py
#   (PROFILE_ENDPOINTS map). These synthesizers encode the exact crypto
#   findings the scanner would emit for each chaos lab profile and are kept in
#   drift-lock with quantum-chaos-enterprise-lab/docker-compose.yml by
#   tests/test_cbom_schema_validation.py.
#
#   We invoke build_cbom() in-process rather than running the full scanner
#   against live docker-compose targets because:
#     - The synthesizers ARE the deterministic ground truth (already used by
#       golden-fixture tests for two phases of CBOM coverage work).
#     - The full scan path injects timestamps, UUIDs, and random BomRefs that
#       require post-processing anyway.
#     - Docker is not always available in CI / worktree contexts.
#
# Determinism:
#   build_cbom() leaks three non-deterministic fields per run:
#     - metadata.timestamp        (datetime.now)
#     - serialNumber              (uuid4)
#     - one auto-generated BomRef on metadata.component (random.random)
#   We normalize all three via jq below.
#
# Usage:
#   ./scripts/generate_cbom_fixtures.sh
#
# Requirements: python3 (with the project venv active or quirk on PYTHONPATH), jq.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

OUT_DIR="examples/cbom"
mkdir -p "$OUT_DIR"

# Fixed placeholder values for normalization.
FIXED_TIMESTAMP="2026-01-01T00:00:00+00:00"
FIXED_SERIAL="urn:uuid:00000000-0000-0000-0000-000000000000"
FIXED_BOMREF="BomRef.fixture.metadata-component"

# Profile combinations per <interfaces> in 85-04-PLAN.md.
# Format: "<output-filename>|<profile1>[,<profile2>...]"
FIXTURES=(
  "tls-only.cbom.json|phaseA"
  "identity.cbom.json|identity,pki"
  "data-at-rest.cbom.json|database"
  "data-in-motion.cbom.json|phaseA,email,broker"
)

for entry in "${FIXTURES[@]}"; do
  fname="${entry%%|*}"
  profiles="${entry##*|}"
  echo "==> Generating $fname  (profiles: $profiles)"
  raw="$(mktemp)"
  trap 'rm -f "$raw"' EXIT

  python3 - "$profiles" > "$raw" <<'PY'
import sys
from tests._cbom_profiles import PROFILE_ENDPOINTS
from quirk.cbom.builder import build_cbom
from cyclonedx.output.json import JsonV1Dot6

profiles = sys.argv[1].split(",")
endpoints = []
for p in profiles:
    endpoints.extend(PROFILE_ENDPOINTS[p]())
bom = build_cbom(endpoints)
print(JsonV1Dot6(bom).output_as_string(indent=2))
PY

  # Normalize:
  #   - serialNumber           -> FIXED_SERIAL
  #   - metadata.timestamp     -> FIXED_TIMESTAMP
  #   - the single auto-generated metadata.component BomRef and any
  #     dependency back-reference to it -> FIXED_BOMREF
  jq --indent 2 \
     --arg ts "$FIXED_TIMESTAMP" \
     --arg sn "$FIXED_SERIAL" \
     --arg br "$FIXED_BOMREF" '
       # 1. fixed serialNumber and timestamp
       .serialNumber = $sn
       | .metadata.timestamp = $ts
       # 2. normalize the auto-generated metadata-component BomRef.
       # Capture whatever auto-ref is currently on metadata.component, then
       # rewrite both the component itself and any dependency entry that
       # back-references it.
       | (.metadata.component."bom-ref") as $oldref
       | if $oldref and ($oldref | startswith("BomRef.")) then
           .metadata.component."bom-ref" = $br
           | .dependencies |= map(
               if .ref == $oldref then .ref = $br else . end
             )
         else . end
     ' "$raw" > "$OUT_DIR/$fname"

  rm -f "$raw"
  size=$(wc -c < "$OUT_DIR/$fname" | tr -d ' ')
  echo "    wrote $OUT_DIR/$fname  (${size} bytes)"
done

echo
echo "Done. Verify with:"
echo "  for f in $OUT_DIR/*.cbom.json; do jq empty \"\$f\" && echo OK \$f; done"
