---
phase: 67-resumable-partial-failure-scans
reviewed: 2026-05-14T15:42:00Z
depth: standard
files_reviewed: 9
files_reviewed_list:
  - quirk/cli/job_progress.py
  - quirk/dashboard/api/routes/scan.py
  - quirk/dashboard/api/schemas.py
  - quirk/db.py
  - quirk/models.py
  - quirk/reports/writer.py
  - run_scan.py
  - src/dashboard/src/pages/executive.tsx
  - src/dashboard/src/types/api.ts
findings:
  critical: 4
  warning: 4
  info: 2
  total: 10
status: issues_found
---

# Phase 67: Code Review Report

**Reviewed:** 2026-05-14T15:42:00Z
**Depth:** standard
**Files Reviewed:** 9
**Status:** issues_found

## Summary

Phase 67 introduces resumable scans via `scan_checkpoints`, per-stage endpoint flushing, partial failure collection, and a `ScannerStatusCard` UI component. The checkpoint infrastructure is structurally sound — the table definition, the helper module, and the stage-gating pattern are all correct. However, four blockers prevent the resume and partial-failure-display features from functioning correctly in production. The most severe are two independent identifier mismatches: one breaks resumed endpoint loading, and one ensures the `partial_failures` array is always empty in the API response.

---

## Critical Issues

### CR-01: Resumed endpoint loading always returns empty — tz-aware filter against tz-naive DB values

**File:** `run_scan.py:693-699`
**Issue:** `scan_run_id` is stored in `scan_checkpoints` as a timezone-aware ISO string (`datetime.now(timezone.utc).isoformat()` → `"2026-05-14T11:51:54.123456+00:00"`). When resuming, `_target_ts = _dt.fromisoformat(scan_run_id)` produces a tz-aware `datetime`. The subsequent query filters `CryptoEndpoint.scanned_at >= _target_ts`, but `scanned_at` is stored as tz-naive in SQLite (set at line 876 with `.replace(tzinfo=None)`). SQLAlchemy passes the tz-aware Python datetime to SQLite as the string `"2026-05-14 11:51:54.123456+00:00"`. SQLite does string comparison; stored values like `"2026-05-14 11:51:54.123456"` are lexicographically less than `"2026-05-14 11:51:54.123456+00:00"` and fail the `>=` test. `_resumed_endpoints` is always empty. Every resumed scan silently re-runs all skipped stages as if no prior data existed.

**Fix:** Strip the UTC offset before using `scan_run_id` as a datetime filter:
```python
_target_ts = _dt.fromisoformat(scan_run_id).replace(tzinfo=None)
_resumed_endpoints = (
    _db.query(_CE)
    .filter(
        _CE.scanned_at >= _target_ts,
        _CE.scanned_at < _target_ts + _td(seconds=1),
    )
    .all()
)
```

---

### CR-02: `_load_partial_failures` always returns `[]` — semantic and format mismatch between `scan_run_id` and `response_scan_id`

**File:** `quirk/dashboard/api/routes/scan.py:860-895` and `run_scan.py:641`

**Issue:** There are two independent problems that together guarantee `_load_partial_failures` never finds any rows.

**Problem A — different events:** `scan_run_id` in `scan_checkpoints` is `started_utc` (the moment `main()` begins, before any scanning). `response_scan_id` in the API is `MAX(scanned_at)` of `CryptoEndpoint` rows (the moment the last endpoint was written, after the scan completes). These two timestamps differ by the entire duration of the scan.

**Problem B — different formats:** `scan_run_id` is `"2026-05-14T11:51:54.123456+00:00"` (tz-aware ISO, T separator). `response_scan_id` = `latest_ts.isoformat()` where `latest_ts` is a tz-naive `datetime` from SQLite → `"2026-05-14T11:51:54.123456"` (no offset). The `==` equality filter in `_load_partial_failures` will never match.

