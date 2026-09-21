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
  up [flags]      Start the lab (docker compose up -d). Extra flags are passed
                  straight to compose — notably --build, which rebuilds the
                  locally-built prober. Every other service is a pinned public
                  image, so --build only affects the prober in practice.
                  Without it, up reuses an existing prober image no matter how
                  far quirk/ has moved; a warning fires when that image
                  predates the newest commit touching quirk/.
  all             Start ALL profiles at once — every service, every vulnerability
  profiles        Print all known docker-compose profiles (one per line)
  certs           Generate all chaos-lab self-signed certs (mTLS CA/client +
                  labs/email + labs/grpc-tls) without starting containers
  down            Stop the lab (docker compose down)
  reset           Down + remove volumes + start fresh (down -v + up -d)
  status          Show running containers/ports for this lab project
  logs [service]  Tail logs (all services or one service)
  clean           Remove stopped containers with this project name + prune dangling items
  distributed     Manage the distributed multi-segment topology (separate compose file)
                  Subcommands: up, down, status, logs [service], e2e
                  Examples:
                    ./lab.sh distributed up
                    ./lab.sh distributed e2e
                    ./lab.sh distributed down

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
  PROFILE_ARGS="--profile multihost" ./lab.sh up --build   # rebuild the prober
  ./lab.sh certs
  ./lab.sh profiles
  ./lab.sh status
  ./lab.sh logs tls-modern
  ./lab.sh reset
  ./lab.sh distributed up
  ./lab.sh distributed e2e
EOF
}

compose() {
  # Use a fixed project name to prevent name collisions across lab variants
  docker compose -p "${PROJECT_NAME}" -f "${COMPOSE_FILE}" ${PROFILE_ARGS} "$@"
}

# Idempotently materialize the chaos-lab root CA (ca.key/ca.crt) and the mTLS
# client cert (client.key/client.crt). These two PEM keys are NOT committed to
# the repo (Phase 120-02, PUBREPO-LAB-KEYS). On first `up`/`all` invocation
# they're generated as self-signed fixtures — equivalent to the prior committed
# pair. The other lab certs (modern/legacy/expired/selfsigned/mtls/keycloak/
# scenarios/*) remain tracked because the 2026-05-27 posture review flagged
# only ca.key + client.key as the go-public blocker; those scenario keys carry
# no real-world trust path and are intentional chaos fixtures (weak RSA,
# expired validity, SHA-1, etc.).
#
# Idempotent: if both .key files exist, return 0 with no output.
# Re-entrant: callable from `up` and `all` without side effects on second run.
ensure_lab_certs() {
  local CERT_DIR
  CERT_DIR="$(dirname "$0")/certs"
  mkdir -p "${CERT_DIR}"

  # CA pair (root of trust for the lab's mTLS scenarios)
  if [[ ! -f "${CERT_DIR}/ca.key" || ! -f "${CERT_DIR}/ca.crt" ]]; then
    echo "🔐 Generating chaos-lab root CA (ca.key + ca.crt) — first-run regen"
    openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:4096 \
      -out "${CERT_DIR}/ca.key" >/dev/null 2>&1
    chmod 600 "${CERT_DIR}/ca.key"
    openssl req -x509 -new -key "${CERT_DIR}/ca.key" -sha256 -days 3650 \
      -subj "/CN=QUIRK Chaos Lab Root CA" \
      -out "${CERT_DIR}/ca.crt" >/dev/null 2>&1
  fi

  # Client pair (mTLS test client; signed by the CA above)
  if [[ ! -f "${CERT_DIR}/client.key" || ! -f "${CERT_DIR}/client.crt" ]]; then
    echo "🔐 Generating chaos-lab mTLS client cert (client.key + client.crt) — first-run regen"
    openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 \
      -out "${CERT_DIR}/client.key" >/dev/null 2>&1
    chmod 600 "${CERT_DIR}/client.key"
    openssl req -new -key "${CERT_DIR}/client.key" \
      -subj "/CN=quirk-lab-client" \
      -out "${CERT_DIR}/client.csr" >/dev/null 2>&1
    openssl x509 -req -in "${CERT_DIR}/client.csr" \
      -CA "${CERT_DIR}/ca.crt" -CAkey "${CERT_DIR}/ca.key" -CAcreateserial \
      -days 825 -sha256 \
      -out "${CERT_DIR}/client.crt" >/dev/null 2>&1
    rm -f "${CERT_DIR}/client.csr"
  fi
}

