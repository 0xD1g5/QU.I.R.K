---
phase: 39
plan: "03"
subsystem: frontend
tags: [react, dashboard, routing, navigation, data-at-rest]
dependency_graph:
  requires: [39-02]
  provides: [DataAtRestPage component, /data-at-rest route, sidebar nav entry]
  affects: [src/dashboard/src/App.tsx, src/dashboard/src/components/sidebar.tsx]
tech_stack:
  added: []
  patterns: [useScanData hook, ScoreGauge subscore, EmptyStateCard per-section, lockstep route+nav]
key_files:
  created:
    - src/dashboard/src/pages/data-at-rest.tsx
  modified:
    - src/dashboard/src/App.tsx
    - src/dashboard/src/components/sidebar.tsx
    - quirk/dashboard/static/index.html
    - quirk/dashboard/static/assets/index-IsPyIPTZ.js
decisions:
  - Both App.tsx and sidebar.tsx changed in the same commit (D-11 lockstep, Pitfall 7 prevention)
  - ScoreGauge size={120} without isOverall (reserved for executive tab, Pitfall 8 prevention)
  - Empty-state copy verbatim from UI-SPEC Copywriting Contract
  - Placeholder "Pending table render" branches in non-empty paths to satisfy TypeScript strict mode
metrics:
  duration: "~10 minutes"
  completed: "2026-04-29"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 3
---

# Phase 39 Plan 03: Frontend Skeleton + Route/Nav Lockstep Summary

DataAtRestPage React component with ScoreGauge + 4 empty sections wired into App.tsx route and sidebar.tsx nav in a single lockstep commit.

## What Was Built

### Task 1: DataAtRestPage skeleton (commit ae1cb0e)

Created `src/dashboard/src/pages/data-at-rest.tsx`:

- Named export `DataAtRestPage` consumed by App.tsx import
- Uses `useScanData()` hook; derives `dar_findings` array via `useMemo`
- Four `useMemo` category splits: `dbFindings`, `objFindings`, `k8sFindings`, `vaultFindings` (filter on `f.category`)
- Loading state: 5x `Skeleton className="h-10 w-full"` (matches motion.tsx exactly)
- Error state: `<p className="text-muted-foreground text-sm">{error}</p>` (matches motion.tsx exactly)
- `h1` "Data at Rest" at fontSize:20, fontWeight:600
- `ScoreGauge score={data?.score.subscores.data_at_rest ?? 0} label="Data at Rest" size={120}` (no isOverall)
- Four sections in locked order with `aria-labelledby` IDs: `dar-db-heading`, `dar-obj-heading`, `dar-k8s-heading`, `dar-vault-heading`
- Each section renders `EmptyStateCard` with verbatim copy from UI-SPEC §Copywriting Contract
- TypeScript: `tsc --noEmit` passes with zero errors

### Task 2: Route + nav lockstep (commit 2a4b2b5)

Both files changed in the same commit per D-11 / Pitfall 7:

**App.tsx:**
- Added `import { DataAtRestPage } from "@/pages/data-at-rest"`
- Added `<Route path="/data-at-rest" element={<DataAtRestPage />} />` between /motion and /certificates

**sidebar.tsx:**
- Added `HardDrive` to lucide-react import block
- Inserted `{ path: "/data-at-rest", label: "Data at Rest", Icon: HardDrive }` at NAV_ITEMS[4]
- Final order: Executive · Findings · Identity · Motion · **Data at Rest** · Certificates · CBOM · Roadmap · Trends

Build: `npm run build` clean — zero TypeScript or Vite errors, bundle produced successfully.

### Build artifacts update (commit 4296323)

Updated `quirk/dashboard/static/` with new hashed bundle (DataAtRestPage added to bundle; index asset hash changed from `index-xtGSAGU6.js` to `index-IsPyIPTZ.js`).

## Deviations from Plan

None — plan executed exactly as written.

The `tdd="true"` annotation on both tasks refers to verification discipline (write code, verify immediately); there is no frontend test suite in this project (confirmed: no jest/vitest config). Both tasks verified via `tsc --noEmit` (Task 1) and `npm run build` (Task 2) as specified in `<verify>` blocks.

## Known Stubs

The four non-empty branches in each section render `EmptyStateCard message={"Pending table render — N finding(s)"}` as placeholder content. These are intentional stubs — Plan 04 replaces them with `DatabaseTable`, `ObjectStorageTable`, `KubernetesTable`, and `VaultTable` components respectively. The stubs do not affect the plan's goal (delivering a navigable, zero-console-error skeleton tab).

## Threat Flags

None. The new `/data-at-rest` route follows the identical (no) auth wrapper pattern as all sibling tabs — acceptable for this single-tenant local-only consulting tool. Documented in threat model as T-39-04 (accept disposition).

## Self-Check: PASSED

- `src/dashboard/src/pages/data-at-rest.tsx`: FOUND
- `src/dashboard/src/App.tsx` contains `/data-at-rest`: FOUND
- `src/dashboard/src/components/sidebar.tsx` contains `HardDrive`: FOUND
- Commit ae1cb0e: FOUND
- Commit 2a4b2b5: FOUND
- Commit 4296323: FOUND
