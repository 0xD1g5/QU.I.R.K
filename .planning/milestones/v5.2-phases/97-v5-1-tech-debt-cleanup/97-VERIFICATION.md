---
phase: 97-v5-1-tech-debt-cleanup
verified: 2026-05-23T00:00:00Z
status: passed
score: 7/7 must-haves verified
overrides_applied: 0
gaps: []
deferred: []
human_verification: []
---

# Phase 97: v5.1 Tech-Debt Cleanup — Verification Report

**Phase Goal:** The v5.1 carry-over design-judgment issues are corrected so the codebase entering the report milestone is sound.
**Verified:** 2026-05-23
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `from_cli` docstring matches actual `ref in os.environ` behavior — no "all-caps" claim | VERIFIED | `credentials.py:137` contains `"any name present in the environment (D-01)"`. `grep -qi "all-caps"` returns no match. |
| 2 | `as_headers` and `query_param` each carry a D-05 proliferation comment documenting the accepted per-call str-copy and once-per-endpoint-per-scan bound | VERIFIED | Lines 58-61 (`as_headers`) and 80-83 (`query_param`) both contain `D-02/D-05` comment blocks with explicit call-bound statement. Token `D-05` present in both. |
| 3 | `_append_query_param` rejects a URL already carrying a same-named key param with a scrubbed message; the remaining targets still process | VERIFIED | `jwt_scanner.py:76-87` iterates `existing` keys, checks `_KEY_PARAM_NAMES`, emits `logger.warning(..., safe_str(url))` and raises `ValueError`. Caller `_fetch_jwks` catches via broad `except Exception: continue` — one rejection does not abort the loop. 4 tests in `test_jwt_scanner.py` cover reject, no-leak, continue-iteration, and happy-path. |
| 4 | The scheduler auth-reject parses any existing config file (not only `.yml/.yaml`) and fails closed — an authenticated config at an unconventional path is rejected; unparseable/non-dict files also rejected | VERIFIED | `schedule_cmd.py:33` extension gate is absent (`grep endswith(".yml"` returns nothing). Lines 43-74 implement: `os.path.exists` guard, SQLite magic carve-out, `yaml.safe_load`, non-dict → `return True`, `except Exception: return True`. 5 tests in `test_schedule_auth_reject.py` (4 from plan + SQLite carve-out regression). |
| 5 | The REST fuzzer cascade counter (`consecutive_failures`) increments on connection/request exceptions and resets only on genuine success | VERIFIED | `rest_fuzzer.py:497` initialises `consecutive_failures = 0`. Exception branch (line 616) `consecutive_failures += 1` with limit check (617) and break (622). Success path (line 639) `consecutive_failures = 0`. Single constant `_CONSECUTIVE_5XX_LIMIT` confirmed (8 occurrences, no second constant). |
| 6 | At least one sentinel leak test exercises the real scanner/scrub path — safe_str applied by production code, not the test body | VERIFIED | `test_credential_leakage.py:145-185` — `test_sentinel_not_in_scan_error_json` mocks `socket.create_connection`, calls real `_scan_one_fallback`, asserts `SENTINEL not in json.dumps(...)`. No `safe_str` call in the test body. Docstring explicitly states "REAL-PATH TEST." |
| 7 | The PDF-export leak test is marked as a documented coverage gap | VERIFIED | `test_credential_leakage.py:330-343` — `test_sentinel_not_in_pdf_export_surface` docstring opens with "DOCUMENTED COVERAGE GAP (D-04 / WR-05)" and explains no live Playwright render is performed. |

