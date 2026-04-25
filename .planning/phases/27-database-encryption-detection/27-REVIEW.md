---
phase: 27-database-encryption-detection
reviewed: 2026-04-25T00:00:00Z
depth: standard
files_reviewed: 17
files_reviewed_list:
  - pyproject.toml
  - quantum-chaos-enterprise-lab/docker-compose.yml
  - quantum-chaos-enterprise-lab/expected_results_v3.md
  - quirk/cbom/builder.py
  - quirk/config.py
  - quirk/config_template.yaml
  - quirk/db.py
  - quirk/intelligence/evidence.py
  - quirk/intelligence/scoring.py
  - quirk/models.py
  - quirk/scanner/aws_connector.py
  - quirk/scanner/db_connector.py
  - run_scan.py
  - tests/test_cloud_connectors.py
  - tests/test_db_connector.py
  - tests/test_intelligence_evidence.py
  - tests/test_intelligence_scoring.py
findings:
  critical: 0
  warning: 4
  info: 5
  total: 9
status: issues_found
---

# Phase 27: Code Review Report

**Reviewed:** 2026-04-25
**Depth:** standard
**Files Reviewed:** 17
**Status:** issues_found

## Summary

Phase 27 adds PostgreSQL and MySQL SSL posture scanning (`db_connector.py`), an RDS encryption-at-rest sub-scanner inside `aws_connector.py`, DAR protocol counters in `evidence.py`, a `data_at_rest` subscore in `scoring.py`, and the v4.3 schema migration in `db.py`. The integration wiring in `run_scan.py` is correct: `session_start` is assigned before the `db_scanning` block, `db_endpoints` is properly aggregated into the main `endpoints` list, and the CBOM builder (`builder.py`) correctly skips algorithm registration and protocol component generation for `POSTGRESQL`, `MYSQL`, and `RDS` protocols.

No critical security vulnerabilities were found. Credentials are read from config, never hardcoded in source. The SQL injection guard in `_ensure_v43_columns` via `_SAFE_COL_RE` is correct; the guarded column names are compile-time constants so there is no runtime injection risk. The `pg_has_role` function call (not `has_privilege`) is correctly implemented per the RESEARCH.md guidance. The `ssl_disabled=True` parameter is correctly used per the PyMySQL 1.1.0 API. The `StorageEncrypted`/`KmsKeyId` field names in `_scan_rds_encryption` are correct per the boto3 API (not the nonexistent `StorageEncryptionType`).

The most significant issues are: (1) connection errors in both DB scanners are silently dropped — no scan_error endpoint is emitted, causing targeted hosts to vanish from the evidence summary; (2) unencrypted RDS instances (`RDS/none`) are not counted in the `dar_db_plaintext_count` DAR counter despite being the highest-severity finding from the RDS scanner; (3) the `severity` column is migrated as `TEXT` rather than the appropriate type; and (4) the RDS scanner uses `port=5432` for all engine types.

---

## Warnings

### WR-01: Connection errors silently drop the target — no scan_error endpoint emitted

**File:** `quirk/scanner/db_connector.py:152-154` and `237-239`

**Issue:** Both `scan_pg_targets` and `scan_mysql_targets` catch `Exception` at the per-target level and only log to the optional logger. When a target is unreachable (wrong credentials, host down, network timeout, firewall drop), the scanner emits zero endpoints for that target. The target then has no representation in the `endpoints` list, so `evidence.py` sees no record that a scan was attempted. This is inconsistent with every other scanner in the codebase, which emits a `scan_error` endpoint when a host cannot be reached. A silent zero means an unreachable DB server looks identical to "no DB targets configured."

```python
# Current — db_connector.py line 152
except Exception as exc:
    if logger:
        logger.v(f"PostgreSQL scan error for {ep_host}: {exc}")
# Nothing appended — target disappears silently
```

**Fix:** Emit a scan_error endpoint in both except blocks:
```python
except Exception as exc:
    if logger:
        logger.v(f"PostgreSQL scan error for {ep_host}: {exc}")
    results.append(CryptoEndpoint(
        host=ep_host,
        port=port,
        protocol="POSTGRESQL",
        scan_error=f"connection-error: {type(exc).__name__}",
        scanned_at=now,
    ))
```
Apply the identical pattern to the MySQL except block at line 237.

---

### WR-02: Unencrypted RDS instances not counted in `dar_db_plaintext_count`

**File:** `quirk/intelligence/evidence.py:145-158`

