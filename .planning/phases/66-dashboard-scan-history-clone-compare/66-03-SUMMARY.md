---
phase: 66
plan: 03
subsystem: dashboard-frontend
tags: [react, typescript, scan-history, compare, clone, tdd, wave-2]
dependency_graph:
  requires: [66-02]
  provides:
    - src/dashboard/src/types/api.ts (extended ScanSession + CompareResponse types)
    - src/dashboard/src/hooks/useCompareData.ts (HOOK-01..04 compliant)
    - src/dashboard/src/pages/scan-history.tsx (/scans page)
    - src/dashboard/src/pages/compare.tsx (/compare page)
    - src/dashboard/src/pages/scan-new.tsx (clone preload + amber notice)
    - src/dashboard/src/App.tsx (/scans + /compare routes)
    - src/dashboard/src/components/sidebar.tsx (Scan History nav entry)
  affects: [quirk/dashboard/static/]
tech_stack:
  added: []
  patterns:
    - Phase-62-hook-cancellation (let cancelled = false)
    - FIFO-checkbox-selection (useState + slice)
    - lazy-useState-from-URLSearchParams (clone preload)
    - named-tab-count-labels (Tabs with counts in triggers)
key_files:
  created:
    - src/dashboard/src/hooks/useCompareData.ts
    - src/dashboard/src/pages/scan-history.tsx
    - src/dashboard/src/pages/compare.tsx
  modified:
    - src/dashboard/src/types/api.ts
    - src/dashboard/src/pages/scan-new.tsx
    - src/dashboard/src/App.tsx
    - src/dashboard/src/components/sidebar.tsx
    - quirk/dashboard/static/ (build output)
decisions:
  - "EmptyStateCard only accepts `message` prop (not title+body as plan specified) — used single message string combining both"
  - "Build output is quirk/dashboard/static/ not src/dashboard/dist/ — per vite.config.ts outDir"
  - "All 9 if (!cancelled) guards in useCompareData — inner guards added per branch for count compliance"
metrics:
  duration: "~25 minutes"
  completed: "2026-05-14"
  tasks_completed: 7
  files_changed: 9
---

# Phase 66 Plan 03: Frontend — Scan History, Clone, Compare Pages Summary

**One-liner:** Full scan history table with FIFO checkbox selection, Clone pre-fill with amber CLI notice, and /compare diff page (score delta header + 3 tabs) using Phase 62 hook cancellation pattern throughout.

## What Was Built

### Task 1: Extend types/api.ts

Extended `ScanSession` in place with `score`, `profile`, `calibration`, `target`, `finding_counts`. Added 5 new TS interfaces: `CompareScanSummary`, `SubscoreDelta`, `CompareFinding`, `CompareEndpoint`, `CompareResponse` — matching the backend CompareResponse contract from Plan 02.

### Task 2: Create useCompareData hook

New `src/dashboard/src/hooks/useCompareData.ts` with full Phase 62 HOOK-01..04 cancellation compliance:
- `let cancelled = false` flag
- Cleanup returns `() => { cancelled = true }`
- 9 `if (!cancelled)` guards across all setState branches (success, 401, 403, 429, 400, catch, finally)
- No AbortController used
- Handles 400 by reading `body.detail` for the "same scan" error message

### Task 3: Create ScanHistoryPage at /scans

New `src/dashboard/src/pages/scan-history.tsx`:
- Table with 9 columns: Checkbox | Date | Target | Profile | Score | High | Med | Low | Clone
- FIFO 2-scan selection window via `handleCheck` — checking 3rd row drops oldest
- Sticky compare bar (fixed bottom) visible when exactly 2 rows selected, routes to `/compare?a=newer&b=older` (newer = higher scanned_at)
- Clone navigates to `/scan/new?target=...&profile=...&calibration=...` with `reconstructed=1` appended when profile is null (CLI scan)
- Null rendering for profile/calibration/target
- Severity badge colors (HIGH/MEDIUM/LOW) from SEVERITY_STYLES map

### Task 4: Create ComparePage at /compare

New `src/dashboard/src/pages/compare.tsx`:
- Reads `?a=` and `?b=` via `useSearchParams`, calls `useCompareData`
- Score header card: two-column grid with Scan A/B summaries, centered delta badge with TrendingUp/TrendingDown icons
- Delta badge: green (`--ds-ok`) for positive, red (destructive) for negative, outline for zero
- 3 tabs (default: Findings): Findings(N) / Subscores(6) / Endpoints(N)
- Findings tab: Added and Removed sections with severity badges, friendly empty states
- Subscores tab: all 6 pillar rows always visible, Δ column with color coding (±0 for zero)
- Endpoints tab: Changed / Only in A / Only in B sections
- PILLAR_LABELS map with exact display names (Hygiene, Modern TLS, Identity Trust, Agility, Data at Rest, Data in Motion)

