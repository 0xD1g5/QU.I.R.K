# Phase 27: Database Encryption Detection - Context

**Gathered:** 2026-04-25
**Status:** Ready for planning

<domain>
## Phase Boundary

QU.I.R.K. can detect encryption-at-rest posture for PostgreSQL (`pg_stat_ssl`),
MySQL/MariaDB (SSL session status), and RDS (`StorageEncrypted`/`StorageEncryptionType`) —
while establishing the `dat_scan_json` column and `dar_` scoring infrastructure that all
subsequent v4.3 data-at-rest phases (28 Object Storage, 29 K8s Secrets, 30 Vault) depend on.

This phase is CRITICAL PATH: `_ensure_v43_columns()` and the `dar_` subscore prefix must
exist before any downstream phase can begin.

No dashboard UI changes in Phase 27 — DB findings flow through the existing Findings tab.

</domain>

<decisions>
## Implementation Decisions

### Scanner Module Structure

- **D-01:** RDS encryption detection extends `quirk/scanner/aws_connector.py`. Add a new
  `_scan_rds_encryption(session, logger) -> List[CryptoEndpoint]` function alongside the
  existing `_scan_kms`, `_scan_acm`, `_scan_cloudfront`, `_scan_elb` functions. RDS is an
  AWS surface — it reuses the existing boto3 session and `BOTO3_AVAILABLE` flag. No new
  optional import, no new file, no new `enable_*` config flag for RDS specifically. RDS
  runs automatically when `cfg.connectors.enable_aws` is true.

- **D-02:** PostgreSQL and MySQL scanners go in a new `quirk/scanner/db_connector.py`.
  Two separate optional imports (`psycopg2` and `PyMySQL`), one `DB_AVAILABLE` flag (true
  if either is available). Module-level `None` assignments for test patching. Credential
  model: username + password (cloud IAM not applicable here).
  New `enable_db: bool = False` flag in `ConnectorsCfg`.

### PostgreSQL Connection Model

- **D-03:** Add these fields to `ConnectorsCfg` in `config.py`:
  ```python
  enable_db: bool = False
  pg_targets: list = field(default_factory=list)        # host:port strings
  pg_scanner_user: Optional[str] = None
  pg_scanner_password: Optional[str] = None
  mysql_targets: list = field(default_factory=list)     # host:port strings
  mysql_scanner_user: Optional[str] = None
  mysql_scanner_password: Optional[str] = None
  ```
  Add matching fields to `config_template.yaml` under `connectors:`.

- **D-04:** PostgreSQL probe uses a 3-tier approach:
  1. `SHOW ssl` — if `'off'`, emit HIGH finding immediately (SSL disabled at server level).
     Service_detail: `"PostgreSQL/ssl-off"`.
  2. If SSL is on, query `pg_stat_ssl` to confirm scanner's own connection uses SSL.
  3. Check `has_privilege(current_user(), 'pg_read_all_stats')` — if absent, emit INFO
     `scan_error` with value `'insufficient-privilege'` (see D-05).
  4. With `pg_read_all_stats`: count non-SSL rows in `pg_stat_ssl`; if any exist, emit HIGH
     (plaintext connections allowed).

- **D-05:** When `pg_read_all_stats` role is absent, emit `scan_error='insufficient-privilege'`
  with INFO severity. This is a scanner configuration issue, not a host vulnerability.
  Include remediation note: `GRANT pg_read_all_stats TO <scanner_user>`. Do NOT produce a
  false "SSL enabled" result based on the scanner's own connection row alone.

### MySQL/MariaDB SSL Detection

- **D-06:** MySQL probe connects with `ssl_disabled=True` to query SSL status without
  interference, then runs `SHOW STATUS LIKE 'Ssl_cipher'`. Severity ladder:
  - `Ssl_cipher` empty → HIGH finding (no SSL on this connection / SSL globally disabled)
  - `Ssl_cipher` present but in weak cipher list (RC4, DES, NULL ciphers) → MEDIUM finding
    with cipher in `service_detail`
  - `Ssl_cipher` present and strong (AES-GCM, CHACHA20, etc.) → no finding (SAFE)
  Protocol field: `"MYSQL"`, service_detail: `"MySQL/ssl-off"` or `"MySQL/<cipher>-weak"`.

### Schema Migration

