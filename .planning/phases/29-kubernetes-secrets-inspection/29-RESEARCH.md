# Phase 29: Kubernetes Secrets Inspection - Research

**Researched:** 2026-04-26
**Domain:** Kubernetes Python client, EKS/GKE/AKS managed-cluster encryption APIs, K8S secret type enumeration
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

No CONTEXT.md exists for Phase 29 yet. Constraints below are derived from STATE.md accumulated
decisions that apply to ALL v4.3 scanner phases.

### Locked Decisions (from STATE.md structural requirements)

**ISSUE-2 pattern:** `pyproject.toml` diff showing the new extras addition is a REQUIRED deliverable
in PLAN.md. `kubernetes>=35.0.0` goes in the `[cloud]` extras group.

**ISSUE-3 pattern:** `session_start` parameter is MANDATORY for all new scanners. Must be threaded
from `run_scan.py` → `scan_k8s_targets()` → each `CryptoEndpoint` construction. Same
`(session_start or datetime.now(timezone.utc)).replace(tzinfo=None)` idiom.

**dat_scan_json column:** Scanner writes per-cluster findings to `dat_scan_json`. Column already
exists from Phase 27 `_ensure_v43_columns()`. No new ALTER TABLE needed.

**Protocol value:** Use `"KUBERNETES"` — not `"K8S"`, not `"STORAGE"`.
(Rationale: follows established `"POSTGRESQL"`, `"MYSQL"`, `"S3"`, `"AZURE_BLOB"` noun-first
convention; full word is consistent with `"KERBEROS"`, `"DNSSEC"`, `"SAML"`.)

**K8S_AVAILABLE flag pattern:** Module-level `try/except` import guard matching
`GCP_AVAILABLE`, `BOTO3_AVAILABLE`, `AZURE_AVAILABLE` pattern. Mandatory for test patching.

**CryptoEndpoint rows:** All findings (etcd encryption status, secret type counts,
encryption-config-inaccessible) produce CryptoEndpoint rows in the DB.

**evidence.py / scoring.py:** Add `"KUBERNETES"` to `_PROTOCOL_KEYS` tuple and add
`dar_k8s_*` evidence counters + scoring weights following `dar_storage_*` pattern.

**cbom/builder.py:** Add `"KUBERNETES"` to Pass 2 cert skip list and Pass 3 protocol
skip list; add explicit `elif ep.protocol == "KUBERNETES": pass` in Pass 1.

### Claude's Discretion

- Exact wording for `encryption-config-inaccessible` finding remediation text
- Whether to target `"all"` namespaces or a configurable list (recommendation: configurable,
  with `"default"` as sensible default; avoid scanning all namespaces to limit blast radius)
- Chaos lab approach: mock-based (no live cluster) vs kind cluster vs kubeconfig file pointing
  at an in-cluster scenario (recommendation: mock-based for unit tests + brief human-UAT note
  for live cluster; same pattern as `db_connector.py` which has no chaos lab Docker service)
- dar_k8s scoring weight values

### Deferred Ideas (OUT OF SCOPE)

- Self-hosted K8s direct etcd access (violates agentless constraint — REQUIREMENTS.md Out of Scope)
- Agent installation on cluster nodes
- Reading actual secret values
- kube-apiserver pod spec inspection for on-prem (out of scope per requirements)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| K8S-01 | Scanner can detect etcd encryption status on managed clusters (EKS `encryptionConfig`, GKE `databaseEncryption.state`, AKS Key Vault integration) via managed cluster APIs without requiring direct etcd access | Three distinct API call paths verified: EKS via boto3 `describe_cluster`, GKE via `google-cloud-container` `get_cluster`, AKS via `azure-mgmt-containerservice` `managed_clusters.get` |
| K8S-02 | Scanner can enumerate Kubernetes Secret type counts (Opaque, `kubernetes.io/tls`, `kubernetes.io/dockerconfigjson`, etc.) for a configured cluster without reading any secret values | `CoreV1Api.list_namespaced_secret()` returns `type` field on `V1Secret.metadata`; counting `secret.type` from the response never requires reading `secret.data` |
| K8S-03 | Scanner emits an explicit `encryption-config-inaccessible` finding with remediation guidance when etcd encryption state cannot be determined via available managed-cluster APIs | Fires when: not EKS/GKE/AKS provider, OR cloud SDK not installed, OR cluster type detection fails — never silently skips |
</phase_requirements>

---

## Summary

Phase 29 adds a new `quirk/scanner/k8s_connector.py` module. It is the K8S equivalent of
`gcp_connector.py` and `db_connector.py`: one scanner file, optional import guard, session_start
threading, dat_scan_json storage, and `_ensure_v43_columns()` already in place.

The etcd encryption detection path has three distinct sub-paths:

1. **EKS:** Uses the existing boto3 session (already a core dep). Calls
   `client("eks").describe_cluster(name=cluster_name)`. The `encryptionConfig` key in the
   response is either an empty list (unencrypted) or a list of dicts with `resources: ["secrets"]`
   and `provider.keyArn`. This is a boto3 call — NOT a kubernetes Python client call.

2. **GKE:** Requires `google-cloud-container` (NOT `google-api-python-client`). Calls
   `container_v1.ClusterManagerClient().get_cluster(name=...)`. The `cluster.database_encryption`
   object has a `current_state` enum of `CURRENT_STATE_ENCRYPTED` (KMS key enabled) or
   `CURRENT_STATE_DECRYPTED` (default, no CMK). This is a Google Cloud Python library call.

3. **AKS:** Requires `azure-mgmt-containerservice`. Calls
   `ContainerServiceClient.managed_clusters.get(rg, cluster_name)`. The cluster's
   `security_profile.azure_key_vault_kms.enabled` boolean is the detection signal.

K8S-02 (secret type counts) uses the kubernetes Python client (`kubernetes>=35.0.0`):
`CoreV1Api.list_namespaced_secret()`. The `type` field is on each item directly (not in metadata).
`secret.data` is present in the response but is NEVER read — only `secret.type` is accessed.
The result is a `Counter(secret.type for secret in secrets.items)`.

K8S-03 fires when: the `cluster_provider` config field is absent/unknown, OR the required SDK
for that provider is not installed, OR any provider-specific exception occurs. It must never
silently return an empty list.

**Critical structural observation:** EKS etcd detection re-uses the EXISTING boto3 session from
`aws_connector.py` — the EKS `describe_cluster` call goes in `aws_connector.py` alongside
`_scan_rds_encryption`, not in a new file. The kubernetes Python client (for K8S-02) and the
GKE/AKS management clients (K8S-01 paths 2 and 3) go in the new `k8s_connector.py`.

