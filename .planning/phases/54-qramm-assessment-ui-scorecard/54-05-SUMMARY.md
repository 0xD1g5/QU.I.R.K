---
phase: 54-qramm-assessment-ui-scorecard
plan: "05"
subsystem: qramm-frontend
tags: [qramm, react, recharts, scorecard, a11y]

dependency_graph:
  requires:
    - phase: 54-plan-01
      provides: POST /api/qramm/sessions/{id}/score
    - phase: 54-plan-02
      provides: QRAMMContext, qramm-benchmarks.ts, qramm-constants.ts
    - phase: 54-plan-04
      provides: AssessmentPage with ScorecardPlaceholder stub
  provides:
    - src/dashboard/src/components/qramm/ScorecardTab.tsx
    - /qramm and /qramm/assessment a11y harness route registration
    - src/dashboard/tests/a11y/fixture-qramm.json (120-question mock catalog)
  affects:
    - Phase 56 PDF export (isAnimationActive={false} on both Radar elements)

tech_stack:
  added: []
  patterns:
    - "recharts RadarChart with PolarGrid + PolarAngleAxis + two conditional Radar elements"
    - "Explicit Calculate Score button as sole POST /score trigger (D-11)"
    - "Pitfall 4 guard: Radar elements only rendered when scoreResult is non-null; pre-calculate shows callout text"
    - "rgba() RGBA literals for chart fills per UI-SPEC (no #hex literals used)"
    - "a11y fixture auto-discovery pattern: vite.config.ts a11yFixture plugin extended with specificity-ordered QRAMM URL routing"

key_files:
  created:
    - src/dashboard/src/components/qramm/ScorecardTab.tsx (266 lines)
    - src/dashboard/tests/a11y/fixture-qramm.json (1477 lines — 120 questions + session/answer mocks)
  modified:
    - src/dashboard/src/pages/qramm-assessment.tsx (269 -> 256 lines — removed ScorecardPlaceholder, added ScorecardTab import + usage)
    - src/dashboard/tests/a11y/routes.json (9 -> 11 routes — added /qramm and /qramm/assessment)
    - src/dashboard/vite.config.ts (69 -> 124 lines — extended a11yFixture plugin with QRAMM API mocking)

decisions:
  - "Radar elements conditionally rendered only when scoreResult is non-null — prevents invisible all-zeros polygon (Pitfall 4)"
  - "isAnimationActive={false} on both Assessment and Benchmark Radar elements for Phase 56 PDF SVG capture compatibility"
  - "Industry benchmark Radar overlaid only when getBenchmarks(ctx.profile?.industry) returns non-null"
  - "Maturity distribution approximates per-dimension bucketing since /score endpoint returns dimension-level not practice-area-level scores"
  - "vite.config.ts QRAMM URL matching uses specificity-ordered if-chain (sessions/{id}/answers before sessions/{id} before sessions) to avoid prefix collisions"
  - "120 stub questions generated Python-side for fixture-qramm.json to satisfy AssessmentPage rendering invariants (useMemo grouping by practice_area)"
  - "node_modules symlinked from main repo worktree following plan 04 pattern (Rule 3 — blocking dev environment issue)"

metrics:
  duration_minutes: 20
  completed_date: "2026-05-07"
  tasks_completed: 2
  tasks_total: 2
  files_created: 2
  files_modified: 3
---

# Phase 54 Plan 05: QRAMM Scorecard Tab Summary

**One-liner:** Real ScorecardTab with recharts RadarChart (4 axes, isAnimationActive=false), dimension summary table, maturity distribution panel, and explicit Calculate Score button wired to POST /api/qramm/sessions/{id}/score, replacing the plan 04 placeholder; a11y harness extended with /qramm and /qramm/assessment route registration and 120-question QRAMM API fixture.

## What Was Built

### Task 1: ScorecardTab component + replace placeholder

`src/dashboard/src/components/qramm/ScorecardTab.tsx` (266 lines) implements QRAMM-11 in full:

