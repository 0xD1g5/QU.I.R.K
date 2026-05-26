---
phase: 109-console-ingestion-api
verified: 2026-05-25T21:30:00Z
status: passed
score: 8/8 must-haves verified
overrides_applied: 0
gap_closure: >
  The single BLOCKER below was closed in commit 9e183d0. _ingest_envelope now
  discriminates exc.orig: UNIQUE constraint -> DuplicatePayloadError, FOREIGN KEY
  constraint -> UnknownSensorError (clean "sensor not enrolled" message on the
  air-gap path). The import-results success summary print was restored (SENSOR-04
  UX), and the three Phase 108 air-gap tests now seed an enrolled sensor (the
  now-correct invariant: air-gap import requires prior `quirk console enroll`,
  matching the HTTPS push path). Regression run after fix: 82 passed across
  test_console_cmd, test_sensor_ingest, test_sensor_cmd, test_console_enroll,
  test_sensor_no_verify_false, test_api_auth, test_phase57_invariants;
  `python -m compileall quirk run_scan.py` clean.
gaps_resolved:
  - truth: "Phase 108 air-gap import-results tests pass with no regression after _ingest_envelope stub replacement"
    status: resolved
    reason: >
      _ingest_envelope now performs real DB writes including a SensorPush INSERT with an FK constraint
      on sensors.sensor_id (PRAGMA foreign_keys=ON). The Phase 108 test helpers (_make_qpush_file) never
      seed a sensors row, so db.flush() triggers a FOREIGN KEY constraint IntegrityError which is caught
      by the same except IntegrityError block intended for the payload_id UNIQUE guard and re-raised as
      DuplicatePayloadError. This causes three Phase 108 tests to exit 1 with "ERROR: payload_id already
      imported" — a false positive that hides the real FK failure.
    artifacts:
      - path: "quirk/cli/console_cmd.py"
        issue: >
          Lines 390-399: the except IntegrityError block that raises DuplicatePayloadError does not
          distinguish UNIQUE-constraint failures (dedup intent) from FK-constraint failures (missing
          sensors row). Both fire as IntegrityError on db.flush(); the FK failure is misclassified
          as a duplicate payload.
      - path: "tests/test_console_cmd.py"
        issue: >
          test_import_results_success_exit_zero, test_import_results_prints_summary, and
          test_import_results_finding_count_nonzero do not seed a Sensor row before calling
          _cmd_import_results. Previously harmless (stub body wrote nothing); now broken because
          the real _ingest_envelope enforces the FK constraint.
    missing:
      - >
        In _ingest_envelope, distinguish the two IntegrityError cases: inspect
        exc.orig (sqlite3.IntegrityError) message — FK failures contain "FOREIGN KEY constraint
        failed", UNIQUE failures contain "UNIQUE constraint failed" — and only raise DuplicatePayloadError
        on the UNIQUE case; re-raise or convert the FK case to a clear ingest failure.
      - >
        OR seed a Sensor row in the three failing test helpers / fixtures so the FK is satisfied —
        consistent with how test_sensor_ingest.py uses _seed_sensor() for the same reason.
      - >
        Either fix must be accompanied by confirming pytest tests/test_console_cmd.py passes clean
        (all 16 tests green, no DuplicatePayloadError false-positives).
---

# Phase 109: Console Ingestion API — Verification Report