**Issue:** The DAR counter loop handles `proto == "POSTGRESQL"` and `proto == "MYSQL"` but has no branch for `proto == "RDS"`. RDS instances with `service_detail="RDS/none"` (i.e., `StorageEncrypted=False`) produce a `HIGH` finding and are tracked in `protocol_counts["RDS"]`, but they are never added to `dar_db_plaintext_count`. This means unencrypted RDS instances do not reduce the `data_at_rest` subscore, even though they represent the highest-severity data-at-rest finding in Phase 27. The `dar_db_plaintext_ratio` fed to scoring will be understated whenever AWS RDS is in scope.

```python
# evidence.py lines 145-158 — RDS is not handled
elif proto == "POSTGRESQL":
    ...
elif proto == "MYSQL":
    ...
# proto == "RDS" falls through — no counter increment
```

**Fix:** Add an `elif proto == "RDS":` branch after the MySQL branch:
```python
elif proto == "RDS":
    sd = str(getattr(ep, "service_detail", "") or "")
    if "RDS/none" in sd:
        dar_db_plaintext_count += 1
    # RDS/sse-rds and RDS/sse-kms-* are positive posture — no penalty
```

---

### WR-03: `_ensure_v43_columns` migrates `severity` as `TEXT`, not `VARCHAR(16)` — docstring also misleading

**File:** `quirk/db.py:87-103`

**Issue:** `_V43_COLUMNS = ["dat_scan_json", "severity"]` causes both columns to be added with:
```sql
ALTER TABLE crypto_endpoints ADD COLUMN dat_scan_json TEXT
ALTER TABLE crypto_endpoints ADD COLUMN severity TEXT
```
The ORM model at `models.py:80` declares `severity = Column(String(16), nullable=True)`. SQLite ignores column type affinity for string columns so this is not a runtime bug, but it creates a schema drift that matters if the database is inspected by tooling or if the project later migrates to PostgreSQL or MySQL. Additionally, the function docstring says "Add v4.3 data-at-rest JSON column" (singular, implying only `dat_scan_json`), but the function actually adds two columns including `severity`. A developer reading the docstring will be surprised to find `severity` in `_V43_COLUMNS`.

**Fix:** Update the docstring to list both columns explicitly. For DDL correctness, use per-column type mapping:
```python
_V43_COLUMN_DDLS = {
    "dat_scan_json": "TEXT",
    "severity": "VARCHAR(16)",
}

def _ensure_v43_columns(engine) -> None:
    """Add v4.3 data-at-rest columns (dat_scan_json TEXT, severity VARCHAR(16)) if absent."""
    existing = {c["name"] for c in sa_inspect(engine).get_columns("crypto_endpoints")}
    with engine.connect() as conn:
        for col, col_type in _V43_COLUMN_DDLS.items():
            if not _SAFE_COL_RE.match(col):
                raise ValueError(f"Unsafe column name in migration: {col!r}")
            if col not in existing:
                conn.execute(text(f"ALTER TABLE crypto_endpoints ADD COLUMN {col} {col_type}"))
        conn.commit()
```

---

### WR-04: `_scan_rds_encryption` hardcodes `port=5432` for all RDS engine types

**File:** `quirk/scanner/aws_connector.py:111`

**Issue:** Every RDS `CryptoEndpoint` is created with `port=5432`, acknowledged in a comment as a placeholder. This affects MySQL RDS (port 3306), SQL Server (1433), Oracle (1521), and Aurora variants. If any downstream code — including the CBOM builder, the scan summary counter, or a future deduplication pass — uses `(host, port)` as a compound key, MySQL RDS instances will appear as PostgreSQL port services. Even at the reporting level, a user reading `host=arn:aws:rds:..., port=5432, service_detail=RDS/none` for a MySQL instance is receiving misleading data.

**Fix:** Read the actual port from the RDS descriptor, which is available in the `describe_db_instances` response under `Endpoint.Port`:
```python
db_port = int((db.get("Endpoint") or {}).get("Port") or 5432)
ep = CryptoEndpoint(
    host=db_arn,
    port=db_port,
    protocol="RDS",
    ...
)
```

---

## Info

### IN-01: `ssl_disabled=True` means `Ssl_cipher` is always empty — "strong cipher" positive case is unreachable

**File:** `quirk/scanner/db_connector.py:173-239`

**Issue:** `SHOW STATUS LIKE 'Ssl_cipher'` reports the SSL state of the **current session**. Because the scanner connects with `ssl_disabled=True`, the current session is always plaintext. Therefore `Ssl_cipher` will always be empty for the scanner's own connection, regardless of whether the MySQL server supports or requires SSL for other clients. The `else` branch at line 227 (strong cipher positive result) and the `elif _is_weak_mysql_cipher` branch at line 218 are both unreachable when `ssl_disabled=True`. The effective behavior is: connection succeeds → `Ssl_cipher` is empty → always `HIGH` finding.

