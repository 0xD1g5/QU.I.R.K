---
phase: 09-scoring-consolidation
verified: 2026-04-03T18:30:00Z
status: passed
score: 5/5 must-haves verified
gaps: []
human_verification: []
---

# Phase 9: Scoring Consolidation Verification Report

**Phase Goal:** QUIRK produces one readiness score, one confidence value, and one roadmap per scan — sourced from a single authoritative code path — so a client cannot see two different numbers by reading different output artifacts.
**Verified:** 2026-04-03T18:30:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths (Success Criteria)

The five success criteria come directly from ROADMAP.md Phase 9:

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| SC-01 | The readiness score in executive summary markdown matches the score in intelligence JSON — both sourced from same `compute_readiness_score()` call path | VERIFIED | `executive.py` calls `compute_readiness_score(evidence, profile=cfg.intelligence.profile, weights=...)` directly; `writer.py` uses the identical call sequence at lines 115-118. Both feed the same `build_evidence_summary()` output. |
| SC-02 | The roadmap in executive summary markdown is the same data as the roadmap artifact files — unified NOW/NEXT/LATER format | VERIFIED | `executive.py` calls `build_phased_roadmap(evidence, score_raw)` and renders with `phase_labels = {"NOW":…, "NEXT":…, "LATER":…}`. `writer.py` uses the same function. No `wave_1/wave_2/wave_3` strings remain in either file. |
| SC-03 | Four assessment compute modules are physically deleted; no imports referencing them exist in production code | VERIFIED | `ls quirk/assessment/` returns only `migration_advisor.py`, `operator_context.py`, and `__pycache__`. All four files (`readiness_score.py`, `confidence.py`, `transition_planner.py`, `interpretation_engine.py`) confirmed absent. Zero live imports from those paths in `quirk/` or `run_scan.py`. |
| SC-04 | `profile: strict` produces measurably different score weights than `profile: lenient` on the same scan data | VERIFIED | `PROFILE_MULTIPLIERS` constant in `quirk/intelligence/scoring.py` applies 1.4x on `agility_*`/`identity_*` for strict and 0.7x for lenient. `test_profile_strict_scores_differently_from_lenient` passes. |
| SC-05 | `calibration_overrides` set in config are applied to the scoring engine weights at runtime | VERIFIED | Both call sites pass `weights=cfg.intelligence.calibration_overrides or None`. The `weights` block in `compute_readiness_score()` applies user overrides after profile multiplication. `test_calibration_overrides_applied` and `test_profile_then_override` both pass. |

**Score: 5/5 truths verified**

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `quirk/intelligence/scoring.py` | `PROFILE_MULTIPLIERS` constant + `profile=` kwarg on `compute_readiness_score()` | VERIFIED | Both present. `PROFILE_MULTIPLIERS` at line 22-26; `profile: str \| None = None` in signature at line 79. Prefix-loop applied before `weights=` override at lines 83-92. |
| `tests/test_intelligence_scoring.py` | `ProfileWeightTests` class with `test_profile_strict_scores_differently_from_lenient` | VERIFIED | Class present at line 59; all 5 `ProfileWeightTests` methods exist and pass. |
| `tests/test_scoring_consolidation.py` | `ExecutiveConsolidationTests` + `AssessmentDeletionTests` classes | VERIFIED | Both classes present with 7 and 6 tests respectively. No `@unittest.expectedFailure` decorators remain. All 20 tests pass. |
| `quirk/reports/executive.py` | Uses intelligence call sequence; contains `_build_interpretation()`; NOW/NEXT/LATER roadmap | VERIFIED | File fully rewritten. Imports from `quirk.intelligence.*` only (plus `migration_advisor`). `_build_interpretation()` at line 12. NOW/NEXT/LATER phase_labels dict at lines 205-209. |
| `quirk/reports/writer.py` | `profile=cfg.intelligence.profile` and `weights=cfg.intelligence.calibration_overrides or None` at call site; `calibration` block in intelligence dict | VERIFIED | `compute_readiness_score()` call at lines 115-118 passes both kwargs. `calibration` dict at lines 152-155. |
| `quirk/assessment/operator_context.py` | Must be preserved (used by `run_scan.py`) | VERIFIED | File exists at expected path. |
| `quirk/assessment/migration_advisor.py` | Must be preserved (used by `executive.py`) | VERIFIED | File exists and is imported in `executive.py` line 9. |
| `docs/configuration.md` | "How Score Profiles Work" section with multiplier table | VERIFIED | Contains "1.4x base", "0.7x base", "Agility Weight", "Identity Weight" column headers, and `calibration_overrides` override example. |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `quirk/reports/executive.py` | `quirk/intelligence/scoring.py` | `compute_readiness_score(evidence, profile=cfg.intelligence.profile, weights=...)` | WIRED | Line 106-109 in executive.py |
| `quirk/reports/executive.py` | `quirk/intelligence/evidence.py` | `build_evidence_summary(endpoints, findings)` | WIRED | Line 105 in executive.py |
| `quirk/reports/executive.py` | `quirk/intelligence/roadmap.py` | `build_phased_roadmap(evidence, score_raw)` | WIRED | Line 112 in executive.py |
| `quirk/reports/executive.py` | `quirk/assessment/migration_advisor.py` | `recommend_migration_paths(findings)` | WIRED | Line 113 in executive.py |
| `quirk/reports/writer.py` | `quirk/intelligence/scoring.py` | `compute_readiness_score(evidence, profile=cfg.intelligence.profile, weights=...)` | WIRED | Lines 115-118 in writer.py; `profile=cfg.intelligence.profile` explicitly present |
| `run_scan.py` | `quirk/assessment/operator_context.py` | `from quirk.assessment.operator_context import` | WIRED (untouched; not modified in phase) | Preserved as expected |

