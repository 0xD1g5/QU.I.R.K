---
type: todo
created: 2026-10-27
source: Phase 234 (residual (b), code review IN-07; decision record §10)
priority: low
area: src/dashboard/src/context/QRAMMProvider.tsx, src/dashboard/src/components/qramm/ScorecardTab.tsx
status: pending
resolves_phase: null
owner: "999.139"
---

# The QRAMM scorecard's legacy "Recalculate" branch is unreachable in the live UI

**Owner:** 999.139

SCORE-10 (D-25) makes a QRAMM score saved before Phase 234 read "Recalculate to apply the updated overall". The
scorecard implements that branch, but it never receives a saved score: `QRAMMProvider` initialises
`scoreResult` to `null` (`src/dashboard/src/context/QRAMMProvider.tsx:18`) and only a fresh Calculate Score POST
sets it (`ScorecardTab.tsx:157`, `ComplianceMapTab.tsx:142`). A fresh POST always returns a current-format score,
so on the scorecard the legacy branch is pinned by the TS twin and vitest only. Print is the only live surface
that reads the saved score (`src/dashboard/src/hooks/useQRAMMPrintData.ts:134`, from the session detail's
persisted `score_json`), so print is where a pre-upgrade overall actually shows "Recalculate".

The code review (IN-07) confirmed this and required no fix in Phase 234.

## Proposed fix shape

Decide whether the scorecard should show a session's saved score when the session is opened (load
`detail.score` into `scoreResult`, as print does). If yes, the legacy and stale branches become live and the
existing vitest cases cover them; if no, remove the unreachable branch from the scorecard and say in
`docs/report-interpretation.md` that the scorecard shows only a score calculated in the current visit.

## Feasibility & Effort

**CONFIRMED** by reading the provider and the two setters above. Effort **S** either way; the choice is a UX
decision.
