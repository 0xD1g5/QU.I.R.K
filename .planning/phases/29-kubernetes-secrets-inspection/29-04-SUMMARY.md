---
phase: 29-kubernetes-secrets-inspection
plan: "04"
subsystem: kubernetes
tags: [kubernetes, k8s, gap-closure, evidence, aks, rbac, secrets, dar]

requires:
  - phase: 29-01
    provides: k8s_connector.py with scan_k8s_targets, _enumerate_secret_types, _emit_inaccessible_finding
  - phase: 29-02
    provides: evidence.py KUBERNETES elif with dar_k8s_* counters
  - phase: 29-03
    provides: test_dar_k8s_scoring.py baseline tests (12 passing)

provides:
  - CR-01 fix: evidence.py KUBERNETES elif now reads scan_error field to count RBAC 403 as inaccessible
  - CR-02 fix: AKS DefaultAzureCredential failure emits per-cluster inaccessible findings
  - CR-03 fix: _enumerate_secret_types emits service_detail='secret-types-summary' matching docs/UAT-SERIES.md
  - Two new AKS regression tests covering per-cluster and empty-list credential-failure paths
  - False-green tests in test_dar_k8s_scoring.py replaced with live-shape fixtures

affects:
  - phase: 29-verification
  - intelligence evidence pipeline (dar_k8s_inaccessible_count now correctly fires on RBAC 403)
  - UAT-29-01/02/03 live cluster scan assertions

tech-stack:
  added: []
  patterns:
    - "getattr(ep, 'scan_error', '') pattern for defensive field access in KUBERNETES elif"
    - "patch('azure.identity.DefaultAzureCredential', create=True) for SDK-absent AKS test isolation"
    - "Per-cluster inaccessible finding loop in except block (K8S-03 invariant pattern)"

key-files:
  created: []
  modified:
    - quirk/intelligence/evidence.py
    - quirk/scanner/k8s_connector.py
    - tests/test_dar_k8s_scoring.py
    - tests/test_k8s_connector.py

key-decisions:
  - "CR-01: Add scan_err field check alongside 'rbac-403' in sd substring — backward-compat preserved for synthetic fixtures while live shape now counts correctly"
  - "CR-02: Emit findings inside the except block (not after) — credential=None guard stays separate so the happy path (credential not None) is untouched"
  - "CR-03: Align code to docs (change connector, not docs) — UAT-SERIES.md and expected_results.md already document 'secret-types-summary' as the canonical value"

patterns-established:
  - "Gap-closure plans modify only existing files — no new files created"
  - "False-green test replacement: replace synthetic fixture string with live connector shape"

requirements-completed: [K8S-01, K8S-02, K8S-03]

duration: 10min
completed: 2026-04-26
---

# Phase 29 Plan 04: Gap Closure (CR-01/CR-02/CR-03) Summary

**Three confirmed BLOCKER gaps from 29-VERIFICATION.md closed: RBAC 403 evidence counter now fires, AKS credential failure emits per-cluster inaccessible findings, and _enumerate_secret_types aligns to documented service_detail='secret-types-summary' string.**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-04-26T13:26:00Z
- **Completed:** 2026-04-26T13:36:22Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments

- CR-01: `dar_k8s_inaccessible_count` now fires for live RBAC 403 findings (scan_error='insufficient-rbac-privileges')
- CR-02: AKS `DefaultAzureCredential()` failure path emits one inaccessible finding per configured `aks_clusters` entry, and one fallback when list is empty
- CR-03: `_enumerate_secret_types` emits `service_detail='secret-types-summary'` (retired 'K8S-SECRETS/types-enumerated')
- Two false-green tests replaced with live-shape fixtures that will fail when the contract drifts
- Two new AKS regression tests added (per-cluster case + empty-list corollary)
- 69 tests pass across K8S connector, dar scoring, intelligence evidence/scoring, and CBOM suites

## CR-01: evidence.py RBAC 403 Fix

**Problem:** `quirk/intelligence/evidence.py` KUBERNETES elif checked `'rbac-403' in sd` (service_detail substring) but the connector emits `scan_error='insufficient-rbac-privileges'` with a remediation-text `service_detail`. The counter never fired for live RBAC 403 findings.

**Fix:** Added `scan_err = str(getattr(ep, "scan_error", "") or "")` extraction and added `scan_err == "insufficient-rbac-privileges"` and `scan_err == "encryption-config-inaccessible"` checks to the elif condition. The backward-compat `"rbac-403" in sd` substring check is preserved.

**Test fix:** Replaced `test_dar_k8s_inaccessible_count_rbac_403` false-green (using `service_detail="rbac-403"`) with live-shape fixture using `scan_error="insufficient-rbac-privileges"` and a remediation-text service_detail. Extended `_ep()` helper to accept `scan_error` kwarg.

## CR-02: AKS Credential Failure Path

