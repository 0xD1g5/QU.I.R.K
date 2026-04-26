# Phase 30: HashiCorp Vault Connector - Pattern Map

**Mapped:** 2026-04-26
**Files analyzed:** 10
**Analogs found:** 10 / 10

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `quirk/scanner/vault_connector.py` | scanner/service | request-response | `quirk/scanner/gcp_connector.py` | exact |
| `quirk/intelligence/evidence.py` | service/transform | transform | self (extend lines 9, 79-84, 235-242) | exact |
| `quirk/intelligence/scoring.py` | service/transform | transform | self (extend lines 5-27, 131-134, 172-177) | exact |
| `run_scan.py` | orchestrator | request-response | self (db_scanning block lines 506-524) | exact |
| `quirk/config.py` | config | — | self (ConnectorsCfg lines 73-84) | exact |
| `pyproject.toml` | config | — | self (cloud extras lines 44-48) | exact |
| `quirk/cbom/builder.py` | service/transform | transform | self (Pass 1 line 410, Pass 2 line 437, Pass 3 line 518) | exact |
| `tests/test_vault_connector.py` | test | — | `tests/test_db_connector.py` | exact |
| `quantum-chaos-enterprise-lab/storage/vault-seed.sh` | config/infra | — | self (extend existing seed lines 14-33) | exact |
| `labs/storage/expected_results.md` | docs | — | `labs/storage/expected_results.md` (extend) | exact |

---

## Pattern Assignments

### `quirk/scanner/vault_connector.py` (scanner, request-response)

**Analog:** `quirk/scanner/gcp_connector.py`

**Imports pattern** (gcp_connector.py lines 12-17):
```python
from __future__ import annotations

import json
from typing import List, Optional

from quirk.models import CryptoEndpoint
```

Vault connector additionally needs:
```python
import os
from datetime import datetime, timezone
```

**Import guard pattern** (gcp_connector.py lines 22-32 — exact structure to replicate):
```python
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

For vault_connector.py, replicate as:
```python
try:
    import hvac
    from hvac import exceptions as hvac_exceptions
    HVAC_AVAILABLE = True
except ImportError:
    hvac = None           # type: ignore[assignment]
    hvac_exceptions = None  # type: ignore[assignment]
    HVAC_AVAILABLE = False
```

Note: Module-level `None` assignments are mandatory — tests patch
`quirk.scanner.vault_connector.HVAC_AVAILABLE` using `unittest.mock.patch`.
See db_connector.py lines 21-32 for the two-library variant of the same pattern.

**Algorithm map pattern** (gcp_connector.py lines 38-96):
```python
GCP_KMS_ALGORITHM_MAP = {
    # Symmetric encryption
    "GOOGLE_SYMMETRIC_ENCRYPTION": ("AES", 256),
    "AES_128_GCM": ("AES", 128),
    ...
    # PQC algorithms (Cloud KMS, produce quantum-safe findings)
    "PQ_SIGN_ML_DSA_87": ("ml-dsa-87", 87),
    "PQ_SIGN_SLH_DSA_SHA2_128S": ("slh-dsa-128", 128),
    ...
}
```

For vault_connector.py, replicate as `VAULT_TRANSIT_KEY_MAP` with Vault-specific key type strings.
The alg_name values (`"RSA"`, `"ECDSA"`, `"AES"`, `"ml-dsa-87"`, etc.) must match entries in
`quirk/cbom/classifier.py`. The PQC entries use the same name format already in the classifier.

**scan_error CryptoEndpoint pattern** (gcp_connector.py lines 383-391):
```python
return [
    CryptoEndpoint(
        host=f"gcp://{project_id}",
        port=0,
        protocol="GCP",
        scan_error=scan_error_msg,
    )
]
```

For vault_connector.py, replicate as:
```python
return [CryptoEndpoint(
    host=vault_addr or "vault://unknown",
    port=8200,
    protocol="VAULT",
    scan_error="vault-no-token: set VAULT_TOKEN or vault_token in config",
)]
```

**Per-resource try/except pattern** (gcp_connector.py lines 155-208):
```python
for key in ck_response.get("cryptoKeys", []):
    key_name = key.get("name", "")
    try:
        ...
        ep = CryptoEndpoint(...)
        results.append(ep)
    except Exception as exc:
        if logger:
            logger.v(f"Cloud KMS key scan error for {key_name}: {exc}")
