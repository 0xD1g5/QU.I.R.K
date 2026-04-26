---
phase: 29
plan: "01"
subsystem: kubernetes-secrets-inspection
tags: [kubernetes, k8s, eks, gke, aks, scaffold, red-tests, tdd, config]
dependency_graph:
  requires: []
  provides: [K8S-config-fields, K8S-cloud-extras, K8S-red-tests]
  affects: [quirk/config.py, pyproject.toml, tests/test_k8s_connector.py]
tech_stack:
  added: [kubernetes>=35.0.0, google-cloud-container>=2.0.0, azure-mgmt-containerservice>=35.0.0]
  patterns: [TDD-RED-scaffold, ConnectorsCfg-extension, cloud-extras-pattern]
key_files:
  created: [tests/test_k8s_connector.py]
  modified: [pyproject.toml, quirk/config.py, quirk/config_template.yaml]
decisions:
  - "All K8S findings use protocol=KUBERNETES (not K8S, not STORAGE)"
  - "ApiException import shim in test file via try/except ImportError for kubernetes SDK absence"
  - "K8S-03 inaccessible finding required on all unrecognized providers — never silent empty list"
metrics:
  duration: "~10 minutes"
  completed: "2026-04-26"
  tasks_completed: 2
  files_modified: 4
---

# Phase 29 Plan 01: Kubernetes RED Scaffold — pyproject, config, test contract

Established the RED scaffold for Phase 29 K8S secrets inspection: three new cloud extras (kubernetes, google-cloud-container, azure-mgmt-containerservice), eight new ConnectorsCfg fields, config template entries, and 15 RED tests locking the K8S-01/K8S-02/K8S-03/ISSUE-2/ISSUE-3 contract before any implementation.

## What Was Built

### Task 1: pyproject.toml + ConnectorsCfg + config_template (b175523)

**pyproject.toml** — Extended `[cloud]` extras with three Phase 29 SDK version pins:
- `kubernetes>=35.0.0` (K8S-01, K8S-02)
- `google-cloud-container>=2.0.0` (GKE databaseEncryption.state)
- `azure-mgmt-containerservice>=35.0.0` (AKS Key Vault KMS detection)

**quirk/config.py** — Added 8 new K8S fields to `ConnectorsCfg` immediately after the Phase 28 object-storage block (`aws_endpoint_url`):
- `enable_k8s: bool = False`
- `k8s_provider: Optional[str] = None` — "eks" | "gke" | "aks"
- `k8s_cluster_name: Optional[str] = None`
- `k8s_namespace: str = "default"`
- `k8s_kubeconfig: Optional[str] = None`
- `k8s_context: Optional[str] = None`
- `gke_clusters: list = field(default_factory=list)`
- `aks_clusters: list = field(default_factory=list)`

All fields use safe defaults; `ConnectorsCfg()` instantiates without error. `_KNOWN_CONNECTOR_KEYS` auto-discovers all 8 via `dataclasses.fields()` — no manual update needed.

**quirk/config_template.yaml** — Added commented K8S section with section header and all 8 entries after the Phase 28 object-storage block.

### Task 2: tests/test_k8s_connector.py RED scaffold (5b15c94)

Created `tests/test_k8s_connector.py` (377 lines, 15 tests) covering:

| Category | Tests | Requirement |
|----------|-------|-------------|
| ISSUE-2 | `test_pyproject_cloud_extras_lists_phase_29_sdks` | Verifies all 3 new SDK pins in pyproject.toml |
| K8S-01 EKS | 3 tests | encryptionConfig empty/absent → HIGH; with keyArn → no severity |
| K8S-01 GKE | 2 tests | current_state=2 → no severity; current_state=1 → HIGH |
| K8S-01 AKS | 3 tests | kv_kms.enabled=True → no severity; False/None → MEDIUM |
| K8S-02 | 3 tests | type Counter in dat_scan_json; secret.data sentinel; RBAC 403 → scan_error |
| K8S-03 | 2 tests | unknown provider → inaccessible; SDK absent → inaccessible |
| ISSUE-3 | 1 test | session_start stamps scanned_at (tz-stripped) |

**RED state confirmed:** 14 tests fail with `ImportError`/`ModuleNotFoundError` because `quirk/scanner/k8s_connector.py` does not exist and `_scan_eks_encryption` is not yet in `aws_connector.py`. Plan 02 implements the GREEN state.

**ISSUE-2 pyproject test passes immediately** (as designed — locks the dependency contract up front).

The `ApiException` import in `test_secret_rbac_403_produces_insufficient_privileges` uses a `try/except ImportError` shim so the file loads without the kubernetes SDK installed; the test still fails in RED state with `ModuleNotFoundError` on `k8s_connector` until Plan 02.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Critical] ApiException import shim in test_rbac_403 test**
- **Found during:** Task 2
- **Issue:** The plan noted that `from kubernetes.client.rest import ApiException` would cause `ImportError` and suggested a shim pattern in a footnote
- **Fix:** Applied the `try/except ImportError: ApiException = type(...)` shim directly so the file is importable in all environments; the test still fails in RED state as required
- **Files modified:** `tests/test_k8s_connector.py`
- **Commit:** 5b15c94

## Known Stubs

None — this is a RED scaffold plan. No data flows to UI. The test stubs are intentional: they encode the contract for Plan 02's GREEN implementation.

## Threat Flags

None found — this plan only adds optional dependency declarations, config field defaults, and test-only mocks. No new network endpoints, auth paths, file access, or schema changes at trust boundaries.

## Self-Check: PASSED

- `tests/test_k8s_connector.py` exists: FOUND
- `b175523` commit exists: FOUND
- `5b15c94` commit exists: FOUND
- `python -c "from quirk.config import ConnectorsCfg; ConnectorsCfg()"` exits 0: PASSED
- `python -m compileall quirk/` exits clean: PASSED
- 15 tests collected, 14 RED failures, 1 pass (ISSUE-2): CONFIRMED
