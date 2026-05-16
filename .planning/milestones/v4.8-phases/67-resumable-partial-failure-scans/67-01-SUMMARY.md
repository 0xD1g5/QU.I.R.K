---
phase: 67-resumable-partial-failure-scans
plan: "01"
subsystem: database
tags: [resumable-scans, sqlite, sqlalchemy, checkpoint, db-layer]
one_liner: "ScanCheckpoint ORM model + DB table registration + write_scan_checkpoint() helper for Phase 67 resumable scan foundation"
requires: []
provides:
  - quirk.models.ScanCheckpoint
  - quirk.db._ensure_scan_checkpoints_table
  - quirk.cli.job_progress.write_scan_checkpoint
affects:
  - quirk/models.py
  - quirk/db.py
  - quirk/cli/job_progress.py
tech_stack:
  added: []
  patterns:
    - SQLAlchemy ORM column-level index (index=True)
    - silent no-op pattern (bare except Exception: pass)
    - tz-naive UTC datetime convention (matches ScanJob)
key_files:
  created: []
  modified:
    - quirk/models.py
    - quirk/db.py
    - quirk/cli/job_progress.py
decisions:
  - "Used index=True on scan_run_id column instead of explicit Index() form, matching existing column-level index pattern in models.py"
  - "write_scan_checkpoint() imports json both at module level (clarity) and inside the try block (guard against edge-case import failure)"
  - "completed_at is nullable=False in ScanCheckpoint (unlike ScanJob), enforced at write time via _utcnow_naive()"
metrics:
  duration: "114s"
  completed: "2026-05-14"
  tasks_completed: 3
  tasks_total: 3
  files_modified: 3
---

# Phase 67 Plan 01: Scan Checkpoint DB Layer Summary

ScanCheckpoint ORM model, scan_checkpoints table registration in init_db(), and write_scan_checkpoint() helper — the foundation all other Phase 67 plans depend on.

## What Was Built

### Task 1: ScanCheckpoint model (quirk/models.py)

Added `ScanCheckpoint` SQLAlchemy ORM class after the `ScanJob` class. The model defines the `scan_checkpoints` table with 8 columns:

| Column | Type | Notes |
|--------|------|-------|
| checkpoint_id | Integer PK autoincrement | |
| scan_run_id | String, indexed | Links to scan run |
| stage | String(32) | inventory/tls/ssh/api/identity/data_at_rest/broker_email/reports |
| status | String(16) | completed/partial/failed/skipped |
| completed_at | DateTime (tz-naive) | Set by write_scan_checkpoint() |
| endpoint_count | Integer, default 0 | |
| partial_failure | Boolean, default False | |
| error_summary | Text, nullable | JSON array string or NULL |

Commit: `efa1677`

### Task 2: _ensure_scan_checkpoints_table() (quirk/db.py)

Added `_ensure_scan_checkpoints_table(engine)` function after `_ensure_scan_jobs_table()`. Calls `Base.metadata.create_all(engine, checkfirst=True)` — idempotent and safe to call multiple times. Registered in `init_db()` immediately after `_ensure_scan_jobs_table(engine)`.

Commit: `8523140`

### Task 3: write_scan_checkpoint() (quirk/cli/job_progress.py)

Added `write_scan_checkpoint()` helper with signature:
```
write_scan_checkpoint(db_path, scan_run_id, stage, status,
                      endpoint_count=0, partial_failure=False, error_summary=None)
```

- Serializes `error_summary` list to JSON string, or stores NULL
- Sets `completed_at` via `_utcnow_naive()`
- Wraps entire body in `try/except Exception: pass` — never raises
- Added module-level `import json` alongside existing stdlib imports

Commit: `c125065`

## Verification Results

All three plan verify commands passed:

1. `ScanCheckpoint` importable from `quirk.models` with all 8 D-01 columns: PASS
2. `scan_checkpoints` table created by `init_db()` with all 8 columns; idempotent double-init: PASS
3. `write_scan_checkpoint()` writes 2 rows with correct fields; error_summary JSON round-trips correctly; silent no-op on bad path: PASS
4. `python -m compileall quirk/models.py quirk/db.py quirk/cli/job_progress.py`: PASS (no syntax errors)

## Deviations from Plan

None — plan executed exactly as written.

## Threat Surface Scan

No new network endpoints, auth paths, or file access patterns introduced. All additions are internal SQLite write operations by the scan process itself. Consistent with the accepted threat dispositions in the plan's threat model.

## Known Stubs

None.

## Self-Check

Checking files exist and commits are present...

## Self-Check: PASSED

| Item | Status |
|------|--------|
| quirk/models.py | FOUND |
| quirk/db.py | FOUND |
| quirk/cli/job_progress.py | FOUND |
| 67-01-SUMMARY.md | FOUND |
| commit efa1677 | FOUND |
| commit 8523140 | FOUND |
| commit c125065 | FOUND |