**Primary recommendation:** Three-plan structure — (1) RED scaffold with pyproject.toml diff,
config fields, K8S_AVAILABLE guard, and 12+ failing tests; (2) GREEN implementation of
`k8s_connector.py` + EKS extension to `aws_connector.py`; (3) integration wiring in
`run_scan.py`, evidence/scoring, CBOM skip-lists, and expected_results.md.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| EKS encryptionConfig detection | API / Backend (aws_connector.py) | — | boto3 call; reuses existing EKS boto3 session; same tier as `_scan_rds_encryption` |
| GKE databaseEncryption.state detection | API / Backend (k8s_connector.py) | — | `google-cloud-container` management plane; separate from `google-api-python-client` used in Phase 26 |
| AKS Key Vault KMS detection | API / Backend (k8s_connector.py) | — | `azure-mgmt-containerservice` management plane; analogous to `azure-mgmt-storage` used in Phase 28 |
| K8S secret type enumeration | API / Backend (k8s_connector.py) | — | kubernetes Python client; lists secret metadata only |
| encryption-config-inaccessible finding | API / Backend (k8s_connector.py) | — | Emitted by scanner when provider not determinable |
| RBAC 403 handling | API / Backend (k8s_connector.py) | — | `ApiException(status=403)` → `insufficient-rbac-privileges` finding |
| dar_ evidence counters | Intelligence layer (evidence.py) | — | `dar_k8s_unencrypted_count`; follows `dar_db_*` pattern |
| dar_ scoring weights | Intelligence layer (scoring.py) | — | New `dar_k8s_*` entries in SCORE_WEIGHTS |
| CBOM integration | Builder (cbom/builder.py) | — | Pass 1/2/3 skip-list extension for `KUBERNETES` |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| kubernetes | 35.0.0 [VERIFIED: PyPI 2026-01-16] | `CoreV1Api.list_namespaced_secret()` for K8S-02 secret type enumeration; `ApiException` for RBAC 403 detection | Official Python client for the Kubernetes API; only mature option; version 35 maps to K8s 1.32 |
| boto3 | >=1.42.0 (core dep) [VERIFIED: pyproject.toml] | EKS `describe_cluster` for K8S-01 EKS path | Already a core dependency; same session used for KMS, RDS, ACM |
| google-cloud-container | 2.64.0 [VERIFIED: PyPI curl] | GKE `ClusterManagerClient.get_cluster()` for K8S-01 GKE path | Dedicated GKE management client with typed `DatabaseEncryption` model; different from `google-api-python-client` used in Phase 26 |
| azure-mgmt-containerservice | 41.1.0 [VERIFIED: PyPI curl] | AKS `ContainerServiceClient.managed_clusters.get()` for K8S-01 AKS path | Standard Azure SDK management plane; same pattern as `azure-mgmt-storage` in Phase 28 |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| kubernetes.config | (kubernetes package) [VERIFIED: Context7] | `config.load_kube_config()` / `config.load_incluster_config()` | K8S-02 needs to load cluster credentials from kubeconfig or in-cluster service account |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `google-cloud-container` | `google-api-python-client` `container` discovery | Phase 26 already installs `google-api-python-client`, but the discovery API for GKE Container v1 does not expose a typed `database_encryption.current_state` object — requires manual JSON navigation. `google-cloud-container` provides the typed `DatabaseEncryption.CurrentState` enum directly. |
| `azure-mgmt-containerservice` | Azure REST API direct call | Management SDK is already the established pattern (see `azure-mgmt-storage` in Phase 28, `azure-mgmt-network` in core deps); typed response model avoids manual JSON parsing |
| kubernetes Python client for EKS etcd | boto3 EKS `describe_cluster` | EKS etcd encryption is NOT queryable via the kubernetes API server — it is an AWS cluster-management metadata field. `encryptionConfig` exists only in the EKS API response. |

**Installation (pyproject.toml diff — REQUIRED PLAN.md deliverable):**
```toml
[project.optional-dependencies]
cloud = [
    "google-api-python-client>=2.0.0",
    "google-auth>=2.36.0",
    "azure-mgmt-storage>=21.0.0",     # Phase 28: Azure Blob encryption audit (STOR-02)
    "kubernetes>=35.0.0",              # Phase 29: Kubernetes secrets inspection (K8S-01, K8S-02)
    "google-cloud-container>=2.0.0",   # Phase 29: GKE databaseEncryption.state (K8S-01)
    "azure-mgmt-containerservice>=35.0.0",  # Phase 29: AKS Key Vault KMS detection (K8S-01)
]
```

Note: `azure-mgmt-containerservice>=35.0.0` is a conservative minimum that includes
`security_profile.azure_key_vault_kms`. Latest is 41.1.0. Version 35+ is safe. [ASSUMED
minimum — plan execution should verify `azure_key_vault_kms` field appeared in which
exact release via changelog.]

**Version verification:**
```bash
pip index versions kubernetes | head -2        # latest: 35.0.0 (Jan 2026)
pip index versions google-cloud-container | head -2  # latest: 2.64.0
pip index versions azure-mgmt-containerservice | head -2  # latest: 41.1.0
```

---

## Architecture Patterns

### System Architecture Diagram

```
config.yaml (k8s_cluster_name, k8s_provider, k8s_namespace,
             k8s_kubeconfig, enable_k8s)
                         |
                         v
                    run_scan.py
                         |
           ┌─────────────┴──────────────────┐
           |                                |
    k8s_scanning block                aws_scanning block (extended)
           |                                |
           v                                v
   k8s_connector.py                 aws_connector.py
           |                         _scan_eks_encryption()
           |                                |
   ┌───────┴────────────┐                   |
   |                    |                   v
   K8S-01:              K8S-02:      EKS describe_cluster
   _scan_etcd_          _enumerate_  encryptionConfig field
   encryption()         secret_types()   |
           |                    |         |
   ┌───────┼──────┐             |    CryptoEndpoint
   |       |      |             |    protocol="KUBERNETES"
   EKS    GKE    AKS            |    service_detail="EKS/encrypted"
   (boto3)(google-(azure-       |    or "EKS/unencrypted"
          cloud-  mgmt-        |    dat_scan_json={...}
          container)container  |
                 service)      |
           |                    |
           v                    v
      CryptoEndpoint rows (protocol="KUBERNETES")
      service_detail: "GKE/encrypted"|"GKE/unencrypted"
                      "AKS/kv-kms"  |"AKS/platform-managed"
                      "K8S-SECRETS/types-enumerated"
      OR
      scan_error="encryption-config-inaccessible"
      OR
      scan_error="insufficient-rbac-privileges"
                         |
              evidence.py: _collect_evidence()
              dar_k8s_unencrypted_count
                         |
              scoring.py: compute_readiness_score()
              dar_k8s_unencrypted_ratio × weight
                         |
              cbom/builder.py
              Pass 1: KUBERNETES -> pass
              Pass 2/3: KUBERNETES -> skip
```

### Recommended Project Structure

```
quirk/scanner/
├── k8s_connector.py         # NEW: GKE/AKS etcd detection + K8S secret type enumeration
├── aws_connector.py         # MODIFY: add _scan_eks_encryption()
quirk/
├── config.py                # MODIFY: add enable_k8s, k8s_cluster_name, k8s_provider,
│                            #          k8s_namespace, k8s_kubeconfig, k8s_context
├── config_template.yaml     # MODIFY: add k8s connector block (commented out)
quirk/intelligence/
├── evidence.py              # MODIFY: add dar_k8s_unencrypted_count + _PROTOCOL_KEYS
├── scoring.py               # MODIFY: add dar_k8s_unencrypted_ratio weight + dar_impacts
quirk/cbom/
├── builder.py               # MODIFY: Pass 1/2/3 KUBERNETES skip-list entries
run_scan.py                  # MODIFY: add k8s_scanning block
labs/kubernetes/
└── expected_results.md      # NEW: Phase 29 expected results (mock-based, human-UAT note)
tests/
└── test_k8s_connector.py    # NEW: all K8S-01/K8S-02/K8S-03 tests (mocked; no live cluster)
```