**Phase Goal:** The console securely accepts pushed sensor payloads with no authentication bypass, no replay vulnerability, and a full audit trail.
**Verified:** 2026-05-25T21:30:00Z
**Status:** GAPS FOUND — 1 blocker gap
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | POST /api/sensor/push exists on the app, mounted at /api (routes/sensor.py + app.py include_router) | VERIFIED | `app.py:116 application.include_router(sensor.router, prefix="/api")`; runtime check confirms `/api/sensor/push` in app routes |
| 2 | `quirk console enroll` provisions a sensors row + SHA-256-hashed sensor_tokens row and prints a one-time bearer token | VERIFIED | `console_cmd.py:117 def _cmd_enroll`; test_console_enroll.py 2/2 pass |
| 3 | Router-level Depends(require_auth), NO require_csrf; unauthenticated push returns 401 | VERIFIED | `sensor.py:47 router = APIRouter(dependencies=[Depends(require_auth)])`; require_csrf absent (comments only); test_api_auth.py 16/16 pass; test_push_requires_auth: 401 confirmed |
| 4 | 413 on oversize body; 409 on replayed payload_id; 422 outside ±15 min with console_utc echoed | VERIFIED | sensor.py lines 134-141 (413), 244-247 (409), 217-223 (422 + console_utc); test_sensor_ingest.py covers all three |
| 5 | IntegrationDelivery row written on every attempt (success + failures); error_summary=safe_str(exc) | VERIFIED | `sensor.py:84-110 _audit()`; called in 413/400/422/404/409/500/200 branches; test_audit_row_written passes |
| 6 | safe_str AST gate covers routes/sensor.py AND console_cmd.py; no str(exc)/repr(exc) | VERIFIED | test_phase57_invariants.py INGEST_FILES gate; grep confirms zero raw str(exc)/repr(exc) in both files |
| 7 | PushEnvelope uses extra='ignore'; version-skew is graceful (no 422/500) | VERIFIED | `sensor.py:70 model_config = ConfigDict(extra="ignore")`; test_extra_fields_ignored and test_version_skew_graceful both pass |
| 8 | Phase 108 air-gap caller still works (no regression in test_console_cmd.py) | FAILED | 3 of 16 test_console_cmd tests fail with "ERROR: payload_id already imported" — FK constraint IntegrityError misclassified as DuplicatePayloadError; see Gaps Summary |

**Score:** 7/8 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `quirk/dashboard/api/routes/sensor.py` | APIRouter with router-level auth, PushEnvelope, failure ladder, audit | VERIFIED | 264 lines; all required constructs present |
| `quirk/dashboard/api/app.py` | sensor.router mounted at /api | VERIFIED | Line 116 include_router; route confirmed at /api/sensor/push |
| `quirk/cli/console_cmd.py` | _cmd_enroll + real _ingest_envelope with db=None param | VERIFIED | _cmd_enroll at line 117; _ingest_envelope at line 330 with db=None trailing param |
| `tests/test_sensor_ingest.py` | 10 push-endpoint contract tests (401/413/409/422/200/audit/extra/skew) | VERIFIED | 17,436 bytes; 10/10 pass |
| `tests/test_console_enroll.py` | enroll provisioning tests (rows, hash-only, duplicate clean exit) | VERIFIED | 6,283 bytes; 2/2 pass |
| `tests/scanner/test_phase57_invariants.py` | INGEST_FILES safe_str AST gate covering console_cmd.py + sensor.py | VERIFIED | INGEST_FILES at line 25; test_ingest_no_raw_exception_stringification parametrized |
| `docs/UAT-SERIES.md` | Series 109 with UAT-109-01..04 entries; Last Updated 2026-05-25 | VERIFIED | Line 12659 "Series 109"; Last Updated 2026-05-25 |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `quirk/dashboard/api/app.py` | `routes/sensor.py::router` | `include_router(sensor.router, prefix='/api')` | VERIFIED | app.py line 116 |
| `routes/sensor.py::sensor_push` | `console_cmd.py::_ingest_envelope` | call with injected db session | VERIFIED | sensor.py lines 237-243 |
| `routes/sensor.py` | `quirk.models.IntegrationDelivery` | `_audit()` on every branch | VERIFIED | _audit helper lines 84-110; called 8 times |
| `console_cmd.py::_cmd_enroll` | `quirk.models.Sensor / SensorToken` | sessionmaker + db.add + commit | VERIFIED | console_cmd.py lines 146-196 |
| `console_cmd.py::_cmd_import_results` | `_ingest_envelope` | positional call with skip_replay_window=True | VERIFIED | console_cmd.py line 305 (signature unchanged) |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|-------------------|--------|
| `routes/sensor.py::sensor_push` | envelope (PushEnvelope) | await request.body() + PushEnvelope parse | Yes — body deserialized from actual HTTP request | FLOWING |
| `routes/sensor.py` | IntegrationDelivery rows | _audit() + db.commit() | Yes — written on every branch | FLOWING |
| `console_cmd.py::_ingest_envelope` | SensorPush + CryptoEndpoint | db.add + db.commit (own-session) or db.flush (injected) | Yes — real DB writes | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| POST /api/sensor/push registered | `python3 -c "from quirk.dashboard.api.app import create_app; app=create_app(); print('/api/sensor/push' in [r.path for r in app.routes if hasattr(r,'path')])"` | True | PASS |
| No raw str(exc) in sensor.py | `grep -n 'str(exc)\|repr(exc)' sensor.py` | 0 matches (comments only) | PASS |
| PushEnvelope extra=ignore | `grep 'ConfigDict(extra="ignore")' sensor.py` | line 70 | PASS |
| compileall clean | `python -m compileall quirk run_scan.py` | exit 0 | PASS |
| Phase 109 test suite | `pytest tests/test_sensor_ingest.py tests/test_console_enroll.py tests/scanner/test_phase57_invariants.py -q` | 22/22 pass | PASS |
| test_api_auth.py (auth gate) | `pytest tests/test_api_auth.py -q` | 16/16 pass | PASS |
| Phase 108 regression | `pytest tests/test_console_cmd.py -q` | 3 FAILED (test_import_results_success_exit_zero, test_import_results_prints_summary, test_import_results_finding_count_nonzero) | FAIL |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| CONSOLE-01 | 109-01, 109-02 | POST /api/sensor/push exists; quirk console enroll provisions sensors row | SATISFIED | Route live at /api/sensor/push; _cmd_enroll writes sensors+sensor_tokens rows |
| CONSOLE-02 | 109-02, 109-03 | Router-level require_auth; unauthenticated → 401; no bypass possible | SATISFIED | APIRouter(dependencies=[Depends(require_auth)]); test_push_requires_auth passes |
| CONSOLE-03 | 109-02, 109-03 | 413 oversize; 409 duplicate payload_id; 422 outside ±15 min + console_utc | SATISFIED | All three branches verified in sensor.py + test_sensor_ingest.py |
| CONSOLE-04 | 109-02, 109-03 | IntegrationDelivery row on every attempt; safe_str(exc); AST gate covers sensor.py + console_cmd.py | SATISFIED | _audit() called in all branches; INGEST_FILES AST gate passes |
| CONSOLE-05 | 109-02, 109-03 | PushEnvelope extra='ignore'; version-skew graceful | SATISFIED | ConfigDict(extra="ignore") at sensor.py:70; test_version_skew_graceful passes |