# Idempotently materialize the per-profile self-signed certs consumed by the
# `email` and `grpc-tls` chaos-lab profiles: labs/email/certs/{postfix,
# dovecot}.{key,crt} and labs/grpc-tls/certs/grpc-tls.{key,crt}. Both
# labs/*/.gitignore exclude certs/*.key and certs/*.crt, and the
# `postfix-email`, `dovecot-email` and `grpc-tls` docker-compose services
# bind-mount these paths read-only. On a fresh clone with no generator,
# Docker turns a missing bind-mount source into an empty directory and then
# fails to mount that directory onto the container's file destination — the
# "not a directory" runc error this function exists to prevent (D-12/D-13).
#
# Idempotent: each pair is guarded by an existence check and left untouched
# if both files already exist. Re-entrant: callable from `up`, `all`,
# `reset` and the standalone `certs` command without side effects on
# subsequent runs. Docker-free: only shells out to `mkdir`/`openssl`/`chmod`.
ensure_profile_certs() {
  local LABS_ROOT
  LABS_ROOT="$(dirname "$0")/../labs"

  # labs/email/certs/postfix.{key,crt}
  local EMAIL_CERT_DIR="${LABS_ROOT}/email/certs"
  if [[ ! -f "${EMAIL_CERT_DIR}/postfix.key" || ! -f "${EMAIL_CERT_DIR}/postfix.crt" ]]; then
    echo "🔐 Generating labs/email/certs/postfix.{key,crt} — first-run regen"
    mkdir -p "${EMAIL_CERT_DIR}"
    openssl req -x509 -newkey rsa:2048 -keyout "${EMAIL_CERT_DIR}/postfix.key" \
      -out "${EMAIL_CERT_DIR}/postfix.crt" -days 3650 -nodes \
      -subj "/CN=postfix.chaos.local" >/dev/null 2>&1
    chmod 644 "${EMAIL_CERT_DIR}/postfix.crt"
    chmod 600 "${EMAIL_CERT_DIR}/postfix.key"
  fi

  # labs/email/certs/dovecot.{key,crt}
  if [[ ! -f "${EMAIL_CERT_DIR}/dovecot.key" || ! -f "${EMAIL_CERT_DIR}/dovecot.crt" ]]; then
    echo "🔐 Generating labs/email/certs/dovecot.{key,crt} — first-run regen"
    mkdir -p "${EMAIL_CERT_DIR}"
    openssl req -x509 -newkey rsa:2048 -keyout "${EMAIL_CERT_DIR}/dovecot.key" \
      -out "${EMAIL_CERT_DIR}/dovecot.crt" -days 3650 -nodes \
      -subj "/CN=dovecot.chaos.local" >/dev/null 2>&1
    chmod 644 "${EMAIL_CERT_DIR}/dovecot.crt"
    chmod 600 "${EMAIL_CERT_DIR}/dovecot.key"
  fi

  # labs/grpc-tls/certs/grpc-tls.{key,crt}
  local GRPC_TLS_CERT_DIR="${LABS_ROOT}/grpc-tls/certs"
  if [[ ! -f "${GRPC_TLS_CERT_DIR}/grpc-tls.key" || ! -f "${GRPC_TLS_CERT_DIR}/grpc-tls.crt" ]]; then
    echo "🔐 Generating labs/grpc-tls/certs/grpc-tls.{key,crt} — first-run regen"
    mkdir -p "${GRPC_TLS_CERT_DIR}"
    openssl req -x509 -newkey rsa:2048 -keyout "${GRPC_TLS_CERT_DIR}/grpc-tls.key" \
      -out "${GRPC_TLS_CERT_DIR}/grpc-tls.crt" -days 3650 -nodes \
      -subj "/CN=grpc-tls.chaos.local" >/dev/null 2>&1
    chmod 644 "${GRPC_TLS_CERT_DIR}/grpc-tls.crt"
    chmod 640 "${GRPC_TLS_CERT_DIR}/grpc-tls.key"
  fi
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

# CHAOS-05 image-pin policy gate. Parses the compose file (pure parse, no
# daemon required) and fails if any service.image uses `:latest` or a bare
# untagged reference. Build-only services (no `image:` key) are skipped —
# pinning for them is enforced via the FROM directive in their Dockerfile.
# Returns 0 on clean compose file, 1 on policy violation.
_validate_pinned_tags() {
  if ! command -v python3 >/dev/null 2>&1; then
    echo "⚠️  python3 not found; skipping pin-policy gate (CHAOS-05)" >&2
    return 0
  fi
  local violations
  violations="$(python3 - "${COMPOSE_FILE}" <<'PY'
import sys
try:
    import yaml
except ImportError:
    # PyYAML unavailable — defer to pytest gate (tests/test_chaos_lab_image_pinning.py).
    sys.exit(0)
data = yaml.safe_load(open(sys.argv[1]).read()) or {}
bad = []
for name, svc in (data.get("services") or {}).items():
    if not isinstance(svc, dict):
        continue
    img = svc.get("image")
    if img is None:
        continue
    if img.endswith(":latest") or ":" not in img:
        bad.append(f"{name}: {img}")
print("\n".join(bad))
PY
)"
  if [[ -n "${violations}" ]]; then
    echo "❌ CHAOS-05 violation — chaos-lab images must be pinned (no :latest, no bare names):" >&2
    echo "${violations}" | sed 's/^/    /' >&2
    return 1
  fi
  return 0
}