**Problem:** The `except Exception as exc` block after `DefaultAzureCredential()` only set `credential = None` and logged a message. No `_emit_inaccessible_finding` call — K8S-03 invariant violated on AKS when Azure credentials are unavailable.

**Fix:** Added a loop over `aks_clusters` inside the except block that calls `_emit_inaccessible_finding` once per configured cluster entry. When `aks_clusters` is empty/None, emits one fallback finding. The `if credential is not None:` guard remains a separate statement so the happy path is untouched.

**New tests:**
- `test_aks_credential_failure_emits_inaccessible_per_cluster` — 2-cluster config → 2 inaccessible findings
- `test_aks_credential_failure_no_clusters_still_emits_one_inaccessible` — empty aks_clusters → at least 1 finding

## CR-03: service_detail String Alignment

**Problem:** `_enumerate_secret_types` emitted `service_detail='K8S-SECRETS/types-enumerated'` but `docs/UAT-SERIES.md` (lines 1781, 1789, 1824, 1867) and `labs/kubernetes/expected_results.md` (line 90) document `'secret-types-summary'`. Code drifted from docs — docs are the contract.

**Fix (one-line change):** Changed `service_detail="K8S-SECRETS/types-enumerated"` to `service_detail="secret-types-summary"` in `_enumerate_secret_types` return statement. No docs were modified.

**Test fixes:**
- `tests/test_k8s_connector.py` line 265 assertion updated to `"secret-types-summary"`
- `test_dar_k8s_secret_types_summary_neutral` rewritten to use the direct `CryptoEndpoint` constructor with `host="k8s://secrets/default"`, `port=0` — pins the exact production shape instead of the `_ep()` helper

## Task Commits

1. **Task 1: CR-01 — evidence.py + test_dar_k8s_scoring.py** - `54b65b1` (fix)
2. **Task 2: CR-02 — AKS credential failure path + regression tests** - `dbb8589` (fix)
3. **Task 3: CR-03 — service_detail alignment + test updates** - `8dc1022` (fix)

## Files Created/Modified

- `quirk/intelligence/evidence.py` — Added scan_err extraction and two scan_error checks to KUBERNETES elif
- `quirk/scanner/k8s_connector.py` — CR-02 except block emits per-cluster inaccessible findings; CR-03 service_detail string changed
- `tests/test_dar_k8s_scoring.py` — Extended _ep() helper; replaced CR-01 false-green; rewrote CR-03 neutrality test with live shape
- `tests/test_k8s_connector.py` — Updated assertion for CR-03; appended two new CR-02 AKS regression tests

## Decisions Made

- CR-01: Kept backward-compat `"rbac-403" in sd` check alongside new scan_error checks — cost is zero, protects any remaining synthetic-string fixtures
- CR-02: Per-cluster loop lives inside the except block; `if credential is not None:` guard remains separate (not inside the else of an inner if) — preserves happy-path readability
- CR-03: Code aligned to docs (connector changed, not docs) — UAT-SERIES.md and expected_results.md were already correct; the string 'K8S-SECRETS/types-enumerated' is now fully retired from the repo

## Deviations from Plan

None — plan executed exactly as written. All three CRs applied via the specified line-level changes.

## Issues Encountered

None — all edits were one-to-one replacements matching the plan's before/after blocks. Tests passed on first run after each edit.

## Known Stubs

None — all production code paths emit the correct strings and counter increments; no placeholder values.

## Threat Flags

None — no new network endpoints, auth paths, file access patterns, or schema changes introduced. The changes close existing threat surface (T-29-10, T-29-11, T-29-12 from the plan's threat register).

## Next Phase Readiness

- All three BLOCKER gaps from 29-VERIFICATION.md are resolved
- Phase 29 verification can be re-run: 29-VERIFICATION.md criteria for CR-01/CR-02/CR-03 are now satisfied
- `python -m compileall quirk/` exits 0 — no syntax errors
- 69 tests pass across the full K8S + intelligence + CBOM regression suite
- docs/UAT-SERIES.md and labs/kubernetes/expected_results.md required no modification

## Self-Check: PASSED

- `quirk/intelligence/evidence.py` — exists, contains `scan_err == "insufficient-rbac-privileges"`
- `quirk/scanner/k8s_connector.py` — exists, contains `service_detail="secret-types-summary"` and `CR-02 (Phase 29 gap closure)` comment
- `tests/test_dar_k8s_scoring.py` — exists, contains `scan_error="insufficient-rbac-privileges"` and `host="k8s://secrets/default"`
- `tests/test_k8s_connector.py` — exists, contains `service_detail == "secret-types-summary"` and `test_aks_credential_failure_emits_inaccessible_per_cluster`
- Commits verified: 54b65b1, dbb8589, 8dc1022 all present in git log

---
*Phase: 29-kubernetes-secrets-inspection*
*Completed: 2026-04-26*
