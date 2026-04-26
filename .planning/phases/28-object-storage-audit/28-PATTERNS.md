# Phase 28: Object Storage Audit - Pattern Map

**Mapped:** 2026-04-25
**Files analyzed:** 10 modified files + 3 new files
**Analogs found:** 13 / 13

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `quirk/scanner/aws_connector.py` | scanner/service | request-response (boto3 S3) | `quirk/scanner/aws_connector.py` `_scan_rds_encryption()` | exact |
| `quirk/scanner/azure_connector.py` | scanner/service | request-response (mgmt plane) | `quirk/scanner/azure_connector.py` `_scan_app_gateways()` | exact |
| `run_scan.py` | orchestrator | batch | `run_scan.py` db_scanning phase block (lines 480-499) | exact |
| `quirk/config.py` | config | — | `quirk/config.py` `ConnectorsCfg` (existing fields) | exact |
| `quirk/config_template.yaml` | config | — | `quirk/config_template.yaml` `# enable_gcp / enable_db` commented block | exact |
| `quirk/intelligence/evidence.py` | service/transform | batch | `quirk/intelligence/evidence.py` `elif proto == "RDS"` block (lines 160-164) | exact |
| `quirk/intelligence/scoring.py` | service/transform | batch | `quirk/intelligence/scoring.py` `dar_impacts` list (lines 168-172) | exact |
| `quirk/cbom/builder.py` | service/transform | batch | `quirk/cbom/builder.py` `elif ep.protocol in ("POSTGRESQL", "MYSQL", "RDS")` blocks | exact |
| `pyproject.toml` | config | — | `pyproject.toml` `cloud = [...]` extras block (lines 44-47) | exact |
| `tests/test_storage_connectors.py` | test | — | `tests/test_cloud_connectors.py` + `tests/test_db_connector.py` | exact |
| `quantum-chaos-enterprise-lab/docker-compose.yml` | config/infra | — | `localstack-kms-seed` / `vault-seed` service blocks (lines 671-717) | exact |
| `quantum-chaos-enterprise-lab/storage/minio-seed.sh` | utility/infra | — | `quantum-chaos-enterprise-lab/storage/kms-seed.sh` (entrypoint pattern) | role-match |
| `labs/storage/expected_results.md` | documentation | — | `labs/*/expected_results.md` (existing lab docs) | role-match |

---

## Pattern Assignments

### `quirk/scanner/aws_connector.py` — add `_scan_s3_encryption()`

**Analog:** `quirk/scanner/aws_connector.py` `_scan_rds_encryption()` (lines 75-129)

**Imports pattern** (lines 1-23) — already in place, no additions needed:
```python
from __future__ import annotations
import json
from datetime import datetime, timezone
from typing import List, Optional
from quirk.models import CryptoEndpoint

try:
    import boto3
    BOTO3_AVAILABLE = True
except ImportError:
    boto3 = None  # type: ignore[assignment]
    BOTO3_AVAILABLE = False
```

Also add at function scope (inside `_scan_s3_encryption`):
```python
from concurrent.futures import ThreadPoolExecutor
from botocore.exceptions import ClientError
```

**Core pattern — `_scan_rds_encryption()` (lines 85-129) is the direct template:**
```python
def _scan_rds_encryption(session, logger) -> List[CryptoEndpoint]:
    results: List[CryptoEndpoint] = []
    try:
        client = session.client("rds")
        paginator = client.get_paginator("describe_db_instances")
        for page in paginator.paginate():
            for db in page.get("DBInstances", []):
                db_id = db.get("DBInstanceIdentifier", "unknown")
                db_arn = db.get("DBInstanceArn", db_id)
                try:
                    encrypted = db.get("StorageEncrypted", False)
                    kms_key = str(db.get("KmsKeyId") or "").strip()
                    if not encrypted:
                        service_detail = "RDS/none"
                        severity = "HIGH"
                    elif not kms_key:
                        service_detail = "RDS/sse-rds"
                        severity = None
                    ...
                    ep = CryptoEndpoint(
                        host=db_arn,
                        port=db_port,
                        protocol="RDS",
                        service_detail=service_detail,
                        scanned_at=datetime.now(timezone.utc).replace(tzinfo=None),
                    )
                    if severity:
                        ep.severity = severity
                    results.append(ep)
                except Exception as exc:
                    if logger:
                        logger.v(f"RDS instance scan error for {db_id}: {exc}")
    except Exception as exc:
        if logger:
            logger.v(f"RDS scan error: {exc}")
    return results
```

