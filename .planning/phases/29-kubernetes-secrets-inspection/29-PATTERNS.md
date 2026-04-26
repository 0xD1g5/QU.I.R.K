# Phase 29: Kubernetes Secrets Inspection — Pattern Map

**Mapped:** 2026-04-26
**Files analyzed:** 11 (new/modified)
**Analogs found:** 11 / 11

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `quirk/scanner/k8s_connector.py` | service/scanner | request-response + event-driven | `quirk/scanner/azure_connector.py` + `quirk/scanner/db_connector.py` | role-match (composite) |
| `quirk/scanner/aws_connector.py` | service/scanner | request-response | self (`_scan_rds_encryption`) | exact |
| `quirk/scanner/gcp_connector.py` | service/scanner | request-response | self (no change — EKS path moves to aws_connector) | N/A (no GKE change needed per RESEARCH.md) |
| `quirk/scanner/azure_connector.py` | service/scanner | request-response | self (`_scan_blob_encryption`) | exact |
| `quirk/config.py` | config | N/A | self (`ConnectorsCfg` Phase 28 additions) | exact |
| `quirk/intelligence/evidence.py` | intelligence | transform | self (`dar_storage_*` block) | exact |
| `quirk/intelligence/scoring.py` | intelligence | transform | self (`dar_storage_*` weight entries) | exact |
| `quirk/cbom/builder.py` | builder | transform | self (Pass 1/2/3 protocol skip-lists) | exact |
| `run_scan.py` | orchestrator | request-response | self (`blob_scanning` block lines 557–571) | exact |
| `pyproject.toml` | config | N/A | self (`[cloud]` extras, line 44–48) | exact |
| `tests/test_k8s_connector.py` | test | N/A | `tests/test_azure_blob.py` + `tests/test_db_connector.py` | role-match |
| `labs/kubernetes/expected_results.md` | docs/lab | N/A | `labs/storage/expected_results.md` | role-match |

---

## Pattern Assignments

### `quirk/scanner/k8s_connector.py` (NEW — service/scanner, request-response)

**Primary analog:** `quirk/scanner/azure_connector.py` (import guard + optional-dep inline import pattern)
**Secondary analog:** `quirk/scanner/db_connector.py` (session_start threading, AVAILABLE guard with None assignment)

#### Import guard pattern (from `quirk/scanner/db_connector.py` lines 21–33 and `quirk/scanner/azure_connector.py` lines 19–28)

Three separate module-level import blocks, one per optional SDK. Each name is assigned `None`
at module level when the import fails so `unittest.mock.patch` can target it.

```python
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from typing import List, Optional

from quirk.models import CryptoEndpoint

# ---------------------------------------------------------------------------
# kubernetes Python client optional import — required for test patching
# ---------------------------------------------------------------------------
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

**Key rule:** The `db_connector.py` pattern (lines 21–33) assigns the module itself to `None`
(`psycopg2 = None`). The k8s connector follows the same convention: each name that tests
need to patch must live at module level even when the import fails.

#### GKE encryption detection sub-function

**Analog:** `quirk/scanner/azure_connector.py` `_scan_blob_encryption` (lines 120–226) —
same shape: guard check at top, inline import inside function, per-item try/except, `session_start`
timestamp, `dat_scan_json`, severity conditional, `getattr` defensiveness.

```python
def _scan_gke_encryption(
    project_id: str,
    cluster_configs: list,
    logger,
    session_start=None,
) -> List[CryptoEndpoint]:
    """Detect GKE cluster etcd encryption via databaseEncryption.state (K8S-01 GKE path)."""
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
                state_val = int(db_enc.current_state) if db_enc else 0
                # 2 = CURRENT_STATE_ENCRYPTED; 0/1 = unencrypted/unspecified
                if state_val == 2:
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

#### AKS encryption detection sub-function

