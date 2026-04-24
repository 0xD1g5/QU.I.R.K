---
phase: 24-scan-session-timestamp
plan: "02"
subsystem: identity-scanners
tags: [tdd, green-gate, session-start, issue-3, dnssec, saml, kerberos, run-scan]
dependency_graph:
  requires: [RED-tests-session-start]
  provides: [GREEN-session-start, ISSUE-3-root-cause-fix]
  affects:
    - quirk/scanner/dnssec_scanner.py
    - quirk/scanner/saml_scanner.py
    - quirk/scanner/kerberos_scanner.py
    - run_scan.py
    - tests/test_dnssec_scanner.py
tech_stack:
  added: []
  patterns: [TDD-GREEN, session-shared-timestamp, optional-kwarg-default-None]
key_files:
  created: []
  modified:
    - quirk/scanner/dnssec_scanner.py
    - quirk/scanner/saml_scanner.py
    - quirk/scanner/kerberos_scanner.py
    - run_scan.py
    - tests/test_dnssec_scanner.py
decisions:
  - "ISSUE-3 regression test (test_issue3_scan_window_returns_all_identity_protocols) still fails — it tests the scan-window query layer which is out of scope; root cause fix (shared session_start) prevents the problem in production without changing the query"
  - "Rule 1 fix: test_dnssec_session_start_stamps_all_endpoints RED test had broken NS mock (plain string iter instead of _mock_ns_answer()/_mock_a_answer() objects); fixed to match existing test pattern"
  - "Kerberos tzinfo normalization: now uses .replace(tzinfo=None) matching DNSSEC and SAML naive-datetime storage pattern"
metrics:
  duration: "95s"
  completed: "2026-04-24"
  tasks_completed: 2
  files_modified: 5
---

# Phase 24 Plan 02: GREEN — Session-Start Timestamp Isolation Summary

**One-liner:** Minimal surgical diffs adding session_start=None kwarg to all 3 identity scanners and wiring one shared datetime.now() from run_scan.py, eliminating ISSUE-3 root cause.

## What Was Built

### Task 1: GREEN — Add session_start to all 3 identity scanners

Modified 3 scanner files with minimal PEP-8-compliant diffs:

**`quirk/scanner/dnssec_scanner.py` (2 changes):**
- `_scan_domain` signature: added `session_start=None` param
- `_scan_domain` body: `now = datetime.now(timezone.utc).replace(tzinfo=None)` → `now = (session_start or datetime.now(timezone.utc)).replace(tzinfo=None)`
- `scan_dnssec_targets` signature: added `session_start=None` param
- `scan_dnssec_targets` loop: threads `session_start=session_start` into `_scan_domain(...)` call

**`quirk/scanner/saml_scanner.py` (5 changes):**
- `_parse_saml_metadata` signature: added `now=None` param; body replaces `now = datetime.now(...)` with `if now is None: now = datetime.now(...)`
- `_parse_oidc_discovery` signature: added `now=None` param; body same guard pattern
- `scan_saml_targets` signature: added `session_start=None` param
- `scan_saml_targets` body: computes `now = (session_start or datetime.now(timezone.utc)).replace(tzinfo=None)` once at top
- Both call sites updated: `_parse_oidc_discovery(content, target_url, now=now)` and `_parse_saml_metadata(content, target_url, now=now)`

**`quirk/scanner/kerberos_scanner.py` (4 changes):**
- `scan_kerberos_targets` signature: added `session_start=None` param
- Compute `now = (session_start or datetime.now(timezone.utc)).replace(tzinfo=None)` once after the IMPACKET guard
- All 3 inline `scanned_at=datetime.now(timezone.utc)` calls replaced with `scanned_at=now` (unreachable ep, per-etype ep, no-preauth placeholder)
- Note: tzinfo normalization brings Kerberos into consistency with DNSSEC/SAML naive-datetime storage

Also fixed `tests/test_dnssec_scanner.py` (Rule 1 deviation): the RED test had a broken NS mock using plain strings (`iter(["198.51.100.1"])`) instead of mock objects with `.target` attributes — `_resolve_ns` silently returned `[]` causing zero endpoints. Fixed to use `_mock_ns_answer()` / `_mock_a_answer()` matching the existing test pattern.

**Result:** All 3 RED tests from Plan 01 now PASS. 66 scanner tests passed, 3 skipped, 0 regressions.

### Task 2: GREEN — Wire session_start in run_scan.py

Added 6 lines to `run_scan.py` around lines 462-501:

