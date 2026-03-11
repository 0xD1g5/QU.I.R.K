#!/usr/bin/env bash
# demo_reset.sh — Reset Operation Ghost Wait environment to clean baseline
# Usage: ./scripts/demo_reset.sh
# Completes in < 60 seconds. Exits 0 on success.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'

step() { echo -e "\n${BOLD}[$((++STEP_NUM))]${NC} $1"; }
ok()   { echo -e "  ${GREEN}✓${NC} $1"; }
warn() { echo -e "  ${YELLOW}△${NC} $1"; }
err()  { echo -e "  ${RED}✗${NC} $1"; }

STEP_NUM=0
RESET_START=$(date +%s)

echo ""
echo -e "${BOLD}━━━ QFL Demo Reset ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo "  Resetting environment to clean baseline..."

cd "$PROJECT_DIR"

# ─── Step 1: Stop QL service containers ─────────────────────────────────────
step "Stopping QL service containers"
docker compose stop ql-assist ql-docuintel ql-fraudsentinel 2>/dev/null && ok "QL services stopped" || warn "Some services may not have been running"

# ─── Step 2: Clear vector store volume (DocuIntel) ──────────────────────────
step "Clearing QL-DocuIntel vector store"
docker compose run --rm --no-deps \
  -v docuintel-vectorstore:/data \
  --entrypoint sh \
  ql-docuintel -c "rm -rf /data/*" 2>/dev/null && ok "Vector store cleared" || \
  (docker volume rm ghost_weight_docuintel-vectorstore 2>/dev/null || true; ok "Vector store volume removed (will be recreated)")

# ─── Step 3: Clear memory store volume (FraudSentinel) ──────────────────────
step "Clearing QL-FraudSentinel memory store"
docker compose run --rm --no-deps \
  -v fraudsentinel-memory:/data \
  --entrypoint sh \
  ql-fraudsentinel -c "rm -rf /data/*" 2>/dev/null && ok "Memory store cleared" || \
  (docker volume rm ghost_weight_fraudsentinel-memory 2>/dev/null || true; ok "Memory store volume removed (will be recreated)")

# ─── Step 4: Delete and recreate OpenSearch SIEM index ──────────────────────
step "Resetting SIEM event index (OpenSearch)"
if curl -sf "http://localhost:9200/_cluster/health" > /dev/null 2>&1; then
  # Delete all qfl-events-* indexes
  DELETE_RESULT=$(curl -sf -X DELETE "http://localhost:9200/qfl-events-*" 2>/dev/null || echo "")
  if echo "$DELETE_RESULT" | grep -q '"acknowledged":true'; then
    ok "SIEM indexes deleted"
  else
    warn "No SIEM indexes found (already clean)"
  fi
else
  warn "OpenSearch not reachable — SIEM index reset skipped"
fi

# ─── Step 5: Restart QL service containers ──────────────────────────────────
step "Starting QL services"
docker compose up -d ql-assist ql-docuintel ql-fraudsentinel 2>/dev/null && ok "QL services starting" || { err "Failed to start QL services"; exit 1; }

# Wait for services to become healthy
echo "  Waiting for services to become healthy..."
MAX_WAIT=45
ELAPSED=0
ALL_HEALTHY=false
while [ $ELAPSED -lt $MAX_WAIT ]; do
  ASSIST_OK=$(curl -sf "http://localhost:8001/health" > /dev/null 2>&1 && echo "y" || echo "n")
  DOCU_OK=$(curl -sf "http://localhost:8002/health" > /dev/null 2>&1 && echo "y" || echo "n")
  FRAUD_OK=$(curl -sf "http://localhost:8003/health" > /dev/null 2>&1 && echo "y" || echo "n")
  if [ "$ASSIST_OK$DOCU_OK$FRAUD_OK" = "yyy" ]; then
    ALL_HEALTHY=true
    break
  fi
  sleep 3
  ELAPSED=$((ELAPSED + 3))
  echo -n "."
done
echo ""

if $ALL_HEALTHY; then
  ok "All QL services healthy"
else
  warn "Some services not yet healthy — health_check.sh will show details"
fi

# ─── Step 6: Verify clean state ─────────────────────────────────────────────
step "Running health check"
bash "${SCRIPT_DIR}/health_check.sh"

# ─── Timing check ───────────────────────────────────────────────────────────
RESET_END=$(date +%s)
RESET_ELAPSED=$((RESET_END - RESET_START))

echo -e "${BOLD}━━━ Reset Complete ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
if [ "$RESET_ELAPSED" -le 60 ]; then
  echo -e "  ${GREEN}✓${NC} Completed in ${RESET_ELAPSED}s (within 60s budget)"
else
  echo -e "  ${YELLOW}△${NC} Completed in ${RESET_ELAPSED}s (exceeded 60s budget — investigate container startup)"
fi
echo ""
