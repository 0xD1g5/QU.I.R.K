#!/usr/bin/env bash
# validate-fresh-install.sh — prove a fresh Ubuntu install of QU.I.R.K. actually
# WORKS, not merely that each documented command exited 0.
#
# Why this exists: on 2026-09-16 the sensor container was found to emit no
# report-{stamp}.pdf for any scan, silently. The playwright Python package was
# installed, its browser binary and ~19 system libraries were not, and
# render_pdf_report() caught the launch error and returned False. Every scan
# exited 0, wrote eleven other artifacts, and warned about nothing. Graceful
# degradation intended for "playwright not installed" absorbed "playwright
# installed but unlaunchable".
#
# An install check that only asserts exit codes cannot see that class of defect.
# So every check here asserts an OBSERVABLE OUTCOME -- a launched browser, a file
# with PDF magic bytes, an HTTP 200 carrying a non-zero body of the right type.
#
# Deliberate departures from this repo's other scripts/*.sh, each with a reason:
#
#   1. NO `set -e`. The others are CI gates and should fail fast. This one exists
#      to produce a REPORT: aborting at check 4 would hide checks 5-9. Failures
#      are recorded and surfaced in the summary instead.
#   2. Requires an explicit --yes. It runs `sudo apt-get install` and
#      `sudo playwright install-deps`, which modify the system. It must not run
#      by accident on a machine you care about.
#   3. Emits a DOC DIVERGENCE section. The highest-value output is not pass/fail
#      but "docs/installation.md says X, reality needed Y" -- that is what feeds
#      back into the documentation.
#
# Prerequisite: the repo is already cloned (this script lives in it). The clone
# step from docs/installation.md is therefore assumed, not validated.
#
# Usage:
#   scripts/validate-fresh-install.sh --yes
#   scripts/validate-fresh-install.sh --yes --extras dashboard
#   scripts/validate-fresh-install.sh --self-check      # no system changes
#
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}" || { echo "cannot cd to ${REPO_ROOT}" >&2; exit 2; }

# --------------------------------------------------------------------------
# Options
# --------------------------------------------------------------------------
CONFIRMED=0
SELF_CHECK=0
EXTRAS="all"
VENV_DIR=".venv"
WORK_DIR="${REPO_ROOT}/validate-output"
PORT=8599              # deliberately not 8512 -- must not collide with a real dashboard
DOC="docs/installation.md"

while [ $# -gt 0 ]; do
  case "$1" in
    --yes)         CONFIRMED=1 ;;
    --self-check)  SELF_CHECK=1 ;;
    --extras)      EXTRAS="${2:-all}"; shift ;;
    --venv)        VENV_DIR="${2:-.venv}"; shift ;;
    --port)        PORT="${2:-8599}"; shift ;;
    -h|--help)
      sed -n '2,40p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
      exit 0 ;;
    *)
      echo "unknown option: $1 (try --help)" >&2; exit 2 ;;
  esac
  shift
done

# --------------------------------------------------------------------------
# Output helpers. Colour only when stdout is a terminal.
# --------------------------------------------------------------------------
if [ -t 1 ]; then
  B=$'\033[1m'; DIM=$'\033[2m'; R=$'\033[31m'; G=$'\033[32m'; Y=$'\033[33m'; C=$'\033[36m'; Z=$'\033[0m'
else
  B=""; DIM=""; R=""; G=""; Y=""; C=""; Z=""
fi

# Parallel indexed arrays -- NOT associative, so this runs on bash 3.2 (macOS)
# as well as bash 5 (Ubuntu). A --self-check on a Mac is the point.
RESULT_NAME=()
RESULT_STATE=()
RESULT_NOTE=()
DIVERGENCE=()
CURRENT=""
FAILED=0

check() {
  CURRENT="$1"
  printf '\n%s▸ %s%s\n' "${B}" "$1" "${Z}"
}

pass() {
  RESULT_NAME+=("${CURRENT}"); RESULT_STATE+=("PASS"); RESULT_NOTE+=("${1:-}")
  printf '  %sPASS%s %s\n' "${G}" "${Z}" "${1:-}"
}

