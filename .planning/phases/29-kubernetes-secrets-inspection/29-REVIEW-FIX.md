---
phase: 29-kubernetes-secrets-inspection
fixed_date: 2026-04-26
fix_scope: critical_warning
findings_in_scope: 6
fixed: 5
skipped: 1
iteration: 1
status: partial
---

# Phase 29: Code Review Fix Report

**Fixed at:** 2026-04-26
**Source review:** .planning/phases/29-kubernetes-secrets-inspection/29-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 6
- Fixed: 5
- Skipped: 1

## Fixed Issues

### WR-01: Dead condition `"rbac-403" in sd` removed from evidence counter

**Files modified:** `quirk/intelligence/evidence.py`
**Commit:** cd436b8
**Applied fix:** Removed the `or "rbac-403" in sd` condition from the `elif` branch in the KUBERNETES protocol block. Also updated the comment to accurately describe the conditions (removed reference to "synthetic-fixture cases" which had no basis in the test suite).

---

### WR-03: UAT-29-03 pass criteria corrected to reflect actual connector output

**Files modified:** `docs/UAT-SERIES.md`, `labs/kubernetes/expected_results.md`
**Commits:** 54ae888, f117371
**Applied fix:**
- `docs/UAT-SERIES.md` lines 1867/1874: Replaced `service_detail=rbac-403` references with the accurate connector output — `scan_error=insufficient-rbac-privileges` with remediation text in `service_detail`.
- `labs/kubernetes/expected_results.md` K8S-03 table: Updated the inaccessible findings table to show `scan_error` field values instead of the incorrect `service_detail=rbac-403` entry.

---

### WR-04: GKE cluster YAML `project` key removed from docs

**Files modified:** `labs/kubernetes/expected_results.md`
**Commit:** ab635c5
**Applied fix:** Removed the per-cluster `project` key from the GKE YAML config example. Added a note explaining that only the top-level `gcp_project_id` parameter is used and that multi-project scanning requires separate runs. Also corrected the `dar_k8s_inaccessible_count` evidence description to replace the inaccurate `rbac-403` reference with `scan_error=insufficient-rbac-privileges`.

---

### WR-05: AKS cluster YAML `subscription_id` key removed from docs

**Files modified:** `labs/kubernetes/expected_results.md`
**Commit:** 3e63fa6
**Applied fix:** Removed the per-cluster `subscription_id` key from the AKS YAML config example. Added a note explaining that only the top-level `azure_subscription_id` parameter is used and that multi-subscription scanning requires separate runs.

---

### WR-06: Fragile driver-extraction logic fixed in test

**Files modified:** `tests/test_dar_k8s_scoring.py`
**Commit:** 7fd92ea
**Applied fix:** Replaced the `d[0] if isinstance(d, (list, tuple)) else str(d)` pattern with `d.get("reason", "") if isinstance(d, dict) else str(d)`. This correctly extracts the `reason` field from the dict-structured driver entries that `scoring.py` returns, eliminating the brittle reliance on `str(d)` dict repr containing the target substring.

---

## Skipped Issues

### WR-02: UAT-SERIES.md `Gate Status` line references v4.2 not v4.3

**File:** `docs/UAT-SERIES.md:6,94`
**Reason:** Code already matches the fix. When the source file was read, both lines were already at v4.3:
- Line 6: `"release gate for QU.I.R.K. v4.3"` (already v4.3)
- Line 94: `quirk 4.3.0` or `QU.I.R.K. v4.3.0` (already 4.3.0)

The `**Last Updated:**` note on line 4 explicitly states "Gate Status bumped to v4.3; UAT-1-02 version string updated to v4.3.0", indicating this fix was already applied during the phase-29 documentation commit.
**Original issue:** Version strings still referencing v4.2 would cause live testers to incorrectly mark UAT-1-02 as FAIL.

---

Next step: /gsd-verify-work

---

_Fixed: 2026-04-26_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
