# Phase 26: GCP Connector - Pattern Map

**Mapped:** 2026-04-24
**Files analyzed:** 9
**Analogs found:** 9 / 9

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `quirk/scanner/gcp_connector.py` | service | request-response | `quirk/scanner/aws_connector.py` + `quirk/scanner/azure_connector.py` | exact |
| `quirk/db.py` | utility | CRUD | `quirk/db.py` (`_ensure_identity_columns`) | exact (self-extension) |
| `quirk/config.py` | config | — | `quirk/config.py` (`ConnectorsCfg`) | exact (self-extension) |
| `quirk/config_template.yaml` | config | — | `quirk/config_template.yaml` (identity block) | exact (self-extension) |
| `quirk/models.py` | model | CRUD | `quirk/models.py` (v4.2 identity fields) | exact (self-extension) |
| `run_scan.py` | utility | request-response | `run_scan.py` (aws/azure scan phases) | exact (self-extension) |
| `quirk/cbom/builder.py` | service | transform | `quirk/cbom/builder.py` (AWS/AZURE branch, Pass 3 skip list) | exact (self-extension) |
| `pyproject.toml` | config | — | `pyproject.toml` (`[identity]` extras group) | exact (self-extension) |
| `tests/test_cloud_connectors.py` | test | request-response | `tests/test_cloud_connectors.py` (AWS/Azure test classes) | exact (self-extension) |

---

## Pattern Assignments

### `quirk/scanner/gcp_connector.py` (service, request-response)

**Primary analog:** `quirk/scanner/aws_connector.py`
**Secondary analog:** `quirk/scanner/azure_connector.py`

**Module docstring pattern** (`aws_connector.py` lines 1-6):
```python
"""GCP cloud connector for cryptographic resource enumeration (GCP-01, GCP-02, GCP-03).

Scans Cloud KMS key specs, Cloud SQL TLS enforcement, and GCS bucket encryption.
Uses Application Default Credentials (ADC) — no credentials stored in this module.
Degrades gracefully when google-api-python-client is not installed.
"""
```

**Imports pattern** (`aws_connector.py` lines 7-12 + `azure_connector.py` lines 7-12):
```python
from __future__ import annotations

import json
from typing import List, Optional

from quirk.models import CryptoEndpoint
```

**Optional import / availability flag** (`azure_connector.py` lines 18-27 — use this form, not aws form, because GCP needs module-level None assignments for all names):
```python
# ---------------------------------------------------------------------------
# google-api-python-client optional import (D-02)
# Names must remain at module level (even as None) for test patching.
# ---------------------------------------------------------------------------
try:
    from googleapiclient.discovery import build as _gcp_build
    import google.auth
    from google.auth.exceptions import DefaultCredentialsError
    GCP_AVAILABLE = True
except ImportError:
    _gcp_build = None           # type: ignore[assignment]
    google = None               # type: ignore[assignment]
    DefaultCredentialsError = None  # type: ignore[assignment]
    GCP_AVAILABLE = False
```

**Algorithm map pattern** (`aws_connector.py` lines 27-41 — `KMS_KEY_SPEC_MAP`):
```python
KMS_KEY_SPEC_MAP = {
    "RSA_2048": ("RSA", 2048),
    "RSA_3072": ("RSA", 3072),
    ...
    "SYMMETRIC_DEFAULT": ("AES", 256),
    "HMAC_224": ("HMAC", 224),
    ...
}
```
For GCP, replicate as `GCP_KMS_ALGORITHM_MAP` with all 47 entries from RESEARCH.md. Same `(algorithm, key_size)` tuple structure.

