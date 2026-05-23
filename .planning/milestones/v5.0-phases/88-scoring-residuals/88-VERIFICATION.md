---
phase: 88-scoring-residuals
verified: 2026-05-22T00:00:00Z
status: human_needed
score: 5/5 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Open a CLI scan report (quirk scan ...) and confirm the '## Score Decomposition' table appears with six N/25 rows and the rollup line"
    expected: "All six subscore labels visible with numeric values e.g. 'Hygiene | 20 | /25' and a 'Rollup: X ÷ 1.5 = Y / 100' line"
    why_human: "The test_score_transparency.py gate validates the data-layer output of _scorecard_markdown but does not exercise the full CLI write_report path end-to-end"
  - test: "Open a generated HTML report in a browser and verify the Score Decomposition table renders with six subscore rows and the rollup math"
    expected: "A table headed 'Score Decomposition' with Hygiene / Modern TLS / Identity / Agility / Data at Rest / Data in Motion rows, each showing N/25, and a footer line 'X ÷ 1.5 = Y / 100'"
    why_human: "html_renderer.py passes subscores to Jinja2 template — rendering requires a browser or a full render pipeline; the Jinja2 context is wired but visual output is not programmatically asserted"
  - test: "Open a generated PDF report and verify the Score Decomposition table appears with six rows"
    expected: "Same table as HTML report visible in the PDF"
    why_human: "PDF rendering involves Playwright; cannot run in automated verification context without a running server"
---

# Phase 88: Scoring Residuals Verification Report

**Phase Goal:** The scoring system is correct and transparent: (EVIDENCE-TALLY-01) the evidence-tally semantics resolved by a model-grounded product decision; (RENDER-CLI-01/PDF-01) CLI/markdown and HTML/PDF reports verified against the Phase 86 normalized 0-100 contract; (SCORE-CBOM-01) the five zero-algo CBOM profiles emit real components or affirmative no-crypto markers (closes Phase 42 OBS-1); (SCORE-XPARENCY-01) reports surface the six subscores against their /25 budget with the overall rollup.
**Verified:** 2026-05-22
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A written product decision states orthogonal subscores are correct-by-design; won't-fix rationale committed inline (D-01 / EVIDENCE-TALLY-01) | VERIFIED | Module docstring of `tests/test_scoring_orthogonal_contract.py` lines 1-16 contains the explicit won't-fix resolution citing `quirk/intelligence/scoring.py` `_apply_weighted_impacts` and D-01 rejection of cross-category penalties |
| 2 | A parametrized six-subscore test locks the orthogonality contract — a finding in one category leaves all other five subscores at 25 (D-02) | VERIFIED | `test_subscore_orthogonality` parametrized over all six categories (hygiene, modern_tls, identity_trust, agility_signals, data_at_rest, data_in_motion); all 6 cases pass |
| 3 | CLI/markdown report overall + subscores match canonical scoring engine; Phase 86 0-100 int contract anchored (D-04 / RENDER-CLI-01, RENDER-PDF-01) | VERIFIED | `test_render_parity_all_surfaces` asserts writer-wrap dict equals canonical dict, dashboard re-call equals canonical, and overall is `int` in `[0,100]` with subscores each `int` in `[0,25]`; passes |
| 4 | All three non-dashboard report surfaces (CLI markdown, executive markdown, HTML/PDF) display all six subscores as `Label: N/25` plus `sum ÷ 1.5 = overall / 100` rollup (D-07 / SCORE-XPARENCY-01) | VERIFIED | `writer.py` line 109-115: `## Score Decomposition` block with six rows and `÷ 1.5` rollup; `executive.py` line 186-194: `### Score Decomposition` block; `html_renderer.py` line 206: `subscores=score.get("subscores", {})` kwarg; `report.html.j2` lines 155-169: guarded table with six rows and `÷ 1.5` rollup; `test_score_transparency.py` two tests pass |
| 5 | All five formerly-zero-algo CBOM profiles (database, registry, source, ssh-weak, storage-s3) emit real algorithm components OR affirmative hardcoded quirk:coverage-note markers; ssh-weak specifically emits diffie-hellman-group1-sha1, ssh-dss, hmac-md5 (D-05/D-06 / SCORE-CBOM-01, closes Phase 42 OBS-1) | VERIFIED | `test_zero_algo_profile_emits_components_or_marker` passes for all five profiles; `test_ssh_weak_emits_real_weak_algorithm_components` passes asserting the three specific weak algorithms |

