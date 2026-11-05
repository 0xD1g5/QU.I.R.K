#!/usr/bin/env bash
# Runs INSIDE a clean environment (a python:3.X-slim container, or a scrubbed
# macOS environment). Driven by scripts/release_smoke.sh; not meant to be run
# by hand. It executes the README's own commands as written (logging a
# disposition for every one), then proves OUTCOMES rather than exit codes.
#
# Inputs (environment, set by the outer driver):
#   Q_LEG               linux-3.11 | linux-3.10 | linux-3.15-neg | macos | contributor
#   Q_SOURCE_KIND       wheel | pypi | git
#   Q_SOURCE_VALUE      wheel path as seen here, a PyPI version, or a git ref
#   Q_EXPECTED_VERSION  version `quirk --version` must report
#   Q_TARGETS           HOST:PORT,HOST:PORT scan targets
#   Q_COMMANDS_JSON     output of `readme_audit.py commands`
#   Q_OUT               directory the transcript and artifacts are written to
#   Q_SCORE_ATTR        path to score_attribution.py
#   Q_PIP_VERDICT       path to pip_unpinned_verdict.py (linux-3.15-neg check N2; missing = FAIL)
#   Q_DIVERGENCE_SET    optional path to a divergence-set JSON
#   Q_START_DIR         optional starting directory (contributor clone parent)
#   Q_PORT              dashboard port (default 8512, the README default)
#
# Last line of the transcript is exactly `RESULT: PASS` or `RESULT: FAIL`.
# No `set -e`: a failed check must be recorded and the run must carry on.
set -uo pipefail

# --------------------------------------------------------------------------
# Pure helpers (also exercised by --self-check)
# --------------------------------------------------------------------------

# minor_key 3.10 -> 310 (the README range is expressed in 3.X versions)
minor_key() {
  local major="${1%%.*}" rest="${1#*.}"
  rest="${rest%%.*}"
  echo $((major * 100 + rest))
}

# interp_in_range IVER RANGE   (RANGE like 3.10-3.14)
interp_in_range() {
  local iv="$1" lo="${2%-*}" hi="${2#*-}"
  local k
  k="$(minor_key "${iv}")"
  [ "${k}" -ge "$(minor_key "${lo}")" ] && [ "${k}" -le "$(minor_key "${hi}")" ]
}

# decide_interp LEG IVER RANGE VENV_INTERP
#   Prints one of: ASIS | SUBST | EXEMPT-ASIS | EXEMPT-SUBST | FAIL:<reason>
#   VENV_INTERP is the interpreter name in the README's venv line.
decide_interp() {
  local leg="$1" iv="$2" range="$3" name="$4"
  local versioned=0
  case "${name}" in python3|python) versioned=0 ;; *) versioned=1 ;; esac
  if [ "${leg}" = "linux-3.15-neg" ]; then
    # Deliberate negative leg: 3.15 is outside the stated range by design.
    [ "${versioned}" -eq 1 ] && echo "EXEMPT-SUBST" || echo "EXEMPT-ASIS"
    return 0
  fi
  if [ -z "${range}" ]; then
    if [ "${versioned}" -eq 1 ]; then
      echo "FAIL:README names ${name} but states no supported Python range, so the substitution cannot be justified"
    else
      echo "ASIS"
    fi
    return 0
  fi
  if ! interp_in_range "${iv}" "${range}"; then
    echo "FAIL:interpreter ${iv} is outside the README's stated range ${range}"
    return 0
  fi
  if [ "${versioned}" -eq 1 ] && [ "${name}" != "python${iv}" ]; then
    echo "SUBST"
  else
    echo "ASIS"
  fi
}

# neg_verdict FILE : 0 when the pip output shows a Requires-Python refusal
neg_verdict() {
  grep -qE "Requires-Python|requires a different Python" "$1" \
    && ! grep -q "ResolutionImpossible" "$1"
}

# verdict_line FAILED SKIPS TOTAL : the ONLY place a run verdict is decided.
# PASS requires zero failures, zero skips and at least one recorded check
# (235.1 HARNESS-04 NEW-1/NEW-2: a SKIP or an empty run must never print PASS).
verdict_line() {
  if [ "$1" -eq 0 ] && [ "$2" -eq 0 ] && [ "$3" -gt 0 ]; then
    echo "RESULT: PASS"
  else
    echo "RESULT: FAIL"
  fi
}

# needs_inshell TEXT : 0 when the command changes shell state (cd/source/./
# export) and therefore must run via in-shell eval, not under a watchdog.
needs_inshell() {
  case "$1" in
    *"cd "*|*"source "*|". "*|*"&& . "*|*"; . "*|*"export "*) return 0 ;;
  esac
  return 1
}

