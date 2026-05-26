#!/usr/bin/env bash
# QU.I.R.K. — Distributed E2E Orchestrator
#
# Runs the full enroll → push → merge workflow against the distributed lab stack.
# Requires the stack to already be up via: ./lab.sh distributed up
#
# Usage:
#   ./lab.sh distributed e2e
#   # or directly:
#   bash quantum-chaos-enterprise-lab/scripts/distributed-e2e.sh
#
# Orchestration steps:
#   1. enroll  — provision each sensor in the console DB; capture bearer tokens
#   2. push    — each sensor scans crypto.internal:443 locally and pushes to console
#   3. merge   — console merges all pushed findings into a unified CBOM + score
#
# The live run is human-UAT; this script delivers a runnable orchestrator.
# Automated verification floor: tests/test_distributed_topology.py.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAB_DIR="$(dirname "${SCRIPT_DIR}")"
DIST_COMPOSE="${LAB_DIR}/docker-compose.distributed.yml"
PROJECT="quirk-dist"

DC="docker compose -p ${PROJECT} -f ${DIST_COMPOSE}"

CONSOLE_URL="http://console:8512"

echo "==> Distributed E2E: enroll → push → merge"
echo "    Project:  ${PROJECT}"
echo "    Compose:  ${DIST_COMPOSE}"

# -----------------------------------------------------------------------
# Step 1: enroll — provision each sensor in the console DB
# -T disables TTY allocation so $() captures stdout cleanly.
# The bearer token is on the last line of stdout; extract it.
# -----------------------------------------------------------------------
echo ""
echo "--- Step 1: enroll (provision sensors in console DB) ---"

echo "  Enrolling sensor-a (segment-a)..."
ENROLL_OUT_A=$(${DC} exec -T console \
  quirk console enroll --segment segment-a --sensor-id sensor-a 2>/dev/null)
TOKEN_A=$(echo "${ENROLL_OUT_A}" | tail -n1)
# WR-03: command-substitution failures do NOT trigger set -e; guard explicitly.
if [[ -z "${TOKEN_A}" ]]; then
  echo "ERROR: enrollment failed for sensor-a (empty token — console may not be ready)" >&2
  exit 1
fi
echo "  sensor-a enrolled."

echo "  Enrolling sensor-b (segment-b)..."
ENROLL_OUT_B=$(${DC} exec -T console \
  quirk console enroll --segment segment-b --sensor-id sensor-b 2>/dev/null)
TOKEN_B=$(echo "${ENROLL_OUT_B}" | tail -n1)
# WR-03: same empty-token guard for sensor-b.
if [[ -z "${TOKEN_B}" ]]; then
  echo "ERROR: enrollment failed for sensor-b (empty token — console may not be ready)" >&2
  exit 1
fi
echo "  sensor-b enrolled."

# -----------------------------------------------------------------------
# Step 2: push — write sensor config then run scan + push to console
# Each sensor enrolls with its bearer token, then pushes its local scan.
#
# CR-03: CONSOLE_URL resolves to a private RFC1918 IP inside the container
# (console is on console-net 10.30.0.x).  --allow-internal-console opts in
# to allow private-IP console URLs — this is trusted at enroll time (the
# operator controls both the sensor container and the console network).
# The flag is persisted in sensor.yaml so subsequent `push` calls also
# allow the internal URL automatically.  Redirect-SSRF protection
# (_NoRedirectHandler) and metadata-service blocking remain in force.
#
# --scan-config /quirk/sensor-config.yaml: the scan target (crypto.internal:443)
# comes from the mounted config file, not a --target CLI flag (which does not
# exist on `quirk sensor push`).
# -----------------------------------------------------------------------
echo ""
echo "--- Step 2: push (scan local target + push findings to console) ---"

echo "  Configuring + pushing sensor-a..."
${DC} exec -T sensor-a \
  quirk sensor enroll "${CONSOLE_URL}" --segment segment-a --api-token "${TOKEN_A}" \
  --allow-internal-console
${DC} exec -T sensor-a \
  quirk sensor push --scan-config /quirk/sensor-config.yaml
echo "  sensor-a push complete."

echo "  Configuring + pushing sensor-b..."
${DC} exec -T sensor-b \
  quirk sensor enroll "${CONSOLE_URL}" --segment segment-b --api-token "${TOKEN_B}" \
  --allow-internal-console
${DC} exec -T sensor-b \
  quirk sensor push --scan-config /quirk/sensor-config.yaml
echo "  sensor-b push complete."

# -----------------------------------------------------------------------
# Step 3: merge — produce unified CBOM + score on the console
# -----------------------------------------------------------------------
echo ""
echo "--- Step 3: merge (build unified CBOM + quantum-readiness score) ---"

${DC} exec -T console \
  quirk sensor merge

echo ""
echo "==> Distributed E2E complete."
echo "    Two sensors scanned crypto.internal:443 (one per segment)."
echo "    The console merged their findings into a single CBOM + score."
echo "    Expected: two CryptoEndpoint components with host=crypto.internal,"
echo "    differing by sensor_id — proving MERGE-03 under real Docker networking."
