---
phase: 44-uat-debt-automation
plan: "03"
subsystem: tests
tags: [vault, live-integration, uat, skip-registry]
dependency_graph:
  requires: []
  provides: [test_vault_live_uat_30_01_five_findings, vault-skip-registry-entry]
  affects: [tests/test_vault_connector.py, tests/skip_registry.py]
tech_stack:
  added: []
  patterns: [live-infra-skipif, pytest.mark.slow, ALLOWED_SKIPS registration]
key_files:
  created: []
  modified:
    - tests/test_vault_connector.py
    - tests/skip_registry.py
decisions:
  - "Used vault_addr= kwarg (single string) per actual scan_vault_targets signature, not targets= list per plan interface note"
  - "Fixed 2 pre-existing skip_registry drift issues alongside the new vault entry to make test_skip_registry.py pass"
metrics:
  duration: "~8 minutes"
  completed: "2026-05-03"
  tasks_completed: 2
  files_modified: 2
---

# Phase 44 Plan 03: Vault Live Integration Test Summary

One-liner: Vault UAT-30-01 live integration test targeting port 28200 (vault-30 chaos lab, root token) with 5-finding assertion spec and skip_registry registration.

## What Was Built

### Task 1: Append live-infra section to tests/test_vault_connector.py

Added `test_vault_live_uat_30_01_five_findings` to the end of `tests/test_vault_connector.py`. The function:

- Guards with `@_pytest_uat.mark.skipif(not _os_uat.environ.get("QUIRK_VAULT_INTEGRATION"), ...)` and `@_pytest_uat.mark.slow`
- Calls `scan_vault_targets(vault_addr="http://localhost:28200", token="root")` targeting port 28200 (vault-30, image 1.17 — Pitfall 3 compliant)
- Asserts `len(results) >= 5`
- Asserts transit/rsa-2048-exportable finding with `severity == "MEDIUM"` (Finding 2)
- Asserts PKI finding with `severity == "HIGH"` (Finding 3: RSA-2048 root CA)
- Asserts auth/token finding with `severity == "HIGH"` (Finding 4)
- Asserts auth/userpass finding with `severity == "MEDIUM"` (Finding 5)
- Asserts `high_count >= 2` (matches `dar_vault_weak_count == 2` from expected_results_v4.md)

Skips cleanly without env var (SKIPPED via `pytest.mark.slow` + skipif gate).
All 22 existing mock tests remain unaffected.

**Commit:** e0815dc

**Operator command:**
```
cd quantum-chaos-enterprise-lab && ./lab.sh up vault
QUIRK_VAULT_INTEGRATION=1 python -m pytest tests/test_vault_connector.py::test_vault_live_uat_30_01_five_findings -v
```

### Task 2: Register new vault live_infra skip in tests/skip_registry.py

Added 1 new entry to `ALLOWED_SKIPS`:

```python
("test_vault_connector.py", 455, "live_infra", "Requires Vault-30 chaos lab (vault profile)"),
```

Line 455 is the exact line of the `@_pytest_uat.mark.skipif(` decorator in `tests/test_vault_connector.py`.

Also fixed 2 pre-existing drift issues that were causing `test_skip_registry.py` to fail:
- `test_cbom_motion_golden.py`: line 189 -> 195 (decorator moved, outside ±2 tolerance)
- `test_cbom_classifier_coverage.py:84`: new unregistered skip entry added

Net result: `test_skip_registry.py` now passes (was failing before this plan).

**Commit:** aca8d8d

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Used correct scan_vault_targets signature**
- **Found during:** Task 1
- **Issue:** Plan interface section showed `scan_vault_targets(targets=["http://localhost:28200"], ...)` but actual signature is `scan_vault_targets(vault_addr: str, ...)` (single string, not list)
- **Fix:** Called `scan_vault_targets(vault_addr="http://localhost:28200", token="root")` matching the actual function signature
- **Files modified:** tests/test_vault_connector.py
- **Commit:** e0815dc

**2. [Rule 3 - Blocking] Fixed pre-existing skip_registry drift**
- **Found during:** Task 2
- **Issue:** `test_skip_registry.py` was already failing with 2 unregistered skips before this plan. Adding only the vault entry would not make the meta-test pass.
- **Fix:** Updated `test_cbom_motion_golden.py` line from 189 to 195; added missing `test_cbom_classifier_coverage.py:84` live_infra entry
- **Files modified:** tests/skip_registry.py
- **Commit:** aca8d8d

## Key Notes

- **Port 28200 confirmed:** Pitfall 3 avoided — test targets vault-30 (port 28200, image 1.17), not the legacy storage-profile vault (port 20009, image 1.15)
- **Skipif decorator line:** Line 455 in `tests/test_vault_connector.py`
- **Phase 30 closure:** The STATE.md row closure (partial -> automated) happens in plan 44-06 as designed
- **Test suite improvement:** Pre-plan suite had 21 failures; post-plan suite has 20 failures (fixed skip_registry drift)

## Self-Check: PASSED

- tests/test_vault_connector.py exists and contains `def test_vault_live_uat_30_01_five_findings`
- tests/skip_registry.py contains `("test_vault_connector.py", 455, "live_infra", ...)`
- Commits e0815dc and aca8d8d present in git log
- `test_skip_registry.py` passes
- 22 existing mock tests pass unchanged
