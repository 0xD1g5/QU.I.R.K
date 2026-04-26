---
phase: 29
slug: kubernetes-secrets-inspection
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-26
---

# Phase 29 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing — no config file, discovered by convention) |
| **Config file** | none — existing pytest infrastructure |
| **Quick run command** | `python -m pytest tests/test_k8s_connector.py -x -q` |
| **Full suite command** | `python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_k8s_connector.py -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -x -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Secure Behavior | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------------|-----------|-------------------|--------|
| 29-01-01 | 01 | 1 | ISSUE-2 | pyproject.toml [cloud] extras has all 3 K8S deps | unit | `pytest tests/test_k8s_connector.py::test_pyproject_cloud_extras -x` | ⬜ pending |
| 29-01-02 | 01 | 1 | K8S-01/02/03 | RED scaffold: 14+ tests fail with ImportError/NotImplemented | unit | `python -m pytest tests/test_k8s_connector.py -x -q 2>&1 \| grep -E "FAILED\|ERROR"` | ⬜ pending |
| 29-02-01 | 02 | 2 | K8S-01/02/03 | GREEN: all 14 RED tests pass; secret.data never accessed | unit | `python -m pytest tests/test_k8s_connector.py -x -q` | ⬜ pending |
| 29-02-02 | 02 | 2 | K8S-01 | EKS wired in aws_connector.py; run_scan.py K8S block present | unit | `python -m pytest tests/ -x -q` | ⬜ pending |
| 29-03-01 | 03 | 3 | K8S-01/02/03 | dar_k8s_* counters in evidence.py; 2 weights in scoring.py | unit | `python -m pytest tests/test_dar_k8s_scoring.py tests/test_intelligence_evidence.py tests/test_intelligence_scoring.py -x -q` | ⬜ pending |
| 29-03-02 | 03 | 3 | K8S-01 | builder.py Pass 1/2/3 all skip KUBERNETES | unit | `python -m pytest tests/test_cbom_builder.py -x -q` | ⬜ pending |
| 29-03-03 | 03 | 3 | K8S-01/02/03 | labs/kubernetes/expected_results.md exists; UAT-SERIES updated | file | `test -f labs/kubernetes/expected_results.md && grep -c 'Phase 29' docs/UAT-SERIES.md` | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Phase Requirements → Test Map

| Requirement | Behavior | Test Type | Command | Wave |
|-------------|----------|-----------|---------|------|
| K8S-01 | EKS `encryptionConfig` absent/empty → HIGH/KUBERNETES/EKS-unencrypted | unit | `pytest tests/test_k8s_connector.py::test_eks_unencrypted -x` | Wave 0 |
| K8S-01 | EKS `encryptionConfig` with `resources: ["secrets"]` → no finding / EKS/encrypted | unit | `pytest tests/test_k8s_connector.py::test_eks_encrypted -x` | Wave 0 |
| K8S-01 | GKE `current_state == 2` (ENCRYPTED) → no finding / GKE/encrypted | unit | `pytest tests/test_k8s_connector.py::test_gke_encrypted -x` | Wave 0 |
| K8S-01 | GKE `current_state == 1` (DECRYPTED) → HIGH / GKE/unencrypted | unit | `pytest tests/test_k8s_connector.py::test_gke_unencrypted -x` | Wave 0 |
| K8S-01 | AKS `kv_kms.enabled=True` → no finding / AKS/kv-kms | unit | `pytest tests/test_k8s_connector.py::test_aks_kv_kms_enabled -x` | Wave 0 |
| K8S-01 | AKS `kv_kms.enabled=False` → MEDIUM / AKS/platform-managed | unit | `pytest tests/test_k8s_connector.py::test_aks_platform_managed -x` | Wave 0 |
| K8S-02 | `list_namespaced_secret` returns type counts; `secret.data` never accessed | unit | `pytest tests/test_k8s_connector.py::test_secret_type_counts -x` | Wave 0 |
| K8S-02 | Mixed secret types (Opaque, tls, dockerconfigjson) produce correct Counter | unit | `pytest tests/test_k8s_connector.py::test_secret_type_counter -x` | Wave 0 |
| K8S-02 | RBAC 403 ApiException → `insufficient-rbac-privileges` scan_error endpoint | unit | `pytest tests/test_k8s_connector.py::test_k8s_rbac_403 -x` | Wave 0 |
| K8S-03 | Unknown provider → `encryption-config-inaccessible` finding (not empty list) | unit | `pytest tests/test_k8s_connector.py::test_unknown_provider_inaccessible -x` | Wave 0 |
| K8S-03 | `K8S_AVAILABLE=False` → `encryption-config-inaccessible` finding (not empty list) | unit | `pytest tests/test_k8s_connector.py::test_sdk_unavailable_inaccessible -x` | Wave 0 |
| ISSUE-2 | `pyproject.toml` `[cloud]` extras includes `kubernetes>=35.0.0` | unit | `pytest tests/test_k8s_connector.py::test_pyproject_cloud_extras -x` | Wave 0 |
| ISSUE-3 | `scan_k8s_targets()` accepts `session_start` and stamps endpoints | unit | `pytest tests/test_k8s_connector.py::test_session_start_stamped -x` | Wave 0 |
| evidence | `dar_k8s_unencrypted_count` increments for KUBERNETES/unencrypted rows | unit | `pytest tests/test_intelligence_evidence.py -x -q` | Exists |
| scoring | `dar_k8s_unencrypted_ratio` weight appears in score computation | unit | `pytest tests/test_intelligence_scoring.py -x -q` | Exists |

---

## Wave 0 Requirements

- [ ] `tests/test_k8s_connector.py` — all K8S-01/K8S-02/K8S-03 + ISSUE-2/ISSUE-3 tests (new file, created in Plan 29-01)
- [ ] `tests/test_dar_k8s_scoring.py` — evidence/scoring tests (new file, created in Plan 29-03)

*Existing `tests/test_intelligence_evidence.py` and `tests/test_intelligence_scoring.py` are extended — no new infrastructure needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live EKS cluster etcd encryption detection | K8S-01 | Requires AWS credentials + live EKS cluster | UAT-29-01: configure aws_eks_cluster_name, run quirk, verify KUBERNETES rows in output |
| Live GKE cluster databaseEncryption.state | K8S-01 | Requires GCP ADC + live GKE cluster | UAT-29-02: configure gke_cluster_name + gke_project_id, run quirk |
| Live AKS cluster Key Vault KMS detection | K8S-01 | Requires Azure subscription + live AKS cluster | UAT-29-03: configure aks_resource_group + aks_cluster_name, run quirk |
| Secret type enumeration on live cluster | K8S-02 | Requires live cluster with secrets | Part of UAT-29-01/02/03 above |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
