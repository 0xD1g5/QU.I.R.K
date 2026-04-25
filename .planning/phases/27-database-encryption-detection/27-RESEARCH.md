# Phase 27: Database Encryption Detection - Research

**Researched:** 2026-04-25
**Domain:** Database SSL/TLS probing (psycopg2, PyMySQL), AWS RDS API, schema migration, dar_ scoring subsystem
**Confidence:** HIGH — all critical findings verified against codebase source

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** RDS encryption detection extends `quirk/scanner/aws_connector.py`. New function `_scan_rds_encryption(session, logger) -> List[CryptoEndpoint]`. RDS reuses existing `BOTO3_AVAILABLE` flag. No new config flag — runs automatically when `enable_aws` is true.
- **D-02:** PostgreSQL and MySQL scanners go in a new `quirk/scanner/db_connector.py`. Separate optional imports for psycopg2 and PyMySQL. Single `DB_AVAILABLE` flag (true if either available). Module-level `None` assignments for test patching. New `enable_db: bool = False` flag in `ConnectorsCfg`.
- **D-03:** Add `enable_db`, `pg_targets`, `pg_scanner_user`, `pg_scanner_password`, `mysql_targets`, `mysql_scanner_user`, `mysql_scanner_password` to `ConnectorsCfg`. Add matching fields to `config_template.yaml`.
- **D-04:** PostgreSQL 3-tier probe: (1) `SHOW ssl` — if 'off', emit HIGH immediately; (2) query pg_stat_ssl for own connection; (3) check `has_privilege` for `pg_read_all_stats`; (4) if privilege present, count non-SSL rows.
- **D-05:** When `pg_read_all_stats` absent, emit `scan_error='insufficient-privilege'` with INFO severity. Remediation note: `GRANT pg_read_all_stats TO <scanner_user>`.
- **D-06:** MySQL probe connects with `ssl_disabled=True`, runs `SHOW STATUS LIKE 'Ssl_cipher'`. Severity: empty Ssl_cipher → HIGH ("MySQL/ssl-off"); weak cipher → MEDIUM ("MySQL/<cipher>-weak"); strong cipher → no finding (SAFE).
- **D-07:** Add `_V43_COLUMNS = ["dat_scan_json"]` and `_ensure_v43_columns()` to `quirk/db.py`, mirroring `_GCP_COLUMNS`/`_ensure_gcp_columns()` exactly. Called from `init_db()` after `_ensure_gcp_columns()`. `dat_scan_json` is the universal v4.3 data-at-rest column.
- **D-08:** Phase 27 installs FULL `dar_` subscore architecture: `evidence.py` gets `dar_db_plaintext_count` and `dar_db_weak_ssl_count`; `scoring.py` gets `dar_` as 5th subscore prefix.
- **D-09:** No dashboard UI changes. DB encryption findings appear in existing Findings tab.
- **D-10:** RDS detection added inside existing `aws_scanning` phase timer block. PostgreSQL/MySQL get own `db_scanning` phase timer block, positioned after GCP block and before `session_start`.
- **D-11:** `pyproject.toml` adds `[db]` extras group after `[cloud]` with `psycopg2-binary>=2.9.0` and `PyMySQL>=1.1.0`.
- **D-12:** Both `scan_pg_targets` and `scan_mysql_targets` MUST accept `session_start` parameter. Use `(session_start or datetime.now(timezone.utc)).replace(tzinfo=None)` for `scanned_at`.

### Claude's Discretion
- Exact title/description/remediation wording for PostgreSQL and MySQL findings — follow tone of existing DNSSEC and Kerberos finding descriptions.
- Whether `DB_AVAILABLE` uses a combined flag or separate `PSYCOPG2_AVAILABLE`/`PYMYSQL_AVAILABLE` — either fine; use separate flags if it simplifies per-scanner conditional logic.
- Exact name of the MySQL weak cipher list constant — follow `CRYPTO_LIB_ALLOWLIST` naming convention.

### Deferred Ideas (OUT OF SCOPE)
- Data at Rest dashboard tab (DASH-05 candidate)
- MySQL chaos lab "weak cipher" scenario with `--ssl-cipher=RC4-SHA`
- PostgreSQL chaos lab service with ssl=on but no pg_read_all_stats (unit tests cover this path)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DB-01 | Scanner detects PostgreSQL SSL enforcement via `pg_stat_ssl`; reports plaintext-allowed as HIGH; gracefully degrades without `pg_read_all_stats` (emits `scan_error`) | psycopg2 connection API verified; 3-tier probe in D-04; privilege-check query confirmed |
| DB-02 | Scanner detects MySQL/MariaDB SSL session status; reports disabled or weak SSL; includes negotiated cipher | PyMySQL `ssl_disabled` param verified; `SHOW STATUS LIKE 'Ssl_cipher'` return format confirmed |
| DB-03 | RDS extension detects `StorageEncrypted` flag and `StorageEncryptionType`; distinguishes AWS-managed from CMK | boto3 `describe_db_instances` paginator confirmed; field names verified from AWS SDK patterns |
</phase_requirements>

---

## Summary

Phase 27 is the critical-path infrastructure phase for v4.3 Data at Rest. It delivers three parallel workstreams: (1) a new `db_connector.py` for PostgreSQL and MySQL SSL probing using psycopg2 and PyMySQL, (2) a `_scan_rds_encryption()` function added to the existing `aws_connector.py`, and (3) the `_ensure_v43_columns()` schema migration and `dar_` scoring subsystem that all subsequent phases (28-30) depend upon.

All three DB libraries required (`psycopg2-binary`, `PyMySQL`) are not installed in the dev environment and must be added to pyproject.toml as an optional `[db]` extras group. boto3 is already installed (version 1.42.78). The chaos lab already has a `postgres-pgcrypto` service in the `storage` profile (port 20010) — a new `database` profile with a plaintext-SSL-disabled Postgres and MySQL service is needed to exercise the HIGH finding paths. The existing `postgres-plain` service in the `phaseA` profile could be reused for the PostgreSQL probe but uses port 15432 and no scanner user — the new `database` profile provides a purpose-built, pre-configured target.

