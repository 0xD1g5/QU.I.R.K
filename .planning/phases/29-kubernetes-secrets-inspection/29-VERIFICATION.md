---
phase: 29-kubernetes-secrets-inspection
verified: 2026-04-26T18:00:00Z
status: gaps_found
score: 3/4 roadmap success criteria verified (SC-1 and SC-4 partial; see gaps)
overrides_applied: 0
gaps:
  - truth: "When etcd encryption state cannot be determined, scanner emits explicit encryption-config-inaccessible finding — never silently skips (K8S-03 invariant)"
    status: partial
    reason: "AKS credential failure silently drops the AKS cluster without emitting inaccessible finding — K8S-03 invariant violated for AKS DefaultAzureCredential exceptions. Confirmed in codebase: k8s_connector.py lines 453-467 set credential=None and skip _scan_aks_encryption without calling _emit_inaccessible_finding for each configured AKS cluster."
    artifacts:
      - path: "quirk/scanner/k8s_connector.py"
        issue: "Lines 453-467: except block sets credential=None and skips scan; no inaccessible finding emitted for configured aks_clusters. The final safety net at line 495 does not fire if another provider (GKE) or secret enum produces results."
    missing:
      - "Emit _emit_inaccessible_finding for each cfg_item in aks_clusters when DefaultAzureCredential raises"

  - truth: "RBAC 403 errors produce insufficient-rbac-privileges findings that are counted in dar_k8s_inaccessible_count"
    status: failed
    reason: "CR-01 confirmed: evidence.py KUBERNETES branch checks 'rbac-403' in service_detail, but the live connector emits scan_error='insufficient-rbac-privileges' with service_detail='Remediation: RBAC role requires...' — substring 'rbac-403' never appears in service_detail. dar_k8s_inaccessible_count is 0 for RBAC 403 findings. Test test_dar_k8s_inaccessible_count_rbac_403 passes against synthetic endpoint with service_detail='rbac-403', NOT the string the real connector emits — false-green coverage."
    artifacts:
      - path: "quirk/intelligence/evidence.py"
        issue: "Line 196: checks 'rbac-403' in sd (service_detail only) but connector emits scan_error='insufficient-rbac-privileges'. Evidence counter never increments for live RBAC 403 findings."
      - path: "tests/test_dar_k8s_scoring.py"
        issue: "Line 75: test_dar_k8s_inaccessible_count_rbac_403 creates endpoint with service_detail='rbac-403' — a string the connector never emits. Test is a false-green."
    missing:
      - "Add scan_error check to evidence.py KUBERNETES elif: also check scan_err == 'insufficient-rbac-privileges'"
      - "Update test_dar_k8s_inaccessible_count_rbac_403 to use the connector's actual service_detail string, or set scan_error='insufficient-rbac-privileges'"

  - truth: "service_detail emitted by secret type enumeration matches documented and user-visible value in UAT-SERIES.md and labs/kubernetes/expected_results.md"
    status: failed
    reason: "CR-03 confirmed: _enumerate_secret_types emits service_detail='K8S-SECRETS/types-enumerated' but UAT-SERIES.md (lines 1781, 1789, 1824, 1867) and labs/kubernetes/expected_results.md (line 90) document 'secret-types-summary'. Live UAT assertions will fail. The test test_dar_k8s_secret_types_summary_neutral uses service_detail='secret-types-summary' (non-matching) and passes only because neither counter checks that string — false-green."
    artifacts:
      - path: "quirk/scanner/k8s_connector.py"
        issue: "Line 293: service_detail='K8S-SECRETS/types-enumerated'"
      - path: "docs/UAT-SERIES.md"
        issue: "Lines 1781, 1789, 1824, 1867: documents 'secret-types-summary' as expected service_detail"
      - path: "labs/kubernetes/expected_results.md"
        issue: "Line 90: documents 'secret-types-summary' as expected service_detail"
      - path: "tests/test_dar_k8s_scoring.py"
        issue: "Line 75: uses 'secret-types-summary' (not what connector emits) in neutrality test — false-green"
    missing:
      - "Either update k8s_connector.py line 293 to emit service_detail='secret-types-summary' (and update test_k8s_connector.py line 265 to match), or update all docs to 'K8S-SECRETS/types-enumerated'"
human_verification:
  - test: "Live EKS cluster etcd encryption detection"
    expected: "One aws://eks/<cluster> row with service_detail EKS/encrypted or EKS/unencrypted depending on encryptionConfig; one secret-types-summary row with type counts"
    why_human: "Requires live AWS EKS cluster with valid credentials — cannot be verified programmatically"
  - test: "Live GKE cluster databaseEncryption.state detection"
    expected: "One gcp://gke/... row with service_detail GKE/encrypted (state==2) or GKE/unencrypted (state!=2)"
    why_human: "Requires live GKE cluster with GCP ADC configured"
  - test: "Live AKS cluster Key Vault KMS detection"
    expected: "One azure://aks/... row with AKS/kv-kms (no severity) or AKS/platform-managed (MEDIUM)"
    why_human: "Requires live Azure subscription with AKS cluster"
