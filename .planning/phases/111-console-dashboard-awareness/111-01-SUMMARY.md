---
phase: "111"
plan: "01"
subsystem: dashboard-api
tags: [sensor-registry, merge-latest, segment-filter, tdd, read-only]
dependency_graph:
  requires:
    - "107 (MergeRun/Sensor models)"
    - "109 (sensor.py push endpoint + Sensor FK)"
    - "110 (merge_scan/_assemble_union)"
  provides:
    - "GET /api/sensor/registry — sensor push-status"
    - "GET /api/merge/latest — merged result + per-segment scores"
    - "GET /api/scan/latest?segment= — NULL-safe segment filter"
    - "FindingItem.sensor_id, FindingItem.segment (nullable)"
    - "CbomComponent.sensor_id, CbomComponent.segment (nullable)"
  affects:
    - "quirk/dashboard/api/schemas.py"
    - "quirk/dashboard/api/routes/sensor.py"
    - "quirk/dashboard/api/routes/scan.py"
    - "quirk/dashboard/api/routes/merge.py (new)"
    - "quirk/dashboard/api/app.py"
tech_stack:
  added: []
  patterns:
    - "TDD RED/GREEN per task — all three tasks followed the cycle"
    - "_sensor_status standalone helper (NOT _build_coverage_warning) — Trap T7"
    - "NULL-safe segment filter guard: if segment is not None (Trap T4)"
    - "Per-segment recompute groups by ep.segment NOT ep.sensor_id (Trap T5)"
    - "coverage_warning_json parse in try/except (ValueError, TypeError) (Trap T8)"
    - "Read-only GET handlers — AST-verified no db.add/flush/commit (Trap T6)"
key_files:
  created:
    - quirk/dashboard/api/routes/merge.py
    - tests/test_sensor_registry_status.py
    - tests/test_dashboard_sensor_registry.py
    - tests/test_dashboard_merge_latest.py
    - tests/test_dashboard_segment_filter.py
    - tests/test_dashboard_finding_segment_field.py
  modified:
    - quirk/dashboard/api/schemas.py
    - quirk/dashboard/api/routes/sensor.py
    - quirk/dashboard/api/routes/scan.py
    - quirk/dashboard/api/app.py
decisions:
  - "sensor_id/segment on CbomComponent default None (aggregated model — no per-endpoint provenance)"
  - "Unknown-segment 404: after NULL-safe filter removes all endpoints the 404 guard fires naturally"
  - "Per-segment recompute calls build_evidence_summary(eps, findings=None) — findings=None is correct (evidence uses endpoint state, not pre-derived FindingItems)"
metrics:
  duration_minutes: 7
  completed_date: "2026-05-26"
  tasks_completed: 3
  files_changed: 10
---

# Phase 111 Plan 01: Backend Read-Layer (Sensor Registry + Merge Latest + Segment Filter) Summary

Pure read-layer over Phases 107–110: sensor registry endpoint with push-status, merge/latest with per-segment Option-A score recompute, NULL-safe ?segment= filter on scan/latest, and nullable sensor_id/segment fields on FindingItem and CbomComponent.

## What Was Built

### Task 1: Schema extensions + sensor registry endpoint

**schemas.py** — added to `FindingItem` and `CbomComponent`:
- `sensor_id: Optional[str] = None`
- `segment: Optional[str] = None`