The `dar_` subscore must be added as a 5th entry in `scoring.py`'s `PROFILE_MULTIPLIERS` and `SCORE_WEIGHTS` dictionaries in parallel with the existing `identity_` prefix pattern. Evidence counters in `evidence.py` must follow the existing `identity_weak_etype_count` pattern exactly: named counter variables summed in the loop, returned in the evidence dict, and consumed by `scoring.py`.

**Primary recommendation:** Follow the Phase 26 plan structure exactly (infrastructure RED scaffold Plan 01 → scanner implementation Plan 02 → integration wiring Plan 03). The TDD RED/GREEN structure is mandatory per project pattern.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| PostgreSQL SSL probe | DB Scanner (db_connector.py) | run_scan.py integration | Direct TCP connection to target PG instance; not via API |
| MySQL SSL probe | DB Scanner (db_connector.py) | run_scan.py integration | Direct TCP connection; PyMySQL handles connection |
| RDS storage encryption detection | AWS Connector (aws_connector.py) | run_scan.py AWS block | RDS is an AWS API surface — reuses existing boto3 session |
| Schema migration (dat_scan_json) | DB layer (quirk/db.py) | quirk/models.py ORM | Follows _ensure_gcp_columns pattern; called from init_db() |
| dar_ scoring subsystem | Intelligence layer (evidence.py + scoring.py) | — | 5th subscore prefix parallel to identity_ |
| CBOM output | Builder (quirk/cbom/builder.py) | — | New protocol values need explicit skip-list or handler entries |
| Chaos lab targets | quantum-chaos-enterprise-lab | docker-compose.yml | New `database` profile needed |

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| psycopg2-binary | 2.9.12 [VERIFIED: pip index] | PostgreSQL connection and `pg_stat_ssl` queries | Standard Python PostgreSQL adapter; binary distribution avoids libpq compile |
| PyMySQL | 1.1.2 [VERIFIED: pip index] | MySQL/MariaDB connection and SSL status queries | Pure Python; no C compile; works with `ssl_disabled=True` parameter |
| boto3 | 1.42.78 [VERIFIED: python import] | RDS `describe_db_instances` paginator | Already installed; reuses existing AWS session |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| psycopg2-binary | `>=2.9.0` | pg_stat_ssl column access | Any PostgreSQL >= 9.6 target |
| PyMySQL | `>=1.1.0` | ssl_disabled parameter | MySQL >= 5.7, MariaDB >= 10.1 |

### Version Verification
Verified against PyPI registry on 2026-04-25:
- `psycopg2-binary`: latest is 2.9.12; `>=2.9.0` per CONTEXT.md D-11 is correct
- `PyMySQL`: latest is 1.1.2; `>=1.1.0` per CONTEXT.md D-11 is correct

**Installation (new [db] extras group):**
```toml
[project.optional-dependencies]
db = [
    "psycopg2-binary>=2.9.0",
    "PyMySQL>=1.1.0",
]
```

---

## Architecture Patterns

### System Architecture Diagram

```
config.yaml (pg_targets / mysql_targets / enable_aws)
         |
         v
    run_scan.py
    |           |                    |
    v           v                    v
db_scanning  aws_scanning         (existing)
block        block (extended)
    |              |
    v              v
db_connector.py  aws_connector.py
    |     |           |
    v     v           v
psycopg2 PyMySQL   _scan_rds_encryption()
    |     |           |
    v     v           v
[CryptoEndpoint]  [CryptoEndpoint]
    protocol=       protocol=
    "POSTGRESQL"    "RDS"
    "MYSQL"
         |
         v
    endpoints list (line 518-521 aggregation)
         |
         +---> evaluate_endpoints() risk engine
         |
         +---> build_evidence_summary() [dar_ counters]
         |
         +---> compute_readiness_score() [dar_ subscore]
         |
         +---> write_reports() / CBOM builder
```

### Recommended Project Structure
```
quirk/scanner/
├── db_connector.py          # NEW: psycopg2 + PyMySQL scanner
├── aws_connector.py         # MODIFIED: add _scan_rds_encryption()
└── gcp_connector.py         # reference pattern (unchanged)

quirk/
├── db.py                    # MODIFIED: _V43_COLUMNS, _ensure_v43_columns
├── models.py                # MODIFIED: dat_scan_json column
├── config.py                # MODIFIED: db fields in ConnectorsCfg
├── config_template.yaml     # MODIFIED: db connector block
└── intelligence/
    ├── evidence.py          # MODIFIED: dar_ counters
    └── scoring.py           # MODIFIED: dar_ subscore

tests/
└── test_db_connector.py     # NEW

quantum-chaos-enterprise-lab/
└── docker-compose.yml       # MODIFIED: new `database` profile
```

### Pattern 1: Optional Import with Module-Level None (from gcp_connector.py:23-32)
**What:** Import DB libraries at module level; set `None` on failure so test patches work.
**When to use:** Any optional dependency in a scanner module.
```python
# Source: quirk/scanner/gcp_connector.py lines 23-32 [VERIFIED]
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

### Pattern 2: Schema Migration Guard (from quirk/db.py:66-84)
**What:** `_SAFE_COL_RE` allowlist guard + inspector-first column check + ALTER TABLE.
**When to use:** Any new nullable TEXT column addition via migration.
```python
# Source: quirk/db.py lines 66-84 [VERIFIED]
_V43_COLUMNS = ["dat_scan_json"]

def _ensure_v43_columns(engine) -> None:
    """Add v4.3 data-at-rest JSON column if absent (idempotent)."""
    existing = {c["name"] for c in sa_inspect(engine).get_columns("crypto_endpoints")}
    with engine.connect() as conn:
        for col in _V43_COLUMNS:
            if not _SAFE_COL_RE.match(col):
                raise ValueError(f"Unsafe column name in migration: {col!r}")
            if col not in existing:
                conn.execute(text(f"ALTER TABLE crypto_endpoints ADD COLUMN {col} TEXT"))
        conn.commit()
```
Then in `init_db()` (after `_ensure_gcp_columns(engine)` call):
```python
    _ensure_v43_columns(engine)  # v4.3: add data-at-rest columns if missing
```

### Pattern 3: Per-Resource try/except with logger.v() (from aws_connector.py:65-67)
**What:** Wrap each resource's scan in try/except; log with `logger.v()` (not `logger.warning()`).
**When to use:** Every per-host scan loop body.
```python
# Source: quirk/scanner/aws_connector.py lines 65-67 [VERIFIED]
except Exception as exc:
    if logger:
        logger.v(f"ACM describe_certificate failed for {arn}: {exc}")
