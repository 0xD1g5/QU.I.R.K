---
phase: 51-qramm-core-infrastructure
plan: 05
subsystem: testing
tags: [datetime, deprecation, python3.12, tech-debt, cryptography]

# Dependency graph
requires: []
provides:
  - "Zero datetime.utcnow() calls in test_saml_scanner.py"
  - "Zero datetime.utcnow() calls in test_broker_scanner_redis.py"
  - "Both test files pass -W error::DeprecationWarning gate"
affects: [future-test-additions, ci-deprecation-warnings]

# Tech tracking
tech-stack:
  added: []
  patterns: ["datetime.now(timezone.utc).replace(tzinfo=None) for cryptography certificate fixtures"]

key-files:
  created: []
  modified:
    - tests/test_saml_scanner.py
    - tests/test_broker_scanner_redis.py

key-decisions:
  - "Added `from datetime import timezone as _tz` alias in test_saml_scanner.py to avoid shadowing the existing `import datetime` module alias"
  - "Reused existing `from datetime import datetime, timezone` in test_broker_scanner_redis.py — no new import needed"
  - "Used .replace(tzinfo=None) to strip tzinfo from aware datetime before passing to cryptography not_valid_before/after (backward-compatible with older cryptography versions)"

patterns-established:
  - "Cert fixture pattern: datetime.now(timezone.utc).replace(tzinfo=None) for not_valid_before/after in test cert builders"

requirements-completed: [DEBT-01]

# Metrics
duration: 5min
completed: 2026-05-05
---

# Phase 51 Plan 05: DEBT-01 datetime.utcnow() Deprecation Fix Summary

**Replaced 4 deprecated `datetime.utcnow()` calls with `datetime.now(timezone.utc)` in two test cert builder fixtures, closing DEBT-01 and eliminating DeprecationWarning escalation under `-W error::DeprecationWarning`**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-05-05T00:00:00Z
- **Completed:** 2026-05-05T00:05:00Z
- **Tasks:** 1
- **Files modified:** 2

## Accomplishments
- Eliminated all `datetime.utcnow()` calls from test certificate builders in `tests/test_saml_scanner.py` (lines 44-45) and `tests/test_broker_scanner_redis.py` (lines 122-123)
- Both files compile cleanly and pass all 41 tests under both default pytest mode and `-W error::DeprecationWarning`
- Production code in `quirk/` remains clean (zero utcnow occurrences confirmed)

## Task Commits

Each task was committed atomically:

1. **Task 1: Audit and fix datetime.utcnow() in both test files** - `e4b9c47` (fix)

## Files Created/Modified
- `tests/test_saml_scanner.py` - Added `from datetime import timezone as _tz`; replaced 2 `datetime.datetime.utcnow()` calls with `datetime.datetime.now(_tz.utc).replace(tzinfo=None)`
- `tests/test_broker_scanner_redis.py` - Reused existing `datetime`/`timezone` imports; replaced 2 `dt.datetime.utcnow()` calls with `datetime.now(timezone.utc).replace(tzinfo=None)`

## Decisions Made
- In `test_saml_scanner.py`, the top-level uses `import datetime` (module alias), so introduced `from datetime import timezone as _tz` to avoid shadowing — `datetime.datetime.now(_tz.utc)` preserves the existing module-reference style.
- In `test_broker_scanner_redis.py`, the file already imports `from datetime import datetime, timezone` at line 10, so `datetime.now(timezone.utc)` was used directly without any new import.
- `.replace(tzinfo=None)` applied to strip tzinfo before passing to `not_valid_before`/`not_valid_after` — required for backward compatibility with older `cryptography` library versions; semantically no-op (UTC time is preserved).

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- DEBT-01 is fully closed; test suite is free of utcnow deprecation noise
- Any future test certificate fixtures should follow the established `datetime.now(timezone.utc).replace(tzinfo=None)` pattern

## Self-Check: PASSED

- `tests/test_saml_scanner.py`: 0 utcnow occurrences, 41 tests pass
- `tests/test_broker_scanner_redis.py`: 0 utcnow occurrences, tests pass
- Commit `e4b9c47` exists in git log

---
*Phase: 51-qramm-core-infrastructure*
*Completed: 2026-05-05*
