---
phase: 34
plan: 01
status: complete
updated: 2026-04-28
---

# Plan 34-01 Summary — RED test scaffold

## Files created
- `tests/test_motion_scoring.py` (220 lines, 15 test functions)

## Tests collected
`pytest tests/test_motion_scoring.py --collect-only -q` reports **15 items** — exactly matching the `def test_*` count in the action block:

1. test_motion_keys_present_in_summary
2. test_motion_broker_plaintext_count_kafka
3. test_motion_broker_plaintext_count_amqp_and_redis
4. test_motion_broker_weak_tls_count
5. test_motion_broker_weak_cipher_count
6. test_motion_email_starttls_missing_count
7. test_motion_email_plaintext_count
8. test_motion_email_weak_cipher_count
9. test_score_weights_motion_values
10. test_profile_multipliers_motion
11. test_subscores_includes_data_in_motion
12. test_motion_subscore_lowers_with_findings
13. test_top_drivers_surfaces_motion
14. test_legacy_evidence_no_motion_keys_full_credit
15. test_profile_strict_increases_motion_penalty

## RED state confirmed
`PYTHONPATH=. pytest tests/test_motion_scoring.py -q` → **15 failed, 0 passed**.

Failure modes observed (all are missing-implementation signals, not collection errors):
- `KeyError: 'motion_email_plaintext_ratio'` on `SCORE_WEIGHTS` lookup
- `KeyError: 'motion_'` on `PROFILE_MULTIPLIERS["strict"]["motion_"]`
- `KeyError: 'data_in_motion'` on `subscores`
- `AssertionError: missing key motion_email_starttls_missing_count` on summary keys

Zero `ImportError` / `SyntaxError` when invoked with the project's normal pytest runner (`PYTHONPATH=.`).

## Acceptance verified
- [x] File exists
- [x] `python -m compileall` exits 0
- [x] 15 collectable items
- [x] RED state (failures, not collection errors)
- [x] Contains `from quirk.intelligence.evidence import build_evidence_summary`
- [x] Contains `from quirk.intelligence.scoring import`
- [x] Contains `def _ep(protocol: str`
- [x] No `== 25` or `== 100` substrings (relative-only assertions)
- [x] 57 occurrences of `motion_` (≥30 sanity)

## Deviations
None. File written verbatim from the action block.

## Next
Plan 34-02 (Wave 2) lands the implementation in `quirk/intelligence/evidence.py` and `quirk/intelligence/scoring.py` to turn all 15 tests GREEN.
