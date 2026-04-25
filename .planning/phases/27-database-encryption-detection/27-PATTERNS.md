# Phase 27: Database Encryption Detection - Pattern Map

**Mapped:** 2026-04-25
**Files analyzed:** 11 new/modified files
**Analogs found:** 11 / 11

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `quirk/scanner/db_connector.py` | service | request-response | `quirk/scanner/gcp_connector.py` | exact |
| `quirk/scanner/aws_connector.py` | service | request-response | `quirk/scanner/aws_connector.py` (self) | self-extend |
| `quirk/db.py` | migration | CRUD | `quirk/db.py` `_ensure_gcp_columns()` (self) | self-extend |
| `quirk/config.py` | config | — | `quirk/config.py` `ConnectorsCfg` (self) | self-extend |
| `quirk/config_template.yaml` | config | — | `quirk/config_template.yaml` GCP block (self) | self-extend |
| `quirk/intelligence/evidence.py` | utility | transform | `quirk/intelligence/evidence.py` `identity_` counters (self) | self-extend |
| `quirk/intelligence/scoring.py` | utility | transform | `quirk/intelligence/scoring.py` `identity_trust` block (self) | self-extend |
| `run_scan.py` | controller | request-response | `run_scan.py` GCP/Kerberos blocks (self) | self-extend |
| `pyproject.toml` | config | — | `pyproject.toml` `[identity]` group (self) | self-extend |
| `quirk/cbom/builder.py` | utility | transform | `quirk/cbom/builder.py` KERBEROS/CLOUD_SQL skip blocks (self) | self-extend |
| `tests/test_db_connector.py` | test | — | `tests/test_cloud_connectors.py` + `tests/test_identity_infra.py` | role-match |

---

## Pattern Assignments

### `quirk/scanner/db_connector.py` (service, request-response) — NEW

**Analog:** `quirk/scanner/gcp_connector.py`

**Imports pattern** (gcp_connector.py lines 12-17):
```python
from __future__ import annotations

import json
from typing import List, Optional

from quirk.models import CryptoEndpoint
```

**Optional import with module-level None** (gcp_connector.py lines 23-32):
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
Adaptation: use TWO separate try/except blocks — one for `psycopg2`, one for `pymysql` — yielding `PSYCOPG2_AVAILABLE` and `PYMYSQL_AVAILABLE`. Both module-level names must be `None` on failure so `patch('quirk.scanner.db_connector.psycopg2')` works in tests.

**Availability guard in public function** (gcp_connector.py lines 362-366):
```python
if not GCP_AVAILABLE:
    if logger:
        logger.v("google-api-python-client not installed -- GCP scanning unavailable")
    return []
```
Adaptation: check `PSYCOPG2_AVAILABLE` at top of `scan_pg_targets()`; check `PYMYSQL_AVAILABLE` at top of `scan_mysql_targets()`.

**Public function signature with session_start** (synthesised from gcp_connector.py line 345 + CONTEXT.md D-12):
```python
def scan_pg_targets(
    targets: list,
    user: Optional[str] = None,
    password: Optional[str] = None,
    logger=None,
    session_start=None,
) -> List[CryptoEndpoint]:
    now = (session_start or datetime.now(timezone.utc)).replace(tzinfo=None)
```
The `datetime` import required: `from datetime import datetime, timezone`.

**Per-host try/except with logger.v()** (aws_connector.py lines 53-67, inner try):
```python
try:
    detail = client.describe_certificate(CertificateArn=arn).get("Certificate", {})
    ...
    results.append(ep)
except Exception as exc:
    if logger:
        logger.v(f"ACM describe_certificate failed for {arn}: {exc}")
```
Use this same inner try/except structure for each `host:port` iteration in both `scan_pg_targets` and `scan_mysql_targets`.

**Outer try/except** (aws_connector.py lines 46-70, outer try):
```python
try:
    client = session.client("acm")
    paginator = client.get_paginator("list_certificates")
    for page in paginator.paginate():
        ...
except Exception as exc:
    if logger:
        logger.v(f"ACM scan error: {exc}")
return results
```
Adaptation: outer try wraps the entire `psycopg2.connect()` block per host.

