---
phase: 36-dashboard-motion-tab
plan: "01"
subsystem: dashboard-api
tags: [dashboard, fastapi, pydantic, motion, tdd]
dependency_graph:
  requires: [Phase 34 motion intelligence, Phase 35 CBOM integration]
  provides: [MotionFinding Pydantic model, SubScores.data_in_motion field, ScanLatestResponse.motion_findings, _derive_motion_findings derivation]
  affects: [quirk/dashboard/api/schemas.py, quirk/dashboard/api/routes/scan.py, tests/test_dashboard_api.py]
tech_stack:
  added: []
  patterns: [TDD RED/GREEN, Pydantic model extension, derivation function mirroring _derive_identity_findings]
key_files:
  created: []
  modified:
    - quirk/dashboard/api/schemas.py
    - quirk/dashboard/api/routes/scan.py
    - tests/test_dashboard_api.py
decisions:
  - Move _derive_motion_findings imports inside test functions (lazy import) so module is collectable during RED phase; avoids ImportError blocking all 5 tests at collection time
metrics:
  duration: "~5 minutes"
  completed: "2026-04-29"
  tasks_completed: 3
  files_modified: 3
---

# Phase 36 Plan 01: Backend API Extension — Motion Findings Summary

One-liner: FastAPI `/api/scan/latest` extended with typed `MotionFinding` list and `data_in_motion` subscore via `_derive_motion_findings()` derivation function and Pitfall 1 SubScores constructor fix.

## What Was Built

### schemas.py Changes

Three additive extensions:

1. **`SubScores.data_in_motion: int = 0`** — 6th field added after `data_at_rest`. Plugs Pitfall 1: without this, the manually-keyed SubScores constructor in scan.py silently dropped the subscore even after scoring.py produced it.

2. **`MotionFinding` Pydantic model** — Added after `IdentityFinding`. Shape mirrors `IdentityFinding` plus two non-optional booleans: `plaintext_exposed: bool = False` and `starttls_warning: bool = False` (both per D-02 requirement). Fields include `tls_version`, `cipher_suite`, and `cert_not_after` (as ISO date string, not datetime).

3. **`ScanLatestResponse.motion_findings: List[MotionFinding] = []`** — Added directly after `identity_findings` field. Defaults to empty list so existing scan sessions without motion data are backward-compatible.

### scan.py Changes

Three changes in the same file:

1. **Pitfall 1 fix**: Added `data_in_motion=subscores_raw.get("data_in_motion", 0)` as the 6th kwarg to the `SubScores(...)` constructor call (lines ~595-601). Without this, the value produced by `scoring.py` was silently dropped at the constructor boundary.

2. **`_derive_motion_findings(endpoints)` function**: Added directly after `_derive_identity_findings` (~line 334). Uses protocol set membership to classify CryptoEndpoints:
   - `EMAIL_PROTOS`: SMTP-STARTTLS, SMTPS, IMAP-STARTTLS, IMAPS, POP3-STARTTLS, POP3S
   - `BROKER_PLAIN`: KAFKA-PLAIN, AMQP-PLAIN, REDIS-PLAIN
   - `BROKER_TLS`: KAFKA-TLS, AMQPS, AMQPS/Azure-ServiceBus, HTTPS/AWS-SQS, REDIS-TLS
   - Severity rules: BROKER_PLAIN → HIGH, port-25 SMTP-STARTTLS → MEDIUM, BROKER_TLS + legacy TLS → HIGH, else → LOW
   - Uses `getattr()` for `cipher_suite`/`cert_not_after` (Pitfall 5: older rows may lack these fields)
   - Protocol labels preserved verbatim — `AMQPS/Azure-ServiceBus` passes through without normalization

3. **Response wiring**: Added `motion_findings=_derive_motion_findings(endpoints)` to `ScanLatestResponse(...)` build, inline like `identity_findings`. Runs on every request.

4. **`MotionFinding` import**: Added to the schema import block at the top of scan.py.

### tests/test_dashboard_api.py Changes

5 new pytest cases appended:

| Test | What It Verifies |
|------|-----------------|
| `test_motion_findings_endpoint` | GET /api/scan/latest response has `motion_findings` list key |
| `test_data_in_motion_subscore` | GET /api/scan/latest response has `score.subscores.data_in_motion` as int |
| `test_derive_motion_findings_plaintext` | KAFKA-PLAIN → severity==HIGH, plaintext_exposed==True |
| `test_derive_motion_findings_starttls` | port-25 SMTP-STARTTLS → starttls_warning==True; port-587 → False |
| `test_derive_motion_findings_azure` | AMQPS/Azure-ServiceBus protocol label preserved verbatim |

## Test Results

All 5 motion pytest cases GREEN after Task 3:

```
tests/test_dashboard_api.py::test_motion_findings_endpoint PASSED
tests/test_dashboard_api.py::test_data_in_motion_subscore PASSED
tests/test_dashboard_api.py::test_derive_motion_findings_plaintext PASSED
tests/test_dashboard_api.py::test_derive_motion_findings_starttls PASSED
tests/test_dashboard_api.py::test_derive_motion_findings_azure PASSED
```

Full test suite: 101/101 CBOM tests GREEN; pre-existing version-check failures (test_version_consistency, test_version_is_4_2_0, test_pyproject_version_field_is_4_1_0) are out of scope and pre-date Phase 36.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Moved `_derive_motion_findings` import inside test functions**
- **Found during:** Task 1 (RED phase)
- **Issue:** The plan skeleton placed `from quirk.dashboard.api.routes.scan import _derive_motion_findings` at module level in the test file. This caused a collection-time `ImportError` that blocked all 5 tests from being individually identified by pytest, preventing the Task 2 partial GREEN gate (`test_data_in_motion_subscore` passing while others remain RED).
- **Fix:** Moved the import inside each of the three `test_derive_motion_findings_*` functions. The two endpoint tests (`test_motion_findings_endpoint`, `test_data_in_motion_subscore`) don't need the import. This preserves the behavioral contract exactly as specified.
- **Files modified:** `tests/test_dashboard_api.py`
- **Commit:** eda1fb8 (amended into Task 1 commit)

## TDD Gate Compliance

- RED gate: commit `eda1fb8` — `test(36-01): add failing motion_findings ...` — all 5 tests failing
- GREEN gate: commit `e0735b8` — `feat(36-01): add _derive_motion_findings ...` — all 5 tests passing
- REFACTOR gate: not required (implementation was clean)

## Known Stubs

None. All motion findings are derived from real CryptoEndpoint data; no hardcoded placeholders.

## Threat Flags

None. `_derive_motion_findings` is a pure read-only derivation from existing DB data; no new network endpoints or trust boundaries introduced.

## Self-Check: PASSED

- `quirk/dashboard/api/schemas.py` — file exists, contains `class MotionFinding`, `data_in_motion`, `motion_findings`
- `quirk/dashboard/api/routes/scan.py` — file exists, contains `_derive_motion_findings`, `motion_findings=_derive_motion_findings`, `data_in_motion=subscores_raw.get`
- `tests/test_dashboard_api.py` — file exists, contains all 5 test functions
- Task 1 commit: eda1fb8
- Task 2 commit: 0244fd4
- Task 3 commit: e0735b8
