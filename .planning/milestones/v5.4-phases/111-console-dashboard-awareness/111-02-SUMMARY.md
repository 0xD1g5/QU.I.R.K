---
phase: "111"
plan: "02"
subsystem: dashboard-frontend
tags: [sensors-page, segment-filter, merge-gauges, coverage-banner, tdd]
dependency_graph:
  requires:
    - "111-01 (sensor registry + merge/latest endpoints + schema fields)"
  provides:
    - "GET /sensors — SensorsPage with registry table + status badges"
    - "useSensorRegistry hook (cancellation-safe, fetchApi)"
    - "useMergeLatest hook (cancellation-safe, fetchApi)"
    - "segment filter Select on FindingsPage + CbomPage"
    - "per-segment ScoreGauge rows on ExecutivePage (maxValue=100)"
    - "non-dismissible amber coverage_warning banner (role=alert) on ExecutivePage"
    - "src/dashboard/src/types/api.ts — sensor_id/segment on FindingItem/CbomComponent; 4 new types"
  affects:
    - "src/dashboard/src/types/api.ts"
    - "src/dashboard/src/hooks/useSensorRegistry.ts"
    - "src/dashboard/src/hooks/useMergeLatest.ts"
    - "src/dashboard/src/pages/sensors.tsx"
    - "src/dashboard/src/components/sidebar.tsx"
    - "src/dashboard/src/App.tsx"
    - "src/dashboard/src/pages/findings.tsx"
    - "src/dashboard/src/pages/cbom.tsx"
    - "src/dashboard/src/pages/executive.tsx"
tech_stack:
  added: []
  patterns:
    - "useScanData cancellation pattern — let cancelled; sync clear; !cancelled guards; cleanup return"
    - "fetchApi (never raw fetch) — HARDEN-API-01 enforced in both hooks"
    - "data-at-rest.tsx analog — loading skeleton (role=status), EmptyStateCard, Card/Table structure"
    - "findings.tsx/cbom.tsx segment filter pattern — segmentFilter state + distinctSegments useMemo"
    - "Recharts children statically mounted — executive.tsx Bar/Cell untouched"
    - "per-segment ScoreGauge maxValue=100 + >16-char label truncation"
    - "coverage_warning banner non-dismissible, role=alert, amber CSS variable styling"
key_files:
  created:
    - src/dashboard/src/hooks/useSensorRegistry.ts
    - src/dashboard/src/hooks/useMergeLatest.ts
    - src/dashboard/src/pages/sensors.tsx
    - src/dashboard/src/pages/__tests__/sensors-loading.test.tsx
  modified:
    - src/dashboard/src/types/api.ts
    - src/dashboard/src/components/sidebar.tsx
    - src/dashboard/src/App.tsx
    - src/dashboard/src/pages/findings.tsx
    - src/dashboard/src/pages/cbom.tsx
    - src/dashboard/src/pages/executive.tsx
    - quirk/dashboard/static/ (rebuilt statics)
decisions:
  - "segment filter state per-page (not a shared context) — simplest; consistent with existing severityFilter/protocolFilter pattern"
  - "distinctSegments derived from components/findings locally — no additional API call"
  - "coverage banner uses IIFE render pattern to scope missingSensors derivation cleanly inline"
  - "coverage_warning typed as Record<string,unknown> in TS; cast to { missing_sensors?: string[] } inline in render"
metrics:
  duration_minutes: 15
  completed_date: "2026-05-26"
  tasks_completed: 3
  files_changed: 11
---

# Phase 111 Plan 02: Frontend — Sensors Page, Segment Filters, Executive Awareness Summary

TypeScript types mirrored from Plan 01 schemas, two cancellation-safe fetch hooks created, Sensors registry page with text+color status badges, segment filter Select added to Findings and CBOM views, per-segment ScoreGauges and non-dismissible amber coverage_warning banner added to Executive — npm run build exits 0 and Sensors vitest passes 3/3.

## What Was Built

### Task 1: Mirror TS types + add useSensorRegistry / useMergeLatest hooks

**types/api.ts** — extended existing interfaces and added new types (Trap T3 — mirror Plan 01 exactly):
- `FindingItem` gains `sensor_id?: string | null` and `segment?: string | null`
- `CbomComponent` gains `sensor_id?: string | null` and `segment?: string | null`
- New `SensorRegistryItem` (sensor_id, segment, sensor_version?, last_push_at?, status: "current"|"stale"|"unknown")
- New `SensorRegistryResponse` (sensors: SensorRegistryItem[])
- New `MergeLatestData` (scan_id, merged_at, score, endpoint_count, sensor_count, coverage_warning?, per_segment_scores)
- New `MergeLatestResponse` (merge: MergeLatestData | null)

**useSensorRegistry.ts** — fetches `/api/sensor/registry`, exposes `{ sensors, loading, error }`. Follows useScanData cancellation pattern: `let cancelled = false`, sync state clear before fetch, `if (!cancelled)` guards on all setState calls, `return () => { cancelled = true }` cleanup. Uses `fetchApi` (HARDEN-API-01 — never raw `fetch`).

**useMergeLatest.ts** — fetches `/api/merge/latest`, exposes `{ merge, loading, error }`. Identical cancellation pattern. Returns `json.merge ?? null` on success.