**CryptoEndpoint construction for scan_error** (from RESEARCH.md D-05 pattern):
```python
ep = CryptoEndpoint(
    host=f"postgresql://{host}:{port}",
    port=port,
    protocol="POSTGRESQL",
    scan_error="insufficient-privilege",
    service_detail="Remediation: GRANT pg_read_all_stats TO <scanner_user>",
    scanned_at=now,
)
```

---

### `quirk/scanner/aws_connector.py` — MODIFY: add `_scan_rds_encryption()`

**Analog:** `quirk/scanner/aws_connector.py` `_scan_acm()` (lines 44-71)

**Paginator pattern to copy** (aws_connector.py lines 44-71):
```python
def _scan_acm(session, logger) -> List[CryptoEndpoint]:
    results: List[CryptoEndpoint] = []
    try:
        client = session.client("acm")
        paginator = client.get_paginator("list_certificates")
        for page in paginator.paginate():
            for cert_summary in page.get("CertificateSummaryList", []):
                arn = cert_summary.get("CertificateArn", "")
                try:
                    detail = client.describe_certificate(CertificateArn=arn).get("Certificate", {})
                    ...
                    results.append(ep)
                except Exception as exc:
                    if logger:
                        logger.v(f"ACM describe_certificate failed for {arn}: {exc}")
    except Exception as exc:
        if logger:
            logger.v(f"ACM scan error: {exc}")
    return results
```
Adaptation: replace `"acm"` with `"rds"`, `"list_certificates"` with `"describe_db_instances"`, iterate `page.get("DBInstances", [])`, derive `service_detail` from `StorageEncrypted` + `KmsKeyId`.

**Extend scan_aws_targets()** (aws_connector.py lines 196-202):
```python
results.extend(_scan_kms(session, logger))
results.extend(_scan_cloudfront(session, logger))
results.extend(_scan_elbv2(session, logger))
results.extend(_scan_acm(session, logger))
# ADD:
results.extend(_scan_rds_encryption(session, logger))
```

**KMS_KEY_SPEC_MAP dict structure** (aws_connector.py lines 27-41):
```python
KMS_KEY_SPEC_MAP = {
    "RSA_2048": ("RSA", 2048),
    "RSA_3072": ("RSA", 3072),
    ...
}
```
Adaptation: RDS does not need a key-spec map. Derive `service_detail` inline:
- `StorageEncrypted == False` → `"RDS/none"`, severity HIGH
- `StorageEncrypted == True`, `KmsKeyId` absent/empty → `"RDS/sse-rds"`
- `StorageEncrypted == True`, `KmsKeyId` contains `"alias/aws/"` → `"RDS/sse-kms-aws"`
- `StorageEncrypted == True`, `KmsKeyId` present, not AWS alias → `"RDS/sse-kms-cmk"`

---

### `quirk/db.py` — MODIFY: add `_V43_COLUMNS` + `_ensure_v43_columns()`

**Analog:** `quirk/db.py` `_GCP_COLUMNS`/`_ensure_gcp_columns()` (lines 66-84)

**Exact pattern to copy** (db.py lines 66-84):
```python
_GCP_COLUMNS = [
    "gcs_scan_json",
]


def _ensure_gcp_columns(engine) -> None:
    """Add GCP scanner JSON column to crypto_endpoints if absent (idempotent).

    Uses SQLAlchemy inspector to check existing columns before ALTER TABLE.
    Called from init_db() after _ensure_identity_columns().
    """
    existing = {c["name"] for c in sa_inspect(engine).get_columns("crypto_endpoints")}
    with engine.connect() as conn:
        for col in _GCP_COLUMNS:
            if not _SAFE_COL_RE.match(col):
                raise ValueError(f"Unsafe column name in migration: {col!r}")
            if col not in existing:
                conn.execute(text(f"ALTER TABLE crypto_endpoints ADD COLUMN {col} TEXT"))
        conn.commit()
```
Replace `_GCP_COLUMNS`/`_ensure_gcp_columns` with `_V43_COLUMNS`/`_ensure_v43_columns`. Column list: `["dat_scan_json"]`. Docstring: `"Add v4.3 data-at-rest JSON column if absent (idempotent). Phases 28-30 write to dat_scan_json."`.

**init_db() call chain to extend** (db.py lines 103-106):
```python
Base.metadata.create_all(engine)
_ensure_identity_columns(engine)  # v4.2: add identity columns if missing
_ensure_gcp_columns(engine)  # v4.3: add GCP columns if missing
# ADD:
_ensure_v43_columns(engine)  # v4.3: add data-at-rest columns if missing
```