**Private scan function signature** (`aws_connector.py` lines 74-105 — `_scan_kms`):
```python
def _scan_kms(session, logger) -> List[CryptoEndpoint]:
    """Enumerate KMS keys and map their KeySpec to algorithm/size."""
    results: List[CryptoEndpoint] = []
    try:
        client = session.client("kms")
        paginator = client.get_paginator("list_keys")
        for page in paginator.paginate():
            for key_entry in page.get("Keys", []):
                key_id = key_entry.get("KeyId", "")
                try:
                    metadata = client.describe_key(KeyId=key_id).get("KeyMetadata", {})
                    ...
                    ep = CryptoEndpoint(
                        host=arn,
                        port=0,
                        protocol="AWS",
                        cert_pubkey_alg=alg_name,
                        cert_pubkey_size=key_size,
                        cloud_scan_json=json.dumps(metadata, default=str),
                        service_detail="KMS",
                    )
                    results.append(ep)
                except Exception as exc:
                    if logger:
                        logger.v(f"KMS describe_key failed for {key_id}: {exc}")
    except Exception as exc:
        if logger:
            logger.v(f"KMS scan error: {exc}")
    return results
```
For GCP functions: replace `session.client(...)` / `paginator` with Discovery API `list()` + `list_next()` pagination. Replace `protocol="AWS"` with `protocol="GCP"` or `protocol="CLOUD_SQL"` as appropriate. Keep the per-resource inner try/except inside an outer try/except — identical error handling structure.

**Public entry-point pattern** (`aws_connector.py` lines 175-202 — `scan_aws_targets`):
```python
def scan_aws_targets(
    region: str,
    profile: Optional[str] = None,
    logger=None,
) -> List[CryptoEndpoint]:
    if not BOTO3_AVAILABLE:
        if logger:
            logger.v("boto3 not installed — AWS scanning unavailable")
        return []
    session = boto3.Session(region_name=region, profile_name=profile)
    results: List[CryptoEndpoint] = []
    results.extend(_scan_kms(session, logger))
    results.extend(_scan_cloudfront(session, logger))
    results.extend(_scan_elbv2(session, logger))
    results.extend(_scan_acm(session, logger))
    return results
```
For GCP: signature is `scan_gcp_targets(project_id: str, logger=None) -> List[CryptoEndpoint]`. Guard on `GCP_AVAILABLE`. Call `google.auth.default()` once, pass `credentials` to all three `build()` calls. Extend with `gcs_scan_json` write pattern per RESEARCH.md Pattern 4.

**GCS data serialization** — no direct analog; follow RESEARCH.md Pattern 4 exactly:
- One sentinel `CryptoEndpoint` with `gcs_scan_json=json.dumps(bucket_list, default=str)` carries the full list
- Separate per-bucket `CryptoEndpoint` rows for individual findings (no `gcs_scan_json` on those)

---

### `quirk/db.py` (utility, CRUD — `_ensure_gcp_columns`)

**Analog:** `quirk/db.py` lines 38-57 and 60-78

**Column list + migration function** (lines 38-57):
```python
_IDENTITY_COLUMNS = [
    "kerberos_scan_json",
    "saml_scan_json",
    "dnssec_scan_json",
]


def _ensure_identity_columns(engine) -> None:
    """Add identity scanner JSON columns to crypto_endpoints if absent (idempotent).

    Uses SQLAlchemy inspector to check existing columns before ALTER TABLE.
    Called from init_db() after create_all(). Per D-01: inspector-first,
    no exception-for-control-flow.
    """
    existing = {c["name"] for c in sa_inspect(engine).get_columns("crypto_endpoints")}
    with engine.connect() as conn:
        for col in _IDENTITY_COLUMNS:
            if col not in existing:
                conn.execute(text(f"ALTER TABLE crypto_endpoints ADD COLUMN {col} TEXT"))
        conn.commit()
```
Replicate as `_GCP_COLUMNS = ["gcs_scan_json"]` and `_ensure_gcp_columns(engine)` with identical inspector-first structure.

**`init_db` call site** (lines 60-78):
```python
def init_db(db_path: str) -> Engine:
    engine = get_engine(db_path)
    with engine.connect() as conn:
        conn.commit()
    Base.metadata.create_all(engine)
    _ensure_identity_columns(engine)  # v4.2: add identity columns if missing
    return engine
```
Add `_ensure_gcp_columns(engine)` on the line immediately after `_ensure_identity_columns(engine)`, with a `# v4.3: add GCP columns if missing` comment.

---

### `quirk/config.py` (config — `ConnectorsCfg` extension)

**Analog:** `quirk/config.py` lines 44-68

