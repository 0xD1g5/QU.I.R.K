#!/usr/bin/env bash
# Clean-environment release smoke: run the README as a stranger would, then
# prove observable outcomes, not exit codes. One invocation = one leg.
#
#   scripts/release_smoke.sh --leg LEG --source SRC --out DIR [options]
#
#   --leg LEG       linux-3.11 | linux-3.10 | linux-3.15-neg | macos | contributor
#   --source SRC    wheel:/abs/path/quirk_scanner-X-py3-none-any.whl
#                   pypi:X.Y.Z
#                   git:REF                (contributor leg only)
#   --out DIR       transcript directory. Must not be inside the checkout or
#                   under /tmp, and must live on /Volumes/Digs-1TB unless
#                   --allow-out-anywhere is given.
#   --targets H:P,H:P   chaos-lab endpoints. Default: derived at run time from
#                   quantum-chaos-enterprise-lab/scan-configs/config-lab-core.yaml
#                   (host.docker.internal on Linux legs, 127.0.0.1 otherwise).
#   --divergence-set PATH  optional JSON {"patterns":[{"match","phrase"}]}
#                   carrying the todo-derived half of the score divergence set.
#   --python PATH   macOS / contributor interpreter (default /opt/homebrew/bin/python3.14)
#   --allow-out-anywhere   waive the /Volumes/Digs-1TB requirement for --out
#   --self-check    run the helper self-tests; no docker, no network; exit 0
#
# Linux legs run in a throwaway python:3.X-slim container with no repo mount.
# The macOS and contributor legs run under `env -i` with a private HOME and a
# PATH of /usr/bin:/bin:/usr/sbin:/sbin plus one symlinked interpreter, so
# Homebrew's nmap/syft/semgrep are NOT visible.
#
# The last line of the transcript is exactly `RESULT: PASS` or `RESULT: FAIL`.
# Exit status follows it. No `set -e`: every failure must be recorded.
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT_DIR="${REPO_ROOT}/scripts"
LAB_CFG="${REPO_ROOT}/quantum-chaos-enterprise-lab/scan-configs/config-lab-core.yaml"
README_FILE="${REPO_ROOT}/README.md"
VOLUME_ROOT="/Volumes/Digs-1TB"
REPO_URL="https://github.com/0xD1g5/QU.I.R.K"
D07_LIMITATION="LIMITATION (D-07): this leg cannot detect dependence on system-wide state such as Homebrew openssl or an existing Playwright Chromium cache at ~/Library/Caches/ms-playwright. A throwaway HOME forces a fresh Chromium download."

LEG=""; SOURCE=""; OUT=""; TARGETS=""; DIVERGENCE_SET=""
MAC_PYTHON="/opt/homebrew/bin/python3.14"
ALLOW_ANYWHERE=0; SELF_CHECK=0

# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
abspath() { ( cd "$(dirname "$1")" 2>/dev/null && printf '%s/%s\n' "$(pwd -P)" "$(basename "$1")" ); }