Four new Pydantic models added (these are the exact names Plan 02's `types/api.ts` must mirror):
- `SensorRegistryItem(sensor_id: str, segment: str, sensor_version: Optional[str], last_push_at: Optional[datetime], status: str)`
- `SensorRegistryResponse(sensors: List[SensorRegistryItem])`
- `MergeLatestData(scan_id, merged_at, score, endpoint_count, sensor_count, coverage_warning: Optional[Dict[str,Any]], per_segment_scores: Dict[str,int])`
- `MergeLatestResponse(merge: Optional[MergeLatestData])`

**sensor.py** — added:
- `_STALE_DAYS = 30` constant
- `_sensor_status(s, now) -> str` standalone helper (current/stale/unknown) — does NOT call `_build_coverage_warning`
- `GET /api/sensor/registry` on the existing auth-gated router (read-only, no db writes)

### Task 2: New merge router

**merge.py** (new) — `GET /api/merge/latest`:
- Router-level `Depends(require_auth)` (T-111-01)
- Graceful no-merge: returns `{"merge": null}` when no MergeRun rows exist
- `coverage_warning_json` parsed in `try/except (ValueError, TypeError)` → `None` on parse failure (T-111-03 / Trap T8)
- `_assemble_union(db)` used as read-only source (T-111-04 / Trap T6)
- Per-segment recompute groups by `ep.segment`, NOT `ep.sensor_id` (Trap T5); calls `build_evidence_summary` + `compute_readiness_score` per segment
- AST-verified: zero `db.add/flush/commit` calls in module

**app.py** — `merge` added to routes import (alphabetical), `include_router(merge.router, prefix="/api")` added alongside other routers.

### Task 3: ?segment= filter on /api/scan/latest

**scan.py** changes:
- Added `segment: Optional[str] = Query(default=None, ...)` param to `get_latest_scan`
- NULL-safe filter inserted after endpoints load, before all `_derive_*` calls:
  ```python
  if segment is not None:
      endpoints = [ep for ep in endpoints if ep.segment == segment]
  if segment is not None and not endpoints:
      raise HTTPException(status_code=404, ...)
  ```
  The `if segment is not None:` guard is mandatory (Trap T4) — omitting it would filter out NULL-segment local scan endpoints.
- `sensor_id=ep.sensor_id, segment=ep.segment` added to all 7 `FindingItem(...)` constructions in `_derive_findings`
- `CbomComponent` gains `sensor_id`/`segment` via schema defaults (None) — CBOM aggregates across endpoints so per-endpoint provenance isn't tracked at the component level

## Test Summary

| Test file | Tests | Purpose |
|-----------|-------|---------|
| test_sensor_registry_status.py | 8 | _sensor_status unit tests (current/stale/unknown boundary cases) |
| test_dashboard_sensor_registry.py | 5 | GET /api/sensor/registry endpoint tests |
| test_dashboard_merge_latest.py | 10 | GET /api/merge/latest — no-data, shape, per-segment, coverage_warning, Trap T5/T6/T8 |
| test_dashboard_segment_filter.py | 4 | ?segment= filter: NULL-safe guard (Trap T4 regression), exclude/include behavior |
| test_dashboard_finding_segment_field.py | 4 | FindingItem/CbomComponent carry sensor_id/segment keys |
| test_route_coverage.py | ✓ pass | Auth gate — new routes auto-covered by existing iterate-all-routes check |
| test_dashboard_api.py | ✓ pass | Backward compat — existing scan/findings/cbom assertions unaffected |

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all endpoints return live data from the DB.

## Note for Plan 02 executor (types/api.ts mirror)

The following Pydantic model fields were added and must be mirrored in `src/dashboard/src/types/api.ts`:

**FindingItem additions:**
```typescript
sensor_id?: string | null;
segment?: string | null;
```

**CbomComponent additions:**
```typescript
sensor_id?: string | null;
segment?: string | null;
```

**New types to add:**
```typescript
interface SensorRegistryItem {
  sensor_id: string;
  segment: string;
  sensor_version?: string | null;
  last_push_at?: string | null;  // ISO datetime string
  status: "current" | "stale" | "unknown";
}
interface SensorRegistryResponse {
  sensors: SensorRegistryItem[];
}
interface MergeLatestData {
  scan_id?: string | null;
  merged_at?: string | null;   // ISO datetime string
  score?: number | null;
  endpoint_count: number;
  sensor_count: number;
  coverage_warning?: Record<string, unknown> | null;
  per_segment_scores: Record<string, number>;
}
interface MergeLatestResponse {
  merge: MergeLatestData | null;
}
```

## Threat Flags

None — all new routes follow the existing auth-gated, read-only pattern. No new network endpoints beyond what the plan specified. No new file access, schema mutations, or trust boundary changes.

## Self-Check: PASSED

- quirk/dashboard/api/routes/merge.py — FOUND
- quirk/dashboard/api/routes/sensor.py (modified) — FOUND
- quirk/dashboard/api/schemas.py (modified) — FOUND
- quirk/dashboard/api/routes/scan.py (modified) — FOUND
- quirk/dashboard/api/app.py (modified) — FOUND
- tests/test_sensor_registry_status.py — FOUND
- tests/test_dashboard_sensor_registry.py — FOUND
- tests/test_dashboard_merge_latest.py — FOUND
- tests/test_dashboard_segment_filter.py — FOUND
- tests/test_dashboard_finding_segment_field.py — FOUND
- Commits 0ecb47b, 95c9f46, 849174a, 32c22c6, 31114fd, 00baaab — FOUND