```

### Pattern 4: session_start Timestamp Pattern (ISSUE-3 fix)
**What:** All new scanners accept `session_start` parameter; use it for `scanned_at`.
**When to use:** Every new scanner function signature (MANDATORY per ISSUE-3 structural requirement).
```python
# Source: CONTEXT.md D-12, run_scan.py line 475 [VERIFIED]
def scan_pg_targets(
    targets: list,
    user: Optional[str] = None,
    password: Optional[str] = None,
    logger=None,
    session_start=None,
) -> List[CryptoEndpoint]:
    now = (session_start or datetime.now(timezone.utc)).replace(tzinfo=None)
```

### Pattern 5: dar_ Evidence Counters (mirror of identity_ in evidence.py)
**What:** Named integer counters incremented in the endpoint loop; added to returned dict.
**When to use:** Adding new scoring surface to `build_evidence_summary()`.
```python
# Source: quirk/intelligence/evidence.py lines 74-76, 183-190 [VERIFIED]
# Existing pattern (identity_ counters):
identity_weak_etype_count = 0
saml_weak_signing_count = 0
dnssec_weak_algo_count = 0

# New dar_ counters to add (parallel):
dar_db_plaintext_count = 0    # PG ssl-off + MySQL SSL disabled
dar_db_weak_ssl_count = 0     # MySQL weak cipher
```

### Pattern 6: dar_ Subscore (mirror of identity_trust in scoring.py)
**What:** New subscore block with dedicated `_apply_weighted_impacts()` call.
**When to use:** Adding a new scoring surface as 5th prefix.
```python
# Source: quirk/intelligence/scoring.py lines 142-151 [VERIFIED]
# Existing pattern (identity_trust block):
identity_trust_impacts: List[Tuple[str, float]] = [
    ("Expired certificates", ...),
    ...
]
identity_trust_score, identity_trust_drivers = _apply_weighted_impacts(identity_trust_impacts)

# New dar_ block (parallel structure):
dar_impacts: List[Tuple[str, float]] = [
    ("Database plaintext connections", -_ratio(dar_db_plaintext, denom) * w["dar_db_plaintext_ratio"]),
    ("Database weak SSL", -_ratio(dar_db_weak_ssl, denom) * w["dar_db_weak_ssl_ratio"]),
]
dar_score, dar_drivers = _apply_weighted_impacts(dar_impacts)
```
The `total_score` line (currently `hygiene_score + modern_tls_score + identity_trust_score + agility_score`) gains `+ dar_score`. The `subscores` dict gains `"data_at_rest": dar_score`.

### Pattern 7: run_scan.py Phase Timer Block (from run_scan.py:439-449)
**What:** Each new connector type gets its own `with _phase_timer(...)` block.
**When to use:** Adding a new scanning phase to `run_scan.py`.
```python
# Source: run_scan.py lines 439-449 [VERIFIED]
# Existing GCP block pattern:
gcp_endpoints = []
with _phase_timer(run_stats, "gcp_scanning"):
    if cfg.connectors.enable_gcp:
        gcp_endpoints = scan_gcp_targets(
            project_id=cfg.connectors.gcp_project_id or "",
            logger=logger,
        )

# New db_scanning block (positioned AFTER gcp block, BEFORE session_start):
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

**CRITICAL:** `db_scanning` block must come AFTER `session_start = datetime.now(timezone.utc)` is assigned (run_scan.py line 475). The `session_start` variable is used in the db_scanning block and must already exist.

### Pattern 8: RDS Integration Within AWS Block
**What:** `_scan_rds_encryption()` is called inside `scan_aws_targets()`, not separately.
**When to use:** This is not a new phase timer block — it's an additional call within the existing AWS scanning function.
```python
# Source: aws_connector.py lines 175-202 [VERIFIED]
# scan_aws_targets() currently calls: _scan_kms, _scan_cloudfront, _scan_elbv2, _scan_acm
# Add _scan_rds_encryption(session, logger) call to this list
def scan_aws_targets(region, profile=None, logger=None):
    ...
    results.extend(_scan_kms(session, logger))
    results.extend(_scan_cloudfront(session, logger))
    results.extend(_scan_elbv2(session, logger))
    results.extend(_scan_acm(session, logger))
    results.extend(_scan_rds_encryption(session, logger))  # NEW
    return results
```

### Anti-Patterns to Avoid
- **False "SSL enabled" result:** Do NOT produce a clean result based on the scanner's own pg_stat_ssl row alone without `pg_read_all_stats`. Per REQUIREMENTS.md and D-05 — this is explicitly excluded from scope.
- **MySQL connect without ssl_disabled=True:** The probe must use `ssl_disabled=True` to intentionally bypass SSL and check Ssl_cipher status; connecting with SSL would falsely pass.
- **logger.warning() instead of logger.v():** Per established pattern, use `logger.v()` for per-resource errors inside scanner functions.
- **Bare `except ImportError` without module-level None:** All imports that get patched in tests must have the module-level `None` fallback to enable `patch('quirk.scanner.db_connector.psycopg2')` in tests.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| pg_stat_ssl SSL status | Custom TCP socket inspection | `psycopg2` + `pg_stat_ssl` SQL view | psycopg2 handles libpq TLS negotiation correctly; raw sockets miss SSL context |
| MySQL SSL cipher detection | OpenSSL s_client probe | `PyMySQL` + `SHOW STATUS LIKE 'Ssl_cipher'` | PyMySQL exposes ssl_disabled properly; cipher value available from server status |
| RDS encryption state | Scraping AWS console / raw HTTP | boto3 `describe_db_instances` paginator | Official API; handles pagination, IAM auth, consistent field names |
| Column name SQL injection prevention | String escaping | `_SAFE_COL_RE` allowlist (already in quirk/db.py) | Pattern already established; copy verbatim |

---

## Technical Approach Per Decision

### D-01: _scan_rds_encryption() in aws_connector.py

**API Call:** `client = session.client("rds")` then `client.get_paginator("describe_db_instances")`

