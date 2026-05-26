---
phase: 111-console-dashboard-awareness
verified: 2026-05-25T22:20:00Z
status: human_needed
score: 9/9 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Open the built dashboard in a browser. Click the new 'Sensors' nav item (radio icon, between Scan History and Schedules). Confirm the registry table shows Sensor ID (monospace) / Segment / Version / Last Seen / Status columns. Status badges must show a TEXT label (Current / Stale / Unknown) plus color — not color alone. With no sensors enrolled, confirm the empty-state enroll-command message appears."
    expected: "Sensors page renders correctly per 111-UI-SPEC.md §1. Status badges are visually distinct for each state and never rely on color alone."
    why_human: "Badge color (#d4893a amber for Stale, green for Current, secondary for Unknown), layout, monospace font rendering, and relative-time formatting cannot be confirmed by grep or tsc."
  - test: "Navigate to the Findings page and the CBOM page. Confirm an 'All segments' dropdown appears in the filter bar on each. Select a specific segment and verify only matching rows remain. Re-select 'All segments' and confirm all rows return, including any single-host (NULL-segment) rows."
    expected: "Segment filter on both pages works correctly; NULL-segment single-host rows are NOT dropped when 'All segments' is selected."
    why_human: "Client-side filter behavior and the presence/absence of NULL-segment rows requires running the app with real scan data."
  - test: "On the Executive page, if merge data exists with multiple segments, confirm per-segment ScoreGauges appear alongside the org-wide gauge. If a merge ran with missing sensors, confirm the amber non-dismissible banner appears ABOVE the gauges with factual copy and NO dismiss/close button. With no merge, confirm only the org-wide gauge shows and no banner appears."
    expected: "Per-segment gauges render with maxValue=100, labels truncated at 16 chars. Coverage banner uses amber styling, role=alert, no dismiss button. No-merge state shows only org-wide gauge."
    why_human: "Visual appearance of the banner (amber color, positioning above gauges), per-segment gauge sizing, and the absence of a dismiss button require visual inspection against 111-UI-SPEC.md §3/§4."
---

# Phase 111: Console Dashboard Awareness Verification Report

**Phase Goal:** A consultant using the dashboard can see which sensors are active, filter findings by segment, and immediately notice when a merged score is based on incomplete sensor coverage.
**Verified:** 2026-05-25T22:20:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | GET /api/sensor/registry returns each enrolled sensor with current/stale/unknown status | VERIFIED | `quirk/dashboard/api/routes/sensor.py` L112-133: `@router.get("/sensor/registry")` on auth-gated router; `_sensor_status()` L80-105 is standalone (does NOT call `_build_coverage_warning`); 9 tests in `test_sensor_registry_status.py` + `test_dashboard_sensor_registry.py` all pass |
| 2  | GET /api/merge/latest returns the latest merge_runs row plus per-segment scores recomputed on read (Option A), or `{"merge": null}` when no merge exists | VERIFIED | `quirk/dashboard/api/routes/merge.py` L42-107: groups by `ep.segment` (not `ep.sensor_id` — Trap T5), calls `build_evidence_summary` + `compute_readiness_score` per segment, `{"merge": None}` on no row; `test_dashboard_merge_latest.py` covers both cases; zero `db.add/flush/commit` calls confirmed by grep |
| 3  | GET /api/scan/latest?segment=<label> filters findings/CBOM to that segment; omitting the param leaves NULL-segment local scans unaffected | VERIFIED | `quirk/dashboard/api/routes/scan.py` L975: `segment: Optional[str] = Query(default=None)`; L1032-1034: `if segment is not None: endpoints = [ep for ep in endpoints if ep.segment == segment]` — mandatory NULL-safe guard; `test_dashboard_segment_filter.py` proves omitted param includes NULL-segment rows and `?segment=dmz` excludes corp/NULL |
| 4  | FindingItem and CbomComponent responses carry nullable sensor_id and segment fields | VERIFIED | `quirk/dashboard/api/schemas.py` L68-69 (FindingItem), L95-96 (CbomComponent): `sensor_id: Optional[str] = None` and `segment: Optional[str] = None` on both; `_derive_findings` and `_derive_cbom` in scan.py pass `sensor_id=ep.sensor_id, segment=ep.segment` at every construction site (8 grep matches); `test_dashboard_finding_segment_field.py` asserts field presence |
| 5  | Both new GET routes require authentication (router-level Depends(require_auth)) | VERIFIED | sensor.py L55: `router = APIRouter(dependencies=[Depends(require_auth)])` (pre-existing, registry route added to existing router); merge.py L35: `router = APIRouter(dependencies=[Depends(require_auth)])`; `test_route_coverage.py::test_all_data_routes_have_auth_dependency` PASSED with new routes registered |
| 6  | TypeScript types in types/api.ts mirror the Pydantic schema fields added in Plan 01 | VERIFIED | `src/dashboard/src/types/api.ts` L34-35 (FindingItem: `sensor_id?: string \| null`, `segment?: string \| null`), L55-56 (CbomComponent: same); L336-360: `SensorRegistryItem`, `SensorRegistryResponse`, `MergeLatestData`, `MergeLatestResponse` interfaces all present; `npx tsc --noEmit` exits 0 |
| 7  | A Sensors page (/sensors) + nav item (Radio icon) exist and are wired into App.tsx | VERIFIED | `src/dashboard/src/pages/sensors.tsx` exists (132 lines); `sidebar.tsx` L20: `Radio` in lucide import; L41: `{ path: "/sensors", label: "Sensors", Icon: Radio }`; `App.tsx` L26: `SensorsPage` imported; L75: `<Route path="/sensors" element={<SensorsPage />} />`; hooks `useSensorRegistry.ts` and `useMergeLatest.ts` both exist and use `fetchApi` with `cancelled` guard |
| 8  | Executive page renders per-segment ScoreGauges (maxValue=100) and coverage_warning banner (role=alert, non-dismissible) when merge data present | VERIFIED | `executive.tsx` L9: `AlertTriangle` in lucide import; L11: `useMergeLatest` imported; L98: `const { merge } = useMergeLatest()`; L229: `merge?.coverage_warning &&` gate; L242: `role="alert"`; L245: `AlertTriangle` aria-hidden; L292-300: per-segment ScoreGauge loop with `maxValue={100}`; grep confirms no dismiss button in the banner block |
| 9  | Frontend build succeeds: `npx tsc --noEmit` clean and `npm run build` exits 0; vitest suite (20 files, 77 tests) green | VERIFIED | `npx tsc --noEmit` — no output (clean); `npm run build` exit 0, all 8 assets emitted; `npx vitest run` — 20 test files, 77 tests, all passed |

