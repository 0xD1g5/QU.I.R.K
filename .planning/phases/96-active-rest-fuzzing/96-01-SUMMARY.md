---
phase: 96-active-rest-fuzzing
plan: "01"
subsystem: scanner/fuzzer + packaging + tests
tags: [rest-fuzzer, schemathesis, confirm-gate, non-tty-abort, budget-ceiling, tdd, fuzz-02, fuzz-03, pkg-01]
dependency_graph:
  requires: [phase-94-openapi-scanner, phase-93-ephemeral-creds]
  provides: [quirk.scanner.rest_fuzzer, confirm_fuzz_gate, _resolve_budget, MAX_FUZZ_BUDGET]
  affects: [pyproject.toml, tests/test_install_all_excludes_schemathesis.py]
tech_stack:
  added: [schemathesis>=4.4.4 (via [api] extras)]
  patterns: [TDD RED/GREEN, injectable prompt_fn/stderr_print_fn, Final[int] constants, try/except optional-dep guard]
key_files:
  created:
    - quirk/scanner/rest_fuzzer.py
    - tests/test_rest_fuzzer_gate.py
  modified:
    - pyproject.toml
    - tests/test_install_all_excludes_schemathesis.py
decisions:
  - "confirm_fuzz_gate does NOT use .strip() on the answer — CONFIRM with trailing/leading space is rejected per FUZZ-03 spec (test-first contract)"
  - "schemathesis 4.19.0 installed (satisfies >=4.4.4 pin); as_transport_kwargs() verified available"
  - "No dispatch code in rest_fuzzer.py — Plan 02 owns run_fuzz_scan and probe loop"
metrics:
  duration: "4 minutes"
  completed: "2026-05-23"
  tasks_completed: 2
  files_changed: 4
  commits: 3
---

# Phase 96 Plan 01: schemathesis [api] install + CONFIRM gate + budget ceiling (TDD) Summary

Wave 0 infrastructure: installed schemathesis into the `[api]` extras group, extended the PKG-01 CI guard, then built the REST fuzz safety gate layer test-first with zero dispatch code.

## What Was Built

### Task 1: schemathesis in [api] + extended CI guard

Added `schemathesis>=4.4.4` to the `[api]` optional-dependencies group in `pyproject.toml` (after `openapi-spec-validator>=0.9.0`) with an inline comment marking it `[api] only, NOT [all]`. Installed schemathesis 4.19.0 (satisfying the `>=4.4.4` pin) into the project venv via `pip install -e ".[api]"`.

Extended `tests/test_install_all_excludes_schemathesis.py` by adding `test_install_api_includes_schemathesis` — a fast, deterministic test that reads `pyproject.toml` via `tomllib` and asserts schemathesis IS present in `[api]`. The existing `test_install_all_excludes_schemathesis` body is unchanged (PKG-01 guard preserved).

**Acceptance verified:**
- `pyproject.toml` [api] contains `schemathesis>=4.4.4`
- `pyproject.toml` [all] does NOT contain `schemathesis`
- `python -c "import schemathesis; from schemathesis.core.result import Ok"` exits 0
- Both guard tests pass

### Task 2: Test-first CONFIRM gate + non-TTY hard abort + budget ceiling (TDD)

**RED phase (commit d920e87):** `tests/test_rest_fuzzer_gate.py` written before any implementation. 22 tests covering:
- `test_non_tty_hard_abort_zero_requests`: asserts `session_mock.request.call_count == 0` after `confirm_fuzz_gate(is_tty=False)` returns False
- `test_non_tty_hard_abort_returns_false_no_prompt`: asserts `prompt_fn` is never called in non-TTY path
- `test_confirm_required_exact_string_rejects_bad_input` (parametrized, 11 cases): rejects "y", "yes", "confirm", "", " ", "CONFIRM " (trailing space), "CONFIRM\n", "YES", "ok", "1", "true"
- `test_confirm_required_exact_string_accepts_confirm`: returns True for exact "CONFIRM"
- `test_confirm_prompt_includes_budget_and_target_count`: prompt text includes budget and target_count values
- `test_budget_hard_ceiling_raises_on_501`: `_resolve_budget(501)` raises `ValueError(match="hard maximum")`
- `test_budget_hard_ceiling_accepts_500`, `test_budget_none_resolves_to_default`, `test_budget_default_resolves_correctly`, `test_budget_max_constant_is_500`, `test_budget_raises_for_various_overflows`

All tests failed with `ModuleNotFoundError` (correct RED).

**GREEN phase (commit 2195ce3):** `quirk/scanner/rest_fuzzer.py` created with gate-layer only:
- `MAX_FUZZ_BUDGET: Final[int] = 500`, `DEFAULT_FUZZ_BUDGET = 50`, `FUZZ_RATE_DEFAULT = 5.0`
- `_resolve_budget(requested)`: raises `ValueError("...hard maximum...")` when `effective > 500`
- `confirm_fuzz_gate(budget, target_count, is_tty=None, prompt_fn=input, stderr_print_fn=None)`: auto-detects TTY via `sys.stdin.isatty()` when `is_tty` is None; HARD ABORTS in non-TTY; requires exact `"CONFIRM"` in TTY (no `.strip()` — trailing/leading whitespace rejected)
- `try/except ImportError` for schemathesis sets `SCHEMATHESIS_AVAILABLE`
- No `session.request` or `socket.create_connection` calls (grep confirms 0 dispatch sites)

All 22 tests pass.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] confirm_fuzz_gate initial .strip() implementation rejected "CONFIRM " incorrectly**
- **Found during:** Task 2, GREEN phase — test_confirm_required_exact_string_rejects_bad_input[CONFIRM ] failed
- **Issue:** PATTERNS.md showed `answer = prompt_fn(...).strip()` but the PLAN.md behavior spec explicitly lists `"CONFIRM "` (trailing space) as a rejected input. The plan's behavior list is the authoritative spec; `.strip()` would silently accept `"CONFIRM "`.
- **Fix:** Removed `.strip()` from the answer comparison. Exact string equality `answer == "CONFIRM"` is enforced. The decision comment documents why.
- **Files modified:** `quirk/scanner/rest_fuzzer.py`
- **Commit:** 2195ce3

## TDD Gate Compliance

- RED gate: `test(96-01)` commit d920e87 — tests written before implementation, all failing on import
- GREEN gate: `feat(96-01)` commit 2195ce3 — implementation written, all 22 tests pass
- REFACTOR: none needed (clean implementation)

## Known Stubs

- `quirk/scanner/rest_fuzzer.py` imports `requests`, `TokenBucket`, `CryptoEndpoint`, `CredentialContext`, `safe_str`, `validate_external_url` at module level but does not yet use them in any function — these are stub-level imports for the Plan 02 dispatch loop. The module is intentionally gate-layer only for this plan.

## Threat Flags

None — no new network endpoints, auth paths, or file access patterns beyond what the threat model covers.

## Self-Check: PASSED

- `quirk/scanner/rest_fuzzer.py`: FOUND
- `tests/test_rest_fuzzer_gate.py`: FOUND
- `pyproject.toml` schemathesis entry: FOUND
- `tests/test_install_all_excludes_schemathesis.py` new test: FOUND
- Commit 5d92864 (Task 1): FOUND
- Commit d920e87 (RED): FOUND
- Commit 2195ce3 (GREEN): FOUND
- grep dispatch sites == 0: CONFIRMED
- 23 tests passing: CONFIRMED