**`_SAFE_COL_RE` is already defined** (db.py line 13):
```python
_SAFE_COL_RE = re.compile(r"^[a-z][a-z0-9_]*$")
```
Do not redeclare. `dat_scan_json` passes this regex.

---

### `quirk/models.py` — MODIFY: add `dat_scan_json` column

**Analog:** `quirk/models.py` GCP fields block (lines 71-74):
```python
    # ==========================
    # v4.3 GCP connector fields
    # ==========================
    gcs_scan_json = Column(Text, nullable=True)        # GCS bucket list JSON (Phase 28 hand-off)
```
Adaptation — append after the GCP block:
```python
    # ==========================
    # v4.3 Data-at-Rest fields
    # ==========================
    dat_scan_json = Column(Text, nullable=True)  # Universal DAR scan result JSON (Phase 27+)
```

---

### `quirk/config.py` — MODIFY: add DB fields to `ConnectorsCfg`

**Analog:** `quirk/config.py` GCP fields (lines 69-71):
```python
    # GCP connector config (v4.3, Phase 26, per D-06)
    enable_gcp: bool = False
    gcp_project_id: Optional[str] = None
```
Adaptation — append after `gcp_project_id`:
```python
    # DB connector config (v4.3, Phase 27)
    enable_db: bool = False
    pg_targets: list = field(default_factory=list)
    pg_scanner_user: Optional[str] = None
    pg_scanner_password: Optional[str] = None
    mysql_targets: list = field(default_factory=list)
    mysql_scanner_user: Optional[str] = None
    mysql_scanner_password: Optional[str] = None
```

**`config_from_dict()` requires no changes** (config.py lines 164-167):
```python
connectors=ConnectorsCfg(
    **{k: v for k, v in (raw.get("connectors") or {}).items() if k != "enable_windows_adcs"}
),
```
New fields with defaults are picked up automatically via `**kwargs` unpacking.

---

### `quirk/config_template.yaml` — MODIFY: add `database` connector block

**Analog:** `quirk/config_template.yaml` GCP block (lines 71-73):
```yaml
  # -- GCP connector (optional, requires: pip install quirk[cloud]) --
  # enable_gcp: false
  # gcp_project_id: "my-gcp-project"
```
Adaptation — append after the GCP block:
```yaml
  # -- Database connector (optional, requires: pip install quirk[db]) --
  # enable_db: false
  # pg_targets:
  #   - "localhost:5432"       # host:port of PostgreSQL instance
  # pg_scanner_user: "quirk_scanner"
  # pg_scanner_password: ""
  # mysql_targets:
  #   - "localhost:3306"       # host:port of MySQL/MariaDB instance
  # mysql_scanner_user: "quirk_scanner"
  # mysql_scanner_password: ""
```

---

### `quirk/intelligence/evidence.py` — MODIFY: add `dar_` counters

**Analog:** `quirk/intelligence/evidence.py` `identity_` counter pattern (lines 73-75):
```python
identity_weak_etype_count = 0
saml_weak_signing_count = 0
dnssec_weak_algo_count = 0
```
Add after `dnssec_weak_algo_count = 0`:
```python
    # DAR protocol counters (Phase 27+)
    dar_db_plaintext_count = 0    # PG ssl=off + MySQL SSL disabled
    dar_db_weak_ssl_count = 0     # MySQL weak cipher
```

**Identity branch pattern to mirror** (evidence.py lines 115-139):
```python
        # Identity protocol counters (IDENT-01)
        if proto == "KERBEROS":
            sd = str(getattr(ep, "service_detail", "") or "")
            parts = sd.split(":")
            if len(parts) >= 4 and parts[-1] in ("CRITICAL", "HIGH"):
                identity_weak_etype_count += 1

        elif proto == "SAML":
            _saml_alg = str(getattr(ep, "cert_pubkey_alg", "") or "").upper()
            ...

        elif proto == "DNSSEC":
            ...
```
Add as additional `elif` branches after the `DNSSEC` branch:
```python
        elif proto == "POSTGRESQL":
            if getattr(ep, "scan_error", None) == "insufficient-privilege":
                pass  # privilege gap — not a confirmed vulnerability
            else:
                sd = str(getattr(ep, "service_detail", "") or "")
                if "ssl-off" in sd:
                    dar_db_plaintext_count += 1

        elif proto == "MYSQL":
            sd = str(getattr(ep, "service_detail", "") or "")
            if "ssl-off" in sd:
                dar_db_plaintext_count += 1
            elif "-weak" in sd:
                dar_db_weak_ssl_count += 1
```