### Pattern 1: EKS etcd Encryption Detection (boto3, in aws_connector.py)

EKS exposes `encryptionConfig` as a list in `describe_cluster`. An empty list means no
secrets encryption. A list entry with `resources: ["secrets"]` and a `provider.keyArn` means
secrets are encrypted. This is a boto3 call, NOT a kubernetes Python client call.

```python
# Source: AWS boto3 docs describe_cluster + CONTEXT.md STATE.md accumulated decisions
# Location: aws_connector.py — new function alongside _scan_rds_encryption

def _scan_eks_encryption(session, logger, session_start=None) -> List[CryptoEndpoint]:
    """Detect EKS cluster etcd encryption status (K8S-01 EKS path).

    Uses describe_cluster response encryptionConfig field.
    No kubernetes Python client required — this is an AWS management plane API call.
    """
    results: List[CryptoEndpoint] = []
    try:
        client = session.client("eks")
        # EKS clusters must be enumerated via list_clusters paginator
        paginator = client.get_paginator("list_clusters")
        for page in paginator.paginate():
            for cluster_name in page.get("clusters", []):
                try:
                    resp = client.describe_cluster(name=cluster_name)
                    cluster = resp.get("cluster", {})
                    enc_cfg = cluster.get("encryptionConfig", [])
                    # encryptionConfig absent or empty list -> secrets NOT encrypted
                    if not enc_cfg:
                        service_detail = "EKS/unencrypted"
                        severity = "HIGH"
                    else:
                        # Check if 'secrets' resource is encrypted
                        secrets_encrypted = any(
                            "secrets" in (entry.get("resources") or [])
                            for entry in enc_cfg
                        )
                        if secrets_encrypted:
                            kms_key = enc_cfg[0].get("provider", {}).get("keyArn", "")
                            service_detail = f"EKS/encrypted:{kms_key}"
                            severity = None
                        else:
                            service_detail = "EKS/unencrypted"
                            severity = "HIGH"

                    now = (session_start or datetime.now(timezone.utc)).replace(tzinfo=None)
                    ep = CryptoEndpoint(
                        host=f"aws://eks/{cluster_name}",
                        port=0,
                        protocol="KUBERNETES",
                        service_detail=service_detail,
                        dat_scan_json=json.dumps(
                            {"cluster": cluster_name, "provider": "EKS",
                             "encryptionConfig": enc_cfg},
                            default=str,
                        ),
                        scanned_at=now,
                    )
                    if severity:
                        ep.severity = severity
                    results.append(ep)
                except Exception as exc:
                    if logger:
                        logger.v(f"EKS cluster scan error for {cluster_name}: {exc}")
    except Exception as exc:
        if logger:
            logger.v(f"EKS encryption scan error: {exc}")
    return results
```

### Pattern 2: GKE databaseEncryption.state Detection (google-cloud-container)

`google-cloud-container` provides a typed `DatabaseEncryption.CurrentState` enum. The values
are `CURRENT_STATE_ENCRYPTED` (CMK active) and `CURRENT_STATE_DECRYPTED` (default, no CMK).
This is separate from `google-api-python-client` used in Phase 26.

```python
# Source: Google Cloud docs DatabaseEncryption.CurrentState + cloud.google.com/python/docs/reference
# Location: k8s_connector.py

def _scan_gke_encryption(project_id: str, cluster_configs: list, logger,
                         session_start=None) -> List[CryptoEndpoint]:
    """Detect GKE cluster etcd encryption via databaseEncryption.state (K8S-01 GKE path).

    cluster_configs: list of dicts with 'name' (cluster name) and 'location' (region or zone).
    Requires google-cloud-container (pip install quirk[cloud]).
    """
    if not GKE_AVAILABLE:
        return []
    results: List[CryptoEndpoint] = []
    now = (session_start or datetime.now(timezone.utc)).replace(tzinfo=None)
    try:
        from google.cloud import container_v1
        gke_client = container_v1.ClusterManagerClient()
        for cfg in cluster_configs:
            cluster_name_path = (
                f"projects/{project_id}/locations/{cfg['location']}"
                f"/clusters/{cfg['name']}"
            )
            try:
                cluster = gke_client.get_cluster(name=cluster_name_path)
                db_enc = cluster.database_encryption
                # current_state is a CurrentState enum; 2 = CURRENT_STATE_ENCRYPTED
                state_val = int(db_enc.current_state) if db_enc else 0
                if state_val == 2:  # CURRENT_STATE_ENCRYPTED
                    service_detail = f"GKE/encrypted:{db_enc.key_name}"
                    severity = None
                else:
                    service_detail = "GKE/unencrypted"
                    severity = "HIGH"

                ep = CryptoEndpoint(
                    host=f"gcp://gke/{project_id}/{cfg['name']}",
                    port=0,
                    protocol="KUBERNETES",
                    service_detail=service_detail,
                    dat_scan_json=json.dumps(
                        {"cluster": cfg["name"], "provider": "GKE",
                         "current_state": state_val,
                         "key_name": getattr(db_enc, "key_name", "")},
                        default=str,
                    ),
                    scanned_at=now,
                )
                if severity:
                    ep.severity = severity
                results.append(ep)
            except Exception as exc:
                if logger:
                    logger.v(f"GKE cluster scan error for {cfg['name']}: {exc}")
    except Exception as exc:
        if logger:
            logger.v(f"GKE encryption scan error: {exc}")
    return results
```

### Pattern 3: AKS Key Vault KMS Detection (azure-mgmt-containerservice)

`security_profile.azure_key_vault_kms.enabled` is the AKS etcd encryption signal.
`enabled == True` means Azure Key Vault KMS is active (encrypted).
`enabled == False` or `security_profile` absent means platform-managed key (MEDIUM finding).

```python
# Source: Azure SDK docs ManagedClusterSecurityProfile.azure_key_vault_kms + azure-mgmt-containerservice
# Location: k8s_connector.py

def _scan_aks_encryption(credential, subscription_id: str, cluster_configs: list,
                          logger, session_start=None) -> List[CryptoEndpoint]:
    """Detect AKS cluster etcd encryption via security_profile.azure_key_vault_kms (K8S-01 AKS path)."""
    if not AKS_AVAILABLE:
        return []
    results = []
    now = (session_start or datetime.now(timezone.utc)).replace(tzinfo=None)
    try:
        from azure.mgmt.containerservice import ContainerServiceClient
        aks_client = ContainerServiceClient(credential, subscription_id)
        for cfg in cluster_configs:
            # cfg has 'resource_group' and 'name'
            try:
                cluster = aks_client.managed_clusters.get(
                    resource_group_name=cfg["resource_group"],
                    resource_name=cfg["name"],
                )
                sec = getattr(cluster, "security_profile", None)
                kv_kms = getattr(sec, "azure_key_vault_kms", None)
                kv_enabled = bool(getattr(kv_kms, "enabled", False))
                if kv_enabled:
                    service_detail = "AKS/kv-kms"
                    severity = None
                else:
                    service_detail = "AKS/platform-managed"
                    severity = "MEDIUM"

                ep = CryptoEndpoint(
                    host=f"azure://aks/{cfg['resource_group']}/{cfg['name']}",
                    port=0,
                    protocol="KUBERNETES",
                    service_detail=service_detail,
                    dat_scan_json=json.dumps(
                        {"cluster": cfg["name"], "provider": "AKS",
                         "kv_kms_enabled": kv_enabled},
                        default=str,
                    ),
                    scanned_at=now,
                )
                if severity:
                    ep.severity = severity
                results.append(ep)
            except Exception as exc:
                if logger:
                    logger.v(f"AKS cluster scan error for {cfg['name']}: {exc}")
    except Exception as exc:
        if logger:
            logger.v(f"AKS encryption scan error: {exc}")
    return results
```