# run_bounded SECS TEXT : run TEXT in a child shell with a watchdog.
# Returns the command's rc, or 124 on expiry. stdout/stderr are the caller's.
run_bounded() {
  local secs="$1" text="$2" pid wd rc mark
  if [ -z "${Q_NO_TIMEOUT_BIN:-}" ] && command -v timeout >/dev/null 2>&1; then
    timeout -k 5 "${secs}" bash -c "${text}" </dev/null
    return $?
  fi
  mark="$(mktemp "${TMPDIR:-/tmp}/qwd.XXXXXX")"; rm -f "${mark}"
  ( eval "${text}" ) </dev/null &
  pid=$!
  ( sleep "${secs}"; : >"${mark}"; kill -TERM "${pid}" 2>/dev/null; sleep 2; kill -KILL "${pid}" 2>/dev/null ) &
  wd=$!
  wait "${pid}"; rc=$?
  kill "${wd}" 2>/dev/null; wait "${wd}" 2>/dev/null
  if [ -f "${mark}" ]; then rm -f "${mark}"; return 124; fi
  return "${rc}"
}

# timed_out RC : 0 when RC is a run_bounded watchdog expiry (124, or 137 once -k
# escalates to SIGKILL). A killed command's partial output must never be judged.
timed_out() { [ "$1" -eq 124 ] || [ "$1" -eq 137 ]; }

# port_in_use PORT : 0 when something already answers on 127.0.0.1:PORT
port_in_use() {
  python3 - "$1" <<'PY' >/dev/null 2>&1
import socket, sys
s = socket.socket()
s.settimeout(2)
try:
    sys.exit(0 if s.connect_ex(("127.0.0.1", int(sys.argv[1]))) == 0 else 1)
finally:
    s.close()
PY
}

if [ "${1:-}" = "--probe-port" ]; then
  if port_in_use "${2:?port}"; then echo "port ${2} already in use"; exit 1; fi
  echo "port ${2} free"; exit 0
fi

if [ "${1:-}" = "--self-check" ]; then
  bad=0
  expect() {
    local got
    got="$(decide_interp "$1" "$2" "$3" "$4")"
    case "${got}" in
      $5) echo "  ok   decide_interp $1 $2 '$3' $4 -> ${got}" ;;
      *)  echo "  FAIL decide_interp $1 $2 '$3' $4 -> ${got} (wanted $5)"; bad=1 ;;
    esac
  }
  expect linux-3.11 3.11 3.10-3.14 python3.12 SUBST
  expect linux-3.11 3.15 3.10-3.14 python3 'FAIL:*'
  expect linux-3.15-neg 3.15 3.10-3.14 python3.12 EXEMPT-SUBST
  expect linux-3.10 3.10 3.10-3.14 python3 ASIS
  expect linux-3.11 3.11 "" python3.12 'FAIL:*'
  d="$(mktemp -d)"
  printf 'ERROR: Package requires a different Python: 3.15.0 not in <3.15\n' >"${d}/a"
  printf 'Requires-Python ... ResolutionImpossible\n' >"${d}/b"
  if neg_verdict "${d}/a"; then echo "  ok   neg_verdict accepts a Requires-Python refusal"; else echo "  FAIL neg_verdict (a)"; bad=1; fi
  if neg_verdict "${d}/b"; then echo "  FAIL neg_verdict accepted ResolutionImpossible"; bad=1; else echo "  ok   neg_verdict rejects ResolutionImpossible"; fi
  PV="$(dirname "$0")/pip_unpinned_verdict.py"
  printf '{"version":"1","install":[{"metadata":{"name":"quirk-scanner","version":"5.21.0"}}]}' >"${d}/u.json"
  printf 'ERROR: ResolutionImpossible: for help visit\n' >"${d}/u.txt"
  if python3 "${PV}" --report "${d}/u.json" --output "${d}/u.txt" --rc 0 --expected 5.28.1 >/dev/null; then
    echo "  FAIL unpinned verdict accepted an older selected release"; bad=1
  else echo "  ok   unpinned verdict rejects an older selected release"; fi
  if python3 "${PV}" --report "${d}/none.json" --output "${d}/u.txt" --rc 1 --expected 5.28.1 >/dev/null; then
    echo "  ok   unpinned verdict accepts ResolutionImpossible"
  else echo "  FAIL unpinned verdict rejected ResolutionImpossible"; bad=1; fi
  # verdict_line: SKIP, zero checks and a clean PASS (235.1 NEW-1/NEW-2)
  [ "$(verdict_line 0 1 3)" = "RESULT: FAIL" ] && echo "  ok   verdict_line: a SKIP is FAIL" || { echo "  FAIL verdict_line accepted a SKIP"; bad=1; }
  [ "$(verdict_line 0 0 0)" = "RESULT: FAIL" ] && echo "  ok   verdict_line: zero checks is FAIL" || { echo "  FAIL verdict_line accepted zero checks"; bad=1; }
  [ "$(verdict_line 1 0 3)" = "RESULT: FAIL" ] && echo "  ok   verdict_line: a failure is FAIL" || { echo "  FAIL verdict_line accepted a failure"; bad=1; }
  [ "$(verdict_line 0 0 3)" = "RESULT: PASS" ] && echo "  ok   verdict_line: clean run is PASS" || { echo "  FAIL verdict_line rejected a clean run"; bad=1; }
  # watchdog: a hung command must come back 124 quickly (WR-10)
  t0="$(date +%s)"
  run_bounded 1 'sleep 12' >/dev/null 2>&1; wrc=$?
  t1="$(date +%s)"
  if [ "${wrc}" -ne 0 ] && [ $((t1 - t0)) -le 8 ]; then echo "  ok   run_bounded times out a hung command (rc ${wrc}, $((t1 - t0))s)"; else echo "  FAIL run_bounded did not stop a hung command (rc ${wrc}, $((t1 - t0))s)"; bad=1; fi
  if timed_out 124 && timed_out 137 && ! timed_out 1 && ! timed_out 0; then echo "  ok   timed_out recognises 124/137 only"; else echo "  FAIL timed_out misclassifies watchdog exits"; bad=1; fi
  run_bounded 5 'exit 0' >/dev/null 2>&1 && echo "  ok   run_bounded passes a quick command" || { echo "  FAIL run_bounded failed a quick command"; bad=1; }
  needs_inshell 'python3.12 -m venv .venv && source .venv/bin/activate' && echo "  ok   needs_inshell keeps source in-shell" || { echo "  FAIL needs_inshell on source"; bad=1; }
  needs_inshell 'pip install x' && { echo "  FAIL needs_inshell flagged pip"; bad=1; } || echo "  ok   needs_inshell lets pip run bounded"
  # port collision: a live listener must be seen (WR-09)
  python3 -c "