**Analog:** `quirk/scanner/azure_connector.py` `_scan_app_gateways` (lines 80–117) —
inline import inside function body with `except ImportError:` guard, `getattr` defensive
access on optional SDK attributes.

```python
def _scan_aks_encryption(
    credential,
    subscription_id: str,
    cluster_configs: list,
    logger,
    session_start=None,
) -> List[CryptoEndpoint]:
    """Detect AKS etcd encryption via security_profile.azure_key_vault_kms (K8S-01 AKS path)."""
    if not AKS_AVAILABLE:
        return []
    results = []
    now = (session_start or datetime.now(timezone.utc)).replace(tzinfo=None)
    try:
        from azure.mgmt.containerservice import ContainerServiceClient
        aks_client = ContainerServiceClient(credential, subscription_id)
        for cfg in cluster_configs:
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

**Critical:** Three nested `getattr` calls on `security_profile` → `azure_key_vault_kms` →
`enabled` prevent `AttributeError` on clusters created before the security_profile API existed.
This is the same defensive `getattr` pattern used in `_scan_app_gateways` lines 88–93.

#### Secret type enumeration sub-function (K8S-02)

**Analog:** `quirk/scanner/db_connector.py` (session_start threading, per-target try/except,
scan_error endpoint on access failure).

```python
def _enumerate_secret_types(
    k8s_core_v1,
    namespace: str,
    logger,
    session_start=None,
) -> Optional[CryptoEndpoint]:
    """Enumerate K8S secret types in namespace without reading any secret values (K8S-02).

    Only accesses secret.type — never secret.data.
    """
    now = (session_start or datetime.now(timezone.utc)).replace(tzinfo=None)
    host_id = f"k8s://secrets/{namespace}"
    try:
        secrets = k8s_core_v1.list_namespaced_secret(namespace=namespace)
        # Count by type -- NEVER access secret.data
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
                    f"Remediation: RBAC role requires get,list on secrets "
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

#### K8S-03 encryption-config-inaccessible finding

**Analog:** No direct analog — this is unique to K8S. Nearest is `gcp_connector.py` lines
382–391 where credentials unavailability produces an explicit `scan_error` endpoint rather
than a silent empty return.

```python
# In scan_k8s_targets() — fires when provider not determinable
SUPPORTED_PROVIDERS = frozenset(["eks", "gke", "aks"])

if provider not in SUPPORTED_PROVIDERS:
    now = (session_start or datetime.now(timezone.utc)).replace(tzinfo=None)
    return [CryptoEndpoint(
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
    )]
```

**K8S-03 also fires when `K8S_AVAILABLE=False`** — unlike other scanners that silently return
`[]` when their SDK is absent, K8S must emit the inaccessible finding. This is a deliberate
departure from the `db_connector.py` `if not PSYCOPG2_AVAILABLE: return []` pattern.

#### Public entry point

**Analog:** `quirk/scanner/gcp_connector.py` `scan_gcp_targets` (lines 345–426) — input
validation before API calls, AVAILABLE guard at top, sub-function delegation.

```python
def scan_k8s_targets(
    provider: str,
    cluster_name: str,
    namespace: str = "default",
    kubeconfig: Optional[str] = None,
    context: Optional[str] = None,
    gcp_project_id: str = "",
    gke_clusters: list = None,
    azure_subscription_id: str = "",
    aks_clusters: list = None,
    logger=None,
    session_start=None,
) -> List[CryptoEndpoint]:
    ...
```

---

### `quirk/scanner/aws_connector.py` — ADD `_scan_eks_encryption()` (EXTEND)

**Analog:** `_scan_rds_encryption` in same file (lines 75–129) — paginator pattern, per-item
try/except, `service_detail` string encoding, severity conditional, `CryptoEndpoint` construction.

**Note:** `_scan_rds_encryption` does NOT yet use `session_start`. The new `_scan_eks_encryption`
MUST include `session_start` (ISSUE-3 pattern). Copy the `_scan_s3_encryption` session_start
pattern (line 166): `ts = (session_start or datetime.now(timezone.utc)).replace(tzinfo=None)`.

