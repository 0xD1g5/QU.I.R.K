# QU.I.R.K. — v4.10.1 Requirements

**Milestone:** v4.10.1 — Scoring Correctness Hotfix
**Opened:** 2026-05-22
**Status:** active

---

## Milestone v4.10.1 Requirements

### Scoring Correctness (SCORE-FIX)

- [ ] **SCORE-FIX-01**: `compute_readiness_score()` produces an overall score on a 0–100 scale derived by normalizing (sum-of-subscores ÷ 1.5), replacing the broken clamp-at-100 path at `quirk/intelligence/scoring.py:253-257`.
- [ ] **SCORE-FIX-02**: The module docstring at `quirk/intelligence/scoring.py:1-17` accurately describes the contract — six subscores each on a 0–25 scale, overall = `int(round(sum / 1.5))`, no misleading "clamp [0,100] is intentional" wording.
- [ ] **SCORE-FIX-03**: `tests/test_score_weights_invariant.py` (and any companion tests) reflect the new aggregation formula. A new test asserts that `compute_readiness_score` returns 100 only when all six subscores are at their 25 ceiling, and returns 0 only when every subscore is 0.

### Dashboard Gauge Correctness (GAUGE)

- [ ] **GAUGE-01**: `ScoreGauge` accepts a `maxValue?: number` prop (default 100). Arc fill and the displayed numeric label are computed against `score / maxValue`, not `score / 100`. Existing call sites that omit the prop behave unchanged.
- [ ] **GAUGE-02**: `_gaugeColor()` operates on a normalized fraction (0–1) instead of a raw score. Color thresholds: red < 50 %, amber 50–79 %, green ≥ 80 %. A subscore that maxes out its category budget shows green; a subscore at 0 shows red.
- [ ] **GAUGE-03**: `executive.tsx` passes `maxValue={25}` to all six subscore gauges (Hygiene, Modern TLS, Identity, Agility, Data at Rest, Data in Motion). The overall-readiness gauge keeps `maxValue` default (100).

### Release Engineering (RELEASE)

- [ ] **RELEASE-01**: `CHANGELOG.md` / `changelog.d/` entry documents the scoring-correctness fix in plain operator language ("Overall readiness no longer caps at 100 on real scans; old stored scores will display lower after upgrade. The underlying penalty math is unchanged."). Includes the canonical 25+25+23+3+25+19 → before-and-after example.
- [ ] **RELEASE-02**: `pyproject.toml` `[project.version]` bumped from `4.10.0` to `4.10.1`. Version single-source-of-truth invariant preserved.

---

## Future Requirements (deferred to v5.0 — Stabilization)

Captured here so the v5.0 plan absorbs them without re-discovery:

- **EVIDENCE-TALLY-01** *(deferred to v5.0 Phase 01)* — Investigate why three subscores (Hygiene, Modern TLS, Data at Rest) report exactly 25 despite the scan having HIGH/CRITICAL findings. Audit `quirk/intelligence/evidence.py::build_evidence_summary` for missing penalty-counter increments.
- **RENDER-CLI-01** *(deferred to v5.0 Phase 01)* — Audit `quirk/reports/executive.py` and `quirk/reports/html_renderer.py` for the same backend-scale vs render-scale mismatch as the dashboard. Apply equivalent normalization/percentage logic where needed.
- **RENDER-PDF-01** *(deferred to v5.0 Phase 01)* — Same audit for the Playwright-rendered PDF (which renders the HTML report).

---

## Out of Scope (this milestone)

| Item | Reason |
|------|--------|
| CLI / HTML / PDF render-side fixes | Scope discipline. Same bug class likely lives there but v5.0 Phase 01 is the right shape (full-stack scoring correctness sweep). Mixing into a hotfix risks shipping new bugs. |
| Evidence-tally bug (3 categories at 25 with findings present) | Separate root cause in the evidence summarizer; touching the tally pipeline expands the diff well beyond a hotfix. Deferred to v5.0 with explicit follow-up REQ. |
| Backwards-compat migration of stored scores | Stored evidence + score values in SQLite are unchanged. Old scans display the new math when re-rendered — accepted "visual jump" trade-off, documented in release notes. |
| Score-engine redesign (subscores as 0-100, weighted average, etc.) | Larger architectural change. The surgical fix preserves the 0-25 subscore model and just corrects the aggregation + display. A redesign can be considered at v5.x or beyond if usage data justifies it. |

---

## Traceability

Will be filled in by the roadmapper when ROADMAP.md phases are defined.

| Requirement | Phase | Plan | Status |
|-------------|-------|------|--------|
| SCORE-FIX-01 | TBD | TBD | open |
| SCORE-FIX-02 | TBD | TBD | open |
| SCORE-FIX-03 | TBD | TBD | open |
| GAUGE-01 | TBD | TBD | open |
| GAUGE-02 | TBD | TBD | open |
| GAUGE-03 | TBD | TBD | open |
| RELEASE-01 | TBD | TBD | open |
| RELEASE-02 | TBD | TBD | open |
