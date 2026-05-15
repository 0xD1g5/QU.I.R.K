---
phase: 73-cbom-intel-reports-warnings
plan: 03
subsystem: intelligence + reports + cbom
tags: [intel-03, score-weights, roadmap, executive-guard, tls-kex, confidence-clamp, audit-cluster-closure]
requires:
  - phase-60 (SCORE-04/CR-06 cap-sharing rationale cited in SCORE_WEIGHTS docstring)
provides:
  - SCORE_WEIGHTS sum=261.0 invariant (documented + CI-gated)
  - _why double-period normalization (rstrip)
  - _add_candidate merge-rule docstring
  - _build_interpretation score guard + _INTERPRETATION_UNAVAILABLE fallback
  - _KEX_MAP["RSA"] = "RSA-kex" relabel
  - confidence.py inline clamp + fail-loud + WARN on unknown override keys
affects:
  - tests CI gate on SCORE_WEIGHTS sum drift
  - downstream CBOM consumers reading KEX role labels
  - JSON output factor_breakdown weights (clamped)
key-files:
  created:
    - tests/test_score_weights_invariant.py
    - tests/test_executive_score_guard.py
    - tests/test_tls_kex_label.py
  modified:
    - quirk/intelligence/scoring.py
    - quirk/intelligence/roadmap.py
    - quirk/reports/executive.py
    - quirk/cbom/builder.py
    - quirk/intelligence/confidence.py
    - tests/test_intelligence_roadmap.py
    - tests/test_intelligence_confidence.py
    - .planning/audit-2026-05-08/AUDIT-TASKS.md
decisions:
  - D-04 / WR-06: SCORE_WEIGHTS invariant is documentation + CI-gate only — NO value changes (D-14 honored)
  - D-05 / WR-07: hint.rstrip('.') before re-appending the trailing period
  - D-06 / WR-08: docstring-only fix on _add_candidate (RESEARCH C-6 — module is not a generator; "mutation-after-yield" was figurative)
  - D-07 / WR-09: module-level _INTERPRETATION_UNAVAILABLE constant + isinstance(dict) guard + .get('score') / .get('rating', 'Unknown')
  - D-08 / WR-12: single-line _KEX_MAP["RSA"] = "RSA-kex" relabel at cbom/builder.py:142 (RESEARCH C-1/C-4 path (a) — NOT evidence.py, NOT dual-emit)
  - D-09 / WR-13: inline clamp + fail-loud + WARN at confidence.py:46-49 (RESEARCH C-5 — no apply_weight_overrides function exists)
metrics:
  duration: ~25 minutes
  completed: 2026-05-15
  tasks_completed: 6/6
  tests_added: 25+ (2 invariant + 6 roadmap + 5 executive + 10 KEX + 7 confidence)
  files_created: 3
  files_modified: 8
---

# Phase 73 Plan 03: INTEL-03 SCORE_WEIGHTS / Roadmap / Executive / TLS KEX / Confidence Summary

Six surgical CBOM / intelligence / reports hardening fixes plus one invariant test, closing WR-06, WR-07, WR-08, WR-09, WR-12, WR-13 and completing the full 13-row `cbom-intel-reports/WR-*` cluster under Phase 73.

## One-liner

INTEL-03 closes six independent WR rows: SCORE_WEIGHTS sum=261.0 documented and CI-gated, roadmap `_why` no longer emits `..`, `_add_candidate` merge rule documented, executive `_build_interpretation` guards against malformed score dicts via `_INTERPRETATION_UNAVAILABLE` fallback, TLS 1.2 non-PFS RSA suites emit `RSA-kex` (disambiguating from cert-signature `RSA-auth`), and user-supplied confidence weight overrides are clamped to `[0.0, 1.0]` with fail-loud `ValueError` on non-numeric and a WARNING on unknown keys.

## Tasks & Commits

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | SCORE_WEIGHTS docstring + invariant test (D-04 / WR-06) | `d5a1fa5` | quirk/intelligence/scoring.py, tests/test_score_weights_invariant.py |
| 2 | Roadmap `_why` double-period + `_add_candidate` merge-rule docstring (D-05, D-06; WR-07, WR-08) | `9d2b01d` | quirk/intelligence/roadmap.py, tests/test_intelligence_roadmap.py |
| 3 | Executive `_build_interpretation` score guard (D-07 / WR-09) | `791a675` | quirk/reports/executive.py, tests/test_executive_score_guard.py |
| 4 | `_KEX_MAP` RSA-kex relabel (D-08 / WR-12) | `f75c8c5` | quirk/cbom/builder.py, tests/test_tls_kex_label.py |
| 5 | Confidence override clamp + fail-loud + WARN (D-09 / WR-13) | `c4b3645` | quirk/intelligence/confidence.py, tests/test_intelligence_confidence.py |
| 6 | Audit rows WR-06/07/08/09/12/13 → Phase 73 [x] closed | `268b2e4` | .planning/audit-2026-05-08/AUDIT-TASKS.md |