**Fix:** Store a correlation ID that is shared between the scan run and its CryptoEndpoint rows. The simplest approach: write a sentinel `CryptoEndpoint` row at scan start with `protocol="SCAN_RUN"` and `scan_error=scan_run_id`, or add a `scan_run_id` column to `CryptoEndpoint`. The API then resolves the checkpoint's `scan_run_id` by joining through this sentinel rather than guessing from `MAX(scanned_at)`. Alternatively, store the checkpoints using the `scanned_at` timestamp of the first endpoint rather than `started_utc`.

---

### CR-03: Bulk `db_persist` calls `session.add()` on detached resumed endpoints — causes UNIQUE/PK constraint violations on resume

**File:** `run_scan.py:1608-1612`

**Issue:** On resume, skipped-stage endpoint lists (e.g. `tls_endpoints`, `ssh_endpoints`) are populated from `_resumed_endpoints` — ORM objects loaded from a closed `get_session()` context. After that context manager exits, the objects are detached. At line 1576–1588, all stage lists (including the detached resumed objects) are merged into `endpoints`. At line 1611, `session.add(ep)` is called for each endpoint in a **new** session. SQLAlchemy treats detached objects with a populated primary key as "pending for INSERT" in the new session. This produces an `IntegrityError` (UNIQUE constraint on the autoincrement `id` column) at `session.commit()`, crashing every resumed scan.

**Fix:** Replace `session.add(ep)` with `session.merge(ep)` in the bulk persist block, matching the pattern already used in `_flush_stage_endpoints`:
```python
with _phase_timer(run_stats, "db_persist"):
    with get_session(cfg.output.db_path) as session:
        for ep in endpoints:
            session.merge(ep)   # safe for both new and pre-existing rows
        session.commit()
```

---

### CR-04: Entry point `quirk = "run_scan:main"` bypasses `_run_main_with_job_guard` — job failure marking is broken for all CLI-dispatched scans

**File:** `run_scan.py:1657-1666` and `pyproject.toml` (entry point declaration)

**Issue:** The installed `quirk` CLI entry point calls `main()` directly. `_run_main_with_job_guard()` — the wrapper that calls `mark_job_failed()` on uncaught exceptions — is only reachable via `if __name__ == "__main__":` (line 1669), which is never true when running via the installed script. Any exception that escapes `main()` leaves the `ScanJob` row permanently stuck in `status="running"`. The dashboard has no mechanism to detect or recover stale jobs.

**Fix:** Change the entry point in `pyproject.toml` to call the guard wrapper:
```toml
[project.scripts]
quirk = "run_scan:_run_main_with_job_guard"
```

---

## Warnings

### WR-01: `_dar_azure_blob` uses `"SSE-S3"` as the fallback `encryption_mode` for Azure Blob

**File:** `quirk/dashboard/api/routes/scan.py:555`
**Issue:** `_dar_azure_blob` sets `encryption_mode = "SSE-S3"` when the key source is not `microsoft.keyvault`. "SSE-S3" is an AWS S3 server-side encryption mode. Azure Blob's default encryption is Microsoft-managed keys, which should be labeled something like `"SSE-Azure"` or `"Microsoft-managed"`. This surfaces incorrect data in the DAR findings panel.

**Fix:**
```python
def _dar_azure_blob(host, port, severity, dat):
    key_source = (dat.get("key_source") or "").lower()
    if key_source == "microsoft.keyvault":
        enc, mode = True, "CMK"
    else:
        enc, mode = True, "SSE-Azure"   # Microsoft-managed default
    ...
```

---

### WR-02: `ScanCheckpoint` has no unique constraint on `(scan_run_id, stage)` — repeated retries accumulate duplicate rows

**File:** `quirk/models.py:229-237`
**Issue:** The `scan_checkpoints` table only has an index on `scan_run_id`. If a stage is attempted, fails, and retried (or if a resumed run re-runs a stage), multiple rows for the same `(scan_run_id, stage)` pair accumulate. `_handle_list_resumable` uses `.order_by(ScanCheckpoint.checkpoint_id.desc()).first()` which correctly picks the latest, but `_load_partial_failures` scans all rows for the `scan_run_id` with `partial_failure=True`, which could produce duplicate entries in the API response.

