---
status: issues_found
files_reviewed: 8
depth: deep
reviewed: 2026-05-08
findings:
  critical: 4
  warning: 13
  info: 0
  total: 17
---

# Code Review — QRAMM + Compliance + Assessment Subsystem

**Reviewed:** 2026-05-08
**Depth:** deep
**Files Reviewed:** 8
**Status:** issues_found

## Summary

Cross-file analysis of QRAMM core (scoring, evidence bridge, compliance map, questions, model meta) plus assessment helpers. The D-09 isolation invariant for `scoring.py` and `compliance_map.py` holds — both are stdlib/typing-only. Evidence bridge correctly avoids `risk_engine` imports.

However, **4 BLOCKER** correctness/security issues and **13 WARNING** quality issues were identified, including a profile-multiplier clamp that does not exist server-side, a fragile string-comparison `last_verified` lookup that breaks staleness math near year-end, an uncaught `int()` exception path in operator_context, and maturity thresholds that mis-classify a wide band of scores.

---

## BLOCKER Findings

### BL-01: Profile multiplier is not clamped server-side
**File:** `quirk/qramm/scoring.py:42-63`
**Issue:** Docstring states "multiplier: profile multiplier (typically 0.8-1.5; default 1.0)" but `compute_overall_score` accepts any float — negative, zero, 100, NaN — applies it directly. Client passing `multiplier=10.0` produces overall scores >40, breaking thresholds.
**Fix:** Clamp authoritatively server-side:
```python
_MIN_MULT, _MAX_MULT = 0.8, 1.5
multiplier = max(_MIN_MULT, min(_MAX_MULT, float(multiplier)))
```

### BL-02: Maturity threshold gap mis-classifies scores in [1.4, 1.5), [2.4, 2.5), [3.4, 3.5)
**File:** `quirk/qramm/scoring.py:66-84`
**Issue:** Docstring claims `1.0-1.4: Basic`, `1.5-2.4: Developing`, etc., but implementation uses strict `>=` cutoffs at 1.5 / 2.5 / 3.5 / 4.0. A score of 1.45 falls in an undocumented gap. Will produce unexplainable customer-facing maturity labels.
**Fix:** Update docstring to match (`1.0–<1.5`, etc.) OR change to closed bands. Add regression test for boundary values 1.49, 1.50, 2.49, 2.50, 3.49, 3.50, 3.99, 4.00.

### BL-03: `last_verified` lexicographic string comparison is fragile
**File:** `quirk/compliance/__init__.py:260`
**Issue:** `if e["last_verified"] < seen[key]["last_verified"]` uses string comparison to find oldest date. Works ONLY if every entry is strict ISO-8601. A typo like `"2026-5-5"` (missing zero pad) sorts before `"2026-05-05"` and corrupts staleness signal silently. Single malformed date poisons the report without raising.
**Fix:** Parse with `datetime.strptime(..., "%Y-%m-%d").date()` and compare as `date` objects. Raise on parse failure.

### BL-04: `int(years_raw)` accepts negative/zero years
**File:** `quirk/assessment/operator_context.py:38-42`
**Issue:** `int(years_raw) if years_raw else 7` accepts `-5` or `0` silently. `data_longevity_years=0` flows into scoring engine for "harvest now, decrypt later" weighting — zero/negative skews the entire roadmap. `except Exception` is over-broad.
**Fix:**
```python
try:
    years = int(years_raw) if years_raw else 7
    if years < 1:
        years = 7
except ValueError:
    years = 7
```

---

## WARNING Findings

- **WR-01:** Evidence bridge uses date-string equality vulnerable to TZ drift across UTC midnight (`evidence_bridge.py:43-52`).
- **WR-02:** `compute_practice_score` accepts out-of-range answers without validation — defense-in-depth (`scoring.py:20-28`).
- **WR-03:** `evidence_bridge` `synchronize_session="fetch"` is suboptimal; no idempotency marker for repeat invocation (`evidence_bridge.py:124`).
- **WR-04:** Practice 1.1 "Discovery" score ignores endpoint count entirely — only protocol diversity matters (`evidence_bridge.py:78-87`).
- **WR-05:** `vuln_pct` unbounded division — scan with zero classifiable algorithms scores **4 (Advanced)** despite zero evidence (`evidence_bridge.py:90-98`).
- **WR-06:** Maturity label `>= 4.0` unreachable at multiplier=1.0 due to floating-point noise (`scoring.py:76, 57`).
- **WR-07:** `evidence_bridge` does not handle `db.commit()` failure — partial-state risk (`evidence_bridge.py:127`).
- **WR-08:** `attach_context` swallows all exceptions including `AttributeError`; user-entered context silently dropped (`operator_context.py:78-94`).
- **WR-09:** `migration_advisor` has no severity weighting; substring matching produces false positives (`migration_advisor.py:14-76`).
- **WR-10:** `_walk_json_for_alg_strings` skips non-`_ALG_KEYS` strings — schema drift on scanner JSON silently drops evidence (`evidence_bridge.py:188-196`).
- **WR-11:** `compliance_map.py` weight 0.0 is allowed; falsy in defaults — distinguish "not yet covered" vs "covered, score 0" (`compliance_map.py:35-40`).
- **WR-12:** `model_meta.py` lacks `is_qramm_model_stale(today=None)` helper; CI gate and CLI must re-implement date math + env override independently (`model_meta.py:1-23`).
- **WR-13:** TODO Phase 50 comment left in production module header (`compliance/__init__.py:3`).

---

## Cross-File / Invariant Checks

- **D-09 isolation invariant — PASS**: `scoring.py`, `compliance_map.py`, `questions.py`, `model_meta.py` import only stdlib + typing. `evidence_bridge.py` imports `quirk.cbom.classifier` and `quirk.models` but **not** `quirk.engine.risk_engine` or any scanner module.
- **Phase 49 schema gate — PASS**: every `COMPLIANCE_MAP` entry carries `framework`, `control`, `version`, `last_verified`, `source_url`.
- **Phase 52 zero-utcnow gate — PASS for these files**: no `datetime.utcnow()` calls.
- **120-question completeness — PASS**: `QRAMM_QUESTIONS` has exactly 120 entries spanning Q1–Q120.
- **Server-side multiplier clamp — FAIL** (BL-01).

---

_Reviewed: 2026-05-08_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