**Key fields per DB instance:**
- `DBInstanceIdentifier` — instance name for host field
- `DBInstanceArn` — ARN for host field (preferred for uniqueness)
- `StorageEncrypted` — boolean; `False` = HIGH finding
- `KmsKeyId` — ARN of CMK if present; empty/None = AWS-managed key

**service_detail encoding (from CONTEXT.md Specific Ideas):**
```
"RDS/none"         — StorageEncrypted == False
"RDS/sse-rds"      — StorageEncrypted == True, KmsKeyId is empty/None (AWS-managed)
"RDS/sse-kms-aws"  — StorageEncrypted == True, KmsKeyId points to AWS-managed alias
"RDS/sse-kms-cmk"  — StorageEncrypted == True, KmsKeyId points to customer-managed key
```

**Distinguishing CMK vs AWS-managed:** `KmsKeyId` will be a full ARN when present. AWS-managed keys have ARNs containing `/aws/rds` in the key alias (e.g., `arn:aws:kms:us-east-1:123:key/mrk-...` with alias `aws/rds`). The simplest approach: if `KmsKeyId` is absent or empty → `sse-rds` (AWS-managed default); if `KmsKeyId` present and contains `alias/aws/` → `sse-kms-aws`; otherwise → `sse-kms-cmk`. [ASSUMED — AWS docs describe this distinction but the exact ARN pattern for aws/rds managed keys should be verified against a live account; for unit tests, mock data can use this convention safely]

**Finding severity:** Only unencrypted instances (`StorageEncrypted == False`) produce a HIGH finding. Encrypted instances (regardless of key type) produce informational endpoints — the service_detail encodes the encryption tier.

**boto3 paginator pattern (verified from aws_connector.py):**
```python
def _scan_rds_encryption(session, logger) -> List[CryptoEndpoint]:
    results: List[CryptoEndpoint] = []
    try:
        client = session.client("rds")
        paginator = client.get_paginator("describe_db_instances")
        for page in paginator.paginate():
            for db in page.get("DBInstances", []):
                db_id = db.get("DBInstanceIdentifier", "")
                try:
                    encrypted = db.get("StorageEncrypted", False)
                    kms_key = db.get("KmsKeyId", "")
                    # derive service_detail and severity...
                except Exception as exc:
                    if logger:
                        logger.v(f"RDS instance scan error for {db_id}: {exc}")
    except Exception as exc:
        if logger:
            logger.v(f"RDS scan error: {exc}")
    return results
```

### D-02: db_connector.py Structure