```

Each sub-scanner function (`_scan_transit_keys`, `_scan_pki_mounts`, `_scan_auth_methods`) must
wrap individual resource calls in inner try/except so a single failure does not suppress results
from other resources. The outer function try/except catches connection-level failures only.

**session_start timestamp pattern** (db_connector.py lines 73-74):
```python
now = (session_start or datetime.now(timezone.utc)).replace(tzinfo=None)
```

Use this at the top of each sub-scanner function. Pass `scanned_at=now` to every CryptoEndpoint.

**dat_scan_json population pattern** (gcp_connector.py lines 195-203):
```python
ep = CryptoEndpoint(
    host=key_name,
    port=0,
    protocol="GCP",
    cert_pubkey_alg=alg_name,
    cert_pubkey_size=key_size,
    service_detail=protection_level,
    cloud_scan_json=json.dumps(
        {
            "gcp_algorithm": algorithm,
            "key_size": key_size,
            "protectionLevel": protection_level,
            "purpose": key.get("purpose", ""),
        },
        default=str,
    ),
)
```

For vault_connector.py, use `dat_scan_json=` (not `cloud_scan_json=`) — this column was added in
Phase 27 for DAR scanners. Follow the same `json.dumps(..., default=str)` pattern.

**Sub-scanner aggregation pattern** (gcp_connector.py lines 415-425):
```python
results: List[CryptoEndpoint] = []

if kms_service is not None:
    results.extend(_scan_kms(kms_service, project_id, logger))

if sql_service is not None:
    results.extend(_scan_cloud_sql(sql_service, project_id, logger))

if storage_service is not None:
    results.extend(_scan_gcs(storage_service, project_id, logger))

return results
```

For vault_connector.py, all three sub-scanners receive the same authenticated `client` object:
```python
results: List[CryptoEndpoint] = []
results.extend(_scan_transit_keys(client, vault_transit_mount, logger, session_start))
results.extend(_scan_pki_mounts(client, logger, session_start))
results.extend(_scan_auth_methods(client, logger, session_start))
return results
```

**HVAC_AVAILABLE guard and empty-return pattern** (gcp_connector.py lines 362-366):
```python
if not GCP_AVAILABLE:
    if logger:
        logger.v("google-api-python-client not installed -- GCP scanning unavailable")
    return []
```

---

### `quirk/intelligence/evidence.py` (service/transform — extend existing file)

**Analog:** self (current file — additive changes only)

**_PROTOCOL_KEYS extension** (evidence.py line 9):
```python
# Current:
_PROTOCOL_KEYS = ("TLS", "HTTP", "SSH", "UNKNOWN", "KERBEROS", "SAML", "DNSSEC",
                  "POSTGRESQL", "MYSQL", "RDS", "S3", "AZURE_BLOB")

# Phase 30 — append "VAULT":
_PROTOCOL_KEYS = ("TLS", "HTTP", "SSH", "UNKNOWN", "KERBEROS", "SAML", "DNSSEC",
                  "POSTGRESQL", "MYSQL", "RDS", "S3", "AZURE_BLOB", "VAULT")
```

**DAR counter initialization pattern** (evidence.py lines 78-84):
```python
# DAR protocol counters (Phase 27+)
dar_db_plaintext_count = 0    # PG ssl=off + MySQL SSL disabled
dar_db_weak_ssl_count = 0     # MySQL weak cipher

# Object storage DAR counters (Phase 28, per D-09)
dar_storage_unencrypted_count = 0   # S3/unencrypted (HIGH)
dar_storage_aws_managed_count = 0   # S3/sse-kms-aws + BLOB/platform-managed (MEDIUM)
```

Add after line 84:
```python
# Vault DAR counters (Phase 30)
dar_vault_weak_count = 0   # transit keys with weak alg + PKI HIGH + HIGH auth methods
```

**elif branch pattern for protocol counter** (evidence.py lines 171-183):
```python
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

Add after `elif proto == "AZURE_BLOB":` block:
```python
elif proto == "VAULT":
    sev = str(getattr(ep, "severity", "") or "")
    if sev == "HIGH":
        dar_vault_weak_count += 1
```

