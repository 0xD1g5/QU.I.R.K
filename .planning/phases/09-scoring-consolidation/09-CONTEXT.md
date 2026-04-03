# Phase 9: Scoring Consolidation - Context

**Gathered:** 2026-04-03
**Status:** Ready for planning

<domain>
## Phase Boundary

QUIRK produces one readiness score, one confidence value, and one roadmap per scan — sourced from
a single authoritative code path — so a client cannot see two different numbers by reading different
output artifacts.

Scope: eliminate dual scoring (assessment/ vs intelligence/), wire profile-based weight tables,
apply calibration_overrides at runtime, unify roadmap format to NOW/NEXT/LATER, port narrative
interpretation to intelligence data, delete the four dead assessment compute modules.

Not in scope: net-new scanner additions, Windows ADCS (Phase 10), web dashboard changes beyond
what the unified intelligence JSON enables.
</domain>

<decisions>
## Implementation Decisions

### Dual Scoring Path Elimination
- **D-01:** Refactor `quirk/reports/executive.py` to call `build_evidence_summary(endpoints, findings)`
  first, then call `intelligence/scoring.py::compute_readiness_score()`,
  `intelligence/confidence.py::compute_confidence()`, and `intelligence/roadmap.py::build_phased_roadmap()`.
  This is the same call sequence already used by `writer.py`. The executive summary markdown and
  intelligence JSON will share the same source data and produce the same score.
- **D-02:** Delete `quirk/assessment/readiness_score.py`, `quirk/assessment/confidence.py`,
  `quirk/assessment/transition_planner.py`, and `quirk/assessment/interpretation_engine.py`.
  Keep `quirk/assessment/operator_context.py` (used by `run_scan.py` for operator context prompts)
  and `quirk/assessment/migration_advisor.py` (rules-based migration recommendations, no intelligence
  equivalent exists).

### Roadmap Format Unification
- **D-03:** Use NOW/NEXT/LATER format throughout. The executive summary markdown renders
  `build_phased_roadmap()` output (same as intelligence JSON and HTML). Wave 1/2/3 format is retired.

### Narrative Interpretation
- **D-04:** Port the rich narrative logic from `assessment/interpretation_engine.py` into a new
  function that takes `evidence: Dict` and `score: Dict` instead of `ReadinessScore` dataclass.
  Preserve these elements: top-3 score driver analysis, TLS/SSH visibility framing (successful
  handshake counts), TIMEOUT and NOT_TLS_ON_PORT event context, CRITICAL+HIGH severity summary.
  This function lives in `intelligence/` or directly in `executive.py` — Claude's discretion on
  placement.

### Profile-Based Weight Tables
- **D-05:** Add per-profile weight multipliers to `intelligence/scoring.py`. Semantics:
  - `strict` — `agility_*` and `identity_*` weights × 1.4 (amplifies crypto-agility and cert
    hygiene penalties; appropriate for a post-quantum readiness posture)
  - `balanced` — base weights as currently defined in `SCORE_WEIGHTS` (1.0×)
  - `lenient` — `agility_*` and `identity_*` weights × 0.7
  - `hygiene_*` and `modern_tls_*` weights unchanged across all profiles
- **D-06:** `compute_readiness_score()` accepts a new `profile: str | None = None` keyword
  argument alongside the existing `weights: Mapping[str, float] | None = None`. Profile
  multipliers are applied first; then `weights` (calibration_overrides) are merged on top —
  user-specific overrides always win over profile defaults.

### Calibration Wiring
- **D-07:** Wire `cfg.intelligence.profile` and `cfg.intelligence.calibration_overrides` into
  both `compute_readiness_score()` call sites: `writer.py` (line 115) and the refactored
  `executive.py`. Pass `profile=cfg.intelligence.profile` and
  `weights=cfg.intelligence.calibration_overrides` (the latter may be None — the function
  already handles None gracefully).

### Claude's Discretion
- Exact placement of the ported `build_interpretation()` logic (new file in intelligence/ or
  inline in executive.py)
- Precise weight multiplier values beyond the 1.4/1.0/0.7 anchors — tuning within that range
  is acceptable to achieve measurably different scores on the same scan data
- Whether to add a `--score-profile` flag passthrough test to the validate.py integration test
  added in Phase 8 D-02
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Primary source
- `.planning/codebase/CONCERNS.md` §4.1–4.3, §12.1 — Full dual-scoring audit with file:line citations

