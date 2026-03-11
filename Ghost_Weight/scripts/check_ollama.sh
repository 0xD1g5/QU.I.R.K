#!/usr/bin/env bash
# check_ollama.sh — Verify Ollama is running on host with required model
# Usage: ./scripts/check_ollama.sh [model_name]
# Default model: llama3.2:3b

set -euo pipefail

MODEL="${1:-llama3.2:3b}"
OLLAMA_URL="http://localhost:11434"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass() { echo -e "${GREEN}  [PASS]${NC} $1"; }
fail() { echo -e "${RED}  [FAIL]${NC} $1"; }
warn() { echo -e "${YELLOW}  [WARN]${NC} $1"; }

echo ""
echo "─── Ollama Host Check ──────────────────────────────────"

# Check Ollama API reachable
if curl -sf "${OLLAMA_URL}/api/tags" > /tmp/ollama_tags.json 2>/dev/null; then
  pass "Ollama API reachable at ${OLLAMA_URL}"
else
  fail "Ollama API not reachable at ${OLLAMA_URL}"
  echo ""
  echo "  Remediation:"
  echo "    macOS:   brew install ollama && ollama serve"
  echo "    Windows: winget install Ollama.Ollama  (then restart and run 'ollama serve')"
  exit 1
fi

# Check model is available
if grep -q "\"name\":\"${MODEL}\"" /tmp/ollama_tags.json 2>/dev/null || \
   python3 -c "import json,sys; tags=json.load(open('/tmp/ollama_tags.json')); print(any(m['name'].startswith('${MODEL}'.split(':')[0]) for m in tags.get('models',[])))" 2>/dev/null | grep -q "True"; then
  pass "Model '${MODEL}' is available"
else
  fail "Model '${MODEL}' not found"
  echo ""
  echo "  Available models:"
  python3 -c "import json; [print('    -', m['name']) for m in json.load(open('/tmp/ollama_tags.json')).get('models',[])]" 2>/dev/null || true
  echo ""
  echo "  Remediation: ollama pull ${MODEL}"
  exit 1
fi

# Check response latency
START=$(date +%s%N)
curl -sf -X POST "${OLLAMA_URL}/api/generate" \
  -H "Content-Type: application/json" \
  -d "{\"model\":\"${MODEL}\",\"prompt\":\"ping\",\"stream\":false,\"options\":{\"num_predict\":1}}" \
  > /dev/null 2>&1
END=$(date +%s%N)
LATENCY=$(( (END - START) / 1000000 ))

if [ "$LATENCY" -lt 10000 ]; then
  pass "Model inference responsive (${LATENCY}ms for single token)"
else
  warn "Model inference slow (${LATENCY}ms) — may impact Phase 6 live demo. Consider pre-warming."
fi

rm -f /tmp/ollama_tags.json
echo "─────────────────────────────────────────────────────────"
echo ""
