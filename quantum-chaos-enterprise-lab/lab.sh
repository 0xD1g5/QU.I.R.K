#!/usr/bin/env bash
set -euo pipefail

if [[ -f ".env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source ".env"
  set +a
fi

# ---- Config ----
PROJECT_NAME="${PROJECT_NAME:-chaoslab}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"
PROFILE_ARGS="${PROFILE_ARGS:-}"   # e.g. "--profile identity" or "--profile core --profile identity"

# ---- Helpers ----
usage() {
  cat <<EOF
Usage: ./lab.sh <command> [options]

Commands:
  up              Start the lab (docker compose up -d)
  all             Start ALL profiles at once — every service, every vulnerability
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
  ./lab.sh status
  ./lab.sh logs tls-modern
  ./lab.sh reset
EOF
}

compose() {
  # Use a fixed project name to prevent name collisions across lab variants
  docker compose -p "${PROJECT_NAME}" -f "${COMPOSE_FILE}" ${PROFILE_ARGS} "$@"
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
    ALL_PROFILES="--profile phaseA --profile cloud --profile identity --profile pki \
      --profile jwt --profile registry --profile source --profile storage \
      --profile ssh-weak --profile ldaps --profile dnssec --profile saml \
      --profile kerberos"
    echo "🔥 Starting ALL profiles: project=${PROJECT_NAME} file=${COMPOSE_FILE}"
    echo "   Profiles: phaseA cloud identity pki jwt registry source storage ssh-weak ldaps dnssec saml kerberos"
    PROFILE_ARGS="${ALL_PROFILES}" compose up -d
    echo "✅ Full chaos lab started."
    compose ps
    ;;
  down)
    echo "🧯 Stopping lab: project=${PROJECT_NAME}"
    compose down
    echo "✅ Lab stopped."
    ;;
  reset)
    echo "♻️ Resetting lab (down -v + up -d): project=${PROJECT_NAME}"
    compose down -v
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