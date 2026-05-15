#!/usr/bin/env bash
set -euo pipefail

_PROFILE_ARGS_OVERRIDE="${PROFILE_ARGS:-}"   # snapshot CLI value BEFORE .env can overwrite it (Phase 52 DEBT-02)

if [[ -f ".env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source ".env"
  set +a
fi

# ---- Config ----
PROJECT_NAME="${PROJECT_NAME:-chaoslab}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"
PROFILE_ARGS="${_PROFILE_ARGS_OVERRIDE:-${PROFILE_ARGS:-}}"   # CLI wins over .env (Phase 52 DEBT-02)

# ---- Helpers ----
usage() {
  cat <<EOF
Usage: ./lab.sh <command> [options]

Commands:
  up              Start the lab (docker compose up -d)
  all             Start ALL profiles at once — every service, every vulnerability
  profiles        Print all known docker-compose profiles (one per line)
  down            Stop the lab (docker compose down)
  reset           Down + remove volumes + start fresh (down -v + up -d)
  status          Show running containers/ports for this lab project
  logs [service]  Tail logs (all services or one service)
  clean           Remove stopped containers with this project name + prune dangling items

Options (via env vars):
  PROJECT_NAME    Compose project name (default: chaoslab)
  COMPOSE_FILE    Compose file path (default: docker-compose.yml)
  PROFILE_ARGS    Profile flags (default: empty)
                  Examples:
                    PROFILE_ARGS="--profile identity"
                    PROFILE_ARGS="--profile core --profile identity"

Examples:
  ./lab.sh up
  PROFILE_ARGS="--profile identity" ./lab.sh up
  ./lab.sh profiles
  ./lab.sh status
  ./lab.sh logs tls-modern
  ./lab.sh reset
EOF
}

compose() {
  # Use a fixed project name to prevent name collisions across lab variants
  docker compose -p "${PROJECT_NAME}" -f "${COMPOSE_FILE}" ${PROFILE_ARGS} "$@"
}

# Derive ALL profiles from docker-compose.yml. Output: alphabetized, deduped, one per line.
# Preserves set -euo pipefail (no unbound vars; pipefail-safe — sort handles empty input).
_derive_all_profiles() {
  if command -v yq >/dev/null 2>&1; then
    yq eval '.. | select(has("profiles")) | .profiles[]' "${COMPOSE_FILE}" 2>/dev/null \
      | sort -u
  else
    # Fallback: handles inline-array form (the only form in docker-compose.yml today).
    # Restricted character class [a-zA-Z0-9_-] mitigates shell-injection risk on parsed names.
    grep -E '^[[:space:]]*profiles:[[:space:]]*\[' "${COMPOSE_FILE}" \
      | grep -oE '"[a-zA-Z0-9_-]+"' \
      | tr -d '"' \
      | sort -u
  fi
}

cmd="${1:-}"
shift || true

case "${cmd}" in
  up)
    echo "🚀 Starting lab: project=${PROJECT_NAME} file=${COMPOSE_FILE} profiles='${PROFILE_ARGS}'"
    compose up -d
    echo "✅ Lab started."
    compose ps
    ;;
  all)
    # Portable across bash 3.2 (macOS default) — `mapfile` is bash 4+.
    _profiles=()
    while IFS= read -r _p; do
      [[ -n "${_p}" ]] && _profiles+=("${_p}")
    done < <(_derive_all_profiles)
    if [[ ${#_profiles[@]} -eq 0 ]]; then
      echo "❌ Could not derive profiles from ${COMPOSE_FILE}" >&2
      exit 1
    fi
    # macOS ships its own KDC bound to *:88 — the `kerberos` profile collides.
    # Skip it on Darwin unless the user explicitly opts in. See BACK-89 for the
    # full remap that makes this unconditional.
    _skipped=""
    if [[ "$(uname -s)" == "Darwin" && "${LAB_INCLUDE_KERBEROS:-0}" != "1" ]]; then
      _filtered=()
      for p in "${_profiles[@]}"; do
        if [[ "$p" == "kerberos" ]]; then
          _skipped="kerberos"
        else
          _filtered+=("$p")
        fi
      done
      _profiles=("${_filtered[@]}")
    fi
    ALL_PROFILES=""
    for p in "${_profiles[@]}"; do ALL_PROFILES+=" --profile $p"; done
    # Assign explicitly so the .env-sourced PROFILE_ARGS can't shadow this.
    PROFILE_ARGS="${ALL_PROFILES}"
    echo "🔥 Starting ALL profiles: project=${PROJECT_NAME} file=${COMPOSE_FILE}"
    echo "   Profiles: ${_profiles[*]}"
    if [[ -n "${_skipped}" ]]; then
      echo "   ⏭  Skipped on macOS: ${_skipped} (set LAB_INCLUDE_KERBEROS=1 to include; see BACK-89)"
    fi
    compose up -d
    echo "✅ Full chaos lab started."
    compose ps
    ;;
  profiles)
    _derive_all_profiles
    ;;
  down)
    echo "🧯 Stopping lab: project=${PROJECT_NAME}"
    compose --profile "*" down --remove-orphans
    echo "✅ Lab stopped."
    ;;
  reset)
    echo "♻️ Resetting lab (down -v + up -d): project=${PROJECT_NAME}"
    compose --profile "*" down -v --remove-orphans
    compose up -d
    echo "✅ Lab reset complete."
    compose ps
    ;;
  status)
    echo "📦 Lab status: project=${PROJECT_NAME}"
    compose ps
    echo ""
    echo "🔌 Published ports:"
    docker ps --filter "label=com.docker.compose.project=${PROJECT_NAME}" \
      --format "table {{.Names}}\t{{.Ports}}\t{{.Status}}"
    ;;
  logs)
    svc="${1:-}"
    if [[ -n "${svc}" ]]; then
      echo "📜 Tailing logs for service: ${svc} (project=${PROJECT_NAME})"
      compose logs -f --tail=200 "${svc}"
    else
      echo "📜 Tailing logs for all services (project=${PROJECT_NAME})"
      compose logs -f --tail=200
    fi
    ;;
  clean)
    echo "🧹 Cleaning up stopped containers for project=${PROJECT_NAME}"
    # Remove stopped containers belonging to this compose project
    docker ps -a --filter "label=com.docker.compose.project=${PROJECT_NAME}" --filter "status=exited" -q | xargs -r docker rm
    echo "🧽 Pruning dangling images/networks (safe):"
    docker system prune -f
    echo "✅ Clean complete."
    ;;
  ""|-h|--help|help)
    usage
    ;;
  *)
    echo "❌ Unknown command: ${cmd}"
    usage
    exit 1
    ;;
esac