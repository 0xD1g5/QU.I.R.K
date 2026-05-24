---
phase: 99-per-finding-context-code-signing-expiry
plan: "01"
subsystem: reports/content_model
tags: [content-model, algo-impact-map, remediation-catalog, codesign, ctx-01, ctx-02, tdd]
requires: []
provides:
  - ALGO_IMPACT_MAP 3-tuple (quantum_risk_sentence at index [2])
  - REMEDIATION_CATALOG (weakness-specific remediation strings)
  - FALLBACK_QUANTUM_RISK constant
  - CODESIGN_EXPIRY / CODESIGN_APPROACHING_EXPIRY crypto-class keys
  - _classify_finding and assert_congruent in __all__
affects:
  - quirk/reports/content_model.py
  - tests/test_content_model_phase99.py
  - tests/test_exec_content_model.py
tech-stack:
  added: []
  patterns:
    - 3-tuple extension of existing static map (ALGO_IMPACT_MAP)
    - Separate REMEDIATION_CATALOG mirroring map key set
    - TDD RED/GREEN cycle for content-model changes
key-files:
  created:
    - tests/test_content_model_phase99.py
  modified:
    - quirk/reports/content_model.py
    - tests/test_exec_content_model.py
decisions:
  - "CODESIGN_EXPIRY/CODESIGN_APPROACHING_EXPIRY placed at top of _ALGO_KEYWORDS to prevent false-match on 'DES' substring"
  - "ALGO_IMPACT_MAP[2] (quantum_risk_sentence) uses verbatim locked strings from 99-UI-SPEC.md"
  - "REMEDIATION_CATALOG uses plain str values (not tuples) matching PATTERNS.md recommendation"
  - "_build_top_risks fixed with 3-value unpack (risk_label, impact_sentence, _)"
metrics:
  duration: "~15 minutes"
  completed: "2026-05-24"
  tasks_completed: 2
  files_modified: 3
  files_created: 1
requirements: [CTX-01, CTX-02]
---

# Phase 99 Plan 01: Content Model Foundation — ALGO_IMPACT_MAP 3-Tuple + REMEDIATION_CATALOG Summary

**One-liner:** ALGO_IMPACT_MAP extended to 3-tuple (risk_label, impact_sentence, quantum_risk_sentence) with REMEDIATION_CATALOG and CODESIGN_EXPIRY keys as the single source of per-finding quantum-risk context and remediation copy.

## What Was Built

### Task 1: Extend ALGO_IMPACT_MAP + Add REMEDIATION_CATALOG (commit f4dce7d)

Extended `quirk/reports/content_model.py` with the full Phase 99 D-01/D-04 content model foundation:

- **ALGO_IMPACT_MAP** type annotation changed from `Dict[str, tuple[str, str]]` to `Dict[str, tuple[str, str, str]]`; every existing entry gained a third element `quantum_risk_sentence` using verbatim locked strings from 99-UI-SPEC.md §Copywriting Contract
- **Two new keys** added: `CODESIGN_EXPIRY` and `CODESIGN_APPROACHING_EXPIRY` — each a 3-tuple with locked quantum_risk sentences from the UI-SPEC expiry rows
- **REMEDIATION_CATALOG** — new `Dict[str, str]` with identical key set to ALGO_IMPACT_MAP, populated verbatim from 99-UI-SPEC.md §Per-Finding Remediation Catalog (D-04)
- **FALLBACK_QUANTUM_RISK** — module-level constant with the default-fallback string from 99-UI-SPEC.md §Field Name Contract
- **`__all__`** updated to export `REMEDIATION_CATALOG`, `FALLBACK_QUANTUM_RISK`, `_classify_finding`, `assert_congruent`
- Module docstring updated to document Phase 99 D-01/D-04 additions

### Task 2: Fix Unpacks + Phase 99 Tests — TDD RED→GREEN (commits 845a232, 8cf6529)

**RED commit (845a232):** Created `tests/test_content_model_phase99.py` with 6 failing tests covering:
- `test_quantum_risk_field_populated` — ALGO_IMPACT_MAP["RSA"][2] is non-empty str
- `test_remediation_catalog_key_parity` — catalog key set == ALGO_IMPACT_MAP key set
- `test_codesign_keys_present` — both codesign keys in both maps as 3-tuples
- `test_classify_finding_matches_codesign_via_check_id` — check_id route (A1)
- `test_build_top_risks_unpacks_three_tuple` — no ValueError on 3-tuple unpack
- `test_fallback_quantum_risk_is_nonempty` — FALLBACK_QUANTUM_RISK defined

**GREEN commit (8cf6529):** Three fixes:
1. `_build_top_risks` (content_model.py line 514): `risk_label, impact_sentence, _ = ALGO_IMPACT_MAP[crypto_class]`
2. `tests/test_exec_content_model.py` line 115: `_, expected_sentence, _ = ALGO_IMPACT_MAP["RSA"]`
3. `_ALGO_KEYWORDS` ordering: moved `CODESIGN_APPROACHING_EXPIRY` and `CODESIGN_EXPIRY` to the top of the tuple — the keyword "DES" is a substring of "CODESIGN_EXPIRY", so the codesign keys must precede "DES" to avoid false first-match

All 12 tests pass (6 new + 6 existing).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed _ALGO_KEYWORDS ordering to prevent DES false-match on codesign check_id**
- **Found during:** Task 2 RED phase — `test_classify_finding_matches_codesign_via_check_id` failed with `'DES'` returned instead of `'CODESIGN_EXPIRY'`
- **Issue:** The keyword "DES" is a substring of "CODESIGN_EXPIRY". With codesign keys appended after "DES" in `_ALGO_KEYWORDS`, `_classify_finding` matched "DES" first via the search_text substring check
- **Fix:** Moved `CODESIGN_APPROACHING_EXPIRY` and `CODESIGN_EXPIRY` to the top of `_ALGO_KEYWORDS` (with doc comment explaining the ordering requirement)
- **Files modified:** `quirk/reports/content_model.py` (_ALGO_KEYWORDS tuple)
- **Commit:** 8cf6529

## Verification

- `python -m compileall quirk/reports/content_model.py` — PASS
- `python -m pytest tests/test_content_model_phase99.py tests/test_exec_content_model.py -x -q` — 12 passed
- ALGO_IMPACT_MAP and REMEDIATION_CATALOG key sets identical; both contain the two codesign keys
- `grep -rn '= ALGO_IMPACT_MAP\[' quirk/ tests/` returns no 2-value unpack survivors

## Known Stubs

None — all copy is populated verbatim from 99-UI-SPEC.md locked strings.

## Threat Flags

None — Plan 99-01 modifies only static compile-time constants (author-locked copy from UI-SPEC); no new network endpoints, auth paths, file access patterns, or schema changes.

## Self-Check: PASSED

- `quirk/reports/content_model.py` — exists and compiles ✓
- `tests/test_content_model_phase99.py` — exists, 12 tests pass ✓
- `tests/test_exec_content_model.py` — updated, existing tests pass ✓
- Commits f4dce7d, 845a232, 8cf6529 — all present in git log ✓