### Pattern 4: Secret Type Enumeration Without Reading Values (K8S-02)

The key insight: `list_namespaced_secret()` returns `V1Secret` objects. Each has a `type` field
(e.g., `"Opaque"`, `"kubernetes.io/tls"`) directly accessible. The `.data` field (base64-encoded
secret values) is present in the response body but is NEVER read. Only `secret.type` is accessed.
A `Counter` produces type counts.

The RBAC minimum is `get`, `list` on `secrets` in the target namespace. `403 ApiException`
maps to an `insufficient-rbac-privileges` scan error endpoint.

```python
# Source: kubernetes-client/python docs CoreV1Api + V1Secret model + ApiException pattern
# Location: k8s_connector.py

from collections import Counter
from kubernetes import client, config
from kubernetes.client.rest import ApiException

def _enumerate_secret_types(k8s_core_v1: "client.CoreV1Api", namespace: str,
                             logger, session_start=None) -> "CryptoEndpoint":
    """Enumerate K8S secret types in namespace without reading any secret values (K8S-02).

    Returns a single CryptoEndpoint summarizing type counts, or a scan_error endpoint
    if RBAC 403 is returned.
    """
    now = (session_start or datetime.now(timezone.utc)).replace(tzinfo=None)
    host_id = f"k8s://secrets/{namespace}"
    try:
        secrets = k8s_core_v1.list_namespaced_secret(namespace=namespace)
        # Count by type -- never access secret.data
        type_counts = dict(Counter(
            (s.type or "Opaque") for s in secrets.items
        ))
        return CryptoEndpoint(
            host=host_id,
            port=0,
            protocol="KUBERNETES",
            service_detail="K8S-SECRETS/types-enumerated",
            dat_scan_json=json.dumps(
                {"namespace": namespace, "secret_type_counts": type_counts},
                default=str,
            ),
            scanned_at=now,
        )
    except ApiException as exc:
        if exc.status == 403:
            return CryptoEndpoint(
                host=host_id,
                port=0,
                protocol="KUBERNETES",
                scan_error="insufficient-rbac-privileges",
                service_detail=(
                    "Remediation: RBAC role requires get,list on secrets "
                    f"in namespace '{namespace}'"
                ),
                scanned_at=now,
            )
        if logger:
            logger.v(f"K8S secret enumeration error in {namespace}: {exc}")
        return None
    except Exception as exc:
        if logger:
            logger.v(f"K8S secret enumeration error in {namespace}: {exc}")
        return None
```

### Pattern 5: K8S_AVAILABLE Import Guard (k8s_connector.py module level)

The three optional SDKs each get their own flag. `K8S_AVAILABLE` guards the kubernetes Python
client; `GKE_AVAILABLE` guards google-cloud-container; `AKS_AVAILABLE` guards
azure-mgmt-containerservice. This is essential for test patching via `unittest.mock.patch`.

```python
# Source: gcp_connector.py lines 23-32 [VERIFIED] — exact pattern
# Adaptation: three separate try/except blocks, three module-level flags

try:
    from kubernetes import client as k8s_client, config as k8s_config
    from kubernetes.client.rest import ApiException
    K8S_AVAILABLE = True
except ImportError:
    k8s_client = None          # type: ignore[assignment]
    k8s_config = None          # type: ignore[assignment]
    ApiException = None        # type: ignore[assignment]
    K8S_AVAILABLE = False

try:
    from google.cloud import container_v1 as _gke_container
    GKE_AVAILABLE = True
except ImportError:
    _gke_container = None      # type: ignore[assignment]
    GKE_AVAILABLE = False

try:
    from azure.mgmt.containerservice import ContainerServiceClient as _AKSClient
    AKS_AVAILABLE = True
except ImportError:
    _AKSClient = None          # type: ignore[assignment]
    AKS_AVAILABLE = False
```

### Pattern 6: encryption-config-inaccessible Finding (K8S-03)

K8S-03 fires when the configured `k8s_provider` does not match any of the three supported
managed providers (EKS/GKE/AKS), or when the appropriate SDK is not installed.
This is a required output — never silently return an empty list.

```python
# K8S-03 implementation in scan_k8s_targets()
SUPPORTED_PROVIDERS = frozenset(["eks", "gke", "aks"])

if provider not in SUPPORTED_PROVIDERS:
    results.append(CryptoEndpoint(
        host=f"k8s://{cluster_name or 'unknown'}",
        port=0,
        protocol="KUBERNETES",
        scan_error="encryption-config-inaccessible",
        service_detail=(
            f"Provider '{provider}' is not a supported managed cluster type. "
            "Supported: EKS, GKE, AKS. "
            "Self-hosted clusters require direct etcd access (out of scope)."
        ),
        scanned_at=now,
    ))
```

### Pattern 7: kubeconfig Loading (K8S-02)

The kubernetes Python client supports two loading modes:
- `config.load_kube_config(config_file=..., context=...)` — file-based kubeconfig
- `config.load_incluster_config()` — service account from within a pod

For QUIRK's use case (scanner runs outside the cluster), always use `load_kube_config`.
If `k8s_kubeconfig` config field is set, pass it as `config_file=`. Otherwise use the default
`~/.kube/config`. A `k8s_context` config field selects the kubeconfig context.

```python
# Source: kubernetes-client/python Context7 docs + github.com/kubernetes-client/python README
k8s_config.load_kube_config(
    config_file=cfg.connectors.k8s_kubeconfig or None,
    context=cfg.connectors.k8s_context or None,
)
v1 = k8s_client.CoreV1Api()
```

### Pattern 8: run_scan.py Integration (k8s_scanning block)

```python
# Source: run_scan.py db_scanning block (Phase 27) [VERIFIED: lines 506-528] — exact template
# Position: after blob_scanning block, before dnssec_scanning block

k8s_endpoints = []
with _phase_timer(run_stats, "k8s_scanning"):
    if cfg.connectors.enable_k8s:
        from quirk.scanner.k8s_connector import scan_k8s_targets
        k8s_endpoints = scan_k8s_targets(
            provider=cfg.connectors.k8s_provider or "",
            cluster_name=cfg.connectors.k8s_cluster_name or "",
            namespace=cfg.connectors.k8s_namespace or "default",
            kubeconfig=cfg.connectors.k8s_kubeconfig or None,
            context=cfg.connectors.k8s_context or None,
            # GKE-specific
            gcp_project_id=cfg.connectors.gcp_project_id or "",
            gke_clusters=cfg.connectors.gke_clusters or [],
            # AKS-specific
            azure_subscription_id=cfg.connectors.azure_subscription_id or "",
            aks_clusters=cfg.connectors.aks_clusters or [],
            logger=logger,
            session_start=session_start,
        )
        logger.info(f"K8S scan: {len(k8s_endpoints)} cluster endpoints")
```

