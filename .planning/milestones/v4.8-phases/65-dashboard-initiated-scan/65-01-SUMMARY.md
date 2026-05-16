---
phase: 65
plan: 01
subsystem: dashboard-initiated-scan
tags: [orm, sqlite, react, shadcn, test-stubs]
dependency_graph:
  requires: []
  provides:
    - quirk.models.ScanJob
    - quirk.db._ensure_scan_jobs_table
    - src/dashboard/src/components/ui/checkbox.tsx
    - tests/test_jobs_api.py (11 stubs)
    - tests/test_job_progress.py (3 stubs)
  affects:
    - quirk/models.py
    - quirk/db.py
tech_stack:
  added:
    - "@radix-ui/react-checkbox ^1.3.3"
  patterns:
    - "Base.metadata.create_all with checkfirst=True for idempotent migrations"
    - "pytest.skip stubs referencing future plan implementations"
key_files:
  created:
    - src/dashboard/src/components/ui/checkbox.tsx
    - tests/test_jobs_api.py
    - tests/test_job_progress.py
  modified:
    - quirk/models.py
    - quirk/db.py
decisions:
  - "Added ScheduledScan/ScheduledRun models (Phase 63 prereqs absent from worktree) alongside ScanJob to keep db.py wiring correct"
  - "Removed stray src/dashboard/@/ artifact left by shadcn CLI path resolution quirk; correct file at src/components/ui/checkbox.tsx"
metrics:
  duration: "~10 minutes"
  completed: "2026-05-13"
  tasks_completed: 3
  files_changed: 5
---

# Phase 65 Plan 01: Dashboard-Initiated Scan — Wave 0 Foundation Summary

One-liner: ScanJob SQLAlchemy model (12 columns), idempotent db migration hook, shadcn Checkbox primitive, and 14 pytest skip-stubs establishing the test surface for Plans 02–05.

## What Was Built

### Task 1: ScanJob ORM Model + DB Migration

Added `ScanJob` class to `quirk/models.py` after `ScheduledRun` with all 12 columns per Phase 65 D-02:

| Column | Type |
|---|---|
| job_id | String(36) PK |
| pid | Integer nullable |
| status | String(16) |
| current_stage | String(32) nullable |
| target | String(512) |
| profile | String(16) |
| calibration | String(16) |
| enable_nmap | Boolean default False |
| started_at | DateTime nullable |
| completed_at | DateTime nullable |
| scan_run_id | String nullable |
| error_message | Text nullable |

Added `_ensure_scan_jobs_table(engine)` to `quirk/db.py` (alongside `_ensure_scheduled_tables`) and wired it into `init_db()` after `_ensure_scheduled_tables` per the plan spec.

Note: `ScheduledScan`, `ScheduledRun`, and `_ensure_scheduled_tables` (Phase 63 additions) were absent from the worktree branch and were added as a prerequisite to enable correct init_db wiring (Rule 3 deviation).

### Task 2: shadcn Checkbox Component

Installed `src/dashboard/src/components/ui/checkbox.tsx` via `npx shadcn@latest add checkbox` from `src/dashboard/`. The CLI placed the file at a stray `@/` alias path; the file was moved to the canonical `src/components/ui/checkbox.tsx` location. `@radix-ui/react-checkbox ^1.3.3` added to `package.json`. TypeScript compiles clean (`npx tsc --noEmit` exits 0).

### Task 3: Test Stubs

Created `tests/test_jobs_api.py` with 11 `pytest.skip` stubs (UI-SCAN-01/02/03 coverage) and `tests/test_job_progress.py` with 3 `pytest.skip` stubs for the `update_job_stage` helper. Both files collect cleanly (14 tests, 0 errors, 14 skipped). The top-of-file setup in `test_jobs_api.py` uses the same `_make_test_engine` / `_app_with_db` pattern as `test_schedules_api.py`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added Phase 63 model/helper prereqs missing from worktree**
- **Found during:** Task 1
- **Issue:** Worktree branch did not have `ScheduledScan`, `ScheduledRun`, or `_ensure_scheduled_tables` (Phase 63 additions present in main). The plan's `init_db` wiring calls `_ensure_scheduled_tables` before `_ensure_scan_jobs_table`. Without it, `init_db` would raise a `NameError`.
- **Fix:** Added Phase 63 classes/helper alongside the Phase 65 additions in the same Task 1 commit.
- **Files modified:** quirk/models.py, quirk/db.py
- **Commit:** 9ccb62d

**2. [Rule 3 - Blocking] shadcn CLI placed checkbox.tsx at wrong path**
- **Found during:** Task 2
- **Issue:** `npx shadcn@latest add checkbox` resolved `@/components/ui/` literally as a directory path (`src/dashboard/@/components/ui/`) instead of the alias target (`src/components/ui/`). The acceptance criteria requires `src/dashboard/src/components/ui/checkbox.tsx`.
- **Fix:** Copied the generated file to the correct location; removed the stray `@/` directory.
- **Files modified:** src/dashboard/src/components/ui/checkbox.tsx (created at correct path)
- **Commit:** a3974e5

## Known Stubs

| File | Stub Type | Reason |
|------|-----------|--------|
| tests/test_jobs_api.py | 11 pytest.skip stubs | Intentional; bodies implemented in Plans 03–04 |
| tests/test_job_progress.py | 3 pytest.skip stubs | Intentional; bodies implemented in Plan 02 |

These are intentional stubs — the plan's goal is to establish the test surface. Plans 02–05 will fill in the bodies.

## Threat Surface Scan

No new network endpoints or auth paths introduced. The `scan_jobs` SQLite table is a new writable table; String(512) length cap on `target` column is present per T-65-01-01 mitigation. Multi-tenant exposure is not applicable (single-user dashboard per T-65-01-02).

## Self-Check: PASSED

- quirk/models.py: ScanJob class present, 12 columns verified via Python introspection
- quirk/db.py: `_ensure_scan_jobs_table` defined and called in `init_db()`
- src/dashboard/src/components/ui/checkbox.tsx: file exists, Radix import present
- tests/test_jobs_api.py: 11 stubs collected, 0 errors
- tests/test_job_progress.py: 3 stubs collected, 0 errors
- Commits: 9ccb62d, a3974e5, a90d630 all present in git log