import socket, sys, time
s = socket.socket(); s.bind(('127.0.0.1', 0)); s.listen(1)
print(s.getsockname()[1], flush=True); time.sleep(8)" >"${d}.port" &
  lpid=$!
  for _ in 1 2 3 4 5 6 7 8 9 10; do [ -s "${d}.port" ] && break; sleep 0.3; done
  lport="$(head -n 1 "${d}.port")"
  if [ -n "${lport}" ] && port_in_use "${lport}"; then echo "  ok   port_in_use sees a foreign listener"; else echo "  FAIL port_in_use missed a foreign listener"; bad=1; fi
  kill "${lpid}" 2>/dev/null; wait "${lpid}" 2>/dev/null; rm -f "${d}.port"
  rm -rf "${d}"
  [ "${bad}" -eq 0 ] && echo "inner self-check: ok" && exit 0
  echo "inner self-check: FAILED"; exit 1
fi

# --------------------------------------------------------------------------
# Transcript + result helpers (bash-3.2 safe: indexed arrays only)
# --------------------------------------------------------------------------
: "${Q_LEG:?}" "${Q_SOURCE_KIND:?}" "${Q_SOURCE_VALUE:?}" "${Q_OUT:?}"
mkdir -p "${Q_OUT}"
LOG="${Q_OUT}/transcript.txt"
: >"${LOG}"
RESULT_NAME=(); RESULT_STATE=(); RESULT_NOTE=(); DIVERGENCE=()
CURRENT=""; FAILED=0; ABORT=0
PORT="${Q_PORT:-8512}"

say() { printf '%s\n' "$*" | tee -a "${LOG}"; }
check() { CURRENT="$1"; say ""; say "== $1"; }
pass() { RESULT_NAME+=("${CURRENT}"); RESULT_STATE+=("PASS"); RESULT_NOTE+=("${1:-}"); say "  PASS ${1:-}"; }
fail() {
  RESULT_NAME+=("${CURRENT}"); RESULT_STATE+=("FAIL"); RESULT_NOTE+=("$1")
  FAILED=$((FAILED + 1)); say "  FAIL $1"
  [ -n "${2:-}" ] && say "       Fix: $2"
  return 0
}
skip() { RESULT_NAME+=("${CURRENT}"); RESULT_STATE+=("SKIP"); RESULT_NOTE+=("$1"); say "  SKIP $1"; }
info() { say "  $1"; }
diverge() { DIVERGENCE+=("$1"); say "  ! doc divergence: $1"; }
disposition() { say "DISPOSITION: README line $1 | $2 | $3"; }

