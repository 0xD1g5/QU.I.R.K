---
phase: 29-kubernetes-secrets-inspection
reviewed: 2026-04-26T00:00:00Z
depth: standard
files_reviewed: 13
files_reviewed_list:
  - pyproject.toml
  - quirk/cbom/builder.py
  - quirk/config.py
  - quirk/config_template.yaml
  - quirk/intelligence/evidence.py
  - quirk/intelligence/scoring.py
  - quirk/scanner/aws_connector.py
  - quirk/scanner/k8s_connector.py
  - run_scan.py
  - tests/test_dar_k8s_scoring.py
  - tests/test_k8s_connector.py
  - labs/kubernetes/expected_results.md
  - docs/UAT-SERIES.md
findings:
  critical: 3
  warning: 4
  info: 2
  total: 9
status: issues_found
---

# Phase 29: Code Review Report

**Reviewed:** 2026-04-26T00:00:00Z
**Depth:** standard
**Files Reviewed:** 13
**Status:** issues_found

## Summary

Phase 29 introduces Kubernetes secrets inspection (K8S-01/K8S-02/K8S-03) across EKS, GKE, and AKS,
plus corresponding evidence counter and scoring additions. The connector logic, SDK import guards,
and security invariants (no secret.data access, no credential leakage to logs) are structurally
sound. However three blockers prevent correct behavior in production:

1. The `rbac-403` evidence counter never fires because the scanner emits `"insufficient-rbac-privileges"` in `scan_error`, not `"rbac-403"` in `service_detail` — the substring the counter actually checks.
2. AKS Azure credential failure silently drops the AKS K8S-01 scan without emitting the required K8S-03 inaccessible finding, violating the stated invariant.
3. The `service_detail` value emitted by `_enumerate_secret_types` (`"K8S-SECRETS/types-enumerated"`) disagrees with the value documented in expected_results.md and UAT-SERIES.md (`"secret-types-summary"`), meaning the test that uses `"secret-types-summary"` passes against the wrong string and the live UAT assertion fails.

---

## Critical Issues

### CR-01: `rbac-403` Evidence Counter Never Fires — Evidence Mis-count

**File:** `quirk/intelligence/evidence.py:194-196`
**Issue:** The KUBERNETES branch checks `"rbac-403" in sd` where `sd` is `service_detail`. But
`_enumerate_secret_types` (k8s_connector.py line 308-316) sets `scan_error="insufficient-rbac-privileges"`
and `service_detail="Remediation: RBAC role requires get,list on secrets in namespace '...'"`.
The substring `"rbac-403"` does not appear in that service_detail string. As a result,
`dar_k8s_inaccessible_count` is never incremented for 403 findings, silently under-reporting
the RBAC access gap.

The scoring test `test_dar_k8s_inaccessible_count_rbac_403` in test_dar_k8s_scoring.py (line 57-60)
constructs a synthetic endpoint with `service_detail="rbac-403"` directly, so it passes — but it
does not match the string the live connector actually emits.

**Fix:** Either update the evidence counter to also check `scan_error`, or change the service_detail
string emitted on the 403 path to include the literal substring `"rbac-403"`. The cleanest fix is
to add a `scan_error` check:

```python
elif proto == "KUBERNETES":
    sd = str(getattr(ep, "service_detail", "") or "")
    scan_err = str(getattr(ep, "scan_error", "") or "")
    if "/unencrypted" in sd:
        dar_k8s_unencrypted_count += 1
    elif ("encryption-config-inaccessible" in sd
          or "encryption-config-inaccessible" in scan_err
          or "/platform-managed" in sd
          or "rbac-403" in sd
          or scan_err == "insufficient-rbac-privileges"):
        dar_k8s_inaccessible_count += 1
```

---

### CR-02: AKS Credential Failure Silently Violates K8S-03 Invariant