**Calculate Score action (D-11 compliance):**
- Single Button with `variant="default"` and `className="w-full"` that calls POST `/api/qramm/sessions/${sessionId}/score`
- Body includes `profile_multiplier` from `QRAMMContext.profile?.multiplier`
- Inline `<Loader2>` spinner while in-flight; `calculating` state disables button preventing concurrent requests (T-54-24 mitigation)
- Error message renders below button on failure; clears on next Calculate click
- Scores are never recalculated on answer changes — only on explicit button click

**RadarChart (recharts):**
- `RadarChart` with `PolarGrid`, `PolarAngleAxis` (4 axes: CVI, SGRM, DPE, ITR)
- `role="img"` and `aria-label="QRAMM radar chart showing dimension scores"` for a11y
- Assessment `Radar`: `fill="rgba(75, 168, 168, 0.20)"`, `stroke="hsl(var(--accent))"`, `isAnimationActive={false}`
- Benchmark `Radar`: `fill="rgba(110, 122, 149, 0.15)"`, `stroke="hsl(var(--muted-foreground))"`, `strokeDasharray="4 2"`, `isAnimationActive={false}`; only rendered when `getBenchmarks(profile.industry)` returns non-null
- Pitfall 4 fix: both Radar elements are conditionally rendered only when `ctx.scoreResult` is non-null; pre-calculate state shows axis labels + muted callout text (no invisible zero polygon)

**Dimension summary table:**
- Columns: Dimension | Raw Score | Weighted Score | Industry Benchmark | Maturity Level | Completion %
- Numeric cells use `className="font-data"` (Raw Score, Weighted Score, Industry Benchmark, Completion %)
- Maturity Level cell renders `<Badge className={MATURITY_BADGE_CLASS[maturityInt]}>` with `MATURITY_LABEL[maturityInt]` text
- "—" shown in all numeric cells when scoreResult is null

**Maturity distribution panel:**
- Shows 4 maturity levels (Optimizing, Established, Developing, Basic) in reverse order
- Horizontal progress bar using `MATURITY_BADGE_CLASS` for semantic color
- Count via dimension score rounding and bucketing (approximation — /score endpoint is dimension-level only)
- Displays "—" when scoreResult is null

**Completion percentage (client-side computation):**
- `completionByDim` computed via `useMemo` from `ctx.answers` Map
- Question number ranges: 1-30 = CVI, 31-60 = SGRM, 61-90 = DPE, 91-120 = ITR
- Falls back to 0% correctly when no answers exist

`src/dashboard/src/pages/qramm-assessment.tsx` patched:
- Removed inline `ScorecardPlaceholder` component (269 → 256 lines)
- Added `import { ScorecardTab } from "@/components/qramm/ScorecardTab"`
- `<TabsContent value="scorecard">` now renders `<ScorecardTab />` (import + usage = 2 occurrences)

### Task 2: A11y route registration + QRAMM API fixture

`src/dashboard/tests/a11y/routes.json`: Added 2 entries (9 → 11 total):
- `{ "slug": "qramm", "path": "/qramm" }`
- `{ "slug": "qramm-assessment", "path": "/qramm/assessment" }`

`src/dashboard/tests/a11y/fixture-qramm.json` (1477 lines, 4 keys):
- `GET /api/qramm/sessions` — array with 1 Acme Corp draft session
- `GET /api/qramm/sessions/1` — single session detail with profile_id: null
- `GET /api/qramm/sessions/1/answers` — 2 answer rows (one answered, one auto-suggested)
- `GET /api/qramm/questions` — 120 questions (4 dimensions × 3 practice areas × 10 questions each) with correct dimension/practice_area classification, satisfying AssessmentPage's `useMemo` grouping-by-practice_area invariant

`src/dashboard/vite.config.ts` (69 → 124 lines): Extended `a11yFixture` plugin:
- Loads `fixture-qramm.json` at plugin init time following scan/trends pattern
- Specificity-ordered URL routing: `sessions/{id}/answers` → `sessions/{id}` → `sessions` → `questions` → `profiles`
- POST to `profiles` returns a fixed mock response (no fixture key needed — profiles POST only called from OrgProfilePage)

## Build Output

```
vite v8.0.3 building for production
2392 modules transformed
index-CZ2axfbN.js   245.84 kB gzip: 70.25 kB
vendor-charts-dmjVwZdK.js   398.94 kB gzip: 104.35 kB
built in 333ms
```

