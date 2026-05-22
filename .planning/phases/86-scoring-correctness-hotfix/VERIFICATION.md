---
phase: 86-scoring-correctness-hotfix
verified: 2026-05-22T10:00:00Z
status: passed
score: 5/5 must-haves verified
overrides_applied: 0
---

# Phase 86: Scoring Correctness Hotfix — Verification Report

**Phase Goal:** As a security consultant, I want to have the executive-summary overall readiness score reflect actual scan posture, so that the marquee number doesn't contradict the visible CRITICAL findings and red subscore gauges below it.
**Verified:** 2026-05-22
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths (5 ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Scan against `tls-cert-defects` shows overall < 100, non-EXCELLENT rating; canonical 25+25+23+3+25+19 displays as ~80 | ✓ VERIFIED | `compute_readiness_score` now uses `int(round(sum / 1.5))` at scoring.py:255-258. Test `test_overall_score_canonical_example_120_to_80` passes (120 → 80). HUMAN-UAT Criterion 1: PASS (live scan confirmed overall < 100). |
| 2 | Six subscore radials display color matching penalty state; overall gauge keeps default maxValue=100 | ✓ VERIFIED | `ScoreGauge.tsx`: `_gaugeColor(fraction)` uses thresholds 0.8/0.5; `executive.tsx` lines 262-267 pass `maxValue={25}` on all six subscores; overall gauge at lines 245-250 has no `maxValue` prop (defaults to 100). HUMAN-UAT Criterion 2: PASS after hard refresh. Vitest: 4 tests pass. |
| 3 | `pytest tests/test_score_weights_invariant.py` passes; new normalization-boundary test asserts overall=100 iff all subscores=25, overall=0 iff all=0 | ✓ VERIFIED | pytest run confirmed: 5/5 pass — `test_overall_score_max_when_all_subscores_at_25 PASSED`, `test_overall_score_zero_when_all_subscores_zero PASSED`, `test_overall_score_canonical_example_120_to_80 PASSED`, `test_score_weights_sum_invariant PASSED`, `test_score_weights_count_invariant PASSED`. |
| 4 | scoring.py:1-17 docstring names 0-25 subscores and int(round(sum/1.5)) formula; no "Phase 60 SCORE-04 clamp-to-[0,100] is intentional" wording | ✓ VERIFIED | Lines 5-18 read: "Scoring contract (v4.10.1, Phase 86 D-01): Each of the six categories is scored on a 0-25 scale... overall readiness score is then: total_score = int(round((sum of six 0-25 subscores) / 1.5))". grep for "clamp.*intentional\|Phase 60 SCORE-04" returns no matches in lines 1-17. |
| 5 | pyproject.toml version=4.10.1; changelog.d/ entry has canonical 25+25+23+3+25+19 example + visual-jump note | ✓ VERIFIED | pyproject.toml line 7: `version = "4.10.1"`. `changelog.d/v4.10.1.bugfix.md` exists and contains: the canonical 25+25+23+3+25+19 table; "Old stored scores will display lower after upgrade"; "The underlying per-category penalty math is unchanged". |

**Score:** 5/5 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `quirk/intelligence/scoring.py` | Normalized aggregator + corrected docstring | ✓ VERIFIED | Lines 255-258: `int(round((...) / 1.5))`. Docstring lines 5-18 rewritten. Commit `7d0f71e`. |
| `tests/test_scoring_normalization.py` | 3 boundary tests (max, zero, canonical) | ✓ VERIFIED | File exists with `test_overall_score_max_when_all_subscores_at_25`, `test_overall_score_zero_when_all_subscores_zero`, `test_overall_score_canonical_example_120_to_80`. All pass. Commit `96f5ebd`. |
| `tests/test_score_weights_invariant.py` | Sum=275.0 / count=36 invariant preserved | ✓ VERIFIED | Unchanged; both invariants hold. Pass confirmed. |
| `src/dashboard/src/components/gauges/ScoreGauge.tsx` | maxValue prop + normalized color thresholds | ✓ VERIFIED | `maxValue?: number` in interface; `const fraction = Math.max(0, Math.min(1, score / maxValue))`; `_gaugeColor(fraction)` with 0.8/0.5 thresholds. No `score / 100` in live code. Commit `fad2ced`. |
| `src/dashboard/src/pages/executive.tsx` | 6x `maxValue={25}` on subscores; overall unchanged | ✓ VERIFIED | Lines 262-267: all six subscore gauges pass `maxValue={25}`. Lines 244-250: overall gauge has no maxValue prop. `grep -c` = 6. Commit `620e5db`. |
| `src/dashboard/src/pages/data-at-rest.tsx` | 1x `maxValue={25}` on standalone DAR gauge | ✓ VERIFIED | Line 301: `<ScoreGauge score={darScore} label="Data at Rest" size={120} maxValue={25} />`. `grep -c` = 1. Commit `620e5db`. |
| `src/dashboard/src/components/gauges/__tests__/ScoreGauge.test.tsx` | 4 vitest cases (green-at-max, red-at-low, amber/green boundary, legacy-default) | ✓ VERIFIED | File exists with 4 `it(...)` cases; all 4 pass (74 total tests pass). Commit `b9bab9e`. |
| `pyproject.toml` | version = "4.10.1" | ✓ VERIFIED | Line 7: `version = "4.10.1"`. Commit `94ac361`. |
| `changelog.d/v4.10.1.bugfix.md` | Operator language + canonical example + visual-jump note | ✓ VERIFIED | Contains: canonical table (25+25+23+3+25+19 → 100 → 80); "Old stored scores will display lower"; "underlying per-category penalty math is unchanged". Commit `94ac361`. |
| `.planning/phases/86-scoring-correctness-hotfix/HUMAN-UAT.md` | PASS record with 4 criteria signed off | ✓ VERIFIED | `**Result:** PASS` present. All 4 criteria marked PASS. Operator: Digs. Date: 2026-05-22. Screenshots `uat-86-hf1.png` and `uat-86-hf2.png` on disk. Commit `bce265b`. |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `scoring.py compute_readiness_score` | `_apply_weighted_impacts(score_cap=25.0)` | Six per-category calls; sum normalized by 1.5 | ✓ WIRED | Lines 255-258 sum all six subscores then apply `int(round(.../1.5))`. `_apply_weighted_impacts` unchanged. |
| `tests/test_scoring_normalization.py` | `quirk.intelligence.scoring.compute_readiness_score` | Direct import + monkeypatch for canonical case | ✓ WIRED | `from quirk.intelligence.scoring import compute_readiness_score` present; canonical test uses `monkeypatch.setattr` on `_apply_weighted_impacts`. |
| `ScoreGauge.tsx _gaugeColor` | arc fill calculation | `fraction = score / maxValue` shared fraction | ✓ WIRED | `fillEndAngle = Math.PI - fraction * Math.PI`; `_gaugeColor(fraction)` called on line 40. |
| `executive.tsx subscore row` | `ScoreGauge maxValue prop` | Explicit `maxValue={25}` on each of 6 subscore gauges | ✓ WIRED | grep confirms exactly 6 occurrences in executive.tsx. |
| `data-at-rest.tsx:301` | `ScoreGauge maxValue prop` | `maxValue={25}` on standalone DAR tab gauge | ✓ WIRED | Confirmed at line 301. |

---

### Requirements Coverage

| Requirement | Plan | Description | Status | Evidence |
|-------------|------|-------------|--------|----------|
| SCORE-FIX-01 | 86-01 | `compute_readiness_score()` uses `int(round(sum/1.5))` | ✓ SATISFIED | scoring.py:255-258 confirmed. Test proves 120→80. |
| SCORE-FIX-02 | 86-01 | Module docstring accurately describes 0-25 + normalize-by-1.5; no misleading clamp language | ✓ SATISFIED | Lines 5-18 rewritten. No "clamp intentional" wording. |
| SCORE-FIX-03 | 86-01 | New test asserts overall=100 iff all subscores=25, overall=0 iff all=0 | ✓ SATISFIED | `test_scoring_normalization.py` — 3 tests all pass. |
| GAUGE-01 | 86-02 | `ScoreGauge` accepts `maxValue?: number` (default 100) | ✓ SATISFIED | Prop in interface; `maxValue = 100` default in signature. |
| GAUGE-02 | 86-02 | `_gaugeColor()` operates on normalized fraction (0-1) | ✓ SATISFIED | `_gaugeColor(fraction: number)` with 0.8/0.5 thresholds. |
| GAUGE-03 | 86-02 | `executive.tsx` passes `maxValue={25}` to all 6 subscore gauges; overall keeps default | ✓ SATISFIED | 6 occurrences confirmed; overall gauge has no maxValue. |
| RELEASE-01 | 86-03 | Changelog entry with canonical example + visual-jump note | ✓ SATISFIED | `changelog.d/v4.10.1.bugfix.md` confirmed. |
| RELEASE-02 | 86-03 | `pyproject.toml [project.version]` = 4.10.1 | ✓ SATISFIED | Line 7 confirmed. |

**Coverage: 8/8 requirements satisfied.**

---

### Out-of-Scope Guards (D-14/D-15/D-16)

| Guard | Files Checked | Status |
|-------|---------------|--------|
| D-14: NO edits to `quirk/reports/executive.py` or `quirk/reports/html_renderer.py` | Phase 86 commits: 96f5ebd, 7d0f71e, fad2ced, 620e5db, b9bab9e, 94ac361, 34eb1f9, bce265b | ✓ CLEAN — none of these Phase 86 commits touched either file. (Commit `81deeb9` touched `html_renderer.py` but that is a pre-Phase-86 post-ship v4.10 cleanup commit listed in CONTEXT.md dependencies, not a Phase 86 execution commit.) |
| D-15: NO edits to evidence summarizer | No Phase 86 commit touched `quirk/intelligence/evidence.py` | ✓ CLEAN |
| D-16: NO SQLite migration | No schema migration files added or modified | ✓ CLEAN |
| `print.tsx` NOT a caller (per revised D-07) | `print.tsx` not in any Phase 86 commit's changed files | ✓ CONFIRMED |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `compute_readiness_score` returns 80 for canonical 120-sum | pytest `test_overall_score_canonical_example_120_to_80` | PASSED | ✓ PASS |
| Weight-sum invariant 275.0 preserved | pytest `test_score_weights_sum_invariant` | PASSED | ✓ PASS |
| Weight-count invariant 36 preserved | pytest `test_score_weights_count_invariant` | PASSED | ✓ PASS |
| All boundary tests green | pytest `tests/test_scoring_normalization.py tests/test_score_weights_invariant.py` | 5/5 passed in 0.03s | ✓ PASS |
| No forbidden docstring language | `grep "clamp.*intentional\|Phase 60 SCORE-04" scoring.py` | No matches in lines 1-17 | ✓ PASS |

---

### Anti-Patterns Found

None. No TBD/FIXME/XXX markers in Phase 86 modified files. No stub return patterns. No hardcoded empty data flowing to rendering.

---

### Human Verification

Human operator UAT already completed and recorded:

**HUMAN-UAT.md** — Operator: Digs, Date: 2026-05-22, Result: PASS

- Criterion 1 (Overall gauge < 100, non-EXCELLENT): PASS
- Criterion 2 (Six subscore radials correct colors, post-hard-refresh): PASS
- Criterion 3 (Data at Rest tab parity with Executive Summary): PASS
- Criterion 4 (Screenshots captured — `uat-86-hf1.png` diagnostic + `uat-86-hf2.png` canonical evidence): PASS

Note: Initial render showed stale bundle (browser cache); hard refresh (Cmd+Shift+R) produced correct rendering. This is documented in HUMAN-UAT.md and captured as a durable memory entry.

---

### Gaps Summary

No gaps. All 5 ROADMAP success criteria verified against codebase evidence. All 8 requirements satisfied. Out-of-scope guards held. Tests pass. UAT signed off by operator.

---

**Note:** ROADMAP.md progress table still shows "2/3 plans complete" and 86-03-PLAN.md checkbox unchecked. This is a documentation bookkeeping gap — the ROADMAP was not updated in the `bce265b` UAT close commit. This does NOT affect goal achievement (all code, tests, release engineering, and UAT are complete and verified). The ROADMAP update is a housekeeping task for the orchestrator's `update_roadmap` step.

---

_Verified: 2026-05-22T10:00:00Z_
_Verifier: Claude (gsd-verifier)_