- **D-07:** Add `_V43_COLUMNS` and `_ensure_v43_columns()` to `quirk/db.py`, mirroring the
  `_GCP_COLUMNS` / `_ensure_gcp_columns()` pattern exactly:
  ```python
  _V43_COLUMNS = ["dat_scan_json"]
  def _ensure_v43_columns(engine) -> None: ...
  ```
  Called from `init_db()` after `_ensure_gcp_columns()`. The `dat_scan_json` TEXT column
  is the universal storage column for all v4.3 data-at-rest scanner output — parallel to
  `cloud_scan_json` for cloud connectors. Phases 28-30 write to this same column; no new
  columns needed for subsequent phases.

### dar_ Scoring Infrastructure

- **D-08:** Phase 27 installs the FULL `dar_` subscore architecture in `evidence.py` and
  `scoring.py`, but populates only DB-specific counters now:
  - `evidence.py`: add `dar_db_plaintext_count` (PG ssl=off + MySQL SSL disabled HOW
    many endpoints) and `dar_db_weak_ssl_count` (MySQL weak cipher endpoints) alongside
    existing identity_ counters
  - `scoring.py`: add `dar_` as 5th subscore prefix with its own weight, parallel to the
    `identity_` subscore introduced in Phase 21
  - Phases 28, 29, 30 follow this established pattern by adding their own `dar_storage_*`,
    `dar_k8s_*`, `dar_vault_*` counters without touching the architecture

- **D-09:** No dashboard UI changes in Phase 27. DB encryption findings appear in the
  existing Findings tab as `CryptoEndpoint` rows with `protocol="POSTGRESQL"` or
  `protocol="MYSQL"` / `protocol="RDS"`. A dedicated Data at Rest dashboard tab is deferred
  to a future UI phase (noted in Deferred Ideas).

### run_scan.py Integration

- **D-10:** RDS encryption detection is added inside the existing `aws_scanning` phase timer
  block in `run_scan.py` — no new phase timer needed. When `enable_aws` is true, `_scan_rds_encryption`
  runs as an additional call within `scan_aws_targets` (or as a direct call in the AWS block).
  PostgreSQL/MySQL get their own `db_scanning` phase timer block, positioned after the GCP
  block and before `session_start`.

### ISSUE-2/ISSUE-3 Structural Requirements

- **D-11:** `pyproject.toml` diff is a required deliverable for this phase:
  ```toml
  [project.optional-dependencies]
  db = [
      "psycopg2-binary>=2.9.0",
      "PyMySQL>=1.1.0",
  ]
  ```
  The `[db]` extras group goes after `[cloud]` in the optional-dependencies section.

- **D-12:** Both `scan_pg_targets` and `scan_mysql_targets` in `db_connector.py` MUST accept
  a `session_start` parameter (mandatory pattern from ISSUE-3 fix). PostgreSQL/MySQL
  endpoints use `(session_start or datetime.now(timezone.utc)).replace(tzinfo=None)` for
  `scanned_at` timestamps.

### Claude's Discretion

- Exact title/description/remediation wording for PostgreSQL and MySQL findings — follow
  the tone of existing DNSSEC and Kerberos finding descriptions in the codebase.
- Whether `DB_AVAILABLE` checks both psycopg2 and PyMySQL separately or uses a single
  combined flag — either is fine; use separate `PSYCOPG2_AVAILABLE` / `PYMYSQL_AVAILABLE`
  if it simplifies per-scanner conditional logic.
- Exact name of the MySQL weak cipher list constant — follow the `CRYPTO_LIB_ALLOWLIST`
  naming convention from container_scanner.py.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing Connector Patterns (primary references)
- `quirk/scanner/aws_connector.py` — boto3 Session pattern, optional import with BOTO3_AVAILABLE,
  `KMS_KEY_SPEC_MAP` structure; RDS `_scan_rds_encryption()` goes in this file (D-01)
- `quirk/scanner/gcp_connector.py` — optional import + GCP_AVAILABLE flag + module-level None;
  reference implementation for `db_connector.py` structure (D-02)

### Schema Migration Pattern
- `quirk/db.py` — `_GCP_COLUMNS` / `_ensure_gcp_columns()` — mirror exactly for
  `_V43_COLUMNS` / `_ensure_v43_columns()` (D-07); also check the `_SAFE_COL_RE` guard

### Config Extension
- `quirk/config.py` — `ConnectorsCfg` dataclass — add all db fields from D-03
- `quirk/config_template.yaml` — add matching fields under `connectors:` section

### Scoring Infrastructure Reference
- `quirk/intelligence/evidence.py` — existing `identity_` counter pattern to mirror for `dar_`
- `quirk/intelligence/scoring.py` — existing 4-prefix subscore loop to extend with `dar_` (D-08)