## A11y Harness Status

`npm run a11y:check` was NOT run in this plan (requires Chrome and puppeteer-core). The two new routes are registered and the fixture is wired. Baseline capture (`npm run a11y:baseline`) is a developer-run step per VALIDATION.md Wave 0 note.

## No #hex Literals

Confirmed: `grep -E '#[0-9a-fA-F]{3,8}' ScorecardTab.tsx` returns no matches. The two RGBA fill values (`rgba(75, 168, 168, 0.20)` and `rgba(110, 122, 149, 0.15)`) are the only color literals present — these are the documented UI-SPEC §Color approximations of the accent and muted-foreground tokens at prescribed opacities.

## isAnimationActive={false} Confirmation

Both Radar elements in ScorecardTab.tsx have `isAnimationActive={false}`:
- Line for Assessment Radar: `isAnimationActive={false}`
- Line for Benchmark Radar: `isAnimationActive={false}`
Count confirmed: `grep -c 'isAnimationActive={false}'` returns 2.

## Phase 54 User Flow Status

End-to-end flow is reachable after this plan:
1. Sidebar → `/qramm` (OrgProfilePage) — plan 03
2. Complete Org Profile → navigate to `/qramm/assessment` — plan 03
3. `/qramm/assessment` → 4 dimension tabs (CVI/SGRM/DPE/ITR) with 120 questions — plan 04
4. `/qramm/assessment` → Scorecard tab → Calculate Score → RadarChart + dimension table — plan 05 (this plan)

All 5 tabs of AssessmentPage are now fully implemented.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Symlinked node_modules from main repo (same fix as plan 04)**
- **Found during:** Task 1 build verification
- **Issue:** Worktree src/dashboard had no node_modules; tsc and vite build require actual packages
- **Fix:** `ln -s /path/to/QUIRK/src/dashboard/node_modules worktree/src/dashboard/node_modules`
- **Impact:** Build environment only; no committed code change

**2. [Rule 3 - Blocking] Accidentally wrote ScorecardTab.tsx to .clone/ directory**
- **Found during:** Task 1 file creation (absolute path error)
- **Issue:** Write tool wrote to `.clone/src/dashboard/...` instead of `.claude/worktrees/.../src/dashboard/...`
- **Fix:** Wrote correct file to worktree path; deleted `.clone/` stale copy before commit
- **Impact:** None on committed code

## Known Stubs

None. ScorecardTab renders real recharts components from real QRAMMContext data. The "—" placeholders for numeric cells (when scoreResult is null) are intentional UX states, not data stubs.

## Threat Coverage

All STRIDE threats from the plan's threat model were addressed:

| Threat | Disposition | Mitigation |
|--------|-------------|-----------|
| T-54-22 Tampering (profile_multiplier) | mitigate | Client passes `ctx.profile?.multiplier` (already server-computed in plan 01); backend Phase 51 score endpoint clamps to [0.8, 1.5] server-side |
| T-54-23 Info Disclosure (benchmark overlay) | accept | Benchmarks are static community averages in qramm-benchmarks.ts — no PII |
| T-54-24 DoS (repeated Calculate clicks) | mitigate | `calculating` state disables button while in-flight; only one POST in-flight |
| T-54-25 Tampering (a11y fixture) | accept | Fixture only served by Vite dev middleware during a11y runs; not in production build |

## Threat Flags

No new trust boundary surface beyond the plan's threat model.

## Self-Check

Files exist:
- src/dashboard/src/components/qramm/ScorecardTab.tsx: FOUND (266 lines)
- src/dashboard/tests/a11y/fixture-qramm.json: FOUND (1477 lines)
- src/dashboard/tests/a11y/routes.json: FOUND (13 lines, 11 entries)
- src/dashboard/src/pages/qramm-assessment.tsx: FOUND (256 lines — ScorecardPlaceholder removed)
- src/dashboard/vite.config.ts: FOUND (124 lines — QRAMM routes added)

Commits:
- 42de342: Task 1 — ScorecardTab component + replace placeholder
- cb50d9c: Task 2 — a11y route registration + fixture

## Self-Check: PASSED