finish() {
  say ""; say "SUMMARY"
  local i=0
  while [ "${i}" -lt "${#RESULT_NAME[@]}" ]; do
    say "  ${RESULT_STATE[$i]}  ${RESULT_NAME[$i]}  ${RESULT_NOTE[$i]}"
    i=$((i + 1))
  done
  if [ "${#DIVERGENCE[@]}" -gt 0 ]; then
    say ""; say "DOC DIVERGENCE (reconcile the README, not the environment)"
    for d in "${DIVERGENCE[@]}"; do say "  - ${d}"; done
  fi
  say ""
  local skips=0 j=0
  while [ "${j}" -lt "${#RESULT_STATE[@]}" ]; do
    [ "${RESULT_STATE[$j]}" = "SKIP" ] && skips=$((skips + 1))
    j=$((j + 1))
  done
  [ "${skips}" -gt 0 ] && say "NOTE: ${skips} check(s) were SKIPPED; a skipped check is not a pass"
  [ "${#RESULT_NAME[@]}" -eq 0 ] && say "NOTE: no checks were recorded; an empty run is not a pass"
  local vline
  vline="$(verdict_line "${FAILED}" "${skips}" "${#RESULT_NAME[@]}")"
  say "${vline}"
  [ "${vline}" = "RESULT: PASS" ] && exit 0
  exit 1
}

SERVE_PID=""
cleanup() {
  if [ -n "${SERVE_PID}" ] && kill -0 "${SERVE_PID}" 2>/dev/null; then
    kill "${SERVE_PID}" 2>/dev/null; wait "${SERVE_PID}" 2>/dev/null
  fi
}
trap cleanup EXIT INT TERM

CMDLOG="${Q_OUT}/commands.log"
: >"${CMDLOG}"

# run_readme_cmd <text> : eval in THIS shell (so `source activate` and `cd`
# persist), output appended to the command log and echoed into the transcript.
run_readme_cmd() {
  local before after rc
  before="$(wc -l <"${CMDLOG}")"
  say "RUN: $1"
  set +u
  if needs_inshell "$1"; then
    eval "$1" >>"${CMDLOG}" 2>&1 </dev/null
    rc=$?
  else
    run_bounded "${Q_CMD_TIMEOUT:-900}" "$1" >>"${CMDLOG}" 2>&1 </dev/null
    rc=$?
  fi
  set -u
  after="$(wc -l <"${CMDLOG}")"
  tail -n $((after - before)) "${CMDLOG}" | sed 's/^/    | /' >>"${LOG}"
  if [ "${rc}" -eq 124 ]; then
    fail "timed out after ${Q_CMD_TIMEOUT:-900}s: $1" "a README command hung; see commands.log"
  fi
  return "${rc}"
}

# --------------------------------------------------------------------------
# Header
# --------------------------------------------------------------------------
BASE_PY="${Q_BASE_PYTHON:-python3}"
IVER="$("${BASE_PY}" -c 'import sys;print("%d.%d.%d" % sys.version_info[:3])')"
say "QUIRK release smoke - leg ${Q_LEG}"
say "inner start (UTC): $(date -u +%Y-%m-%dT%H:%M:%SZ)"
say "interpreter: $(command -v "${BASE_PY}") ${IVER}"
say "source: ${Q_SOURCE_KIND}:${Q_SOURCE_VALUE}"
say "expected version: ${Q_EXPECTED_VERSION:-unknown}"
say "targets: ${Q_TARGETS:-none}"

WORK="${Q_START_DIR:-}"
if [ -z "${WORK}" ]; then
  WORK="$(mktemp -d "${TMPDIR:-/tmp}/qsmoke.XXXXXX")"
fi
cd "${WORK}" || { say "cannot cd to ${WORK}"; exit 2; }
say "workdir: ${WORK}"

# --------------------------------------------------------------------------
# Command list from the README (never hard-coded here)
# --------------------------------------------------------------------------
TSV="${Q_OUT}/readme-commands.tsv"
RANGE="$("${BASE_PY}" - "${Q_COMMANDS_JSON}" "${TSV}" <<'PY'
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
with open(sys.argv[2], "w", encoding="utf-8") as out:
    for c in d["commands"]:
        out.write("%s\t%s\t%s\t%s\n" % (
            c["line"], c["kind"], c.get("block", "user"),
            c["text"].replace("\t", " ").replace("\n", " ")))
print(d.get("python_range") or "")
PY
)"
say "README stated Python range: ${RANGE:-none stated}"
say "README commands enumerated: $(wc -l <"${TSV}" | tr -d ' ')"

NEG=0; [ "${Q_LEG}" = "linux-3.15-neg" ] && NEG=1
CONTRIB=0; [ "${Q_LEG}" = "contributor" ] && CONTRIB=1
SCAN_DONE=0; REWRITTEN=0; N_RAN=0; N2_RAN=0

pip_target() {
  # $1 = extras string such as "[all]" (may be empty)
  case "${Q_SOURCE_KIND}" in
    wheel) printf "'%s%s'" "${Q_SOURCE_VALUE}" "$1" ;;
    pypi)  printf "'quirk-scanner%s==%s'" "$1" "${Q_SOURCE_VALUE}" ;;
    *)     printf "'quirk-scanner%s'" "$1" ;;
  esac
}