**Fix:** Add a unique constraint:
```python
from sqlalchemy import UniqueConstraint
class ScanCheckpoint(Base):
    __tablename__ = "scan_checkpoints"
    __table_args__ = (
        UniqueConstraint("scan_run_id", "stage", name="uq_checkpoint_run_stage"),
    )
    ...
```
Or use `INSERT OR REPLACE` / `session.merge()` in `write_scan_checkpoint` (keyed on `scan_run_id` + `stage`).

---

### WR-03: `TypeScript RoadmapNode.phase` is `string` (required) but Python schema declares it `Optional[str] = None`

**File:** `src/dashboard/src/types/api.ts:60` vs `quirk/dashboard/api/schemas.py:176`

**Issue:** The Python schema has `phase: Optional[str] = None` on `RoadmapNode`. The TypeScript interface declares `phase: string` (non-optional). If the backend returns a `null` phase (which it can, per the Python model), TypeScript consumers that reference `node.phase` will receive `null` at runtime. Any code that calls `.startsWith()`, `.toLowerCase()`, etc. on `phase` without a null guard will throw a runtime error.

**Fix:** Update the TypeScript interface to match the Python schema:
```typescript
export interface RoadmapNode {
  id: string
  title: string
  timeframe: string
  why?: string
  phase?: string   // Optional — can be null per Python schema
}
```

---

### WR-04: `TypeScript ConfidenceData.factor_breakdown` is `Record<string, unknown>` (required) but Python schema declares it `Optional[Dict[str, Any]] = None`

**File:** `src/dashboard/src/types/api.ts:20` vs `quirk/dashboard/api/schemas.py:39`

**Issue:** Python's `ConfidenceData.factor_breakdown` has a default of `None` and is optional. The TypeScript type declares it as a required `Record<string, unknown>`. When `compute_confidence` returns a result where `factor_breakdown` is absent or `None`, the backend serializes it as `null`. Any TypeScript consumer that iterates or accesses properties of `factor_breakdown` without null checking will throw at runtime.

**Fix:**
```typescript
export interface ConfidenceData {
  confidence_score: number
  confidence_rating: string
  factor_breakdown?: Record<string, unknown> | null
}
```

---

## Info

### IN-01: `TypeScript FindingItem` is missing `category` and `compliance` fields present in the Python schema

**File:** `src/dashboard/src/types/api.ts:23-34` vs `quirk/dashboard/api/schemas.py:60-65`

**Issue:** Python's `FindingItem` has `category: Optional[str] = None` (Phase 45) and `compliance: List[Dict[str, Any]] = []` (Phase 49). Both fields are absent from the TypeScript `FindingItem` interface. If any UI code ever needs to access compliance data from `FindingItem`, it would have to use `(finding as any).compliance`, bypassing type safety.

**Fix:** Add the missing fields to `FindingItem` in `api.ts`:
```typescript
export interface FindingItem {
  ...
  category?: string
  compliance?: Record<string, unknown>[]
}
```

---

### IN-02: `inventory` checkpoint is written without partial failure tracking

**File:** `run_scan.py:924-930`

**Issue:** The `inventory` checkpoint is always written with `status="completed"` and no `partial_failure` or `error_summary` argument. However, `inventory_endpoints` may contain `CLOSED` or `UNKNOWN` endpoints with `scan_error` set (added during fingerprinting). This means inventory-stage errors are invisible in the checkpoint system and will not surface as `PartialFailureEntry` items in the API response.

**Fix:** Capture inventory errors the same way other stages do:
```python
_inv_pf = _collect_stage_partial_failures(run_stats, "inventory", error_endpoints, 0)
if args.db_path:
    write_scan_checkpoint(
        args.db_path, scan_run_id, "inventory",
        status="partial" if _inv_pf else "completed",
        endpoint_count=len(inventory_endpoints),
        partial_failure=bool(_inv_pf),
        error_summary=_inv_pf or None,
    )
```

---

_Reviewed: 2026-05-14T15:42:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