**Return dict to extend** (evidence.py lines 185-190):
```python
        "identity_weak_etype_count": identity_weak_etype_count,
        "saml_weak_signing_count": saml_weak_signing_count,
        "dnssec_weak_algo_count": dnssec_weak_algo_count,
        "identity_kerberos_weak_etype_ratio": round(identity_weak_etype_count / total_endpoints, 4) if total_endpoints else 0.0,
        "identity_saml_weak_signing_ratio": round(saml_weak_signing_count / total_endpoints, 4) if total_endpoints else 0.0,
        "identity_dnssec_weak_algo_ratio": round(dnssec_weak_algo_count / total_endpoints, 4) if total_endpoints else 0.0,
```
Append after `identity_dnssec_weak_algo_ratio`:
```python
        "dar_db_plaintext_count": dar_db_plaintext_count,
        "dar_db_weak_ssl_count": dar_db_weak_ssl_count,
        "dar_db_plaintext_ratio": round(dar_db_plaintext_count / total_endpoints, 4) if total_endpoints else 0.0,
        "dar_db_weak_ssl_ratio": round(dar_db_weak_ssl_count / total_endpoints, 4) if total_endpoints else 0.0,
```

Also add `"POSTGRESQL"` and `"MYSQL"` to the `_PROTOCOL_KEYS` tuple (evidence.py line 9):
```python
_PROTOCOL_KEYS = ("TLS", "HTTP", "SSH", "UNKNOWN", "KERBEROS", "SAML", "DNSSEC")
# becomes:
_PROTOCOL_KEYS = ("TLS", "HTTP", "SSH", "UNKNOWN", "KERBEROS", "SAML", "DNSSEC", "POSTGRESQL", "MYSQL", "RDS")
```

---

### `quirk/intelligence/scoring.py` — MODIFY: add `dar_` subscore

**Analog:** `quirk/intelligence/scoring.py` `identity_trust` block (lines 142-151)

**SCORE_WEIGHTS to extend** (scoring.py lines 5-23):
```python
SCORE_WEIGHTS: Dict[str, float] = {
    ...
    "identity_kerberos_weak_etype_ratio": 10.0,
    "identity_saml_weak_signing_ratio": 8.0,
    "identity_dnssec_weak_algo_ratio": 8.0,
    "agility_high_impact_ratio": 14.0,
    ...
}
```
Add after `"identity_dnssec_weak_algo_ratio"`:
```python
    "dar_db_plaintext_ratio": 12.0,
    "dar_db_weak_ssl_ratio": 6.0,
```

**PROFILE_MULTIPLIERS to extend** (scoring.py lines 25-29):
```python
PROFILE_MULTIPLIERS: Dict[str, Dict[str, float]] = {
    "strict":   {"agility_": 1.4, "identity_": 1.4},
    "balanced": {"agility_": 1.0, "identity_": 1.0},
    "lenient":  {"agility_": 0.7, "identity_": 0.7},
}
```
Add `"dar_"` key to each profile:
```python
PROFILE_MULTIPLIERS: Dict[str, Dict[str, float]] = {
    "strict":   {"agility_": 1.4, "identity_": 1.4, "dar_": 1.4},
    "balanced": {"agility_": 1.0, "identity_": 1.0, "dar_": 1.0},
    "lenient":  {"agility_": 0.7, "identity_": 0.7, "dar_": 0.7},
}
```

**Evidence extraction to add** (scoring.py lines 124-126 pattern):
```python
kerberos_weak_count = max(0, _as_int(evidence.get("identity_weak_etype_count", 0)))
saml_weak_count = max(0, _as_int(evidence.get("saml_weak_signing_count", 0)))
dnssec_weak_count = max(0, _as_int(evidence.get("dnssec_weak_algo_count", 0)))
```
Add after `dnssec_weak_count`:
```python
    dar_db_plaintext = max(0, _as_int(evidence.get("dar_db_plaintext_count", 0)))
    dar_db_weak_ssl = max(0, _as_int(evidence.get("dar_db_weak_ssl_count", 0)))
```