rewrite_targets() {
  local ln="$1"
  python - "${Q_TARGETS}" <<'PY' >>"${LOG}" 2>&1
import ipaddress, sys, pathlib, yaml
hosts, ports = [], []
for item in filter(None, sys.argv[1].split(",")):
    host, _, port = item.rpartition(":")
    if host not in hosts:
        hosts.append(host)
    if int(port) not in ports:
        ports.append(int(port))
p = pathlib.Path("config.yaml")
cfg = yaml.safe_load(p.read_text())
ips, names = [], []
for h in hosts:
    try:
        ipaddress.ip_address(h); ips.append(h)
    except ValueError:
        names.append(h)
cfg.setdefault("targets", {})
cfg["targets"]["include_ips"] = ips
cfg["targets"]["cidrs"] = []
cfg["targets"]["fqdns"] = names
cfg.setdefault("scan", {})["ports_tls"] = ports
p.write_text(yaml.safe_dump(cfg, sort_keys=False))
print("targets rewritten: hosts=%s ports=%s" % (hosts, ports))
PY
  if [ $? -eq 0 ]; then
    say "SUBSTITUTED: ${ln} | config.yaml targets as written by 'quirk init' -> ${Q_TARGETS} | the starter config has placeholder targets; the README tells the reader to edit them"
    REWRITTEN=1
  else
    fail "could not rewrite config.yaml targets" "the starter config no longer parses"
  fi
}