**Score:** 9/9 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `quirk/dashboard/api/routes/sensor.py` | GET /api/sensor/registry + _sensor_status helper | VERIFIED | Route at L112; standalone `_sensor_status` at L80 |
| `quirk/dashboard/api/routes/merge.py` | GET /api/merge/latest with per-segment recompute | VERIFIED | Route at L42; groups by `ep.segment`; read-only confirmed |
| `quirk/dashboard/api/schemas.py` | SensorRegistryItem/Response, MergeLatestData/Response, nullable fields on FindingItem/CbomComponent | VERIFIED | All 4 models at L380-410; nullable fields at L68-69 and L95-96 |
| `src/dashboard/src/pages/sensors.tsx` | Sensors registry page (min 40 lines) | VERIFIED | 132 lines |
| `src/dashboard/src/hooks/useSensorRegistry.ts` | Registry fetch hook | VERIFIED | Uses fetchApi + cancelled guard |
| `src/dashboard/src/hooks/useMergeLatest.ts` | Merge/latest fetch hook | VERIFIED | Uses fetchApi + cancelled guard |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `merge.py` | `_assemble_union` + `compute_readiness_score` | per-segment recompute on read | VERIFIED | `grep _assemble_union merge.py` → L75; groups by segment not sensor_id |
| `app.py` | `merge.router` | `include_router(merge.router, prefix='/api')` | VERIFIED | L116 in app.py; `merge` in imports at L25 |
| `scan.py` | endpoints list filter | `if segment is not None` guard | VERIFIED | L1034 in scan.py |
| `types/api.ts` | `schemas.py` | mirrored `sensor_id?: string` fields | VERIFIED | L34-35, L55-56 in api.ts |
| `executive.tsx` | `/api/merge/latest` | `useMergeLatest` hook | VERIFIED | L11 import, L98 usage |
| `sensors.tsx` | `/api/sensor/registry` | `useSensorRegistry` hook | VERIFIED | Present in sensors.tsx |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `sensors.tsx` | `sensors` | `useSensorRegistry` → `fetchApi("/api/sensor/registry")` → `db.query(Sensor).all()` | Yes — ORM query over `sensors` table | FLOWING |
| `executive.tsx` (coverage banner) | `merge` | `useMergeLatest` → `fetchApi("/api/merge/latest")` → `db.query(MergeRun).first()` + `_assemble_union(db)` | Yes — DB queries, no static fallback | FLOWING |
| `findings.tsx` (segment filter) | `segmentFilter` applied to `data.findings` | Client-side filter on scan data (already flowing from useScanData) | Yes — filters existing live data | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Phase 111 backend tests | `pytest tests/test_sensor_registry_status.py tests/test_dashboard_sensor_registry.py tests/test_dashboard_merge_latest.py tests/test_dashboard_segment_filter.py tests/test_dashboard_finding_segment_field.py -q` | 33 passed | PASS |
| Auth gate covers new routes | `pytest tests/test_route_coverage.py -q` | 1 passed | PASS |
| Backward-compat: existing dashboard API | `pytest tests/test_dashboard_api.py -q` | 13 passed | PASS |
| Python compile | `python -m compileall quirk run_scan.py -q` | No output (clean) | PASS |
| TypeScript type-check | `npx tsc --noEmit` | No output (clean) | PASS |
| Frontend build | `npm run build` | Exit 0, 8 assets emitted (578ms) | PASS |
| Vitest suite | `npx vitest run` | 20 files, 77 tests, all passed | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| DASH-01 | 111-01, 111-02 | Sensor registry on console dashboard with ID/segment/version/last-seen/status badge | SATISFIED | `GET /api/sensor/registry` (sensor.py), `SensorRegistryItem` schema, `sensors.tsx` page + nav, `SensorStatusBadge` with text labels |
| DASH-02 | 111-01, 111-02 | Findings/CBOM expose sensor_id/segment dimension; per-segment filter on `/api/scan/latest` | SATISFIED | Nullable fields on `FindingItem`/`CbomComponent` in schemas.py and api.ts; `?segment=` NULL-safe guard in scan.py; "All segments" Select on findings.tsx and cbom.tsx |
| DASH-03 | 111-01, 111-02 | Per-segment score gauges + coverage_warning banner when merge ran with sensors missing | SATISFIED | `GET /api/merge/latest` per-segment recompute (merge.py); per-segment ScoreGauge `maxValue={100}` in executive.tsx; `role="alert"` non-dismissible banner gated on `merge?.coverage_warning`; graceful `{"merge": null}` on no-merge |