**Also note:** `scan_aws_targets` (lines 347–375) does not currently accept `session_start`.
The EKS call should be wired via a separate call in `run_scan.py` (see run_scan.py section
below) rather than through `scan_aws_targets`, to avoid changing its existing signature.

```python
# Paginator pattern from _scan_rds_encryption (lines 88-90):
client = session.client("rds")
paginator = client.get_paginator("describe_db_instances")
for page in paginator.paginate():
    for db in page.get("DBInstances", []):
        ...

# New _scan_eks_encryption uses same paginator shape:
def _scan_eks_encryption(session, logger, session_start=None) -> List[CryptoEndpoint]:
    results: List[CryptoEndpoint] = []
    ts = (session_start or datetime.now(timezone.utc)).replace(tzinfo=None)
    try:
        client = session.client("eks")
        paginator = client.get_paginator("list_clusters")
        for page in paginator.paginate():
            for cluster_name in page.get("clusters", []):
                try:
                    resp = client.describe_cluster(name=cluster_name)
                    cluster = resp.get("cluster", {})
                    enc_cfg = cluster.get("encryptionConfig", [])
                    if not enc_cfg:
                        service_detail = "EKS/unencrypted"
                        severity = "HIGH"
                    else:
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
                        scanned_at=ts,
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

**session_start pattern source:** `aws_connector.py` `_scan_s3_encryption` line 166:
```python
ts = (session_start or datetime.now(timezone.utc)).replace(tzinfo=None)
```

**Severity conditional pattern source:** `aws_connector.py` `_scan_rds_encryption` lines 118–119:
```python
if severity:
    ep.severity = severity
```

---

### `quirk/config.py` — EXTEND `ConnectorsCfg` (MODIFY)

**Analog:** Phase 28 addition block (lines 81–84) — `enable_*: bool`, `Optional[str]` fields,
`list = field(default_factory=list)` for list fields, grouped by feature with comment.

**Current last block (lines 81–84):**
```python
    # Object storage connector config (v4.3, Phase 28, per D-04)
    enable_s3: bool = False
    enable_blob: bool = False
    aws_endpoint_url: Optional[str] = None  # MinIO/LocalStack S3 endpoint override
```

**New block to append after line 84:**
```python
    # K8S connector config (v4.3, Phase 29)
    enable_k8s: bool = False
    k8s_provider: Optional[str] = None    # "eks" | "gke" | "aks"
    k8s_cluster_name: Optional[str] = None
    k8s_namespace: str = "default"
    k8s_kubeconfig: Optional[str] = None
    k8s_context: Optional[str] = None
    gke_clusters: list = field(default_factory=list)   # [{name, location}]
    aks_clusters: list = field(default_factory=list)   # [{name, resource_group}]
```

**No changes needed to `config_from_dict`** — it uses `_KNOWN_CONNECTOR_KEYS` (line 131)
which is computed dynamically from `dataclasses.fields(ConnectorsCfg)`, so new fields are
picked up automatically.

---

### `quirk/intelligence/evidence.py` — EXTEND (MODIFY)

**Analog:** Phase 28 `dar_storage_*` block — exact template to replicate.

**`_PROTOCOL_KEYS` (line 9–10) — add `"KUBERNETES"`:**
```python
# Current (line 9):
_PROTOCOL_KEYS = ("TLS", "HTTP", "SSH", "UNKNOWN", "KERBEROS", "SAML", "DNSSEC",
                  "POSTGRESQL", "MYSQL", "RDS", "S3", "AZURE_BLOB")

# New:
_PROTOCOL_KEYS = ("TLS", "HTTP", "SSH", "UNKNOWN", "KERBEROS", "SAML", "DNSSEC",
                  "POSTGRESQL", "MYSQL", "RDS", "S3", "AZURE_BLOB", "KUBERNETES")