**Score:** 7/7 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `quirk/auth/credentials.py` | Corrected `from_cli` docstring (D-01) + D-02 proliferation comments at both decode sites | VERIFIED | File exists, substantive, wired. Commits `04e5b57` and `b30abf6`. |
| `quirk/scanner/rest_fuzzer.py` | Combined `consecutive_failures` counter covering 5xx AND request/connection exceptions | VERIFIED | File exists, substantive. `consecutive_failures` at 5 sites; increment-on-exception at line 616; single `_CONSECUTIVE_5XX_LIMIT`. Commits `d6dde4b`. |
| `tests/test_rest_fuzzer_cascade.py` | Regression test proving exception-only cascade trips the pause | VERIFIED | File exists with 3 tests: exception-only cascade, success-reset, 5xx-no-regression. 261 lines, substantive. |
| `quirk/scanner/jwt_scanner.py` | `_append_query_param` pre-existing-param guard (D-03) | VERIFIED | File exists. Guard at lines 76-87 references `_KEY_PARAM_NAMES`, logs `safe_str(url)`, raises `ValueError`. Commits `c5bd617`. |
| `quirk/cli/schedule_cmd.py` | Parse-based, fail-closed `_config_has_authenticated_mode` (D-05) | VERIFIED | File exists. Extension gate removed. `os.path.exists` + SQLite carve-out + `yaml.safe_load` + fail-closed branches at lines 40-74. Commits `8057260` + `298704d` (post-merge SQLite regression fix). |
| `tests/test_jwt_scanner.py` | Pre-existing-param reject + continue-iteration tests | VERIFIED | File exists, 4 new tests covering D-03 behaviors. |
| `tests/test_schedule_auth_reject.py` | Extensionless-config + unparseable-config fail-closed tests | VERIFIED | File exists with 5 tests (4 planned + SQLite carve-out). |
| `tests/test_credential_leakage.py` | Real-path sentinel surface + PDF coverage-gap annotation (D-04) | VERIFIED | File exists. `test_sentinel_not_in_scan_error_json` is real-path; `test_sentinel_not_in_pdf_export_surface` annotated as coverage gap. |
| `docs/UAT-SERIES.md` | Updated UAT series + last-updated 2026-05-23 | VERIFIED | `**Last Updated:**` line 4 shows 2026-05-23 with Phase 97 detail. UAT-97-01..04 series at lines 10976+. |
| `Phases/Phase-97-v5.1-Tech-Debt-Cleanup.md` (vault) | Obsidian phase note with `status: complete` | VERIFIED | File exists at `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-97-v5.1-Tech-Debt-Cleanup.md`. Frontmatter `status: complete`. |
| `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md` (vault) | UAT vault sync | VERIFIED | File exists. |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `rest_fuzzer.py` exception branch | `_CONSECUTIVE_5XX_LIMIT` cascade break | `consecutive_failures +=` at line 616, check at 617 | WIRED | Both increment and limit check confirmed in the exception handler. |
| `jwt_scanner._append_query_param` reject | caller target-list iteration in `_fetch_jwks` | `ValueError` caught by existing `except Exception: continue` (line ~216) | WIRED | D-03 reject raises `ValueError`; existing broad handler continues iteration — one rejection does not abort. |
| `schedule_cmd._config_has_authenticated_mode` | scheduler `sys.exit(2)` | `return True` on fail-closed branches | WIRED | Function returns `True` for auth or unclassifiable configs; caller at line ~75-78 gates `sys.exit(2)` on the return value. |
| real `_scan_one_fallback` exception path | `test_sentinel_not_in_scan_error_json` assertion | `socket.create_connection` mock + real call | WIRED | Test mocks socket, calls real function, asserts on production-scrubbed `scan_error`. |

---

### Data-Flow Trace (Level 4)

Not applicable — this phase modifies no data-rendering components. All changes are: docstring/comment corrections (credentials.py), a cascade counter logic fix (rest_fuzzer.py), a query-param guard (jwt_scanner.py), a scheduler config-classification fix (schedule_cmd.py), and test-honesty improvements. No new data flows through UI rendering.

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Phase 97 test surfaces all pass | `python -m pytest tests/test_rest_fuzzer_cascade.py tests/test_jwt_scanner.py tests/test_schedule_auth_reject.py tests/test_credential_leakage.py -q` | 48 passed in 1.11s | PASS |
| Credential context tests pass (no regression) | `python -m pytest tests/test_credential_context.py -q` | 26 passed in 0.08s | PASS |
| No "all-caps" in credentials.py | `grep -qi "all-caps" quirk/auth/credentials.py` | no output (exit 1 = absent) | PASS |
| "any name present in the environment" in from_cli docstring | `grep -n "any name present in the environment" quirk/auth/credentials.py` | line 137 match | PASS |
| Extension gate removed from schedule_cmd.py | `grep "endswith.*\.yml" quirk/cli/schedule_cmd.py` | no output | PASS |
| Single `_CONSECUTIVE` constant (no second threshold) | `grep -c "_CONSECUTIVE" quirk/scanner/rest_fuzzer.py` | 8 (all references to `_CONSECUTIVE_5XX_LIMIT`, no new constant) | PASS |