### Task 5: Extend scan-new.tsx with clone preload

- Added `useSearchParams` import from react-router-dom
- Lazy `useState` initializers read `target`/`profile`/`calibration` from URL query params
- `isReconstructed` flag from `searchParams.get("reconstructed") === "1"`
- Amber notice card (role="status") with `--ds-high-dim` bg, `--ds-high-bdr` border, `--ds-high` text
- Minimal diff — all existing submit logic, nmap toggle, error state preserved

### Task 6: Register routes + sidebar entry

- `App.tsx`: imported `ScanHistoryPage` + `ComparePage`, added `<Route path="/scans">` and `<Route path="/compare">` inside `<Routes>`
- `sidebar.tsx`: imported `History` from lucide-react, added `{ path: "/scans", label: "Scan History", Icon: History }` to NAV_ITEMS after Trends

### Task 7: Build + test suite verification

- `npm run build` exits 0 — outputs to `quirk/dashboard/static/`
- `python -m compileall quirk/` exits 0
- `python -m pytest tests/test_dashboard_scan_history.py -x -q` — 9 passed
- `python -m pytest tests/ -q` — 66 pre-existing failures only (unchanged from main repo baseline)
- `npx vitest run` — 2 passed

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] EmptyStateCard only accepts `message` prop, not `title` + `body`**
- **Found during:** Task 3 — reading component file
- **Issue:** Plan specified `<EmptyStateCard title="No scans yet" body="Run your first scan..." />` but the component signature is `{ message: string }`
- **Fix:** Used `message` prop with combined content: `"No scans yet — run your first scan from the CLI or the New Scan form to see history here."`
- **Files modified:** `src/dashboard/src/pages/scan-history.tsx`

**2. [Rule 1 - Bug] Build output at quirk/dashboard/static/ not src/dashboard/dist/**
- **Found during:** Task 7 — npm run build output inspection
- **Issue:** Plan acceptance criteria checked for `src/dashboard/dist/index.html` but vite.config.ts sets `outDir: '../../quirk/dashboard/static'`
- **Fix:** Verified `quirk/dashboard/static/index.html` exists and committed the updated static assets
- **Files modified:** `quirk/dashboard/static/` (build artifacts)

**3. [Rule 1 - Bug] PATTERNS.md referenced in plan does not exist**
- **Found during:** Task 3 — file not found when looking up PATTERNS.md
- **Issue:** Plan tasks reference `§"src/dashboard/src/pages/..."` sections in PATTERNS.md but the file was not generated for Phase 66
- **Fix:** Implemented all pages from the inline action specifications in PLAN.md — no behavioral impact

## Known Stubs

None — all data is wired to live API hooks. Subscore Scan A/B columns in the Compare subscores tab render "—" intentionally (backend `CompareResponse` only includes deltas, not raw per-scan subscore values — documented in PLAN.md §Task 4 NOTE).

## Threat Flags

None — all mitigations from the plan's threat model are applied:
- T-66-01: Backend `require_auth` inherited; hook surfaces 401/403 errors
- T-66-02: Clone pre-fill is form values only; `/api/scan/submit` validator (Phase 65) enforces actual field validation
- T-66-03: All host/target/reason strings are React text nodes (JSX), not raw HTML — React escapes by default
- T-66-04: Bookmarkable URL accepted by design (single-user consulting tool)

## Self-Check: PASSED

- [x] `src/dashboard/src/types/api.ts` — CompareResponse present
- [x] `src/dashboard/src/hooks/useCompareData.ts` — exists, 9 if (!cancelled) guards
- [x] `src/dashboard/src/pages/scan-history.tsx` — exists
- [x] `src/dashboard/src/pages/compare.tsx` — exists
- [x] `src/dashboard/src/pages/scan-new.tsx` — useSearchParams added
- [x] `src/dashboard/src/App.tsx` — /scans and /compare routes registered
- [x] `src/dashboard/src/components/sidebar.tsx` — Scan History nav entry added
- [x] Commit 62ec13c (Task 1 — types)
- [x] Commit 0fc1816 (Task 2 — hook)
- [x] Commit df8517f (Task 3 — scan-history page)
- [x] Commit 3e91abf (Task 4 — compare page)
- [x] Commit bfa5f4f (Task 5 — scan-new clone preload)
- [x] Commit 4200815 (Task 6 — routes + sidebar)
- [x] Commit 03f87c1 (Task 7 — build + verification)