**Return dict extension** (evidence.py lines 239-242):
```python
"dar_storage_unencrypted_count": dar_storage_unencrypted_count,
"dar_storage_aws_managed_count": dar_storage_aws_managed_count,
"dar_storage_unencrypted_ratio": round(dar_storage_unencrypted_count / total_endpoints, 4) if total_endpoints else 0.0,
"dar_storage_aws_managed_ratio": round(dar_storage_aws_managed_count / total_endpoints, 4) if total_endpoints else 0.0,
```

Add two more entries after line 242:
```python
"dar_vault_weak_count": dar_vault_weak_count,
"dar_vault_weak_ratio": round(dar_vault_weak_count / total_endpoints, 4) if total_endpoints else 0.0,
```

---

### `quirk/intelligence/scoring.py` (service/transform — extend existing file)

**Analog:** self (current file — additive changes only)

**SCORE_WEIGHTS addition pattern** (scoring.py lines 5-27):
```python
SCORE_WEIGHTS: Dict[str, float] = {
    ...
    "dar_db_plaintext_ratio": 12.0,
    "dar_db_weak_ssl_ratio": 6.0,
    "dar_storage_unencrypted_ratio": 12.0,   # Phase 28 D-10 — same weight as plaintext DB
    "dar_storage_aws_managed_ratio": 4.0,    # Phase 28 D-10 — compliance gap, not active weakness
    ...
}
```

Add after `"dar_storage_aws_managed_ratio"`:
```python
"dar_vault_weak_ratio": 8.0,    # Phase 30 — Vault crypto policy gap
```

**dar_ evidence extraction pattern** (scoring.py lines 131-134):
```python
dar_db_plaintext = max(0, _as_int(evidence.get("dar_db_plaintext_count", 0)))
dar_db_weak_ssl = max(0, _as_int(evidence.get("dar_db_weak_ssl_count", 0)))
dar_storage_unencrypted = max(0, _as_int(evidence.get("dar_storage_unencrypted_count", 0)))
dar_storage_aws_managed = max(0, _as_int(evidence.get("dar_storage_aws_managed_count", 0)))
```

Add after line 134:
```python
dar_vault_weak = max(0, _as_int(evidence.get("dar_vault_weak_count", 0)))
```

**dar_impacts list extension** (scoring.py lines 172-177):
```python
dar_impacts: List[Tuple[str, float]] = [
    ("Database plaintext connections", -_ratio(dar_db_plaintext, denom) * w["dar_db_plaintext_ratio"]),
    ("Database weak SSL configuration", -_ratio(dar_db_weak_ssl, denom) * w["dar_db_weak_ssl_ratio"]),
    ("Object storage unencrypted", -_ratio(dar_storage_unencrypted, denom) * w["dar_storage_unencrypted_ratio"]),
    ("Object storage platform-managed keys", -_ratio(dar_storage_aws_managed, denom) * w["dar_storage_aws_managed_ratio"]),
]
```

Append one tuple (do NOT create a new subscore block — NUM_SUBSCORES must stay 5):
```python
dar_impacts: List[Tuple[str, float]] = [
    ("Database plaintext connections", -_ratio(dar_db_plaintext, denom) * w["dar_db_plaintext_ratio"]),
    ("Database weak SSL configuration", -_ratio(dar_db_weak_ssl, denom) * w["dar_db_weak_ssl_ratio"]),
    ("Object storage unencrypted", -_ratio(dar_storage_unencrypted, denom) * w["dar_storage_unencrypted_ratio"]),
    ("Object storage platform-managed keys", -_ratio(dar_storage_aws_managed, denom) * w["dar_storage_aws_managed_ratio"]),
    ("Vault weak crypto posture", -_ratio(dar_vault_weak, denom) * w["dar_vault_weak_ratio"]),  # Phase 30
]
```

---

### `run_scan.py` (orchestrator — extend existing file)

**Analog:** self (db_scanning block lines 506-524, kerberos_scanning block lines 609-621)

**db_scanning block pattern** (run_scan.py lines 506-524):
```python
# ==============================
# DB connector phase (PostgreSQL / MySQL) — Phase 27
# ==============================
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

**HVAC_AVAILABLE guard pattern** (from s3_scanning block lines 533-548):
```python
s3_endpoints = []
with _phase_timer(run_stats, "s3_scanning"):
    if cfg.connectors.enable_s3:
        from quirk.scanner.aws_connector import _scan_s3_encryption, BOTO3_AVAILABLE
        if not BOTO3_AVAILABLE:
            logger.v("boto3 not installed — S3 scanning skipped")
        ...
