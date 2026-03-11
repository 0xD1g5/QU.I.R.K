#!/usr/bin/env bash
# check_ollama_from_container.sh — Verify Ollama is reachable from inside Docker
# Runs a temporary container and checks host.docker.internal:11434

set -euo pipefail

MODEL="${1:-llama3.2:3b}"
OLLAMA_CONTAINER_URL="http://host.docker.internal:11434"

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

pass() { echo -e "${GREEN}  [PASS]${NC} $1"; }
fail() { echo -e "${RED}  [FAIL]${NC} $1"; }

echo ""
echo "─── Ollama Container Reachability Check ─────────────────"

# Run check inside a temporary alpine container
RESULT=$(docker run --rm \
  --add-host=host.docker.internal:host-gateway \
  alpine/curl:latest \
  sh -c "curl -sf ${OLLAMA_CONTAINER_URL}/api/tags && echo OK" 2>/dev/null || echo "FAIL")

if echo "$RESULT" | grep -q "OK"; then
  pass "Ollama reachable from container at ${OLLAMA_CONTAINER_URL}"
else
  fail "Ollama NOT reachable from container at ${OLLAMA_CONTAINER_URL}"
  echo ""
  echo "  Remediation:"
  echo "    - Ensure Ollama is running on host (ollama serve)"
  echo "    - On Linux: docker compose services need 'extra_hosts: [host.docker.internal:host-gateway]'"
  echo "    - On Windows/Mac Docker Desktop: host.docker.internal resolves automatically"
  exit 1
fi

# Check model reachable from container
MODEL_CHECK=$(docker run --rm \
  --add-host=host.docker.internal:host-gateway \
  alpine/curl:latest \
  sh -c "curl -sf ${OLLAMA_CONTAINER_URL}/api/tags" 2>/dev/null || echo "{}")

if echo "$MODEL_CHECK" | grep -q "${MODEL%%:*}"; then
  pass "Model '${MODEL}' visible from container"
else
  fail "Model '${MODEL}' not visible from container"
  exit 1
fi

echo "─────────────────────────────────────────────────────────"
echo ""
