---
status: completed
completed: 2026-10-25
resolves_phase: 231
---

# QRAMM compliance map: scores never populate (2 causes)

**Filed:** 2026-10-02 (Phase 222.1 operator UAT, step 4 follow-up)
**Priority:** P2 — user-facing QRAMM surface reads as broken; candidate for a v5.27 follow-on or v5.28
**Status:** closed 2026-10-25 by Phase 231, see Resolution. Originally: open — operator chose to defer to a follow-on session ("save this for a follow on session, if it looks like it will take time away from the intent of this milestone")

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

## Resolution (Phase 231, 2026-10-25)

### Cause A: manually assessed SGRM/DPE/ITR rows (QRAMM-19)

- Operator decision, 2026-10-24 (Phase 231 D-01): show them, marked self-assessed. An answered SGRM, DPE or ITR
  dimension's rows carry `coverage_status: self-assessed` and a score of `static_weight × dimension score / 4`, at full
  weight with no scanner ceiling and no half weight (D-02/D-03). Any dimension with no answered question, CVI included,
  is `pending` with a null score (D-02a). `scanner_informed` and `SCANNER_COVERAGE_STATUS` are unchanged.
- Commits: assessed-state predicate `75ab5aa4`; endpoint `7bdbd355`; shared contract fixture and pytest parity half
  `c74b3fcd` (231-01); shared TS vocabulary `a641951e` (231-03); Compliance Map tab Assessment column, legend and
  footnote `fd6889ba` (231-05); print/PDF page `54e0952a` and `eabc6cf2` (231-06); cross-surface parity vitest
  `6d55c5b1` and bundle rebuild `e92144df` (231-07).
- D-20, found and fixed in scope: the print/PDF QRAMM page sent a GET to the POST-only `/score` route, the SPA fallback
  answered HTML, `data-ready` was never set and the PDF export timed out after 15 s. Fixed in `d4295641`: the hook reads
  the persisted score from `GET /api/qramm/sessions/{id}`.
- Proof, observed 2026-10-25: endpoint nodes plus `tests/test_compliance_coverage_status.py` 11 passed (UAT-231-03);
  `compliance-map-self-assessed.test.tsx` 8 passed (UAT-231-04); `useQRAMMPrintData.test.ts` plus
  `print-qramm-self-assessed.test.tsx` 11 passed (UAT-231-05); `tests/test_qramm_assessment_parity.py` 5 passed and
  `qramm-assessment-parity.test.tsx` 5 passed (UAT-231-06). Live leg, 2026-10-24 (231-07, sqlite snapshot): `/print`
  reached `data-ready` in 1.08 s with no `/score` request; `POST /api/export/pdf` returned 200 `application/pdf`,
  205340 bytes, in 1.39 s (UAT-231-07).
- The open unknown above is answered: the Python consulting report does not consume compliance-map rows (only
  `compliance_map.py` and `routes/qramm.py` read them, per the Phase 231 research grep).

### Cause B: no refetch after Calculate Score (QRAMM-17)

- Commit `e280eb48` (231-05): a successful `handleCalculate` bumps a local `reloadKey` in the rows effect's deps
  (`[ctx.sessionId, reloadKey]`, `scoreResult` still excluded) and a polite status region announces "Compliance map
  updated."; a failed or thrown Calculate Score does not refetch.
- Proof, observed 2026-10-25: `compliance-map-tab.test.tsx` 10 passed (UAT-231-01), including the unmodified WR-13
  case "does not refetch when scoreResult mutates but sessionId is stable".

### Scorecard flaw (QRAMM-18)

- Commit `63a35a33` (231-04): a dimension with no answered question shows a secondary "Not assessed" badge and "—"
  scores, and is excluded from the Maturity Distribution. The decision uses the live answered count, never the stored
  0.0. The `Math.max(1, …)` clamp stays for assessed dimensions.
- Proof, observed 2026-10-25: `scorecard-maturity.test.tsx` 18 passed (UAT-231-02).

### Documented, not fixed

- Answered after scoring: assessment state comes from the live answers and scores from the last Calculate, so a
  dimension answered after scoring reads Self-assessed with its stale 0.0 score until the operator scores again.
  Documented in operators guide §22 (`9be9eb7c`).
- The overall QRAMM score is unchanged by this phase and still averages a Not assessed dimension in as 0
  (`quirk/qramm/scoring.py`). Documented in both guides (`9be9eb7c`, `16cad977`); tracked separately as SCORE-10.
- Docs and UAT: operators guide `9be9eb7c`, report interpretation and changelog fragment `16cad977`, UAT Series 231
  `536bb652`.