---

### Probe Execution

No probe scripts declared or discoverable for this phase. Step 7c: SKIPPED (no `scripts/*/tests/probe-*.sh` files associated with this phase).

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| TD-01 | 97-01, 97-03, 97-04 | Credential env-var contract + CredentialContext per-call str-copy / `_append_query_param` overwrite behaviors corrected | SATISFIED | D-01: docstring corrected. D-02: proliferation comments added. D-03: param guard implemented. D-04/WR-05: real-path sentinel test. D-05/WR-06: fail-closed scheduler. All sub-items verified in artifacts above. |
| TD-02 | 97-02 | The 5xx cascade counter correctly trips on connection-exception failures | SATISFIED | `consecutive_failures` counter increments on exceptions at `rest_fuzzer.py:616`; 3 regression tests in `test_rest_fuzzer_cascade.py`. |

REQUIREMENTS.md traceability rows for TD-01 (line 82) and TD-02 (line 83) both map to Phase 97. Both satisfied.

---

### Anti-Patterns Found

No TBD, FIXME, or XXX markers found in any phase-97-modified file. No TODO or PLACEHOLDER markers found in production files (`quirk/auth/credentials.py`, `quirk/scanner/rest_fuzzer.py`, `quirk/scanner/jwt_scanner.py`, `quirk/cli/schedule_cmd.py`). Clean.

---

### Code Review Findings Assessment

The 97-REVIEW.md found 0 Critical / 4 Warning / 4 Info. Per the context notes, these are documented as adjacent realism gaps, not locked-scope failures. Assessment:

**WR-01 (REVIEW):** JWT fetch appends path after query string (malformed URL). Not in TD-01/TD-02 locked scope. The WR-04 guard mitigates the specific tested case. Documented for a future phase.

**WR-02 (REVIEW):** WR-04 reject silently swallowed by broad `except Exception` in `_fetch_jwks`. D-03 intent ("skip the target") is achieved — the target is skipped via the existing exception handler. The warning-level issue about caller-level distinguishability is a realism gap, not a locked requirement. D-03 as specified is satisfied.

**WR-03 (REVIEW):** Alg-confusion cascade reset on 4xx. The alg-confusion path at lines 697-700 uses `< 500` for reset (same semantics as main path). D-06 specified "reset only on a genuine success" — a 4xx is the *expected* healthy outcome for alg-confusion (server rejected forged token), which is distinct from a real operation success. This is a nuance documented in the review but does not violate D-06's intent for the main dispatch loop. The context notes explicitly classify this as a warning adjacent to scope.

**WR-04 (REVIEW):** PDF leak test docstring + module claim overstates coverage. The plan (D-04) only required: (1) annotate PDF as coverage gap, and (2) route ≥1 surface through real path. Both are done. The module-level docstring wording is a remaining cosmetic gap (also identified in review). Not a blocker for TD-01 satisfaction.

All four warnings are adjacent-realism gaps that do not invalidate the TD-01 or TD-02 deliverables.

---

### Human Verification Required

None. All must-haves are mechanically verifiable and verified. The UAT-97-01..04 test cases in `docs/UAT-SERIES.md` are available for optional operator walkthrough but are not required to confirm phase goal achievement.

---

### Gaps Summary

No gaps. All must-haves for TD-01 and TD-02 are verified:

- TD-01 (5 sub-items D-01..D-05/WR-02..WR-06): all corrected in production code with tests or documentation.
- TD-02 (D-06/WR-03): cascade counter fix implemented, three behavioral regression tests pass.
- Documentation: UAT-SERIES.md updated (2026-05-23), Obsidian phase note created, vault sync completed.
- No debt markers (TBD/FIXME/XXX) in any modified file.
- REQUIREMENTS.md traceability rows TD-01 and TD-02 correctly mapped to Phase 97.

The codebase entering the v5.2 report milestone is sound with respect to the v5.1 carry-over design-judgment issues this phase was scoped to address.

---

_Verified: 2026-05-23_
_Verifier: Claude (gsd-verifier)_