**Critical difference from RDS — S3 `list_buckets` is NOT a paginator (anti-pattern):**
```python
# DO NOT: client.get_paginator("list_buckets")  -> raises OperationNotPageableError
# DO: direct call
buckets = client.list_buckets().get("Buckets", [])
```

**ClientError as detection path (not scan error):**
```python
except ClientError as e:
    code = e.response.get("Error", {}).get("Code", "")
    if code == "ServerSideEncryptionConfigurationNotFoundError":
        # This IS the unencrypted detection path — NOT a scan error
        return {"service_detail": "S3/unencrypted", "severity": "HIGH"}
    if logger:
        logger.v(f"S3 get_bucket_encryption error for {bucket_name}: {e}")
    return None  # genuine access error — skip bucket
```

**session_start parameter (ISSUE-3 pattern — line 116 shows current call; new functions must accept it):**
```python
# Current _scan_rds_encryption uses: datetime.now(timezone.utc).replace(tzinfo=None)
# New _scan_s3_encryption must instead accept and use:
def _scan_s3_encryption(session, logger, session_start=None) -> List[CryptoEndpoint]:
    ...
    scanned_at=(session_start or datetime.now(timezone.utc)).replace(tzinfo=None),
```

**dat_scan_json field (Phase 27 column, follow cloud_scan_json pattern from KMS/ACM):**
```python
# Existing cloud_scan_json usage (aws_connector.py lines 63, 153, 191):
cloud_scan_json=json.dumps(detail, default=str),
# Phase 28 equivalent on storage rows:
dat_scan_json=json.dumps({"bucket": name, **enc}, default=str),
```

**scan_aws_targets() call site (lines 255-261) — add `_scan_s3_encryption` call conditionally in run_scan.py, NOT inside scan_aws_targets():**
```python
def scan_aws_targets(region, profile=None, logger=None) -> List[CryptoEndpoint]:
    if not BOTO3_AVAILABLE:
        ...
        return []
    session = boto3.Session(region_name=region, profile_name=profile)
    results: List[CryptoEndpoint] = []
    results.extend(_scan_kms(session, logger))
    results.extend(_scan_cloudfront(session, logger))
    results.extend(_scan_elbv2(session, logger))
    results.extend(_scan_acm(session, logger))
    results.extend(_scan_rds_encryption(session, logger))
    # _scan_s3_encryption is called from run_scan.py (enable_s3 guard), NOT here
    return results
```

---

### `quirk/scanner/azure_connector.py` — add `_scan_blob_encryption()`

**Analog:** `quirk/scanner/azure_connector.py` `_scan_app_gateways()` (lines 79-116)

**Module-level import guard (lines 17-27) — AZURE_AVAILABLE stays unchanged; azure-mgmt-storage import goes INSIDE the function body:**
```python
# Module level (existing — do NOT change):
try:
    from azure.identity import DefaultAzureCredential
    from azure.keyvault.keys import KeyClient
    from azure.keyvault.certificates import CertificateClient
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False
    DefaultAzureCredential = None  # type: ignore[assignment,misc]
    ...

# Inside _scan_blob_encryption() function body (follow _scan_app_gateways pattern line 83):
try:
    from azure.mgmt.storage import StorageManagementClient  # type: ignore[import-untyped]
    ...
except ImportError:
    if logger:
        logger.v("azure-mgmt-storage not installed — Azure Blob scanning unavailable")
    return results
```

**Core pattern — `_scan_app_gateways()` (lines 79-116) is the direct template:**
```python
def _scan_app_gateways(credential, subscription_id: str, logger) -> List[CryptoEndpoint]:
    results: List[CryptoEndpoint] = []
    try:
        from azure.mgmt.network import NetworkManagementClient  # inline import
        client = NetworkManagementClient(credential, subscription_id)
        for gateway in client.application_gateways.list_all():
            try:
                ssl_policy = getattr(gateway, "ssl_policy", None)
                if ssl_policy is None:
                    continue
                ...
                ep = CryptoEndpoint(
                    host=gateway.id,
                    port=443,
                    protocol="AZURE",
                    ...
                    cloud_scan_json=json.dumps(ssl_policy_dict, default=str),
                    service_detail="AppGateway",
                )
                results.append(ep)
            except Exception as exc:
                if logger:
                    logger.v(f"AppGateway policy scan error: {exc}")
    except ImportError:
        if logger:
            logger.v("azure-mgmt-network not installed — App Gateway scanning unavailable")
    except Exception as exc:
        if logger:
            logger.v(f"App Gateway scan error: {exc}")
    return results
```