fail() {
  # fail <what went wrong> <how to fix it>
  RESULT_NAME+=("${CURRENT}"); RESULT_STATE+=("FAIL"); RESULT_NOTE+=("$1")
  FAILED=$((FAILED + 1))
  printf '  %sFAIL%s %s\n' "${R}" "${Z}" "$1"
  [ -n "${2:-}" ] && printf '       %sFix: %s%s\n' "${DIM}" "$2" "${Z}"
  return 0
}

skip() {
  RESULT_NAME+=("${CURRENT}"); RESULT_STATE+=("SKIP"); RESULT_NOTE+=("$1")
  printf '  %sSKIP%s %s\n' "${Y}" "${Z}" "$1"
}

info() { printf '  %s%s%s\n' "${DIM}" "$1" "${Z}"; }

diverge() {
  DIVERGENCE+=("$1")
  printf '  %s! doc divergence: %s%s\n' "${C}" "$1" "${Z}"
}

# --------------------------------------------------------------------------
# Guards
# --------------------------------------------------------------------------
if [ "${SELF_CHECK}" -eq 0 ] && [ "${CONFIRMED}" -eq 0 ]; then
  cat >&2 <<'EOF'
This script installs system packages (apt-get, playwright install-deps) and
creates a virtualenv. Run it only on a throwaway VM.

  scripts/validate-fresh-install.sh --yes

To exercise the harness without touching the system:

  scripts/validate-fresh-install.sh --self-check
EOF
  exit 2
fi

printf '%s%s%s\n' "${B}" "QU.I.R.K. fresh-install validation" "${Z}"
printf '%srepo:   %s%s\n' "${DIM}" "${REPO_ROOT}" "${Z}"
printf '%sextras: [%s]   venv: %s   port: %s%s\n' "${DIM}" "${EXTRAS}" "${VENV_DIR}" "${PORT}" "${Z}"
[ "${SELF_CHECK}" -eq 1 ] && printf '%s%sSELF-CHECK MODE — no system changes, results are not a validation%s\n' "${Y}" "${B}" "${Z}"

# ==========================================================================
# 1. Environment
# ==========================================================================
check "1. Environment"

if [ -r /etc/os-release ]; then
  # shellcheck disable=SC1091
  . /etc/os-release
  info "os: ${NAME:-unknown} ${VERSION_ID:-}"
  case "${ID:-}" in
    ubuntu|debian) : ;;
    *) diverge "${DOC} documents Ubuntu/Debian; this host reports ID=${ID:-unknown}" ;;
  esac
else
  info "os: $(uname -s) (no /etc/os-release)"
  [ "${SELF_CHECK}" -eq 0 ] && diverge "no /etc/os-release — not an Ubuntu/Debian host"
fi

# glibc >= 2.17 is docs/installation.md's own stated Playwright floor.
GLIBC="$(ldd --version 2>/dev/null | head -1 | grep -oE '[0-9]+\.[0-9]+$')"
if [ -n "${GLIBC}" ]; then
  GLIBC_MAJOR="${GLIBC%%.*}"; GLIBC_MINOR="${GLIBC##*.}"
  if [ "${GLIBC_MAJOR}" -gt 2 ] || { [ "${GLIBC_MAJOR}" -eq 2 ] && [ "${GLIBC_MINOR}" -ge 17 ]; }; then
    pass "glibc ${GLIBC} (>= 2.17, Playwright floor met)"
  else
    fail "glibc ${GLIBC} is below 2.17" "PDF export cannot work here; use Ubuntu 20.04 or later"
  fi
else
  skip "glibc version not detectable (non-glibc host)"
fi

PY="$(command -v python3 || true)"
if [ -n "${PY}" ]; then
  PYV="$("${PY}" -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null)"
  if "${PY}" -c 'import sys; sys.exit(0 if sys.version_info[:2] >= (3,11) else 1)' 2>/dev/null; then
    pass "python3 ${PYV} (>= 3.11)"
  else
    fail "python3 ${PYV} is below the required 3.11" "install a newer python3"
  fi
else
  fail "python3 not found" "sudo apt-get install -y python3"
fi

AVAIL_KB="$(df -Pk "${REPO_ROOT}" 2>/dev/null | awk 'NR==2 {print $4}')"
if [ -n "${AVAIL_KB}" ]; then
  AVAIL_GB=$((AVAIL_KB / 1024 / 1024))
  if [ "${AVAIL_GB}" -ge 5 ]; then
    pass "disk ${AVAIL_GB}G available"
  else
    fail "only ${AVAIL_GB}G available" "chromium plus deps needs several GB; free space first"
  fi
