---
phase: 29-kubernetes-secrets-inspection
verified: 2026-04-26T14:00:00Z
status: passed
score: 7/7 must-haves verified
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 3/4 roadmap success criteria (2 partial/blocker)
  gaps_closed:
    - "CR-01: evidence.py KUBERNETES elif now checks scan_err == 'insufficient-rbac-privileges'; dar_k8s_inaccessible_count fires for live RBAC 403 findings"
    - "CR-02: AKS DefaultAzureCredential() failure path now emits per-cluster inaccessible findings; K8S-03 invariant restored"
    - "CR-03: _enumerate_secret_types now emits service_detail='secret-types-summary'; false-green tests replaced with live-shape fixtures"
  gaps_remaining: []
  regressions: []
---

# Phase 29: Kubernetes Secrets Inspection — Verification Report

**Phase Goal:** QU.I.R.K. can detect etcd encryption status and enumerate secret types on managed Kubernetes clusters — using managed cloud APIs without requiring direct etcd access or agent installation on cluster nodes
**Verified:** 2026-04-26T14:00:00Z
**Status:** PASSED
**Re-verification:** Yes — after gap closure by plan 29-04 (CR-01/CR-02/CR-03)

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | K8S-01: EKS encryption status detected via AWS boto3 paginator + describe_cluster encryptionConfig ladder; no direct etcd access | ✓ VERIFIED | `_scan_eks_encryption` at `quirk/scanner/aws_connector.py:132`; paginator + describe_cluster pattern confirmed; 3 EKS tests pass (empty config HIGH, absent key HIGH, keyArn+secrets no-severity) |
| 2 | K8S-01: GKE encryption detected via `databaseEncryption.current_state` int comparison (state==2 encrypted, other unencrypted) | ✓ VERIFIED | `_scan_gke_encryption` at `k8s_connector.py:96`; `int(db_enc.current_state) == 2` at line 133; 2 GKE tests pass |
| 3 | K8S-01: AKS encryption detected via three nested getattr defenses on `security_profile.azure_key_vault_kms.enabled`; CR-02 fix: DefaultAzureCredential failure emits per-cluster inaccessible finding | ✓ VERIFIED | `_scan_aks_encryption` at `k8s_connector.py:175`; getattr chain at lines 220-222; CR-02 except block at lines 456-491 confirmed; 3 AKS happy-path tests + 2 CR-02 regression tests pass |
| 4 | K8S-02: `_enumerate_secret_types` accesses only `s.type` (never `s.data`); emits `service_detail='secret-types-summary'`; RBAC 403 → `scan_error='insufficient-rbac-privileges'` | ✓ VERIFIED | Line 293: `service_detail="secret-types-summary"`; 0 executable occurrences of `secret.data` in `quirk/scanner/k8s_connector.py`; line 310: `scan_error="insufficient-rbac-privileges"`; 3 K8S-02 tests pass including sentinel test |
| 5 | K8S-03: Never silently skips — emits `encryption-config-inaccessible` on unknown provider, SDK absent, GKE SDK absent, AKS SDK absent, AKS credential failure (per cluster), and final safety net | ✓ VERIFIED | `_emit_inaccessible_finding` called at 7 sites in `scan_k8s_targets`; K8S-03 path-A (line 392), path-B (line 407); GKE SDK absent (422); AKS SDK absent (443); AKS credential-failure loop (477) + fallback (486); safety net (528) |
| 6 | RBAC 403 findings correctly increment `dar_k8s_inaccessible_count` via scan_error field check (CR-01 fix) | ✓ VERIFIED | `evidence.py:191`: `scan_err = str(getattr(ep, "scan_error", "") or "")`; `evidence.py:195`: `scan_err == "insufficient-rbac-privileges"` check; live-shape test `test_dar_k8s_inaccessible_count_rbac_403` passes with `scan_error="insufficient-rbac-privileges"` fixture |
| 7 | All 69 tests pass: K8S connector (17), dar_k8s scoring (12), intelligence evidence, intelligence scoring, CBOM | ✓ VERIFIED | `python -m pytest tests/test_k8s_connector.py tests/test_dar_k8s_scoring.py tests/test_intelligence_evidence.py tests/test_intelligence_scoring.py tests/test_cbom_builder.py -x -q` → **69 passed in 0.58s** |