**Key differences for `_scan_blob_encryption`:**
- `protocol="AZURE_BLOB"` (not `"AZURE"`)
- `dat_scan_json=json.dumps({...}, default=str)` (not `cloud_scan_json`)
- Resource group extraction from ARM resource ID: `account.id.split("/resourceGroups/")[1].split("/")[0]`
- `keySource` normalization: `str(getattr(enc, "key_source", "") or "").lower()` then compare `"microsoft.keyvault"` / `"microsoft.storage"`
- Accept `session_start=None` parameter; use `(session_start or datetime.now(timezone.utc)).replace(tzinfo=None)` for `scanned_at`

**scan_azure_targets() call site (lines 119-146) — add blob call at the end:**
```python
def scan_azure_targets(subscription_id, keyvault_urls=None, logger=None):
    if not AZURE_AVAILABLE:
        ...
        return []
    credential = DefaultAzureCredential()
    results: List[CryptoEndpoint] = []
    for vault_url in (keyvault_urls or []):
        results.extend(_scan_keyvault_keys(credential, vault_url, logger))
    if subscription_id:
        results.extend(_scan_app_gateways(credential, subscription_id, logger))
    # _scan_blob_encryption is called from run_scan.py (enable_blob guard), NOT here
    return results
```

---

### `run_scan.py` — add S3, Azure Blob, and GCS re-use phase blocks

**Analog:** `run_scan.py` db_scanning phase block (lines 474-499)

**session_start pattern (line 475) — already established, Phase 28 reuses it:**
```python
# Line 474-475 in run_scan.py (existing):
# ── Shared identity-scan session timestamp (ISSUE-3 fix) ──
session_start = datetime.now(timezone.utc)
```

**DB scanning block (lines 480-499) — exact template for S3 and Azure Blob blocks:**
```python
db_endpoints = []
with _phase_timer(run_stats, "db_scanning"):
    if cfg.connectors.enable_db:
        from quirk.scanner.db_connector import scan_pg_targets, scan_mysql_targets
        if cfg.connectors.pg_targets:
            db_endpoints.extend(scan_pg_targets(
                targets=cfg.connectors.pg_targets,
                user=cfg.connectors.pg_scanner_user,
                password=cfg.connectors.pg_scanner_password,
                logger=logger,
                session_start=session_start,
            ))
```

**New S3 scanning block (copy db_scanning pattern):**
```python
s3_endpoints = []
with _phase_timer(run_stats, "s3_scanning"):
    if cfg.connectors.enable_s3:
        from quirk.scanner.aws_connector import _scan_s3_encryption
        if not BOTO3_AVAILABLE:  # or check inside _scan_s3_encryption
            pass
        else:
            s3_session = boto3.Session(
                region_name=cfg.connectors.aws_region,
                profile_name=cfg.connectors.aws_profile,
            )
            s3_client_kwargs = {}
            if getattr(cfg.connectors, "aws_endpoint_url", None):
                s3_client_kwargs["endpoint_url"] = cfg.connectors.aws_endpoint_url
            s3_endpoints = _scan_s3_encryption(
                session=s3_session,
                logger=logger,
                session_start=session_start,
                endpoint_url=cfg.connectors.aws_endpoint_url or None,
            )
```

**GCS re-use block (follows same `with _phase_timer` pattern; reads from in-memory gcp_endpoints):**
```python
# After gcp_scanning block (lines 466-472), before session_start assignment:
# gcp_endpoints is already populated — read sentinel from it, no new API call
gcs_storage_endpoints = []
sentinel = next(
    (ep for ep in gcp_endpoints if getattr(ep, "cert_pubkey_alg", "") == "GCS-SUMMARY"),
    None,
)
# sentinel consumed — Phase 26 per-bucket rows already in gcp_endpoints (STOR-03 satisfied)
```