# --------------------------------------------------------------------------
# README command pass
# --------------------------------------------------------------------------
check "A. README commands"
while IFS=$'\t' read -r LN KIND BLOCK TEXT; do
  [ -z "${LN}" ] && continue
  if [ "${KIND}" = "inline" ]; then
    disposition "${LN}" "not-applicable" "inline mention in prose, not a standalone step: ${TEXT}"
    continue
  fi
  if [ "${ABORT}" -eq 1 ]; then
    disposition "${LN}" "not-applicable" "skipped after an earlier install failure"
    continue
  fi
  case "${TEXT}" in
    pypi-attestations*|gh\ attestation*)
      if [ "${Q_SOURCE_KIND}" = "wheel" ]; then
        disposition "${LN}" "post-publish-only" "attestations exist only for the published release: ${TEXT}"
        continue
      fi ;;
  esac
  if [ "${CONTRIB}" -eq 1 ] && [ "${BLOCK}" != "contributor" ]; then
    disposition "${LN}" "not-applicable" "user Quick Start block; the contributor leg runs the contributor block"
    continue
  fi
  if [ "${CONTRIB}" -eq 0 ] && [ "${BLOCK}" = "contributor" ]; then
    disposition "${LN}" "not-applicable" "contributor block; not part of a user install"
    continue
  fi

  case "${TEXT}" in
    python*\ -m\ venv*)
      NAME="${TEXT%% *}"
      DEC="$(decide_interp "${Q_LEG}" "${IVER}" "${RANGE}" "${NAME}")"
      case "${DEC}" in
        FAIL:*)
          fail "${DEC#FAIL:}" "fix the README's stated range or run the leg on an in-range interpreter"
          diverge "line ${LN}: ${DEC#FAIL:}"
          ABORT=1; continue ;;
        EXEMPT-*)
          say "RANGE-EXEMPT: linux-3.15-neg | interpreter ${IVER%.*} outside stated range ${RANGE:-3.10-3.14} | deliberate negative leg, PASS only on a Requires-Python refusal" ;;
      esac
      AS_RUN="${TEXT}"
      case "${DEC}" in
        SUBST|EXEMPT-SUBST)
          AS_RUN="${BASE_PY} ${TEXT#* }"
          say "SUBSTITUTED: ${LN} | ${NAME} -> ${BASE_PY} (${IVER}) | the README names one example interpreter; this leg proves a different point of the stated range ${RANGE:-n/a}"
          disposition "${LN}" "ran-substituted" "${TEXT}" ;;
        *) disposition "${LN}" "ran-as-written" "${TEXT}" ;;
      esac
      if ! run_readme_cmd "${AS_RUN}"; then
        fail "venv creation failed: ${TEXT}" "the README's venv step does not work on this image"
        diverge "line ${LN}: ${TEXT} failed (see commands.log)"; ABORT=1
      fi ;;

    pip\ install\ -e*)
      disposition "${LN}" "ran-as-written" "${TEXT}"
      run_readme_cmd "${TEXT}" || { fail "editable install failed" "see commands.log"; diverge "line ${LN}: ${TEXT} failed"; ABORT=1; } ;;

    pip\ install*quirk-scanner*)
      EXTRAS=""
      if [[ "${TEXT}" =~ quirk-scanner(\[[^]]*\])? ]]; then EXTRAS="${BASH_REMATCH[1]:-}"; fi
      AS_RUN="pip install $(pip_target "${EXTRAS}")"
      if [ "${Q_SOURCE_KIND}" = "git" ]; then AS_RUN="${TEXT}"; fi
      if [ "${AS_RUN}" = "${TEXT}" ]; then
        disposition "${LN}" "ran-as-written" "${TEXT}"
      else
        say "SUBSTITUTED: ${LN} | ${TEXT} -> ${AS_RUN} | pin the install to the artifact under test"
        disposition "${LN}" "ran-substituted" "${TEXT}"
      fi
      if [ "${NEG}" -eq 1 ]; then
        say "RUN: ${AS_RUN}   (expected to be refused)"
        set +u; run_bounded "${Q_CMD_TIMEOUT:-900}" "${AS_RUN}" >"${Q_OUT}/pip-negative.txt" 2>&1; PIP_RC=$?; set -u
        sed 's/^/    | /' "${Q_OUT}/pip-negative.txt" >>"${LOG}"
        check "N. Python 3.15 is refused by Requires-Python"; N_RAN=1
        if timed_out "${PIP_RC}"; then
          fail "pip timed out after ${Q_CMD_TIMEOUT:-900}s (rc ${PIP_RC})" "a hung install is not a refusal"
        elif [ "${PIP_RC}" -ne 0 ] && neg_verdict "${Q_OUT}/pip-negative.txt"; then
          pass "pip refused the install with a Requires-Python message (rc ${PIP_RC})"
        else
          fail "pip rc ${PIP_RC}; refusal not a clean Requires-Python message" \
               "a ResolutionImpossible or a successful install means python_requires is wrong"
        fi
        # N2 (235.1 D-02): an UNPINNED resolve must not fall back to an older release.
        check "N2. unpinned resolve selects no older quirk-scanner"; N2_RAN=1
        set +u; run_bounded "${Q_CMD_TIMEOUT:-900}" \
          "python -m pip install --dry-run --quiet --report \"${Q_OUT}/pip-unpinned.json\" quirk-scanner" \
          >"${Q_OUT}/pip-unpinned.txt" 2>&1; PIP_U_RC=$?; set -u
        printf '%s\n' "${PIP_U_RC}" >"${Q_OUT}/pip-unpinned.rc"
        sed 's/^/    | /' "${Q_OUT}/pip-unpinned.txt" >>"${LOG}"
        if timed_out "${PIP_U_RC}"; then
          fail "unpinned pip resolve timed out after ${Q_CMD_TIMEOUT:-900}s (rc ${PIP_U_RC})" \
               "a killed resolve's partial output is not a verdict"
        elif [ -z "${Q_PIP_VERDICT:-}" ] || [ ! -f "${Q_PIP_VERDICT}" ]; then
          fail "pip_unpinned_verdict.py not provided" "the harness must copy scripts/pip_unpinned_verdict.py and set Q_PIP_VERDICT"
        else
          PIP_U_LINE="$(python3 "${Q_PIP_VERDICT}" --report "${Q_OUT}/pip-unpinned.json" \
            --output "${Q_OUT}/pip-unpinned.txt" --rc "${PIP_U_RC}" --expected "${Q_EXPECTED_VERSION:-}" 2>&1)"
          PIP_U_VRC=$?
          if [ "${PIP_U_VRC}" -eq 0 ]; then pass "${PIP_U_LINE}"
          else fail "${PIP_U_LINE}" "an unpinned 3.15 install must refuse, not fall back to an older release (yank, 235.2)"; fi
        fi
        ABORT=1
      else
        run_readme_cmd "${AS_RUN}" || {
          fail "pip install failed: ${AS_RUN}" "see commands.log"
          diverge "line ${LN}: ${TEXT} failed on a clean ${Q_LEG}"; ABORT=1; }
      fi ;;

    quirk\ serve*)
      disposition "${LN}" "ran-substituted" "${TEXT}"
      say "SUBSTITUTED: ${LN} | ${TEXT} -> quirk serve in the background after the scan | the dashboard has no scan data until the scan finishes, and the harness must keep control of the shell" ;;

    quirk\ init*)
      disposition "${LN}" "ran-as-written" "${TEXT}"
      if run_readme_cmd "${TEXT}"; then rewrite_targets "${LN}"
      else fail "quirk init failed" "see commands.log"; diverge "line ${LN}: ${TEXT} failed"; fi ;;

    quirk\ --config*)
      disposition "${LN}" "ran-as-written" "${TEXT}"
      if [ "${REWRITTEN}" -eq 0 ]; then
        fail "scan reached before targets were set" "README order: init, edit targets, scan"
      elif run_readme_cmd "${TEXT}"; then SCAN_DONE=1
      else fail "scan exited non-zero" "see commands.log"; fi ;;

    git\ clone*)
      disposition "${LN}" "ran-substituted" "${TEXT}"
      say "SUBSTITUTED: ${LN} | ${TEXT} -> already cloned by the driver at ${Q_SOURCE_VALUE} | the README clones the default branch; the leg must test the ref under review (see CLONE_HEAD in the header)" ;;

    *)
      disposition "${LN}" "ran-as-written" "${TEXT}"
      run_readme_cmd "${TEXT}" || { fail "command failed: ${TEXT}" "see commands.log"; diverge "line ${LN}: ${TEXT} failed"; } ;;
  esac
done <"${TSV}"

if [ "${NEG}" -eq 1 ]; then
  # NEW-2: a negative leg whose README install line never matched ran no check N.
  if [ "${N_RAN}" -eq 0 ]; then check "N. Python 3.15 is refused by Requires-Python"; fail "check N never ran" "the README install line was not matched on the negative leg"; fi
  if [ "${N2_RAN}" -eq 0 ]; then check "N2. unpinned resolve selects no older quirk-scanner"; fail "check N2 never ran" "the README install line was not matched on the negative leg"; fi