### Key source files
- `quirk/reports/executive.py` — Current dual-path entry point (to be refactored)
- `quirk/reports/writer.py` — Reference implementation of the intelligence call sequence
- `quirk/intelligence/scoring.py` — `compute_readiness_score()`, `SCORE_WEIGHTS` — add profile param here
- `quirk/intelligence/confidence.py` — `compute_confidence()` — second target for profile wiring check
- `quirk/intelligence/roadmap.py` — `build_phased_roadmap()` — becomes the unified roadmap source
- `quirk/intelligence/evidence.py` — `build_evidence_summary()` — executive.py must call this first
- `quirk/assessment/interpretation_engine.py` — rich narrative logic to be ported, then deleted
- `quirk/assessment/readiness_score.py` — to be deleted after executive.py migration
- `quirk/assessment/confidence.py` — to be deleted after executive.py migration
- `quirk/assessment/transition_planner.py` — to be deleted after executive.py migration
- `quirk/config.py` — `IntelligenceCfg` (profile, calibration_overrides fields)
- `run_scan.py` — `cfg.intelligence.profile` set here (line ~192); also imports operator_context
- `quirk/intelligence/schema.py` — available for repurposing if a typed Score input is needed
- `quirk/reports/scorecard.py` — existing intelligence-path scorecard for reference

### Phase 8 context
- `.planning/phases/08-legacy-debt-cleanup/08-CONTEXT.md` D-14 — schema.py and scorecard.py
  left for Phase 9; D-16 — assessment/ compute modules left for Phase 9
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `intelligence/evidence.py::build_evidence_summary(endpoints, findings)` — already converts raw
  scan objects to the evidence dict both scoring and confidence functions consume; executive.py
  just needs to call this first
- `intelligence/scoring.py::SCORE_WEIGHTS` dict — profile multipliers should be applied as a
  pre-pass over this dict before the existing weight-override logic
- `reports/scorecard.py::_interpretation_bullets()` — simpler alternative reference for
  interpretation if the ported logic grows too complex; uses same evidence-dict interface

### Established Patterns
- `writer.py` lines 113–117: `evidence = build_evidence_summary(endpoints, findings)` →
  `score_raw = compute_readiness_score(evidence)` → `conf_raw = compute_confidence(evidence)` →
  `roadmap_raw = build_phased_roadmap(evidence, score_raw)` — exact call sequence to replicate
  in executive.py
- Profile is already parsed and stored at `cfg.intelligence.profile` by `config.py` lines
  101–119; downstream code just needs to read it
- `calibration_overrides` is at `cfg.intelligence.calibration_overrides` (Optional[Dict])

### Integration Points
- `executive.py` is called from `writer.py::write_reports()` — it receives `(cfg, endpoints,
  findings)` as arguments; this signature stays unchanged, only internal calls change
- `run_scan.py` imports `prompt_for_context` and `attach_context` from `assessment/operator_context`
  — this module must not be deleted
- `assessment/migration_advisor.py` is imported by `executive.py` for `recommend_migration_paths()`
  — no intelligence equivalent; keep in place
- Phase 8 D-02 added an integration test calling `validate_run()` — scoring consolidation may
  change the intelligence JSON schema; update that test if field names change
</code_context>

<specifics>
## Specific Ideas

- Profile semantics are quantum-readiness-native: strict = conservative PQC posture (amplify
  agility/identity penalties), lenient = status-quo baseline (reduce them). Hygiene weights
  stay neutral — a plaintext HTTP endpoint is equally bad regardless of profile.
- The ported interpretation function should preserve the "TLS/SSH visibility framing" bullet
  because it directly answers the consulting question "how much did you actually see?"

</specifics>

<deferred>
## Deferred Ideas

- `assessment/operator_context.py` runtime prompts — currently prompts for org name, industry,
  etc. at scan time. After Phase 9, assess whether these fields feed into the intelligence
  scoring or are decorative. If decorative, consider removing in a future phase.
- `scorecard.py` fate — currently orphaned (§1.8); Phase 9 may leave it as-is or consolidate
  into executive.py. Out of scope unless it blocks the migration.
- `intelligence/schema.py` typed Score inputs — available for repurposing but not required
  by Phase 9 success criteria; defer unless a natural use emerges during implementation.

None — discussion stayed within phase scope.
</deferred>

---

*Phase: 09-scoring-consolidation*
*Context gathered: 2026-04-03*