**File:** `quirk/scanner/k8s_connector.py:452-467`
**Issue:** When `DefaultAzureCredential()` raises an exception on the AKS path, `credential` is
set to `None`, a log message is emitted, and `_scan_aks_encryption` is skipped. No inaccessible
finding is emitted for the configured AKS clusters. If the GKE scan or secret enumeration later
produces results, `results` is non-empty and the final K8S-03 safety net at line 495 does not
fire — so the AKS cluster's encryption state is silently unknown.

The K8S-03 invariant documented in the module docstring says "NEVER returns empty list silently"
and "every scan call produces at least one CryptoEndpoint." That invariant is per-cluster, not
just per-call; AKS clusters with credential failures produce zero findings.

**Fix:** Emit an inaccessible finding for each configured AKS cluster when the credential fails:

```python
except Exception as exc:
    credential = None
    if logger:
        logger.v(f"Azure credential unavailable: {exc}")
    # K8S-03: credential failure must produce inaccessible findings, not silent skips
    for cfg_item in (aks_clusters or []):
        results.append(_emit_inaccessible_finding(
            provider="aks",
            cluster_name=cfg_item.get("name", "unknown"),
            reason=f"Azure credential unavailable: {type(exc).__name__}",
            session_start=session_start,
        ))
```

---

### CR-03: `service_detail` Value Inconsistency — Test Passes Against Wrong String

**File:** `quirk/scanner/k8s_connector.py:293` vs `tests/test_dar_k8s_scoring.py:75` vs
`labs/kubernetes/expected_results.md:90` vs `docs/UAT-SERIES.md:1781`

**Issue:** `_enumerate_secret_types` emits `service_detail="K8S-SECRETS/types-enumerated"` (connector
line 293). The scoring test `test_dar_k8s_secret_types_summary_neutral` (test_dar_k8s_scoring.py line 75)
creates an endpoint with `service_detail="secret-types-summary"` and asserts it is neutral. Because
no evidence counter checks for `"K8S-SECRETS/types-enumerated"` and none checks for `"secret-types-summary"`,
both pass the neutral assertion — but for the wrong reason: the test exercises a string that the
live connector never emits, making it a false-green coverage claim.

Meanwhile UAT-SERIES.md line 1781 and labs/kubernetes/expected_results.md line 90 document that the
expected `service_detail` is `"secret-types-summary"`, which means live UAT assertions against the
actual DB will fail when checking for that string.

This is a documentation-code contract break: either the connector must be updated to emit
`"secret-types-summary"`, or all documentation references must be updated to `"K8S-SECRETS/types-enumerated"`.
The test in test_k8s_connector.py line 265 asserts `"K8S-SECRETS/types-enumerated"` — so that test
aligns with the code, but the scoring test and all user-facing docs do not.

**Fix (prefer): change the connector** to match the documented, user-visible value:

```python
# k8s_connector.py line 293
service_detail="secret-types-summary",
```

Then update test_k8s_connector.py line 265 to match:
```python
assert ep.service_detail == "secret-types-summary"
```

---

## Warnings

### WR-01: GKE Cluster YAML Config `project` Key Silently Ignored — Documentation Mismatch

**File:** `labs/kubernetes/expected_results.md:44-48` vs `quirk/scanner/k8s_connector.py:125-128`

**Issue:** `expected_results.md` and the template YAML in the docs show GKE cluster configs with a
per-cluster `project` key:

```yaml
gke_clusters:
  - project: my-gcp-project
    location: us-central1
    name: my-gke-cluster
```

But `_scan_gke_encryption` never reads `cfg["project"]` — it uses only `cfg["location"]` and
`cfg["name"]`, building the path from the top-level `project_id` parameter. Users who follow the
documented YAML will place their project in the `project` key, which is silently dropped. This
means multi-project GKE scans (where different clusters belong to different GCP projects) are
impossible to express even though the YAML schema implies they are supported.

**Fix:** Either (a) read `cfg.get("project") or project_id` in `_scan_gke_encryption` to support
per-cluster project overrides, or (b) remove the `project` key from all documentation to avoid
misleading users.

---

### WR-02: AKS Cluster YAML Config `subscription_id` Key Silently Ignored

**File:** `labs/kubernetes/expected_results.md:55-61` vs `quirk/scanner/k8s_connector.py:212-217`