**Existing AWS scanning block (lines 442-449) — shows the enable guard pattern:**
```python
aws_endpoints = []
with _phase_timer(run_stats, "aws_scanning"):
    if cfg.connectors.enable_aws:
        aws_endpoints = scan_aws_targets(
            region=cfg.connectors.aws_region,
            profile=cfg.connectors.aws_profile,
            logger=logger,
        )
```

---

### `quirk/config.py` — extend `ConnectorsCfg`

**Analog:** `quirk/config.py` `ConnectorsCfg` dataclass (lines 45-80)

**Existing pattern for Phase 27 DB fields (lines 72-80) — add storage fields immediately after:**
```python
# Phase 27 additions (lines 72-80) — copy this pattern:
# DB connector config (v4.3, Phase 27, per D-03)
enable_db: bool = False
pg_targets: list = field(default_factory=list)
pg_scanner_user: Optional[str] = None
pg_scanner_password: Optional[str] = None
mysql_targets: list = field(default_factory=list)
mysql_scanner_user: Optional[str] = None
mysql_scanner_password: Optional[str] = None

# Phase 28 additions — follow same pattern:
# Object storage connector config (v4.3, Phase 28)
enable_s3: bool = False
enable_blob: bool = False
aws_endpoint_url: Optional[str] = None  # for MinIO/LocalStack override
```

**`_KNOWN_CONNECTOR_KEYS` (line 127) — automatically includes new fields via `dataclasses.fields(ConnectorsCfg)`, no change needed:**
```python
_KNOWN_CONNECTOR_KEYS = {f.name for f in dataclasses.fields(ConnectorsCfg)}
```

---

### `quirk/config_template.yaml` — add storage connector entries

**Analog:** `quirk/config_template.yaml` existing GCP/DB commented block:
```yaml
# -- GCP connector (optional, requires: pip install quirk[cloud]) --
# enable_gcp: false
# gcp_project_id: "my-gcp-project"
# -- Database connector (optional, requires: pip install quirk[db]) --
# enable_db: false
```

**New entries to add (follow same commented pattern):**
```yaml
  # -- Object storage connectors (optional, requires: pip install quirk[cloud]) --
  # enable_s3: false
  # aws_endpoint_url: null            # override for MinIO/LocalStack testing
  # enable_blob: false
```

---

### `quirk/intelligence/evidence.py` — add `dar_storage_*` counters

**Analog:** `quirk/intelligence/evidence.py` `elif proto == "RDS"` block (lines 160-164) and `_PROTOCOL_KEYS` (line 9)

**`_PROTOCOL_KEYS` (line 9) — add `"S3"` and `"AZURE_BLOB"` to this tuple:**
```python
# Existing (line 9):
_PROTOCOL_KEYS = ("TLS", "HTTP", "SSH", "UNKNOWN", "KERBEROS", "SAML", "DNSSEC", "POSTGRESQL", "MYSQL", "RDS")

# Phase 28 — extend with:
_PROTOCOL_KEYS = ("TLS", "HTTP", "SSH", "UNKNOWN", "KERBEROS", "SAML", "DNSSEC",
                  "POSTGRESQL", "MYSQL", "RDS", "S3", "AZURE_BLOB")
```

**Counter initialization (line 78-79) — add alongside `dar_db_*` counters:**
```python
# Existing (lines 78-79):
dar_db_plaintext_count = 0    # PG ssl=off + MySQL SSL disabled
dar_db_weak_ssl_count = 0     # MySQL weak cipher

# Phase 28 additions:
dar_storage_unencrypted_count = 0   # S3 HIGH + Azure Blob absent keySource
dar_storage_aws_managed_count = 0   # S3 SSE-KMS-AWS + Azure Blob platform-managed
```

**Per-endpoint counter logic (follow RDS block pattern, lines 160-164):**
```python
# Existing RDS block (lines 160-164):
elif proto == "RDS":
    sd = str(getattr(ep, "service_detail", "") or "")
    if "RDS/none" in sd:
        dar_db_plaintext_count += 1
    # RDS/sse-rds and RDS/sse-kms-* are positive posture — no penalty

# Phase 28 additions — same elif chain pattern:
elif proto == "S3":
    sd = str(getattr(ep, "service_detail", "") or "")
    if "S3/unencrypted" in sd:
        dar_storage_unencrypted_count += 1
    elif "S3/sse-kms-aws" in sd:
        dar_storage_aws_managed_count += 1

elif proto == "AZURE_BLOB":
    sd = str(getattr(ep, "service_detail", "") or "")
    if "BLOB/platform-managed" in sd:
        dar_storage_aws_managed_count += 1
```

