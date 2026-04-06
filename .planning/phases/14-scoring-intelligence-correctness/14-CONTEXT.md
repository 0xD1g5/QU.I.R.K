# Phase 14: Scoring & Intelligence Correctness - Context

**Gathered:** 2026-04-06
**Status:** Ready for planning

<domain>
## Phase Boundary

The readiness score a consultant presents to a client is accurate, profile-aware, and identical
whether viewed from the CLI report or the dashboard.

Scope: wire calibration profile into compute_readiness_score() (verify + prove via TDD), fix
validate.py artifact list to remove phantom delta requirement, fix migration_advisor pattern
strings to match risk_engine finding titles, propagate profile kwarg from stored intelligence
JSON to dashboard score computation.

Not in scope: score transparency / methodology explanation in reports (captured as backlog item),
new scanner additions, dashboard UI changes beyond the profile propagation fix.
</domain>

<decisions>
## Implementation Decisions

### Test Plan Structure
- **D-01:** 2-plan TDD approach matching Phase 12 pattern.
  - Plan 1: RED scaffold — write failing tests that prove each of the 4 SCORE bugs exists
    (SCORE-01 through SCORE-04). Tests must fail before any fixes land.
  - Plan 2: GREEN fixes — implement changes that make all RED tests pass.

### SCORE-01: Calibration Profile Application
- **D-02:** The `PROFILE_MULTIPLIERS` structure and `profile` parameter exist in
  `intelligence/scoring.py`. Phase 9 also wired `writer.py` to pass `profile=cfg.intelligence.profile`.
  Plan 1 must prove whether the end-to-end path actually produces measurably different scores
  for `strict` vs `lenient` on identical scan data. If the structure is already correct,
  the RED test becomes the permanent regression guard.
- **D-03:** Success criterion: `strict` profile produces a higher combined `agility_*` +
  `identity_*` weight contribution than `lenient` on the same evidence dict, measurable in the
  returned `score["total"]`.

### SCORE-02: validate.py Artifact List
- **D-04:** Remove the `require_delta_if_baseline` logic entirely from `validate.py`. Delta
  reports are not implemented — this parameter causes permanent validation failures when a
  baseline intelligence JSON exists. `validate_run()` should validate only what
  `write_reports()` actually produces.
- **D-05:** After removal, the `expected_files` list (findings, executive-summary,
  technical-findings, scorecard, roadmap, run-stats, cbom.json, cbom.xml) should be verified
  against the actual `write_reports()` output paths. Remove any artifact from the list that
  `write_reports()` doesn't reliably produce.

### SCORE-03: migration_advisor Pattern Matching
- **D-06:** `migration_advisor.py` uses substring matching (`"legacy tls" in title.lower()`).
  `risk_engine.py` emits `"Legacy TLS versions allowed (TLS 1.0/1.1)"` — this does match after
  `.lower()`. The RED test must confirm whether migration recommendations actually surface in
  practice by running `recommend_migration_paths()` with a representative findings list from
  `risk_engine.py`. If there is a mismatch on another pattern (e.g., "plaintext http", "ssh",
  "quantum"), the test will surface it; fix the pattern string to match exactly.

### SCORE-04: Dashboard Profile Propagation
- **D-07:** The dashboard's `quirk/dashboard/api/routes/scan.py` (line 329-330) calls
  `compute_readiness_score(evidence)` without a `profile` kwarg. Fix: read the `profile` value
  from the stored `intelligence-*.json` file (field: `assessment.profile`, written by
  `writer.py` line 153), then pass it as `compute_readiness_score(evidence, profile=stored_profile)`.
- **D-08:** Do NOT re-read `config.yaml` at dashboard request time — the config could change
  after a scan was stored, causing dashboard score to drift from the CLI report score.
  The scan-time profile is the authoritative source.

### Claude's Discretion
- Exact structure of the RED test file(s) — one test file per bug or a single
  `test_scoring_correctness.py` covering all four
- Whether to use fixtures from existing test infrastructure or inline minimal evidence dicts
- Exact line removal scope in validate.py delta logic (function signature vs body)
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Scoring engine
- `quirk/intelligence/scoring.py` — `compute_readiness_score()`, `PROFILE_MULTIPLIERS`,
  `SCORE_WEIGHTS` — primary target for SCORE-01 verification
- `quirk/reports/writer.py` lines 114-120 — correct call site (profile + weights passed);
  reference for what SCORE-04 should replicate

### Validation
- `quirk/validate.py` lines 105-135 — `validate_run()`, `expected_files` list, delta logic
  to remove (SCORE-02)

### Migration advisor
- `quirk/assessment/migration_advisor.py` — pattern matching logic (SCORE-03); verify against
  `quirk/engine/risk_engine.py` finding titles
- `quirk/engine/risk_engine.py` lines 31-40, 188-197 — exact finding title strings emitted

### Dashboard
- `quirk/dashboard/api/routes/scan.py` lines 329-330 — `compute_readiness_score(evidence)`
  call missing profile (SCORE-04 fix target)

### Prior phase decisions
- `.planning/phases/09-scoring-consolidation/09-CONTEXT.md` D-05, D-06, D-07 — profile
  multiplier semantics (strict/balanced/lenient), parameter contract for compute_readiness_score()

### Requirements
- `.planning/REQUIREMENTS.md` SCORE-01 through SCORE-04 — acceptance criteria

No external specs — requirements fully captured in decisions above.
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tests/test_intelligence_scoring.py` — existing scoring tests; extend here for SCORE-01 RED tests
- `tests/test_scoring_consolidation.py` — Phase 9 consolidation tests; review for overlap before
  adding new coverage
- `intelligence/evidence.py::build_evidence_summary()` — use to build minimal evidence fixtures
  for RED tests without needing real scan data

### Established Patterns
- Phase 12's 2-plan TDD structure: Plan 1 (RED scaffold with `@pytest.mark.xfail` or assert-fails),
  Plan 2 (GREEN implementation + remove xfail markers)
- `writer.py` lines 114-120: `compute_readiness_score(evidence, profile=..., weights=...)` —
  the reference call signature to replicate in dashboard code
- `validate.py::expected_files` uses `f"artifact-{stamp}.ext"` naming; `stamp` is parsed from
  the intelligence file name — same pattern applies for any artifact list changes

### Integration Points
- Dashboard route at `quirk/dashboard/api/routes/scan.py` — must read intelligence JSON to
  extract stored profile before calling compute_readiness_score()
- `validate_run()` is called from `run_scan.py` after `write_reports()` — removing delta logic
  must not break the integration test added in Phase 8
- `migration_advisor.py::recommend_migration_paths()` is called from `executive.py` —
  changes to pattern matching must be covered by the executive summary integration path
</code_context>

<specifics>
## Specific Ideas

- "Transparency is key for scoring" — user wants reports to explain how scoring is calculated
  and what score ranges mean (high/medium/low readiness). DEFERRED to backlog (medium priority)
  — review after Phase 14 ships to decide if existing driver output is sufficient.

</specifics>

<deferred>
## Deferred Ideas

- **Score transparency in reports** — Add a scoring methodology section to executive summaries
  explaining: how profile weights affect the score, what score ranges map to readiness levels
  (e.g., 80-100 = high, 60-79 = medium, <60 = low), and which subscores contributed most.
  Deferred to backlog at medium priority. User will review Phase 14 output first.
  → `/gsd:add-backlog` candidate after Phase 14 completes.

None — discussion stayed within phase scope.
</deferred>

---

*Phase: 14-scoring-intelligence-correctness*
*Context gathered: 2026-04-06*
