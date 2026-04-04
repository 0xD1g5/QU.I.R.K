---
phase: 11-dashboard-wiring-fixes
plan: 02
subsystem: dashboard
tags: [fastapi, sqlite, cbom, ssh, ssh-audit, classifier]

# Dependency graph
requires:
  - phase: 11-dashboard-wiring-fixes
    plan: 01
    provides: test_dashboard_wiring.py scaffold with 2 RED SSH CBOM stubs as Plan 02 contract
  - phase: 02-cbom-pipeline
    provides: quirk/cbom/builder.py::_extract_ssh_algorithms() as reference implementation
  - phase: 10-v39-gap-closure
    provides: _QS_DISPLAY at module level in scan.py; GAP-INT-03 identified
provides:
  - _derive_cbom() parses ep.ssh_audit_json via kex/key/enc/mac section-to-type mapping
  - SSH endpoints contribute CbomComponent entries to the dashboard CBOM tab
  - GAP-INT-03 closed: dashboard CBOM viewer now includes SSH algorithm inventory
affects: [12-documentation-sync, cbom-viewer]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Mirror builder.py SSH section parsing pattern inline in _derive_cbom() without calling builder directly
    - Section-to-type mapping dict for SSH algorithm classification in dashboard path

key-files:
  created: []
  modified:
    - quirk/dashboard/api/routes/scan.py

key-decisions:
  - "_SSH_TYPE dict defined inline in the for-ep loop (not as a module-level constant) to keep the SSH parsing block self-contained and readable — no shared state required"
  - "_qs_for_alg() already handles @openssh.com vendor suffixes via the except Exception guard — no additional stripping needed in the SSH branch"
  - "json.loads(ep.ssh_audit_json) wrapped in try/except (json.JSONDecodeError, TypeError, ValueError) matching builder.py defensive pattern exactly"

patterns-established:
  - "SSH CBOM branch mirrors builder.py section loop: iterate kex/key/enc/mac, extract entry.get('algorithm'), guard isinstance(entry, dict)"

requirements-completed: [UI-03]

# Metrics
duration: 3min
completed: 2026-04-04
---

# Phase 11 Plan 02: Dashboard Wiring Fixes — SSH CBOM Parsing Summary

**SSH algorithm parsing added to _derive_cbom() in scan.py: kex/key/enc/mac sections from ssh_audit_json now produce classified CbomComponent entries in the dashboard CBOM viewer, closing GAP-INT-03**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-04T12:33:41Z
- **Completed:** 2026-04-04T12:37:00Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Closed GAP-INT-03: `_derive_cbom()` in `quirk/dashboard/api/routes/scan.py` now parses `ep.ssh_audit_json` using the same four-section pattern (`kex`, `key`, `enc`, `mac`) as `builder.py::_extract_ssh_algorithms()`
- SSH algorithms are classified via `_qs_for_alg()` with section-to-type mapping: `kex` -> `key-exchange`, `key` -> `signature`, `enc` -> `cipher`, `mac` -> `hash`
- All 5 `test_dashboard_wiring.py` tests GREEN (2 previously-RED SSH CBOM stubs now passing)
- Full 199-test suite passes with zero regressions

## Task Commits

1. **Task 1: Add SSH algorithm parsing branch to _derive_cbom()** - `e1f62d1` (feat)

## Files Created/Modified

- `quirk/dashboard/api/routes/scan.py` — Added 22-line SSH parsing block inside `_derive_cbom()` for loop, between the `tls_version` block and the JWT/cloud JSON loop

## Decisions Made

- **`_SSH_TYPE` dict inline, not module-level:** The section-to-type mapping is defined inside the `for ep in endpoints:` loop to keep the SSH parsing block self-contained. No shared state is needed.
- **No vendor suffix stripping needed:** `_qs_for_alg()` already guards vendor-suffixed names like `chacha20-poly1305@openssh.com` via the `except Exception` handler in the classifier call — same behavior as builder.py's fuzzy fallback.
- **Exact defensive pattern from builder.py:** `try: ssh_data = json.loads(ep.ssh_audit_json) except (json.JSONDecodeError, TypeError, ValueError): ssh_data = {}` mirrors the reference implementation precisely.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## Known Stubs

None — both SSH CBOM stubs from Plan 01 are now GREEN.

## Next Phase Readiness

- Phase 11 is complete: all three gaps closed (GAP-INT-01, GAP-INT-02, GAP-INT-03)
- Dashboard CBOM tab now shows SSH algorithm inventory for SSH-only and mixed scans
- Ready for Phase 12 (documentation sync) — SSH CBOM parsing should be documented in the CBOM guide

## Self-Check: PASSED

- FOUND: `.planning/phases/11-dashboard-wiring-fixes/11-02-SUMMARY.md`
- FOUND: `quirk/dashboard/api/routes/scan.py`
- FOUND: commit `e1f62d1`

---
*Phase: 11-dashboard-wiring-fixes*
*Completed: 2026-04-04*