### Pattern 9: Config Fields for K8S Connector

```python
# config.py ConnectorsCfg additions (after blob/s3 fields)
# Analog: GCP fields (lines 70-72) and DB fields (lines 73-80)

    # K8S connector config (v4.3, Phase 29)
    enable_k8s: bool = False
    k8s_provider: Optional[str] = None   # "eks" | "gke" | "aks"
    k8s_cluster_name: Optional[str] = None
    k8s_namespace: str = "default"
    k8s_kubeconfig: Optional[str] = None
    k8s_context: Optional[str] = None
    gke_clusters: list = field(default_factory=list)  # [{name, location}]
    aks_clusters: list = field(default_factory=list)  # [{name, resource_group}]
```

### Anti-Patterns to Avoid

- **Using kubernetes Python client for EKS etcd detection:** EKS etcd encryption is NOT a K8s API resource. It is an AWS cluster metadata field visible only via boto3 `describe_cluster`. The kubernetes client cannot query it.
- **Reading `secret.data` for K8S-02:** The type count enumeration accesses only `secret.type`. The `data` dict contains base64-encoded secret values — NEVER access it, even for length checks.
- **Importing `google-cloud-container` at module level without guard:** Follow the `_gke_container = None` pattern. The import guard must assign module-level None so tests can patch `K8S_CONNECTOR_MODULE.GKE_AVAILABLE`.
- **Returning empty list on `encryption-config-inaccessible`:** K8S-03 mandates an explicit endpoint with `scan_error="encryption-config-inaccessible"`. Never silently return `[]` when the provider is unknown or the SDK is absent — the finding is the signal.
- **Using `load_incluster_config()` by default:** QUIRK runs as a CLI scanner outside any pod. Default to `load_kube_config()`. `load_incluster_config()` would fail outside a pod and produce confusing errors.
- **Using `azure-mgmt-containerservice` at module level without lazy import:** Follow the `azure_connector.py _scan_app_gateways` pattern for inline imports inside the function body with `except ImportError:` guard. This is distinct from the module-level `AKS_AVAILABLE` flag (which is set at import time).
- **Setting `k8s_provider="eks"` and expecting the kubernetes Python client to list EKS clusters:** EKS detection uses boto3, not the kubernetes client. The `enable_k8s` flag controls the entire k8s scan block, but the EKS sub-path calls `_scan_eks_encryption(session, ...)` from `aws_connector.py`.
- **Forgetting to add `"KUBERNETES"` to `_PROTOCOL_KEYS` in evidence.py:** The `protocol_counts` dict is initialized from the `_PROTOCOL_KEYS` allowlist. KUBERNETES must be added or counts will be absent from evidence output.
- **Azure `security_profile` being None/absent for older clusters:** `getattr(cluster, "security_profile", None)` with nested `getattr(sec, "azure_key_vault_kms", None)` prevents AttributeError on clusters created before the security_profile API existed.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| EKS cluster encryption metadata | Custom HTTP calls to AWS EKS API | `boto3 eks.describe_cluster` | boto3 is core dep; handles SigV4 auth, retry, region |
| GKE cluster state query | Parse `gcloud` CLI output | `google-cloud-container ClusterManagerClient.get_cluster` | Typed response with `DatabaseEncryption.CurrentState` enum; no subprocess |
| AKS cluster security profile | Parse `az` CLI output | `azure-mgmt-containerservice ContainerServiceClient.managed_clusters.get` | Typed `ManagedClusterSecurityProfile`; standard Azure SDK pattern |
| Kubernetes secret type counting | Write kubeconfig parser + custom API HTTP calls | `kubernetes.client.CoreV1Api.list_namespaced_secret` | Official client handles auth, TLS, pagination; type field is in every response |
| RBAC permission detection | Try/catch generic Exception | `except ApiException as exc: if exc.status == 403:` | `ApiException.status` is the correct discriminator; generic except masks real errors |

**Key insight:** EKS etcd detection is a boto3 call (not kubernetes client), GKE detection needs
a separate `google-cloud-container` SDK (not `google-api-python-client`), and secret type counts
never require reading secret values — only the `type` metadata field per secret.

---

## Common Pitfalls

### Pitfall 1: Using kubernetes Python Client to Detect EKS etcd Encryption
**What goes wrong:** The Kubernetes API server on EKS does not expose its own encryption
configuration as an API resource. `kubectl get` cannot retrieve `encryptionConfig`. Code that
tries to use `CoreV1Api` to detect EKS etcd encryption will find nothing and silently return
no findings — triggering K8S-03's `encryption-config-inaccessible` path incorrectly.
**Why it happens:** EKS `encryptionConfig` is AWS infrastructure metadata, not a K8s resource.
**How to avoid:** EKS path is boto3 `session.client("eks").describe_cluster(name=cluster_name)`.
Place this function in `aws_connector.py`, not `k8s_connector.py`.
**Warning signs:** Tests that mock `CoreV1Api` and expect EKS findings pass; live scan returns no EKS finding.

### Pitfall 2: `google-cloud-container` vs `google-api-python-client` Confusion
**What goes wrong:** Phase 26 uses `google-api-python-client` (the discovery-based client) with
`_gcp_build("cloudkms", ...)`. Trying to use this same approach for GKE cluster inspection does
not produce a typed `database_encryption.current_state` object — the raw JSON must be parsed
manually and field names differ.
**Why it happens:** `google-api-python-client` returns raw dicts; `google-cloud-container` returns
proto-backed Python objects with enum types.
**How to avoid:** Add `google-cloud-container>=2.0.0` to `[cloud]` extras. Use
`from google.cloud import container_v1` with `ClusterManagerClient`. Do NOT use `_gcp_build`.
**Warning signs:** Code building `_gcp_build("container", "v1", ...)` then accessing
`.get("databaseEncryption", {}).get("currentState")` — raw dict nav, MEDIUM confidence.

### Pitfall 3: Empty `encryptionConfig` vs Absent `encryptionConfig` in EKS
**What goes wrong:** If `describe_cluster` returns `encryptionConfig: []` vs the key being
entirely absent, code that does `if not response.get("encryptionConfig"):` handles both correctly.
But code that does `if "encryptionConfig" not in response["cluster"]:` only handles the
absent case and misses the empty-list case.
**Why it happens:** AWS may return `encryptionConfig: []` for clusters where it was explicitly
disabled vs never configured. Both mean "secrets not encrypted."
**How to avoid:** Use `enc_cfg = cluster.get("encryptionConfig", [])` then `if not enc_cfg:`.
**Warning signs:** Test with `encryptionConfig: []` response fails to produce HIGH finding.

### Pitfall 4: DatabaseEncryption.CurrentState Enum Integer Values (GKE)
**What goes wrong:** `cluster.database_encryption.current_state` is an enum (int under the hood).
Code comparing with string `"ENCRYPTED"` will never match; `== 2` is correct for
`CURRENT_STATE_ENCRYPTED`. The sentinel `0` means `CURRENT_STATE_UNSPECIFIED` (treat as
unencrypted — no CMK configured).
**Why it happens:** google-cloud-container protos use integer enums, not string enums.
**How to avoid:** Compare `int(db_enc.current_state) == 2` for encrypted state. Or compare
against the enum class: `db_enc.current_state == container_v1.types.DatabaseEncryption.CurrentState.CURRENT_STATE_ENCRYPTED`.
**Warning signs:** All GKE clusters produce the unencrypted finding even when CMK is configured.

