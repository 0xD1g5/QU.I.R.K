---
phase: 80-windows-adcs-scanner
plan: 03
type: execute
status: complete
commit: 9ad9829
updated: 2026-05-16
files_modified:
  - quirk/intelligence/scoring.py
  - quirk/intelligence/evidence.py
requirements:
  - ADCS-04
---

# Phase 80 Plan 03: ADCS Scoring Weights + Evidence Counters Summary

One-liner: Wired four ADCS counters (weak_template / misconfig / weak_signing / coverage_gap) into evidence.py and scoring.py under `identity_trust`, each at weight 2.0, lifting `SCORE_WEIGHTS` sum from 267.0 → 275.0.

## What Was Built

### scoring.py (3 edits)
- **SCORE_WEIGHTS** gained 4 entries at 2.0 each, immediately after the SMIME triplet:
  - `identity_adcs_weak_template_count` (ESC1/2/3 templates)
  - `identity_adcs_misconfig_count` (ESC6 / general permissive flags)
  - `identity_adcs_weak_signing_count` (CA signing alg/key weakness)
  - `identity_adcs_coverage_gap_count` (ESC4/5/7/8 COVERAGE-GAP per CONTEXT D-Area-1)
- **identity_trust_impacts** gained 4 matching `-_ratio(...) * w[...]` rows, feeding the existing `identity_trust` subscore (NO new top-level subscore).
- **Four `_as_int` extractions** added immediately after the SMIME analog block, sourcing `evidence.get("adcs_*_count", 0)`.

### evidence.py (3 edits)
- **Declarations** — 4 zero-initialised counters after the SMIME triplet (~line 92).
- **Accumulator branch** — new `elif proto == "ADCS":` immediately after the SMIME branch, dispatching off `service_detail` substring tags per PATTERNS.md §4:

  | service_detail substring | counter incremented |
  |---|---|
  | `weak-signing-alg` OR `is_weak_cipher(cert_sig_alg)` true | `adcs_weak_signing_count` |
  | `esc1-` / `esc2-` / `esc3-` (any) | `adcs_weak_template_count` |
  | `esc6-` | `adcs_misconfig_count` |
  | starts with `coverage-gap|` | `adcs_coverage_gap_count` |
  | `adcs-unreachable|base=...` | (no counter — LOW finding via scan_error_category) |
- **Export dict** — 4 entries added after the SMIME exports (~line 363).

## Sum Delta Confirmation

- Pre-plan SCORE_WEIGHTS sum: **267.0** (post-Phase-79)
- Post-plan SCORE_WEIGHTS sum: **275.0** ✓ (267.0 + 4 × 2.0)
- Verified via: `python -c "from quirk.intelligence.scoring import SCORE_WEIGHTS; assert sum(SCORE_WEIGHTS.values()) == 275.0"` → exit 0
- Grep count for four ADCS counter names in evidence.py: **12** (4 names × 3 sites) ✓

## Invariant Test State (Deliberate RED)

`tests/test_score_weights_invariant.py` — **INTENTIONALLY RED on this commit** per D-80-R5:

```
FAILED test_score_weights_sum_invariant — assert abs(275.0 - 261.0) < 1e-9 fails (delta 14.0)
FAILED test_score_weights_count_invariant — assert 36 == 29 fails
```

Delta 14.0 = Phase 79 SMIME (+6.0) + Phase 80 ADCS (+8.0). Phase 83 CLEAN-01 owns the consolidated bump (sum→275.0, count→36).

**Not touched** in this plan: `tests/test_score_weights_invariant.py`, `quirk/scanner/adcs_scanner.py`, `quirk/cbom/builder.py`, `run_scan.py` (Plan 80-02 owns those).

## Verification Performed

- `python -m compileall quirk/intelligence/` → exit 0 (both scoring.py and evidence.py compiled clean)
- `python -c "...SCORE_WEIGHTS asserts..."` → exit 0 (all 4 weights present, sum == 275.0)
- `grep -cE 'adcs_weak_template_count|adcs_misconfig_count|adcs_weak_signing_count|adcs_coverage_gap_count' quirk/intelligence/evidence.py` → 12 (≥12 expected)
- `pytest tests/test_score_weights_invariant.py` → expected RED (sum 275.0, count 36)
- `tests/test_evidence.py` and `tests/test_scoring.py` — not present in repo; skipped.

## Deviations from Plan

None — plan executed exactly as written.

## Commit

- **SHA:** `9ad9829`
- **Message:** `feat(80-03): adcs scoring weights + evidence counters (4 entries; invariant red — Phase 83 owns bump)`
- **Files staged:** `quirk/intelligence/scoring.py`, `quirk/intelligence/evidence.py` (explicit paths; no `-A`)

## Self-Check: PASSED
- FOUND: quirk/intelligence/scoring.py (4 weights, 4 impacts, 4 extractions)
- FOUND: quirk/intelligence/evidence.py (4 declarations, 1 ADCS branch, 4 exports)
- FOUND: commit 9ad9829 in git log
- CONFIRMED: SCORE_WEIGHTS sum == 275.0
- CONFIRMED: invariant test red with delta 14.0 (per D-80-R5)