# out_dir_ok PATH ALLOW  -> prints a reason and returns 1 when refused
out_dir_ok() {
  local p="$1" allow="$2" parent
  mkdir -p "$(dirname "${p}")" 2>/dev/null
  parent="$(abspath "${p}")"
  [ -z "${parent}" ] && { echo "cannot resolve ${p}"; return 1; }
  case "${parent}" in
    "${REPO_ROOT}"|"${REPO_ROOT}"/*) echo "refusing --out inside the repository checkout"; return 1 ;;
    /tmp|/tmp/*|/private/tmp|/private/tmp/*|/var/folders/*|/private/var/folders/*)
      echo "refusing --out under the boot-disk /tmp"; return 1 ;;
  esac
  if [ "${allow}" -eq 0 ]; then
    case "${parent}" in
      "${VOLUME_ROOT}"/*) ;;
      *) echo "--out must live on ${VOLUME_ROOT} (or pass --allow-out-anywhere)"; return 1 ;;
    esac
  fi
  return 0
}

# derive_default_targets LEG -> HOST:PORT,... from the lab's scan config
derive_default_targets() {
  local host="127.0.0.1"
  case "$1" in linux-*) host="host.docker.internal" ;; esac
  python3 - "${LAB_CFG}" "${host}" <<'PY'
import re, sys
text = open(sys.argv[1], encoding="utf-8").read()
ports = re.search(r"ports_tls:\s*\[([^\]]*)\]", text)
if not ports:
    sys.exit(1)
plist = [p.strip() for p in ports.group(1).split(",") if p.strip()]
print(",".join("%s:%s" % (sys.argv[2], p) for p in plist))
PY
}

leg_images() {
  case "$1" in
    linux-3.11) echo "python:3.11-slim" ;;
    linux-3.10) echo "python:3.10-slim" ;;
    linux-3.15-neg) echo "python:3.15-slim python:3.15-rc-slim python:3.15-rc" ;;
  esac
}

valid_leg() {
  case "$1" in linux-3.11|linux-3.10|linux-3.15-neg|macos|contributor) return 0 ;; *) return 1 ;; esac
}

sha256_of() { shasum -a 256 "$1" 2>/dev/null | cut -d' ' -f1; }

# --------------------------------------------------------------------------
# Arguments
# --------------------------------------------------------------------------
while [ $# -gt 0 ]; do
  case "$1" in
    --leg) LEG="${2:-}"; shift ;;
    --source) SOURCE="${2:-}"; shift ;;
    --out) OUT="${2:-}"; shift ;;
    --targets) TARGETS="${2:-}"; shift ;;
    --divergence-set) DIVERGENCE_SET="${2:-}"; shift ;;
    --python) MAC_PYTHON="${2:-}"; shift ;;
    --allow-out-anywhere) ALLOW_ANYWHERE=1 ;;
    --self-check) SELF_CHECK=1 ;;
    -h|--help) sed -n '2,32p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown option: $1 (try --help)" >&2; exit 2 ;;
  esac
  shift
done

# --------------------------------------------------------------------------
# Self-check
# --------------------------------------------------------------------------
if [ "${SELF_CHECK}" -eq 1 ]; then
  bad=0
  ok() { echo "  ok   $1"; }
  no() { echo "  FAIL $1"; bad=1; }
  bash -n "${SCRIPT_DIR}/release_smoke.sh" && ok "bash -n release_smoke.sh" || no "bash -n release_smoke.sh"
  bash -n "${SCRIPT_DIR}/release_smoke_inner.sh" && ok "bash -n release_smoke_inner.sh" || no "bash -n release_smoke_inner.sh"

  out_dir_ok "${REPO_ROOT}/x-out" 0 >/dev/null && no "out refused inside the repo" || ok "out refused inside the repo"
  out_dir_ok "/tmp/x-out" 1 >/dev/null && no "out refused under /tmp" || ok "out refused under /tmp"
  out_dir_ok "${HOME}/x-out-elsewhere" 0 >/dev/null && no "out refused off the volume" || ok "out refused off the volume"
  out_dir_ok "${VOLUME_ROOT}/tmp-235/selfcheck-out" 0 >/dev/null && ok "out accepted on the volume" || no "out accepted on the volume"

  t="$(derive_default_targets linux-3.11)"
  case "${t}" in host.docker.internal:443,*) ok "linux targets: ${t%%,*},... ($(echo "${t}" | tr ',' '\n' | wc -l | tr -d ' ') endpoints)" ;; *) no "linux targets: '${t}'" ;; esac
  t="$(derive_default_targets macos)"
  case "${t}" in 127.0.0.1:443,*) ok "macos targets start ${t%%,*}" ;; *) no "macos targets: '${t}'" ;; esac

  for l in linux-3.11 linux-3.10 linux-3.15-neg macos contributor; do
    valid_leg "${l}" && ok "leg ${l}" || no "leg ${l}"
  done
  valid_leg bogus && no "bogus leg rejected" || ok "bogus leg rejected"

  bash "${SCRIPT_DIR}/release_smoke_inner.sh" --self-check || bad=1
  python3 "${SCRIPT_DIR}/score_attribution.py" --self-test | tee /dev/stderr | grep -qx "self-test: 6/6" \
    && ok "score_attribution --self-test 6/6" || no "score_attribution --self-test"
  [ "${bad}" -eq 0 ] && { echo "release_smoke self-check: ok (this is NOT a smoke run)"; exit 0; }
  echo "release_smoke self-check: FAILED"; exit 1
fi

# --------------------------------------------------------------------------
# Validate the request
# --------------------------------------------------------------------------
die() { echo "release_smoke: $1" >&2; exit 2; }
valid_leg "${LEG}" || die "--leg must be one of linux-3.11 linux-3.10 linux-3.15-neg macos contributor"
[ -n "${SOURCE}" ] || die "--source is required"
[ -n "${OUT}" ] || die "--out is required"
reason="$(out_dir_ok "${OUT}" "${ALLOW_ANYWHERE}")" || die "${reason}"
mkdir -p "${OUT}" || die "cannot create ${OUT}"
OUT="$(cd "${OUT}" && pwd -P)"

SRC_KIND="${SOURCE%%:*}"; SRC_VALUE="${SOURCE#*:}"
case "${SRC_KIND}" in wheel|pypi|git) ;; *) die "--source must be wheel:PATH, pypi:VERSION or git:REF" ;; esac
if [ "${LEG}" = "contributor" ] && [ "${SRC_KIND}" != "git" ]; then die "the contributor leg takes --source git:REF"; fi
if [ "${LEG}" != "contributor" ] && [ "${SRC_KIND}" = "git" ]; then die "--source git:REF is for the contributor leg only"; fi
if [ "${SRC_KIND}" = "wheel" ]; then
  [ -f "${SRC_VALUE}" ] || die "wheel not found: ${SRC_VALUE}"
  SRC_VALUE="$(abspath "${SRC_VALUE}")"
fi
if [ -n "${DIVERGENCE_SET}" ]; then
  [ -f "${DIVERGENCE_SET}" ] || die "divergence set not found: ${DIVERGENCE_SET}"
  DIVERGENCE_SET="$(abspath "${DIVERGENCE_SET}")"
fi
[ -n "${TARGETS}" ] || TARGETS="$(derive_default_targets "${LEG}")" || die "could not derive targets from ${LAB_CFG}"

AUDIT_PY="python3"
[ -x "${REPO_ROOT}/.venv/bin/python" ] && AUDIT_PY="${REPO_ROOT}/.venv/bin/python"

# --------------------------------------------------------------------------
# Commands JSON (the only README-derived input that crosses the boundary)
# --------------------------------------------------------------------------
CMDS_JSON="${OUT}/readme-commands.json"
( cd "${REPO_ROOT}" && "${AUDIT_PY}" -m scripts.readme_audit commands --readme README.md ) >"${CMDS_JSON}" \
  || die "readme_audit commands failed"

case "${SRC_KIND}" in
  wheel) EXPECTED="$(basename "${SRC_VALUE}" | cut -d- -f2)" ;;
  pypi)  EXPECTED="${SRC_VALUE}" ;;
  git)   EXPECTED="" ;;
esac

START_UTC="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
HEADER="${OUT}/header.txt"
{
  echo "QUIRK release smoke transcript"
  echo "leg: ${LEG}"
  echo "start (UTC): ${START_UTC}"
  case "${SRC_KIND}" in
    wheel) echo "source: wheel ${SRC_VALUE}"; echo "wheel sha256: $(sha256_of "${SRC_VALUE}")" ;;
    pypi)  echo "source: PyPI quirk-scanner==${SRC_VALUE}" ;;
    git)   echo "source: git ref ${SRC_VALUE} of ${REPO_URL}" ;;
  esac
  echo "targets: ${TARGETS}"
  echo "divergence set: ${DIVERGENCE_SET:-none (code-derived keys only)}"
} >"${HEADER}"

INNER_OUT=""   # directory holding the inner transcript once the leg ran

run_env() {   # prints the Q_* variable assignments shared by both runtimes
  printf 'Q_LEG=%s Q_SOURCE_KIND=%s Q_EXPECTED_VERSION=%s Q_TARGETS=%s' \
    "${LEG}" "${SRC_KIND}" "${EXPECTED}" "${TARGETS}"
}

# --------------------------------------------------------------------------
# Linux legs: throwaway container, nothing mounted
# --------------------------------------------------------------------------
run_linux() {
  command -v docker >/dev/null 2>&1 || { echo "docker is not installed" >&2; return 2; }
  docker info >/dev/null 2>&1 || { echo "docker daemon is not running" >&2; return 2; }
  local image="" cand
  for cand in $(leg_images "${LEG}"); do
    if docker pull -q "${cand}" >/dev/null 2>&1; then image="${cand}"; break; fi
    echo "image ${cand} unavailable" >>"${HEADER}"
  done
  if [ -z "${image}" ]; then
    echo "no usable image for ${LEG}" >>"${HEADER}"; return 3
  fi
  local digest
  digest="$(docker image inspect --format '{{index .RepoDigests 0}}' "${image}" 2>/dev/null)"
  echo "image: ${image}" >>"${HEADER}"
  echo "image digest: ${digest:-unknown}" >>"${HEADER}"

  local cn="q235-${LEG}-$(date +%s)"
  docker run -d --rm --name "${cn}" --add-host host.docker.internal:host-gateway "${image}" sleep 7200 >/dev/null \
    || { echo "docker run failed" >&2; return 2; }
  trap 'docker rm -f "'"${cn}"'" >/dev/null 2>&1' EXIT

  docker exec "${cn}" mkdir -p /smoke/out
  docker cp "${SCRIPT_DIR}/release_smoke_inner.sh" "${cn}:/smoke/release_smoke_inner.sh"
  docker cp "${SCRIPT_DIR}/score_attribution.py" "${cn}:/smoke/score_attribution.py"
  docker cp "${CMDS_JSON}" "${cn}:/smoke/readme-commands.json"
  local srcval="${SRC_VALUE}" divarg=""
  if [ "${SRC_KIND}" = "wheel" ]; then
    docker cp "${SRC_VALUE}" "${cn}:/smoke/$(basename "${SRC_VALUE}")"
    srcval="/smoke/$(basename "${SRC_VALUE}")"
  fi
  if [ -n "${DIVERGENCE_SET}" ]; then
    docker cp "${DIVERGENCE_SET}" "${cn}:/smoke/divergence.json"; divarg="/smoke/divergence.json"
  fi
  docker exec \
    -e Q_LEG="${LEG}" -e Q_SOURCE_KIND="${SRC_KIND}" -e Q_SOURCE_VALUE="${srcval}" \
    -e Q_EXPECTED_VERSION="${EXPECTED}" -e Q_TARGETS="${TARGETS}" \
    -e Q_COMMANDS_JSON=/smoke/readme-commands.json -e Q_OUT=/smoke/out \
    -e Q_SCORE_ATTR=/smoke/score_attribution.py -e Q_DIVERGENCE_SET="${divarg}" \
    "${cn}" bash /smoke/release_smoke_inner.sh >"${OUT}/inner-stdout.txt" 2>&1
  local rc=$?
  mkdir -p "${OUT}/inner"
  docker cp "${cn}:/smoke/out/." "${OUT}/inner/" >/dev/null 2>&1
  docker rm -f "${cn}" >/dev/null 2>&1
  trap - EXIT
  INNER_OUT="${OUT}/inner"
  return "${rc}"
}

# --------------------------------------------------------------------------
# macOS and contributor legs: scrubbed environment on the host
# --------------------------------------------------------------------------
run_host() {
  [ -x "${MAC_PYTHON}" ] || { echo "interpreter not found: ${MAC_PYTHON}" >&2; return 2; }
  mkdir -p "${VOLUME_ROOT}/tmp-235/smoke" 2>/dev/null
  local base smoke
  base="${VOLUME_ROOT}/tmp-235/smoke"
  smoke="$(mktemp -d "${base}/${LEG}.XXXXXX")" || return 2
  mkdir -p "${smoke}/home" "${smoke}/tmp" "${smoke}/bin" "${smoke}/in" "${smoke}/out" "${smoke}/work"
  ln -s "${MAC_PYTHON}" "${smoke}/bin/python3"
  local pyver
  pyver="$("${MAC_PYTHON}" -c 'import sys;print("%d.%d.%d" % sys.version_info[:3])')"
  {
    echo "interpreter: ${MAC_PYTHON} ${pyver}"
    echo "environment: env -i, HOME=${smoke}/home, PATH=${smoke}/bin:/usr/bin:/bin:/usr/sbin:/sbin, cwd=${smoke}/work"
    echo "${D07_LIMITATION}"
  } >>"${HEADER}"

  cp "${SCRIPT_DIR}/release_smoke_inner.sh" "${smoke}/in/"
  cp "${SCRIPT_DIR}/score_attribution.py" "${smoke}/in/"
  cp "${CMDS_JSON}" "${smoke}/in/readme-commands.json"
  local srcval="${SRC_VALUE}" divarg="" startdir=""
  if [ "${SRC_KIND}" = "wheel" ]; then
    cp "${SRC_VALUE}" "${smoke}/in/"; srcval="${smoke}/in/$(basename "${SRC_VALUE}")"
  fi
  if [ -n "${DIVERGENCE_SET}" ]; then
    cp "${DIVERGENCE_SET}" "${smoke}/in/divergence.json"; divarg="${smoke}/in/divergence.json"
  fi
  local expected="${EXPECTED}"
  if [ "${LEG}" = "contributor" ]; then
    startdir="${smoke}/work"
    if ! git clone --depth 1 --branch "${SRC_VALUE}" "${REPO_URL}" "${startdir}/QU.I.R.K" >"${OUT}/clone.log" 2>&1; then
      echo "CLONE_HEAD: clone failed (see clone.log)" >>"${HEADER}"; return 3
    fi
    echo "CLONE_HEAD: $(git -C "${startdir}/QU.I.R.K" rev-parse HEAD)" >>"${HEADER}"
    expected="$(sed -n 's/^version = "\(.*\)"/\1/p' "${startdir}/QU.I.R.K/pyproject.toml" | head -1)"
    echo "expected version (from the clone's pyproject): ${expected}" >>"${HEADER}"
  fi

  ( cd "${smoke}/work" && env -i \
      HOME="${smoke}/home" TMPDIR="${smoke}/tmp" LANG=en_US.UTF-8 \
      PATH="${smoke}/bin:/usr/bin:/bin:/usr/sbin:/sbin" \
      Q_LEG="${LEG}" Q_SOURCE_KIND="${SRC_KIND}" Q_SOURCE_VALUE="${srcval}" \
      Q_EXPECTED_VERSION="${expected}" Q_TARGETS="${TARGETS}" \
      Q_COMMANDS_JSON="${smoke}/in/readme-commands.json" Q_OUT="${smoke}/out" \
      Q_SCORE_ATTR="${smoke}/in/score_attribution.py" Q_DIVERGENCE_SET="${divarg}" \
      Q_START_DIR="${startdir}" \
      /bin/bash "${smoke}/in/release_smoke_inner.sh" ) >"${OUT}/inner-stdout.txt" 2>&1
  local rc=$?
  mkdir -p "${OUT}/inner"
  cp -R "${smoke}/out/." "${OUT}/inner/" 2>/dev/null
  INNER_OUT="${OUT}/inner"
  return "${rc}"
}

# --------------------------------------------------------------------------
# Run, assemble the transcript, decide
# --------------------------------------------------------------------------
case "${LEG}" in
  linux-*) run_linux; RUN_RC=$? ;;
  *)       run_host;  RUN_RC=$? ;;
esac

TRANSCRIPT="${OUT}/transcript.txt"
{
  cat "${HEADER}"
  echo ""
  if [ -n "${INNER_OUT}" ] && [ -f "${INNER_OUT}/transcript.txt" ]; then
    cat "${INNER_OUT}/transcript.txt"
  else
    echo "(no inner transcript was produced; run rc ${RUN_RC})"
    [ -f "${OUT}/inner-stdout.txt" ] && sed 's/^/    | /' "${OUT}/inner-stdout.txt"
  fi
} >"${TRANSCRIPT}.body"

VERDICT="FAIL"
if [ -n "${INNER_OUT}" ] && grep -qx "RESULT: PASS" "${INNER_OUT}/transcript.txt" 2>/dev/null; then
  VERDICT="PASS"
fi

# The 3.15 negative leg is re-checked here, independently of the inner script:
# PASS only if pip failed AND said Requires-Python AND did not say ResolutionImpossible.
if [ "${LEG}" = "linux-3.15-neg" ]; then
  NEGF="${INNER_OUT}/pip-negative.txt"
  if [ -f "${NEGF}" ] \
     && grep -qE "Requires-Python|requires a different Python" "${NEGF}" \
     && ! grep -q "ResolutionImpossible" "${NEGF}"; then
    echo "driver re-check: pip output carries a Requires-Python refusal and no ResolutionImpossible" >>"${TRANSCRIPT}.body"
  else
    echo "driver re-check: pip output is NOT a clean Requires-Python refusal" >>"${TRANSCRIPT}.body"
    VERDICT="FAIL"
  fi
fi

{
  grep -v '^RESULT: \(PASS\|FAIL\)$' "${TRANSCRIPT}.body"
  echo "RESULT: ${VERDICT}"
} >"${TRANSCRIPT}"
rm -f "${TRANSCRIPT}.body"

echo "transcript: ${TRANSCRIPT}"
tail -n 1 "${TRANSCRIPT}"
[ "${VERDICT}" = "PASS" ] && exit 0
exit 1