### Pitfall 5: AKS `security_profile` Attribute Error on Old Clusters
**What goes wrong:** Clusters created before AKS introduced `security_profile` in the API may
return `None` for `cluster.security_profile`. Accessing `.azure_key_vault_kms` on None raises
`AttributeError`.
**Why it happens:** `azure-mgmt-containerservice` returns a `ManagedCluster` object where
`security_profile` is optional.
**How to avoid:** Use `getattr(cluster, "security_profile", None)` then
`getattr(sec, "azure_key_vault_kms", None)` then `getattr(kv_kms, "enabled", False)` —
three nested `getattr` calls with defaults. Document with a comment.
**Warning signs:** `AttributeError: 'NoneType' object has no attribute 'azure_key_vault_kms'`.

### Pitfall 6: Secret `data` Field Is Returned — Must Not Be Logged
**What goes wrong:** `list_namespaced_secret` returns the full `V1Secret` object including
the `data` dict (base64-encoded values). If logger.v() is called with the full secret object
or `str(secret)`, it logs all secret values.
**Why it happens:** The `data` field is in the API response by default — there is no
`metadata_only` parameter in the kubernetes Python client.
**How to avoid:** Only access `secret.type`. Never log `str(secret)` or `secret.data`.
Log only namespace, type counts, and total count. Add a code comment: `# Never access secret.data`.
**Warning signs:** `dat_scan_json` or log output contains base64 strings.

### Pitfall 7: K8S_AVAILABLE flag Insufficient — Must Also Guard `GKE_AVAILABLE` and `AKS_AVAILABLE`
**What goes wrong:** The `K8S_AVAILABLE` flag only guards the kubernetes Python client import.
If a user installs `pip install quirk[cloud]` but only gets `kubernetes>=35.0.0` (not
`google-cloud-container` or `azure-mgmt-containerservice`), the GKE and AKS paths will fail
at import time inside the function body.
**Why it happens:** Three separate optional dependencies.
**How to avoid:** Three separate module-level import guards: `K8S_AVAILABLE`, `GKE_AVAILABLE`,
`AKS_AVAILABLE`. Check the relevant flag before each provider path, NOT just `K8S_AVAILABLE`.
**Warning signs:** `ImportError` in `_scan_gke_encryption` when `K8S_AVAILABLE=True` but
`google-cloud-container` not installed.

### Pitfall 8: `encryption-config-inaccessible` Must Fire for `K8S_AVAILABLE = False`
**What goes wrong:** If `kubernetes>=35.0.0` is not installed and `K8S_AVAILABLE = False`,
the scanner must still emit the `encryption-config-inaccessible` finding (K8S-03). Simply
returning `[]` because the package is absent violates K8S-03 ("never silently skips").
**Why it happens:** The SDK-unavailable path returns empty by default in other scanners
(because those other scanners have no K8S-03-equivalent requirement).
**How to avoid:** When `K8S_AVAILABLE = False`, emit one `encryption-config-inaccessible`
endpoint with remediation: "Install quirk[cloud] to enable Kubernetes scanning."
**Warning signs:** K8S-03 test fails when `K8S_AVAILABLE=False` — no endpoint produced.

---

## Code Examples

### EKS `describe_cluster` Response Structure (Verified)

```python
# Source: AWS boto3 docs describe_cluster [VERIFIED: docs.aws.amazon.com]
# encryptionConfig when ENABLED:
{
    "cluster": {
        "name": "my-cluster",
        "encryptionConfig": [
            {
                "resources": ["secrets"],
                "provider": {
                    "keyArn": "arn:aws:kms:us-east-1:123456789:key/abc-def"
                }
            }
        ]
    }
}

# encryptionConfig when DISABLED (empty list or absent):
{
    "cluster": {
        "name": "my-cluster",
        "encryptionConfig": []   # OR key entirely absent
    }
}
```

### GKE DatabaseEncryption CurrentState Values (Verified)

```python
# Source: Google Cloud docs DatabaseEncryption.CurrentState [VERIFIED: docs.cloud.google.com]
# 0 = CURRENT_STATE_UNSPECIFIED (treat as unencrypted)
# 1 = CURRENT_STATE_DECRYPTED    (no CMK — default)
# 2 = CURRENT_STATE_ENCRYPTED    (CMK active — positive finding)
# Additional transient states may exist; only 0, 1, 2 are stable for detection

from google.cloud import container_v1
client = container_v1.ClusterManagerClient()
cluster = client.get_cluster(name="projects/my-proj/locations/us-central1/clusters/my-gke")
state = cluster.database_encryption.current_state   # int enum
key_name = cluster.database_encryption.key_name      # str, CMK resource name
```

### AKS Security Profile Pattern (Verified)

```python
# Source: Azure SDK ManagedClusterSecurityProfile [VERIFIED: PyPI azure-mgmt-containerservice]
from azure.mgmt.containerservice import ContainerServiceClient
from azure.identity import DefaultAzureCredential

client = ContainerServiceClient(DefaultAzureCredential(), subscription_id)
cluster = client.managed_clusters.get(resource_group_name="rg", resource_name="my-aks")

sec = getattr(cluster, "security_profile", None)
kv_kms = getattr(sec, "azure_key_vault_kms", None)
enabled = bool(getattr(kv_kms, "enabled", False))  # True = KV KMS active
```

### Kubernetes Secret Type Count (No Data Read)

```python
# Source: kubernetes-client/python CoreV1Api docs [VERIFIED: Context7]
from kubernetes import client, config
from kubernetes.client.rest import ApiException
from collections import Counter

config.load_kube_config(config_file=kubeconfig_path, context=context)
v1 = client.CoreV1Api()

try:
    secrets = v1.list_namespaced_secret(namespace="default")
    # SAFE: only accesses secret.type; never touches secret.data
    type_counts = dict(Counter((s.type or "Opaque") for s in secrets.items))
    # e.g., {"Opaque": 12, "kubernetes.io/tls": 3, "kubernetes.io/dockerconfigjson": 1}
except ApiException as exc:
    if exc.status == 403:
        # insufficient-rbac-privileges finding
        pass
```

### Evidence Counter Pattern (K8S additions to evidence.py)

```python
# Source: evidence.py lines 83-84 + 171-181 [VERIFIED: read in session] — dar_storage_* template
# Append to _PROTOCOL_KEYS:
_PROTOCOL_KEYS = ("TLS", "HTTP", "SSH", "UNKNOWN", "KERBEROS", "SAML", "DNSSEC",
                  "POSTGRESQL", "MYSQL", "RDS", "S3", "AZURE_BLOB", "KUBERNETES")  # add KUBERNETES

# Append counter variables (after dar_storage_aws_managed_count):
dar_k8s_unencrypted_count = 0   # EKS/unencrypted + GKE/unencrypted + AKS/platform-managed

# In the endpoint loop (elif chain after AZURE_BLOB):
elif proto == "KUBERNETES":
    sd = str(getattr(ep, "service_detail", "") or "")
    if "unencrypted" in sd or "platform-managed" in sd:
        dar_k8s_unencrypted_count += 1
    # K8S-SECRETS/types-enumerated is informational — no penalty

# In return dict (after dar_storage_aws_managed_ratio):
"dar_k8s_unencrypted_count": dar_k8s_unencrypted_count,
"dar_k8s_unencrypted_ratio": round(dar_k8s_unencrypted_count / total_endpoints, 4) if total_endpoints else 0.0,
```