**Issue:** `expected_results.md` documents AKS cluster entries with a `subscription_id` field:

```yaml
aks_clusters:
  - subscription_id: <azure-subscription-uuid>
    resource_group: my-rg
    name: my-aks-cluster
```

But `_scan_aks_encryption` calls `aks_client.managed_clusters.get(resource_group_name=cfg["resource_group"], resource_name=cfg["name"])` — it never reads `cfg["subscription_id"]`. The `ContainerServiceClient` is constructed with the global `subscription_id` parameter only. So if an AKS cluster is in a different subscription from the global setting, the per-cluster `subscription_id` has no effect.

**Fix:** Either read `cfg.get("subscription_id") or subscription_id` when constructing the per-cluster
client, or remove the `subscription_id` field from the documentation.

---

### WR-03: Mutable Default Argument Type Annotation Error in `scan_k8s_targets`

**File:** `quirk/scanner/k8s_connector.py:366-367`

**Issue:** The function signature uses:

```python
gke_clusters: list = None,
aks_clusters: list = None,
```

The type annotation `list` with a default of `None` is a type error — `None` is not a `list`. While
Python does not enforce this at runtime and the code defensively uses `gke_clusters or []` everywhere,
a type checker will flag these as `Optional[list]` mismatches and static analysis tools will reject them.

**Fix:** Use `Optional[list]` with `None` default:

```python
gke_clusters: Optional[list] = None,
aks_clusters: Optional[list] = None,
```

`Optional` is already imported at line 27.

---

### WR-04: EKS Encryption Not Scanned When Only `enable_aws` Is True

**File:** `quirk/scanner/aws_connector.py:416-444` / `run_scan.py:472-478`

**Issue:** `scan_aws_targets` (the function called when `enable_aws=true`) enumerates KMS, CloudFront,
ELBv2, ACM, and RDS — but does NOT call `_scan_eks_encryption`. EKS encryption scanning only
happens when `enable_k8s=true` and `k8s_provider=eks` (run_scan.py lines 595-611). A user who enables
AWS scanning but not the K8S connector (a very natural configuration when they are not aware of the
K8S connector) will silently miss EKS cluster encryption posture. This is never mentioned in the
config template or documentation.

**Fix:** Document this explicitly in `quirk/config_template.yaml` under the K8S section:

```yaml
# NOTE: EKS etcd encryption inspection requires enable_k8s: true with k8s_provider: eks
# even when enable_aws: true is already set. The AWS connector (enable_aws) does not scan
# EKS cluster encryption — that is handled by the Kubernetes connector.
```

---

## Info

### IN-01: Total Readiness Score Can Exceed 100

**File:** `quirk/intelligence/scoring.py:187`

**Issue:** `total_score` is the sum of five subscores each individually clamped to `[0, 25]`. The
maximum theoretical total is 125 (all five subscores at 25). No final clamp is applied to
`total_score`. The `_rating` function treats scores above 85 as "EXCELLENT" without a ceiling check,
so a score of 125 would be rated "EXCELLENT" rather than an anomaly. This is a pre-existing pattern,
not introduced in Phase 29, but the addition of the `data_at_rest` subscore increases the real-world
range.

**Fix:** Apply a final clamp after summing subscores:

```python
total_score = _clamp(
    int(hygiene_score + modern_tls_score + identity_trust_score + agility_score + dar_score),
    0,
    100,
)
```

---

### IN-02: UAT Pass Criteria Count May Be Stale

**File:** `docs/UAT-SERIES.md:1787-1788`

**Issue:** UAT-29-01 pass criteria states "`python -m pytest tests/test_k8s_connector.py` — 15 passed"
and "`python -m pytest tests/test_dar_k8s_scoring.py` — 12 passed". The test count should be
verified against the actual number of tests in each file; if CR-01 fixes add new tests for the
`insufficient-rbac-privileges` evidence path, these counts will be stale.

**Fix:** After addressing CR-01, recount and update the pass criteria numbers in UAT-SERIES.md.

---

_Reviewed: 2026-04-26T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
