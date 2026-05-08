---
phase: 56-pdf-export-staleness-enforcement
plan: "01"
subsystem: dashboard-hooks
tags: [react, hooks, qramm, print, typescript]
dependency_graph:
  requires: []
  provides: [useQRAMMPrintData hook]
  affects: [print route, QRAMM governance section]
tech_stack:
  added: []
  patterns: [cancellation guard, parallel fetch with Promise.all, null-on-no-session pattern]
key_files:
  created:
    - src/dashboard/src/hooks/useQRAMMPrintData.ts
  modified: []
decisions:
  - "Separate print-only hook — does not reuse useQRAMMSession (D-03)"
  - "Null payloads on no-scored-session path are not an error (D-04, D-05)"
  - "Empty dependency array — fetch once on mount for print use case"
metrics:
  duration: "< 5 minutes"
  completed: "2026-05-08"
  tasks_completed: 1
  files_created: 1
  files_modified: 0
requirements: [QRAMM-16]
---

# Phase 56 Plan 01: useQRAMMPrintData Hook Summary

## One-liner

React hook `useQRAMMPrintData` that selects the most-recent scored QRAMM session and parallel-fetches its score + compliance-map for the PDF print route.

## What Was Built

### Task 1: Create useQRAMMPrintData hook

Created `src/dashboard/src/hooks/useQRAMMPrintData.ts` — a print-scoped data hook that:

1. Fetches `/api/qramm/sessions` to get the session list
2. Selects the first entry where `status === "scored"` (most-recent-first ordering per qramm.py)
3. When a scored session is found, issues `Promise.all` to parallel-fetch both `/api/qramm/sessions/{id}/score` and `/api/qramm/sessions/{id}/compliance-map`
4. When no scored session exists, resolves cleanly with `{ scoreResult: null, complianceRows: null, loading: false, error: null }` — NOT an error condition
5. On HTTP errors, sets `error` to `"API error: {status} {statusText}"` matching the existing useScanData pattern
6. On exceptions, sets `error` to `err.message` or `"Failed to load QRAMM data"` as fallback
7. Uses `let cancelled = false` cancellation guard with cleanup function setting `cancelled = true`

Return shape: `{ scoreResult: QRAMMScoreResponse | null, complianceRows: QRAMMComplianceMapRow[] | null, loading: boolean, error: string | null }`

**Commit:** `84205eb`

## Deviations from Plan

None — plan executed exactly as written.

## Threat Mitigations Applied

- **T-56-02 (Information Disclosure):** Error strings expose only `resp.status`/`resp.statusText` — no auth tokens or payload echo.
- **T-56-03 (DoS / unmount race):** Cancellation guard prevents state writes after unmount; empty deps array prevents re-fetch loop.

## Known Stubs

None — hook is fully wired to live API endpoints. No hardcoded data, no placeholder values.

## Threat Flags

None — no new trust boundary surfaces introduced. Hook uses same-origin fetch to existing `/api/qramm/*` endpoints already present from Phase 55.

## Self-Check: PASSED

- `src/dashboard/src/hooks/useQRAMMPrintData.ts` — FOUND
- Commit `84205eb` — verified via `git rev-parse --short HEAD`
- TypeScript compilation: zero errors referencing `useQRAMMPrintData.ts`
- All acceptance criteria grep checks: PASS