```

Add vault_scanning block after the kerberos_scanning block (before the `endpoints = (...)` aggregation line 623):
```python
# ── Vault scanning ────────────────────────────────────
vault_endpoints = []
with _phase_timer(run_stats, "vault_scanning"):
    if cfg.connectors.enable_vault:
        from quirk.scanner.vault_connector import scan_vault_targets, HVAC_AVAILABLE
        if not HVAC_AVAILABLE:
            logger.v("hvac not installed — Vault scanning skipped")
        elif not (cfg.connectors.vault_addr or os.environ.get("VAULT_ADDR")):
            logger.v("vault_addr not configured — Vault scanning skipped")
        else:
            vault_endpoints = scan_vault_targets(
                vault_addr=cfg.connectors.vault_addr or "",
                token=cfg.connectors.vault_token,
                logger=logger,
                session_start=session_start,
            )
            logger.info(f"Vault scan: {len(vault_endpoints)} endpoints")
```

**Endpoint aggregation line** (run_scan.py lines 623-628):
```python
endpoints = (inventory_endpoints + tls_endpoints + ssh_endpoints
             + jwt_endpoints + container_endpoints + source_endpoints
             + aws_endpoints + azure_endpoints + gcp_endpoints
             + db_endpoints
             + s3_endpoints + blob_endpoints + gcs_storage_endpoints
             + dnssec_endpoints + saml_endpoints + kerberos_endpoints)
```

Append `+ vault_endpoints` at the end of the existing aggregation tuple.

---

### `quirk/config.py` (config — extend ConnectorsCfg)

**Analog:** self (ConnectorsCfg lines 73-84)

**DB connector config pattern** (config.py lines 73-80):
```python
# DB connector config (v4.3, Phase 27, per D-03)
enable_db: bool = False
pg_targets: list = field(default_factory=list)
pg_scanner_user: Optional[str] = None
pg_scanner_password: Optional[str] = None
mysql_targets: list = field(default_factory=list)
mysql_scanner_user: Optional[str] = None
mysql_scanner_password: Optional[str] = None
```

**Object storage config pattern** (config.py lines 81-84):
```python
# Object storage connector config (v4.3, Phase 28, per D-04)
enable_s3: bool = False
enable_blob: bool = False
aws_endpoint_url: Optional[str] = None  # MinIO/LocalStack S3 endpoint override
```

Add after line 84 (the last line of ConnectorsCfg):
```python
# Vault connector config (v4.3, Phase 30)
enable_vault: bool = False
vault_addr: Optional[str] = None        # e.g. "http://localhost:8200"
vault_token: Optional[str] = None       # if None, falls back to VAULT_TOKEN env var
vault_transit_mount: str = "transit"    # default transit mount path
```

Note: `_KNOWN_CONNECTOR_KEYS` (line 131) is built via `dataclasses.fields(ConnectorsCfg)` —
no manual update needed. New fields are picked up automatically.

---

### `pyproject.toml` (config — extend cloud extras)

**Analog:** self (lines 44-48)

**Current cloud extras block** (pyproject.toml lines 44-48):
```toml
cloud = [
    "google-api-python-client>=2.0.0",
    "google-auth>=2.36.0",
    "azure-mgmt-storage>=21.0.0",  # Phase 28: Azure Blob encryption audit (STOR-02)
]
```

Phase 30 change — append one line:
```toml
cloud = [
    "google-api-python-client>=2.0.0",
    "google-auth>=2.36.0",
    "azure-mgmt-storage>=21.0.0",  # Phase 28: Azure Blob encryption audit (STOR-02)
    "hvac>=2.4.0",                  # Phase 30: HashiCorp Vault connector (VAULT-01/02/03)
]
```

---

### `quirk/cbom/builder.py` (service/transform — extend skip lists)

**Analog:** self (Pass 1 line 410, Pass 2 lines 436-438, Pass 3 lines 517-519)

**Pass 1 DAR skip pattern** (builder.py line 410):
```python
elif ep.protocol in ("POSTGRESQL", "MYSQL", "RDS", "S3", "AZURE_BLOB"):
    # DB and object storage config findings — no key material to catalog.
    # Security signal is in service_detail; CBOM algorithm catalog not applicable.
    pass