```

**New counter variable (after line 84, alongside `dar_storage_aws_managed_count`):**
```python
    dar_k8s_unencrypted_count = 0   # EKS/unencrypted + GKE/unencrypted + AKS/platform-managed
```

**New elif branch in the endpoint loop (after the `AZURE_BLOB` branch, lines 179–182):**
```python
        elif proto == "KUBERNETES":
            sd = str(getattr(ep, "service_detail", "") or "")
            if "unencrypted" in sd or "platform-managed" in sd:
                dar_k8s_unencrypted_count += 1
            # K8S-SECRETS/types-enumerated and scan_error rows are informational — no penalty
```

**New return dict entries (after `dar_storage_aws_managed_ratio` at lines 241–242):**
```python
        "dar_k8s_unencrypted_count": dar_k8s_unencrypted_count,
        "dar_k8s_unencrypted_ratio": round(dar_k8s_unencrypted_count / total_endpoints, 4) if total_endpoints else 0.0,
```

---

### `quirk/intelligence/scoring.py` — EXTEND (MODIFY)

**Analog:** Phase 28 additions — `dar_storage_unencrypted_ratio` and `dar_storage_aws_managed_ratio`
in `SCORE_WEIGHTS` (lines 21–22) and `dar_impacts` list (lines 172–177).

**New `SCORE_WEIGHTS` entries (after line 22):**
```python
    "dar_k8s_unencrypted_ratio": 10.0,     # Phase 29 — unencrypted etcd (HIGH) or platform-managed (MEDIUM)
```

**New variable in `compute_readiness_score` (after `dar_storage_aws_managed` line 134):**
```python
    dar_k8s_unencrypted = max(0, _as_int(evidence.get("dar_k8s_unencrypted_count", 0)))
```

**New `dar_impacts` entry (after line 176):**
```python
        ("Kubernetes etcd unencrypted or platform-managed", -_ratio(dar_k8s_unencrypted, denom) * w["dar_k8s_unencrypted_ratio"]),
```

---

### `quirk/cbom/builder.py` — EXTEND skip-lists (MODIFY)

**Analog:** Current Pass 1/2/3 skip-lists — add `"KUBERNETES"` to all three.

**Pass 1 (line 410) — add `KUBERNETES` to the existing tuple:**
```python
# Current (line 410):
        elif ep.protocol in ("POSTGRESQL", "MYSQL", "RDS", "S3", "AZURE_BLOB"):

# New:
        elif ep.protocol in ("POSTGRESQL", "MYSQL", "RDS", "S3", "AZURE_BLOB", "KUBERNETES"):
```

**Pass 2 (lines 436–438) — add `KUBERNETES` to the existing tuple:**
```python
# Current (lines 436–438):
        if ep.protocol in ("SSH", "CONTAINER", "SOURCE", "KERBEROS", "SAML", "DNSSEC",
                           "GCP", "CLOUD_SQL", "POSTGRESQL", "MYSQL", "RDS",
                           "S3", "AZURE_BLOB"):

# New — append "KUBERNETES" to last line:
        if ep.protocol in ("SSH", "CONTAINER", "SOURCE", "KERBEROS", "SAML", "DNSSEC",
                           "GCP", "CLOUD_SQL", "POSTGRESQL", "MYSQL", "RDS",
                           "S3", "AZURE_BLOB", "KUBERNETES"):
```

**Pass 3 (lines 517–519) — add `KUBERNETES` to the existing tuple:**
```python
# Current (lines 517–519):
        elif ep.protocol in ("JWT", "CONTAINER", "SOURCE", "AWS", "AZURE", "GCP", "CLOUD_SQL",
                             "DNSSEC", "SAML", "KERBEROS", "POSTGRESQL", "MYSQL", "RDS",
                             "S3", "AZURE_BLOB"):