**Return dict (lines 184-220) — add storage entries alongside `dar_db_*` entries (lines 216-219):**
```python
# Existing (lines 216-219):
"dar_db_plaintext_count": dar_db_plaintext_count,
"dar_db_weak_ssl_count": dar_db_weak_ssl_count,
"dar_db_plaintext_ratio": round(dar_db_plaintext_count / total_endpoints, 4) if total_endpoints else 0.0,
"dar_db_weak_ssl_ratio": round(dar_db_weak_ssl_count / total_endpoints, 4) if total_endpoints else 0.0,

# Phase 28 additions:
"dar_storage_unencrypted_count": dar_storage_unencrypted_count,
"dar_storage_aws_managed_count": dar_storage_aws_managed_count,
"dar_storage_unencrypted_ratio": round(dar_storage_unencrypted_count / total_endpoints, 4) if total_endpoints else 0.0,
"dar_storage_aws_managed_ratio": round(dar_storage_aws_managed_count / total_endpoints, 4) if total_endpoints else 0.0,
```

---

### `quirk/intelligence/scoring.py` — add `dar_storage_*` weights

**Analog:** `quirk/intelligence/scoring.py` `SCORE_WEIGHTS` dict (lines 5-25) and `dar_impacts` list (lines 168-172)

**`SCORE_WEIGHTS` (lines 19-20) — add after existing `dar_db_*` entries:**
```python
# Existing (lines 19-20):
"dar_db_plaintext_ratio": 12.0,
"dar_db_weak_ssl_ratio": 6.0,

# Phase 28 additions — immediately after:
"dar_storage_unencrypted_ratio": 12.0,   # same weight as plaintext DB (D-10)
"dar_storage_aws_managed_ratio": 4.0,    # compliance gap, not active weakness (D-10)
```

**Evidence extraction (lines 129-130) — add alongside `dar_db_*` extraction:**
```python
# Existing (lines 129-130):
dar_db_plaintext = max(0, _as_int(evidence.get("dar_db_plaintext_count", 0)))
dar_db_weak_ssl = max(0, _as_int(evidence.get("dar_db_weak_ssl_count", 0)))

# Phase 28 additions:
dar_storage_unencrypted = max(0, _as_int(evidence.get("dar_storage_unencrypted_count", 0)))
dar_storage_aws_managed = max(0, _as_int(evidence.get("dar_storage_aws_managed_count", 0)))
```

**`dar_impacts` list (lines 168-172) — append two new tuples:**
```python
# Existing (lines 168-172):
dar_impacts: List[Tuple[str, float]] = [
    ("Database plaintext connections", -_ratio(dar_db_plaintext, denom) * w["dar_db_plaintext_ratio"]),
    ("Database weak SSL configuration", -_ratio(dar_db_weak_ssl, denom) * w["dar_db_weak_ssl_ratio"]),
]

# Phase 28 additions — extend the list:
dar_impacts: List[Tuple[str, float]] = [
    ("Database plaintext connections", -_ratio(dar_db_plaintext, denom) * w["dar_db_plaintext_ratio"]),
    ("Database weak SSL configuration", -_ratio(dar_db_weak_ssl, denom) * w["dar_db_weak_ssl_ratio"]),
    ("Object storage unencrypted", -_ratio(dar_storage_unencrypted, denom) * w["dar_storage_unencrypted_ratio"]),
    ("Object storage platform-managed keys", -_ratio(dar_storage_aws_managed, denom) * w["dar_storage_aws_managed_ratio"]),
]
```

**`PROFILE_MULTIPLIERS` (lines 27-31) — no change needed; `"dar_"` prefix already covers new weights:**
```python
PROFILE_MULTIPLIERS: Dict[str, Dict[str, float]] = {
    "strict":   {"agility_": 1.4, "identity_": 1.4, "dar_": 1.4},
    "balanced": {"agility_": 1.0, "identity_": 1.0, "dar_": 1.0},
    "lenient":  {"agility_": 0.7, "identity_": 0.7, "dar_": 0.7},
}
```

---

### `quirk/cbom/builder.py` — extend Pass 1/2/3 skip lists

