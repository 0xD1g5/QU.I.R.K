---
phase: 79-smime-ldap-discovery-scanner
plan: 03
subsystem: intelligence
tags: [smime, scoring, evidence, identity-trust, v4.10]
requires: [79-01]
provides:
  - SCORE_WEIGHTS entries: identity_smime_weak_signing_count, identity_smime_expired_count, identity_smime_weak_key_count
  - evidence counters: smime_weak_signing_count, smime_expired_count, smime_weak_key_count
  - identity_trust_impacts rows for the three SMIME findings
affects:
  - quirk/intelligence/scoring.py
  - quirk/intelligence/evidence.py
key-files:
  modified:
    - quirk/intelligence/scoring.py
    - quirk/intelligence/evidence.py
  created: []
decisions:
  - "Naming suffix `_count` (CONTEXT D-79-R6 / D-Area-4) — not renamed to `_ratio` to match SAML/DNSSEC siblings"
  - "All three impacts feed existing identity_trust subscore — NO new top-level subscore"
  - "tests/test_score_weights_invariant.py is intentionally left untouched (D-79-R3); Phase 83 CLEAN-01 owns the consolidated bump"
metrics:
  duration: ~5 min
  tasks: 2
  files_modified: 2
  lines_added: 31
  commit: 618e479
  completed: 2026-05-16
---

# Phase 79 Plan 03: SMIME Scoring Weights + Evidence Counters Summary

Wired SMIME findings into the scoring pipeline (SMIME-04) by adding three weight entries and three counter accessors so SMIME weaknesses now move the `identity_trust` subscore.

## What Was Built

### Task 1 — `quirk/intelligence/scoring.py`

Three additive edits, none altering existing rows:

1. **SCORE_WEIGHTS** — three new entries (after `identity_dnssec_weak_algo_ratio`):
   - `identity_smime_weak_signing_count: 2.0`
   - `identity_smime_expired_count: 2.0`
   - `identity_smime_weak_key_count: 2.0`
2. **Extractions** — three `_as_int(evidence.get(...))` lookups next to the existing `dnssec_weak_count` extraction:
   - `smime_weak_signing_count`, `smime_expired_count`, `smime_weak_key_count`
3. **identity_trust_impacts** — three new rows appended after the DNSSEC row:
   - `("Weak S/MIME signing", -_ratio(...) * w["identity_smime_weak_signing_count"])`
   - `("Expired S/MIME cert", -_ratio(...) * w["identity_smime_expired_count"])`
   - `("Weak S/MIME key", -_ratio(...) * w["identity_smime_weak_key_count"])`

### Task 2 — `quirk/intelligence/evidence.py`

Three additive edits modeled on the `saml_weak_signing_count` lifecycle:

1. **Declarations** — three zero-initialised counters next to `saml_weak_signing_count = 0`.
2. **SMIME accumulator branch** — `elif proto == "SMIME":` block inserted immediately after the DNSSEC branch:
   - Reads `cert_pubkey_alg`, `cert_pubkey_size`, `service_detail`, `cert_sig_alg`
   - Increments `smime_weak_signing_count` when either `cert_sig_alg` or `cert_pubkey_alg` matches `is_weak_cipher`
   - Increments `smime_weak_key_count` when RSA key size is a positive integer below 2048
   - Increments `smime_expired_count` when `service_detail` contains `expired=true` sentinel (Plan 79-02 contract)
3. **Export dict** — three entries appended next to `saml_weak_signing_count` / `dnssec_weak_algo_count` exports.

## Sum Delta Confirmation

Pre-Plan-79-03 `SCORE_WEIGHTS` sum: **261.0** (per `tests/test_score_weights_invariant.py:12`).
Post-Plan-79-03 `SCORE_WEIGHTS` sum: **267.0** (delta = +6.0 = 3 × 2.0).

Verified via:
```
python -c "from quirk.intelligence.scoring import SCORE_WEIGHTS; print(sum(SCORE_WEIGHTS.values()))"
# → 267.0
```

## Expected Red — `test_score_weights_invariant`

Per D-79-R3, the invariant test is **intentionally** red on this commit. Phase 83 CLEAN-01 owns the consolidated bump after Phase 80 also lands one weight.

Observed failure (matches plan prediction):
```
AssertionError: SCORE_WEIGHTS sum drifted from 261.0 to 267.0. Per D-04 this is intentional —
update this test ONLY if rebalance is documented.
assert 6.0 < 1e-09
```

This is the **expected** failure mode; all other tests remain unaffected because the change is purely additive (new keys, new counters, new impact rows — no rename, no value mutation).

## Verification Results

- `python -m compileall quirk/intelligence/` → exit 0
- `from quirk.intelligence.scoring import SCORE_WEIGHTS` — all three new keys present at value 2.0
- `grep -c 'smime_weak_signing_count|smime_expired_count|smime_weak_key_count' evidence.py` → 9 (3 names × 3 sites: decl, accumulator, export)
- `grep -c 'smime_weak_signing_count|smime_expired_count|smime_weak_key_count|identity_smime' scoring.py` → 9 (3 weights + 3 extractions + 3 impact rows)
- `tests/test_score_weights_invariant.py` → fails as planned (sum drift 261 → 267)

## Files Modified

| File | Lines Added |
|------|-------------|
| `quirk/intelligence/scoring.py` | +13 |
| `quirk/intelligence/evidence.py` | +18 |
| **Total** | **+31** |

## Commit

`618e479` — `feat(79-03): smime scoring weights + evidence counters (invariant temporarily red — Phase 83 owns bump)`

## Deviations from Plan

None — plan executed exactly as written. No deviations, no auto-fixes, no architectural decisions required.

## Self-Check: PASSED

- `quirk/intelligence/scoring.py` — FOUND, all three weights & impacts & extractions present
- `quirk/intelligence/evidence.py` — FOUND, all three counters declared / accumulated / exported
- Commit `618e479` — FOUND on main
- Expected red `tests/test_score_weights_invariant.py` — confirmed (delta +6.0 from 3× weight 2.0)
- Out-of-scope files (`smime_scanner.py`, `cbom/builder.py`, `test_score_weights_invariant.py`) — UNTOUCHED