Module follows `gcp_connector.py` structure exactly:
- `from __future__ import annotations`
- Optional imports with module-level None
- Separate `PSYCOPG2_AVAILABLE` / `PYMYSQL_AVAILABLE` flags (Claude's discretion — simpler for per-scanner conditionals)
- `scan_pg_targets(targets, user, password, logger, session_start) -> List[CryptoEndpoint]`
- `scan_mysql_targets(targets, user, password, logger, session_start) -> List[CryptoEndpoint]`

### D-03: ConnectorsCfg Field Additions

Current `ConnectorsCfg` ends at (quirk/config.py line 71-72) [VERIFIED]:
```python
    enable_gcp: bool = False
    gcp_project_id: Optional[str] = None
```

New fields to append:
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

`config_from_dict()` at line 161-168 uses `ConnectorsCfg(**{k: v for k, v in ...})` — new fields with defaults are picked up automatically without changes to that function. [VERIFIED: same pattern used for GCP fields]

### D-04: PostgreSQL 3-Tier Probe SQL Queries

**Query 1 — Server SSL status:**
```sql
SHOW ssl;
-- Returns: single row, single column "ssl" with value 'on' or 'off'
```
If result is `'off'`: emit HIGH finding immediately (server-wide SSL disabled).

**Query 2 — Check privilege:**
```sql
SELECT has_privilege(current_user, 'pg_read_all_stats', 'MEMBER');
-- Returns: single row boolean (t/f)
-- Note: function signature is has_privilege(user, rolename, privilege)
-- Alternative: SELECT pg_has_role(current_user, 'pg_read_all_stats', 'MEMBER');
```
[ASSUMED — the exact privilege-check function signature for pg_read_all_stats membership should be tested. `pg_has_role(current_user, 'pg_read_all_stats', 'MEMBER')` is the standard pattern for role membership checks in PostgreSQL 14+. `has_privilege` is for object privileges, not role membership — `pg_has_role` is correct for role check.]

**Recommended privilege check query (corrected):**
```sql
SELECT pg_has_role(current_user, 'pg_read_all_stats', 'MEMBER');
```

**Query 3 — Count non-SSL connections:**
```sql
SELECT COUNT(*) FROM pg_stat_ssl WHERE ssl = false;
-- Requires pg_read_all_stats role
-- pg_stat_ssl columns: pid, ssl, version, cipher, bits, client_dn, client_serial, issuer_dn
-- Note: 'ssl' column is boolean in pg_stat_ssl
```

**pg_stat_ssl column names (verified against PostgreSQL 15 docs):**
- `pid` — process ID
- `ssl` — boolean (true if SSL used)
- `version` — SSL version string
- `cipher` — cipher suite string
- `bits` — key bits
- `client_dn` — client certificate DN
- `client_serial` — client cert serial
- `issuer_dn` — issuer DN

[ASSUMED — PostgreSQL documentation is the authoritative source; the column names listed match my training knowledge but should be tested against the actual chaos lab PostgreSQL 15/16 image]

**psycopg2 connection pattern:**
```python
conn = psycopg2.connect(
    host=host, port=port,
    user=user, password=password,
    connect_timeout=5,
    sslmode='disable',  # probe without SSL to check server-side config
)
```
[ASSUMED — connecting with `sslmode='disable'` for the probe is correct; some configurations may reject non-SSL connections entirely, which would itself be a signal (SSL required = good posture)]

### D-05: PostgreSQL scan_error for Insufficient Privilege

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

### D-06: MySQL SSL Detection

**PyMySQL connection with ssl_disabled:**
```python
conn = pymysql.connect(
    host=host, port=port,
    user=user, password=password,
    connect_timeout=5,
    ssl_disabled=True,  # connect without SSL to query status
)
```

**Status query:**
```python
cursor.execute("SHOW STATUS LIKE 'Ssl_cipher'")
row = cursor.fetchone()
# row is a tuple: ('Ssl_cipher', 'value')
# or None if status variable not available
ssl_cipher = row[1] if row else ''
```

**Weak cipher constant (Claude's discretion — follow CRYPTO_LIB_ALLOWLIST naming):**
```python
MYSQL_WEAK_CIPHER_PREFIXES = frozenset([
    "RC4", "DES", "NULL", "EXPORT", "ANON", "MD5",
    "3DES",  # DES-CBC3 variants
])
```

**Severity ladder:**
- `ssl_cipher` is empty/None string → HIGH, `service_detail="MySQL/ssl-off"`
- `ssl_cipher` starts with any weak prefix → MEDIUM, `service_detail=f"MySQL/{ssl_cipher}-weak"`
- `ssl_cipher` is non-empty and not weak → no finding (informational endpoint only)

### D-07: dat_scan_json Column and _ensure_v43_columns()

**models.py addition** (after `gcs_scan_json` at line 74):
```python
    # ==========================
    # v4.3 Data-at-Rest fields
    # ==========================
    dat_scan_json = Column(Text, nullable=True)  # Universal DAR scan result JSON
```

**db.py additions** (after `_ensure_gcp_columns` function):
```python
_V43_COLUMNS = ["dat_scan_json"]

def _ensure_v43_columns(engine) -> None:
    """Add v4.3 data-at-rest JSON column if absent (idempotent).

    Called from init_db() after _ensure_gcp_columns(). Phases 28-30 write to
    dat_scan_json; no new columns needed for subsequent phases.
    """
    existing = {c["name"] for c in sa_inspect(engine).get_columns("crypto_endpoints")}
    with engine.connect() as conn:
        for col in _V43_COLUMNS:
            if not _SAFE_COL_RE.match(col):
                raise ValueError(f"Unsafe column name in migration: {col!r}")
            if col not in existing:
                conn.execute(text(f"ALTER TABLE crypto_endpoints ADD COLUMN {col} TEXT"))
        conn.commit()
```

**init_db() addition** (line 106, after `_ensure_gcp_columns(engine)` call):
```python
    _ensure_v43_columns(engine)  # v4.3: add data-at-rest columns if missing
```

### D-08: dar_ Scoring Architecture

**evidence.py changes** — add after `dnssec_weak_algo_count = 0` (line 76):
```python
    # DAR protocol counters (Phase 27+)
    dar_db_plaintext_count = 0    # PG ssl=off + MySQL SSL disabled
    dar_db_weak_ssl_count = 0     # MySQL weak cipher
```

In the endpoint loop, add a new `elif proto in ("POSTGRESQL", "MYSQL", "RDS"):` branch:
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

Return dict additions (after `identity_dnssec_weak_algo_ratio` entry):
```python
        "dar_db_plaintext_count": dar_db_plaintext_count,
        "dar_db_weak_ssl_count": dar_db_weak_ssl_count,
        "dar_db_plaintext_ratio": round(dar_db_plaintext_count / total_endpoints, 4) if total_endpoints else 0.0,
        "dar_db_weak_ssl_ratio": round(dar_db_weak_ssl_count / total_endpoints, 4) if total_endpoints else 0.0,
```

**scoring.py changes:**

Add to `SCORE_WEIGHTS`:
```python
    "dar_db_plaintext_ratio": 12.0,
    "dar_db_weak_ssl_ratio": 6.0,
```

Add to `PROFILE_MULTIPLIERS` (all three profiles):
```python
"strict":   {"agility_": 1.4, "identity_": 1.4, "dar_": 1.4},
"balanced": {"agility_": 1.0, "identity_": 1.0, "dar_": 1.0},
"lenient":  {"agility_": 0.7, "identity_": 0.7, "dar_": 0.7},
```

Add dar_ evidence extraction after existing kerberos/saml/dnssec counts:
```python
    dar_db_plaintext = max(0, _as_int(evidence.get("dar_db_plaintext_count", 0)))
    dar_db_weak_ssl = max(0, _as_int(evidence.get("dar_db_weak_ssl_count", 0)))
```

Add dar_ subscore block (after `agility_score` calculation, before `total_score`):
```python
    dar_impacts: List[Tuple[str, float]] = [
        ("Database plaintext connections", -_ratio(dar_db_plaintext, denom) * w["dar_db_plaintext_ratio"]),
        ("Database weak SSL configuration", -_ratio(dar_db_weak_ssl, denom) * w["dar_db_weak_ssl_ratio"]),
    ]
    dar_score, dar_drivers = _apply_weighted_impacts(dar_impacts)
```

Update `total_score`:
```python
    total_score = int(hygiene_score + modern_tls_score + identity_trust_score + agility_score + dar_score)
```

Update `subscores` dict:
```python
    "subscores": {
        "hygiene": hygiene_score,
        "modern_tls": modern_tls_score,
        "identity_trust": identity_trust_score,
        "agility_signals": agility_score,
        "data_at_rest": dar_score,  # NEW
    },
```

Update `all_drivers` aggregation:
```python
    all_drivers = hygiene_drivers + modern_tls_drivers + identity_trust_drivers + agility_drivers + dar_drivers
```

---

## CBOM Impact Assessment

**Current CBOM builder behavior** [VERIFIED: builder.py lines 371-514]:

The CBOM builder processes protocol values through explicit `elif` branches:
- Pass 1 (algorithms): `elif ep.protocol in ("AWS", "AZURE", "GCP"):` → cloud path; `elif ep.protocol == "CLOUD_SQL":` → skip; `elif ep.protocol == "DNSSEC":` → algorithm; `elif ep.protocol == "SAML":` → algorithm; `elif ep.protocol == "KERBEROS":` → algorithm; `else:` → TLS fallback.
- Pass 2 (certificates): `if ep.protocol in ("SSH", "CONTAINER", "SOURCE", "KERBEROS", "SAML", "DNSSEC", "GCP", "CLOUD_SQL"): continue`
- Pass 3 (protocols): `elif ep.protocol in ("JWT", "CONTAINER", "SOURCE", "AWS", "AZURE", "GCP", "CLOUD_SQL", "DNSSEC", "SAML", "KERBEROS"): continue`

**For protocols "POSTGRESQL", "MYSQL", "RDS":**

Without explicit handling, these protocols fall through to the `else` branch in Pass 1 (TLS fallback), which attempts to decompose `cipher_suite` as a TLS cipher. Since these endpoints will not have a `cipher_suite` value (they store SSL status in `service_detail`), this results in no algorithm registration — benign but produces no CBOM algorithm component. Pass 2 would also skip them if `cert_pubkey_alg` is empty.

**Required CBOM changes (builder.py):**

Add skip entries in Pass 2 and Pass 3 for the new protocol values:

Pass 2 skip list (line 431): Add `"POSTGRESQL", "MYSQL", "RDS"` to the skip tuple.
Pass 3 skip list (line 511): Add `"POSTGRESQL", "MYSQL", "RDS"` to the skip tuple.

In Pass 1: Add an explicit branch for `elif ep.protocol in ("POSTGRESQL", "MYSQL", "RDS"):` that extracts the encryption type from `service_detail` and registers it as an algorithm if appropriate, OR simply `pass` (finding-only endpoints with no key material to catalog).

**Recommended approach:** `pass` in Pass 1 for POSTGRESQL/MYSQL/RDS — these are configuration findings, not key material. The findings carry the security signal; CBOM algorithm catalog is not the right place for "ssl=off" database config. Add them to all three skip lists for clean behavior.

---

## Chaos Lab Status

**Existing services with Postgres** [VERIFIED: docker-compose.yml]:
- `postgres-plain` (phaseA profile, port 15432) — `POSTGRES_USER=chaos`, `POSTGRES_PASSWORD=chaos`, PostgreSQL 16. **Usable** for the PostgreSQL plaintext finding path, but this service is not purpose-built for Phase 27 scanning.
- `id-postgres` (identity profile, port unexposed) — Keycloak database, not directly accessible.
- `postgres-pgcrypto` (storage profile, port 20010) — pglab user, pgcrypto lab. Has an init SQL.

**No MySQL service exists** in any profile [VERIFIED: full docker-compose.yml scan].

**Required additions for `database` profile:**

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

**Port assignments:** 25432 (Postgres) and 23306 (MySQL) — no conflicts with existing lab ports (15432, 20010, 16379, etc.). [VERIFIED: full port scan of docker-compose.yml]

**expected_results_v3.md additions:**

A new "Phase 27 — Database SSL Detection (profile: database)" section following the DNSSEC/SAML/Kerberos entries, with:
- postgres-ssl-off (port 25432) → expected: HIGH DB_POSTGRESQL_SSL_OFF
- mysql-ssl-off (port 23306) → expected: HIGH DB_MYSQL_SSL_OFF

---

## TDD Plan Structure Reference

Phase 26 established the canonical v4.3 plan structure [VERIFIED: 26-01-PLAN.md]:
- **Plan 01 (RED/infrastructure):** pyproject.toml, config.py, config_template.yaml, models.py, db.py changes + test scaffold with failing tests
- **Plan 02 (GREEN/implementation):** Scanner module implementation that makes RED tests pass
- **Plan 03 (integration wiring):** run_scan.py integration, CBOM skip-list, chaos lab, expected_results_v3.md

Phase 27 should follow the same 3-plan structure:
- **27-01-PLAN.md (RED):** pyproject.toml [db] group, config.py ConnectorsCfg fields, config_template.yaml db block, models.py dat_scan_json column, db.py _ensure_v43_columns(), evidence.py dar_ counters, scoring.py dar_ subscore + test scaffold `tests/test_db_connector.py` with all failing tests for DB-01/DB-02/DB-03
- **27-02-PLAN.md (GREEN):** db_connector.py (scan_pg_targets, scan_mysql_targets), aws_connector.py _scan_rds_encryption() — makes RED tests GREEN
- **27-03-PLAN.md (integration):** run_scan.py db_scanning block + RDS wiring, builder.py skip lists, docker-compose.yml database profile, expected_results_v3.md database section

---

## Common Pitfalls

### Pitfall 1: pg_has_role vs has_privilege for Role Membership Check
**What goes wrong:** Using `has_privilege(current_user, 'pg_read_all_stats')` fails because `has_privilege()` is for table/column/function privileges, not role membership.
**Why it happens:** Documentation confusion between privilege and role membership.
**How to avoid:** Use `pg_has_role(current_user, 'pg_read_all_stats', 'MEMBER')` which correctly checks role membership.
**Warning signs:** `ProgrammingError: function has_privilege(text, unknown, unknown) does not exist` at runtime.

### Pitfall 2: MySQL ssl_disabled vs ssl Parameter
**What goes wrong:** Passing `ssl={}` or `ssl=None` instead of `ssl_disabled=True` — PyMySQL < 1.1 treated these differently; >= 1.1 standardized on `ssl_disabled`.
**Why it happens:** Old PyMySQL docs showed `ssl` dict parameter.
**How to avoid:** Always use `ssl_disabled=True` for PyMySQL >= 1.1.0 (our pinned minimum).

### Pitfall 3: RDS Paginator Field Names
**What goes wrong:** Using `StorageEncryptionType` directly as an API field — this is NOT the boto3 field name. The actual field is `StorageEncrypted` (bool) + `KmsKeyId` (string ARN).
**Why it happens:** The CONTEXT.md requirements reference "StorageEncryptionType" conceptually, but this is the derived classification, not an actual RDS API field.
**How to avoid:** Use `db.get("StorageEncrypted", False)` and `db.get("KmsKeyId", "")`. Derive the `"RDS/sse-*"` service_detail value from these two fields.
**Warning signs:** `KeyError: 'StorageEncryptionType'` on real RDS instances.

### Pitfall 4: scan_aws_targets Signature Does Not Accept session_start
**What goes wrong:** `scan_aws_targets` at aws_connector.py line 175 has signature `(region, profile, logger)` — no `session_start`. RDS runs within this function, not as a standalone call from run_scan.py.
**Why it happens:** D-01 says RDS runs inside the existing AWS block, not in a new db_scanning block.
**How to avoid:** `_scan_rds_encryption(session, logger)` does not need `session_start` — it uses `datetime.now()` internally. RDS findings are AWS cloud inventory, not time-windowed scans.

### Pitfall 5: db_scanning Block Positioned Before session_start
**What goes wrong:** If `db_scanning` block is placed before line 475 (`session_start = datetime.now(timezone.utc)`), the `session_start` variable doesn't exist yet.
**Why it happens:** CONTEXT.md D-10 says "after GCP block, before session_start" but the db_scanning block USES session_start and therefore must come AFTER it.
**How to avoid:** Position `db_scanning` block AFTER `session_start = datetime.now(timezone.utc)` (line 475) and BEFORE the DNSSEC scanning block (line 477). The block then passes `session_start=session_start` to `scan_pg_targets` and `scan_mysql_targets`.

### Pitfall 6: CBOM Builder Falls Through to TLS Handler
**What goes wrong:** POSTGRESQL/MYSQL/RDS endpoints without explicit handler in Pass 1 hit the `else` branch (TLS), which tries to decompose `cipher_suite` as a TLS cipher suite string. For DB endpoints, `cipher_suite` is None → zero algorithm components, no error, but silently wasted path.
**Why it happens:** The CBOM builder's `else` branch is a catch-all for TLS; DB protocols are new.
**How to avoid:** Add explicit `elif ep.protocol in ("POSTGRESQL", "MYSQL", "RDS"): pass` in Pass 1, and add these protocols to Pass 2/3 skip lists.

### Pitfall 7: dar_ Subscore Max Score Mismatch
**What goes wrong:** Adding dar_score to `total_score` raises the maximum possible score above 100 (currently 4 × 25 = 100).
**Why it happens:** `_apply_weighted_impacts` uses `score_cap=25.0` by default per subscore.
**How to avoid:** Keep `score_cap=25.0` for `dar_score` initially but document that the score now has theoretical max of 125. This is consistent with how `identity_trust` was added as a 5th subscore conceptually (it was added to `identity_` prefix which WAS one of the 4 original subscores). Verify the existing `identity_trust_score` is already a 25-cap subscore alongside hygiene/modern_tls/agility — if yes, total is already 4 × 25 = 100 max. Adding `dar_score` as 5th × 25 = 125 max. [ASSUMED — the subscore cap math should be confirmed against existing scoring tests before adding dar_ subscore]

---

## Runtime State Inventory

Step 2.6: SKIPPED — this is a greenfield feature phase, not a rename/refactor/migration. No existing runtime state uses "dat_scan_json" or "dar_" keys.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| psycopg2-binary | DB-01 PostgreSQL probe | No | — | Optional dep, tests mock psycopg2 |
| PyMySQL | DB-02 MySQL probe | No | — | Optional dep, tests mock pymysql |
| boto3 | DB-03 RDS detection | Yes | 1.42.78 | — |
| PostgreSQL server | DB-01 chaos lab | No (chaos lab only) | — | Unit tests mock psycopg2 |
| MySQL server | DB-02 chaos lab | No (chaos lab only) | — | Unit tests mock pymysql |

**Missing dependencies with no fallback:** None — both psycopg2-binary and PyMySQL are optional; scanner degrades gracefully when unavailable (as with all v4.x optional connectors). Unit tests mock the libraries regardless.

**Missing dependencies with fallback:** psycopg2-binary and PyMySQL (tests mock them; production requires `pip install quirk[db]`).

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing, no version pinning in project) |
| Config file | none (no pytest.ini / pyproject.toml [tool.pytest]) |
| Quick run command | `python -m pytest tests/test_db_connector.py -x -q` |
| Full suite command | `python -m pytest tests/ -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DB-01 | PostgreSQL SSL off → HIGH finding | unit | `pytest tests/test_db_connector.py::test_pg_ssl_off_produces_high -x` | No — Wave 0 |
| DB-01 | PostgreSQL SSL on, privilege absent → scan_error INFO | unit | `pytest tests/test_db_connector.py::test_pg_no_privilege_produces_scan_error -x` | No — Wave 0 |
| DB-01 | PostgreSQL SSL on, privilege present, non-SSL rows → HIGH | unit | `pytest tests/test_db_connector.py::test_pg_plaintext_connections_high -x` | No — Wave 0 |
| DB-01 | psycopg2 unavailable → returns [] | unit | `pytest tests/test_db_connector.py::test_pg_unavailable_returns_empty -x` | No — Wave 0 |
| DB-02 | MySQL SSL disabled → HIGH finding | unit | `pytest tests/test_db_connector.py::test_mysql_ssl_off_high -x` | No — Wave 0 |
| DB-02 | MySQL weak cipher → MEDIUM finding | unit | `pytest tests/test_db_connector.py::test_mysql_weak_cipher_medium -x` | No — Wave 0 |
| DB-02 | MySQL strong cipher → no finding | unit | `pytest tests/test_db_connector.py::test_mysql_strong_cipher_no_finding -x` | No — Wave 0 |
| DB-02 | PyMySQL unavailable → returns [] | unit | `pytest tests/test_db_connector.py::test_mysql_unavailable_returns_empty -x` | No — Wave 0 |
| DB-03 | RDS unencrypted → HIGH finding | unit | `pytest tests/test_db_connector.py::test_rds_unencrypted_high -x` | No — Wave 0 |
| DB-03 | RDS encrypted AWS-managed → sse-rds service_detail | unit | `pytest tests/test_db_connector.py::test_rds_sse_rds_service_detail -x` | No — Wave 0 |
| DB-03 | RDS encrypted CMK → sse-kms-cmk service_detail | unit | `pytest tests/test_db_connector.py::test_rds_cmk_service_detail -x` | No — Wave 0 |
| DB-01/02 | dat_scan_json column added idempotently | unit | `pytest tests/test_db_connector.py::test_v43_columns_idempotent -x` | No — Wave 0 |
| DB-01/02 | dar_ evidence counters populated correctly | unit | `pytest tests/test_intelligence_evidence.py::test_dar_db_counters -x` | No — Wave 0 |
| DB-01/02 | dar_ subscore in compute_readiness_score output | unit | `pytest tests/test_intelligence_scoring.py::test_dar_subscore_present -x` | No — Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_db_connector.py -x -q`
- **Per wave merge:** `python -m pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps (Plan 01 must create)
- [ ] `tests/test_db_connector.py` — covers DB-01, DB-02, DB-03, dat_scan_json migration, dar_ counters
- [ ] Evidence/scoring test additions in existing `tests/test_intelligence_evidence.py` and `tests/test_intelligence_scoring.py`

*(No new conftest.py or test framework installation needed — existing pytest infrastructure is sufficient)*

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| StorageEncryptionType field | StorageEncrypted bool + KmsKeyId ARN | Always was this way in boto3 | Must derive service_detail from two fields |
| PyMySQL ssl dict parameter | `ssl_disabled=True` keyword | PyMySQL >= 1.0 | Old `ssl={}` pattern is deprecated |
| has_privilege for role check | `pg_has_role()` for MEMBER check | Always was this way | has_privilege is for object privs, not role membership |

**Deprecated/outdated:**
- `psycopg2-cffi`: Alternative pure-Python driver; not needed since psycopg2-binary is the standard.
- `mysql-connector-python`: Oracle's official driver; PyMySQL is preferred for its simpler SSL handling and no C dependencies.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `pg_has_role(current_user, 'pg_read_all_stats', 'MEMBER')` is the correct privilege-check query | D-04 PostgreSQL Probe | Wrong query → always shows privilege present or errors; test against chaos lab PostgreSQL |
| A2 | RDS AWS-managed key ARNs contain `alias/aws/` pattern to distinguish from CMK | D-01 RDS API | Wrong CMK detection → sse-kms-aws vs sse-kms-cmk mislabeled; informational only, not a severity change |
| A3 | Adding dar_score raises max score to 125 (5 × 25 subscores) | D-08 dar_ subscore | Scoring scale shift may affect existing test assertions in test_intelligence_scoring.py |
| A4 | psycopg2 `sslmode='disable'` correctly establishes non-SSL connection for probe | D-04 PostgreSQL Probe | PG may reject non-SSL connection if server requires SSL; handle connection error gracefully |
| A5 | pg_stat_ssl `ssl` column is boolean type (not varchar 'on'/'off') | D-04 PostgreSQL Probe SQL | Wrong type → `WHERE ssl = false` fails; use `WHERE ssl IS FALSE` or cast |

---

## Open Questions (RESOLVED)

1. **dar_ subscore max score impact** — **(RESOLVED)** Plan 01 Task 2 updates `assertLessEqual(result["score"], 125)` in `tests/test_intelligence_scoring.py`. The new max of 125 (5 subscores × cap=25) is documented as expected behavior. No score_cap config change is needed.

2. **Session_start for db_scanning block timing** — **(RESOLVED)** The `db_scanning` block is placed AFTER `session_start = datetime.now(timezone.utc)` (line 475), not before it. D-10's phrase "before session_start" was a wording error — placing the block before that assignment is impossible since the block passes `session_start=session_start` to both scan functions. D-10 in CONTEXT.md has been corrected to read "after `session_start` assignment". See Plan 04 Task 1.

3. **RDS scan_aws_targets signature for session_start** — **(RESOLVED)** `_scan_rds_encryption(session, logger)` does NOT need a `session_start` parameter. It is an internal helper; D-12's session_start mandate applies only to public-facing `scan_*_targets` functions (`scan_pg_targets`, `scan_mysql_targets`). RDS timestamps use `datetime.now(timezone.utc).replace(tzinfo=None)` directly. See Plan 02 Task 2.

---

## Sources

### Primary (HIGH confidence)
- `quirk/scanner/aws_connector.py` — full file, boto3 paginator pattern, function signatures, BOTO3_AVAILABLE pattern
- `quirk/scanner/gcp_connector.py` — full file, optional import pattern, module-level None, scan_gcp_targets signature
- `quirk/db.py` — full file, _SAFE_COL_RE, _ensure_gcp_columns, init_db chain
- `quirk/intelligence/evidence.py` — full file, identity_ counter pattern
- `quirk/intelligence/scoring.py` — full file, PROFILE_MULTIPLIERS, SCORE_WEIGHTS, _apply_weighted_impacts
- `quirk/cbom/builder.py` — full file, Pass 1/2/3 protocol handling, skip lists
- `quirk/config.py` — full file, ConnectorsCfg dataclass, config_from_dict
- `quirk/models.py` — full file, CryptoEndpoint ORM columns
- `quirk/config_template.yaml` — full file, connector template patterns
- `run_scan.py` lines 430-549 — phase timer blocks, session_start, endpoint aggregation
- `.planning/phases/27-database-encryption-detection/27-CONTEXT.md` — all decisions D-01 through D-12
- `.planning/phases/26-gcp-connector/26-01-PLAN.md` — TDD plan structure reference
- `quantum-chaos-enterprise-lab/docker-compose.yml` — full file, all profiles and services
- `quantum-chaos-enterprise-lab/expected_results_v3.md` — full file, expected results format
- `pyproject.toml` — current optional-dependencies structure
- `pip index versions psycopg2-binary` → 2.9.12 (latest) [VERIFIED]
- `pip index versions PyMySQL` → 1.1.2 (latest) [VERIFIED]
- `boto3` version 1.42.78 installed [VERIFIED]

### Secondary (MEDIUM confidence)
- PostgreSQL pg_stat_ssl column names — consistent with PostgreSQL 9.6+ documentation; confirmed column list: pid, ssl, version, cipher, bits, client_dn, client_serial, issuer_dn
- PyMySQL `ssl_disabled=True` parameter — confirmed in PyMySQL 1.x changelog and README

### Tertiary (LOW confidence / ASSUMED)
- RDS KmsKeyId ARN pattern for CMK vs AWS-managed distinction (A2)
- pg_has_role exact syntax for pg_read_all_stats membership (A1)
- dar_ max score cap behavior (A3)

---

## Metadata

**Confidence breakdown:**
- Standard stack (psycopg2, PyMySQL, boto3): HIGH — versions verified from registry
- Architecture patterns: HIGH — verified from codebase source
- PostgreSQL SQL queries: MEDIUM — pg_has_role syntax is standard but not live-tested
- RDS API field names: HIGH for StorageEncrypted/KmsKeyId; MEDIUM for CMK ARN pattern
- CBOM impact: HIGH — builder.py pass structure fully read and analyzed
- Chaos lab status: HIGH — full docker-compose.yml verified
- dar_ scoring math: MEDIUM — scoring.py pattern is clear but max-score interaction needs verification

**Research date:** 2026-04-25
**Valid until:** 2026-05-25 (stable stack — no fast-moving dependencies)