**Existing `ConnectorsCfg` pattern** (lines 44-68):
```python
@dataclass
class ConnectorsCfg:
    enable_aws: bool = False
    enable_azure: bool = False
    # Phase 3 scanner enable flags (per D-04)
    enable_jwt: bool = False
    ...
    # Identity connector enable flags (v4.2, per D-04)
    enable_kerberos: bool = False
    enable_saml: bool = False
    enable_dnssec: bool = False
    # Identity connector target lists (v4.2, per D-05)
    kerberos_targets: list = field(default_factory=list)
    saml_targets: list = field(default_factory=list)
    dnssec_targets: list = field(default_factory=list)
```
Add at the end of the dataclass body, following the identity block pattern:
```python
    # GCP connector config (v4.3, Phase 26)
    enable_gcp: bool = False
    gcp_project_id: Optional[str] = None
```
No `field(default_factory=list)` needed — no list fields for GCP in this phase.

---

### `quirk/config_template.yaml` (config — connectors block extension)

**Analog:** `quirk/config_template.yaml` lines 61-70 (identity connectors commented block)

**Existing identity block pattern** (lines 61-70):
```yaml
  # -- Identity connectors (optional, requires: pip install quirk[identity]) --
  # enable_kerberos: false
  # kerberos_targets:
  #   - "kdc.example.com"       # KDC hostname or IP (port 88, TCP with UDP fallback)
  # enable_saml: false
  # saml_targets:
  #   - "https://idp.example.com/metadata.xml"  # SAML IdP metadata URL
  # enable_dnssec: false
  # dnssec_targets:
  #   - "example.com"           # Domain name for DNSKEY / DS record queries
```
Append after this block:
```yaml
  # -- GCP connector (optional, requires: pip install quirk[cloud]) --
  # enable_gcp: false
  # gcp_project_id: "my-gcp-project"
```

---

### `quirk/models.py` (model — new `gcs_scan_json` column)

**Analog:** `quirk/models.py` lines 63-69 (v4.2 identity scanner fields)

**Existing v4.2 field declaration pattern** (lines 63-69):
```python
    # ==========================
    # v4.2 Identity scanner fields
    # ==========================
    kerberos_scan_json = Column(Text, nullable=True)  # Full Kerberos scan JSON
    saml_scan_json = Column(Text, nullable=True)       # Full SAML scan JSON
    dnssec_scan_json = Column(Text, nullable=True)     # Full DNSSEC scan JSON
```
Add immediately after, following the same section header and inline comment style:
```python
    # ==========================
    # v4.3 GCP connector fields
    # ==========================
    gcs_scan_json = Column(Text, nullable=True)        # GCS bucket list JSON (Phase 28 hand-off)
```
Note: `Column` and `Text` are already imported at line 4.

---

### `run_scan.py` (utility, request-response — GCP scan phase wiring)

**Analog:** `run_scan.py` lines 21-22 (import), lines 440-460 (aws/azure scan phase blocks)

**Import pattern** (lines 20-22):
```python
from quirk.scanner.aws_connector import scan_aws_targets
from quirk.scanner.azure_connector import scan_azure_targets
from quirk.scanner.dnssec_scanner import scan_dnssec_targets
```
Add on the line after `azure_connector` import:
```python
from quirk.scanner.gcp_connector import scan_gcp_targets
```

**AWS scan phase block pattern** (lines 440-449):
```python
    # ==============================
    # AWS cloud connector phase
    # ==============================
    aws_endpoints = []
    with _phase_timer(run_stats, "aws_scanning"):
        if cfg.connectors.enable_aws:
            aws_endpoints = scan_aws_targets(
                region=cfg.connectors.aws_region,
                profile=cfg.connectors.aws_profile,
                logger=logger,
            )
```
**Azure scan phase block pattern** (lines 451-460):
```python
    # ==============================
    # Azure cloud connector phase
    # ==============================
    azure_endpoints = []
    with _phase_timer(run_stats, "azure_scanning"):
        if cfg.connectors.enable_azure:
            azure_endpoints = scan_azure_targets(
                subscription_id=cfg.connectors.azure_subscription_id or "",
                keyvault_urls=cfg.connectors.azure_keyvault_urls,
                logger=logger,
            )
```
Replicate this pattern for GCP immediately after the Azure block:
```python
    # ==============================
    # GCP cloud connector phase
    # ==============================
    gcp_endpoints = []
    with _phase_timer(run_stats, "gcp_scanning"):
        if cfg.connectors.enable_gcp:
            gcp_endpoints = scan_gcp_targets(
                project_id=cfg.connectors.gcp_project_id or "",
                logger=logger,
            )
```

