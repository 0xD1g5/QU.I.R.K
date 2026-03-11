#!/usr/bin/env bash
# health_check.sh — Verify all Operation Ghost Wait services are healthy
# Usage: ./scripts/health_check.sh
# Exits 0 if all checks pass, exits 1 if any fail.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

PASS=0
FAIL=0

pass() { echo -e "  ${GREEN}✓${NC} $1"; ((PASS++)); }
fail() { echo -e "  ${RED}✗${NC} $1"; ((FAIL++)); }
warn() { echo -e "  ${YELLOW}△${NC} $1"; }
section() { echo -e "\n${CYAN}${BOLD}$1${NC}"; }

echo ""
echo -e "${BOLD}━━━ QFL Operation Ghost Wait — Health Check ━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# ─── Docker Daemon ──────────────────────────────────────────────────────────
section "Docker"
if docker info > /dev/null 2>&1; then
  pass "Docker daemon running"
else
  fail "Docker daemon not running"
  echo -e "\n${RED}Cannot continue — Docker is required. Start Docker Desktop and retry.${NC}"
  exit 1
fi

# ─── QL Services ────────────────────────────────────────────────────────────
section "QL Services"
check_service() {
  local name=$1
  local url=$2
  if curl -sf "${url}/health" > /dev/null 2>&1; then
    pass "${name} healthy (${url}/health)"
  else
    fail "${name} not responding (${url}/health)"
  fi
}

check_service "QL-Assist" "http://localhost:8001"
check_service "QL-DocuIntel" "http://localhost:8002"
check_service "QL-FraudSentinel" "http://localhost:8003"

# ─── OpenSearch (SIEM) ──────────────────────────────────────────────────────
section "SIEM (OpenSearch)"
OPENSEARCH_STATUS=$(curl -sf "http://localhost:9200/_cluster/health" 2>/dev/null || echo "")
if [ -n "$OPENSEARCH_STATUS" ]; then
  OS_HEALTH=$(echo "$OPENSEARCH_STATUS" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('status','unknown'))" 2>/dev/null || echo "unknown")
  if [ "$OS_HEALTH" = "green" ] || [ "$OS_HEALTH" = "yellow" ]; then
    pass "OpenSearch healthy (status: ${OS_HEALTH})"
  else
    fail "OpenSearch unhealthy (status: ${OS_HEALTH})"
  fi
else
  fail "OpenSearch not responding at http://localhost:9200"
fi

# Check SIEM UI (OpenDashboards)
if curl -sf "http://localhost:5601/api/status" > /dev/null 2>&1; then
  pass "OpenDashboards (SIEM UI) responding at :5601"
else
  fail "OpenDashboards (SIEM UI) not responding at :5601"
fi

# Check index pattern exists
INDEX_CHECK=$(curl -sf "http://localhost:9200/qfl-events-*" 2>/dev/null || echo "")
if echo "$INDEX_CHECK" | grep -q "qfl-events" 2>/dev/null; then
  pass "SIEM index pattern 'qfl-events-*' exists"
else
  warn "SIEM index 'qfl-events-*' not yet created (expected after first log event)"
fi

# ─── Ollama ─────────────────────────────────────────────────────────────────
section "Ollama (AI Backend)"
if bash "${SCRIPT_DIR}/check_ollama.sh" > /dev/null 2>&1; then
  pass "Ollama reachable on host with required model"
else
  fail "Ollama check failed — run: ./scripts/check_ollama.sh for details"
fi

if bash "${SCRIPT_DIR}/check_ollama_from_container.sh" > /dev/null 2>&1; then
  pass "Ollama reachable from Docker containers"
else
  fail "Ollama not reachable from Docker containers — run: ./scripts/check_ollama_from_container.sh for details"
fi

# ─── Orchestrator UI ────────────────────────────────────────────────────────
section "Orchestrator"
if curl -sf "http://localhost:3000" > /dev/null 2>&1; then
  pass "Orchestrator UI responding at http://localhost:3000"
else
  fail "Orchestrator UI not responding at http://localhost:3000"
fi

# ─── Summary ────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}━━━ Summary ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  ${GREEN}Passed: ${PASS}${NC}   ${RED}Failed: ${FAIL}${NC}"
echo ""

if [ "$FAIL" -gt 0 ]; then
  echo -e "${RED}Environment not ready. Resolve failures above before running the demo.${NC}"
  echo ""
  exit 1
else
  echo -e "${GREEN}All checks passed. Environment is ready.${NC}"
  echo -e "  Open ${BOLD}http://localhost:3000${NC} to begin."
  echo ""
  exit 0
fi
