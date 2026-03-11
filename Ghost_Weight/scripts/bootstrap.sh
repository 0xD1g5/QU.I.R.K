#!/usr/bin/env bash
# bootstrap.sh — One-shot environment setup for Operation Ghost Wait
# Usage: ./scripts/bootstrap.sh
# Run once on a fresh environment. Safe to re-run.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

ok()   { echo -e "  ${GREEN}✓${NC} $1"; }
fail() { echo -e "  ${RED}✗${NC} $1"; }
warn() { echo -e "  ${YELLOW}△${NC} $1"; }
info() { echo -e "  ${CYAN}→${NC} $1"; }

echo ""
echo -e "${BOLD}━━━ Operation Ghost Wait — Bootstrap ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

cd "$PROJECT_DIR"

# ─── Prerequisite: Docker ────────────────────────────────────────────────────
echo -e "${BOLD}[1/6] Checking Docker${NC}"
if ! docker info > /dev/null 2>&1; then
  fail "Docker is not running"
  echo ""
  echo "  Please start Docker Desktop and retry."
  exit 1
fi
ok "Docker running"

# ─── Prerequisite: Ollama + Model ───────────────────────────────────────────
echo -e "\n${BOLD}[2/6] Checking Ollama${NC}"
MODEL="${OLLAMA_MODEL:-llama3.2:3b}"

if ! curl -sf "http://localhost:11434/api/tags" > /dev/null 2>&1; then
  fail "Ollama is not running"
  echo ""
  echo "  Start Ollama:"
  echo "    macOS:   ollama serve"
  echo "    Windows: Start Ollama from system tray or run 'ollama serve'"
  echo ""
  exit 1
fi
ok "Ollama running"

if ! curl -sf "http://localhost:11434/api/tags" | grep -q "${MODEL%%:*}"; then
  fail "Model '${MODEL}' not found"
  echo ""
  info "Pulling model (this may take several minutes)..."
  if ollama pull "$MODEL"; then
    ok "Model '${MODEL}' pulled"
  else
    fail "Failed to pull '${MODEL}'"
    echo "  Manually run: ollama pull ${MODEL}"
    exit 1
  fi
else
  ok "Model '${MODEL}' available"
fi

# ─── Start Docker Compose Stack ─────────────────────────────────────────────
echo -e "\n${BOLD}[3/6] Starting Docker Compose stack${NC}"
info "Starting base stack + SIEM..."
if docker compose -f docker-compose.yml -f docker-compose.siem.yml up -d --build 2>&1 | tail -5; then
  ok "Docker Compose stack started"
else
  fail "Docker Compose failed to start"
  echo "  Run manually: docker compose -f docker-compose.yml -f docker-compose.siem.yml up -d"
  exit 1
fi

# ─── Wait for OpenSearch ─────────────────────────────────────────────────────
echo -e "\n${BOLD}[4/6] Waiting for OpenSearch${NC}"
info "Polling http://localhost:9200/_cluster/health (60s timeout)..."
TIMEOUT=60
ELAPSED=0
READY=false
while [ $ELAPSED -lt $TIMEOUT ]; do
  STATUS=$(curl -sf "http://localhost:9200/_cluster/health" 2>/dev/null | \
    python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('status',''))" 2>/dev/null || echo "")
  if [ "$STATUS" = "green" ] || [ "$STATUS" = "yellow" ]; then
    READY=true
    break
  fi
  sleep 5
  ELAPSED=$((ELAPSED + 5))
  echo -n "."
done
echo ""

if $READY; then
  ok "OpenSearch healthy (status: ${STATUS})"
else
  fail "OpenSearch did not become healthy within ${TIMEOUT}s"
  echo "  Check: docker compose logs opensearch"
  exit 1
fi

# ─── Wait for OpenDashboards ─────────────────────────────────────────────────
echo -e "\n${BOLD}[5/6] Waiting for OpenDashboards (SIEM UI)${NC}"
info "Polling http://localhost:5601 (30s timeout)..."
TIMEOUT=30
ELAPSED=0
READY=false
while [ $ELAPSED -lt $TIMEOUT ]; do
  if curl -sf "http://localhost:5601/api/status" > /dev/null 2>&1; then
    READY=true
    break
  fi
  sleep 5
  ELAPSED=$((ELAPSED + 5))
  echo -n "."
done
echo ""

if $READY; then
  ok "OpenDashboards healthy at http://localhost:5601"
else
  warn "OpenDashboards not yet responding — it may still be starting. Continue anyway."
fi

# ─── Run OpenSearch Bootstrap ────────────────────────────────────────────────
echo -e "\n${BOLD}[6/6] Configuring SIEM (index templates, monitors, dashboards)${NC}"
if python3 "${PROJECT_DIR}/siem/bootstrap_opensearch.py"; then
  ok "SIEM bootstrap complete"
else
  warn "SIEM bootstrap returned errors — check output above. Some features may be limited."
fi

# ─── Final Health Check ──────────────────────────────────────────────────────
echo ""
bash "${SCRIPT_DIR}/health_check.sh"

echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  ${GREEN}${BOLD}Environment ready.${NC} Open ${BOLD}http://localhost:3000${NC} to begin."
echo ""