---

### Data-Flow Trace (Level 4)

Both `executive.py` and `writer.py` are wired and render dynamic data. Tracing from the score variable to its source:

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `executive.py::build_exec_markdown` | `score_raw["score"]` | `compute_readiness_score(build_evidence_summary(endpoints, findings))` | Yes — evidence derived from live endpoint/finding lists, not static | FLOWING |
| `executive.py::build_exec_markdown` | `roadmap_raw["items"]` | `build_phased_roadmap(evidence, score_raw)` | Yes — items generated from evidence and score | FLOWING |
| `writer.py::write_reports` | `intelligence["calibration"]` | `{"profile": cfg.intelligence.profile, "overrides_applied": bool(...)}` | Yes — reads from runtime config, not hardcoded | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| 28 scoring + consolidation tests pass | `python3 -m pytest tests/test_scoring_consolidation.py tests/test_intelligence_scoring.py -v` | 28 passed in 0.04s | PASS |
| Full test suite has no regressions | `python3 -m pytest tests/ -x -q` | 179 passed, 8 skipped in 2.27s | PASS |
| All Python files compile cleanly | `python3 -m compileall quirk/ -q` | No errors | PASS |
| Four deleted files are absent | Filesystem check via `AssessmentDeletionTests` | 4 deletion guards pass | PASS |
| No live import from deleted modules in production code | `grep "^from quirk.assessment.(readiness_score\|confidence\|transition_planner\|interpretation_engine)" quirk/ run_scan.py` | Zero matches | PASS |

---

### Requirements Coverage

The plans declare phase-local requirement IDs (SC-01 through SC-05) derived from CONCERNS.md §4.1–4.3, §1.7, §12.1. These IDs do not appear in `.planning/REQUIREMENTS.md` (which uses CORE/SCAN/CBOM/LAB/UI/DOC/BRAND prefixes for the v1 milestone). The SC codes are phase-local tracking identifiers mapped to the five Success Criteria in ROADMAP.md.

| Phase-Local ID | Plan | Description | Status |
|----------------|------|-------------|--------|
| SC-01 | 09-02 | Score consistency across all output artifacts | SATISFIED — both executive.py and writer.py call the same intelligence path |
| SC-02 | 09-02 | Roadmap format unification to NOW/NEXT/LATER | SATISFIED — wave_1/wave_2/wave_3 absent from both files; NOW/NEXT/LATER rendered |
| SC-03 | 09-03 | Four assessment compute modules deleted | SATISFIED — all four absent from filesystem; deletion guard tests pass |
| SC-04 | 09-01 | Profile-based weight differentiation functional | SATISFIED — PROFILE_MULTIPLIERS wired; strict vs lenient test passes |
| SC-05 | 09-01, 09-02 | Calibration overrides applied at runtime | SATISFIED — both call sites pass `weights=cfg.intelligence.calibration_overrides or None` |

**Cross-reference against `.planning/REQUIREMENTS.md`:** The v1 REQUIREMENTS.md contains CORE-01 ("Scoring system consolidation — deprecate duplicate paths") mapped to Phase 1. Phase 9 extends and completes the depth of this consolidation work (CORE-01 established the intelligence path; Phase 9 eliminates the residual assessment path from `executive.py` and wires profiles/calibration). No SC-prefix IDs appear in REQUIREMENTS.md; they are phase-local identifiers consistent with the ROADMAP.md derivation note. No orphaned requirements detected.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `quirk/reports/executive.py` | 20 | Comment `Ported from quirk.assessment.interpretation_engine` | Info | No impact — a docstring, not an import. The module is deleted; the comment is harmless provenance. |

No stubs, no hardcoded empty returns, no placeholder renders, no `TODO/FIXME` in modified files. The `@unittest.expectedFailure` decorators from Wave 0 were correctly removed in Plan 02.

---

### Human Verification Required

None. All Success Criteria are programmatically verifiable:

- Score consistency (SC-01) is enforced by the shared call path in code; verified by import-guard tests.
- Roadmap format (SC-02) verified by `test_executive_uses_now_next_later_roadmap`.
- Module deletion (SC-03) verified by `AssessmentDeletionTests` filesystem assertions.
- Profile differentiation (SC-04) verified by `test_profile_strict_scores_differently_from_lenient`.
- Calibration wiring (SC-05) verified by `test_calibration_overrides_applied` and call-site code inspection.

The one behavioral item that cannot be confirmed without a live scan run is whether the score in a real HTML report matches the executive summary markdown. However, this is architecturally guaranteed: the HTML report is rendered from the same `score` compat wrapper populated from `score_raw`, which is derived from `compute_readiness_score()` — the same function called by `executive.py`.

---

### Gaps Summary

No gaps. All five success criteria are satisfied:

1. The dual scoring path is eliminated — `executive.py` no longer calls `assessment/` compute modules for score, confidence, or roadmap.
2. Both call sites (`executive.py` and `writer.py`) pass `profile=` and `weights=` from `cfg.intelligence`.
3. All four deprecated assessment compute modules are deleted and guarded by filesystem tests.
4. Profile multipliers produce measurably different scores (1.4x vs 0.7x on agility/identity weights).
5. Calibration overrides are applied at runtime and override profile defaults.
6. The full test suite (179 passed, 8 skipped) has no regressions from this work.
7. Documentation updated with profile multiplier table and calibration override example.

---

_Verified: 2026-04-03T18:30:00Z_
_Verifier: Claude (gsd-verifier)_