**Score:** 5/5 truths verified

---

## D-01 Critical Check: scoring.py Math Unchanged

**Status: VERIFIED**

`git log --oneline 3a13c8d..HEAD -- quirk/intelligence/scoring.py` produces empty output — no commits touched scoring.py during Phase 88. The `_apply_weighted_impacts` function at lines 103-111 and the `sum(six subscores) / 1.5` overall at lines 255-258 are identical to the pre-phase baseline. No overall critical-cap was introduced (grep for "critical_cap" / "critical.cap" across `quirk/intelligence/scoring.py` and `quirk/reports/` returns zero results).

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tests/test_scoring_orthogonal_contract.py` | Forward-locking orthogonality invariant (D-02); contains `compute_readiness_score` | VERIFIED | 185-line file; parametrized over all 6 categories; module docstring has won't-fix rationale |
| `tests/test_score_render_parity.py` | Data-layer parity gate (D-04); contains `compute_readiness_score` | VERIFIED | Asserts writer-wrap, dashboard-recall, and Phase 86 int-range contract |
| `tests/test_score_transparency.py` | Subscore decomposition render gate (D-07); contains `/25` | VERIFIED | Two tests asserting `/25`, `÷ 1.5`, and `Score Decomposition` in both markdown surfaces |
| `quirk/reports/writer.py` | Scorecard markdown decomposition block; contains `Score Decomposition` | VERIFIED | Line 109: `## Score Decomposition`; six-row table plus rollup |
| `quirk/reports/executive.py` | Executive markdown decomposition section; contains `Score Decomposition` | VERIFIED | Line 186: `### Score Decomposition`; six-row table plus rollup |
| `quirk/reports/templates/report.html.j2` | HTML/PDF subscore table; contains `Score Decomposition` | VERIFIED | Lines 155-169: guarded `{% if subscores %}` table with six rows and rollup |
| `quirk/cbom/classifier.py` | Weak SSH algorithm entries including `diffie-hellman-group1-sha1` | VERIFIED | Lines 68, 80, 97-99: all five weak SSH entries present with correct (primitive, 0, bits) tuple shape |
| `quirk/cbom/builder.py` | D-06 coverage-note emission; contains `quirk:coverage-note` | VERIFIED | `_emit_coverage_note` helper at line 373; 5 `coverage_notes.append()` call sites at lines 443, 456, 539, 550, 572 using hardcoded string literals |
| `tests/test_cbom_zero_algo_profiles.py` | Per-profile components-or-marker gate; contains `quirk:coverage-note` | VERIFIED | Parametrized over 5 profiles + dedicated ssh-weak specific-algo test |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `quirk/reports/html_renderer.py` | `report.html.j2` | `subscores=score.get("subscores", {})` kwarg | WIRED | Line 206 confirmed; template reads `subscores.get('hygiene')` etc. |
| `quirk/reports/writer.py` | score dict | `score.get("subscores")` (WRAPPED dict) | WIRED | Lines 108-115 confirmed; correctly uses wrapped dict key |
| `quirk/cbom/builder.py` | `bom.metadata.component.properties` | `Property(name="quirk:coverage-note")` | WIRED | Lines 373-384 (`_emit_coverage_note`); lines 753-754 apply notes to `root_component` after Pass-1 |
| `quirk/cbom/builder.py` SSH branch | `quirk/cbom/classifier.py _ALGORITHM_TABLE` | `_register_algorithm` for ssh-audit weak algorithms | WIRED | `diffie-hellman-group1-sha1` at classifier line 68; `ssh-dss` at 80; `hmac-md5` at 97; all resolve non-UNKNOWN |

---

## Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `writer.py` `_scorecard_markdown` decomposition block | `score.get("subscores")` | `compute_readiness_score` via `writer.py` line 157 call | Yes — live integer subscores from canonical engine | FLOWING |
| `executive.py` `build_exec_markdown` decomposition section | `score_raw.get("subscores")` | `compute_readiness_score` called at `executive.py` line ~120 | Yes — same canonical engine, independent call | FLOWING |
| `report.html.j2` subscore table | `subscores` Jinja2 variable | `html_renderer.py` line 206: `subscores=score.get("subscores", {})` | Yes — same wrapped dict, integer values | FLOWING |
| `builder.py` coverage-note properties | Hardcoded string literals | `_emit_coverage_note` with HARDCODED constants (T-88-03) | Yes — affirmative marker, never scanner-derived | FLOWING |