fi
if [ "${NEG}" -eq 1 ] || [ "${ABORT}" -eq 1 ]; then finish; fi

# --------------------------------------------------------------------------
# Outcome checks
# --------------------------------------------------------------------------
check "1. quirk --version"
VER_OUT="$(quirk --version 2>&1)"
if [ -n "${Q_EXPECTED_VERSION:-}" ] && printf '%s' "${VER_OUT}" | grep -qF "${Q_EXPECTED_VERSION}"; then
  pass "${VER_OUT}"
else
  fail "version output '${VER_OUT}' does not contain '${Q_EXPECTED_VERSION:-?}'" "install resolved a different version than the artifact under test"
fi

check "2. quirk doctor exits 0"
quirk doctor >"${Q_OUT}/doctor.txt" 2>&1; DOC_RC=$?
sed 's/^/    | /' "${Q_OUT}/doctor.txt" >>"${LOG}"
[ "${DOC_RC}" -eq 0 ] && pass "doctor exit 0" || fail "doctor exit ${DOC_RC}" "a fresh install must not fail its own health check"

check "3. chaos-lab scan"
if [ ! -f config.yaml ]; then
  say "harness-run (not in this block): quirk init"
  quirk init >>"${CMDLOG}" 2>&1 || fail "quirk init failed"
fi
[ "${REWRITTEN}" -eq 0 ] && [ -f config.yaml ] && rewrite_targets "harness"
if [ "${SCAN_DONE}" -eq 0 ]; then
  say "harness-run (not in this block): quirk --config config.yaml"
  if run_readme_cmd "quirk --config config.yaml"; then SCAN_DONE=1; fi
fi
INTEL=""
for f in $(find . -name 'intelligence-*.json' -not -path './.venv/*' -print 2>/dev/null); do
  if [ -z "${INTEL}" ] || [ "${f}" -nt "${INTEL}" ]; then INTEL="${f}"; fi
done
if [ "${SCAN_DONE}" -eq 1 ] && [ -n "${INTEL}" ]; then
  OUTD="$(dirname "${INTEL}")"
  pass "scan completed; newest intelligence file ${INTEL}"
else
  fail "scan did not complete or wrote no intelligence file" "see commands.log"
  OUTD=""
fi

check "4. HTML report"
HTML=""; STAMP=""
if [ -n "${OUTD}" ]; then
  STAMP="$(basename "${INTEL}" .json)"; STAMP="${STAMP#intelligence-}"
  HTML="${OUTD}/report-${STAMP}.html"
  [ -s "${HTML}" ] && pass "$(basename "${HTML}") $(wc -c <"${HTML}" | tr -d ' ') bytes" || fail "no report-${STAMP}.html"
else
  skip "no scan output"
fi

check "5. PDF report (chromium launch probe first)"
if python - <<'PY' >"${Q_OUT}/chromium-probe.txt" 2>&1
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch()
    b.close()
PY
then
  pass "chromium launches"
else
  grep -E "Error|doesn't exist|not found" "${Q_OUT}/chromium-probe.txt" | head -3 | cut -c1-240 | sed 's/^/    | /' >>"${LOG}"
  fail "chromium will not launch" "PDF export silently produces nothing (full probe output: chromium-probe.txt)"
  diverge "the README steps did not leave a launchable chromium on ${Q_LEG}"
fi
PDF="${OUTD:+${OUTD}/report-${STAMP}.pdf}"
if [ -n "${PDF}" ] && [ -f "${PDF}" ]; then
  PSIZE="$(wc -c <"${PDF}" | tr -d ' ')"; PMAGIC="$(head -c 4 "${PDF}")"
  if [ "${PMAGIC}" = "%PDF" ] && [ "${PSIZE}" -gt 1000 ]; then pass "$(basename "${PDF}") ${PSIZE} bytes, %PDF magic"
  else fail "$(basename "${PDF}") ${PSIZE} bytes, magic '${PMAGIC}'"; fi
else
  fail "no report PDF was written" "the scan exits 0 without a PDF when chromium is unusable"
  diverge "scan completed and wrote other artifacts, but no PDF"
fi

check "6. quirk serve answers"
UP=0; PORT_BUSY=0
if port_in_use "${PORT}"; then
  PORT_BUSY=1
  fail "port ${PORT} already in use; refusing to probe a foreign server" "pick a free Q_PORT; the probe must reach OUR dashboard"
elif [ -f config.yaml ]; then
  quirk serve --port "${PORT}" >"${Q_OUT}/serve.log" 2>&1 &
  SERVE_PID=$!
  UP=0
  for _ in $(seq 1 30); do
    if python - "${PORT}" <<'PY' >/dev/null 2>&1
import sys, urllib.request
urllib.request.urlopen("http://127.0.0.1:%s/api/scan/latest" % sys.argv[1], timeout=3).read()
PY
    then UP=1; break; fi
    sleep 1
  done
  if [ "${UP}" -eq 1 ] && ! kill -0 "${SERVE_PID}" 2>/dev/null; then
    UP=0; fail "quirk serve exited; the probe answered from another process" "see serve.log"
  elif [ "${UP}" -eq 1 ]; then pass "dashboard answering on 127.0.0.1:${PORT}"
  else fail "dashboard did not answer within 30s" "see serve.log"; fi
