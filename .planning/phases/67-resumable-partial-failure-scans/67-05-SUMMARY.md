---
phase: 67-resumable-partial-failure-scans
plan: "05"
subsystem: dashboard-api-ui
tags: [partial-failures, dashboard, api, react, pydantic]
dependency_graph:
  requires: [67-01, 67-02]
  provides: [RESUME-02-dashboard]
  affects: [quirk/dashboard/api/schemas.py, quirk/dashboard/api/routes/scan.py, src/dashboard/src/types/api.ts, src/dashboard/src/pages/executive.tsx]
tech_stack:
  added: []
  patterns: [conditional-render, pydantic-extension, typescript-interface-mirror]
key_files:
  modified:
    - quirk/dashboard/api/schemas.py
    - quirk/dashboard/api/routes/scan.py
    - src/dashboard/src/types/api.ts
    - src/dashboard/src/pages/executive.tsx
decisions:
  - Partial failures read via optional chaining on data.partial_failures to avoid null-access when data is null
  - error_category drives badge color: missing_extra=Skipped(gray), exception=Failed(red), other=Partial(amber)
  - PartialFailureEntry optional (?) on ScanLatestResponse TS interface for forward-compat with older API responses
metrics:
  duration: "~15 minutes"
  completed: "2026-05-14"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 4
---

# Phase 67 Plan 05: Dashboard API + Scanner Status Card Summary

Dashboard half of RESUME-02: PartialFailureEntry Pydantic model in schemas.py, partial_failures field on ScanLatestResponse, population from scan_checkpoints in get_latest_scan(), TypeScript interface mirror in api.ts, and ScannerStatusCard component on the Executive Summary page.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | PartialFailureEntry model + ScanLatestResponse extension + get_latest_scan() population | 49de94e | quirk/dashboard/api/schemas.py, quirk/dashboard/api/routes/scan.py |
| 2 | TypeScript types + Scanner Status card + dashboard build | db04b03 | src/dashboard/src/types/api.ts, src/dashboard/src/pages/executive.tsx |

## What Was Built

### Task 1: Python Backend

**quirk/dashboard/api/schemas.py:**
- Added `PartialFailureEntry` Pydantic model with 5 fields: `stage`, `scanner`, `error_category`, `error_message`, `endpoint_count` (default 0)
- Extended `ScanLatestResponse` with `partial_failures: List[PartialFailureEntry] = []`

**quirk/dashboard/api/routes/scan.py:**
- Imported `PartialFailureEntry` from schemas
- Added `_load_partial_failures(db, scan_run_id_str)` helper that reads `ScanCheckpoint` rows where `partial_failure == True`, parses `error_summary` JSON, and returns a list of `PartialFailureEntry` objects
- Returns `[]` gracefully for pre-Phase 67 scans (no ScanCheckpoint rows) and clean scans
- JSON parse errors are silently skipped per entry; outer exceptions return `[]`
- Wired into `get_latest_scan()` before the `return ScanLatestResponse(...)` call

### Task 2: TypeScript + React UI

**src/dashboard/src/types/api.ts:**
- Added `PartialFailureEntry` interface matching the Pydantic model exactly
- Extended `ScanLatestResponse` interface with `partial_failures?: PartialFailureEntry[]`

**src/dashboard/src/pages/executive.tsx:**
- Imported `PartialFailureEntry` type
- Added `ScannerStatusCard` component before `ExecutivePage`:
  - Renders one row per failure with stage, scanner label, status badge, error_category, and error_message
  - Badge logic: `missing_extra` → Skipped (gray, `variant="secondary"`), `exception` → Failed (red, `variant="destructive"`), other → Partial (amber custom className)
  - Each badge has `aria-label="status: Skipped|Failed|Partial"`
  - Error message rendered as plain JSX string child with `truncate max-w-[60ch]` and `title={entry.error_message}` for hover tooltip
- Card renders conditionally: `{data.partial_failures && data.partial_failures.length > 0 && ...}`
- Placement: after Severity Breakdown card, before scan metadata paragraph

**Build:** `npm run build` exits 0 with no TypeScript errors.

## Verification Results

```
python -m compileall quirk/dashboard/api/schemas.py quirk/dashboard/api/routes/scan.py  → OK
PartialFailureEntry and ScanLatestResponse extension OK
_load_partial_failures importable OK
npm run build  → ✓ built in 591ms (no TypeScript errors)
PartialFailureEntry occurrences in api.ts: 2
ScannerStatusCard occurrences in executive.tsx: 2
```

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. The Scanner Status card renders from live API data (`data.partial_failures` from `GET /api/scan/latest`). For clean scans, the card is simply hidden.

## Threat Flags

No new threat surface beyond the plan's `<threat_model>`. The `/api/scan/latest` route already requires auth via `require_auth` at the router level. `error_message` values are operator-facing diagnostic strings rendered as safe JSX text children (React escapes by default).

## Self-Check

- [x] quirk/dashboard/api/schemas.py modified — PartialFailureEntry class present
- [x] quirk/dashboard/api/routes/scan.py modified — _load_partial_failures + import + wired
- [x] src/dashboard/src/types/api.ts modified — PartialFailureEntry interface + ScanLatestResponse extension
- [x] src/dashboard/src/pages/executive.tsx modified — ScannerStatusCard component + conditional render
- [x] Commit 49de94e — feat(67-05): PartialFailureEntry model + partial_failures in ScanLatestResponse
- [x] Commit db04b03 — feat(67-05): TypeScript types + ScannerStatusCard on Executive Summary page
- [x] npm run build exits 0

## Self-Check: PASSED