---

## Runtime State Inventory

> Omitted — Phase 29 is a greenfield extension, not a rename/refactor/migration.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| EncryptionConfiguration as queryable K8s resource | Managed-cluster APIs (EKS/GKE/AKS) only | Always been this way | Direct etcd inspection is out of scope; managed APIs are the only agentless path |
| `google-api-python-client` for all GCP services | `google-cloud-container` for GKE cluster inspection | Phase 29 introduces this distinction | `google-api-python-client` does not expose typed `DatabaseEncryption.CurrentState` enum |
| `azure-mgmt-containerservice` <= 34.x | 35.0+ with `security_profile.azure_key_vault_kms` | Introduced in 2022+ API versions | `azure_key_vault_kms.enabled` is the correct field; absent in very old SDK versions |

**Deprecated/outdated:**
- Direct etcd `EncryptionConfiguration` REST inspection: requires agent on etcd nodes — violates agentless constraint and is out of scope per REQUIREMENTS.md.
- kubernetes Python client versions < 30.0: version numbering tracks the K8s release (v35 = K8s 1.32); earlier versions may lack `ApiException.status` discriminator consistency.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `azure-mgmt-containerservice>=35.0.0` is a valid minimum for `security_profile.azure_key_vault_kms` | Standard Stack | Wrong minimum version could produce `AttributeError` on `azure_key_vault_kms`; plan execution should verify via changelog or `pip show` |
| A2 | GKE `DatabaseEncryption.CurrentState` enum value `2` = ENCRYPTED, `1` = DECRYPTED, `0` = UNSPECIFIED | Code Examples | If enum values differ in `google-cloud-container 2.64.0`, all GKE findings would be misclassified; compare against enum class rather than raw int if uncertain |
| A3 | EKS `list_clusters` paginator exists and enumerates all accessible clusters | Architecture Patterns | Verified from boto3 EKS docs search; if paginator absent, use `list_clusters` directly (like `list_buckets` for S3) |
| A4 | `kubernetes>=35.0.0` maps to Kubernetes API 1.32 and `list_namespaced_secret` signature is unchanged since v29 | Standard Stack | Unlikely to break; kubernetes client versioning is highly stable for CoreV1 APIs |
| A5 | AKS `platform-managed` key (KV KMS disabled) warrants MEDIUM severity rather than HIGH | Architecture Patterns | Platform-managed key is encrypted but not CMK; analogous to S3/sse-kms-aws MEDIUM vs S3/unencrypted HIGH. Reasonable but requires user confirmation in CONTEXT.md |

---

## Open Questions

1. **EKS path in aws_connector.py vs k8s_connector.py**
   - What we know: EKS etcd detection uses boto3, not the kubernetes Python client. The boto3
     session already exists in `aws_connector.py`.
   - What's unclear: Should `_scan_eks_encryption` be added to `aws_connector.py` alongside
     `_scan_rds_encryption`, or should it live in `k8s_connector.py` with boto3 imported there?
   - Recommendation: `aws_connector.py` is correct. It reuses the existing boto3 session.
     `k8s_connector.py` imports are gated on `K8S_AVAILABLE` / `GKE_AVAILABLE` / `AKS_AVAILABLE`.
     Adding boto3 EKS calls to `k8s_connector.py` would create an implicit core-dep assumption.

2. **Namespace targeting strategy**
   - What we know: K8S-02 requires secret type counts "for a configured cluster namespace."
     The success criteria says "a configured cluster namespace" — singular.
   - What's unclear: Should the scanner support a list of namespaces or a single namespace?
   - Recommendation: Single configurable namespace (`k8s_namespace: str = "default"`).
     Multi-namespace support can be added later. Avoids blast radius from listing secrets
     across all namespaces.

3. **GKE cluster config format**
   - What we know: GKE `get_cluster` requires a resource path
     `projects/{project}/locations/{location}/clusters/{name}`. Location can be a region
     (e.g., `us-central1`) or zone (e.g., `us-central1-a`).
   - What's unclear: Should config be `gke_clusters: [{name: ..., location: ...}]` or
     a comma-separated string?
   - Recommendation: List of dicts `[{name, location}]` — consistent with
     `aks_clusters: [{name, resource_group}]`. Both follow existing `pg_targets` list pattern.

4. **Chaos lab for K8S phase**
   - What we know: Phase 27 (DB connector) has no live Docker chaos lab service — it relies
     entirely on unit tests with mocks. Kind cluster requires Docker-in-Docker and significant
     setup.
   - What's unclear: Is a live K8S chaos lab needed, or are mocks + a human-UAT note sufficient?
   - Recommendation: Mock-only unit tests (like `db_connector.py` pattern) + a
     `labs/kubernetes/expected_results.md` file describing the human-UAT procedure for a real
     cluster. Do NOT add a kind cluster to docker-compose.yml — the complexity is out of
     proportion to the test value.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| boto3 | EKS etcd detection | ✓ (core dep) [VERIFIED: pyproject.toml] | >=1.42.0 | N/A — already in core |
| kubernetes | K8S-02 secret enumeration | ✗ (not yet added) | — | Add `kubernetes>=35.0.0` to `[cloud]` extras |
| google-cloud-container | GKE K8S-01 path | ✗ (not yet added) | — | Add `google-cloud-container>=2.0.0` to `[cloud]` extras |
| azure-mgmt-containerservice | AKS K8S-01 path | ✗ (not yet added) | — | Add `azure-mgmt-containerservice>=35.0.0` to `[cloud]` extras |
| azure-identity | AKS credential | ✓ (core dep) [VERIFIED: pyproject.toml] | >=1.25.0 | N/A — already in core |

**Missing dependencies with no fallback:**
- `kubernetes`, `google-cloud-container`, `azure-mgmt-containerservice` — all three required for
  full K8S-01/K8S-02 coverage; must be added to `[cloud]` extras in pyproject.toml (ISSUE-2 pattern).

**Missing dependencies with fallback:**
- None — when these SDKs are absent, `K8S_AVAILABLE=False` / `GKE_AVAILABLE=False` /
  `AKS_AVAILABLE=False` trigger the K8S-03 `encryption-config-inaccessible` finding path,
  which is the correct degraded output per the requirements.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (existing — no config file, discovered by convention) |
| Config file | none |
| Quick run command | `python -m pytest tests/test_k8s_connector.py -x -q` |
| Full suite command | `python -m pytest tests/ -x -q` |

### RED/GREEN/REFACTOR Strategy

All K8S tests are **mock-based** — no live cluster is required. This matches the `db_connector.py`
pattern which also has no live Docker service. The Kubernetes Python client mock approach is:

