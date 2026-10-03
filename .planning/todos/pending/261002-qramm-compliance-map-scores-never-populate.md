# QRAMM compliance map: scores never populate (2 causes)

**Filed:** 2026-10-02 (Phase 222.1 operator UAT, step 4 follow-up)
**Priority:** P2 — user-facing QRAMM surface reads as broken; candidate for a v5.27 follow-on or v5.28
**Status:** open — operator chose to defer to a follow-on session ("save this for a follow on session, if it looks like it will take time away from the intent of this milestone")

## What the operator saw

Session 1 fully answered CVI (30/30) and SGRM (30/30), DPE/ITR unanswered. After Calculate Score
(working since the 222.1 CSRF fix `a4286c22`), the radar/scorecard showed scores but the compliance
map table did not.

Persisted `score_json` (session 1): CVI 2.80, SGRM 1.40, DPE 0.00, ITR 0.00, overall 1.05 Basic.

## Cause A — by design: non-CVI rows are always null

`quirk/qramm/compliance_map.py:53-58` sets `SCANNER_COVERAGE_STATUS` CVI=`covered`,
SGRM/DPE/ITR=`pending`; `quirk/dashboard/api/routes/qramm.py:738-740` returns
`relevance_score=None` for every `pending`/`n/a` row regardless of manual answers (Phase 74-03 D-10).
So 9 of 12 practice areas (72 of 96 rows) can never show a score. The banner "Coverage reflects
QUIRK scanner findings for CVI only — SGRM, DPE, ITR require manual assessment" describes this,
but an operator who DID the manual assessment reasonably expects it to appear.

**Product decision needed (operator):** should self-assessed dimensions contribute to the compliance
map (e.g. shown with a "self-assessed" marker, not the scanner ceiling), or stay excluded with a
clearer banner?

## Cause B — bug: Calculate Score in the compliance tab never refetches rows

`src/dashboard/src/components/qramm/ComplianceMapTab.tsx:90-111` `handleCalculate` calls
`ctx.setScoreResult(json)` but the rows effect depends only on `[ctx.sessionId]` (`:137-139`,
D-07/WR-13 — deliberate, to stop a refetch loop). So even CVI rows stay null until the tab
remounts. Latent until 2026-10-02: the button 403'd on every live server since 58-04 (2026-05-09).

Fix shape: refetch explicitly at the end of a successful `handleCalculate` (a local `reloadKey`
counter in the effect deps, NOT `scoreResult`), preserving WR-13's no-loop guarantee
(`compliance-map-tab.test.tsx` "does not refetch when scoreResult mutates but sessionId is stable"
must stay green). Test must assert a second `/compliance-map` request after a successful score.

## Related presentation flaw (scorecard)

`ScorecardTab.tsx` clamps `Math.max(1, …)` so unanswered dimensions (score 0.0 from SCOREFIX-02
injection) render an "Initial" maturity badge and count in the Maturity Distribution as level 1 —
"not assessed" is indistinguishable from "assessed at level 1". Consider a "Not assessed" state
driven by completion % (0%).

## Feasibility & Effort

- Cause B: **CONFIRMED** (read `ComplianceMapTab.tsx:90-139`), effort **S** — one state counter +
  one vitest; rebuild statics. No spike.
- Cause A: **CONFIRMED** mechanism (read `compliance_map.py:42-58`, `qramm.py:732-748`); effort
  **M** once the operator decides presentation — touches the endpoint, `SCANNER_COVERAGE_STATUS`
  semantics, the rollup half-weight rule (D-10a), the print/PDF QRAMM page
  (`useQRAMMPrintData.ts:66` also reads compliance-map), and report-interpretation docs. Unknown:
  whether the consulting PDF report consumes the same rows (check before changing semantics).
- Scorecard "Not assessed": **LIKELY** S — `ScorecardTab.tsx` maturityDist + badge cell;
  `scorecard-maturity.test.tsx` covers the bucket maths.
