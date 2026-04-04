---
phase: 11-dashboard-wiring-fixes
plan: 01
subsystem: dashboard
tags: [fastapi, sqlite, uvicorn, tdd, env-vars]

# Dependency graph
requires:
  - phase: 10-v39-gap-closure
    provides: v3.9 audit findings — GAP-INT-01 and GAP-INT-02 identified
  - phase: 05-web-dashboard
    provides: quirk/dashboard/api/deps.py and quirk/dashboard/server.py baseline
provides:
  - deps.py _default_db_path() returns './quirk.db' matching config_template.yaml
  - server.py sets QUIRK_SERVE_PORT env var before uvicorn.run() for PDF exporter
  - test_dashboard_wiring.py scaffold with 5 tests (3 GREEN for this plan, 2 RED awaiting Plan 02)
affects: [12-documentation-sync, plan-02-ssh-cbom]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - sys.modules injection for mocking lazily-imported modules (uvicorn inside serve())
    - TDD RED/GREEN: write failing tests first, then fix source, verify GREEN

key-files:
  created:
    - tests/test_dashboard_wiring.py
  modified:
    - quirk/dashboard/api/deps.py
    - quirk/dashboard/server.py

key-decisions:
  - "sys.modules patch used instead of patch('uvicorn.run') — uvicorn is lazily imported inside serve() and not installed in test env; sys.modules injection intercepts the import cleanly"
  - "SSH CBOM tests (test_derive_cbom_ssh_algorithms, test_derive_cbom_ssh_only_scan) left RED intentionally — will go GREEN in Plan 02 as contracted test scaffold"

patterns-established:
  - "Lazy-import mocking: use patch.dict(sys.modules, {'module': mock}) when target is imported inside the function under test and may not be installed in test environment"

requirements-completed: [UI-01, UI-04]

# Metrics
duration: 2min
completed: 2026-04-04
---

# Phase 11 Plan 01: Dashboard Wiring Fixes Summary

**Two-line fix closes GAP-INT-01 and GAP-INT-02: deps.py default db_path aligned to './quirk.db' (config_template.yaml) and server.py now sets QUIRK_SERVE_PORT before uvicorn starts so PDF export inherits the correct port**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-04T12:29:53Z
- **Completed:** 2026-04-04T12:31:41Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Fixed GAP-INT-01: `_default_db_path()` now returns `"./quirk.db"` matching `config_template.yaml:44`, ending 404s on `/api/scan/latest` for fresh installs
- Fixed GAP-INT-02: `os.environ["QUIRK_SERVE_PORT"] = str(port)` added before `uvicorn.run()` so PDF export always targets the actual serving port, not the hardcoded 8512 fallback
- Created Phase 11 test scaffold `tests/test_dashboard_wiring.py` with 5 tests (3 GREEN for this plan, 2 RED contracted stubs for Plan 02 SSH CBOM work)

## Task Commits

1. **Task 1: TDD RED — test scaffold** - `884e314` (test)
2. **Task 2: Fix deps.py and server.py + test mock fix** - `b387a48` (fix)

## Files Created/Modified

- `tests/test_dashboard_wiring.py` — 5-test wiring scaffold; 3 GREEN (deps default path, env override, QUIRK_SERVE_PORT); 2 RED (SSH CBOM — Plan 02)
- `quirk/dashboard/api/deps.py` — Changed default from `"data/quirk.db"` to `"./quirk.db"` on line 14
- `quirk/dashboard/server.py` — Added `os.environ["QUIRK_SERVE_PORT"] = str(port)` before `uvicorn.run()` on line 39

## Decisions Made

- **sys.modules patch for uvicorn mock:** `patch("uvicorn.run", ...)` failed because uvicorn is lazily imported inside `serve()` and is not installed in the test environment. Used `patch.dict(sys.modules, {"uvicorn": mock_uvicorn})` to intercept the lazy import cleanly.
- **SSH CBOM tests left RED:** `test_derive_cbom_ssh_algorithms` and `test_derive_cbom_ssh_only_scan` are intentionally failing — they define the Plan 02 implementation contract for SSH CBOM parsing.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed uvicorn mock strategy in test_server_sets_quirk_serve_port**
- **Found during:** Task 2 (verification run)
- **Issue:** `patch("uvicorn.run", ...)` raised `ModuleNotFoundError: No module named 'uvicorn'` — the plan's suggested mock target assumes uvicorn is a top-level importable module, but it is lazily imported inside `serve()` and not installed in the test environment
- **Fix:** Replaced with `patch.dict(sys.modules, {"uvicorn": mock_uvicorn})` to inject the mock before the lazy import runs
- **Files modified:** `tests/test_dashboard_wiring.py`
- **Verification:** `test_server_sets_quirk_serve_port` passes GREEN; mock is called and env var captured correctly
- **Committed in:** `b387a48` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — bug in mock strategy)
**Impact on plan:** Required correction; same behavioral assertion, different mock mechanism. No scope creep.

## Issues Encountered

None beyond the mock strategy deviation above.

## Known Stubs

- `test_derive_cbom_ssh_algorithms` and `test_derive_cbom_ssh_only_scan` in `tests/test_dashboard_wiring.py` — intentional RED stubs defining the Plan 02 contract. They will be wired GREEN when `_derive_cbom()` gains `ssh_audit_json` parsing in Plan 02.

## Next Phase Readiness

- Plan 02 (SSH CBOM parsing) has its test contract ready — both RED stubs define expected behavior precisely
- Existing dashboard API tests (11 tests) continue passing — no regressions

---
*Phase: 11-dashboard-wiring-fixes*
*Completed: 2026-04-04*