**Endpoint aggregation** (line 506-509):
```python
    endpoints = (inventory_endpoints + tls_endpoints + ssh_endpoints
                 + jwt_endpoints + container_endpoints + source_endpoints
                 + aws_endpoints + azure_endpoints + dnssec_endpoints
                 + saml_endpoints + kerberos_endpoints)
```
Add `+ gcp_endpoints` after `+ azure_endpoints`.

---

### `quirk/cbom/builder.py` (service, transform — Pass 1 and Pass 3 extension)

**Analog:** `quirk/cbom/builder.py`

**`_normalize_cloud_key_spec` — current state** (lines 67-77):
```python
def _normalize_cloud_key_spec(key_spec: str) -> str | None:
    """Normalize AWS KMS KeySpec or Azure key_type to algorithm name."""
    spec_upper = (key_spec or "").upper().replace("-", "_")
    mapping = {
        "RSA_2048": "RSA", "RSA_3072": "RSA", "RSA_4096": "RSA",
        "ECC_NIST_P256": "ECDSA", "ECC_NIST_P384": "ECDSA", "ECC_NIST_P521": "ECDSA",
        "ECC_SECG_P256K1": "ECDSA", "SYMMETRIC_DEFAULT": "AES-256-GCM",
        "RSA": "RSA", "RSA_HSM": "RSA", "EC": "ECDSA", "EC_HSM": "ECDSA",
        "OCT": "AES-256-GCM", "OCT_HSM": "AES-256-GCM",
    }
    return mapping.get(spec_upper)
```
Update docstring to "Normalize AWS KMS KeySpec, Azure key_type, or GCP algorithm string to algorithm name." Extend `mapping` dict with GCP entries from RESEARCH.md Code Examples (the `_normalize_cloud_key_spec()` extension block). Key point: GCP algorithm strings are already upper-cased, but the `.replace("-", "_")` normalization step still applies safely.

**Pass 1 cloud branch** (lines 342-356) — change `elif ep.protocol in ("AWS", "AZURE"):` to `elif ep.protocol in ("AWS", "AZURE", "GCP"):`. No other changes to this block needed. Add a new `elif ep.protocol == "CLOUD_SQL":` branch after it:
```python
        elif ep.protocol == "CLOUD_SQL":
            # Cloud SQL TLS finding — cert_pubkey_alg holds the finding level (HIGH/MEDIUM)
            if ep.cert_pubkey_alg:
                _register_algorithm(ep.cert_pubkey_alg, algo_registry, key_size=ep.cert_pubkey_size)
```

**Pass 1 GCS-SUMMARY sentinel guard** — add a `gcp_algorithm` key lookup to the `key_spec` extraction in the AWS/AZURE/GCP branch. The sentinel endpoint sets `cert_pubkey_alg="GCS-SUMMARY"` and carries no algorithm to register; the `if key_spec:` guard already handles this gracefully (no action if `key_spec` is falsy), but add `cloud_data.get("gcp_algorithm")` to the chain for forward compatibility.

**Pass 3 skip list** (line 475) — change:
```python
        elif ep.protocol in ("JWT", "CONTAINER", "SOURCE", "AWS", "AZURE", "DNSSEC", "SAML", "KERBEROS"):
```
to:
```python
        elif ep.protocol in ("JWT", "CONTAINER", "SOURCE", "AWS", "AZURE", "GCP", "CLOUD_SQL",
                             "DNSSEC", "SAML", "KERBEROS"):
```

---

### `pyproject.toml` (config — `[cloud]` extras group)

**Analog:** `pyproject.toml` lines 33-43 (`[project.optional-dependencies]` section)

**Existing `[identity]` group pattern** (lines 40-43):
```toml
identity = [
    "impacket>=0.13.0,<0.14",
    "ldap3>=2.9.1",
]
```
Add a new `cloud` group immediately after `identity`:
```toml
cloud = [
    "google-api-python-client>=2.0.0",
    "google-auth>=2.36.0",
]
```

---

### `tests/test_cloud_connectors.py` (test, request-response — GCP test class addition)

**Analog:** `tests/test_cloud_connectors.py` (full file, lines 1-105)