# New — append "KUBERNETES" to last line:
        elif ep.protocol in ("JWT", "CONTAINER", "SOURCE", "AWS", "AZURE", "GCP", "CLOUD_SQL",
                             "DNSSEC", "SAML", "KERBEROS", "POSTGRESQL", "MYSQL", "RDS",
                             "S3", "AZURE_BLOB", "KUBERNETES"):
```

---

### `run_scan.py` — ADD `k8s_scanning` block (MODIFY)

**Analog:** `blob_scanning` block (lines 556–571) — exact shape: `with _phase_timer(...)`,
`if cfg.connectors.enable_*:`, inline import, AVAILABLE guard check, function call with
all config params, `logger.info(f"... scan: {len(...)} ...")`.

**Insert after the `blob_scanning` block (after line 571), before `gcs_storage_reuse`:**

```python
    # ==============================
    # K8S secrets inspection (Phase 29, K8S-01 / K8S-02 / K8S-03)
    # ==============================
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
                gcp_project_id=cfg.connectors.gcp_project_id or "",
                gke_clusters=cfg.connectors.gke_clusters or [],
                azure_subscription_id=cfg.connectors.azure_subscription_id or "",
                aks_clusters=cfg.connectors.aks_clusters or [],
                logger=logger,
                session_start=session_start,
            )
            logger.info(f"K8S scan: {len(k8s_endpoints)} cluster endpoints")
```

**EKS wiring** — the EKS path calls `_scan_eks_encryption` from `aws_connector.py`.
It must be added inside the existing `aws_scanning` block (lines 472–483), after
the existing `scan_aws_targets` call, using the boto3 session already created there
OR via a separate boto3 session if `enable_k8s` is set independently of `enable_aws`.
Simplest approach: add EKS call inside the `k8s_scanning` block when `k8s_provider == "eks"`,
creating a fresh boto3 session using the same `aws_region`/`aws_profile` config fields.

**Also:** `k8s_endpoints` must be appended to the `all_endpoints` list that feeds the DB
persist phase. Check the existing `all_endpoints` aggregation in `run_scan.py` and add
`k8s_endpoints` there following the same pattern as `s3_endpoints`, `blob_endpoints`.

---

### `pyproject.toml` — EXTEND `[cloud]` extras (MODIFY)

**Analog:** Phase 28 `azure-mgmt-storage` addition (line 47) — append comment-annotated lines.

**Current `[cloud]` block (lines 44–48):**
```toml
cloud = [
    "google-api-python-client>=2.0.0",
    "google-auth>=2.36.0",
    "azure-mgmt-storage>=21.0.0",  # Phase 28: Azure Blob encryption audit (STOR-02)
]
```

**New `[cloud]` block:**
```toml
cloud = [
    "google-api-python-client>=2.0.0",
    "google-auth>=2.36.0",
    "azure-mgmt-storage>=21.0.0",      # Phase 28: Azure Blob encryption audit (STOR-02)
    "kubernetes>=35.0.0",              # Phase 29: Kubernetes secrets inspection (K8S-01, K8S-02)
    "google-cloud-container>=2.0.0",   # Phase 29: GKE databaseEncryption.state (K8S-01)
    "azure-mgmt-containerservice>=35.0.0",  # Phase 29: AKS Key Vault KMS detection (K8S-01)
]
```

---

### `tests/test_k8s_connector.py` (NEW — test)

**Primary analog:** `tests/test_azure_blob.py` — inline import inside each test, `patch` of
`AVAILABLE` flag, `MagicMock` for SDK client, helper builder function for mock objects.

**Secondary analog:** `tests/test_db_connector.py` lines 38–43 — `AVAILABLE=False` returns `[]`
test pattern, module-level `patch` of the flag.

**File header / import block pattern (from `tests/test_azure_blob.py` lines 1–8):**
```python
"""Tests for K8S secrets inspection — K8S-01 / K8S-02 / K8S-03 (Phase 29).

Tests mock kubernetes, google-cloud-container, and azure-mgmt-containerservice SDK calls.
No live cluster required. Scanner: quirk/scanner/k8s_connector.py
"""
import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
```

**AVAILABLE=False returns inaccessible finding pattern (K8S-03 + SDK-absent):**
```python
def test_sdk_unavailable_produces_inaccessible_finding():
    """K8S_AVAILABLE=False must emit encryption-config-inaccessible endpoint (not empty list)."""
    with patch("quirk.scanner.k8s_connector.K8S_AVAILABLE", False):
        from quirk.scanner.k8s_connector import scan_k8s_targets
        results = scan_k8s_targets(
            provider="gke",
            cluster_name="my-cluster",
            namespace="default",
            logger=None,
        )
    assert len(results) >= 1
    assert any(
        getattr(ep, "scan_error", "") == "encryption-config-inaccessible"
        for ep in results
    )