**`_apply_weighted_impacts` subscore block** (scoring.py lines 142-151 — exact `identity_trust` pattern):
```python
identity_trust_impacts: List[Tuple[str, float]] = [
    ("Expired certificates", -_ratio(expired_count, denom) * w["identity_expired_ratio"]),
    ("Expiring certificates", -_ratio(expiring_count, denom) * w["identity_expiring_ratio"]),
    ("Self-signed certificates", -_ratio(self_signed_count, denom) * w["identity_self_signed_ratio"]),
    ("mTLS enforcement signals", _ratio(mtls_present_count, denom) * w["identity_mtls_ratio_bonus"]),
    ("RC4/DES Kerberos etypes detected", -_ratio(kerberos_weak_count, denom) * w["identity_kerberos_weak_etype_ratio"]),
    ("Weak SAML signing key", -_ratio(saml_weak_count, denom) * w["identity_saml_weak_signing_ratio"]),
    ("Weak DNSSEC signing algorithm", -_ratio(dnssec_weak_count, denom) * w["identity_dnssec_weak_algo_ratio"]),
]
identity_trust_score, identity_trust_drivers = _apply_weighted_impacts(identity_trust_impacts)
```
Add a parallel `dar_` block after `agility_score, agility_drivers = _apply_weighted_impacts(agility_impacts)` (line 162):
```python
    dar_impacts: List[Tuple[str, float]] = [
        ("Database plaintext connections", -_ratio(dar_db_plaintext, denom) * w["dar_db_plaintext_ratio"]),
        ("Database weak SSL configuration", -_ratio(dar_db_weak_ssl, denom) * w["dar_db_weak_ssl_ratio"]),
    ]
    dar_score, dar_drivers = _apply_weighted_impacts(dar_impacts)
```

**total_score line** (scoring.py line 164):
```python
total_score = int(hygiene_score + modern_tls_score + identity_trust_score + agility_score)
# becomes:
total_score = int(hygiene_score + modern_tls_score + identity_trust_score + agility_score + dar_score)
```

**subscores dict** (scoring.py lines 174-179):
```python
"subscores": {
    "hygiene": hygiene_score,
    "modern_tls": modern_tls_score,
    "identity_trust": identity_trust_score,
    "agility_signals": agility_score,
},
# becomes:
"subscores": {
    "hygiene": hygiene_score,
    "modern_tls": modern_tls_score,
    "identity_trust": identity_trust_score,
    "agility_signals": agility_score,
    "data_at_rest": dar_score,
},
```

**all_drivers line** (scoring.py line 167):
```python
all_drivers: List[Tuple[str, int]] = (
    hygiene_drivers + modern_tls_drivers + identity_trust_drivers + agility_drivers
)
# becomes:
all_drivers: List[Tuple[str, int]] = (
    hygiene_drivers + modern_tls_drivers + identity_trust_drivers + agility_drivers + dar_drivers
)
```

---

### `run_scan.py` — MODIFY: add `db_scanning` block

**Analog:** `run_scan.py` GCP block (lines 464-472):
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

**`session_start` placement** (run_scan.py line 474-475):
```python
    # ── Shared identity-scan session timestamp (ISSUE-3 fix) ──
    session_start = datetime.now(timezone.utc)
```
The `db_scanning` block goes AFTER this line (line 475) and BEFORE the `dnssec_scanning` block (line 477). Insert:
```python
    # ==============================
    # DB connector phase (PostgreSQL / MySQL)
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
            if cfg.connectors.mysql_targets:
                db_endpoints.extend(scan_mysql_targets(
                    targets=cfg.connectors.mysql_targets,
                    user=cfg.connectors.mysql_scanner_user,
                    password=cfg.connectors.mysql_scanner_password,
                    logger=logger,
                    session_start=session_start,
                ))
```

**Existing identity scanning blocks** (run_scan.py lines 490-516) show the `session_start=session_start` kwarg pattern — use exactly the same.