**File header / imports pattern** (lines 1-11):
```python
"""Tests for AWS and Azure cloud connectors (SCAN-06, SCAN-07).

Tests mock boto3/azure SDK calls to avoid requiring cloud credentials.
Scanner modules: quirk/scanner/aws_connector.py, quirk/scanner/azure_connector.py
"""
import json
import pytest
from unittest.mock import patch, MagicMock, PropertyMock

from quirk.scanner.aws_connector import scan_aws_targets
from quirk.scanner.azure_connector import scan_azure_targets
```
Extend the docstring to include `GCP-01, GCP-02, GCP-03`, add `from quirk.scanner.gcp_connector import scan_gcp_targets` to the imports.

**Availability flag test pattern** (`test_aws_boto3_unavailable`, line 69-73):
```python
def test_aws_boto3_unavailable():
    """If boto3 is not importable, scan_aws_targets must return empty list."""
    with patch("quirk.scanner.aws_connector.BOTO3_AVAILABLE", False):
        endpoints = scan_aws_targets(region="us-east-1", profile=None)
        assert endpoints == []
```
Replicate as:
```python
def test_gcp_unavailable():
    """If google-api-python-client is not installed, scan_gcp_targets must return empty list."""
    with patch("quirk.scanner.gcp_connector.GCP_AVAILABLE", False):
        endpoints = scan_gcp_targets(project_id="my-project")
        assert endpoints == []
```

**Mock-based scan test pattern** (`test_azure_keyvault`, lines 78-98):
```python
def test_azure_keyvault():
    mock_key = MagicMock()
    mock_key.name = "my-rsa-key"
    mock_key.key_type = "RSA"
    mock_key.key_size = 2048
    mock_key.id = "https://myvault.vault.azure.net/keys/my-rsa-key/abc123"

    mock_key_client = MagicMock()
    mock_key_client.list_properties_of_keys.return_value = [mock_key]

    with patch("quirk.scanner.azure_connector.AZURE_AVAILABLE", True), \
         patch("quirk.scanner.azure_connector.KeyClient", return_value=mock_key_client), \
         patch("quirk.scanner.azure_connector.DefaultAzureCredential"):
        endpoints = scan_azure_targets(
            subscription_id="sub-123",
            keyvault_urls=["https://myvault.vault.azure.net"]
        )
        azure_eps = [ep for ep in endpoints if ep.protocol == "AZURE"]
        assert len(azure_eps) >= 1
        assert azure_eps[0].host is not None
```
For GCP tests, mock `_gcp_build` and `google.auth` at module level:
```python
with patch("quirk.scanner.gcp_connector.GCP_AVAILABLE", True), \
     patch("quirk.scanner.gcp_connector._gcp_build", return_value=mock_service), \
     patch("quirk.scanner.gcp_connector.google") as mock_google:
    mock_google.auth.default.return_value = (MagicMock(), "my-project")
    endpoints = scan_gcp_targets(project_id="my-project")
```

**Test cases to implement** (all GCP tests go in a `# ---- GCP Tests (GCP-01, GCP-02, GCP-03) ----` section):
- `test_gcp_unavailable` — `GCP_AVAILABLE=False` returns `[]`
- `test_gcp_kms_algorithm_mapping` — RSA_SIGN_PKCS1_2048_SHA256 → `cert_pubkey_alg="RSA"`, `cert_pubkey_size=2048`
- `test_gcp_cloud_sql_plaintext_allowed` — sslMode=ALLOW_UNENCRYPTED_AND_ENCRYPTED → HIGH finding
- `test_gcp_cloud_sql_encrypted_only` — sslMode=ENCRYPTED_ONLY → MEDIUM finding
- `test_gcp_cloud_sql_mtls_no_finding` — sslMode=TRUSTED_CLIENT_CERTIFICATE_REQUIRED → no finding endpoint
- `test_gcp_gcs_cmek_detection` — bucket with `defaultKmsKeyName` → `cert_pubkey_alg="CMEK"`
- `test_gcp_gcs_scan_json_written` — sentinel endpoint has non-null `gcs_scan_json`; parseable JSON array
- `test_gcp_credentials_error_graceful` — `google.auth.default()` raises `DefaultCredentialsError` → returns `[ep]` with `scan_error` set, no exception raised