---

# Phase 29: Kubernetes Secrets Inspection Verification Report

**Phase Goal:** QU.I.R.K. can detect etcd encryption status and enumerate secret types on managed Kubernetes clusters — using managed cloud APIs without requiring direct etcd access or agent installation on cluster nodes
**Verified:** 2026-04-26T18:00:00Z
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (from ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| SC-1 | EKS/GKE/AKS managed cluster encryption APIs each return etcd encryption status via distinct API paths with consistent schema | VERIFIED (with WARNING) | k8s_connector.py 506 lines, _scan_gke_encryption and _scan_aks_encryption wired; _scan_eks_encryption in aws_connector.py; all 15 tests pass. WARNING: AKS credential failure drops silently (CR-02) |
| SC-2 | Secret type count enumeration returns types without reading any secret values | VERIFIED | _enumerate_secret_types accesses only s.type; test_secret_type_enumeration_never_reads_data uses property sentinel raising AssertionError on .data access — passes |
| SC-3 | Scanner emits explicit encryption-config-inaccessible finding when etcd state cannot be determined — never silently skips | PARTIAL — BLOCKER | Unknown-provider and K8S_AVAILABLE=False paths emit correctly; but AKS DefaultAzureCredential failure silently drops the AKS scan without emitting inaccessible finding (CR-02 confirmed) |
| SC-4 | kubernetes>=35.0.0 in [cloud] extras; RBAC 403 caught and produces insufficient-rbac-privileges finding | PARTIAL — BLOCKER | kubernetes>=35.0.0 in pyproject.toml VERIFIED; RBAC 403 scan_error emitted correctly by connector VERIFIED; but dar_k8s_inaccessible_count never increments for this finding (CR-01 mismatch confirmed by running actual Python) |

**Score:** 2/4 truths fully verified; 2 PARTIAL (blocker gaps confirmed by code execution)

### Requirement Coverage

| Requirement | Description | Status | Evidence |
|-------------|-------------|--------|----------|
| K8S-01 | EKS/GKE/AKS encryption detection via managed APIs | PARTIAL | Three API paths implemented and tested; AKS silent drop on credential failure violates coverage for that path |
| K8S-02 | Secret type count enumeration, no secret values read | VERIFIED | _enumerate_secret_types confirmed; sentinel test passes |
| K8S-03 | Explicit encryption-config-inaccessible finding when state unknowable | PARTIAL | Unknown provider and SDK-absent paths correct; AKS credential failure path is a gap |

All three requirement IDs (K8S-01, K8S-02, K8S-03) declared across Plans 01/02/03 — all map to REQUIREMENTS.md Phase 29 row. No orphaned requirements found.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `quirk/scanner/k8s_connector.py` | GKE+AKS encryption, secret enum, K8S-03 inaccessible | VERIFIED (506 lines) | Triple import guards; all functions present; no s.data access |
| `quirk/scanner/aws_connector.py` | `_scan_eks_encryption` present | VERIFIED | Lines 132-198; paginator pattern; session_start threaded; protocol=KUBERNETES |
| `run_scan.py` | `k8s_scanning` block gated on enable_k8s | VERIFIED | Lines 573-612; calls scan_k8s_targets and _scan_eks_encryption; aggregates k8s_endpoints |
| `quirk/config.py` | ConnectorsCfg with 8 K8S fields | VERIFIED | Lines 85-93; enable_k8s, k8s_provider, k8s_cluster_name, k8s_namespace, k8s_kubeconfig, k8s_context, gke_clusters, aks_clusters; ConnectorsCfg() instantiates cleanly |
| `quirk/config_template.yaml` | Commented K8S section | VERIFIED | Contains commented K8S section with section header |
| `pyproject.toml` | kubernetes>=35.0.0, google-cloud-container>=2.0.0, azure-mgmt-containerservice>=35.0.0 in [cloud] | VERIFIED | All three entries confirmed present |
| `quirk/intelligence/evidence.py` | _PROTOCOL_KEYS includes KUBERNETES; dar_k8s_* counters | VERIFIED (partially broken) | KUBERNETES in _PROTOCOL_KEYS; counters initialized; KUBERNETES elif block present; but rbac-403 check targets wrong field (CR-01) |
| `quirk/intelligence/scoring.py` | dar_k8s_unencrypted_ratio: 10.0, dar_k8s_inaccessible_ratio: 4.0 in SCORE_WEIGHTS; Kubernetes etcd impacts in dar_impacts | VERIFIED | SCORE_WEIGHTS confirmed; 6-entry dar_impacts confirmed; extraction variables present |
| `quirk/cbom/builder.py` | Pass 1/2/3 skip-lists include KUBERNETES | VERIFIED | All three pass locations confirmed with grep; no KUBERNETES rows produce CBOM components |
| `tests/test_k8s_connector.py` | 15 tests, all GREEN | VERIFIED | 377 lines; 15 tests; all pass |
| `tests/test_dar_k8s_scoring.py` | 12 tests, all GREEN (with false-greens noted) | VERIFIED (with false-greens) | 112 lines; 12 tests pass; BUT test_dar_k8s_inaccessible_count_rbac_403 and test_dar_k8s_secret_types_summary_neutral are false-greens |
| `labs/kubernetes/expected_results.md` | ≥40 lines, Limitations section, UAT-29-XX refs | VERIFIED | 145 lines; explicit no-Docker-chaos-lab section; UAT-29-01/02/03 referenced |
| `docs/UAT-SERIES.md` | UAT-29-01/02/03 cases, Last Updated: 2026-04-26 | VERIFIED | 4 matches for UAT-29-0x; Last Updated confirmed; 3 full UAT cases present |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `run_scan.py` | `scan_k8s_targets` | `with _phase_timer(run_stats, 'k8s_scanning')` | WIRED | Lines 577-612 confirmed |
| `run_scan.py` | `_scan_eks_encryption` | `if k8s_provider == 'eks'` inside k8s_scanning | WIRED | Lines 596-609 confirmed |
| `k8s_connector.scan_k8s_targets` | `encryption-config-inaccessible` | `_emit_inaccessible_finding` | WIRED (incomplete) | Unknown-provider and K8S_AVAILABLE=False paths wired; AKS credential failure path is NOT wired |
| `k8s_connector._enumerate_secret_types` | ApiException status==403 | `getattr(exc, 'status', None) == 403` | WIRED | Line 305; duck-typed |
| `evidence.py KUBERNETES elif` | `dar_k8s_inaccessible_count` | `'rbac-403' in sd` | BROKEN | Checks service_detail substring; connector emits scan_error field — mismatch confirmed by execution |
| `k8s_endpoints` aggregation | `endpoints` master list in run_scan.py | `+ k8s_endpoints` | WIRED | Line 669 confirmed |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `_scan_gke_encryption` | `cluster.database_encryption.current_state` | GKE ClusterManagerClient.get_cluster() | Mocked in tests; live requires GKE | VERIFIED (test path) |
| `_scan_aks_encryption` | `cluster.security_profile.azure_key_vault_kms.enabled` | ContainerServiceClient.managed_clusters.get() | Mocked in tests | VERIFIED (test path) |
| `_enumerate_secret_types` | `s.type` (never s.data) | k8s_client.CoreV1Api.list_namespaced_secret() | Mocked in tests | VERIFIED (test path) |
| `evidence.py dar_k8s_inaccessible_count` | RBAC 403 path via service_detail | `_enumerate_secret_types` scan_error output | DISCONNECTED — wrong field checked | HOLLOW — rbac-403 path data does not flow |

### Behavioral Spot-Checks

| Behavior | Command/Method | Result | Status |
|----------|---------------|--------|--------|
| All 15 K8S connector tests pass | `python -m pytest tests/test_k8s_connector.py` | 15 passed in 0.25s | PASS |
| All 12 dar_k8s scoring tests pass | `python -m pytest tests/test_dar_k8s_scoring.py` | 12 passed | PASS (2 are false-greens) |
| CBOM regression tests pass | `python -m pytest tests/test_cbom_builder.py tests/test_intelligence_evidence.py tests/test_intelligence_scoring.py` | 40 passed | PASS |
| ConnectorsCfg instantiates with defaults | `python -c "from quirk.config import ConnectorsCfg; ConnectorsCfg()"` | OK | PASS |
| CR-01: rbac-403 counter for live connector output | `build_evidence_summary([ep_with_scan_error])` | dar_k8s_inaccessible_count=0 | FAIL — confirmed blocker |
| CR-03: service_detail mismatch | `_enumerate_secret_types(...).service_detail` | "K8S-SECRETS/types-enumerated" | FAIL — confirmed mismatch with docs |
| CR-02: AKS credential failure inaccessible finding | Code inspection lines 453-467 | No _emit_inaccessible_finding call in except block | FAIL — confirmed blocker |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `tests/test_dar_k8s_scoring.py` | 75 | `service_detail="rbac-403"` — synthetic string that connector never emits | WARNING | False-green test: test_dar_k8s_inaccessible_count_rbac_403 passes against a fixture that does not match live connector output |
| `tests/test_dar_k8s_scoring.py` | 75 | `service_detail="secret-types-summary"` in neutrality test | WARNING | False-green test: connector emits "K8S-SECRETS/types-enumerated"; test passes for wrong reason (neither counter matches either string) |
| `quirk/scanner/k8s_connector.py` | 366-367 | `gke_clusters: list = None, aks_clusters: list = None` | INFO | Type annotation mismatch; not a runtime error; mypy would reject |
| `docs/UAT-SERIES.md` | 1781, 1789, 1824, 1867 | References `secret-types-summary` as expected service_detail | BLOCKER | Live UAT will fail when querying DB for this string |
| `labs/kubernetes/expected_results.md` | 90 | References `secret-types-summary` | BLOCKER | Documentation contract broken with implementation |

### Human Verification Required

#### 1. Live EKS Encryption Detection (UAT-29-01)

**Test:** Configure `enable_k8s: true`, `k8s_provider: eks`, valid `aws_region`, run `quirk`
**Expected:** One `aws://eks/<cluster>` row with `service_detail=EKS/unencrypted` (severity HIGH) or `EKS/encrypted:<keyArn>` (no severity); one `K8S-SECRETS/types-enumerated` row (note: docs say `secret-types-summary` — resolve CR-03 first)
**Why human:** Requires live AWS EKS cluster with credentials

#### 2. Live GKE Encryption Detection (UAT-29-02)

**Test:** Configure `enable_k8s: true`, `k8s_provider: gke`, `gke_clusters: [{name, location}]`, GCP ADC, run `quirk`
**Expected:** One `gcp://gke/.../<cluster>` row with `GKE/encrypted:<key>` (state==2) or `GKE/unencrypted` (HIGH)
**Why human:** Requires live GKE cluster

#### 3. Live AKS Encryption Detection (UAT-29-03)

**Test:** Configure `enable_k8s: true`, `k8s_provider: aks`, `aks_clusters: [{name, resource_group}]`, Azure login, run `quirk`
**Expected:** One `azure://aks/.../<cluster>` row with `AKS/kv-kms` (no severity) or `AKS/platform-managed` (MEDIUM)
**Why human:** Requires live Azure AKS cluster

### Gaps Summary

Three blockers were confirmed by running actual Python code against the codebase — not inferred from static analysis alone.

**CR-01 (BLOCKER):** The `dar_k8s_inaccessible_count` evidence counter never fires for real RBAC 403 findings. The connector emits `scan_error="insufficient-rbac-privileges"` with a human-readable `service_detail`, but the counter only checks `"rbac-403" in service_detail`. Running `build_evidence_summary([ep])` with a connector-shaped endpoint confirms the count stays at 0. The scoring test that covers this is a false-green using a synthetic fixture. Fix: check `scan_error == "insufficient-rbac-privileges"` in addition to (or instead of) the service_detail substring.

**CR-02 (BLOCKER):** The K8S-03 invariant ("never silently skips") is violated on the AKS path when `DefaultAzureCredential()` raises. Code inspection of lines 453-467 of k8s_connector.py confirms: the except block sets `credential = None` and emits a log message only. No `_emit_inaccessible_finding` call is made for the configured AKS clusters. If GKE or secret enumeration produces results, the final safety net at line 495 does not fire. Fix: emit inaccessible finding per AKS cluster in the credential except block.

**CR-03 (BLOCKER):** `_enumerate_secret_types` emits `service_detail="K8S-SECRETS/types-enumerated"` but UAT-SERIES.md and labs/kubernetes/expected_results.md document `"secret-types-summary"` as the expected string. The connector test (test_k8s_connector.py line 265) correctly asserts the code's actual value; the scoring test (test_dar_k8s_scoring.py line 75) tests the documented value — so two tests test two different strings, both pass, and neither exposes the break. Live UAT query against the database will not find `secret-types-summary` rows. Fix: align connector and documentation on one string (prefer changing connector to match documented value).

These three gaps are rooted in two files (`evidence.py` and `k8s_connector.py`) and two documentation files (`UAT-SERIES.md`, `labs/kubernetes/expected_results.md`). CR-03 is a documentation-code contract break with a straightforward one-line fix to the connector. CR-01 is a one-line fix to evidence.py. CR-02 requires adding an emit loop in the AKS except block.

The core scanner functionality (EKS/GKE/AKS encryption detection ladder, secret enumeration without reading secret values, CBOM skip-list, intelligence score wiring) is present and structurally sound. The gaps are at the correctness boundary (counter mismatch, AKS K8S-03 invariant hole, doc/code contract break) rather than missing features.

---

_Verified: 2026-04-26T18:00:00Z_
_Verifier: Claude (gsd-verifier)_
