---
phase: 110-cross-sensor-merge-scoring
plan: "02"
subsystem: merge
tags: [merge, scoring, sensors, distributed, cbom]
dependency_graph:
  requires: [110-01]
  provides: [quirk.merge.scan.merge_scan, merge_runs table]
  affects: [quirk/models.py, quirk/db.py]
tech_stack:
  added: []
  patterns: [Option-A union scoring, SESSION_BRACKET local window, last_push_at overdue check]
key_files:
  created:
    - quirk/merge/__init__.py
    - quirk/merge/scan.py
    - tests/test_merge_scan.py
  modified:
    - quirk/models.py
    - quirk/db.py
decisions:
  - "Option A: single compute_readiness_score call over the full union (never averaged) — MERGE-02"
  - "Source CryptoEndpoint.scanned_at never mutated; merge result persisted as separate MergeRun row — MERGE-05"
  - "_SESSION_BRACKET redefined locally in merge/scan.py to avoid importing from dashboard layer (D-06 seam)"
  - "Sensors silent >30 days excluded from coverage_warning (assumed decommissioned)"
  - "Empty union guard: returns coverage_warning 'no data', never silently scores 100 — T-110-03"
metrics:
  duration: "~20 minutes"
  completed: "2026-05-25"
  tasks_completed: 2
  files_created: 3
  files_modified: 2
---

# Phase 110 Plan 02: Cross-Sensor Merge Scoring Summary

**One-liner:** Standalone merge_scan() callable runs Option-A union scoring with coverage_warning from sensor push recency and persists results as merge_runs rows without mutating source scanned_at.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | MergeRun model + idempotent table | 7206400 | quirk/models.py, quirk/db.py |
| 2 RED | Failing tests for merge_scan() | 07d1065 | tests/test_merge_scan.py |
| 2 GREEN | Implement merge_scan() | 16ee14b | quirk/merge/__init__.py, quirk/merge/scan.py |

## What Was Built

### Task 1: MergeRun Model + Table Registration

Added `MergeRun(Base)` class to `quirk/models.py` after `SensorPush` following the project's plain-Column style (no `relationship()` declarations). Columns: `id`, `scan_id` (ISO merge timestamp, indexed), `merged_at`, `endpoint_count`, `sensor_count`, `score`, `coverage_warning_json` (Text, nullable).

Added `_ensure_merge_runs_table(engine)` to `quirk/db.py` mirroring the `_ensure_integration_deliveries_table` pattern, and called it from `init_db()` right after the existing integration deliveries call. Table created idempotently via `Base.metadata.create_all(checkfirst=True)`.

### Task 2: merge_scan() Implementation (TDD RED→GREEN)

**RED phase:** 8 failing tests in `tests/test_merge_scan.py` covering:
- MERGE-01: pipeline calls build_evidence_summary → compute_readiness_score → build_cbom
- MERGE-02 / Option A: score equals union-level scoring, not averaged per-segment
- MERGE-04: coverage_warning for overdue (last_push_at=None or >2×cadence late) sensors
- MERGE-04: coverage_warning is None when all sensors are current
- MERGE-05: source CryptoEndpoint.scanned_at is unchanged after merge
- Pitfall 4 / T-110-03: empty union produces coverage_warning, not a clean score 100
- Persistence: MergeRun row written with correct fields

**GREEN phase:** `quirk/merge/scan.py` implementing `merge_scan(db, *, now, stale_days, profile, weights)`:

1. `_assemble_union()`: subquery of `func.max(scanned_at)` grouped by non-null `sensor_id` joined back for latest-per-sensor rows; plus NULL-sensor local rows within `_SESSION_BRACKET = timedelta(minutes=5)` of the latest local `scanned_at`.

2. `_build_coverage_warning()`: reads `Sensor.last_push_at` (NOT `CryptoEndpoint.scanned_at` — Pitfall 5); sensor is overdue when `last_push_at is None` OR `now > last_push_at + 2×cadence`; sensors silent >30 days excluded (decommissioned). Returns `None` when all current.

3. Empty union guard: returns `coverage_warning` with reason "no data", never a clean score.

4. Option A: `build_evidence_summary(union, findings=None)` → `compute_readiness_score(evidence, profile=profile, weights=weights)` called EXACTLY ONCE over the full union. No per-segment averaging.

5. `build_cbom(union)` for the Bom artifact.

6. Persist `MergeRun` row with `scan_id` (ISO merge timestamp), `merged_at`, `endpoint_count`, `sensor_count`, `score`, `coverage_warning_json`. Source `CryptoEndpoint.scanned_at` is never assigned or mutated.

## Grep Gates (Verified)

- No `/ len(` in score path: CLEAN
- No `.scanned_at =` assignment (single `=`) in merge_scan: CLEAN
- `last_push_at` used for coverage computation: PRESENT (lines 41, 49, 54, 57, 59)

## Deviations from Plan

None — plan executed exactly as written.

## Phase 111 Consequences (must_haves note)

The dashboard (Phase 111) reads `merge_runs` for the merged view. The merged result is NOT surfaced via `MAX(scanned_at)` on `crypto_endpoints` — it lives in a separate table. Phase 111 must query `merge_runs` to display coverage banner and merged scan results.

## Known Stubs

None.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries beyond what the plan's threat model covers. The `merge_runs` table is written only by `merge_scan()` (local DB write) with no new trust boundaries.

## Self-Check: PASSED

- quirk/merge/__init__.py: FOUND
- quirk/merge/scan.py: FOUND
- tests/test_merge_scan.py: FOUND
- quirk/models.py MergeRun: FOUND (line 338)
- quirk/db.py _ensure_merge_runs_table: FOUND (lines 376, 421)
- Commit 7206400: FOUND
- Commit 07d1065: FOUND
- Commit 16ee14b: FOUND
- python -m pytest tests/test_merge_scan.py: 8 passed
- python -m compileall quirk/merge quirk/models.py quirk/db.py: 0 errors