### Anti-Patterns Found

No TBD, FIXME, or XXX markers found in Phase 111 modified files. No stub patterns detected. The merge.py read-only constraint is enforced: zero `db.add/flush/commit` calls confirmed.

---

### Human Verification Required

#### 1. Sensors Page — Visual Appearance and Status Badges

**Test:** Start `quirk serve`, open the dashboard, click the "Sensors" nav item (radio icon). Inspect the registry table (Sensor ID / Segment / Version / Last Seen / Status columns). With no sensors enrolled, verify the empty-state enroll-command message. With sensors enrolled, verify each badge shows a readable text label (Current / Stale / Unknown) plus its color — not color alone.
**Expected:** Table renders as specified in 111-UI-SPEC.md §1. Sensor ID column is monospace, Last Seen shows relative time or "Never", status badges are visually distinct with text.
**Why human:** Badge colors (#d4893a amber, green, secondary), font rendering, relative-time output format, and the empty-state exact copy cannot be confirmed programmatically.

#### 2. Segment Filter — Runtime Behavior on Findings and CBOM Pages

**Test:** Navigate to Findings. Confirm the "All segments" dropdown appears. Select a specific segment; verify only rows from that segment remain. Re-select "All segments"; verify all rows return including any single-host (NULL-segment) rows.
**Expected:** Filter works correctly. NULL-segment single-host rows are visible under "All segments" and correctly excluded when a specific segment is chosen.
**Why human:** Client-side filter state and the visual appearance of the dropdown require running the app with actual scan data containing both segmented and NULL-segment endpoints.

#### 3. Executive Page — Per-Segment Gauges and Coverage Banner

**Test:** On the Executive page: (a) With no merge, confirm only the org-wide gauge shows, no banner. (b) With a merge and multiple segments, confirm per-segment ScoreGauges appear alongside the org-wide gauge. (c) With a merge where sensors were missing, confirm the amber banner appears ABOVE the gauges, shows a factual missing-sensor count, and has NO dismiss/close button.
**Expected:** Gauges are correctly sized (120px, maxValue=100). Labels >16 chars are truncated with ellipsis. Banner is amber, positioned above gauges, non-dismissible. Matches 111-UI-SPEC.md §3/§4.
**Why human:** Visual layout (banner above vs below gauges), amber color rendering, truncation behavior, and non-dismissible UX require visual inspection against the UI-SPEC.

---

### Gaps Summary

No automated gaps found. All 9 must-have truths verified. The `human_needed` status reflects three visual/interactive UAT items that require running the live dashboard — these were planned as human-UAT from the start (111-03-PLAN.md Task 3 `checkpoint:human-verify`). All automated invariants hold.

---

_Verified: 2026-05-25T22:20:00Z_
_Verifier: Claude (gsd-verifier)_
