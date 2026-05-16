---
phase: 74-qramm-compliance-warnings
verified: 2026-05-15T00:00:00Z
status: passed
score: 3/3 must-haves verified
overrides_applied: 0
---

# Phase 74: QRAMM + Compliance WARNINGs Verification Report

**Phase Goal:** All three WARNING clusters in the QRAMM/compliance subsystem are resolved — practice scores reject out-of-range inputs, the evidence bridge is TZ-safe and idempotent, and migration advisor precision, coverage disambiguation, and stale comments are fixed. Closes audit findings qramm-compliance/WR-01 through WR-13.

**Verified:** 2026-05-15
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP SCs)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `compute_practice_score` raises clear validation error for out-of-range; Practice 1.1 incorporates endpoint count; vuln_pct guarded against zero; Maturity `>= 4.0` reachable | VERIFIED | `quirk/qramm/scoring.py:30-31` raises `ValueError("...out of range [0, 4]")`; `quirk/qramm/evidence_bridge.py:38-44,107` `_discovery_factor` scales score_1_1 by `log10(endpoint_count)/3` in [0.25, 1.0]; `vuln_pct` returns sentinel `None` -> "Indeterminate" maturity label at `scoring.py:77,85`; band threshold lowered to `>= 3.95` at `scoring.py:82,86` per D-04 |
| 2 | Evidence bridge date comparison uses `datetime.date` and is TZ-safe; `synchronize_session` idempotent; `db.commit` failures handled and logged; `attach_context` `AttributeError` logged not swallowed | VERIFIED | `evidence_bridge.py:17` imports `SQLAlchemyError`; `:172-176` wraps UPDATE in try/except logging+rollback; `fromisoformat` pattern referenced; `attach_context` AttributeError logged via `logger.warning` (D-07) |
| 3 | Migration advisor false positives reduced; `_walk_json_for_alg_strings` covers all ALG_KEYS; compliance weight 0.0 vs not-yet-covered disambiguated; `model_meta.py` has `is_qramm_model_stale()`; stale Phase 50 TODO removed | VERIFIED | `quirk/assessment/migration_advisor.py:12,21` defines `CANONICAL_ALG_SYNONYMS` + `_matches` word-boundary regex; `evidence_bridge.py:216-257` `_walk_json_for_alg_strings` scans non-ALG_KEYS strings via `_matches`; `quirk/qramm/compliance_map.py:20,53` adds `CoverageStatus` Literal + `SCANNER_COVERAGE_STATUS`; `quirk/qramm/model_meta.py:28` `is_qramm_model_stale(today=None)`; no `TODO Phase 50` in `quirk/compliance/__init__.py` |

**Score:** 3/3 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `quirk/qramm/scoring.py` | D-01 ValueError, D-03 Indeterminate, D-04 >= 3.95 | VERIFIED | All three present (lines 30-31, 77/85, 82/86) |
| `quirk/qramm/evidence_bridge.py` | D-02 discovery_factor, D-05 fromisoformat, D-06 idempotency, D-07 attach_context log, D-09 _walk extension | VERIFIED | All present; imports `SQLAlchemyError` and `CANONICAL_ALG_SYNONYMS, _matches` from migration_advisor |
| `quirk/assessment/migration_advisor.py` | D-08 CANONICAL_ALG_SYNONYMS + _matches helper | VERIFIED | Line 12 dict, line 21 helper |
| `quirk/qramm/compliance_map.py` | D-10 SCANNER_COVERAGE_STATUS + CoverageStatus | VERIFIED | Line 53 dict, line 20 type |
| `quirk/qramm/model_meta.py` | D-11 is_qramm_model_stale | VERIFIED | Line 28 public function with `today=None` default + strict `>` boundary |
| `quirk/compliance/__init__.py` | D-12 stale TODO removed | VERIFIED | No "TODO Phase 50" grep match in file |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Test suite (5 modules) | `python -m pytest tests/test_qramm_practice_scoring.py tests/test_evidence_bridge_correctness.py tests/test_migration_advisor_precision.py tests/test_compliance_coverage_status.py tests/test_qramm_model_stale.py -q` | 47 passed in 0.20s | PASS |
| Module compile | `python -m compileall quirk/` | exit 0 | PASS |