fi

# ==========================================================================
# 2. System packages
# ==========================================================================
check "2. System packages (${DOC} §Linux)"
APT_LINE="sudo apt-get update && sudo apt-get install -y python3 python3-pip python3-venv git"
info "${APT_LINE}"

if [ "${SELF_CHECK}" -eq 1 ]; then
  skip "self-check: not running apt"
elif ! command -v apt-get >/dev/null 2>&1; then
  skip "no apt-get on this host"
else
  if sudo apt-get update -qq && sudo apt-get install -y -qq python3 python3-pip python3-venv git; then
    pass "documented apt packages present"
  else
    fail "apt-get install failed" "read the apt output above; the doc's package list may be incomplete"
  fi
fi

# ==========================================================================
# 3. venv + editable install
# ==========================================================================
check "3. Virtualenv and pip install -e '.[${EXTRAS}]'"

if [ "${SELF_CHECK}" -eq 1 ]; then
  skip "self-check: not creating a venv"
  VENV_PY="${PY}"
else
  if [ -d "${VENV_DIR}" ]; then
    diverge "${VENV_DIR} already existed — this is not a fresh host; reusing it"
  else
    if ! python3 -m venv "${VENV_DIR}"; then
      fail "python3 -m venv ${VENV_DIR} failed" "sudo apt-get install -y python3-venv"
    fi
  fi
  VENV_PY="${REPO_ROOT}/${VENV_DIR}/bin/python"
  if [ ! -x "${VENV_PY}" ]; then
    fail "no interpreter at ${VENV_DIR}/bin/python" "venv creation did not complete"
  else
    if "${VENV_PY}" -m pip install -q --upgrade pip && \
       "${VENV_PY}" -m pip install -q -e ".[${EXTRAS}]"; then
      pass "installed -e '.[${EXTRAS}]'"
    else
      fail "pip install -e '.[${EXTRAS}]' failed" "read the pip output above"
    fi
  fi
fi

VENV_BIN="${REPO_ROOT}/${VENV_DIR}/bin"

# ==========================================================================
# 4. Playwright — the check that matters most
# ==========================================================================
check "4. Playwright browser and system libraries"

if [ "${SELF_CHECK}" -eq 1 ]; then
  skip "self-check: not installing chromium"
elif ! "${VENV_PY}" -c 'import playwright' 2>/dev/null; then
  skip "playwright not in [${EXTRAS}] — PDF export is not expected to work"
  diverge "extras [${EXTRAS}] does not provide playwright; PDF export unavailable by design"
else
  "${VENV_BIN}/playwright" install chromium >/dev/null 2>&1 \
    || fail "playwright install chromium failed" "check network access"

  if command -v apt-get >/dev/null 2>&1; then
    sudo "${VENV_BIN}/playwright" install-deps chromium >/dev/null 2>&1 \
      || fail "playwright install-deps chromium failed" "needs sudo and apt; run it manually to see the error"
  else
    skip "install-deps needs apt; skipped"
  fi

  # Do not trust the installers' exit codes -- check the binary can actually run.
  BROWSER="$("${VENV_PY}" - <<'PY' 2>/dev/null
import glob, os, sys
hits = []
for root in (os.path.expanduser("~/.cache/ms-playwright"), "/ms-playwright"):
    hits += glob.glob(os.path.join(root, "chromium*", "*", "chrome-headless-shell"))
    hits += glob.glob(os.path.join(root, "chromium*", "*", "chrome"))
print(hits[0] if hits else "")
PY
)"
  if [ -z "${BROWSER}" ]; then
    fail "no chromium binary found under ~/.cache/ms-playwright" "run: ${VENV_DIR}/bin/playwright install chromium"
  else
    info "binary: ${BROWSER}"
    MISSING="$(ldd "${BROWSER}" 2>/dev/null | grep -c 'not found')"
    if [ "${MISSING:-0}" -eq 0 ]; then
      pass "0 missing shared libraries"
    else
      fail "${MISSING} missing shared libraries" "sudo ${VENV_DIR}/bin/playwright install-deps chromium"
      diverge "chromium binary present but unlaunchable — installing the browser alone is not sufficient"
    fi
  fi

  # The real proof: launch it.
  if "${VENV_PY}" - <<'PY' >/dev/null 2>&1
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch()
    b.close()