### run_scan.py Integration
- `run_scan.py` lines 438-521 — existing connector phase blocks and `session_start` placement;
  add `db_scanning` block before `session_start` assignment (D-10)

### Dependency Structure
- `pyproject.toml` — `[project.optional-dependencies]` section; `[db]` group goes after `[cloud]` (D-11)

### Phase Requirements
- `.planning/REQUIREMENTS.md` §Database Encryption — DB-01, DB-02, DB-03 acceptance criteria
- `.planning/ROADMAP.md` §Phase 27 — success criteria and critical-path note

### Chaos Lab Reference
- `quantum-chaos-enterprise-lab/docker-compose.yml` — existing profile structure; add `database`
  profile with postgres:15 and mysql:8 services
- `quantum-chaos-enterprise-lab/expected_results_v3.md` — add database chaos lab expected results

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_ensure_gcp_columns()` in `quirk/db.py:71` — copy structure verbatim for `_ensure_v43_columns()`
- `KMS_KEY_SPEC_MAP` in `aws_connector.py` — dict structure pattern; RDS maps
  `StorageEncryptionType` similarly (none / sse-rds / sse-kms)
- `_phase_timer` context manager in `run_scan.py` — wrap new `db_scanning` block identically
- `scan_gcp_targets` function signature in `gcp_connector.py` — model `scan_pg_targets` and
  `scan_mysql_targets` signatures after this (positional args, logger kwarg, session_start kwarg)

### Established Patterns
- Optional SDK import: `try: import X; AVAILABLE = True except ImportError: X = None; AVAILABLE = False`
  — module-level `None` required for test patching (see `gcp_connector.py` lines 24-32)
- Per-resource try/except with `logger.v()` — not `logger.warning()` — for graceful degradation
- TDD: RED scaffold plan first, then GREEN implementation plan (all v4.2 and v4.3 phases)
- `session_start` pattern: `now = (session_start or datetime.now(timezone.utc)).replace(tzinfo=None)`

### Integration Points
- `run_scan.py:518-521` — endpoint list aggregation; add `db_endpoints` to this list
- `quirk/cbom/builder.py` — Pass 1 processes `cloud_scan_json`; Phase 27 DB endpoints use
  `protocol="POSTGRESQL"` / `protocol="MYSQL"` / `protocol="RDS"` — check if new CBOM
  pass or skip-list entry is needed for these protocol values (likely follows GCP pattern)
- `quirk/intelligence/evidence.py` — identity_ counter pattern; `dar_` counters go after
  existing identity_ block

</code_context>

<specifics>
## Specific Ideas

- `service_detail` for RDS endpoints should encode encryption type:
  `"RDS/none"`, `"RDS/sse-rds"`, `"RDS/sse-kms-aws"`, `"RDS/sse-kms-cmk"` — provides
  richer CBOM output and allows CMK vs AWS-managed key to be distinguished at a glance
- PostgreSQL `dat_scan_json` should store the raw `pg_stat_ssl` query result (or the
  privilege-check result if degraded) as a JSON dict — consistent with `gcs_scan_json`
  storing the raw API response per bucket
- MySQL chaos lab service should use environment variable `MYSQL_ALLOW_EMPTY_PASSWORD=yes`
  or a known scanner password — set in docker-compose to enable passwordless CI testing

</specifics>

<deferred>
## Deferred Ideas

- **Data at Rest dashboard tab** — A dedicated "Data at Rest" tab in the React dashboard
  (alongside TLS, SSH, Cloud, Identity) to surface `dar_` subscore and DB/Storage/K8s/Vault
  findings in one view. Deferred to a future UI polish phase. Ensure it is added when
  dashboard work is next scheduled (DASH-05 candidate).

- **MySQL chaos lab profile with a second 'weak cipher' scenario** — A second MySQL service
  configured with TLS enabled but a forced weak cipher (via `--ssl-cipher=RC4-SHA`) would
  exercise the MEDIUM finding path. Deferred — `--ssl-cipher` support varies by MySQL version;
  add only once tested against the specific image version in use.

- **PostgreSQL chaos lab service with ssl=on, pg_read_all_stats absent** — A second PG
  service that has SSL enabled but grants only a basic user would test the graceful degradation
  (INFO scan_error) path in a live Docker environment. Deferred for now — unit tests cover
  the privilege-check logic; Docker can be added in a lab-hardening phase.

</deferred>

---

*Phase: 27-database-encryption-detection*
*Context gathered: 2026-04-25*
