---
phase: 55-qramm-compliance-mapping-view
plan: 03
subsystem: ui
tags: [react, typescript, shadcn, tailwind, qramm, compliance-map]

# Dependency graph
requires:
  - phase: 55-01
    provides: GET /api/qramm/sessions/{id}/compliance-map endpoint with ComplianceMapRow shape

provides:
  - QRAMMComplianceMapRow TypeScript interface in src/dashboard/src/types/api.ts
  - ComplianceMapTab React component (12x8 framework compliance table, Coverage Tiers legend, footnote, unscored banner, loading/error states)
  - 6th Compliance Map tab wired into qramm-assessment.tsx via TabsTrigger + TabsContent value="compliance"

affects: [55-04, 56-pdf-export, qramm-assessment-ui]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - useEffect async fetch with cancellation guard (cancelled boolean) keyed on [ctx.sessionId, ctx.scoreResult]
    - groupRows() pivot function: flat API rows → keyed PracticeRow objects for table rendering
    - formatScore(score: number | null) → string — renders em-dash for null, toFixed(2) for numeric
    - CSS variable color tokens only — no hardcoded hex/hsl in component source

key-files:
  created:
    - src/dashboard/src/components/qramm/ComplianceMapTab.tsx
  modified:
    - src/dashboard/src/types/api.ts
    - src/dashboard/src/pages/qramm-assessment.tsx

key-decisions:
  - "Pivot groupRows() on practice_area client-side rather than fetching pre-grouped data — keeps API flat, simplifies server"
  - "isUnscored = !ctx.scoreResult || rows.every(r => r.relevance_score === null) — shows banner when no score OR all rows null"
  - "Coverage Tiers legend card shows static Scanner-informed / Manual only badge examples; scanner_informed boolean NOT rendered per-row (96 badges too dense)"

patterns-established:
  - "ComplianceMapTab self-contained: reads sessionId + scoreResult from QRAMMContext, no props"
  - "useEffect cancellation guard: let cancelled = false; return () => { cancelled = true } — matches existing ScorecardTab pattern"
  - "formatScore helper: null/undefined → em-dash U+2014; number → .toFixed(2)"

requirements-completed: [QRAMM-15]

# Metrics
duration: 15min
completed: 2026-05-08
---

# Phase 55 Plan 03: QRAMM Compliance Mapping View (React UI) Summary

**React Compliance Map tab with 12×8 framework table, Coverage Tiers legend, and per-session relevance scores from the Wave 1 API endpoint**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-05-08T00:00:00Z
- **Completed:** 2026-05-08T00:00:00Z
- **Tasks:** 3 of 4 (Task 4 is checkpoint:human-verify — awaiting human approval)
- **Files modified:** 3

## Accomplishments

- Appended `QRAMMComplianceMapRow` TypeScript interface to `src/dashboard/src/types/api.ts` matching the Wave 1 API response shape exactly
- Built self-contained `ComplianceMapTab` component: async fetch with cancellation guard, 12-row practice-area × 8-framework coverage table, Coverage Tiers legend, unscored banner, loading spinner, error card — all per the UI-SPEC
- Wired the 6th `[ Compliance Map ]` tab into `qramm-assessment.tsx` — existing 5 tabs (CVI, SGRM, DPE, ITR, Scorecard) unchanged
- Production build passes (`npm run build` exits 0); TypeScript compiles cleanly (`npx tsc --noEmit` exits 0)
- "fully compliant" grep gate: 0 occurrences; hardcoded hex color gate: 0 occurrences

## Task Commits

1. **Task 1: Append QRAMMComplianceMapRow interface to api.ts** - `21cbcf6` (feat)
2. **Task 2: Create ComplianceMapTab.tsx** - `63a2df2` (feat)
3. **Task 3: Wire 6th tab into qramm-assessment.tsx** - `345d566` (feat)

## Files Created/Modified

- `src/dashboard/src/types/api.ts` — Added `QRAMMComplianceMapRow` interface (practice_number, practice_area, dimension, framework, static_weight, relevance_score: number|null, scanner_informed: boolean)
- `src/dashboard/src/components/qramm/ComplianceMapTab.tsx` — New self-contained 6th tab component (231 lines)
- `src/dashboard/src/pages/qramm-assessment.tsx` — Added ComplianceMapTab import, TabsTrigger value="compliance", TabsContent value="compliance"

## Decisions Made

- `groupRows()` pivot done client-side from flat API rows — keeps the server endpoint simple (flat list) while the component does the keying by practice_area
- `isUnscored` check: `!ctx.scoreResult || rows.every(r => r.relevance_score === null)` — shows banner if no score object or all scores are null regardless of session state
- Coverage Tiers badges rendered once in a legend card, not inline per row — 96 badge instances would be too dense per the UI-SPEC

## Deviations from Plan

None — plan executed exactly as written. The component skeleton from the plan was used verbatim.

## Threat Surface Scan

T-55-10 (malformed JSON): mitigated — `r.ok ? r.json() : Promise.reject(r.status)` rejects non-2xx; error card shown on catch.
T-55-11 (XSS via relevance_score): mitigated — all numeric values pass through `formatScore()` → `toFixed(2)` string; rendered as JSX children only.
T-55-12 (refetch loop): mitigated — cancellation flag and narrow dependency array `[ctx.sessionId, ctx.scoreResult]`.
T-55-13 (fully compliant badge): mitigated — grep gate confirmed 0 occurrences in component and page source.

No new threat surface introduced beyond what is in the plan's threat model.

## Issues Encountered

None.

## Next Phase Readiness

- Human verification (Task 4 checkpoint) pending — user must visit `/qramm/assessment` and approve the rendered tab visually
- After approval, plan 03 is complete and QRAMM-15 is closed
- Phase 55 plan 04 (staleness CLI + tests) may proceed once this checkpoint clears

---
*Phase: 55-qramm-compliance-mapping-view*
*Completed: 2026-05-08*