All 5 expected Phase 74 test files exist:
- `tests/test_qramm_practice_scoring.py` (exists)
- `tests/test_evidence_bridge_correctness.py` (exists)
- `tests/test_migration_advisor_precision.py` (exists)
- `tests/test_compliance_coverage_status.py` (exists)
- `tests/test_qramm_model_stale.py` (exists)

### Audit Ledger Closure

All 13 `qramm-compliance/WR-*` rows in `AUDIT-TASKS.md` (lines 124-136) are marked `Phase 74 | [x] closed`:

| Row | Status | Evidence Recorded |
|-----|--------|-------------------|
| WR-01 | closed | Evidence bridge TZ-safe (D-05) |
| WR-02 | closed | compute_practice_score out-of-range ValueError (D-01) |
| WR-03 | closed | synchronize_session idempotency (D-06) |
| WR-04 | closed | Practice 1.1 Discovery endpoint factor (D-02) |
| WR-05 | closed | vuln_pct Indeterminate sentinel (D-03) |
| WR-06 | closed | Maturity >= 3.95 ceiling reachable (D-04) |
| WR-07 | closed | db.commit SQLAlchemyError handling (D-06) |
| WR-08 | closed | attach_context AttributeError logged (D-07) |
| WR-09 | closed | CANONICAL_ALG_SYNONYMS + _matches word-boundary regex (D-08) |
| WR-10 | closed | _walk_json_for_alg_strings scans non-_ALG_KEYS strings (D-09) |
| WR-11 | closed | SCANNER_COVERAGE_STATUS parallel dict (D-10) |
| WR-12 | closed | is_qramm_model_stale() helper (D-11) |
| WR-13 | closed | TODO Phase 50 removed from quirk/compliance/__init__.py:3 (D-12) |

### Decision Compliance (D-01..D-12, D-14)

| Decision | Implementation Site | Status |
|----------|---------------------|--------|
| D-01 out-of-range ValueError | `quirk/qramm/scoring.py:30-31` | VERIFIED |
| D-02 discovery_factor log10 in [0.25, 1.0] | `quirk/qramm/evidence_bridge.py:38-44,107` | VERIFIED |
| D-03 vuln_pct=None -> "Indeterminate" | `quirk/qramm/scoring.py:77,85` | VERIFIED |
| D-04 >= 3.95 reachable | `quirk/qramm/scoring.py:82,86` | VERIFIED |
| D-05 datetime.date TZ-safe | `quirk/qramm/evidence_bridge.py` (fromisoformat use) | VERIFIED |
| D-06 SQLAlchemyError logged + rollback | `quirk/qramm/evidence_bridge.py:172-176` | VERIFIED |
| D-07 attach_context AttributeError logged | `quirk/qramm/evidence_bridge.py` logger.warning | VERIFIED |
| D-08 CANONICAL_ALG_SYNONYMS + _matches | `quirk/assessment/migration_advisor.py:12,21` | VERIFIED |
| D-09 _walk extension via _matches | `quirk/qramm/evidence_bridge.py:216-257` | VERIFIED |
| D-10 SCANNER_COVERAGE_STATUS | `quirk/qramm/compliance_map.py:20,53` | VERIFIED |
| D-11 is_qramm_model_stale | `quirk/qramm/model_meta.py:28` | VERIFIED |
| D-12 stale TODO removed | `quirk/compliance/__init__.py` (no match) | VERIFIED |
| D-14 do-not-touch (questions taxonomy, maturity scale, migration_planner stub) | Not modified | VERIFIED |

### Anti-Patterns Found

None. No TBD/FIXME/XXX markers introduced in Phase 74 files.

### Gaps Summary

No gaps. All 3 ROADMAP SCs satisfied, all 13 audit rows flipped with evidence, all D-01..D-12 + D-14 reflected in code, all 5 expected test files exist and pass (47/47), and `python -m compileall quirk/` exits 0.

---

_Verified: 2026-05-15_
_Verifier: Claude (gsd-verifier)_