## What Was Built

### Task 1 — SCORE_WEIGHTS invariant docstring + CI gate (D-04 / WR-06)

- Added a multi-line comment block above `SCORE_WEIGHTS` in `quirk/intelligence/scoring.py` naming the invariant: "absolute per-ratio coefficients, NOT probabilities, NOT a normalized PMF. Their sum is 261.0 BY DESIGN." Cross-referenced Phase 60 SCORE-04 / CR-06 cap-sharing rationale.
- Created `tests/test_score_weights_invariant.py` with two assertions: `abs(sum - 261.0) < 1e-9` (sum invariant) and `len == 29` (count invariant). Future contributors who add / remove / modify a weight value see the CI gate fail.
- **No SCORE_WEIGHTS values changed** (D-14 honored). All existing scoring + clamp tests pass — zero customer-facing scorecard movement.

### Task 2 — Roadmap `_why` rstrip + `_add_candidate` docstring (D-05, D-06; WR-07, WR-08)

- `_why` now returns `f"{base} Driver: {hint.rstrip('.')}."` — a hint already ending in `.` no longer produces a `..` artifact. Empty-hint early-return preserved.
- `_add_candidate` gained a multi-line docstring explaining the previously-undocumented merge rule: duplicate title → compare `(_PHASE_ORDER[phase], int(_priority), title)` tuples → lexicographically-lower tuple wins (strict `<`, so equal tuples preserve the original). Cites WR-08 closure.
- RESEARCH C-6: the CONTEXT phrasing "mutation-after-yield" was figurative — `roadmap.py` is not a generator. The real undocumented contract is the merge rule, which is what was documented.
- 6 new tests in `tests/test_intelligence_roadmap.py`: 3 `_why` cases (period-terminated hint, no-period hint, empty hint) + 3 `_add_candidate` cases (lower wins, higher loses, equal preserves original).

### Task 3 — Executive `_build_interpretation` score guard (D-07 / WR-09)

- Added module-level constant `_INTERPRETATION_UNAVAILABLE = "Score data unavailable for this run."` to `quirk/reports/executive.py`.
- Replaced the direct `score['score']` subscript at line 30 with a guard: `score_val = score.get("score") if isinstance(score, dict) else None; if score_val is None: return {"bullets": [_INTERPRETATION_UNAVAILABLE]}`.
- Replaced `score['rating']` with `score.get("rating", "Unknown")` (guard guarantees `score` is a dict at this point).
- 5 new tests in `tests/test_executive_score_guard.py`: full dict (happy path), `None`, empty dict, non-dict string, missing rating key.

### Task 4 — `_KEX_MAP["RSA"] = "RSA-kex"` relabel (D-08 / WR-12)

- Single-token edit at `quirk/cbom/builder.py:142`: `_KEX_MAP["RSA"]` now emits `"RSA-kex"` instead of bare `"RSA"`, disambiguating the KEX role from the cert-signature `RSA-auth` label downstream.
- RESEARCH C-1: function lives in `quirk/cbom/builder.py`, NOT `evidence.py` as CONTEXT D-08 invited researcher to confirm.
- RESEARCH C-4 path (a) chosen: minimal-diff relabel over the dual-emit alternative — no auth-loop logic changes (D-14 honored).
- TLS 1.3 path unaffected (skips `_KEX_MAP` per `cbom/builder.py:192`).
- New `tests/test_tls_kex_label.py`: parametrized over 8 non-PFS RSA TLS 1.2 suites (`TLS_RSA_WITH_AES_128_CBC_SHA`, `..._256_CBC_SHA`, `..._128_CBC_SHA256`, `..._256_CBC_SHA256`, `..._128_GCM_SHA256`, `..._256_GCM_SHA384`, `..._NULL_SHA`, `..._NULL_MD5`) asserting `"RSA-kex"` present and bare `"RSA"` absent + ECDHE-RSA negative test (still X25519) + TLS 1.3 path-unaffected test.

### Task 5 — Confidence override clamp + fail-loud + WARN (D-09 / WR-13)