**Endpoint aggregation** (run_scan.py lines 518-521):
```python
endpoints = (inventory_endpoints + tls_endpoints + ssh_endpoints
             + jwt_endpoints + container_endpoints + source_endpoints
             + aws_endpoints + azure_endpoints + gcp_endpoints
             + dnssec_endpoints + saml_endpoints + kerberos_endpoints)
```
Append `+ db_endpoints` at the end.

---

### `pyproject.toml` — MODIFY: add `[db]` extras group

**Analog:** `pyproject.toml` `[identity]` group (lines 40-43):
```toml
identity = [
    "impacket>=0.13.0,<0.14",
    "ldap3>=2.9.1",
]
```
Add after `cloud = [...]` (line 47):
```toml
db = [
    "psycopg2-binary>=2.9.0",
    "PyMySQL>=1.1.0",
]
```

---

### `quirk/cbom/builder.py` — MODIFY: add skip-list entries

**Analog:** `quirk/cbom/builder.py` CLOUD_SQL skip (lines 388-391) and KERBEROS skip patterns.

**Pass 1 — add explicit `elif` branch** (insert after the KERBEROS branch at line 404-408):
```python
        elif ep.protocol in ("POSTGRESQL", "MYSQL", "RDS"):
            # DB config findings — no key material to catalog.
            # Finding detail is in service_detail; CBOM algorithm catalog not applicable.
            pass
```

**Pass 2 skip list** (builder.py line 431):
```python
        if ep.protocol in ("SSH", "CONTAINER", "SOURCE", "KERBEROS", "SAML", "DNSSEC",
                           "GCP", "CLOUD_SQL"):
            continue
```
Extend to:
```python
        if ep.protocol in ("SSH", "CONTAINER", "SOURCE", "KERBEROS", "SAML", "DNSSEC",
                           "GCP", "CLOUD_SQL", "POSTGRESQL", "MYSQL", "RDS"):
            continue
```

**Pass 3 skip list** (builder.py line 511):
```python
        elif ep.protocol in ("JWT", "CONTAINER", "SOURCE", "AWS", "AZURE", "GCP", "CLOUD_SQL",
                             "DNSSEC", "SAML", "KERBEROS"):
            continue
```
Extend to:
```python
        elif ep.protocol in ("JWT", "CONTAINER", "SOURCE", "AWS", "AZURE", "GCP", "CLOUD_SQL",
                             "DNSSEC", "SAML", "KERBEROS", "POSTGRESQL", "MYSQL", "RDS"):
            continue
```

---

### `tests/test_db_connector.py` — NEW

**Analog 1:** `tests/test_cloud_connectors.py` (AWS section, lines 22-79) — mock-based connector tests.
**Analog 2:** `tests/test_identity_infra.py` (lines 1-80) — RED scaffold infra tests.

**Test file header pattern** (test_cloud_connectors.py lines 1-17):
```python
"""Tests for AWS, Azure, and GCP cloud connectors (SCAN-06, SCAN-07, GCP-01, GCP-02, GCP-03).

Tests mock boto3/azure/GCP SDK calls to avoid requiring cloud credentials.
Scanner modules: quirk/scanner/aws_connector.py, quirk/scanner/azure_connector.py, quirk/scanner/gcp_connector.py
"""
import json
import pytest
from unittest.mock import patch, MagicMock, PropertyMock

from quirk.scanner.aws_connector import scan_aws_targets
```
Adaptation:
```python
"""Tests for database connector — PostgreSQL, MySQL, RDS (DB-01, DB-02, DB-03).

Tests mock psycopg2, PyMySQL, and boto3 to avoid network/DB connections.
Scanner modules: quirk/scanner/db_connector.py, quirk/scanner/aws_connector.py
"""
import pytest
from unittest.mock import patch, MagicMock, call
```

**SDK-unavailable guard test pattern** (test_cloud_connectors.py lines 75-79):
```python
def test_aws_boto3_unavailable():
    """If boto3 is not importable, scan_aws_targets must return empty list."""
    with patch("quirk.scanner.aws_connector.BOTO3_AVAILABLE", False):
        endpoints = scan_aws_targets(region="us-east-1", profile=None)
        assert endpoints == []
```
Adaptation for each scanner:
```python
def test_pg_unavailable_returns_empty():
    with patch("quirk.scanner.db_connector.PSYCOPG2_AVAILABLE", False):
        from quirk.scanner.db_connector import scan_pg_targets
        result = scan_pg_targets(targets=["localhost:5432"])
        assert result == []

def test_mysql_unavailable_returns_empty():
    with patch("quirk.scanner.db_connector.PYMYSQL_AVAILABLE", False):
        from quirk.scanner.db_connector import scan_mysql_targets
        result = scan_mysql_targets(targets=["localhost:3306"])
        assert result == []
```

