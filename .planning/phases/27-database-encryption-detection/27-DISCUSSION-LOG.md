# Phase 27: Database Encryption Detection - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-25
**Phase:** 27-database-encryption-detection
**Areas discussed:** Scanner module structure, PostgreSQL connection model, Chaos lab profile design, dar_ scoring scope

---

## Scanner Module Structure

### RDS placement

| Option | Description | Selected |
|--------|-------------|----------|
| Extend aws_connector.py | Add _scan_rds_encryption() in aws_connector.py — reuses boto3 Session, BOTO3_AVAILABLE flag | ✓ |
| New db_connector.py handles all three | Single file for PG + MySQL + RDS; mixes cloud-credential and DB-credential auth | |

**User's choice:** Extend aws_connector.py
**Notes:** RDS is an AWS surface — consistent credential model (IAM), reuses existing boto3 session, zero new optional deps.

### PostgreSQL + MySQL file

| Option | Description | Selected |
|--------|-------------|----------|
| Single db_connector.py for PG + MySQL | One file, two optional imports (psycopg2 + PyMySQL), DB_AVAILABLE flag | ✓ |
| Separate pg_connector.py and mysql_connector.py | Two files — maximum isolation but overkill given GCP precedent of grouping surfaces | |

**User's choice:** Single db_connector.py
**Notes:** Consistent with gcp_connector.py pattern of grouping a surface's scanners together.

---

## PostgreSQL Connection Model

### Credentials in config

| Option | Description | Selected |
|--------|-------------|----------|
| Host + port + user + password | Explicit pg_scanner_user / pg_scanner_password in ConnectorsCfg | ✓ |
| Host + port only (anonymous probe) | Passwordless via pg_hba trust — fails most real deployments | |

**User's choice:** Host + port + user + password
**Notes:** Clients provide a read-only scanner account. Realistic for consulting deployments.

### Privilege gap severity

| Option | Description | Selected |
|--------|-------------|----------|
| INFO severity | Privilege gap = scanner config issue, not host vulnerability; emit scan_error='insufficient-privilege' | ✓ |
| MEDIUM severity | Treat privilege absence as moderate finding | |

**User's choice:** INFO severity
**Notes:** Scanner configuration issue — don't cry wolf at the client.

### Probe approach

| Option | Description | Selected |
|--------|-------------|----------|
| SHOW ssl + pg_stat_ssl check | 3-tier: SHOW ssl → pg_stat_ssl → pg_read_all_stats check | ✓ |
| pg_stat_ssl only | Misses ssl=off at server level (most severe misconfiguration) | |

**User's choice:** SHOW ssl + pg_stat_ssl check (3-tier)
**Notes:** SHOW ssl catches server-wide disabled SSL before any connection-row logic runs.

---

## Chaos Lab Profile Design

### Profile structure

| Option | Description | Selected |
|--------|-------------|----------|
| Single 'database' profile, two services | postgres:15 (ssl=off) + mysql:8 (ssl disabled) — one docker compose --profile database up | ✓ |
| Separate 'postgres' and 'mysql' profiles | Two profiles — inconsistent with existing pattern of grouping surfaces | |
| No chaos lab in Phase 27 | Defer to cleanup phase; use pytest-docker integration tests only | |

**User's choice:** Single 'database' profile with two services
**Notes:** Matches pattern of other single-surface profiles (e.g., 'ldaps').

### MySQL severity ladder

| Option | Description | Selected |
|--------|-------------|----------|
| Disabled=HIGH, Weak cipher=MEDIUM, Good=no finding | Ssl_cipher empty → HIGH; weak cipher → MEDIUM; strong → safe | ✓ |
| Disabled=HIGH, anything SSL=no finding | Binary — misses weak-cipher configurations | |

**User's choice:** Disabled=HIGH, Weak cipher=MEDIUM, Good=no finding
**Notes:** Parallel to TLS scanner severity logic.

---

## dar_ Scoring Scope

### Architecture completeness

| Option | Description | Selected |
|--------|-------------|----------|
| Full architecture, DB counters only | Build complete dar_ subscore pattern; Phases 28-30 add their own counters | ✓ |
| Stub only — just _ensure_v43_columns() | Skip dar_ scoring entirely; defer to Phase 31 | |
| Full architecture with all v4.3 counters pre-declared | Pre-declare ALL counter names now — creates cross-phase coupling | |

**User's choice:** Full architecture, DB counters only
**Notes:** Consistent with how identity_ was built in Phase 21 — architecture first, surface-specific counters per phase.

### Dashboard changes

| Option | Description | Selected |
|--------|-------------|----------|
| No dashboard changes | DB findings flow to existing Findings tab (protocol='POSTGRESQL'/'MYSQL'/'RDS') | ✓ |
| Add a Data at Rest tab now | New DAR tab — adds scope beyond critical path mission | |

**User's choice:** No dashboard changes
**Notes:** User noted: ensure a Data at Rest tab is added in a future UI phase (DASH-05 candidate).

---

## Claude's Discretion

- Exact finding title/description/remediation wording for PG and MySQL — follow DNSSEC/Kerberos tone
- Whether to use separate PSYCOPG2_AVAILABLE + PYMYSQL_AVAILABLE flags or a combined DB_AVAILABLE
- MySQL weak cipher list constant naming — follow CRYPTO_LIB_ALLOWLIST convention

## Deferred Ideas

- Data at Rest dashboard tab (DASH-05 candidate) — future UI phase
- MySQL chaos lab scenario with forced weak cipher (ssl-cipher=RC4-SHA) — version-dependent; add later
- PostgreSQL chaos lab service with SSL on + no pg_read_all_stats — test graceful degradation in Docker
