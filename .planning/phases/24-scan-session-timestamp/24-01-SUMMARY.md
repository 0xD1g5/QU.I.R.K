---
phase: 24-scan-session-timestamp
plan: "01"
subsystem: testing
tags: [tdd, red-tests, session-start, issue-3, dnssec, saml, kerberos]
dependency_graph:
  requires: []
  provides: [RED-tests-session-start, RED-test-issue3-regression]
  affects: [tests/test_dnssec_scanner.py, tests/test_saml_scanner.py, tests/test_kerberos_scanner.py, tests/test_identity_surface.py]
tech_stack:
  added: []
  patterns: [TDD-RED, pytest-unittest-mix, in-memory-sqlite-testclient]
key_files:
  created: []
  modified:
    - tests/test_dnssec_scanner.py
    - tests/test_saml_scanner.py
    - tests/test_kerberos_scanner.py
    - tests/test_identity_surface.py
decisions:
  - "test_dnssec_session_start_stamps_all_endpoints uses RSASHA1 mock pattern from existing test_rsasha1_produces_critical_finding — confirmed ns_answer iteration works with direct string iter"
  - "ISSUE-3 regression test uses inline TestClient setup (not conftest.py fixture) because unittest.TestCase classes cannot use pytest fixtures directly"
  - "Issue3ScanWindowRegressionTest class inserted above the existing __main__ guard to preserve file structure"
metrics:
  duration: "119s"
  completed: "2026-04-24"
  tasks_completed: 2
  files_modified: 4
---

# Phase 24 Plan 01: RED Tests for Session-Start Timestamp Isolation Summary

**One-liner:** Four RED TDD tests establishing the session_start parameter contract and ISSUE-3 scan-window regression scenario across 3 identity scanners and the API layer.

## What Was Built

### Task 1: RED tests for session_start parameter on all 3 identity scanners

Appended one new test function to each of the three existing scanner test files:

- `tests/test_dnssec_scanner.py` — `test_dnssec_session_start_stamps_all_endpoints`: Calls `scan_dnssec_targets(["weak.example.com"], session_start=fixed_dt)` where `fixed_dt = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)`. Asserts all returned endpoints have `scanned_at == datetime(2026, 1, 15, 12, 0, 0)` (naive). **FAILS with TypeError** because `session_start` kwarg does not exist yet.

- `tests/test_saml_scanner.py` — `test_saml_session_start_stamps_all_endpoints`: Calls `scan_saml_targets(["https://idp.chaos.local/metadata"], session_start=fixed_dt)` with same fixed_dt. Asserts all endpoints have matching naive `scanned_at`. **FAILS with TypeError**.

- `tests/test_kerberos_scanner.py` — `test_kerberos_session_start_stamps_all_endpoints`: Calls `scan_kerberos_targets(["localhost"], timeout=5, session_start=fixed_dt)` with etypes=[18, 23] patched. Asserts both endpoints have `scanned_at == expected_naive`. **FAILS with TypeError**.

### Task 2: RED test for ISSUE-3 API regression (scan-window timing)

Appended `class Issue3ScanWindowRegressionTest(unittest.TestCase)` to `tests/test_identity_surface.py`:

- `test_issue3_scan_window_returns_all_identity_protocols`: Creates an in-memory SQLite DB with inline TestClient setup, inserts DNSSEC+SAML endpoints at `early_ts = datetime(2026, 1, 15, 12, 0, 0)` and Kerberos at `late_ts = datetime(2026, 1, 15, 12, 0, 30)` (30s later), calls `GET /api/scan/latest`, asserts all 3 protocols appear in `identity_findings`. **FAILS with AssertionError**: SAML not found in `{'KERBEROS'}` — proving the scan-window query anchors on MAX(scanned_at)=12:00:30 and excludes early endpoints.

## RED Gate Verification

All 4 tests confirmed FAILING before any implementation:

```
FAILED tests/test_dnssec_scanner.py::test_dnssec_session_start_stamps_all_endpoints
FAILED tests/test_saml_scanner.py::test_saml_session_start_stamps_all_endpoints
FAILED tests/test_kerberos_scanner.py::test_kerberos_session_start_stamps_all_endpoints
FAILED tests/test_identity_surface.py::Issue3ScanWindowRegressionTest::test_issue3_scan_window_returns_all_identity_protocols
```

Existing test suite (80 passed, 3 skipped) — zero regressions.

## Deviations from Plan

None — plan executed exactly as written. Both tasks committed together in a single commit since all 4 test additions are pure RED scaffolding with no implementation.

## TDD Gate Compliance

RED gate: Confirmed — all 4 new tests fail before implementation.
GREEN gate: Pending — Plan 02 will implement the fix.

## Self-Check

### Files Modified

- [x] `tests/test_dnssec_scanner.py` — contains `def test_dnssec_session_start_stamps_all_endpoints`
- [x] `tests/test_saml_scanner.py` — contains `def test_saml_session_start_stamps_all_endpoints`
- [x] `tests/test_kerberos_scanner.py` — contains `def test_kerberos_session_start_stamps_all_endpoints`
- [x] `tests/test_identity_surface.py` — contains `class Issue3ScanWindowRegressionTest` and `def test_issue3_scan_window_returns_all_identity_protocols`

### Commits

- [x] `3d6e023` — test(24-01): add RED tests for session_start parameter and ISSUE-3 scan-window regression

## Self-Check: PASSED