**Score:** 7/7 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `quirk/scanner/k8s_connector.py` | Triple import guards + GKE/AKS sub-scanners + secret enum + K8S-03 helper + scan_k8s_targets | ✓ VERIFIED | 539 lines; `K8S_AVAILABLE`, `GKE_AVAILABLE`, `AKS_AVAILABLE` module-level; `service_detail="secret-types-summary"` at line 293; CR-02 loop at lines 469-491 |
| `quirk/scanner/aws_connector.py` | `_scan_eks_encryption` with paginator + severity ladder + protocol="KUBERNETES" | ✓ VERIFIED | `def _scan_eks_encryption` at line 132; `protocol="KUBERNETES"` in CryptoEndpoint construction; `EKS/unencrypted` and `EKS/encrypted:` patterns present |
| `run_scan.py` | `k8s_scanning` phase block gated on `enable_k8s`; `scan_k8s_targets` call; EKS sub-call; `k8s_endpoints` aggregated | ✓ VERIFIED | Lines 577-612: `k8s_scanning` timer block; `enable_k8s` gate; `scan_k8s_targets`; `_scan_eks_encryption` for EKS provider; line 669: `+ k8s_endpoints` in aggregation |
| `quirk/intelligence/evidence.py` | `"KUBERNETES"` in `_PROTOCOL_KEYS`; `dar_k8s_unencrypted_count`/`dar_k8s_inaccessible_count` initialized; KUBERNETES elif with `scan_err` check (CR-01); 4 return dict keys | ✓ VERIFIED | Line 10: `"KUBERNETES"` in tuple; lines 87-88: counters; line 191: `scan_err` extraction; line 195: `scan_err == "insufficient-rbac-privileges"`; lines 265-268: all 4 return dict keys |
| `quirk/intelligence/scoring.py` | `dar_k8s_unencrypted_ratio: 10.0`, `dar_k8s_inaccessible_ratio: 4.0` in `SCORE_WEIGHTS`; `dar_k8s_*` extraction variables; Kubernetes etcd impacts in `dar_impacts` | ✓ VERIFIED | Lines 23-25: both weights; lines 182-183: `"Kubernetes etcd unencrypted"` and `"Kubernetes etcd encryption inaccessible"` impacts |
| `quirk/cbom/builder.py` | `"KUBERNETES"` in Pass 1/2/3 skip-lists | ✓ VERIFIED | Line 410 (Pass 1 elif); line 438 (Pass 2 skip tuple); line 519 (Pass 3 elif) |
| `tests/test_k8s_connector.py` | 17 tests: K8S-01 (3 EKS + 2 GKE + 3 AKS) + K8S-02 (3) + K8S-03 (2) + ISSUE-2/ISSUE-3 (2) + CR-02 regression (2) | ✓ VERIFIED | 17 tests collected; `test_aks_credential_failure_emits_inaccessible_per_cluster` and `test_aks_credential_failure_no_clusters_still_emits_one_inaccessible` present; all pass |
| `tests/test_dar_k8s_scoring.py` | 12 tests; live-shape RBAC 403 fixture; live-shape secret-types-summary neutrality test | ✓ VERIFIED | 12 tests; `scan_error="insufficient-rbac-privileges"` at line 69 (real connector shape); `host="k8s://secrets/default"` in neutrality test (pinned production shape); old false-greens eliminated |
| `labs/kubernetes/expected_results.md` | ≥40 lines; no Docker chaos lab note; UAT-29-01/02/03 references; Limitations section | ✓ VERIFIED | 145 lines; "No Docker chaos lab" section; UAT-29-01/02/03 referenced; Limitations section present |
| `docs/UAT-SERIES.md` | UAT-29-01/02/03 cases; `**Last Updated:** 2026-04-26` | ✓ VERIFIED | 4 matches for UAT-29-0{1,2,3}; header shows `**Last Updated:** 2026-04-26 (Phase 29: added UAT-29-01/02/03 ...)` |
| `pyproject.toml` | `kubernetes>=35.0.0`, `google-cloud-container>=2.0.0`, `azure-mgmt-containerservice>=35.0.0` in `[cloud]` | ✓ VERIFIED | Lines 48-50 confirmed |
| `quirk/config.py` | 8 K8S fields in `ConnectorsCfg` with safe defaults | ✓ VERIFIED | Lines 86-93; `ConnectorsCfg()` instantiates without error (`python -c "..."` confirmed) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `run_scan.py` | `scan_k8s_targets` | `k8s_scanning` phase timer + `enable_k8s` gate | ✓ WIRED | Line 580: `k8s_endpoints = scan_k8s_targets(...)` with all 10 params |
| `run_scan.py` | `_scan_eks_encryption` | `k8s_provider == "eks"` branch + boto3 session | ✓ WIRED | Lines 597-609: boto3 session; `k8s_endpoints.extend(_scan_eks_encryption(...))` |
| `run_scan.py` | `k8s_endpoints` → `endpoints` master list | `+ k8s_endpoints` in final concatenation | ✓ WIRED | Line 669 confirmed |
| `k8s_connector.scan_k8s_targets` | `_emit_inaccessible_finding` | 7 call sites: unsupported provider, K8S absent, GKE absent, AKS absent, AKS credential failure loop, AKS credential failure fallback, final safety net | ✓ WIRED | All 7 sites confirmed in file |
| `k8s_connector._enumerate_secret_types` | `scan_error='insufficient-rbac-privileges'` | `except Exception` with `getattr(exc, "status", None) == 403` | ✓ WIRED | Lines 304-316 |
| `evidence.py KUBERNETES elif` | `dar_k8s_inaccessible_count` | CR-01: `scan_err == "insufficient-rbac-privileges"` OR `scan_err == "encryption-config-inaccessible"` OR service_detail substring checks | ✓ WIRED | Lines 195-199: both scan_error checks + service_detail fallbacks |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `evidence.py:build_evidence_summary` | `dar_k8s_unencrypted_count` | `ep.service_detail` substring `/unencrypted` from KUBERNETES endpoints | Yes — pattern matches EKS/GKE live values | ✓ FLOWING |
| `evidence.py:build_evidence_summary` | `dar_k8s_inaccessible_count` | `ep.scan_error` field (CR-01 fix) + service_detail substrings | Yes — live connector shape now triggers counter | ✓ FLOWING |
| `scoring.py:compute_readiness_score` | `dar_k8s_unencrypted`, `dar_k8s_inaccessible` | `evidence.get("dar_k8s_unencrypted_count")`, `evidence.get("dar_k8s_inaccessible_count")` | Yes — passes through from evidence dict | ✓ FLOWING |
| `k8s_connector._enumerate_secret_types` | `type_counts` | `Counter(s.type or "Opaque" for s in secrets.items)` | Yes — only `s.type` accessed; property sentinel test confirms `s.data` never touched | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All 69 tests pass (full suite) | `python -m pytest tests/test_k8s_connector.py tests/test_dar_k8s_scoring.py tests/test_intelligence_evidence.py tests/test_intelligence_scoring.py tests/test_cbom_builder.py -x -q` | **69 passed in 0.58s** | ✓ PASS |
| `_enumerate_secret_types` emits correct service_detail | `grep -n 'service_detail="secret-types-summary"' quirk/scanner/k8s_connector.py` | Line 293 match | ✓ PASS |
| Old string retired from source and test files | `grep -r "K8S-SECRETS/types-enumerated" quirk/ tests/` | 0 matches | ✓ PASS |
| RBAC 403 increments inaccessible counter | `test_dar_k8s_inaccessible_count_rbac_403` with live `scan_error="insufficient-rbac-privileges"` fixture | PASS | ✓ PASS |
| AKS credential failure emits 2 inaccessible findings for 2 clusters | `test_aks_credential_failure_emits_inaccessible_per_cluster` | PASS | ✓ PASS |
| AKS credential failure with empty aks_clusters still emits 1 finding | `test_aks_credential_failure_no_clusters_still_emits_one_inaccessible` | PASS | ✓ PASS |
| `ConnectorsCfg()` instantiates with K8S defaults | `python -c "from quirk.config import ConnectorsCfg; c = ConnectorsCfg(); assert c.enable_k8s is False; assert c.gke_clusters == []"` | OK | ✓ PASS |
| `python -m compileall quirk/` | Clean compile | 0 errors | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| K8S-01 | 29-01, 29-02 | Scanner detects etcd encryption on EKS/GKE/AKS via managed cluster APIs; no direct etcd access | ✓ SATISFIED | `_scan_eks_encryption` (boto3), `_scan_gke_encryption` (GKE databaseEncryption.state), `_scan_aks_encryption` (AKS Key Vault KMS); 8 provider tests cover all three paths; CR-02 closes AKS credential failure gap |
| K8S-02 | 29-01, 29-02, 29-04 | Scanner enumerates K8S secret type counts without reading secret values | ✓ SATISFIED | `_enumerate_secret_types` accesses only `s.type`; `service_detail="secret-types-summary"` (CR-03 aligned to docs); sentinel test confirms invariant; 3 K8S-02 tests pass |
| K8S-03 | 29-01, 29-02, 29-04 | Explicit `encryption-config-inaccessible` finding emitted when etcd state unknowable | ✓ SATISFIED | `_emit_inaccessible_finding` at 7 call sites; all paths covered including AKS credential failure (CR-02); `test_unknown_provider_produces_inaccessible_finding` and `test_sdk_unavailable_produces_inaccessible_finding` pass; 2 AKS regression tests added |