All five requirements are marked `[x]` complete in REQUIREMENTS.md (lines 47-51, 137-141).

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `quirk/cli/console_cmd.py` | 390-399 | `except IntegrityError` catches BOTH FK-constraint failures and UNIQUE-constraint failures identically | BLOCKER | FK violation on missing sensors row is misclassified as DuplicatePayloadError; causes "payload_id already imported" false positive in air-gap path; breaks 3 Phase 108 tests |

---

### Human Verification Required

None.

---

### Gaps Summary

**Root cause of gap:** The `_ingest_envelope` function's dedup guard uses a broad `except IntegrityError` to detect duplicate payload_id (UNIQUE constraint). SQLite's `PRAGMA foreign_keys=ON` (set in `quirk/db.py`) causes an FK constraint IntegrityError when `SensorPush` is inserted with a `sensor_id` that has no matching row in `sensors`. The two error types are indistinguishable in the current code — both are caught, both roll back, and both raise `DuplicatePayloadError`.

**Impact:** Three Phase 108 tests that call `_cmd_import_results` without seeding a `sensors` row now fail at exit code 1 with a misleading "payload_id already imported" message. The HTTPS route path is not affected (it validates the sensor row before calling `_ingest_envelope`), but the air-gap CLI path is broken for any sensor_id that has not been pre-enrolled in the console DB.

**Required fix (one of two options):**

Option A (discriminate IntegrityError in _ingest_envelope):
Inspect `exc.orig` (the underlying sqlite3.IntegrityError) to distinguish FK failures from UNIQUE failures and re-raise or surface them differently.

Option B (fix test helpers):
Add a Sensor row seed to the three failing Phase 108 test functions, matching the pattern already used in test_sensor_ingest.py's `_seed_sensor()` helper. This is the simpler fix and aligns the test harness with the real deployment invariant (a sensor_id must be enrolled before importing its air-gap results).

**Verification command to confirm closure:**
`pytest tests/test_console_cmd.py -q` — must show 16 passed, 0 failed.

---

_Verified: 2026-05-25T21:30:00Z_
_Verifier: Claude (gsd-verifier)_