```

VAULT transit key endpoints DO carry `cert_pubkey_alg` (the algorithm name) — they should NOT
be skipped in Pass 1. They fall through to the generic `_register_algorithm` path via the
`elif ep.cert_pubkey_alg` branch. However, Pass 2 and Pass 3 must skip VAULT.

Note: The VAULT pass-1 handling depends on whether transit key endpoints should produce algorithm
components. Per RESEARCH.md architecture, they should (to capture PQC alg_name). Therefore VAULT
is NOT added to the Pass 1 skip tuple. Only VAULT auth-method and PKI endpoints that lack
`cert_pubkey_alg` (or have sentinel values) will naturally produce no algorithm component.

**Pass 2 certificate skip list** (builder.py lines 436-438):
```python
if ep.protocol in ("SSH", "CONTAINER", "SOURCE", "KERBEROS", "SAML", "DNSSEC",
                   "GCP", "CLOUD_SQL", "POSTGRESQL", "MYSQL", "RDS",
                   "S3", "AZURE_BLOB"):
    continue
```

Add `"VAULT"` to this tuple.

**Pass 3 protocol skip list** (builder.py lines 517-519):
```python
elif ep.protocol in ("JWT", "CONTAINER", "SOURCE", "AWS", "AZURE", "GCP", "CLOUD_SQL",
                     "DNSSEC", "SAML", "KERBEROS", "POSTGRESQL", "MYSQL", "RDS",
                     "S3", "AZURE_BLOB"):
    # These are not TLS/SSH network protocols — no ProtocolProperties component.
    continue
```

Add `"VAULT"` to this tuple.

---

### `tests/test_vault_connector.py` (test — new file)

**Analog:** `tests/test_db_connector.py`

**File header and import pattern** (test_db_connector.py lines 1-9):
```python
"""Tests for database connector -- PostgreSQL, MySQL, RDS (DB-01, DB-02, DB-03).

Tests mock psycopg2, PyMySQL, and boto3 to avoid network/DB connections.
...
"""
import pytest
from unittest.mock import patch, MagicMock, call
from sqlalchemy import create_engine, inspect as sa_inspect
from quirk.models import Base
```

For test_vault_connector.py:
```python
"""Tests for Vault connector -- transit keys, PKI mounts, auth methods (VAULT-01/02/03).

Tests mock hvac to avoid network/Vault connections.
Scanner module: quirk/scanner/vault_connector.py
"""
import pytest
from unittest.mock import patch, MagicMock
```

**AVAILABLE=False guard test pattern** (test_db_connector.py lines 38-43):
```python
def test_pg_unavailable_returns_empty():
    """scan_pg_targets must return [] when psycopg2 is not installed (PSYCOPG2_AVAILABLE=False)."""
    with patch("quirk.scanner.db_connector.PSYCOPG2_AVAILABLE", False):
        from quirk.scanner.db_connector import scan_pg_targets
        result = scan_pg_targets(targets=["localhost:5432"])
        assert result == []
```

Replicate for vault:
```python
def test_hvac_unavailable_returns_empty():
    with patch("quirk.scanner.vault_connector.HVAC_AVAILABLE", False):
        from quirk.scanner.vault_connector import scan_vault_targets
        result = scan_vault_targets("http://localhost:8200", token="root")
        assert result == []
```

**Mock client construction pattern** (test_db_connector.py lines 59-67):
```python
with patch("quirk.scanner.db_connector.PSYCOPG2_AVAILABLE", True), \
     patch("quirk.scanner.db_connector.psycopg2", mock_psycopg2):
    from quirk.scanner.db_connector import scan_pg_targets
    results = scan_pg_targets(targets=["localhost:5432"], user="u", password="p")
```

For vault connector:
```python
with patch("quirk.scanner.vault_connector.HVAC_AVAILABLE", True), \
     patch("quirk.scanner.vault_connector.hvac") as mock_hvac:
    mock_client = MagicMock()
    mock_hvac.Client.return_value = mock_client
    mock_client.is_authenticated.return_value = True
    mock_client.secrets.transit.list_keys.return_value = {
        "data": {"keys": {"my-rsa-key": {}}}
    }
    mock_client.secrets.transit.read_key.return_value = {
        "data": {"type": "rsa-2048", "exportable": False, "latest_version": 1}
    }
    from quirk.scanner.vault_connector import scan_vault_targets
    result = scan_vault_targets("http://localhost:8200", token="root")