No orphaned requirements. K8S-01/02/03 are the only Phase 29 requirements in REQUIREMENTS.md (traceability table confirmed). All three declared across Plans 01/02/03/04 and all satisfied.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None | — | No TODOs, FIXME, placeholder returns, or hardcoded empty values in source files | — | — |

Anti-pattern scan performed on: `quirk/scanner/k8s_connector.py`, `quirk/scanner/aws_connector.py` (EKS function), `quirk/intelligence/evidence.py`, `quirk/intelligence/scoring.py`, `quirk/cbom/builder.py`, `run_scan.py` (k8s block), `tests/test_k8s_connector.py`, `tests/test_dar_k8s_scoring.py`.

The `return []` patterns in `_scan_gke_encryption` (GKE SDK absent guard) and `_scan_aks_encryption` (AKS SDK absent guard) are intentional guards — the outer `scan_k8s_targets` wraps these with K8S-03 inaccessible-finding emission. Not stubs.

### Human Verification Required

Live cluster UAT (EKS/GKE/AKS) is documented in UAT-29-01/02/03 in `docs/UAT-SERIES.md` and `labs/kubernetes/expected_results.md` and is explicitly flagged "manual-only" (requires real cloud credentials). These are correctly deferred as live-cluster tests — not blockers for phase verification. All programmatically verifiable must-haves are confirmed VERIFIED.