The intent (detecting whether the server accepts plaintext connections at all) is valid for the `ssl-off` detection goal. The limitation is that a MySQL server configured with `require_secure_transport=ON` will refuse the `ssl_disabled=True` connection and fall into the except block (currently silenced by WR-01), which is the correct behavior — but the "weak cipher" and "strong cipher" branches for the session-based check cannot fire in this connection mode.

This is a design constraint that should be documented; it does not cause incorrect HIGH findings, only makes the MEDIUM/OK branches dead code under the current connection strategy. Add a comment:
```python
# NOTE: With ssl_disabled=True the scanner's own Ssl_cipher is always empty.
# The meaningful signal here is whether the server accepted a plaintext connection
# at all. Servers with require_secure_transport=ON will reject this connection
# (falling into the except block). The weak/strong cipher branches apply only
# if ssl_disabled is changed to False in a future revision.
```

---

### IN-02: `pyproject.toml` version not bumped to `4.3.0` — inconsistent with Phase 27 being a v4.3 milestone

**File:** `pyproject.toml:8` and `quirk/cbom/builder.py:109`

**Issue:** `version = "4.2.0"` in `pyproject.toml` and `PLATFORM_VERSION = "4.2.0"` in `builder.py`. Phase 27 is the first phase of the v4.3 "Data at Rest" milestone (per the memory context referencing v4.3 initialization). The `intelligence_version` default in `config.py:92` also reads `"4.2.0"`. All three should be bumped to `"4.3.0"` as part of this milestone's completion.

**Fix:**
```toml
# pyproject.toml
version = "4.3.0"
```
```python
# quirk/cbom/builder.py
PLATFORM_VERSION = "4.3.0"
```
```python
# quirk/config.py
intelligence_version: str = "4.3.0"
```

---

### IN-03: `config.py` `ConnectorsCfg` construction will raise `TypeError` on unrecognized YAML keys

**File:** `quirk/config.py:173-175`

**Issue:** The config loader uses `**{k: v for k, v in ... if k != "enable_windows_adcs"}` to construct `ConnectorsCfg`. Any unrecognized key in the user's `connectors:` YAML block (typo, old key name, future key not yet in the dataclass) will cause `TypeError: __init__() got an unexpected keyword argument`. Phase 27 adds 7 new fields to `ConnectorsCfg`; users upgrading from an older config who happen to have a legacy key will get a hard crash rather than a warning.

**Fix:** Filter to known fields only:
```python
import dataclasses
_KNOWN_CONNECTOR_KEYS = {f.name for f in dataclasses.fields(ConnectorsCfg)}
connectors=ConnectorsCfg(
    **{k: v for k, v in (raw.get("connectors") or {}).items()
       if k in _KNOWN_CONNECTOR_KEYS}
),
```

---

### IN-04: `test_intelligence_scoring.py` score upper-bound assertion may become incorrect as more subscores are added

**File:** `tests/test_intelligence_scoring.py:34`

**Issue:** `self.assertLessEqual(result["score"], 125)` — the comment says "max 5 subscores x 25 cap each after Phase 27 dar_ added." This is correct for Phase 27. However, if future phases (28-30 are planned in the v4.3 milestone) add additional subscores, this assertion will need updating. The magic number `125` should be derived from the actual subscore structure or documented as a computed value:
```python
MAX_SUBSCORE = 25  # per _apply_weighted_impacts cap
NUM_SUBSCORES = 5  # hygiene, modern_tls, identity_trust, agility_signals, data_at_rest
self.assertLessEqual(result["score"], MAX_SUBSCORE * NUM_SUBSCORES)
```

---

### IN-05: `expected_results_v3.md` Phase 27 section has a copy-paste artifact from the Kerberos section

**File:** `quantum-chaos-enterprise-lab/expected_results_v3.md:291`

**Issue:** The Phase 27 section ends at line 291 with:
```
**Expected:** Kerberos scanner returns >= 1 HIGH finding for RC4-HMAC (etype 23)...
```
This sentence belongs to the Kerberos section (Phase 25) and was accidentally appended to the end of the Phase 27 MySQL description. It is misleading documentation — a developer setting up the database lab profile will read this and expect Kerberos scanner output.

**Fix:** Remove lines 291-292 (the Kerberos expected-output sentence) from the Phase 27 MySQL section, or add a proper "Expected" line for the MySQL scanner:
```markdown
**Expected:** DB scanner returns 1 HIGH finding (`DB_MYSQL_SSL_OFF`) for `localhost:23306`.
```

---

_Reviewed: 2026-04-25_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