**Schema migration RED test pattern** (test_identity_infra.py lines 25-59):
```python
def test_schema_fresh_db_has_identity_columns(self):
    from quirk.models import Base
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    col_names = {
        col["name"]
        for col in sa_inspect(engine).get_columns("crypto_endpoints")
    }
    self.assertIn("kerberos_scan_json", col_names, ...)
```
Adaptation for v43 schema test:
```python
def test_schema_fresh_db_has_dat_scan_json():
    from quirk.models import Base
    from sqlalchemy import create_engine, inspect as sa_inspect
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    col_names = {c["name"] for c in sa_inspect(engine).get_columns("crypto_endpoints")}
    assert "dat_scan_json" in col_names, (
        "CryptoEndpoint model missing dat_scan_json column"
    )
```

**Idempotency test pattern** (test_identity_infra.py lines 61-80):
```python
def test_schema_migration_idempotent(self):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    from quirk.db import _ensure_identity_columns
    _ensure_identity_columns(engine)
    _ensure_identity_columns(engine)  # second call must not raise
```
Adaptation:
```python
def test_v43_columns_idempotent():
    from quirk.models import Base
    from quirk.db import _ensure_v43_columns
    from sqlalchemy import create_engine
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    _ensure_v43_columns(engine)
    _ensure_v43_columns(engine)  # must not raise
```

**Mock connection for psycopg2** (test_cloud_connectors.py paginator mock pattern lines 25-43 adapted):
```python
def _make_pg_mock(ssl_value, has_privilege=True, non_ssl_count=0):
    """Build a mock psycopg2 connection + cursor for PostgreSQL probe tests."""
    mock_cursor = MagicMock()

    def execute_side_effect(query, *args):
        pass

    def fetchone_side_effect():
        if "SHOW ssl" in mock_cursor._last_query:
            return (ssl_value,)
        if "pg_has_role" in mock_cursor._last_query:
            return (has_privilege,)
        if "pg_stat_ssl" in mock_cursor._last_query:
            return (non_ssl_count,)
        return None

    mock_cursor.execute = MagicMock(side_effect=lambda q, *a: setattr(mock_cursor, "_last_query", q))
    mock_cursor.fetchone = MagicMock(side_effect=fetchone_side_effect)
    mock_conn = MagicMock()
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    return mock_conn
```

---

### `quantum-chaos-enterprise-lab/docker-compose.yml` — MODIFY: add `database` profile

**Analog:** Existing `postgres-plain` service in the `phaseA` profile (verified: port 15432, `POSTGRES_USER=chaos`).

Add after existing profile sections:
```yaml
  # =========================
  # PHASE 27 — DATABASE SSL DETECTION (profile: database)
  # =========================
  postgres-ssl-off:
    image: postgres:15
    profiles: ["database"]
    environment:
      POSTGRES_DB: quirk_db
      POSTGRES_USER: quirk_scanner
      POSTGRES_PASSWORD: quirk_scanner
    command: postgres -c ssl=off
    ports:
      - "25432:5432"

  mysql-ssl-off:
    image: mysql:8
    profiles: ["database"]
    environment:
      MYSQL_DATABASE: quirk_db
      MYSQL_USER: quirk_scanner
      MYSQL_PASSWORD: quirk_scanner
      MYSQL_ALLOW_EMPTY_PASSWORD: "yes"
      MYSQL_ROOT_PASSWORD: "root"
    command: --skip-ssl
    ports:
      - "23306:3306"
```
Port 25432 and 23306 are verified free (no conflicts with existing lab ports: 15432, 20010, 16379).

---

## Shared Patterns