### Gaps Summary

No gaps. Phase 29 goal is achieved.

All three BLOCKER gaps from the prior verification run are confirmed closed by plan 29-04:

**CR-01 (closed):** `evidence.py` KUBERNETES elif at line 191 now extracts `scan_err = str(getattr(ep, "scan_error", "") or "")` and checks `scan_err == "insufficient-rbac-privileges"` (line 195) alongside `scan_err == "encryption-config-inaccessible"`. The `dar_k8s_inaccessible_count` counter now fires correctly for live RBAC 403 findings. The false-green test `test_dar_k8s_inaccessible_count_rbac_403` is replaced with a live-shape fixture using `scan_error="insufficient-rbac-privileges"`.

**CR-02 (closed):** AKS `DefaultAzureCredential()` except block at lines 456-491 now loops over `aks_clusters` and calls `_emit_inaccessible_finding` once per configured cluster (with a single fallback when the list is empty). K8S-03 invariant is fully restored on the AKS credential-failure path. Two regression tests confirm: `test_aks_credential_failure_emits_inaccessible_per_cluster` (2 clusters → 2 findings) and `test_aks_credential_failure_no_clusters_still_emits_one_inaccessible`.

**CR-03 (closed):** `_enumerate_secret_types` at line 293 now emits `service_detail="secret-types-summary"`. The string `K8S-SECRETS/types-enumerated` is absent from all files under `quirk/` and `tests/` (0 matches). The connector test assertion (`test_secret_type_counts_basic` line 265) and the docs (UAT-SERIES.md, expected_results.md) are now aligned on one canonical value.

---

_Verified: 2026-04-26T14:00:00Z_
_Verifier: Claude (gsd-verifier)_