**Analog:** `quirk/cbom/builder.py` existing `elif ep.protocol in ("POSTGRESQL", "MYSQL", "RDS")` blocks

**Pass 1 — algorithm registration (line 385-413):**
```python
# Existing block (lines 410-413):
elif ep.protocol in ("POSTGRESQL", "MYSQL", "RDS"):
    # DB config findings — no key material to catalog.
    # Security signal is in service_detail; CBOM algorithm catalog not applicable.
    pass

# Phase 28 addition — add S3 and AZURE_BLOB to same pass block:
elif ep.protocol in ("POSTGRESQL", "MYSQL", "RDS", "S3", "AZURE_BLOB"):
    # Storage/DB config findings — no key material to catalog.
    pass
```

**Pass 2 — certificate components skip (line 436-438):**
```python
# Existing (lines 436-438):
if ep.protocol in ("SSH", "CONTAINER", "SOURCE", "KERBEROS", "SAML", "DNSSEC",
                   "GCP", "CLOUD_SQL", "POSTGRESQL", "MYSQL", "RDS"):
    continue

# Phase 28 — add S3 and AZURE_BLOB to skip tuple:
if ep.protocol in ("SSH", "CONTAINER", "SOURCE", "KERBEROS", "SAML", "DNSSEC",
                   "GCP", "CLOUD_SQL", "POSTGRESQL", "MYSQL", "RDS",
                   "S3", "AZURE_BLOB"):
    continue
```

**Pass 3 — protocol components skip (lines 516-520):**
```python
# Existing (lines 516-520):
elif ep.protocol in ("JWT", "CONTAINER", "SOURCE", "AWS", "AZURE", "GCP", "CLOUD_SQL",
                     "DNSSEC", "SAML", "KERBEROS", "POSTGRESQL", "MYSQL", "RDS"):
    continue

# Phase 28 — add S3 and AZURE_BLOB:
elif ep.protocol in ("JWT", "CONTAINER", "SOURCE", "AWS", "AZURE", "GCP", "CLOUD_SQL",
                     "DNSSEC", "SAML", "KERBEROS", "POSTGRESQL", "MYSQL", "RDS",
                     "S3", "AZURE_BLOB"):
    continue
```

---

### `pyproject.toml` — add `azure-mgmt-storage` to `[cloud]` extras

**Analog:** `pyproject.toml` `[cloud]` extras block (lines 44-47)

**Existing block:**
```toml
cloud = [
    "google-api-python-client>=2.0.0",
    "google-auth>=2.36.0",
]
```

**Phase 28 addition:**
```toml
cloud = [
    "google-api-python-client>=2.0.0",
    "google-auth>=2.36.0",
    "azure-mgmt-storage>=21.0.0",   # Phase 28: Azure Blob encryption audit (STOR-02)
]
```

---

### `tests/test_storage_connectors.py` — new test file

**Analog:** `tests/test_cloud_connectors.py` (lines 1-80) + `tests/test_db_connector.py` (lines 1-60)

**File header and import pattern (test_cloud_connectors.py lines 1-17):**
```python
"""Tests for S3, Azure Blob, and GCS re-use storage connectors (STOR-01, STOR-02, STOR-03).

Tests mock boto3/azure-mgmt-storage SDK calls to avoid requiring cloud credentials.
Scanner modules: quirk/scanner/aws_connector.py (_scan_s3_encryption),
                 quirk/scanner/azure_connector.py (_scan_blob_encryption)
"""
import json
import pytest
from unittest.mock import patch, MagicMock, call

from quirk.scanner.aws_connector import _scan_s3_encryption
from quirk.scanner.azure_connector import _scan_blob_encryption
```

**BOTO3_AVAILABLE unavailable guard pattern (test_cloud_connectors.py lines 75-79):**
```python
def test_s3_unavailable_returns_empty():
    """If boto3 is not importable, _scan_s3_encryption must return empty list."""
    with patch("quirk.scanner.aws_connector.BOTO3_AVAILABLE", False):
        result = _scan_s3_encryption(session=MagicMock(), logger=None)
        assert result == []
```

**Mock session pattern for per-function scanner tests (test_cloud_connectors.py lines 39-46):**
```python
mock_client = MagicMock()
mock_session = MagicMock()
mock_session.client.return_value = mock_client

with patch("quirk.scanner.aws_connector.boto3.Session", return_value=mock_session):
    endpoints = scan_aws_targets(region="us-east-1", profile=None)
```