---

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All 15 Phase 88 tests pass | `QUIRK_DB_PATH="$(mktemp -d)/fresh.db" python -m pytest tests/test_scoring_orthogonal_contract.py tests/test_score_render_parity.py tests/test_score_transparency.py tests/test_cbom_zero_algo_profiles.py -v -q` | 15 passed in 0.15s | PASS |
| Full suite: zero new failures vs 39-failure baseline | `QUIRK_DB_PATH="$(mktemp -d)/fresh.db" python -m pytest tests/ -q` | 39 failed, 1806 passed — exactly +15 new passing, 0 new failures | PASS |
| All modified files compile cleanly | `python -m compileall quirk/reports/writer.py quirk/reports/executive.py quirk/reports/html_renderer.py quirk/cbom/builder.py quirk/cbom/classifier.py -q` | Exit 0, no output | PASS |
| Weak SSH algo classifier gate | `python -c "from quirk.cbom.classifier import classify_algorithm as c; from cyclonedx.model.crypto import CryptoPrimitive as P; assert c('ssh-dss')[0]!=P.UNKNOWN and c('hmac-md5')[0]!=P.UNKNOWN and c('diffie-hellman-group1-sha1')[0]!=P.UNKNOWN"` | Exit 0 | PASS |
| scoring.py untouched in phase 88 commits | `git log --oneline 3a13c8d..HEAD -- quirk/intelligence/scoring.py` | Empty — zero commits | PASS |

---

## Probe Execution

No `scripts/*/tests/probe-*.sh` files declared or found for Phase 88. Phase 88 is a scoring/CBOM/test phase with no CLI probe scripts — Step 7c skipped (no declared probes).

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| EVIDENCE-TALLY-01 | 88-01 | Orthogonal subscore product decision + won't-fix rationale + parametrized lock | SATISFIED | Module docstring in `test_scoring_orthogonal_contract.py`; 6 parametrized tests pass |
| RENDER-CLI-01 | 88-01 | CLI/markdown render parity against Phase 86 0-100 contract | SATISFIED | `test_render_parity_all_surfaces` passes; single engine confirmed (D-03); writer.py `Score Decomposition` block present |
| RENDER-PDF-01 | 88-01 | HTML/PDF render parity against Phase 86 0-100 contract | SATISFIED (data-layer) | Same parity gate covers both surfaces at data layer; HTML template wired; PDF rendering requires human visual check |
| SCORE-CBOM-01 | 88-02 | Five zero-algo profiles emit real components or affirmative markers | SATISFIED | 6 tests pass (5 profile tests + ssh-weak specific-algo test); Phase 42 OBS-1 closed |
| SCORE-XPARENCY-01 | 88-01 | Six subscores as N/25 + rollup on all three report surfaces | SATISFIED | Decomposition block in writer.py, executive.py, report.html.j2; transparency tests pass |

**Note on REQUIREMENTS.md and ROADMAP.md documentation state:** The `REQUIREMENTS.md` tracking rows for all five IDs still show `[ ]` and `pending`, and the ROADMAP.md plan checkboxes `88-01-PLAN.md` / `88-02-PLAN.md` remain `[ ]`. Implementation is complete; documentation closure is a bookkeeping step the phase executor did not complete. This is consistent with how Phase 87 was handled (those rows were closed at milestone-complete time by the orchestrator). This is a WARNING, not a BLOCKER — the implementation is fully in place.

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| No debt markers (TBD/FIXME/XXX) found in any phase 88 modified files | — | — | — | — |
| No placeholder or stub patterns found in decomposition blocks | — | — | — | — |

