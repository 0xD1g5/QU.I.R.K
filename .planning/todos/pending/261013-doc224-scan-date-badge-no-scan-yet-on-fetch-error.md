---
type: todo
created: 2026-10-13
source: Phase 224 GC3-R3 (part 05, docs/report-interpretation.md §11 scan-date badge)
priority: low
area: src/dashboard/src/components/ScanDateBadge.tsx
status: pending
resolves_phase: null
owner: "999.137"
---

# Sidebar scan-date badge says "No scan yet" when the scan list fails to load

`useScanList` returns an `error` with empty sessions on a failed `/api/scans` request
(`src/dashboard/src/hooks/useScanList.ts:36` sets the error, `:54` returns it). `ScanDateBadge` reads only
`sessions`/`loading` (`src/dashboard/src/components/ScanDateBadge.tsx:11`) and falls through to "No scan yet" (`:17`),
telling an operator there are no scans when a 401/5xx/network error occurred.

When fixed, update docs/report-interpretation.md §11 state table ("No scan has ever been run, or the scan list could not be loaded").

## Feasibility & Effort

- **Verdict: CONFIRMED, effort S.** `useScanList.ts:36,54`; `ScanDateBadge.tsx:11,17`.
- Fix: destructure `error` and render an "unavailable" label; add a vitest.
