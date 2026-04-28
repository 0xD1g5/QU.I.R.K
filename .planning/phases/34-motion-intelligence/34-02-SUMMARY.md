---
phase: 34
plan: 02
status: complete
updated: 2026-04-28
---

# Plan 34-02 Summary — Motion intelligence GREEN

## Files modified
- `quirk/intelligence/evidence.py` — added 6 motion counters, broker/email elif branches, 11 dict keys
- `quirk/intelligence/scoring.py` — added 5 motion weights, motion_ profile multiplier, motion_impacts block, data_in_motion subscore
- `tests/test_intelligence_scoring.py` — updated subscore set assertion (5 → 6 keys)
- `tests/test_dar_vault_scoring.py` — updated subscore set assertion (5 → 6 keys)

## Test results

### Motion suite (target: all 15 GREEN)
```
PYTHONPATH=. pytest tests/test_motion_scoring.py -q
...............                                                          [100%]
15 passed in 0.02s
```

### Adjacent intelligence + DAR tests (after subscore-set updates)
```
PYTHONPATH=. pytest tests/test_intelligence_scoring.py tests/test_intelligence_evidence.py \
                    tests/test_dar_storage_scoring.py tests/test_dar_k8s_scoring.py \
                    tests/test_dar_vault_scoring.py -q
41 passed in 0.16s
```

### Full suite
```
PYTHONPATH=. pytest tests/ -q
6 failed, 602 passed, 6 skipped
```

The 6 remaining failures pre-exist Phase 34 (confirmed via `git stash` round-trip):
- `test_cli_correctness::test_version_consistency`
- `test_cli_correctness::test_no_quirk_scan_references`
- `test_dashboard_wiring::test_deps_default_db_path`
- `test_identity_surface::test_issue3_scan_window_returns_all_identity_protocols`
- `test_packaging::test_version_is_4_2_0`
- `test_v41_gap_closure::test_pyproject_version_field_is_4_1_0`

These are stale version-pinned tests from earlier milestones — unrelated to motion intelligence.

## Compileall
```
python -m compileall quirk/  → exit 0
```

## Acceptance grep summary
- `grep -c '"motion_' quirk/intelligence/evidence.py` → **11** (6 counts + 5 ratios)
- `grep -c 'motion_' quirk/intelligence/scoring.py` → **25** (≥20 required)
- `grep -c '"data_in_motion"' quirk/intelligence/scoring.py` → **1**
- `grep -c '"motion_": ' quirk/intelligence/scoring.py` → **3** (one per profile)
- 5 existing subscore keys preserved unchanged → **5/5**

## Deviations from plan

1. **Pre-existing tests required updates.** The plan asserted "Existing scoring/evidence tests remain GREEN" but two tests (`test_intelligence_scoring.py:32` and `test_dar_vault_scoring.py:71`) hard-pinned the old 5-subscore set as `==` equality. Phase 34 D-04 explicitly adds `data_in_motion` as a 6th subscore. Both tests updated to expect the 6-key set; the vault test docstring updated to note the Phase 34 contract change. No other test logic changed.

2. **Acceptance criterion `grep -c motion_score ≥ 4`.** The literal token `motion_score` appears 3 times (definition + total_score + subscores entry). The fourth wire site uses `motion_drivers` (the impact-list output), not `motion_score`. Behavior matches the plan; the criterion's count was slightly off. All other acceptance criteria satisfied.

## Success criteria mapped
- **SC-1** Plaintext-broker scan lowers data_in_motion + total score → verified by `test_motion_subscore_lowers_with_findings`
- **SC-2** 6 motion_ counter keys present → verified by `test_motion_keys_present_in_summary`
- **SC-3** 5 motion_*_ratio entries + multiplier in 3 profiles → `test_score_weights_motion_values`, `test_profile_multipliers_motion`
- **SC-4** data_in_motion is the 6th subscores key → `test_subscores_includes_data_in_motion`

## Next
Plan 34-03: phase completion docs (UAT-SERIES.md update + Obsidian phase note + sync + commit).