Scanned files: `tests/test_scoring_orthogonal_contract.py`, `tests/test_score_render_parity.py`, `tests/test_score_transparency.py`, `tests/test_cbom_zero_algo_profiles.py`, `quirk/reports/writer.py`, `quirk/reports/executive.py`, `quirk/reports/html_renderer.py`, `quirk/reports/templates/report.html.j2`, `quirk/cbom/builder.py`, `quirk/cbom/classifier.py`. No `TBD`, `FIXME`, `XXX`, `PLACEHOLDER`, or `return null` / `return []` patterns found in any phase 88 artifacts. Coverage-note values confirmed as hardcoded string literals, not scanner-derived f-strings (T-88-03 satisfied).

---

## ROADMAP Success Criteria Mapping

From ROADMAP.md Phase 88 `success_criteria`:

1. **A written product decision states whether three subscores returning 25 despite findings is a defect or correct-by-design** — VERIFIED: `test_scoring_orthogonal_contract.py` module docstring commits the decision explicitly ("won't-fix at the subscore level") with architectural grounding.

2. **CLI/markdown report's overall readiness value matches the dashboard for the same scan ID** — VERIFIED (data-layer): `test_render_parity_all_surfaces` proves single-engine + identical values; human visual check of CLI output deferred to human verification item 1.

3. **HTML/Playwright-PDF report's overall readiness value matches the dashboard** — VERIFIED (data-layer): same parity gate; HTML template wired with subscores; PDF visual output deferred to human verification item 3.

4. **`builder.py` Pass-1 emits non-empty algorithm components for all five previously-zero profiles — or each zero-output profile has explicit documentation that its zero output is correct** — VERIFIED: `test_zero_algo_profile_emits_components_or_marker` passes for all five; profiles with genuinely plaintext endpoints carry affirmative `quirk:coverage-note` Properties (explicit documentation as required).

5. **CLI/HTML/PDF reports and the dashboard both display the six subscore labels with their `/25` budgets so an operator can trace how the overall score was calculated** — VERIFIED (code): Decomposition blocks present on all three report surfaces; `test_score_transparency.py` locks the contract. Visual rendering confirmed via code inspection; human rendering check deferred.

---

## Human Verification Required

### 1. CLI markdown report — Score Decomposition table visible

**Test:** Run a real scan with `quirk scan ...` (or replay from a saved DB) and view the generated scorecard markdown report.
**Expected:** A `## Score Decomposition` table appears with six rows (`Hygiene`, `Modern TLS`, `Identity`, `Agility`, `Data at Rest`, `Data in Motion`), each showing an integer value and `/25`, followed by a `**Rollup:** X ÷ 1.5 = **Y / 100**` line.
**Why human:** `test_score_transparency.py` validates the function return value but does not exercise the full `write_report()` path including file writing and the CLI rendering pipeline.

### 2. HTML report — Score Decomposition table renders correctly in browser

**Test:** Open a generated `report.html` file in a browser.
**Expected:** A `Score Decomposition` section appears with the six subscore rows (N/25 format) and a rollup math line. The `{% if subscores %}` guard is satisfied (subscores dict is non-empty for any real scan).
**Why human:** Jinja2 template rendering with live data requires a browser; automated tests verify the context dict is populated but not the rendered visual output.

### 3. PDF report — Score Decomposition table present

**Test:** Generate a PDF report (requires Playwright) and open it.
**Expected:** Same Score Decomposition table visible in the PDF.
**Why human:** PDF generation requires Playwright and a running browser subprocess; cannot be run in static verification context.

---

## Gaps Summary

No implementation gaps found. All five ROADMAP success criteria are met in the codebase.

Two non-blocking documentation items were observed:
- `REQUIREMENTS.md` tracking rows for all five IDs remain `[ ]` / `pending` (bookkeeping, not an implementation gap — consistent with project pattern where orchestrator closes rows at milestone-complete time).
- `ROADMAP.md` Phase 88 plan and phase checkboxes remain `[ ]` (same bookkeeping gap).

Three human verification items remain for visual/rendered output confirmation.

---

## Test Differential Confirmation

| Metric | Pre-Phase Baseline | Post-Phase Actual | Delta |
|--------|-------------------|-------------------|-------|
| Passing tests | 1791 | 1806 | +15 |
| Failing tests | 39 | 39 | 0 |
| New failures | — | 0 | — |

The 39 pre-existing failures are all in unrelated areas (version strings, dashboard theme tokens, chaos compose-profile drift, qramm tables) — none in any Phase 88 artifact.

---

_Verified: 2026-05-22_
_Verifier: Claude (gsd-verifier)_
