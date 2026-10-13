---
type: todo
created: 2026-10-13
source: Phase 224 GC3-R3 (part 05, docs/report-interpretation.md §23 honest-absence empty state)
priority: medium
area: src/dashboard/src/pages/exposure-map.tsx
status: pending
resolves_phase: null
---

# Exposure map tab shows the honest-absence empty state when the map computation failed

When derivation fails, the route returns an empty map with `unavailable_reason` set
(`quirk/dashboard/api/routes/exposure_map.py:94-104`, WR-02), and the TS type has the field
(`src/dashboard/src/types/api.ts:736`). The page never reads it and branches only on `edges.length === 0`
(`src/dashboard/src/pages/exposure-map.tsx:328`), so a failure renders "No path data available ... Nothing is
fabricated" as if it were a true zero result. Probe `gc3-r3-f6-exposure-map-failure-probe.py`.

When fixed, update docs/report-interpretation.md §23 "The honest-absence empty state" (the failure exception sentence).

## Feasibility & Effort

- **Verdict: CONFIRMED, effort S.** `exposure_map.py:94-104`; `api.ts:736`; `exposure-map.tsx:328`.
- Fix: branch on `unavailable_reason` before `:328` with an error card; add a vitest.