```

**EKS mock pattern (from `tests/test_db_connector.py` boto3 mock approach):**
```python
def test_eks_unencrypted_produces_high():
    mock_session = MagicMock()
    mock_eks = MagicMock()
    mock_eks.get_paginator.return_value.paginate.return_value = [
        {"clusters": ["my-cluster"]}
    ]
    mock_eks.describe_cluster.return_value = {
        "cluster": {"name": "my-cluster", "encryptionConfig": []}
    }
    mock_session.client.return_value = mock_eks
    from quirk.scanner.aws_connector import _scan_eks_encryption
    results = _scan_eks_encryption(mock_session, logger=None)
    assert len(results) == 1
    assert results[0].severity == "HIGH"
    assert "EKS/unencrypted" in results[0].service_detail
```

**Secret type mock builder (K8S-02):**
```python
def _make_secret_list(types):
    """Build a mock V1SecretList with secrets of given types."""
    mock_secrets = []
    for stype in types:
        s = MagicMock()
        s.type = stype
        mock_secrets.append(s)
    mock_list = MagicMock()
    mock_list.items = mock_secrets
    return mock_list
```

**AKS mock pattern (directly analogous to `tests/test_azure_blob.py` MagicMock structure):**
```python
def test_aks_platform_managed_medium():
    with patch("quirk.scanner.k8s_connector.AKS_AVAILABLE", True), \
         patch("azure.mgmt.containerservice.ContainerServiceClient", create=True) as mock_cls:
        client = MagicMock()
        cluster = MagicMock()
        sec = MagicMock()
        kv_kms = MagicMock()
        kv_kms.enabled = False
        sec.azure_key_vault_kms = kv_kms
        cluster.security_profile = sec
        client.managed_clusters.get.return_value = cluster
        mock_cls.return_value = client
        from quirk.scanner.k8s_connector import _scan_aks_encryption
        results = _scan_aks_encryption(
            credential=MagicMock(),
            subscription_id="sub-1",
            cluster_configs=[{"resource_group": "rg", "name": "my-aks"}],
            logger=None,
        )
    assert len(results) == 1
    assert results[0].service_detail == "AKS/platform-managed"
    assert results[0].severity == "MEDIUM"
```

---

### `labs/kubernetes/expected_results.md` (NEW — lab docs)

**Analog:** `labs/storage/expected_results.md` — markdown structure: Lab header, Lab Setup,
Scanner Configuration, Expected Findings table, UAT pass criteria.

**Key difference from storage lab:** No Docker service is provided (mock-based unit tests only).
Human-UAT note must explain how to point at a real cluster for live verification.

---

## Shared Patterns

### session_start Timestamp Threading (ISSUE-3)

**Source:** `quirk/scanner/aws_connector.py` `_scan_s3_encryption` line 166
**Apply to:** `_scan_eks_encryption`, `_scan_gke_encryption`, `_scan_aks_encryption`,
`_enumerate_secret_types`, `scan_k8s_targets`

```python
ts = (session_start or datetime.now(timezone.utc)).replace(tzinfo=None)
```

### Severity Conditional Assignment

**Source:** `quirk/scanner/aws_connector.py` `_scan_rds_encryption` lines 118–119
**Apply to:** All `_scan_*` functions that produce severity-conditional findings

```python
if severity:
    ep.severity = severity
