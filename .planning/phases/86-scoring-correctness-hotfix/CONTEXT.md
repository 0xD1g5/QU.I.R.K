# Phase 86: Scoring Correctness Hotfix - Context

**Gathered:** 2026-05-22
**Status:** Ready for planning
**Source:** Diagnosis surfaced in `/gsd-mvp-phase` predecessor session (live dashboard bug report)

<domain>
## Phase Boundary

Fix the marquee overall-readiness score so it stops displaying 100/EXCELLENT when underlying subscores are red and CRITICAL findings are present. Surgical fix — no change to the per-category penalty model, no change to evidence tally, no migration of stored scores.

**Trigger evidence (2026-05-22 live dashboard scan):**
- Overall Readiness gauge: **100** (EXCELLENT, Medium Confidence)
- Subscores: Hygiene 25, Modern TLS 25, Identity 23, Agility 3, Data at Rest 25, Data in Motion 19 → sum = **120**
- Severity Breakdown: 2 CRITICAL, 2 HIGH (4 findings total across 28 endpoints)

**Root-cause diagnosis (triple-layer bug):**
1. **Backend:** `compute_readiness_score()` at `quirk/intelligence/scoring.py:253-257` sums six 0–25 subscores and clamps at 100. Max raw sum = 150; any sum ≥ 100 displays as `EXCELLENT`. Function spec at line 103: `_apply_weighted_impacts(impacts, score_cap=25.0)` — confirms 0–25 subscore scale.
2. **Frontend:** `ScoreGauge.tsx` line 2 declares `score: number // 0-100`. `_gaugeColor` at line 9: red < 50, amber 50–79, green ≥ 80. Result: any 0–25 subscore *always* renders red. Hygiene = 25 (perfect) displays as red "25 / 100 = BAD."
3. **Docstring:** `scoring.py:5-13` references "Phase 60 SCORE-04 / CR-06 closure" as if the clamp-to-100 were intentional. Misleads future contributors into believing the broken math is by-design.
</domain>

<decisions>
## Implementation Decisions

### Backend math (LOCKED)
- **D-01:** Replace `_clamp(sum, 0, 100)` at `scoring.py:253-257` with `int(round(sum / 1.5))`. No other formula touched.
- **D-02:** Subscore range stays **0–25** per category (do NOT migrate to 0–100 per category). Preserves `_apply_weighted_impacts(score_cap=25.0)`, the per-category penalty budget model, and all six subscore call sites.
- **D-03:** Rating thresholds (`_rating()` at scoring.py:89-98) remain unchanged. EXCELLENT ≥ 85, GOOD ≥ 70, MODERATE ≥ 55, FAIR ≥ 35, POOR < 35 — these are correct for a true 0–100 scale, just never reached before because the denominator was wrong.

### Frontend gauge (LOCKED)
- **D-04:** Add `maxValue?: number` prop to `ScoreGauge` with default `100`. Internal computation uses `score / maxValue` instead of `score / 100`. Default behavior unchanged for any caller that omits the prop.
- **D-05:** Rewrite `_gaugeColor()` to take a normalized fraction (0.0–1.0), not a raw score. Same thresholds (0.5, 0.8) applied to the fraction.
- **D-06:** Update `executive.tsx` lines 262-267 to pass `maxValue={25}` to each subscore gauge. The overall-readiness gauge (line 244-250) keeps default `maxValue` (100).
- **D-07:** Audit of `ScoreGauge` callers (verified via `grep -rn "ScoreGauge" src/dashboard/src/`):
  - `executive.tsx` lines 245 (overall) + 262–267 (six subscores) — overall gauge keeps default `maxValue=100`; six subscore gauges pass `maxValue={25}` per D-06.
  - **`data-at-rest.tsx:301`** — standalone Data at Rest tab gauge rendering `score={darScore}` where `darScore = data?.score?.subscores?.data_at_rest ?? 0` (a 0–25 subscore). **In scope:** must pass `maxValue={25}` for the same reason as the executive-page subscore gauges; otherwise this seventh occurrence of the bug class survives the fix.
  - `print.tsx` — does **not** import or render `ScoreGauge` (verified 2026-05-22; the file is the QRAMM print page). Prior CONTEXT.md erroneously listed print.tsx as a deferred caller — corrected in plan-check iteration 1.
  - `sidebar.tsx:2` — code comment referencing `ScoreGauge.tsx` token migration history; **not** a caller, no edit needed.

### Tests (LOCKED)
- **D-08:** `tests/test_score_weights_invariant.py` audited for any assertion that depends on the broken clamp behavior. Update assertions to reflect normalized formula. Sum-of-weights invariant (currently 275.0, count 36) is independent and stays.
- **D-09:** Add a new normalization-boundary test (file location TBD by planner — likely `tests/test_scoring_normalization.py` or appended to existing scoring test). Asserts:
  - `compute_readiness_score(evidence_with_max_subscores) → 100` only when all six subscores at 25.
  - `compute_readiness_score(evidence_with_zero_subscores) → 0` only when all six subscores at 0.
  - Canonical example: subscores 25+25+23+3+25+19 = 120 → `int(round(120 / 1.5))` = 80, rating = GOOD.
- **D-10:** Frontend gauge test (e.g., `src/dashboard/src/components/gauges/__tests__/ScoreGauge.test.tsx` if a vitest test exists; otherwise inline the assertions): subscore=25 with maxValue=25 renders green; subscore=3 with maxValue=25 renders red; overall=80 with default maxValue renders amber.

