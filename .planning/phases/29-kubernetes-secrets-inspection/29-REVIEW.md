---
phase: 29-kubernetes-secrets-inspection
reviewed: 2026-04-26T00:00:00Z
depth: standard
files_reviewed: 10
files_reviewed_list:
  - docs/UAT-SERIES.md
  - labs/kubernetes/expected_results.md
  - quirk/cbom/builder.py
  - quirk/intelligence/evidence.py
  - quirk/intelligence/scoring.py
  - quirk/scanner/aws_connector.py
  - quirk/scanner/k8s_connector.py
  - run_scan.py
  - tests/test_dar_k8s_scoring.py
  - tests/test_k8s_connector.py
findings:
  critical: 0
  warning: 6
  info: 4
  total: 10
status: issues_found
---

# Phase 29: Code Review Report

**Reviewed:** 2026-04-26
**Depth:** standard
**Files Reviewed:** 10
**Status:** issues_found

## Summary

Phase 29 delivers Kubernetes Secrets Inspection (K8S-01 through K8S-03) across EKS, GKE, and AKS
providers, integrating etcd-encryption detection, secret-type enumeration, RBAC-degradation
handling, and DAR scoring. The security invariants (no secret.data read, no silent empty return)
are correctly enforced by the connector. No critical security vulnerabilities were found.

Six warnings and four info items are identified. The most impactful are:
- A dead condition in the evidence counter (`"rbac-403" in sd`) that can never match real
  connector output, creating a documentation-to-code contract gap (WR-01).
- Live UAT test documentation (`UAT-29-03`) asserting a `service_detail` value
  (`rbac-403`) the connector never emits, which will cause false FAIL results during
  live-cluster testing (WR-03).
- Two per-cluster YAML config fields (`project` in GKE, `subscription_id` in AKS) that are
  documented in `expected_results.md` but silently ignored by the connector (WR-04, WR-05).

---

## Warnings

### WR-01: Dead condition `"rbac-403" in sd` in evidence counter will never match

**File:** `quirk/intelligence/evidence.py:199`
**Issue:** The `elif` branch that increments `dar_k8s_inaccessible_count` includes
`or "rbac-403" in sd` as one of its conditions, where `sd` is `service_detail`. The
connector's RBAC-403 path (`k8s_connector.py:305-315`) emits:
- `scan_error="insufficient-rbac-privileges"`
- `service_detail="Remediation: RBAC role requires get,list on secrets in namespace '...'"` 

The string `"rbac-403"` never appears in that `service_detail`. The condition is dead code
for any real connector output.

The evidence counter does correctly catch the RBAC-403 case via the first condition
(`scan_err == "insufficient-rbac-privileges"`, line 195), so the counter logic works for
actual connector output. But the dead `"rbac-403"` substring condition misrepresents the
actual tested behavior, causes confusion about what values are expected, and is inconsistent
with the "synthetic-fixture cases" justification in the comment (no such fixtures exist in
the test suite).

**Fix:** Remove the dead substring condition and update the comment:
```python
elif (scan_err == "insufficient-rbac-privileges"
      or scan_err == "encryption-config-inaccessible"
      or "encryption-config-inaccessible" in sd
      or "/platform-managed" in sd):
    dar_k8s_inaccessible_count += 1
```

---

### WR-02: UAT-SERIES.md `Gate Status` line still references v4.2, not v4.3

**File:** `docs/UAT-SERIES.md:6,94`
**Issue:** The document header was updated to `**Version:** 4.3.0` but two lines were missed:
- Line 6: `"This document is the **release gate** for QU.I.R.K. v4.2."` — version not bumped.
- Line 94: Pass criteria for UAT-1-02 still asserts `quirk 4.2.0` or `QU.I.R.K. v4.2.0`.

A tester running UAT-1-02 against v4.3.0 will see `QU.I.R.K. v4.3.0` in the version output and
mark the test FAIL because the pass criteria specifies `v4.2.0`.
**Fix:**
- Line 6: Replace `v4.2` with `v4.3`.
- Line 94: Replace `4.2.0` with `4.3.0` in both version string variants.

---

### WR-03: UAT-29-03 pass criteria reference `service_detail=rbac-403` that the connector never emits