### Optional SDK Import + Module-Level None
**Source:** `quirk/scanner/gcp_connector.py` lines 23-32, `quirk/scanner/aws_connector.py` lines 17-22
**Apply to:** `quirk/scanner/db_connector.py`
```python
try:
    import psycopg2
    PSYCOPG2_AVAILABLE = True
except ImportError:
    psycopg2 = None  # type: ignore[assignment]
    PSYCOPG2_AVAILABLE = False

try:
    import pymysql
    PYMYSQL_AVAILABLE = True
except ImportError:
    pymysql = None  # type: ignore[assignment]
    PYMYSQL_AVAILABLE = False
```
The module-level `None` assignment is mandatory for `patch('quirk.scanner.db_connector.psycopg2')` to work in tests.

### Per-Resource try/except with `logger.v()`
**Source:** `quirk/scanner/aws_connector.py` lines 65-67
**Apply to:** All per-host loops in `db_connector.py`, per-instance loop in `_scan_rds_encryption()`
```python
except Exception as exc:
    if logger:
        logger.v(f"<resource type> scan error for {identifier}: {exc}")
```
Never use `logger.warning()`. Never use bare `except:` without `if logger:` guard.

### `session_start` Timestamp Pattern (ISSUE-3 mandatory)
**Source:** `run_scan.py` line 475, applied in `quirk/scanner/kerberos_scanner.py`, `saml_scanner.py`, `dnssec_scanner.py`
**Apply to:** Both public functions in `quirk/scanner/db_connector.py`
```python
now = (session_start or datetime.now(timezone.utc)).replace(tzinfo=None)
```
This must appear at the top of both `scan_pg_targets()` and `scan_mysql_targets()`.

### Inspector-First Column Migration Guard
**Source:** `quirk/db.py` lines 56-63 (`_SAFE_COL_RE` + `sa_inspect` check + `ALTER TABLE`)
**Apply to:** `_ensure_v43_columns()` in `quirk/db.py`

The pattern is: check existing columns before ALTER TABLE; validate column name against `_SAFE_COL_RE`; commit in same `with engine.connect()` block. Do not use exception-for-control-flow.

### `_phase_timer` + lazy import pattern
**Source:** `run_scan.py` lines 490-502 (SAML block):
```python
    saml_endpoints = []
    with _phase_timer(run_stats, "saml_scanning"):
        if cfg.connectors.enable_saml and cfg.connectors.saml_targets:
            from quirk.scanner.saml_scanner import scan_saml_targets
            saml_endpoints = scan_saml_targets(
                targets=cfg.connectors.saml_targets,
                ...
                session_start=session_start,
            )
```
The lazy `from ... import` inside the `with` block is the established pattern for optional connectors. Use it for `db_connector` imports too.

---

## No Analog Found

All files have close analogs in the codebase. No novel patterns required.

---

## Critical Pitfalls (from RESEARCH.md)

These are anti-patterns the planner must flag in plan acceptance criteria:

| Pitfall | Wrong Pattern | Correct Pattern |
|---------|--------------|-----------------|
| P-1 | `has_privilege(user, 'pg_read_all_stats')` | `pg_has_role(current_user, 'pg_read_all_stats', 'MEMBER')` |
| P-2 | `pymysql.connect(ssl={})` | `pymysql.connect(ssl_disabled=True)` |
| P-3 | `db.get("StorageEncryptionType")` | Derive from `db.get("StorageEncrypted")` + `db.get("KmsKeyId")` |
| P-4 | `db_scanning` block before `session_start` assignment | Position AFTER line 475 (`session_start = datetime.now(timezone.utc)`) |
| P-5 | POSTGRESQL/MYSQL/RDS fall through to TLS `else` in CBOM Pass 1 | Add explicit `elif ep.protocol in ("POSTGRESQL", "MYSQL", "RDS"): pass` |
| P-6 | Adding `dar_score` without accounting for 5×25=125 max | Check `tests/test_intelligence_scoring.py` for `score <= 100` assertions before landing |

---

## Metadata

**Analog search scope:** `quirk/scanner/`, `quirk/`, `quirk/intelligence/`, `quirk/cbom/`, `tests/`, `run_scan.py`, `pyproject.toml`, `quirk/config_template.yaml`
**Files read:** 14 source files (gcp_connector.py, aws_connector.py, db.py, config.py, config_template.yaml, evidence.py, scoring.py, models.py, cbom/builder.py lines 365-524, run_scan.py lines 425-545, test_cloud_connectors.py, test_kerberos_scanner.py, test_identity_infra.py, pyproject.toml)
**Pattern extraction date:** 2026-04-25
