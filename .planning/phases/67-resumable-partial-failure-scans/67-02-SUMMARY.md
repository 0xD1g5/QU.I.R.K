---
phase: 67-resumable-partial-failure-scans
plan: "02"
subsystem: scan-orchestration
tags: [resumable-scans, checkpoint, partial-failures, run_scan, sqlalchemy]
one_liner: "Per-stage DB flush and scan_checkpoints writes wired into run_scan.py with partial_failures accumulation in run_stats"
requires:
  - quirk.cli.job_progress.write_scan_checkpoint  # from plan 01
provides:
  - run_scan._flush_stage_endpoints
  - run_scan._collect_stage_partial_failures
  - per-stage checkpoint rows in scan_checkpoints table
  - partial_failures list in run_stats
affects:
  - run_scan.py
tech_stack:
  added: []
  patterns:
    - session.merge() for idempotent incremental endpoint flush
    - pre-stage error count snapshot for partial_failure detection
    - silent no-op helper pattern (bare except Exception: pass)
key_files:
  created: []
  modified:
    - run_scan.py
decisions:
  - "Identity stage checkpoint covers aws+azure+gcp+db only — dnssec/saml/kerberos run after data_at_rest in the actual code, so they are folded into data_at_rest checkpoint (plan's line references described a different ordering)"
  - "broker_scan_json augmentation happens before broker_email flush so augmented attributes are captured in the incremental persist"
  - "_err_before_STAGE sentinel set just before update_job_stage() call for each stage, matching the logical stage boundary"
  - "data_at_rest stage includes s3+blob+k8s+gcs_storage+dnssec+saml+kerberos+vault (all scanners between identity checkpoint and email/broker)"
metrics:
  duration: "~8 min"
  completed: "2026-05-14"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 1
---

# Phase 67 Plan 02: Stage Checkpoint Wiring Summary

Per-stage DB flush and scan_checkpoints writes wired into run_scan.py, with partial_failures accumulation in run_stats. A crashed scan between stages leaves completed-stage rows in SQLite visible for Plan 04's resume logic.

## What Was Built

### Task 1: Helpers and initializer (run_scan.py)

**Import addition** — `write_scan_checkpoint` added to the `from quirk.cli.job_progress import (...)` block.

**`_flush_stage_endpoints(db_path, endpoints)`** — Module-level helper added before `_process_gcs_storage_encryption`. Uses `session.merge(ep)` for each endpoint so re-persisting already-stored rows on resume is idempotent. Silent no-op on any exception — the existing bulk persist is the safety net.

**`_collect_stage_partial_failures(run_stats, stage, error_endpoints, previous_error_count)`** — Module-level helper that slices `error_endpoints[previous_error_count:]` to find errors added during a specific stage, builds `{stage, scanner, error_category, error_message, endpoint_count}` dicts, and extends `run_stats["partial_failures"]`.

**`run_stats.setdefault("partial_failures", [])`** — Initialized immediately after `run_stats["counts"]` is set (before first scanner stage).

Commit: `068c9aa`

### Task 2: Per-stage checkpoint writes (run_scan.py)

8 stage checkpoints wired in at stage boundaries:

| Stage | Endpoints flushed | Notes |
|-------|------------------|-------|
| inventory | inventory_endpoints | Always "completed"; no error tracking needed |
| tls | tls_endpoints | _wrapped_phase output |
| ssh | ssh_endpoints | _wrapped_phase output |
| api | jwt + container + source endpoints | Inline collection (no _wrapped_phase) |
| identity | aws + azure + gcp + db endpoints | See decisions — dnssec/saml/kerberos in data_at_rest |
| data_at_rest | s3 + blob + k8s + gcs + dnssec + saml + kerberos + vault | All scanners between identity and email/broker |
| broker_email | email + kafka + rabbit + redis endpoints | Flush after broker_scan_json augmentation |
| reports | endpoints (total) | No flush; write_reports already complete |

Pattern per stage:
```python
_err_before_STAGE = len(error_endpoints)   # set before update_job_stage()
# ... scanner runs ...
_flush_stage_endpoints(cfg.output.db_path, STAGE_endpoints)
_STAGE_pf = _collect_stage_partial_failures(run_stats, "STAGE", error_endpoints, _err_before_STAGE)
if args.db_path:
    write_scan_checkpoint(args.db_path, scan_run_id, "STAGE",
        status="partial" if _STAGE_pf else "completed",
        endpoint_count=len(STAGE_endpoints), partial_failure=bool(_STAGE_pf),
        error_summary=_STAGE_pf or None)
```

The existing bulk `db_persist` block at the end is retained — it handles `error_endpoints` rows and any rows not individually flushed. `session.merge()` in `_flush_stage_endpoints` makes re-adding already-persisted rows safe.

Commit: `9d208b4`

## Verification Results

All plan verification commands passed:

1. `python -m compileall run_scan.py` — PASS (no syntax errors)
2. `from run_scan import _flush_stage_endpoints, _collect_stage_partial_failures` — PASS
3. `grep -c "write_scan_checkpoint" run_scan.py` → 9 (8 stage calls + 1 import) — PASS (>= 8)
4. `grep -v "^#" run_scan.py | grep -c "partial_failures"` → 10 — PASS (>= 2)
5. All 8 stage names (`inventory`, `tls`, `ssh`, `api`, `identity`, `data_at_rest`, `broker_email`, `reports`) present in source — PASS

## Deviations from Plan

### Deviation 1: Identity stage membership differs from plan description

**Rule:** Rule 1 (auto-fix — incorrect implementation would fail at runtime)

**Found during:** Task 2

**Issue:** The plan stated identity includes dnssec, saml, kerberos scanners, but those scanners are defined and run AFTER the `data_at_rest` `update_job_stage()` call in the actual code. Including them in `_identity_eps` would cause a `NameError` (variables not yet defined).

**Fix:** Identity checkpoint covers aws+azure+gcp+db only. dnssec, saml, kerberos, and vault are folded into the data_at_rest checkpoint (which runs after all of them complete).

**Files modified:** run_scan.py (same file)

**Commit:** 9d208b4

## Threat Surface Scan

No new network endpoints, auth paths, or file access patterns introduced. All changes are internal SQLite write operations by the scan process itself. Consistent with accepted threat dispositions T-67-02-01 through T-67-02-03 in the plan's threat model.

## Known Stubs

None.

## Self-Check: PASSED

| Item | Status |
|------|--------|
| run_scan.py (modified) | FOUND |
| commit 068c9aa | FOUND |
| commit 9d208b4 | FOUND |
| `_flush_stage_endpoints` in run_scan.py | FOUND |
| `_collect_stage_partial_failures` in run_scan.py | FOUND |
| 8 stage checkpoint calls | FOUND (9 write_scan_checkpoint references) |
| partial_failures in run_stats | FOUND (10 references) |