```

### `dat_scan_json` with `default=str`

**Source:** `quirk/scanner/aws_connector.py` `_scan_s3_encryption` lines 222–224
**Apply to:** All new `CryptoEndpoint` constructions in k8s_connector and aws_connector EKS

```python
dat_scan_json=json.dumps(
    {"bucket": name, **classification}, default=str
),
```

### Inline Import with `except ImportError` Guard

**Source:** `quirk/scanner/azure_connector.py` `_scan_app_gateways` lines 84–86 and
`_scan_blob_encryption` lines 155–159
**Apply to:** `_scan_gke_encryption` and `_scan_aks_encryption` function bodies

```python
try:
    from azure.mgmt.storage import StorageManagementClient  # type: ignore[import-untyped]
except ImportError:
    if logger:
        logger.v("azure-mgmt-storage not installed — Azure Blob scanning unavailable")
    return results
```

### Optional-Dep Flag Test Patching Pattern

**Source:** `tests/test_db_connector.py` line 40 / `tests/test_azure_blob.py` line 29
**Apply to:** All `test_k8s_connector.py` tests that test the AVAILABLE=False path

```python
with patch("quirk.scanner.db_connector.PSYCOPG2_AVAILABLE", False):
    from quirk.scanner.db_connector import scan_pg_targets
    result = scan_pg_targets(targets=["localhost:5432"])
    assert result == []
```

### AVAILABLE Guard at Function Top

**Source:** `quirk/scanner/azure_connector.py` `_scan_blob_encryption` lines 147–150
**Apply to:** `_scan_gke_encryption` (check `GKE_AVAILABLE`), `_scan_aks_encryption` (check `AKS_AVAILABLE`)

```python
if not AZURE_AVAILABLE:
    if logger:
        logger.v("azure SDK not installed — Azure Blob scanning unavailable")
    return results
```

### `getattr` Defensive Access for Optional SDK Attributes

**Source:** `quirk/scanner/azure_connector.py` `_scan_app_gateways` lines 88–93
**Apply to:** AKS `security_profile.azure_key_vault_kms.enabled` access (three nested getattr)

```python
ssl_policy = getattr(gateway, "ssl_policy", None)
if ssl_policy is None:
    continue
min_proto = getattr(ssl_policy, "min_protocol_version", None)
```

---

## No Analog Found

All files have analogs. No new patterns are needed from RESEARCH.md alone.

| File | Notes |
|---|---|
| `quirk/scanner/k8s_connector.py` | Composite of `azure_connector.py` + `db_connector.py`; fully covered |
| `labs/kubernetes/expected_results.md` | Structurally analogous to `labs/storage/expected_results.md`; content differs (mock-only, no Docker service) |

---

## Metadata

**Analog search scope:** `quirk/scanner/`, `quirk/intelligence/`, `quirk/cbom/`, `tests/`, `labs/`
**Files scanned:** 16 source + 5 test files
**Pattern extraction date:** 2026-04-26

**Critical anti-patterns to avoid (from RESEARCH.md):**
1. Do NOT read `secret.data` — only `secret.type` is accessed in K8S-02
2. Do NOT use `google-api-python-client` (`_gcp_build`) for GKE — use `google-cloud-container`
3. Do NOT return `[]` when `K8S_AVAILABLE=False` — K8S-03 requires an explicit inaccessible endpoint
4. Do NOT use kubernetes Python client for EKS etcd detection — use boto3 `describe_cluster` in `aws_connector.py`
5. Do NOT compare GKE `DatabaseEncryption.CurrentState` with strings — use `int(state) == 2`