1. `session_start = datetime.now(timezone.utc)` — created once just before the DNSSEC block (using already-imported `datetime`/`timezone`)
2. `session_start=session_start` added to `scan_dnssec_targets(...)` call
3. `session_start=session_start` added to `scan_saml_targets(...)` call
4. `session_start=session_start` added to `scan_kerberos_targets(...)` call

All identity endpoints from a scan session now share one timestamp. The Kerberos timeout delay no longer shifts `MAX(scanned_at)` outside the 1-second window query in `GET /api/scan/latest`.

**ISSUE-3 regression test status:** `test_issue3_scan_window_returns_all_identity_protocols` still fails — this is expected and documented. The test simulates OLD behavior (mismatched timestamps) to prove the query-layer fails. The ROOT CAUSE fix (shared session_start) prevents mismatched timestamps in production. The scan-window query itself is unchanged (out of scope per D-05).

**Full test suite:** 352 passed, 3 skipped, 1 expected failure (ISSUE-3 regression test), 0 new failures.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed broken NS mock in test_dnssec_session_start_stamps_all_endpoints**
- **Found during:** Task 1 — test returned 0 endpoints despite `session_start` kwarg now accepted
- **Issue:** RED test used `iter(["198.51.100.1"])` (plain strings) for NS answer mock. `_resolve_ns` calls `str(rdata.target)` on each item — AttributeError on plain string → caught by except → returns `[]` → no endpoints produced → assertion "Expected at least one endpoint" fails
- **Fix:** Changed to `iter([_mock_ns_answer()])` for NS answer and added `a_answer = MagicMock()` with `iter([_mock_a_answer("198.51.100.1")])` for A record resolution, matching the working `test_rsasha1_produces_critical_finding` mock pattern
- **Files modified:** `tests/test_dnssec_scanner.py`
- **Commit:** ed0a198 (included with Task 1)

## TDD Gate Compliance

RED gate: Confirmed in Plan 01 — all 3 session_start tests failed with TypeError before implementation.
GREEN gate: All 3 tests PASS after Task 1 implementation.

Commit sequence:
1. `test(24-01)` — RED gate (Plan 01 commit 3d6e023)
2. `feat(24-02)` — GREEN gate (ed0a198) — scanners accept session_start
3. `feat(24-02)` — GREEN gate (0944a5a) — run_scan.py wiring

## Known Stubs

None — all data flows are wired. `session_start` is created from `datetime.now()` in production and passed through to all endpoint `scanned_at` fields.

## Threat Flags

No new network endpoints, auth paths, or trust boundary crossings introduced. The `session_start` parameter is created internally in `run_scan.py` — not user-controllable (T-24-03 accepted per plan threat model).

## Self-Check

### Files Modified

- [x] `quirk/scanner/dnssec_scanner.py` — contains `def scan_dnssec_targets(targets: list, timeout: int = 10, logger=None, session_start=None)`
- [x] `quirk/scanner/dnssec_scanner.py` — contains `now = (session_start or datetime.now(timezone.utc)).replace(tzinfo=None)`
- [x] `quirk/scanner/saml_scanner.py` — contains `def scan_saml_targets(targets: list, timeout: int = 10, logger=None, session_start=None)`
- [x] `quirk/scanner/saml_scanner.py` — contains `def _parse_saml_metadata(xml_bytes: bytes, target_url: str, now=None)`
- [x] `quirk/scanner/saml_scanner.py` — contains `def _parse_oidc_discovery(json_bytes: bytes, target_url: str, now=None)`
- [x] `quirk/scanner/kerberos_scanner.py` — contains `def scan_kerberos_targets(targets: list, timeout: int = 10, logger=None, session_start=None)`
- [x] `quirk/scanner/kerberos_scanner.py` — does NOT contain `scanned_at=datetime.now(timezone.utc)` (all 3 replaced)
- [x] `run_scan.py` — contains `session_start = datetime.now(timezone.utc)` before DNSSEC block
- [x] `run_scan.py` — contains `session_start=session_start` in all 3 identity scanner calls
- [x] `tests/test_dnssec_scanner.py` — NS mock fixed to use `_mock_ns_answer()` / `_mock_a_answer()`

### Commits

- [x] `ed0a198` — feat(24-02): add session_start param to all 3 identity scanners — GREEN gate
- [x] `0944a5a` — feat(24-02): wire session_start in run_scan.py — ISSUE-3 root cause eliminated

## Self-Check: PASSED