# --- Stale locally-built image detection -------------------------------------
#
# `up` runs `compose up -d`, which reuses any existing image regardless of how
# far the repo has moved. Every service in this lab is a pinned public image
# EXCEPT the prober, which is built from this checkout -- so the prober is the
# only one that can silently run stale code.
#
# That is not hypothetical: on 2026-09-14 a multihost scan reported a confident
# 91/100 from a prober built before the v3 scoring change. The same evidence
# scores 15/100 under v3. Exit 0, eleven artifacts, no warning of any kind.
#
# This warns; it does not rebuild. A blanket rebuild would cost a 1.4 GB build
# context on every `up` even on a cache hit. Pass `--build` (now forwarded to
# compose) when the warning fires, or rebuild just the prober:
#   docker compose -p chaoslab --profile multihost build mh-prober
_warn_if_prober_stale() {
  case "${PROFILE_ARGS}" in *multihost*) ;; *) return 0 ;; esac
  command -v docker >/dev/null 2>&1 || return 0
  command -v git >/dev/null 2>&1 || return 0
  command -v python3 >/dev/null 2>&1 || return 0

  local image created commit_ts
  image="${PROJECT_NAME}-mh-prober"
  created="$(docker image inspect -f '{{.Created}}' "${image}" 2>/dev/null)" || return 0
  [ -n "${created}" ] || return 0

  # Newest commit touching scanner code. If the working tree is dirty this is
  # still a lower bound -- uncommitted changes are strictly newer.
  # Derived from BASH_SOURCE, not from `..` of the CWD: the rest of this script
  # assumes it is run from the lab directory, but a warning that silently stops
  # working when it is not would be worse than no warning.
  local repo_root
  repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)" || return 0
  commit_ts="$(git -C "${repo_root}" log -1 --format=%ct -- quirk/ 2>/dev/null)" || return 0
  [ -n "${commit_ts}" ] || return 0

  # Date math in python3 rather than `date`: the -j/-f vs -d split between
  # macOS and GNU makes portable epoch conversion in shell genuinely awkward,
  # and docker reports nanosecond-precision RFC3339 that BSD date rejects.
  if python3 -c "
import sys, datetime
raw = sys.argv[1].strip().replace('Z', '+00:00')
head, sep, rest = raw.partition('.')
if sep:  # trim sub-second precision to 6 digits for fromisoformat
    frac = rest[:6].ljust(6, '0')
    tz = rest.lstrip('0123456789')
    raw = f'{head}.{frac}{tz}'
built = datetime.datetime.fromisoformat(raw).timestamp()
sys.exit(0 if built < float(sys.argv[2]) else 1)
" "${created}" "${commit_ts}" 2>/dev/null; then
    echo "⚠️  Image '${image}' was built BEFORE the newest commit touching quirk/." >&2
    echo "    It will scan with stale scanner code and report a score from whatever" >&2
    echo "    model was current when it was built -- silently, exit 0, no warning in" >&2
    echo "    the scan itself. Check the 'Scoring model' / 'Scanner build' rows in the" >&2
    echo "    scan summary, and rebuild with:" >&2
    echo "      PROFILE_ARGS=\"${PROFILE_ARGS}\" ./lab.sh up --build" >&2
  fi
}

cmd="${1:-}"
shift || true