PY
  then
    pass "chromium launches"
  else
    fail "chromium will not launch" "PDF export will silently produce nothing; see install-deps above"
  fi
fi

# ==========================================================================
# 5. CLI smoke
# ==========================================================================
check "5. CLI responds"

if [ "${SELF_CHECK}" -eq 1 ]; then
  skip "self-check: no venv to invoke"
else
  for sub in "--help" "serve --help"; do
    # shellcheck disable=SC2086
    if "${VENV_BIN}/quirk" ${sub} >/dev/null 2>&1; then
      pass "quirk ${sub}"
    else
      fail "quirk ${sub} failed" "the console script did not install correctly"
    fi
  done
fi

# ==========================================================================
# 6. Functional scan
# ==========================================================================
check "6. Functional scan against localhost"

CONF="${WORK_DIR}/config.yaml"
OUTDIR="${WORK_DIR}/out"

if [ "${SELF_CHECK}" -eq 1 ]; then
  skip "self-check: not scanning"
else
  mkdir -p "${OUTDIR}"
  # Patch the shipped template rather than hand-writing a config: config_from_dict()
  # requires the full top-level schema, and a hand-rolled stub drifts from it.
  if "${VENV_PY}" - "$CONF" "$OUTDIR" <<'PY'
import sys, yaml, pathlib
conf_path, outdir = sys.argv[1], sys.argv[2]
tpl = yaml.safe_load(pathlib.Path("quirk/config_template.yaml").read_text())
tpl.setdefault("targets", {})
tpl["targets"]["cidrs"] = ["127.0.0.1"]
tpl["targets"]["fqdns"] = None
tpl.setdefault("output", {})
tpl["output"]["directory"] = outdir
tpl["output"]["db_path"] = f"{outdir}/quirk.db"
pathlib.Path(conf_path).write_text(yaml.safe_dump(tpl, sort_keys=False))
print("wrote", conf_path)
PY
  then
    info "config: ${CONF} (targets 127.0.0.1, output ${OUTDIR})"
    if "${VENV_BIN}/quirk" --config "${CONF}" >"${WORK_DIR}/scan.log" 2>&1; then
      N="$(find "${OUTDIR}" -maxdepth 1 -type f | wc -l | tr -d ' ')"
      pass "scan completed, ${N} artifacts in ${OUTDIR}"
    else
      fail "scan exited non-zero" "see ${WORK_DIR}/scan.log"
    fi
  else
    fail "could not generate a config from quirk/config_template.yaml" "check the template's schema"
  fi
fi

# ==========================================================================
# 7. PDF actually rendered — the regression this script exists for
# ==========================================================================
check "7. PDF report is real"

if [ "${SELF_CHECK}" -eq 1 ]; then
  skip "self-check: no scan output"
else
  PDF="$(find "${OUTDIR}" -maxdepth 1 -name 'report-*.pdf' 2>/dev/null | head -1)"
  if [ -z "${PDF}" ]; then
    fail "no report-*.pdf was written" "chromium cannot launch; re-read check 4. The scan still exits 0 — that is the bug this check exists to catch."
    diverge "scan exited 0 and wrote other artifacts, but produced no PDF — exit code is not evidence"
  else
    SIZE="$(wc -c < "${PDF}" | tr -d ' ')"
    MAGIC="$(head -c 4 "${PDF}")"
    if [ "${MAGIC}" = "%PDF" ] && [ "${SIZE}" -gt 1000 ]; then
      pass "$(basename "${PDF}") — ${SIZE} bytes, %PDF magic bytes present"
    else
      fail "$(basename "${PDF}") is ${SIZE} bytes, magic '${MAGIC}'" "the file exists but is not a valid PDF"
    fi
  fi
fi

# ==========================================================================
# 8. Dashboard serves all five downloads
# ==========================================================================
check "8. Dashboard and report downloads"

SERVE_PID=""
cleanup() {
  if [ -n "${SERVE_PID}" ] && kill -0 "${SERVE_PID}" 2>/dev/null; then
    kill "${SERVE_PID}" 2>/dev/null
    wait "${SERVE_PID}" 2>/dev/null
  fi
}
trap cleanup EXIT INT TERM