### Docstring (LOCKED)
- **D-11:** Rewrite `scoring.py:5-17` to describe the actual contract. Replace "Phase 60 SCORE-04 / CR-06 closure" mention with a v4.10.1 reference; remove "clamp [0,100] is intentional" language. New language must be honest about what the formula does and why.

### Release engineering (LOCKED)
- **D-12:** Bump `pyproject.toml [project.version]` from `4.10.0` to `4.10.1`. SoT invariant preserved.
- **D-13:** Add a `changelog.d/` fragment (per existing towncrier config) OR add a CHANGELOG.md entry — match the v4.10 release pattern. Plain operator language; canonical 25+25+23+3+25+19 → 100→80 before/after example; visual-jump note for old stored scores.

### Scope (LOCKED — out)
- **D-14:** **NO** change to CLI / HTML / PDF renderers (`quirk/reports/executive.py`, `quirk/reports/html_renderer.py`) — captured as `RENDER-CLI-01` / `RENDER-PDF-01` in REQUIREMENTS.md Future Requirements, deferred to v5.0 Phase 01.
- **D-15:** **NO** investigation of why three subscores show exactly 25 with HIGH/CRITICAL findings present — captured as `EVIDENCE-TALLY-01`, deferred to v5.0 Phase 01.
- **D-16:** **NO** migration of stored scores in SQLite. Accept visual jump; release-note it.

### Claude's Discretion
- Exact location for the new normalization test (new file vs. append to existing).
- Exact phrasing of the docstring rewrite (preserve technical accuracy + tone consistent with existing scoring.py prose).
- Exact phrasing of the changelog entry (must match v4.10 changelog style — terse, operator-facing, before/after example).
- Whether to add a TypeScript test file for ScoreGauge (only if the existing test infrastructure supports it; otherwise rely on the manual UAT criterion).
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `quirk/intelligence/scoring.py` — the broken aggregator (lines 1-17 docstring, 101-109 `_apply_weighted_impacts`, 253-279 `compute_readiness_score`)
- `src/dashboard/src/components/gauges/ScoreGauge.tsx` — the broken-scale gauge component
- `src/dashboard/src/pages/executive.tsx` lines 244-267 — the call sites that need `maxValue={25}`
- `tests/test_score_weights_invariant.py` — sum-of-weights guard (currently asserts 275.0, count 36)
- `pyproject.toml [project]` — version SoT
- `changelog.d/` — towncrier news-fragment directory pattern (look at how v4.10 entries were structured)
- `.planning/REQUIREMENTS.md` — 8 requirements (SCORE-FIX-01..03, GAUGE-01..03, RELEASE-01..02)
- `.planning/ROADMAP.md` Phase 86 section — 5 success criteria
- `.planning/HORIZON.md` v5.0 section — confirms RENDER-CLI-01, RENDER-PDF-01, EVIDENCE-TALLY-01 deferral target
</canonical_refs>

<dependencies>
## Phase Dependencies

- **Depends on:** Phase 85 (v4.10 SHIPPED 2026-05-21) — all v4.10 release engineering is in place; `pyproject.toml`, `release.yml`, `release-container.yml`, `Formula/quirk.rb` all exist and work.
- **Coupled with (this session, already on `main`):** commits `5f9b58c`, `81deeb9`, `ffb6bf3`, `45fd378`, `eb9edcb`, `af6b253`, `b50baa3`, `c9ab714`, `adee32b` — already-shipped post-ship cleanup; the v4.10.1 release tag will package those alongside the Phase 86 changes.
- **Blocks:** v5.0 Phase 01 (Stabilization) — which will inherit RENDER-CLI-01, RENDER-PDF-01, EVIDENCE-TALLY-01.
</dependencies>

<acceptance>
## Acceptance Criteria (from ROADMAP.md)

1. Running a scan against the `tls-cert-defects` chaos lab profile (or any scan that previously hit the clamp) shows an overall-readiness value strictly less than 100, with a corresponding non-EXCELLENT rating — the canonical 25+25+23+3+25+19 sum displays as ~80, not 100.
2. All six subscore radials in the dashboard display a color matching their penalty state: a subscore at its category max of 25 shows green (≥80 % of 25), a subscore at 0–7 shows red (<50 %), and a subscore in the middle range shows amber. The overall-readiness gauge keeps `maxValue` default (100) and renders unchanged when overall is unchanged.
3. `pytest tests/test_score_weights_invariant.py` passes against the new aggregation formula, and a new normalization-boundary test asserts that `compute_readiness_score` returns 100 only when all six subscores are at their 25 ceiling, and returns 0 only when every subscore is 0.
4. The module docstring at `quirk/intelligence/scoring.py:1-17` accurately describes the contract — six subscores each on a 0–25 scale, overall = `int(round(sum / 1.5))` — with no remaining "Phase 60 SCORE-04 clamp-to-[0,100] is intentional" wording or other misleading language.
5. `pyproject.toml` `[project.version]` reads `4.10.1`, and `CHANGELOG.md` / `changelog.d/` has an entry describing the scoring fix in plain operator language including the canonical 25+25+23+3+25+19 before/after example and a note that old stored scores will display lower after upgrade (underlying penalty math unchanged).
</acceptance>
