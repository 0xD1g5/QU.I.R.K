---
phase: 115-live-uat-stabilization-lab-testability
plan: "01"
subsystem: cli
tags: [sensor, console, idempotency, sqlalchemy, sqlite, tdd]

requires:
  - phase: 113-per-sensor-auth
    provides: "Sensor + SensorToken DB models; per-sensor Bearer token minting in console_cmd._cmd_enroll"
  - phase: 108-distributed-sensor
    provides: "sensor_cmd._cmd_enroll and _read_scan_endpoints; push envelope and export-results paths"

provides:
  - "console_cmd._cmd_enroll idempotent: pre-check by sensor_id before token minting, exit 0 on re-enroll (no token churn)"
  - "sensor_cmd._cmd_enroll idempotent: pre-check by sensor.yaml sensor_id before hmac_key generation, exit 0 on re-enroll"
  - "sensor_cmd._read_scan_endpoints filters advisory sentinels (scan_error_category=missing_extra) with mandatory IS NULL clause"
  - "test_enroll_idempotent_console and test_enroll_idempotent_sensor_yaml regression tests"
  - "tests/test_stab04_phantom_rows.py phantom-row regression tests"

affects:
  - 115-live-uat-stabilization-lab-testability
  - distributed-e2e

tech-stack:
  added: []
  patterns:
    - "STAB-01 pre-check pattern: query sensor_id before any secret generation, return/exit-0 if found"
    - "STAB-04 advisory filter: (scan_error_category != 'missing_extra') | scan_error_category.is_(None) — IS NULL clause mandatory for SQLite three-valued logic"
    - "T-109 fixed-string convention on idempotent INFO messages"
    - "WR-04: console_cmd idempotent path uses return not sys.exit(0); sensor_cmd keeps sys.exit(0)"

key-files:
  created:
    - tests/test_stab04_phantom_rows.py
  modified:
    - quirk/cli/console_cmd.py
    - quirk/cli/sensor_cmd.py
    - tests/test_console_cmd.py
    - tests/test_sensor_cmd.py
    - tests/test_console_enroll.py

key-decisions:
  - "D-01: idempotent re-enroll exits 0 without printing any token (no token churn) per 115-CONTEXT.md"
  - "D-02: pre-check by sensor_id/sensor.yaml sensor_id before insert/generation; IntegrityError backstop retained for race window"
  - "WR-04: console_cmd returns normally on idempotent path; sensor_cmd uses sys.exit(0) (mirrors existing function pattern)"
  - "STAB-04 downstream filter: advisory rows stay in local DB (trends.py dependency); filtered at _read_scan_endpoints boundary (covers push L608 and export-results L744)"
  - "IS NULL or-clause mandatory: SQLite !='missing_extra' does NOT match NULL rows (SQL three-valued logic)"

patterns-established:
  - "Idempotency pre-check before secret generation: prevents stale token printing (Pitfall 1)"
  - "SQLAlchemy advisory filter with IS NULL or-clause for nullable category columns"

requirements-completed: [STAB-01, STAB-04]

duration: 20min
completed: 2026-05-27
---

# Phase 115 Plan 01: Idempotent Enroll + Advisory-Row Filter Summary

**Idempotent console/sensor enroll (pre-check before token minting) + SQLAlchemy filter excluding advisory sentinel rows from push/export paths, with IS NULL clause for SQLite three-valued logic correctness**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-05-27T00:00:00Z
- **Completed:** 2026-05-27
- **Tasks:** 3
- **Files modified:** 5 (+ 1 created)

## Accomplishments

- `quirk console enroll` is now idempotent: re-running with the same sensor_id returns normally (no SystemExit), prints no token, and emits INFO to stderr — enabling lab re-runs without `docker compose down -v`
- `quirk sensor enroll` is now idempotent: re-running with the same sensor_id exits 0 with the sensor.yaml unchanged and hmac_key stable — preventing broken pushes from credential regeneration
- `_read_scan_endpoints` filters advisory sentinel rows (host=email_scanner/broker_scanner, port=0, scanned_at=None) before they enter the push envelope or export payload — covers both push (L608) and export-results (L744) call sites in one fix
- Phantom-row regression tests guard D-05: zero scanned_at=None or port=0 endpoints in the returned set