```

**session_start assertion pattern** (test_db_connector.py lines 137-159):
```python
def test_pg_session_start_used_for_scanned_at():
    from datetime import datetime, timezone
    session_start = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    ...
    results = scan_pg_targets(targets=["localhost:5432"], session_start=session_start)
    assert results[0].scanned_at == datetime(2026, 1, 1, 12, 0, 0)  # tzinfo stripped
```

**PKI test PEM generation** (from RESEARCH.md — no existing codebase analog; use cryptography library):
```python
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
import datetime as dt

def _make_test_pem_rsa2048():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([
        x509.NameAttribute(x509.NameOID.COMMON_NAME, "Test CA"),
    ])
    cert = (x509.CertificateBuilder()
        .subject_name(subject).issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(dt.datetime.now(dt.timezone.utc))
        .not_valid_after(dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=365))
        .sign(key, hashes.SHA256()))
    return cert.public_bytes(serialization.Encoding.PEM).decode()
```

---

### `quantum-chaos-enterprise-lab/storage/vault-seed.sh` (config/infra — extend)

**Analog:** self (existing file lines 1-33)

**Existing seed structure** (vault-seed.sh lines 1-33):
```sh
#!/bin/sh
set -e

export VAULT_ADDR="http://vault:8200"
export VAULT_TOKEN="${VAULT_DEV_ROOT_TOKEN_ID:-root}"

echo "=== Waiting for Vault to be ready ==="
until vault status > /dev/null 2>&1; do
  echo "Waiting for Vault..."
  sleep 2
done
sleep 3

echo "=== Enabling transit secrets engine ==="
vault secrets enable transit 2>/dev/null || echo "Transit already enabled"

echo "=== Creating transit engine keys ==="
vault write -f transit/keys/rsa-2048 type=rsa-2048
vault write -f transit/keys/rsa-1024 type=rsa-1024
vault write -f transit/keys/aes256 type=aes256-gcm96
vault write -f transit/keys/ecdsa-p256 type=ecdsa-p256

echo "=== Enabling KV secrets engine ==="
vault secrets enable -version=2 kv 2>/dev/null || echo "KV already enabled"
...
echo "=== Vault seed complete ==="
```

Extend by adding PKI and auth method sections before the final `vault secrets list` line.
Follow the same `command 2>/dev/null || echo "already done"` idempotency pattern used on line 15.

PKI section to add:
```sh
echo "=== Enabling PKI secrets engine ==="
vault secrets enable pki 2>/dev/null || echo "PKI already enabled"
vault secrets tune -max-lease-ttl=87600h pki

echo "=== Generating PKI root CA (RSA-2048, intentionally weak for RED path test) ==="
vault write pki/root/generate/internal \
  common_name="quirk-test-ca" \
  key_type=rsa \
  key_bits=2048 \
  ttl=87600h
```

Auth method section to add:
```sh
echo "=== Enabling userpass auth method ==="
vault auth enable userpass 2>/dev/null || echo "Userpass already enabled"

echo "=== Creating test user ==="
vault write auth/userpass/users/testuser \
  password=testpass \
  policies=default
```

---

### `labs/storage/expected_results.md` (docs — extend)

**Analog:** self (existing file — same format)

**Existing structure pattern** (labs/storage/expected_results.md):
- Lab setup section with `docker compose --profile <name> up -d`
- Scanner configuration YAML snippet
- Expected scan output table (host / service_detail / severity)
- Expected Evidence/Scoring Impact section with counter names
- Expected CBOM Output section
- Teardown section
- Limitations section

Add a `## Vault Scanner` section following the same table format. Key rows to document:

| host | service_detail | severity |
|------|---------------|----------|
| `http://localhost:20009/transit/keys/rsa-2048` | `transit/rsa-2048` | (none — informational) |
| `http://localhost:20009/transit/keys/rsa-1024` | `transit/rsa-1024` | (none — informational) |
| `http://localhost:20009/transit/keys/aes256` | `transit/aes256` | (none — informational) |
| `http://localhost:20009/transit/keys/ecdsa-p256` | `transit/ecdsa-p256` | (none — informational) |
| `http://localhost:20009/pki/pki` | `PKI/pki` | `HIGH` (RSA-2048 CA) |
| `http://localhost:20009/auth/token/` | `auth/token/` | `HIGH` (token auth) |
| `http://localhost:20009/auth/userpass/` | `auth/userpass/` | `MEDIUM` (userpass auth) |

Evidence counter additions to document:
- `dar_vault_weak_count`: 2 (PKI HIGH + token HIGH)
- `dar_vault_weak_ratio`: 2 / total_endpoints

---

## Shared Patterns

### Import Guard (module-level None assignment)
**Source:** `quirk/scanner/gcp_connector.py` lines 22-32 and `quirk/scanner/db_connector.py` lines 21-32
**Apply to:** `quirk/scanner/vault_connector.py`

The pattern requires assigning `None` (not just `pass`) to the module-level names so
`unittest.mock.patch("quirk.scanner.vault_connector.hvac")` targets a real module attribute.
Without the `None` assignment, patching silently creates an attribute that shadows the import.

### session_start Parameter
**Source:** `quirk/scanner/db_connector.py` lines 73-74
**Apply to:** `quirk/scanner/vault_connector.py` — every public function and every sub-scanner
```python
now = (session_start or datetime.now(timezone.utc)).replace(tzinfo=None)
```

### scan_error CryptoEndpoint
**Source:** `quirk/scanner/db_connector.py` lines 153-161
**Apply to:** `quirk/scanner/vault_connector.py` for token-missing, auth-failed, and connection-error paths
```python
results.append(CryptoEndpoint(
    host=ep_host,
    port=port,
    protocol="POSTGRESQL",
    scan_error=f"connection-error: {type(exc).__name__}",
    scanned_at=now,
))
```

### per-resource inner try/except with logger.v()
**Source:** `quirk/scanner/gcp_connector.py` lines 206-208
**Apply to:** Every per-key / per-mount / per-auth-method loop in `vault_connector.py`
```python
except Exception as exc:
    if logger:
        logger.v(f"Cloud KMS key scan error for {key_name}: {exc}")
```

### dat_scan_json with json.dumps default=str
**Source:** `quirk/scanner/gcp_connector.py` lines 195-203
**Apply to:** Every CryptoEndpoint construction in `vault_connector.py`
```python
dat_scan_json=json.dumps({...}, default=str)
```

### DAR counter elif chain
**Source:** `quirk/intelligence/evidence.py` lines 150-183
**Apply to:** `quirk/intelligence/evidence.py` — add `elif proto == "VAULT":` block
Pattern: check `severity` attribute (not `service_detail`) since VAULT uses severity=HIGH for weak findings.

### CBOM skip list extension
**Source:** `quirk/cbom/builder.py` lines 436-438 (Pass 2), lines 517-519 (Pass 3)
**Apply to:** `quirk/cbom/builder.py` — add `"VAULT"` to both skip tuples
```python
# Pass 2 — add VAULT to certificate skip list
if ep.protocol in ("SSH", "CONTAINER", "SOURCE", "KERBEROS", "SAML", "DNSSEC",
                   "GCP", "CLOUD_SQL", "POSTGRESQL", "MYSQL", "RDS",
                   "S3", "AZURE_BLOB", "VAULT"):
    continue

# Pass 3 — add VAULT to protocol skip list
elif ep.protocol in ("JWT", "CONTAINER", "SOURCE", "AWS", "AZURE", "GCP", "CLOUD_SQL",
                     "DNSSEC", "SAML", "KERBEROS", "POSTGRESQL", "MYSQL", "RDS",
                     "S3", "AZURE_BLOB", "VAULT"):
    continue
```

---

## No Analog Found

No files in this phase lack a codebase analog. All files have direct codebase matches.

---

## Metadata

**Analog search scope:** `quirk/scanner/`, `quirk/intelligence/`, `quirk/cbom/`, `quirk/config.py`,
`run_scan.py`, `tests/`, `quantum-chaos-enterprise-lab/storage/`, `labs/storage/`
**Files scanned:** 12 source files read in full; 6 files searched with Grep/Glob
**Pattern extraction date:** 2026-04-26