case "${cmd}" in
  up)
    if ! _validate_pinned_tags; then
      echo "❌ Refusing to start: pin policy violation (CHAOS-05)." >&2
      exit 1
    fi
    ensure_lab_certs
    ensure_profile_certs
    # Warn BEFORE starting, so the operator can re-run with --build rather than
    # discover it after a scan has already produced a plausible wrong number.
    # Skipped when --build was passed, since that rebuild resolves it.
    case " $* " in *" --build "*) ;; *) _warn_if_prober_stale ;; esac
    echo "🚀 Starting lab: project=${PROJECT_NAME} file=${COMPOSE_FILE} profiles='${PROFILE_ARGS}'"
    # "$@" forwards compose flags -- notably `--build`, which `up` previously
    # had no way to reach, making a stale locally-built prober unavoidable
    # without dropping to raw `docker compose`.
    compose up -d "$@"
    echo "✅ Lab started."
    compose ps
    ;;
  all)
    if ! _validate_pinned_tags; then
      echo "❌ Refusing to start: pin policy violation (CHAOS-05)." >&2
      exit 1
    fi
    ensure_lab_certs
    ensure_profile_certs
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
    #
    # NOTE (2026-09-17): this skip applies to the standalone `kerberos` profile only,
    # because that profile PUBLISHES 88:88. The `multihost` profile's mh-kdc runs the
    # same image with no published ports, so it is unaffected by the collision and is
    # NOT filtered here — multihost Kerberos works on macOS. Three provisioning bugs
    # were fixed in samba/ to make either profile start at all (packaged smb.conf role
    # mismatch, missing samba-ad-provision, and overlayfs NT-ACL xattr); before that
    # the kerberos profile could not provision on any platform.
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
    # `all` includes the multihost profile, so it starts the locally-built
    # prober and carries the same stale-image hazard as `up`. Same treatment.
    case " $* " in *" --build "*) ;; *) _warn_if_prober_stale ;; esac
    compose up -d "$@"
    echo "✅ Full chaos lab started."
    compose ps
    ;;
  profiles)
    _derive_all_profiles
    ;;
  certs)
    ensure_lab_certs
    ensure_profile_certs
    echo "✅ Chaos-lab certs materialized (mTLS CA/client + email + grpc-tls)."
    ;;
  down)
    echo "🧯 Stopping lab: project=${PROJECT_NAME}"
    compose --profile "*" down --remove-orphans
    echo "✅ Lab stopped."
    ;;
  reset)
    echo "♻️ Resetting lab (down -v + up -d): project=${PROJECT_NAME}"
    compose --profile "*" down -v --remove-orphans
    ensure_lab_certs
    ensure_profile_certs
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
  distributed)
    # Distributed multi-segment topology — separate compose file + project name.
    # COMPOSE_FILE and PROJECT_NAME are reassigned here so the compose() helper
    # and _validate_pinned_tags both pick up the distributed file.
    # These reassignments are scoped to this arm only; they do NOT affect
    # the main up/all/ALL_PROFILES paths (LAB-03 no-drift guarantee).
    COMPOSE_FILE="$(dirname "$0")/docker-compose.distributed.yml"
    PROJECT_NAME="quirk-dist"
    PROFILE_ARGS=""  # no --profile flags for distributed topology
    subcmd="${1:-up}"
    shift || true
    case "${subcmd}" in
      up)
        if ! _validate_pinned_tags; then
          echo "❌ Refusing to start: pin policy violation (CHAOS-05)." >&2
          exit 1
        fi
        echo "🚀 Starting distributed lab: project=${PROJECT_NAME} file=${COMPOSE_FILE}"
        compose up -d "$@"
        echo "✅ Distributed lab started."
        compose ps
        ;;
      down)
        echo "🧯 Stopping distributed lab: project=${PROJECT_NAME}"
        compose down --remove-orphans "$@"
        echo "✅ Distributed lab stopped."
        ;;
      status)
        echo "📦 Distributed lab status: project=${PROJECT_NAME}"
        compose ps
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
      e2e)
        echo "🧪 Running distributed E2E: enroll → push → merge"
        bash "$(dirname "$0")/scripts/distributed-e2e.sh" "$@"
        ;;
      *)
        echo "❌ Unknown distributed subcommand: ${subcmd}"
        echo "  Valid subcommands: up, down, status, logs [service], e2e"
        exit 1
        ;;
    esac
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