## Task Commits

Each task was committed atomically:

1. **Task 1: Make console enroll idempotent (STAB-01)** - `13264d0` (feat)
2. **Task 2: Make sensor enroll idempotent (STAB-01 mirror)** - `53cc8df` (feat)
3. **Task 3: Filter advisory rows from push/export + phantom-row regression (STAB-04)** - `cd6f458` (feat)

## Files Created/Modified

- `quirk/cli/console_cmd.py` — Added sensor_id pre-check block before `secrets.token_urlsafe` in `_cmd_enroll`; returns normally (WR-04) with INFO to stderr if already enrolled
- `quirk/cli/sensor_cmd.py` — Added sensor.yaml pre-check before hmac_key generation in `_cmd_enroll`; replaced bare `.all()` in `_read_scan_endpoints` with `missing_extra` filter + IS NULL clause
- `tests/test_console_cmd.py` — Added `test_enroll_idempotent_console` (STAB-01 regression)
- `tests/test_sensor_cmd.py` — Added `test_enroll_idempotent_sensor_yaml` (STAB-01 / Pitfall 6 regression)
- `tests/test_stab04_phantom_rows.py` — New file: `test_read_scan_endpoints_excludes_advisory` + `test_no_phantom_rows_in_merged_output` (STAB-04 / D-05)
- `tests/test_console_enroll.py` — Updated `test_console_enroll_duplicate` to reflect new STAB-01 idempotent contract (exit 0, no token, "already enrolled" in stderr)

## Decisions Made

- **Pre-check location:** Placed before `secrets.token_urlsafe` in both functions (Pitfall 1: token must not be minted before the pre-check exits)
- **console_cmd uses `return`, sensor_cmd uses `sys.exit(0)`:** WR-04 applies to console_cmd (atexit + unit test compatibility); sensor_cmd keeps existing `sys.exit(0)` convention already in the function
- **Single filter function covers both paths:** `_read_scan_endpoints` is called by both push (L608) and export-results (L744), so the single fix eliminates advisory rows from both paths without duplication
- **IS NULL clause mandatory:** `CryptoEndpoint.scan_error_category.is_(None)` or-clause required because SQLite `!= 'missing_extra'` evaluates to NULL (not TRUE) for rows with scan_error_category IS NULL — would silently drop all normal finding rows without it

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated test_console_enroll_duplicate to match new STAB-01 contract**
- **Found during:** Task 3 (verification run `pytest tests/ -k enroll`)
- **Issue:** Pre-existing test `test_console_enroll_duplicate` expected `SystemExit` with non-zero code on re-enroll (old IntegrityError path). STAB-01 changed this to an idempotent exit-0 return, so the test correctly failed.
- **Fix:** Updated test to assert: returns normally (no SystemExit), no Bearer token in stdout, "already enrolled" in stderr, row counts still 1/1
- **Files modified:** `tests/test_console_enroll.py`
- **Verification:** `pytest tests/test_console_enroll.py` — 2 passed
- **Committed in:** `cd6f458` (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - test updated to match correct new behavior)
**Impact on plan:** Auto-fix necessary — old test was a contract test for the now-superseded error path. New assertions verify the STAB-01 invariants directly.

## Issues Encountered

None — all three tasks followed the plan as specified. The STAB-04 deviation note (downstream-filter approach) was pre-resolved in the execution context.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- STAB-01 complete: lab `./lab.sh distributed e2e` can now be re-run without `docker compose down -v` for the enroll step
- STAB-04 complete: merged console output will contain no phantom email_scanner/broker_scanner endpoints from the next push cycle
- Plan 115-02 (STAB-02 CMVP packaging + STAB-03 scheduler arg fix) is ready to proceed

## Known Stubs

None — all paths are fully wired. The idempotent pre-check queries live DB state; the advisory filter queries live scan DB state.

## Threat Flags

None — no new network endpoints, auth paths, file access patterns, or schema changes introduced. STAB-04 reduces attack surface (T-115-04: advisory-row injection via push eliminated at push boundary).

---
*Phase: 115-live-uat-stabilization-lab-testability*
*Completed: 2026-05-27*
