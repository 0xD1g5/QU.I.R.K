---
phase: 96-active-rest-fuzzing
verified: 2026-05-23T00:00:00Z
status: human_needed
score: 6/6 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Run quirk scan --fuzz with piped stdin and verify hard-abort before any request"
    expected: "Clear non-TTY error, zero requests dispatched"
    why_human: "Verifier cannot start a live scan session; behavioral assertion requires an operator-controlled TTY/non-TTY scenario"
  - test: "Run quirk scan --fuzz in a TTY, type anything other than CONFIRM (e.g. 'y') and verify abort with zero requests; then type CONFIRM and verify budget summary is shown and scan proceeds"
    expected: "Only exact 'CONFIRM' proceeds; everything else aborts; no requests sent before CONFIRM"
    why_human: "Interactive TTY prompt cannot be driven programmatically in this verifier context"
  - test: "Start the fuzz-target chaos profile (PROFILE_ARGS='--profile fuzz-target' ./lab.sh up), then run: quirk scan --targets http://localhost:20100 --fuzz --openapi-spec http://localhost:20100/openapi.json --fuzz-jwt-alg-confusion; verify CRITICAL ALG_CONFUSION and HIGH HSTS_MISSING findings appear"
    expected: "At least one CRITICAL ALG_CONFUSION finding and one HIGH HSTS_MISSING finding in the scan report"
    why_human: "Requires Docker and the live fuzz-target container; verifier cannot start Docker services"
---

# Phase 96: Active REST Fuzzing Verification Report

**Phase Goal:** Users can opt in to active REST crypto-posture fuzzing (TLS downgrade, cipher, HSTS, JWT alg-confusion), gated behind an explicit CONFIRM prompt, bounded request budget, and hard non-TTY abort.
**Verified:** 2026-05-23T00:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `quirk scan --fuzz` in a TTY presents a budget summary and requires the literal word `CONFIRM`; anything else aborts with NO requests sent [FUZZ-01] | VERIFIED | `confirm_fuzz_gate` at `rest_fuzzer.py:119-173`: exact `answer == "CONFIRM"` (no strip); 22 gate tests pass including 11-case parametrized rejection suite and `test_confirm_prompt_includes_budget_and_target_count` |
| 2 | `quirk scan --fuzz` with non-TTY stdin HARD-ABORTS before sending any request, clear error [FUZZ-03] | VERIFIED | `rest_fuzzer.py:149-162`: `if not is_tty: … return False` — gate returns False before any session/socket call; `test_non_tty_hard_abort_zero_requests` asserts `session_mock.request.call_count == 0` and `test_non_tty_hard_abort_returns_false_no_prompt` confirms prompt_fn never called |
| 3 | Fuzzer pauses+warns after 3 consecutive 5xx; total request count NEVER exceeds the budget (default 50, hard max 500) [FUZZ-02] | VERIFIED | `rest_fuzzer.py:562-616`: `consecutive_5xx` tracker breaks at `_CONSECUTIVE_5XX_LIMIT=3`; TLS/cipher socket probes hoisted pre-loop (CR-02 fix), each consuming one budget unit at lines 531-554; alg-confusion request gated by `budget_used < effective_budget` (line 654) and incremented at line 672 (CR-01 fix); `TestBudgetCeilingBoundsAllTraffic.test_socket_probes_run_once_and_count_budget` green — see WARNING below |
| 4 | `quirk scan --fuzz --fuzz-jwt-alg-confusion` sends the RS256→HS256 probe and produces a CRITICAL finding when the server accepts the forged token [FUZZ-04] | VERIFIED | `_forge_hs256_token` at `rest_fuzzer.py:271-334`: returns bytes for RS256, None for non-RS256; JWKS fetch then alg-confusion dispatch at lines 649-692; `test_alg_confusion_accepted_is_critical` and `test_alg_confusion_skips_non_rs256` both pass |
| 5 | SCORE_WEIGHTS sum 303.0 and count 41; `test_score_weights_invariant.py` green; schemathesis absent from `quirk[all]` and `test_install_all_excludes_schemathesis.py` enforces it [SCORE-01] | VERIFIED | `sum(SCORE_WEIGHTS.values()) == 303.0`, `len(SCORE_WEIGHTS) == 41` (confirmed by runtime check); both invariant tests pass; `test_install_api_includes_schemathesis` (new) and `test_install_all_excludes_schemathesis` (original) both green |
| 6 | New fuzz-target chaos profile with expected_results + README updated [LAB-01] | VERIFIED | `quantum-chaos-enterprise-lab/fuzz-target/` dir exists with Dockerfile, main.py, requirements.txt; `docker-compose.yml` has `profiles: ["fuzz-target"]` on port 20100; `expected_results_v4.md` has `## Profile: fuzz-target` section with four probe findings; `README.md` has fuzz-target row referencing port 20100 |