- Added `import logging`, `_LOGGER = logging.getLogger(__name__)`, and `_KNOWN_CONFIDENCE_KEYS = frozenset(CONFIDENCE_WEIGHTS.keys())` to module top.
- Replaced the `compute_confidence` override block at lines 46-49: `float()` coercion with `(TypeError, ValueError)` re-raised as `ValueError(f"Confidence override {key!r} must be numeric in [0.0, 1.0], got {value!r}")`; clamp via `max(0.0, min(1.0, num))`; `_LOGGER.warning(...)` for unknown override keys (forward-compat per CONTEXT D-09 — NOT a hard error).
- RESEARCH C-5: no `apply_weight_overrides` function exists; applied inline at the existing override site as the locked path.
- 7 new tests in `tests/test_intelligence_confidence.py`: below-zero clamp, above-one clamp, in-range pass-through, non-numeric raises (`"abc"`), `None` raises, list raises, unknown key logs WARNING + accepts.

### Task 6 — Audit ledger flips

Six rows in `.planning/audit-2026-05-08/AUDIT-TASKS.md` flipped to `Phase 73 | [x] closed` with per-row evidence summaries citing the implementing plan/decision and the test files asserting closure. Combined with plans 73-01 (WR-01/02/14) and 73-02 (WR-03/04/10/11), all 13 open `cbom-intel-reports/WR-*` rows are now closed under Phase 73 (WR-05 was previously closed by Phase 60).

## Deviations from Plan

None — plan executed exactly as written. RESEARCH discrepancies (C-1, C-4, C-5, C-6) were already adjudicated in the PLAN.md action sections, so the plan's locked behavior aligned with code reality from the start.

## Verification

```
python -m compileall quirk/intelligence/scoring.py quirk/intelligence/roadmap.py \
    quirk/reports/executive.py quirk/cbom/builder.py quirk/intelligence/confidence.py
# → all 5 files compile clean

pytest tests/test_score_weights_invariant.py tests/test_intelligence_roadmap.py \
    tests/test_executive_score_guard.py tests/test_tls_kex_label.py \
    tests/test_intelligence_confidence.py tests/test_intelligence_scoring.py \
    tests/test_score_clamp_property.py tests/test_cbom_writer.py -x
# → 57 passed in 0.19s

grep -cE "cbom-intel-reports/WR-(06|07|08|09|12|13).*Phase 73.*\[x\] closed" \
    .planning/audit-2026-05-08/AUDIT-TASKS.md
# → 6

grep -cE "cbom-intel-reports/WR-.*\[ \] open" .planning/audit-2026-05-08/AUDIT-TASKS.md
# → 0  (full INTEL WR cluster closed under Phase 73)
```

## Cluster-Level Note

With plan 73-03 complete, **all 13 open `cbom-intel-reports/WR-*` warning rows from the 2026-05-08 audit are closed under Phase 73**:

- Phase 73-01 (INTEL-01): WR-01, WR-02, WR-14 (PDF render hardening)
- Phase 73-02 (INTEL-02): WR-03, WR-04, WR-10, WR-11 (weak-crypto helper unification)
- Phase 73-03 (INTEL-03): WR-06, WR-07, WR-08, WR-09, WR-12, WR-13 (this plan)
- Already closed: WR-05 (Phase 60 SCORE-04)

## Self-Check: PASSED

- File checks (created):
  - tests/test_score_weights_invariant.py — FOUND
  - tests/test_executive_score_guard.py — FOUND
  - tests/test_tls_kex_label.py — FOUND
- File checks (modified):
  - quirk/intelligence/scoring.py — FOUND (comment block above SCORE_WEIGHTS)
  - quirk/intelligence/roadmap.py — FOUND (rstrip + docstring)
  - quirk/reports/executive.py — FOUND (constant + guard)
  - quirk/cbom/builder.py — FOUND ("RSA-kex" entry)
  - quirk/intelligence/confidence.py — FOUND (clamp + WARN block)
  - tests/test_intelligence_roadmap.py — FOUND (6 new tests)
  - tests/test_intelligence_confidence.py — FOUND (7 new tests)
  - .planning/audit-2026-05-08/AUDIT-TASKS.md — FOUND (6 rows flipped)
- Commit checks: d5a1fa5, 9d2b01d, 791a675, f75c8c5, c4b3645, 268b2e4 — all FOUND in git log.
- Acceptance grep checks: 6 rows flipped to "Phase 73 [x] closed"; 0 open cbom-intel-reports/WR-* rows remain.
