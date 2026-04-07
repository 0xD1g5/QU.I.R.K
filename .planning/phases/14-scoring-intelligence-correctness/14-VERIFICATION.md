---
phase: 14-scoring-intelligence-correctness
verified: 2026-04-06T00:00:00Z
status: passed
score: 4/4 must-haves verified
gaps: []
---

# Phase 14: Scoring Intelligence Correctness — Verification Report

**Phase Goal:** Ensure scoring engine and intelligence layer produce correct, deterministic outputs — validated by automated tests covering all four SCORE requirements.
**Verified:** 2026-04-06
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | strict profile produces lower score than lenient on penalized evidence | VERIFIED | `test_strict_scores_lower_than_lenient_on_penalized_evidence` passes; strict=59, lenient=76 confirmed by live test run |
| 2 | validate_run has no require_delta_if_baseline parameter | VERIFIED | `grep -c "require_delta_if_baseline" quirk/validate.py` returns 0; `validate_run(output_dir: Path)` at line 105 confirmed |
| 3 | Legacy TLS migration recommendations surface from risk_engine findings | VERIFIED | Three MigrationAdvisorTests pass; pattern matching on "legacy tls", "plaintext http", and INFO filter all correct |
| 4 | Dashboard score matches CLI score when non-default profile is configured | VERIFIED | `compute_readiness_score(evidence, profile=stored_profile)` at scan.py line 345; `calibration.profile` read at line 338 |

**Score: 4/4 truths verified**

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tests/test_scoring_correctness.py` | RED scaffold + GREEN after fixes, min 80 lines, contains ScoringCorrectnessTests | VERIFIED | 198 lines, 4 test classes, 8 test methods, all GREEN |
| `quirk/validate.py` | Clean validate_run signature without dead delta parameter; `def validate_run(output_dir: Path)` | VERIFIED | Signature confirmed at line 105; zero occurrences of `require_delta_if_baseline`, `no-require-delta`, `no_require_delta` |
| `quirk/dashboard/api/routes/scan.py` | Profile-aware dashboard scoring; contains "calibration" | VERIFIED | `stored_profile` block lines 327-340; `compute_readiness_score(evidence, profile=stored_profile)` at line 345 |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `tests/test_scoring_correctness.py` | `quirk/intelligence/scoring.py` | `from quirk.intelligence.scoring import compute_readiness_score` | WIRED | Line 11 of test file; import confirmed and used in ScoringCorrectnessTests and DashboardProfileTests |
| `tests/test_scoring_correctness.py` | `quirk/validate.py` | `from quirk.validate import validate_run` | WIRED | Line 12 of test file; used in ValidateCorrectnessTests |
| `tests/test_scoring_correctness.py` | `quirk/assessment/migration_advisor.py` | `from quirk.assessment.migration_advisor import recommend_migration_paths` | WIRED | Line 13 of test file; used in MigrationAdvisorTests |
| `quirk/dashboard/api/routes/scan.py` | `quirk/validate.py` | `from quirk.validate import _latest_intelligence` | WIRED | Line 332 of scan.py; import inside try block; used at line 335 to resolve intel path |
| `quirk/dashboard/api/routes/scan.py` | intelligence JSON calibration.profile field | json.loads and dict access | WIRED | `_intel_data.get("calibration", {}).get("profile")` at line 338; `QUIRK_OUTPUT_DIR` env var at line 334 |
| `quirk/validate.py` | validate_run callers | removed require_delta_if_baseline param | WIRED | `def validate_run(output_dir: Path)` — parameter fully removed, no callers pass second arg |

---

### Data-Flow Trace (Level 4)

The primary artifacts for this phase are a test file and two source fixes — not UI-rendering components. Level 4 data-flow applies to the dashboard route fix.

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `quirk/dashboard/api/routes/scan.py` (`get_latest_scan`) | `stored_profile` | `_latest_intelligence(output_dir)` reading calibration.profile from intelligence JSON on disk | Yes — reads actual JSON written by a scan run; falls back to `None` (balanced) on I/O error | FLOWING |
| `quirk/dashboard/api/routes/scan.py` (`get_latest_scan`) | `score_raw` | `compute_readiness_score(evidence, profile=stored_profile)` | Yes — uses real evidence from DB-derived endpoints | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All 8 SCORE tests pass | `python3 -m pytest tests/test_scoring_correctness.py -v` | 8 passed in 0.17s | PASS |
| Full 223-test suite passes (no regressions) | `python3 -m pytest tests/ -v --tb=short` | 223 passed in 2.56s | PASS |
| Python compilation clean | `python3 -m compileall quirk/` | No errors | PASS |
| Dead parameter removed | `grep -c "require_delta_if_baseline" quirk/validate.py` | 0 | PASS |
| Profile kwarg present in dashboard | `grep -n "profile=" quirk/dashboard/api/routes/scan.py` | Line 345: `compute_readiness_score(evidence, profile=stored_profile)` | PASS |
| Calibration field used (not assessment) | `grep -n "calibration" quirk/dashboard/api/routes/scan.py` | Line 338: `_intel_data.get("calibration", {}).get("profile")` | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| SCORE-01 | 14-01, 14-02 | Calibration profile applied to weight multipliers in `compute_readiness_score()` | SATISFIED | `PROFILE_MULTIPLIERS` wired in scoring.py lines 22-26; `test_strict_scores_lower_than_lenient_on_penalized_evidence` PASSES confirming strict < lenient |
| SCORE-02 | 14-01, 14-02 | `validate.py` checks artifacts `write_reports()` actually produces; dead `require_delta_if_baseline` removed | SATISFIED | `validate_run(output_dir: Path)` at line 105; zero dead-param occurrences; `test_validate_run_no_delta_param` and `test_validate_main_no_delta_arg` both PASS |
| SCORE-03 | 14-01, 14-02 | `migration_advisor.py` finding pattern strings match `risk_engine.py` finding titles | SATISFIED | `migration_advisor.py` matches "legacy tls" and "plaintext http" case-insensitively; three MigrationAdvisorTests PASS including INFO-filter guard |
| SCORE-04 | 14-01, 14-02 | Dashboard passes scan-time profile kwarg to `compute_readiness_score()` | SATISFIED | `scan.py` lines 327-345 read `calibration.profile` from intelligence JSON and pass `profile=stored_profile`; `test_dashboard_score_call_uses_profile_kwarg` and `test_dashboard_reads_calibration_profile_not_assessment` both PASS |

**Orphaned requirements check:** REQUIREMENTS.md maps SCORE-01 through SCORE-04 to Phase 14. All four are covered by plans 14-01 and 14-02. No orphaned requirements.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `quirk/dashboard/api/routes/scan.py` | 339-340 | `except Exception: pass` swallows errors silently in profile read | Info | If intelligence JSON is malformed or missing, profile silently defaults to balanced — this is intentional fallback behavior per plan design; not a blocking stub |

No stubs, placeholders, or TODO markers found in phase-modified files.

---

### Human Verification Required

None. All goal behaviors are verifiable programmatically via the test suite and source inspection. The `test_dashboard_reads_calibration_profile_not_assessment` test uses `inspect.getsource` to verify the correct field path without requiring a live server, eliminating the primary ambiguity risk for SCORE-04.

---

### Gaps Summary

None. All four SCORE requirements are satisfied and all 8 tests pass. The full 223-test suite is green with zero regressions. Both committed fixes (`a5e160c` and `5a57eb1`) are present in git history and verified in the working tree.

**Phase 14 goal: ACHIEVED.**

---

_Verified: 2026-04-06_
_Verifier: Claude (gsd-verifier)_