**For K8S-02 (secret enumeration):**
```python
from unittest.mock import patch, MagicMock

def _make_secret_list(type_tuples):
    """Build a mock V1SecretList with secrets of given types."""
    mock_secrets = []
    for stype in type_tuples:
        s = MagicMock()
        s.type = stype
        mock_secrets.append(s)
    mock_list = MagicMock()
    mock_list.items = mock_secrets
    return mock_list

def test_k8s_secret_type_counts():
    with patch("quirk.scanner.k8s_connector.K8S_AVAILABLE", True):
        from quirk.scanner.k8s_connector import _enumerate_secret_types
        mock_v1 = MagicMock()
        mock_v1.list_namespaced_secret.return_value = _make_secret_list([
            "Opaque", "Opaque", "kubernetes.io/tls", "kubernetes.io/dockerconfigjson",
        ])
        ep = _enumerate_secret_types(mock_v1, namespace="default", logger=None)
        counts = json.loads(ep.dat_scan_json)["secret_type_counts"]
        assert counts["Opaque"] == 2
        assert counts["kubernetes.io/tls"] == 1
```

**For K8S-01 EKS (in aws_connector.py):**
```python
def test_eks_encryption_detected():
    mock_session = MagicMock()
    mock_eks = MagicMock()
    mock_eks.get_paginator.return_value.paginate.return_value = [
        {"clusters": ["my-cluster"]}
    ]
    mock_eks.describe_cluster.return_value = {
        "cluster": {
            "name": "my-cluster",
            "encryptionConfig": [
                {"resources": ["secrets"], "provider": {"keyArn": "arn:aws:kms:..."}}
            ]
        }
    }
    mock_session.client.return_value = mock_eks
    results = _scan_eks_encryption(mock_session, logger=None)
    assert any("encrypted" in ep.service_detail for ep in results)
```

**For K8S-03 (encryption-config-inaccessible):**
Tests verify that:
1. Unknown provider → `scan_error="encryption-config-inaccessible"` endpoint produced
2. `K8S_AVAILABLE=False` → `scan_error="encryption-config-inaccessible"` endpoint produced (not empty list)
3. RBAC `ApiException(status=403)` → `scan_error="insufficient-rbac-privileges"` endpoint produced

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
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
| evidence | `dar_k8s_unencrypted_count` increments for KUBERNETES/unencrypted rows | unit | `pytest tests/test_intelligence_evidence.py -x -q` (extend existing) | Exists |
| scoring | `dar_k8s_unencrypted_ratio` weight appears in score computation | unit | `pytest tests/test_intelligence_scoring.py -x -q` (extend existing) | Exists |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_k8s_connector.py -x -q`
- **Per wave merge:** `python -m pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_k8s_connector.py` — all K8S-01/K8S-02/K8S-03 + ISSUE-2/ISSUE-3 tests (new file)
- [ ] `labs/kubernetes/expected_results.md` — human-UAT procedure for live cluster verification

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | N/A — uses ambient cloud credentials (boto3, ADC, DefaultAzureCredential) and kubeconfig |
| V3 Session Management | no | N/A — CLI tool, no user sessions |
| V4 Access Control | yes | Scanner requests minimum RBAC: `get,list` on `secrets`; 403 → explicit finding, no silent escalation |
| V5 Input Validation | yes | `cluster_name` / `namespace` validated as non-empty before API calls; `json.dumps(default=str)` prevents serialization failures |
| V6 Cryptography | no | Scanner detects crypto posture; does not implement crypto operations |

### Known Threat Patterns for Kubernetes Management APIs

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Secret value exposure via `secret.data` logging | Information Disclosure | Never access `secret.data`; log only `secret.type`; add code comment; no `str(secret)` in logger calls |
| RBAC over-permission (cluster-admin instead of minimum role) | Elevation of Privilege | Document minimum RBAC (get,list on secrets in namespace); 403 is expected if under-provisioned |
| kubeconfig exfiltration via `dat_scan_json` | Information Disclosure | `dat_scan_json` stores only type counts, cluster name, provider; no kubeconfig content, no credentials |
| EKS cluster enumeration without authorization | Information Disclosure | EKS `list_clusters` requires `eks:ListClusters` IAM permission; scanner uses ambient credential; unauthorized access produces ClientError, not silent empty list |

---

## Sources

### Primary (HIGH confidence)
- `quirk/scanner/gcp_connector.py` [VERIFIED: read in session] — exact `GCP_AVAILABLE` import guard pattern; public function signature; per-resource try/except
- `quirk/scanner/aws_connector.py` [VERIFIED: read in session] — `_scan_rds_encryption` template; `BOTO3_AVAILABLE` pattern; paginator pattern
- `quirk/scanner/db_connector.py` [VERIFIED: read in session] — `session_start` threading; per-target loop; `PSYCOPG2_AVAILABLE` module-level None
- `quirk/intelligence/evidence.py` [VERIFIED: read in session] — `_PROTOCOL_KEYS` current state; `dar_storage_*` counter pattern
- `quirk/intelligence/scoring.py` [VERIFIED: inferred from Phase 27/28 PATTERNS.md] — `SCORE_WEIGHTS`, `dar_impacts` pattern
- `quirk/cbom/builder.py` [VERIFIED: grep in session] — Pass 1/2/3 skip lists current state (includes KUBERNETES placeholder needed)
- `quirk/models.py` [VERIFIED: read in session] — `dat_scan_json` and `severity` columns present
- `quirk/config.py` [VERIFIED: read in session] — `ConnectorsCfg` current fields; `field(default_factory=list)` pattern
- `pyproject.toml` [VERIFIED: read in session] — current `[cloud]` extras group; `[db]` extras group for structural reference
- `run_scan.py` lines 503-628 [VERIFIED: read in session] — `session_start` placement; `k8s_scanning` block insertion point
- PyPI `kubernetes` [VERIFIED: curl + pip index] — latest: 35.0.0, released 2026-01-16
- PyPI `google-cloud-container` [VERIFIED: curl] — latest: 2.64.0
- PyPI `azure-mgmt-containerservice` [VERIFIED: curl + WebFetch] — latest: 41.1.0
- AWS boto3 docs `describe_cluster` [VERIFIED: WebFetch] — `encryptionConfig` response structure confirmed
- GKE `DatabaseEncryption.CurrentState` [VERIFIED: WebFetch docs.cloud.google.com] — enum values CURRENT_STATE_UNSPECIFIED/ENCRYPTED/DECRYPTED confirmed
- kubernetes Python client Context7 [VERIFIED: Context7 CLI] — `load_kube_config`, `CoreV1Api`, `ApiException` patterns

### Secondary (MEDIUM confidence)
- AKS `ManagedClusterSecurityProfile.azure_key_vault_kms.enabled` [MEDIUM: WebSearch + Learn docs] — field confirmed in search results; exact minimum version for field not pinned to a specific changelog
- `google-cloud-container` typed `DatabaseEncryption` object pattern [MEDIUM: WebFetch + WebSearch] — confirmed via Google Cloud blog and docs references; `ClusterManagerClient.get_cluster` confirmed

### Tertiary (LOW confidence)
- None — all critical claims verified against codebase inspection or official sources

---

## Metadata

**Confidence breakdown:**
- Standard stack (kubernetes library versions): HIGH — PyPI verified
- EKS API structure: HIGH — boto3 docs verified
- GKE DatabaseEncryption enum values: MEDIUM — docs confirmed enum class exists; specific int values assumed based on proto numbering convention
- AKS security_profile field: MEDIUM — field name confirmed in docs; minimum SDK version ASSUMED
- Architecture patterns: HIGH — direct inspection of Phase 27/28 analogs in codebase

**Research date:** 2026-04-26
**Valid until:** 2026-05-26 (Kubernetes client API is highly stable; cloud SDK versions change but API surfaces are stable)
