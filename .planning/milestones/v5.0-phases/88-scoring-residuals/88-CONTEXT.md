# Phase 88: Scoring Residuals - Context

**Gathered:** 2026-05-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Make the scoring system **correct and transparent**, resolving residuals carried into v5.0:
- Resolve the evidence-tally semantics by an explicit, model-grounded product decision (EVIDENCE-TALLY-01).
- Empirically verify the CLI/markdown and HTML/PDF reports against the Phase 86 normalized 0–100 contract (RENDER-CLI-01, RENDER-PDF-01).
- Make the five zero-algo CBOM profiles emit real algorithm components where crypto is observed, and explicitly mark genuine zeros (SCORE-CBOM-01, closes Phase 42 OBS-1).
- Surface the six subscores against their `/25` budget with the overall rollup (SCORE-XPARENCY-01, BACK-63).

**Not in scope:** changing the scoring math itself (e.g. adding an overall critical-cap), adding new scanners/observation, or any new scoring capability. Discussion clarified HOW to satisfy the five requirements — no new capability surface.
</domain>

<decisions>
## Implementation Decisions

### Evidence-tally semantics (EVIDENCE-TALLY-01) — the product gate
- **D-01:** Resolve EVIDENCE-TALLY-01 as **documented correct-by-design / won't-fix at the subscore level.** Grounded in the single canonical model (`quirk/intelligence/scoring.py`): each subscore = `25.0 + sum(that category's penalty impacts)`, clamped `[0,25]` (`_apply_weighted_impacts`, score_cap=25.0); overall = `round(sum(six 0–25 subscores) / 1.5)`. Subscores are **orthogonal per-category dimensions with no cross-category coupling** — so a clean category scoring 25/25 while HIGH/CRITICAL findings exist in *other* categories is consistent with the model as defined throughout the app. Forcing cross-category penalties would contradict the architecture and is rejected.
- **D-02:** Still build the **parametrized six-subscore-family test suite** the requirement calls for — but its purpose is to **forward-lock the orthogonal contract** (each subscore moves only on its own category's findings), not to "fix" a defect. Follow the project's forward-locking-invariant test pattern (cf. `tests/test_xml_safe.py`, `tests/test_score_weights_invariant.py`, `tests/test_audit_ledger_zero_open.py`). Resolution + rationale must be written inline (won't-fix with reasoning), per the requirement.

### Score source-of-truth & render parity (RENDER-CLI-01, RENDER-PDF-01)
- **D-03:** Verify-first. The dual-engine concern in `CONCERNS.md` is **STALE** — `quirk/assessment/readiness_score.py` is deleted and `quirk/reports/writer.py:17` imports `compute_readiness_score` from `quirk.intelligence.scoring`, the same engine the dashboard/HTML/PDF use. There is now one canonical scoring engine; no engine reconciliation is needed. Researcher should confirm and flag the stale CONCERNS entry.
- **D-04:** Satisfy + lock via a **data-layer parity gate** (forward-locking): a parametrized regression test asserting the overall + all six subscore **values** that each surface receives (CLI markdown / dashboard-API / HTML+PDF) are identical for fixture scans, **anchored to the Phase 86 normalized 0–100 contract value** (not merely internal agreement — they must equal the canonical contract, so three surfaces can't agree on a wrong number). Assert the numbers at the data layer, not by scraping rendered PDFs (cheap, non-flaky). If any divergence is found, fix via a **single shared rounding/formatting helper**; otherwise close verified-no-bug with the test as evidence.

### Zero-algo CBOM emission (SCORE-CBOM-01)
- **D-05:** Emission policy: **surface crypto the scanners ALREADY observe** but Pass-1 currently drops — TLS ciphers/certs, SSH host-keys/KEX, KMS keys — for the five zero-algo profiles (`database`, `registry`, `source`, `ssh-weak`, `storage-s3`). **No new scanning/observation** (that would be scope creep). Closes Phase 42 OBS-1.
- **D-06:** Where a profile's zero-algo output is **genuinely correct** (plaintext / ssl-off endpoint), emit an **affirmative no-crypto marker** — a CBOM property / coverage note such as "plaintext endpoint — no cryptographic material observed" — so the zero reads as an affirmative finding ("we looked, it's plaintext"), never as an unscanned gap. Researcher determines per-profile which case applies (real Pass-1 miss vs. genuinely plaintext).

### Subscore transparency (SCORE-XPARENCY-01)
- **D-07:** Reports (**HTML, PDF, and CLI markdown**) surface each subscore as `Label: N/25` **plus the explicit rollup math** — sum of the six → `÷1.5` → overall. The dashboard already shows subscore gauges; this brings the report surfaces to parity and makes the headline auditable.
- **D-08 (cross-cutting synthesis):** D-01 + D-07 together resolve the BACK-89 tension *honestly*: the scoring math stays intact (orthogonal by design), and the rollup transparency makes "Agility 3 but Overall high" self-explaining rather than contradictory — **without** changing the math. Transparency is the fix for the optics, not a scoring change.

### Claude's Discretion
- Exact CBOM property key/shape for the no-crypto marker (D-06), the precise table/layout of the decomposition block (D-07), and the shared rounding-helper location (D-04) are implementation details for the planner/executor, consistent with existing report and CBOM conventions.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Scoring model (source of truth)
- `quirk/intelligence/scoring.py` — THE readiness-scoring model. `_apply_weighted_impacts(impacts, score_cap=25.0)` (~lines 103–111) builds each subscore as `25 + category-local penalties` clamped `[0,25]`; overall = `round(sum(six)/1.5)` (~line 257). Grounds D-01/D-02.
- `quirk/reports/writer.py` — report rendering; imports `compute_readiness_score` at `:17`, calls it at `:157`. Confirms the single-engine fact for D-03.
- `quirk/dashboard/api/schemas.py` + `quirk/dashboard/api/routes/scan.py` — dashboard subscore surface (already shows gauges); parity target for D-04/D-07.

### CBOM
- `quirk/cbom/builder.py` — Pass-1 component emission; target of SCORE-CBOM-01 (D-05/D-06).

### Requirements & cross-links
- `.planning/REQUIREMENTS.md` — EVIDENCE-TALLY-01, RENDER-CLI-01, RENDER-PDF-01, SCORE-CBOM-01, SCORE-XPARENCY-01 (note: REQUIREMENTS wording predates these decisions where they refine it).
- `.planning/codebase/CONCERNS.md` — **STALE on the dual-scoring-engine entry** (assessment engine deleted) — verify and correct per D-03. Other entries may also be stale; treat as leads, not facts.
- ROADMAP backlog: **BACK-89** (overall-vs-severity optics — addressed via transparency, not math), **BACK-63** (score transparency origin), **Phase 42 OBS-1** (the five zero-algo profiles).
- Phase 86 — established the normalized 0–100 overall-readiness contract (the `sum/1.5` clamp + `ScoreGauge maxValue`); the anchor value for D-04.

### Forward-locking test pattern to mirror
- `tests/test_xml_safe.py`, `tests/test_score_weights_invariant.py`, `tests/test_audit_ledger_zero_open.py` — house style for the D-02 contract test and D-04 parity gate.
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `compute_readiness_score` (`quirk/intelligence/scoring.py`) — single scoring entry point shared by CLI markdown, dashboard, and HTML/PDF. Reuse as the parity anchor; do not reintroduce a second engine.
- Existing dashboard subscore gauges (`ScoreGauge`, executive page) — the labeled `/25` presentation already exists on the dashboard; D-07 ports the equivalent to reports.
- `_apply_weighted_impacts` — the per-category cap mechanism; the place to confirm orthogonality for the D-02 test.

### Established Patterns
- Forward-locking CI-invariant tests (grep/AST/assertion gates) are the project's standard way to lock a contract permanently — use for D-02 and D-04.
- Affirmative coverage markers over empty output (consulting-grade) — consistent with how coverage-gap advisories are already surfaced; apply to D-06.

### Integration Points
- Report renderers (`quirk/reports/writer.py`, HTML/PDF templates) — where D-07 decomposition + D-04 shared rounding land.
- `quirk/cbom/builder.py` Pass-1 — where D-05/D-06 emission lands.
</code_context>

<specifics>
## Specific Ideas

- The user's governing principle for the gate: the resolution must be **consistent with the scoring model as defined throughout the application and all models** — not an imposed product preference. (Drove the evidence-based D-01.)
- SSL Labs grading was the reference point for "orthogonal sub-scores + headline cap"; the cap half is explicitly deferred (see Deferred).
</specifics>

<deferred>
## Deferred Ideas

- **Overall critical-cap / severity floor on the headline score** (the SSL-Labs "one critical caps the grade" pattern). This is the *other half* of BACK-89. It is a **deliberate scoring-model CHANGE**, not a consistency fix, so it is explicitly OUT of scope for Phase 88. Capture as a future, explicit design decision (its own phase or a documented model-change proposal). Phase 88 instead addresses the BACK-89 optics via transparency (D-07/D-08).
- None of the discussion strayed otherwise — scope stayed within the five requirements.
</deferred>

---

*Phase: 88-scoring-residuals*
*Context gathered: 2026-05-22*