**File:** `docs/UAT-SERIES.md:1867,1874`
**Issue:** The UAT-29-03 test case documents two assertions that will always fail during live testing:
- Line 1867: `"One secret-types-summary row replaced by service_detail=rbac-403"`
- Line 1874: `"Live path (limited creds): rbac-403 row present"`

The connector emits `scan_error="insufficient-rbac-privileges"` with a remediation-text
`service_detail` on the RBAC-403 path — it never sets `service_detail` to the string `"rbac-403"`.
A tester querying the database for `service_detail='rbac-403'` will find zero rows and incorrectly
mark the test as FAIL.
**Fix:** Update both lines in UAT-29-03 to describe what the connector actually emits:
```
Expected (limited-permission run):
- One KUBERNETES row with scan_error=insufficient-rbac-privileges and service_detail
  containing "Remediation: RBAC role requires get,list on secrets in namespace 'default'"
- dar_k8s_inaccessible_count increments by 1
- No unhandled exception traceback in logs (graceful K8S-03 degradation)

Pass Criteria:
- Live path (limited creds): KUBERNETES row with scan_error=insufficient-rbac-privileges
  present; dar_k8s_inaccessible_count == 1; no traceback
```

---

### WR-04: GKE cluster YAML `project` key is silently ignored by the connector

**File:** `labs/kubernetes/expected_results.md:44-50` and `quirk/scanner/k8s_connector.py:124-128`
**Issue:** The documented GKE config YAML shows a per-cluster `project` key:
```yaml
gke_clusters:
  - project: my-gcp-project
    location: us-central1
    name: my-gke-cluster
```
`_scan_gke_encryption` builds the cluster path using only `cfg['location']` and `cfg['name']`;
it never reads `cfg['project']`. The GCP project comes exclusively from the top-level
`gcp_project_id` parameter. Users who supply different projects per cluster (e.g., multi-project
GKE environments) will have their per-cluster `project` key silently dropped and all clusters
scanned as if they belong to the single `gcp_project_id`. No error or warning is emitted.
**Fix:** Either (a) read `cfg.get("project") or project_id` in the cluster path construction to
support per-cluster project override:
```python
effective_project = cfg.get("project") or project_id
cluster_name_path = (
    f"projects/{effective_project}/locations/{cfg['location']}"
    f"/clusters/{cfg['name']}"
)
```
or (b) remove the `project` key from all YAML examples and document that only the top-level
`gcp_project_id` is used.

---

### WR-05: AKS cluster YAML `subscription_id` key is silently ignored by the connector

**File:** `labs/kubernetes/expected_results.md:57-63` and `quirk/scanner/k8s_connector.py:211-216`
**Issue:** The documented AKS config YAML shows a per-cluster `subscription_id` field:
```yaml
aks_clusters:
  - subscription_id: <azure-subscription-uuid>
    resource_group: my-rg
    name: my-aks-cluster
```
`_scan_aks_encryption` accesses only `cfg["resource_group"]` and `cfg["name"]` from each entry.
The `ContainerServiceClient` is constructed with the global `subscription_id` parameter only.
Per-cluster `subscription_id` has no effect. Multi-subscription AKS scans cannot be expressed
even though the YAML schema implies they can.
**Fix:** Either (a) read `cfg.get("subscription_id") or subscription_id` and construct a new
client per cluster when the subscription differs, or (b) remove `subscription_id` from the AKS
cluster entry docs and note that only the global `azure_subscription_id` is used.

---

### WR-06: `test_dar_score_includes_k8s_drivers` uses fragile driver-extraction logic

**File:** `tests/test_dar_k8s_scoring.py:125`
**Issue:** The test extracts driver label text with:
```python
labels = " ".join(d[0] if isinstance(d, (list, tuple)) else str(d)
                  for d in score.get("drivers", []))
```
`scoring.py` returns `drivers` as a list of dicts `{"reason": ..., "points": ...}`, not tuples.
For each dict, `isinstance(d, (list, tuple))` is `False`, so `str(d)` is called — producing the
full dict repr string. The assertion `"Kubernetes" in labels` passes only because the word
`Kubernetes` happens to appear in that string. This is brittle: any change to the dict key name
(`"reason"` to `"label"`) would silently leave the test passing while extracting no meaningful
text. Additionally, `d[0]` on a Python dict returns the first key (`"reason"`), not the first
value — the `isinstance` guard hides a latent wrong-value bug if the drivers format ever changes
back to tuples.
**Fix:**
```python
labels = " ".join(
    d.get("reason", "") if isinstance(d, dict) else str(d)
    for d in score.get("drivers", [])
)
assert "Kubernetes" in labels or "etcd" in labels
```