else
  UP=0; fail "no config.yaml to serve from"
fi

check "7. /fonts serve JetBrains Mono as font/ttf"
if [ "${UP}" -eq 1 ]; then
  python - "${PORT}" "${Q_OUT}" <<'PY' >"${Q_OUT}/fonts.txt" 2>&1
import re, sys, urllib.request, pathlib
port, out = sys.argv[1], pathlib.Path(sys.argv[2])
base = "http://127.0.0.1:%s" % port
def get(path):
    r = urllib.request.urlopen(base + path, timeout=10)
    return r.status, r.headers.get("content-type", ""), r.read()
_, _, index = get("/")
index = index.decode("utf-8", "replace")
css_paths = re.findall(r'href="(/assets/[^"]+\.css)"', index)
if not css_paths:
    print("FAIL no CSS asset linked from index.html"); sys.exit(1)
css = ""
for p in css_paths:
    css += get(p)[2].decode("utf-8", "replace")
fonts = sorted(set(re.findall(r"url\((/fonts/[^)\s]+)\)", css)))
if len(fonts) < 2:
    print("FAIL expected regular and italic font URLs, got", fonts); sys.exit(1)
bad = 0
for u in fonts:
    status, ctype, body = get(u)
    ok = status == 200 and ctype.split(";")[0].strip() == "font/ttf" \
        and body[:4] == b"\x00\x01\x00\x00"
    print(("ok   " if ok else "FAIL ") + u, status, ctype, body[:4].hex())
    bad += 0 if ok else 1
m = re.search(r"--ds-accent:\s*(#[0-9a-fA-F]{3,8})", css)
(out / "brand-accent.txt").write_text((m.group(1) if m else "NOT FOUND") + "\n")
print("BRAND --ds-accent:", m.group(1) if m else "NOT FOUND")
sys.exit(1 if bad else 0)
PY
  FONT_RC=$?
  sed 's/^/    | /' "${Q_OUT}/fonts.txt" >>"${LOG}"
  [ "${FONT_RC}" -eq 0 ] && pass "every /fonts URL: 200, font/ttf, TrueType magic" || fail "font route contract broken" "see fonts.txt"
else
  fail "dashboard not up; font contract unchecked"
fi

check "8. score parity (intel == html strictly; dashboard == report or attributed)"
if [ "${UP}" -eq 1 ] && [ -n "${HTML}" ] && [ -s "${HTML}" ]; then
  python - "${PORT}" "${Q_OUT}/scan-latest.json" <<'PY' || fail "could not fetch /api/scan/latest"
import sys, urllib.request
r = urllib.request.urlopen("http://127.0.0.1:%s/api/scan/latest" % sys.argv[1], timeout=20)
open(sys.argv[2], "wb").write(r.read())
PY
  HSCORE="$(python - "${HTML}" <<'PY'
import re, sys
t = open(sys.argv[1], encoding="utf-8").read()
m = re.search(r'<div class="score-value">\s*([0-9.]+)\s*</div>', t)
print(m.group(1) if m else "")
PY
)"
  if [ -z "${HSCORE}" ]; then
    fail "no numeric headline score in the HTML report" "the scan produced no assessable domains (is the chaos lab up and reachable at the targets?) or the score block changed"
  else
    FJSON="${OUTD}/findings-${STAMP}.json"
    ARGS=(--dashboard-json "${Q_OUT}/scan-latest.json" --intel-json "${INTEL}" --html-score "${HSCORE}")
    [ -f "${FJSON}" ] && ARGS+=(--findings-json "${FJSON}")
    [ -n "${Q_DIVERGENCE_SET:-}" ] && [ -f "${Q_DIVERGENCE_SET}" ] && ARGS+=(--divergence-set "${Q_DIVERGENCE_SET}")
    python "${Q_SCORE_ATTR}" "${ARGS[@]}" >"${Q_OUT}/score-attribution.txt" 2>&1
    SA_RC=$?
    cat "${Q_OUT}/score-attribution.txt" >>"${LOG}"
    [ "${SA_RC}" -eq 0 ] && pass "score_attribution.py exit 0" || fail "score_attribution.py exit ${SA_RC}" "see the SCORE-* and UNATTRIBUTED lines above"
  fi
else
  fail "dashboard or HTML report unavailable; score parity unchecked"
fi

check "9. brand accent recorded for the visual walkthrough"
if [ -f "${Q_OUT}/brand-accent.txt" ] && ! grep -q "NOT FOUND" "${Q_OUT}/brand-accent.txt"; then
  pass "--ds-accent $(cat "${Q_OUT}/brand-accent.txt")"
else
  fail "--ds-accent not found in the served CSS" "the bundle is missing the brand token"
fi

cleanup; SERVE_PID=""
finish