---

## Shared Patterns

### Optional SDK Import (availability flag)
**Source:** `quirk/scanner/azure_connector.py` lines 17-27
**Apply to:** `gcp_connector.py`
- All three names (`_gcp_build`, `google`, `DefaultCredentialsError`) must be assigned `None` at module level in the `except ImportError` block so that `patch("quirk.scanner.gcp_connector.GCP_AVAILABLE", False)` works in tests without NameError.

### Per-Resource Error Handling
**Source:** `quirk/scanner/aws_connector.py` lines 53-67, 98-101
**Apply to:** All three private scan functions in `gcp_connector.py`
```python
try:
    # inner per-resource work
    ...
except Exception as exc:
    if logger:
        logger.v(f"<service> scan error for <resource>: {exc}")
```
- Use `logger.v()`, never `logger.warning()` or `raise`.
- Outer try/except wraps the full paginated list loop; inner try/except wraps per-resource describe/detail calls.

### `CryptoEndpoint` Construction
**Source:** `quirk/scanner/aws_connector.py` lines 89-96
**Apply to:** All endpoint construction in `gcp_connector.py`
```python
ep = CryptoEndpoint(
    host=arn,
    port=0,
    protocol="AWS",
    cert_pubkey_alg=alg_name,
    cert_pubkey_size=key_size,
    cloud_scan_json=json.dumps(metadata, default=str),
    service_detail="KMS",
)
```
- `port=0` for all cloud resource endpoints (no network port).
- `cloud_scan_json=json.dumps(data, default=str)` on every non-sentinel endpoint.
- `service_detail` encodes the GCP service + protection level: `"CloudKMS/SOFTWARE"`, `"CloudKMS/HSM"`, `"CloudKMS/EXTERNAL"`, `"GCS"`, instance name for Cloud SQL.

### DB Column Migration (inspector-first, idempotent)
**Source:** `quirk/db.py` lines 38-57
**Apply to:** `_ensure_gcp_columns()` in `quirk/db.py`
- Always check `sa_inspect(engine).get_columns("crypto_endpoints")` before issuing ALTER TABLE.
- One `with engine.connect() as conn:` block; loop over columns; single `conn.commit()` at end.

### Config Dataclass Field Addition
**Source:** `quirk/config.py` lines 44-68
**Apply to:** `ConnectorsCfg` extension in `quirk/config.py`
- Append new fields at the end of the `@dataclass` body.
- Use `Optional[str] = None` for nullable string identifiers (matches `aws_profile`, `azure_subscription_id`).
- `config_from_dict` at line 162 uses `**{k: v for k, v in ...}` — new fields with defaults are picked up automatically; no changes to `config_from_dict` needed.

### CBOM Builder Protocol Branch
**Source:** `quirk/cbom/builder.py` lines 342-356 (Pass 1), line 475 (Pass 3)
**Apply to:** Both edit sites in `quirk/cbom/builder.py`
- Pass 1: extend the `elif ep.protocol in (...)` tuple — do not duplicate the block body.
- Pass 3: extend the skip-list `elif` tuple — `"GCP"` and `"CLOUD_SQL"` both skip ProtocolProperties.

### Test Mocking Strategy
**Source:** `tests/test_cloud_connectors.py` lines 36, 62-63, 89-91
**Apply to:** GCP test class in `tests/test_cloud_connectors.py`
- Patch the module-level name (`quirk.scanner.gcp_connector._gcp_build`), not the library path.
- Patch `AVAILABLE` flag directly for the "SDK not installed" tests.
- Return MagicMock service objects whose `.projects().locations().list().execute()` chain returns controlled dict responses; set `list_next()` to return `None` to terminate pagination.

---

## No Analog Found

All files have close analogs. No entries.

---

## Metadata

**Analog search scope:** `quirk/scanner/`, `quirk/cbom/`, `quirk/`, `tests/`, `run_scan.py`, `pyproject.toml`
**Files read:** 11 (aws_connector.py, azure_connector.py, db.py, config.py, config_template.yaml, models.py, run_scan.py, builder.py, test_cloud_connectors.py, pyproject.toml, plus CONTEXT.md + RESEARCH.md)
**Pattern extraction date:** 2026-04-24