if [ "${SELF_CHECK}" -eq 1 ]; then
  skip "self-check: not starting the dashboard"
else
  QUIRK_CONFIG_PATH="${CONF}" "${VENV_BIN}/quirk" serve --port "${PORT}" \
    >"${WORK_DIR}/serve.log" 2>&1 &
  SERVE_PID=$!

  UP=0
  for _ in $(seq 1 30); do
    if curl -fsS -o /dev/null "http://127.0.0.1:${PORT}/api/reports/latest/manifest" 2>/dev/null; then
      UP=1; break
    fi
    sleep 1
  done

  if [ "${UP}" -eq 0 ]; then
    fail "dashboard did not answer on port ${PORT} within 30s" "see ${WORK_DIR}/serve.log"
  else
    pass "dashboard listening on ${PORT}"

    MANIFEST="$(curl -fsS "http://127.0.0.1:${PORT}/api/reports/latest/manifest" 2>/dev/null)"
    UNAVAIL="$(printf '%s' "${MANIFEST}" | "${VENV_PY}" -c '
import json,sys
try: d=json.load(sys.stdin)
except Exception: print("PARSE"); sys.exit()
print(",".join(k for k,v in d.get("formats",{}).items() if not v.get("available")) or "none")
' 2>/dev/null)"

    if [ "${UNAVAIL}" = "none" ]; then
      pass "manifest reports all five formats available"
    else
      fail "formats unavailable: ${UNAVAIL}" "each carries a written reason in the manifest JSON"
    fi

    for fmt in html pdf docx cbom-json cbom-xml; do
      BODY="${WORK_DIR}/dl-${fmt}.bin"
      CODE="$(curl -sS -o "${BODY}" -w '%{http_code}' \
        "http://127.0.0.1:${PORT}/api/reports/latest/${fmt}" 2>/dev/null)"
      BYTES="$(wc -c < "${BODY}" 2>/dev/null | tr -d ' ')"
      if [ "${CODE}" = "200" ] && [ "${BYTES:-0}" -gt 100 ]; then
        pass "download ${fmt}: HTTP 200, ${BYTES} bytes"
      else
        fail "download ${fmt}: HTTP ${CODE}, ${BYTES:-0} bytes" "route or artifact missing"
      fi
    done
  fi
  cleanup; SERVE_PID=""
fi

# ==========================================================================
# 9. Summary
# ==========================================================================
printf '\n%s%s%s\n' "${B}" "──────────────────────────────────────────────────────────" "${Z}"
printf '%s%s%s\n\n' "${B}" "SUMMARY" "${Z}"

i=0
while [ "${i}" -lt "${#RESULT_NAME[@]}" ]; do
  state="${RESULT_STATE[$i]}"
  case "${state}" in
    PASS) col="${G}" ;;
    FAIL) col="${R}" ;;
    *)    col="${Y}" ;;
  esac
  printf '  %s%-4s%s  %-46s %s%s\n' "${col}" "${state}" "${Z}" "${RESULT_NAME[$i]}" "${DIM}" "${RESULT_NOTE[$i]}${Z}"
  i=$((i + 1))
done

if [ "${#DIVERGENCE[@]}" -gt 0 ]; then
  printf '\n%s%sDOC DIVERGENCE — reconcile against %s%s\n\n' "${B}" "${C}" "${DOC}" "${Z}"
  for d in "${DIVERGENCE[@]}"; do
    printf '  %s·%s %s\n' "${C}" "${Z}" "${d}"
  done
fi

printf '\n'
if [ "${SELF_CHECK}" -eq 1 ]; then
  printf '%sSelf-check complete. This is NOT a validation — run with --yes on a fresh VM.%s\n' "${Y}" "${Z}"
  exit 0
fi

if [ "${FAILED}" -eq 0 ]; then
  printf '%s%sAll checks passed.%s Artifacts and logs under %s\n' "${G}" "${B}" "${Z}" "${WORK_DIR}"
  exit 0
fi

printf '%s%s%d check(s) failed.%s Logs under %s\n' "${R}" "${B}" "${FAILED}" "${Z}" "${WORK_DIR}"
exit 1