**Verification:** `npx tsc --noEmit` clean.

### Task 2: Sensors page + nav/route wiring + segment Select on Findings & CBOM

**sensors.tsx** — mirrors data-at-rest.tsx page structure: loading skeleton (`role="status"`, `aria-label="Loading sensors"`, `sr-only` "Loading...", 1 heading + 5 table rows), error → muted `<p>`, empty → `EmptyStateCard` with exact UI-SPEC enroll-command copy, populated → h1 "Sensors" + Card/CardContent p-0 + Table (5 columns). `SensorStatusBadge` helper: `current` → `bg-[hsl(var(--quantum-safe))] text-white`; `stale` → amber `bg-[#d4893a]/10` pattern; `unknown` → `variant="secondary"`. All three badges render text label + aria-label (accessibility rule — no color-only status). Relative-time helper using inline math (no date library).

**sidebar.tsx** — added `Radio` to lucide-react named import block (Trap T1 — omission causes runtime undefined). Inserted `{ path: "/sensors", label: "Sensors", Icon: Radio }` after `/scans` and before `/schedules` in `NAV_ITEMS`.

**App.tsx** — imported `{ SensorsPage }` and added `<Route path="/sensors" element={<SensorsPage />} />`.

**findings.tsx** — added `segmentFilter` state (default `"all"`), `distinctSegments` useMemo (`.map(f => f.segment).filter(Boolean)`, sorted, deduped), segment Select with `aria-label="Filter by segment"` and `className="w-40 h-8 text-sm"` placed after protocolFilter Select. Filter predicate: `if (segmentFilter !== "all") filtered = filtered.filter(f => f.segment === segmentFilter)`.

**cbom.tsx** — same segment filter pattern applied inside `CbomTable` component where `qsFilter` already lives. `distinctSegments` derived from `components` prop. Segment Select placed after qsFilter Select. Filter combined with existing `matchQs` and `matchSearch` in the filtered useMemo.

**Verification:** `npx tsc --noEmit` clean.

### Task 3: Executive per-segment gauges + coverage banner, npm build, Sensors vitest

**executive.tsx** changes:
- `AlertTriangle` added to lucide-react import block (Trap T2 — not previously imported here)
- `useMergeLatest` imported from `@/hooks/useMergeLatest`; `const { merge } = useMergeLatest()` called at component top
- Coverage banner inserted immediately before `<RegressionAlertChip />` inside the `space-y-8` block: gated on `merge?.coverage_warning`, renders `role="alert"` `aria-live="polite"` amber div with AlertTriangle icon (`aria-hidden`), heading "Incomplete sensor coverage", factual body copy with missing sensor count + optional sensor list, NO dismiss button (permanent until condition resolves per UI-SPEC §4)
- Per-segment gauges inserted after existing subscore gauges inside `flex flex-wrap justify-around gap-8` div: `Object.entries(merge.per_segment_scores).map(...)` rendering `<ScoreGauge key={seg} score={segScore} label={truncatedLabel} size={120} maxValue={100} />` with label truncated at 16 chars (`seg.slice(0, 15) + "…"`)
- Existing Recharts `<Bar>` / `<Cell>` children left completely untouched (statically mounted — project rule)

**sensors-loading.test.tsx** — 3 vitest cases:
1. Loading skeleton renders `role="status"` with correct aria-label
2. Empty state renders enroll-command copy
3. Populated state renders one row per sensor with status text labels present (Current/Stale/Unknown)

**Build:** `npm run build` exits 0 (501ms, 2422 modules, statics rebuilt).

## Test Summary

| Test file | Tests | Pass/Fail |
|-----------|-------|-----------|
| sensors-loading.test.tsx | 3 | 3 PASS |

`npx tsc --noEmit` — clean (0 errors) before and after each task.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all components wire to live data via hooks. No hardcoded placeholders.

## Threat Flags

None — all new fetch calls route through `fetchApi` (X-API-Key + X-Quirk-Request CSRF headers). No new network endpoints, no new file access patterns, no schema mutations.

## Self-Check: PASSED

- src/dashboard/src/hooks/useSensorRegistry.ts — FOUND
- src/dashboard/src/hooks/useMergeLatest.ts — FOUND
- src/dashboard/src/pages/sensors.tsx — FOUND
- src/dashboard/src/pages/__tests__/sensors-loading.test.tsx — FOUND
- src/dashboard/src/types/api.ts (modified — sensor_id/segment on both interfaces, 4 new types) — FOUND
- src/dashboard/src/components/sidebar.tsx (Radio import + /sensors NAV_ITEM) — FOUND
- src/dashboard/src/App.tsx (/sensors route) — FOUND
- src/dashboard/src/pages/findings.tsx (segmentFilter + distinctSegments + Select) — FOUND
- src/dashboard/src/pages/cbom.tsx (segmentFilter + distinctSegments + Select) — FOUND
- src/dashboard/src/pages/executive.tsx (AlertTriangle + useMergeLatest + banner + per-segment gauges) — FOUND
- Commits 3e2a4d1, 44fc3b6, 40dcebc — FOUND
- npm run build: 0 exit code, 501ms, 2422 modules — PASSED
- npx vitest run sensors-loading.test.tsx: 3/3 PASS — PASSED
