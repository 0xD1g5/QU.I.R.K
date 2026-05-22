# Phase 88: Scoring Residuals - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-22
**Phase:** 88-scoring-residuals
**Areas discussed:** Evidence-tally semantics, Score source-of-truth & render parity, Zero-algo CBOM emission, Subscore transparency

---

## Evidence-tally semantics (EVIDENCE-TALLY-01 — the product gate)

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — subscores independent | Clean category earns 25/25 regardless of other categories; correct-by-design | (basis of final) |
| No — cross-category penalties | A CRITICAL anywhere drags other subscores; treat 25/25 as defect | |
| Independent subscores, cap the OVERALL | Orthogonal subscores + SSL-Labs-style headline cap on criticals | |

**User's choice:** Free-text — "what makes sense with the scoring as defined throughout the application and all models?" → asked for a model-grounded answer rather than a product preference.
**Notes:** Investigated the code: single canonical engine `quirk/intelligence/scoring.py` builds each subscore as `25 + category-local penalties` (clamped `[0,25]`), overall = `sum(6)/1.5`, no cross-category coupling. Evidence-based conclusion: 25/25 while criticals exist elsewhere is **consistent with the model → correct-by-design / won't-fix at the subscore level**, with a parametrized test built to LOCK the orthogonal contract. The "cap the overall on criticals" idea is a deliberate model change → deferred. User confirmed this recommendation.

---

## Score source-of-truth & render parity (RENDER-CLI-01, RENDER-PDF-01)

| Option | Description | Selected |
|--------|-------------|----------|
| Data-layer parity gate (forward-locking) | Parametrized test: overall+6 subscores identical across CLI/dashboard/PDF, anchored to Phase 86 0–100 contract; shared rounding helper | ✓ |
| One-time empirical verification only | Manual comparison, fix only if math diverges, no permanent gate | |
| Full-render parity (heaviest) | Render CLI+HTML+PDF and scrape displayed numbers | |

**User's choice:** Data-layer parity gate (forward-locking).
**Notes:** Surfaced that CONCERNS.md's dual-engine warning is stale — assessment engine deleted, writer.py uses the intelligence engine. So reconciliation isn't needed; the gate locks parity to the canonical contract value.

---

## Zero-algo CBOM emission (SCORE-CBOM-01)

| Option | Description | Selected |
|--------|-------------|----------|
| Surface already-observed crypto; document genuine zeros | Emit components Pass-1 currently drops; no new scanning | ✓ |
| Aggressive — every profile must emit | Add observation where needed | |
| Conservative — only obvious misses | Fix ssh-weak etc., leave borderline as-is | |

**Follow-up — representation of genuine zeros:**

| Option | Description | Selected |
|--------|-------------|----------|
| Affirmative no-crypto marker | Explicit CBOM property/note: "plaintext — no cryptographic material observed" | ✓ |
| Document in code/docs only | Leave CBOM section empty, rationale in comments | |

**User's choice:** Surface already-observed crypto + affirmative no-crypto marker.
**Notes:** No new scanning (stays in-scope as a Pass-1 emission fix); closes Phase 42 OBS-1.

---

## Subscore transparency (SCORE-XPARENCY-01)

| Option | Description | Selected |
|--------|-------------|----------|
| Labeled decomposition + rollup math | `Label: N/25` + `sum → ÷1.5 → overall` in HTML/PDF/CLI markdown | ✓ |
| Labeled subscore table only | `Label: N/25` without rollup math | |
| Match dashboard gauges in HTML/PDF only | Port gauges to rich reports, leave CLI as-is | |

**User's choice:** Labeled decomposition + rollup math.
**Notes:** Dashboard already shows subscore gauges; this brings reports to parity and makes the headline auditable — softening BACK-89 without changing the scoring math.

## Claude's Discretion

- CBOM no-crypto marker key/shape, decomposition block layout, shared rounding-helper location — implementation details for the planner/executor.

## Deferred Ideas

- Overall critical-cap / severity floor on the headline score (SSL-Labs pattern) — the other half of BACK-89; a deliberate scoring-model change, explicitly out of scope for Phase 88.