**Score:** 6/6 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `quirk/scanner/rest_fuzzer.py` | confirm_fuzz_gate, _resolve_budget, run_fuzz_scan, _forge_hs256_token | VERIFIED | All symbols present; exact-CONFIRM gate (no strip); non-TTY HARD ABORT; budget ceiling 500; six guardrails implemented |
| `tests/test_rest_fuzzer_gate.py` | 22 gate + budget unit tests | VERIFIED | 22 tests pass; `call_count == 0` for non-TTY path |
| `tests/test_rest_fuzzer_probes.py` | Dispatch + probe + alg-confusion tests | VERIFIED | 21 tests pass (43 total including gate tests after deselect) |
| `tests/test_score_weights_invariant.py` | Sum 303.0, count 41 assertions | VERIFIED | Both assertions match; Phase 96 delta documented in test docstring |
| `tests/test_cbom_rest_fuzz_no_tls_component.py` | Zero crypto/protocol/tls/* for REST_FUZZ endpoints | VERIFIED | 4 tests pass |
| `tests/test_install_all_excludes_schemathesis.py` | schemathesis in [api], absent from [all] | VERIFIED | Both tests pass (new + original) |
| `run_scan.py` | --fuzz, --fuzz-jwt-alg-confusion, --fuzz-budget flags + _run_fuzz_phase | VERIFIED | All three flags in argparse; `_run_fuzz_phase` wired via `_wrapped_phase`; `is_tty=sys.stdin.isatty()` passed through |
| `quirk/intelligence/evidence.py` | REST_FUZZ in _PROTOCOL_KEYS, fuzz_finding_count, agility_fuzz_crypto_posture_ratio | VERIFIED | All three present; CRITICAL/HIGH only count; INFO excluded |
| `quirk/intelligence/scoring.py` | agility_fuzz_crypto_posture_ratio: 4.0 | VERIFIED | Weight present; agility impact appended at line 248 |
| `quirk/cbom/builder.py` | REST_FUZZ in Pass-2 and Pass-3 skip tuples | VERIFIED | Lines 682 (Pass-2) and 881 (Pass-3) both have "REST_FUZZ" |
| `quantum-chaos-enterprise-lab/fuzz-target/main.py` | Routes /openapi.json, /probe, /.well-known/jwks.json, no HSTS | VERIFIED | All three routes present; `grep -c strict-transport-security` returns 0 |
| `quantum-chaos-enterprise-lab/expected_results_v4.md` | ## Profile: fuzz-target section | VERIFIED | Section at line 847 with all four probe/findings rows |
| `docs/configuration.md` | REST Fuzzing section with all flags, guardrails, non-TTY abort | VERIFIED | --fuzz, --fuzz-jwt-alg-confusion, --fuzz-budget, CONFIRM, non-TTY hard-abort, "hard max 500", six guardrails all present |
| `docs/UAT-SERIES.md` | UAT-96-01..08 | VERIFIED | 10 UAT-96 references; UAT Series 96 section complete |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `run_scan.py` | `quirk.scanner.rest_fuzzer.run_fuzz_scan` | `_run_fuzz_phase` at line 1466 | WIRED | `run_fuzz_scan` imported and called with `is_tty=sys.stdin.isatty()` |
| `run_scan.py` | `confirm_fuzz_gate` | Internally via `run_fuzz_scan` (single gate call) | WIRED | CLI passes `is_tty` and `prompt_fn=input` through; gate called once inside `run_fuzz_scan` |
| `quirk/intelligence/scoring.py` | `evidence fuzz_finding_count` | `agility_impacts` append at line 248 | WIRED | `-_ratio(fuzz_findings, denom) * w["agility_fuzz_crypto_posture_ratio"]` |
| `quirk/cbom/builder.py` | REST_FUZZ skip | Pass-2 (line 682) + Pass-3 (line 881) tuples | WIRED | Phantom `crypto/protocol/tls/*` CBOM components prevented |
| `tests/test_rest_fuzzer_gate.py` | `quirk.scanner.rest_fuzzer` | `from quirk.scanner.rest_fuzzer import` | WIRED | Imports `confirm_fuzz_gate`, `_resolve_budget`, `MAX_FUZZ_BUDGET` |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|--------------------|--------|
| `run_fuzz_scan` (rest_fuzzer.py) | `findings` list | schemathesis spec parse + session.request | Yes — dispatched HTTP responses + socket probe results | FLOWING |
| `quirk/intelligence/evidence.py` | `fuzz_finding_count` | REST_FUZZ endpoints with severity CRITICAL/HIGH from DB | Yes — live endpoint severity filter | FLOWING |
| `quirk/intelligence/scoring.py` | agility_fuzz impact | `fuzz_finding_count` from evidence dict | Yes — computed ratio | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| --fuzz flags visible in CLI help | `.venv/bin/python run_scan.py --help \| grep -E "\-\-fuzz"` | `--fuzz`, `--fuzz-jwt-alg-confusion`, `--fuzz-budget N` all listed | PASS |
| SCORE_WEIGHTS sum 303.0, count 41 | `.venv/bin/python -c "from quirk.intelligence.scoring import SCORE_WEIGHTS; print(sum(SCORE_WEIGHTS.values()), len(SCORE_WEIGHTS))"` | `303.0 41` | PASS |
| Gate tests all green (22 tests) | `.venv/bin/python -m pytest tests/test_rest_fuzzer_gate.py -q` | `22 passed` | PASS |
| Probe tests all green | `.venv/bin/python -m pytest tests/test_rest_fuzzer_probes.py -q` | `43 passed, 1 deselected` | PASS |
| Score weights invariant | `.venv/bin/python -m pytest tests/test_score_weights_invariant.py -q` | `2 passed` | PASS |
| schemathesis inclusion/exclusion guard | `.venv/bin/python -m pytest tests/test_install_all_excludes_schemathesis.py -q` | `1 passed, 1 deselected` (new test selected only; both pass when run together) | PASS |
| CBOM REST_FUZZ no-TLS component | `.venv/bin/python -m pytest tests/test_cbom_rest_fuzz_no_tls_component.py -q` | `4 passed` | PASS |
| Budget ceiling regression (CR-02) | `.venv/bin/python -m pytest tests/test_rest_fuzzer_probes.py::TestBudgetCeilingBoundsAllTraffic -v` | `1 passed` (socket probes run once, counted, total <= budget) | PASS |
| fuzz-target in docker-compose | `grep -q "fuzz-target" quantum-chaos-enterprise-lab/docker-compose.yml && echo OK` | `OK` | PASS |
| expected_results_v4.md oracle | `grep -q "## Profile: fuzz-target" quantum-chaos-enterprise-lab/expected_results_v4.md && echo OK` | `OK` | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|------------|------------|-------------|--------|---------|
| FUZZ-01 | 96-01, 96-02, 96-03 | Opt-in REST fuzzing with gate + budget | SATISFIED | CLI flag, CONFIRM gate, TLS/cipher/HSTS/http-cred probes, 5xx pause |
| FUZZ-02 | 96-01, 96-02, 96-03 | Six safety guardrails | SATISFIED | GET-only, budget ceiling 500, rate 5 req/s, CONFIRM, scope gate, 5xx cascade — all implemented and tested |
| FUZZ-03 | 96-01, 96-03 | Non-TTY hard-abort | SATISFIED | `confirm_fuzz_gate` returns False + prints error in non-TTY; zero requests dispatched (asserted by test) |
| FUZZ-04 | 96-02, 96-03 | JWT alg-confusion probe | SATISFIED | `_forge_hs256_token`, `_fetch_jwks_public_key_pem`, CRITICAL finding on 2xx acceptance |
| SCORE-01 | 96-03 (final) | Fuzzing signals in agility_signals | SATISFIED | `agility_fuzz_crypto_posture_ratio: 4.0` in SCORE_WEIGHTS; sum 303.0/41; evidence counter wired |
| LAB-01 | 96-04 (final) | Chaos lab fuzz-target profile | SATISFIED | fuzz-target service, expected_results_v4.md oracle, README row all present |

**REQUIREMENTS.md tracking gap (orchestrator action required):** FUZZ-01, FUZZ-02, FUZZ-03, FUZZ-04 remain `[ ]` and "Pending" in `.planning/REQUIREMENTS.md` lines 48-51, 107-110. SCORE-01 (line 61, 101) and LAB-01 (line 63, 106) also remain "Pending". All six requirements are fully implemented and verified — these are administrative tracking rows that must be flipped to `[x]` / "Complete" by the orchestrator as part of phase close-out.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `tests/test_rest_fuzzer_gate.py` | ~90,98 | Comment/docstring says "`.strip()` is done on answer" but `confirm_fuzz_gate` deliberately does NOT strip — exact equality enforced | INFO (IN-02 from code review) | Misleading comment for future contributors; tests pass correctly because `"CONFIRM " != "CONFIRM"`. No functional defect. |
| `quirk/intelligence/scoring.py` | 8 | Module docstring says "sum is 275.0" but actual sum is 303.0 | INFO (IN-01 from code review) | Stale comment; invariant test correctly asserts 303.0 |
| `run_scan.py` | 1449 | `base_url` defaults to `https://localhost` when no FQDNs configured | INFO (IN-03 from code review) | Silent localhost default for `--fuzz` run with no FQDN target; scope gate still applies. Not a DoS risk but surprising behavior. |
| `tests/test_rest_fuzzer_probes.py::TestBudgetCeilingBoundsAllTraffic` | 659-692 | Only one test in the regression class; covers CR-02 (socket probes counted once) but does NOT include a dedicated test for CR-01 (alg-confusion request counted against budget when `run_alg_confusion=True`) | WARNING | CR-01 fix is code-verified (lines 654+672 of rest_fuzzer.py) but has no dedicated regression test exercising the path with `run_alg_confusion=True` and asserting total dispatched count <= budget. The existing `test_alg_confusion_accepted_is_critical` test does not assert budget accounting. |

**Debt-marker check:** No TBD, FIXME, or XXX markers found in phase-modified files.

### Human Verification Required

#### 1. TTY CONFIRM Gate (FUZZ-01, FUZZ-03)

**Test:** Start an interactive `quirk scan --fuzz --openapi-spec <spec> --targets <target>` session. First try typing something other than `CONFIRM` (e.g. "y", "yes", bare Enter). Verify the scan aborts with a clear message and no requests are sent. Then restart and type exactly `CONFIRM` and verify the scan proceeds.
**Expected:** Only the exact string `CONFIRM` proceeds; all other inputs abort cleanly with zero active requests dispatched.
**Why human:** Interactive TTY prompt flow cannot be driven by the automated verifier.

#### 2. Non-TTY Hard-Abort (FUZZ-03)

**Test:** `echo "" | .venv/bin/python run_scan.py --targets localhost --openapi-spec /tmp/test.json --fuzz 2>&1` (or equivalent piped stdin). Verify a clear non-TTY error is printed and the process exits without sending any active requests.
**Expected:** Error message mentioning "non-TTY" or "non-interactive"; exit before any fuzz dispatch; zero HTTP requests to the target.
**Why human:** Verifier cannot observe network I/O in a live scan invocation.

#### 3. Live alg-confusion probe against fuzz-target (FUZZ-04, LAB-01)

**Test:**
1. `PROFILE_ARGS="--profile fuzz-target" ./lab.sh up` (wait for container healthy)
2. `quirk scan --targets http://localhost:20100 --fuzz --openapi-spec http://localhost:20100/openapi.json --fuzz-jwt-alg-confusion` (type CONFIRM when prompted)
3. Inspect findings output for `CRITICAL … alg_confusion` and `HIGH … hsts_missing`
**Expected:** At minimum a CRITICAL `alg_confusion` finding (server accepted forged HS256 token at `/probe`) and a HIGH `hsts_missing` finding (no Strict-Transport-Security header on any response).
**Why human:** Requires Docker, a live fuzz-target container, and interactive CONFIRM — cannot be automated without starting services.

---

## Gaps Summary

No code gaps found. All six success criteria are verified against the actual codebase. The following are the only open items:

1. **WARNING — CR-01 regression coverage incomplete:** The `TestBudgetCeilingBoundsAllTraffic` test class covers the CR-02 fix (socket probes hoisted, counted) but has no dedicated test asserting that `run_alg_confusion=True` with `N` operations results in total dispatched calls `<= budget`. The code at lines 654 and 672 is correct, but the regression test gap means a future refactor could reopen CR-01 undetected. Recommended follow-up: add a second test to `TestBudgetCeilingBoundsAllTraffic` that passes `run_alg_confusion=True` and asserts `session_mock.request.call_count <= budget`.

2. **ORCHESTRATOR ACTION — REQUIREMENTS.md not updated:** FUZZ-01, FUZZ-02, FUZZ-03, FUZZ-04, SCORE-01, LAB-01 remain `[ ]` / "Pending" in `.planning/REQUIREMENTS.md`. These must be flipped to `[x]` / "Complete" as part of phase close-out.

3. **Human verification:** Three live behavioral checks require operator confirmation (items 1-3 in the Human Verification section above).

---

_Verified: 2026-05-23T00:00:00Z_
_Verifier: Claude (gsd-verifier)_
