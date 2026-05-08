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
    - isUnscored derived from API data (rows.length === 0 || rows.every(r => r.relevance_score === null)), NOT ctx.scoreResult

key-files:
  created:
    - src/dashboard/src/components/qramm/ComplianceMapTab.tsx
  modified:
    - src/dashboard/src/types/api.ts
    - src/dashboard/src/pages/qramm-assessment.tsx

key-decisions:
  - "Pivot groupRows() on practice_area client-side rather than fetching pre-grouped data — keeps API flat, simplifies server"
  - "isUnscored derived from API rows, not ctx.scoreResult — ctx.scoreResult resets on page reload and is unreliable for scored-state detection across browser sessions"
  - "Coverage Tiers legend card shows static Scanner-informed / Manual only badge examples; scanner_informed boolean NOT rendered per-row (96 badges too dense)"

patterns-established:
  - "ComplianceMapTab self-contained: reads sessionId + scoreResult from QRAMMContext, no props"
  - "useEffect cancellation guard: let cancelled = false; return () => { cancelled = true } — matches existing ScorecardTab pattern"
  - "formatScore helper: null/undefined → em-dash U+2014; number → .toFixed(2)"
  - "isUnscored must use API data not React state for persistence across browser sessions"

requirements-completed: [QRAMM-15]

# Metrics
duration: 30min
completed: 2026-05-08
---

# Phase 55 Plan 03: QRAMM Compliance Mapping View (React UI) Summary

**React Compliance Map tab with 12x8 framework table, Coverage Tiers legend, and per-session relevance scores from the Wave 1 API endpoint — with bug fix for scored-state detection across browser sessions**

## Performance

- **Duration:** ~30 min (including post-checkpoint bug fix)
- **Started:** 2026-05-08T00:00:00Z
- **Completed:** 2026-05-08T14:00:00Z
- **Tasks:** 4 of 4 (Task 4 human-verify checkpoint approved)
- **Files modified:** 3

## Accomplishments

- Appended `QRAMMComplianceMapRow` TypeScript interface to `src/dashboard/src/types/api.ts` matching the Wave 1 API response shape exactly
- Built self-contained `ComplianceMapTab` component: async fetch with cancellation guard, 12-row practice-area x 8-framework coverage table, Coverage Tiers legend, unscored banner, loading spinner, error card — all per the UI-SPEC
- Wired the 6th `[ Compliance Map ]` tab into `qramm-assessment.tsx` — existing 5 tabs (CVI, SGRM, DPE, ITR, Scorecard) unchanged
- Production build passes (`npm run build` exits 0); TypeScript compiles cleanly (`npx tsc --noEmit` exits 0)
- "fully compliant" grep gate: 0 occurrences; hardcoded hex color gate: 0 occurrences
- Human verification approved: CVI rows show numeric scores for pre-scored session without needing to click Calculate Score in current browser session

## Task Commits

1. **Task 1: Append QRAMMComplianceMapRow interface to api.ts** — `21cbcf6` (feat)
2. **Task 2: Create ComplianceMapTab.tsx** — `63a2df2` (feat)
3. **Task 3: Wire 6th tab into qramm-assessment.tsx** — `345d566` (feat)
4. **Task 4: Human verification + isUnscored bug fix** — `8e695cc` (fix)

## Files Created/Modified

- `src/dashboard/src/types/api.ts` — Added `QRAMMComplianceMapRow` interface (practice_number, practice_area, dimension, framework, static_weight, relevance_score: number|null, scanner_informed: boolean)
- `src/dashboard/src/components/qramm/ComplianceMapTab.tsx` — New self-contained 6th tab component (232 lines); includes post-checkpoint isUnscored fix
- `src/dashboard/src/pages/qramm-assessment.tsx` — Added ComplianceMapTab import, TabsTrigger value="compliance", TabsContent value="compliance"
- `quirk/dashboard/static/assets/` — Rebuilt static assets (index.html + JS/CSS bundles) after isUnscored fix

## Decisions Made

- `groupRows()` pivot done client-side from flat API rows — keeps the server endpoint simple (flat list) while the component does the keying by practice_area
- `isUnscored` check: `rows.length === 0 || rows.every(r => r.relevance_score === null)` — derived from API data, not `ctx.scoreResult`; see Deviations section for the bug this fixed
- Coverage Tiers badges rendered once in a legend card, not inline per row — 96 badge instances would be too dense per the UI-SPEC

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed scored-state detection across browser sessions (isUnscored gate)**

- **Found during:** Task 4 human-verify checkpoint
- **Diagnosis:** The original implementation used `!ctx.scoreResult` as a primary gate for `isUnscored`. `ctx.scoreResult` is in-memory React state initialized to `null` on page load. Sessions that were scored in a prior browser session would always display the unscored banner on fresh page load — even though `score_json` was already persisted in the database — because `ctx.scoreResult` is `null` until the user clicks Calculate Score again in the current browser session.
- **Additional finding:** Session 1 in the DB had `score_json = NULL` during testing (the user had 30 answers but had not clicked Calculate Score in the Scorecard tab). Calling `score_session(1)` directly confirmed the backend works — session 1 now has `score_json` with CVI=1.3, overall=0.325, maturity=Basic.
- **Fix:** Changed `isUnscored` from:
  ```typescript
  const isUnscored = !ctx.scoreResult || rows.every(r => r.relevance_score === null)
  ```
  to:
  ```typescript
  const isUnscored = rows.length === 0 || rows.every(r => r.relevance_score === null)
  ```
  This derives scored-state entirely from the API response. If the compliance-map endpoint returns rows where any `relevance_score` is non-null, the session is considered scored — regardless of in-memory React state.
- **Files modified:** `src/dashboard/src/components/qramm/ComplianceMapTab.tsx` (line 111)
- **Commit:** `8e695cc`

## Threat Surface Scan

T-55-10 (malformed JSON): mitigated — `r.ok ? r.json() : Promise.reject(r.status)` rejects non-2xx; error card shown on catch.
T-55-11 (XSS via relevance_score): mitigated — all numeric values pass through `formatScore()` → `toFixed(2)` string; rendered as JSX children only.
T-55-12 (refetch loop): mitigated — cancellation flag and narrow dependency array `[ctx.sessionId, ctx.scoreResult]`.
T-55-13 (fully compliant badge): mitigated — grep gate confirmed 0 occurrences in component and page source.

No new threat surface introduced beyond what is in the plan's threat model.

## Known Stubs

None — all data is wired to the live API endpoint.

## Self-Check: PASSED

- `src/dashboard/src/components/qramm/ComplianceMapTab.tsx` — EXISTS
- `src/dashboard/src/types/api.ts` — EXISTS, contains QRAMMComplianceMapRow
- `src/dashboard/src/pages/qramm-assessment.tsx` — EXISTS, contains value="compliance" (x2)
- Commits 21cbcf6, 63a2df2, 345d566, 8e695cc — all present in git log

---
*Phase: 55-qramm-compliance-mapping-view*
*Completed: 2026-05-08*