**ClientError mock pattern for S3 unencrypted detection test:**
```python
from botocore.exceptions import ClientError

def test_s3_no_encryption_config_error():
    """ServerSideEncryptionConfigurationNotFoundError must map to HIGH/S3/unencrypted."""
    mock_client = MagicMock()
    mock_client.list_buckets.return_value = {"Buckets": [{"Name": "my-bucket"}]}
    error_response = {"Error": {"Code": "ServerSideEncryptionConfigurationNotFoundError"}}
    mock_client.get_bucket_encryption.side_effect = ClientError(error_response, "GetBucketEncryption")
    # ... assert ep.severity == "HIGH" and "S3/unencrypted" in ep.service_detail
```

**ImportError guard for azure-mgmt-storage (test_db_connector.py lines 38-43 pattern):**
```python
def test_azure_blob_mgmt_storage_unavailable():
    """_scan_blob_encryption must return [] when azure-mgmt-storage is not installed."""
    with patch("builtins.__import__", side_effect=ImportError("azure.mgmt.storage")):
        result = _scan_blob_encryption(credential=MagicMock(), subscription_id="sub-123", logger=None)
        assert result == []
```

---

### `quantum-chaos-enterprise-lab/docker-compose.yml` — add `storage-s3` profile

**Analog:** `quantum-chaos-enterprise-lab/docker-compose.yml` `localstack-kms-seed` + `vault-seed` blocks (lines 671-717)

**`localstack-kms-seed` block (lines 671-684) is the exact seed container template:**
```yaml
localstack-kms-seed:
  image: amazon/aws-cli:latest
  profiles: ["storage"]
  restart: "no"
  depends_on:
    localstack-kms:
      condition: service_healthy
  volumes:
    - ./storage/kms-seed.sh:/kms-seed.sh:ro
  environment:
    - AWS_DEFAULT_REGION=us-east-1
    - AWS_ACCESS_KEY_ID=test
    - AWS_SECRET_ACCESS_KEY=test
  entrypoint: ["/bin/sh", "/kms-seed.sh"]
```

**`vault-seed` block (lines 704-717) shows `restart: "no"` + `service_healthy` condition pattern:**
```yaml
vault-seed:
  image: hashicorp/vault:1.15
  profiles: ["storage"]
  restart: "no"
  depends_on:
    vault:
      condition: service_healthy
  volumes:
    - ./storage/vault-seed.sh:/vault-seed.sh:ro
  entrypoint: ["/bin/sh", "/vault-seed.sh"]
```

**Profile name — CRITICAL:** Use `"storage-s3"` (not `"storage"` — already taken by vault/localstack-kms/pgcrypto from Phase 27, lines 657-730).

**New MinIO service block follows the same structure; ports use safe range 29000-29001:**
```yaml
minio:
  image: minio/minio:latest
  profiles: ["storage-s3"]
  command: server /data --console-address ":9001"
  environment:
    MINIO_ROOT_USER: minioadmin
    MINIO_ROOT_PASSWORD: minioadmin
  ports:
    - "29000:9000"
    - "29001:9001"
  healthcheck:
    test: ["CMD", "mc", "ready", "local"]
    interval: 5s
    timeout: 5s
    retries: 10
    start_period: 10s

minio-seed:
  image: minio/mc:latest
  profiles: ["storage-s3"]
  restart: "no"
  depends_on:
    minio:
      condition: service_healthy
  entrypoint: ["/bin/sh", "/minio-seed.sh"]
  volumes:
    - ./storage/minio-seed.sh:/minio-seed.sh:ro
```

---

### `quantum-chaos-enterprise-lab/storage/minio-seed.sh` — new init script

**Analog:** `quantum-chaos-enterprise-lab/storage/kms-seed.sh` (entrypoint shell script pattern; referenced at line 679)

The kms-seed.sh pattern: single shell script executed by the seed container's entrypoint. For minio-seed.sh, use `mc` commands:
```bash
#!/bin/sh
set -e
mc alias set local http://minio:9000 minioadmin minioadmin
mc mb local/encrypted-bucket
mc mb local/unencrypted-bucket
# Enable SSE-S3 on encrypted-bucket (validates no-finding path)
mc encrypt set sse-s3 local/encrypted-bucket
# unencrypted-bucket intentionally left without encryption policy (HIGH finding path)
echo "MinIO seed complete"
```