---

## Info

### IN-01: Vacuous assertion in `test_dar_k8s_secret_types_summary_neutral` tests nothing

**File:** `tests/test_dar_k8s_scoring.py:103`
**Issue:** The "sanity" assertion is always True and tests nothing:
```python
assert "KUBERNETES" in summary.get("protocols", {}) or summary["dar_k8s_unencrypted_count"] == 0
```
`summary` has no key `"protocols"` — the correct key is `"protocol_counts"`. So
`summary.get("protocols", {})` always returns `{}`, `"KUBERNETES" in {}` is always `False`,
and the assertion reduces to `summary["dar_k8s_unencrypted_count"] == 0` — which was already
asserted on line 100. This line adds zero coverage.
**Fix:** Replace with a meaningful check:
```python
assert summary["protocol_counts"].get("KUBERNETES", 0) == 1
```

---

### IN-02: EKS encryption is silently skipped when only `enable_aws: true` is set

**File:** `run_scan.py:595-611` and `quirk/scanner/aws_connector.py:416-444`
**Issue:** `scan_aws_targets` (invoked when `enable_aws=true`) does NOT call
`_scan_eks_encryption`. EKS cluster encryption scanning only happens when
`enable_k8s: true` AND `k8s_provider: eks` are both configured. A user who enables the AWS
connector but not the K8S connector will silently receive no EKS encryption posture data,
which is counterintuitive given that EKS is an AWS service. This behavior is undocumented
in `expected_results.md` and UAT-SERIES.md.
**Fix:** Add a prominent note to the EKS scanner configuration section in
`labs/kubernetes/expected_results.md` and to UAT-29-01:
```
NOTE: EKS etcd encryption inspection (K8S-01) requires enable_k8s: true with
k8s_provider: eks. Setting enable_aws: true alone does not scan EKS cluster
encryption — the AWS connector covers ACM, KMS, CloudFront, ELBv2, and RDS only.
```

---

### IN-03: GKE/AKS cluster config `KeyError` on malformed entries produces confusing error messages

**File:** `quirk/scanner/k8s_connector.py:126-127` and `214-216`
**Issue:** `_scan_gke_encryption` accesses `cfg['location']` and `cfg['name']` with bracket
notation. A malformed config entry missing either key raises `KeyError`. The inner
`except Exception` at line 161 catches it, but the log message uses
`cfg.get('name', '?')` — which may itself return `'?'` if `'name'` is the missing key —
producing a confusing `"GKE cluster scan error for ?: KeyError: 'name'"` log. Same pattern
in `_scan_aks_encryption` for `cfg['resource_group']` and `cfg['name']`.
**Fix:** Add early validation before the inner loop:
```python
location = cfg.get("location", "")
name = cfg.get("name", "")
if not location or not name:
    if logger:
        logger.v(f"GKE cluster config missing required keys: {list(cfg.keys())!r}")
    continue
```

---

### IN-04: `aws_connector._scan_eks_encryption` reads KMS key ARN from `enc_cfg[0]` regardless of which entry encrypts secrets

**File:** `quirk/scanner/aws_connector.py:166-169`
**Issue:** When `encryptionConfig` contains multiple entries and secrets are encrypted, the KMS
key ARN is always taken from `enc_cfg[0].get("provider", {}).get("keyArn", "")` regardless of
which entry matches `resources=['secrets']`. If the secrets-encrypting entry is not at index 0,
the `service_detail` string records the wrong KMS key ARN. The severity classification is still
correct, but the recorded key ARN will be inaccurate.
**Fix:** Extract the ARN from the matched entry, not always index 0:
```python
secrets_entry = next(
    (e for e in enc_cfg if "secrets" in (e.get("resources") or [])),
    enc_cfg[0],
)
kms_key = secrets_entry.get("provider", {}).get("keyArn", "")
service_detail = f"EKS/encrypted:{kms_key}"
```

---

_Reviewed: 2026-04-26_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
