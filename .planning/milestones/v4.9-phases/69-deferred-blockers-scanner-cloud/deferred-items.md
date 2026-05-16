# Phase 69 Deferred Items

> **UPDATE 2026-05-15:** Phase 69.1 (K8s Test Fixture Hardening) closed
> 6 of the items below. The Phase 69-03 env-fragile test and all 4
> pre-existing `test_k8s_connector.py` failures now pass in canonical
> `.venv`. See `.planning/phases/69.1-k8s-test-fixture-hardening/69.1-VERIFICATION.md`.
> The 2 `test_tls_scanner_chain_verified.py` entries remain open as a
> separate test-infra concern.

## Pre-existing test failures (NOT Phase 69 regressions)

Verified pre-existing by `git checkout 92d9f26 -- tests/test_k8s_connector.py quirk/scanner/k8s_connector.py` and running pytest. All failures predate Phase 69.

- `tests/test_tls_scanner_chain_verified.py::test_sslyze_success_chain_verified_true` — present before plan 69-01, out of scope.
- `tests/test_tls_scanner_chain_verified.py::test_sslyze_success_chain_verified_false` — present before plan 69-01, out of scope.
- `tests/test_k8s_connector.py::test_gke_encrypted_no_severity` — fails in `.venv` (Python 3.14) with `ModuleNotFoundError` on azure SDK plumbing. Pre-existing.
- `tests/test_k8s_connector.py::test_gke_unencrypted_produces_high` — same root cause. Pre-existing.
- `tests/test_k8s_connector.py::test_secret_rbac_403_produces_insufficient_privileges` — pre-existing assertion failure.
- `tests/test_k8s_connector.py::test_aks_credential_failure_emits_inaccessible_per_cluster` — pre-existing assertion failure (expected 2 inaccessible findings, got 1).

Detected during Phase 69 regression sweep on 2026-05-15. All 6 failures share the same family of root cause: `azure.identity.DefaultAzureCredential` patch targets do not intercept the import-resolved binding in `quirk.scanner.k8s_connector` under Python 3.14's azure SDK plumbing in `.venv`. The agent's `/usr/bin/python3` (Python 3.9, user-site pytest install) has a different module-resolution path where the patches land cleanly.

## Phase 69 environment-fragile test

- `tests/test_k8s_connector.py::test_aks_empty_cluster_list_returns_empty` — Phase 69-03 RED-GREEN test that exercises the CR-09 short-circuit. **Source fix is correct** (verified structurally at `k8s_connector.py:502` — `if not (aks_clusters or []): return []` inside the `if credential is not None:` block per locked decision D-09). The test failure in `.venv` is the same azure-SDK-patch-target issue as the pre-existing failures above; not a bug in the fix.

## Recommended follow-up

Open a separate ticket to:
1. Fix the `.venv` azure SDK plumbing so `azure.identity.DefaultAzureCredential` patches intercept the k8s_connector import-resolved binding under Python 3.14.
2. Audit `test_k8s_connector.py` patch targets — likely candidates: switch from `patch("azure.identity.DefaultAzureCredential", create=True, ...)` to `patch("quirk.scanner.k8s_connector.DefaultAzureCredential", create=True, ...)` if that is the actual import path used by the code under test.
3. Once `.venv` is fixed, rerun the Phase 69-03 test as a regression confirmation.