---

## Shared Patterns

### Optional Import Guard (BOTO3/AZURE_AVAILABLE)
**Source:** `quirk/scanner/aws_connector.py` lines 17-23, `quirk/scanner/azure_connector.py` lines 17-27
**Apply to:** All new scanner functions
```python
# Module-level (controls AVAILABLE flag and test patching):
try:
    import boto3
    BOTO3_AVAILABLE = True
except ImportError:
    boto3 = None  # type: ignore[assignment]
    BOTO3_AVAILABLE = False

# Function-body inline import (for optional management-plane SDKs):
try:
    from azure.mgmt.storage import StorageManagementClient
    ...
except ImportError:
    if logger:
        logger.v("azure-mgmt-storage not installed — Azure Blob scanning unavailable")
    return results
```

### CryptoEndpoint Construction with Conditional Severity
**Source:** `quirk/scanner/aws_connector.py` lines 111-119 (`_scan_rds_encryption`)
**Apply to:** `_scan_s3_encryption`, `_scan_blob_encryption`
```python
ep = CryptoEndpoint(
    host=db_arn,
    port=db_port,
    protocol="RDS",
    service_detail=service_detail,
    scanned_at=datetime.now(timezone.utc).replace(tzinfo=None),
)
if severity:
    ep.severity = severity
results.append(ep)
```
Phase 28 replaces `datetime.now(timezone.utc)` with `(session_start or datetime.now(timezone.utc))`.

### Per-Endpoint Exception Handling with logger.v()
**Source:** `quirk/scanner/aws_connector.py` lines 122-124, `quirk/scanner/azure_connector.py` lines 108-109
**Apply to:** All inner try/except blocks in storage scan functions
```python
except Exception as exc:
    if logger:
        logger.v(f"[service] scan error for {identifier}: {exc}")
```

### session_start Pass-Through (ISSUE-3)
**Source:** `run_scan.py` lines 474-499
**Apply to:** `_scan_s3_encryption`, `_scan_blob_encryption`, run_scan.py S3/blob phase blocks
```python
# Set once in run_scan.py before all new scanner blocks:
session_start = datetime.now(timezone.utc)   # line 475

# Pass through to every new scanner function that creates CryptoEndpoints:
session_start=session_start,

# Used inside scanner function (not datetime.now() directly):
scanned_at=(session_start or datetime.now(timezone.utc)).replace(tzinfo=None),
```

### `_phase_timer` Scan Block
**Source:** `run_scan.py` lines 440-499 (aws/azure/gcp/db scanning blocks)
**Apply to:** S3 scanning block, Azure Blob scanning block in run_scan.py
```python
s3_endpoints = []
with _phase_timer(run_stats, "s3_scanning"):
    if cfg.connectors.enable_s3:
        ...
```

### Evidence Counter Pattern (dar_ subscore)
**Source:** `quirk/intelligence/evidence.py` lines 77-79, 160-164, 216-219
**Apply to:** `dar_storage_unencrypted_count`, `dar_storage_aws_managed_count`
- Initialize counter variable to `0` before the for-ep loop
- Increment inside `elif proto == "S3":` / `elif proto == "AZURE_BLOB":` blocks
- Return as both raw count and ratio in the dict

### json.dumps with default=str
**Source:** `quirk/scanner/aws_connector.py` lines 63, 153 (`cloud_scan_json=json.dumps(detail, default=str)`)
**Apply to:** All `dat_scan_json` assignments in storage scan functions
```python
dat_scan_json=json.dumps({"bucket": name, "service_detail": sd, ...}, default=str),
```

---

## No Analog Found

All Phase 28 files have close analogs in the codebase. The only file with a partial match:

| File | Role | Data Flow | Note |
|------|------|-----------|------|
| `labs/storage/expected_results.md` | documentation | — | Pattern from existing `labs/*/expected_results.md` files; content is new but format follows existing lab docs |

---

## Metadata

**Analog search scope:** `quirk/scanner/`, `quirk/intelligence/`, `quirk/cbom/`, `quirk/`, `run_scan.py`, `tests/`, `quantum-chaos-enterprise-lab/`, `pyproject.toml`
**Files scanned:** 13 source files read directly
**Pattern extraction date:** 2026-04-25
