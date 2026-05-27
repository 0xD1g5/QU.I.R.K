import os
import re
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator, Literal, Optional

from sqlalchemy import create_engine, event, inspect as sa_inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from quirk.models import Base  # Declarative Base from quirk/models.py


@dataclass(frozen=True)
class ColumnMigrationResult:
    """Phase 85-01 LAUNCH-04: per-column outcome from `run_additive_migration`.

    Attributes:
        table: SQLite table name the column belongs to.
        column: Column name.
        status: ``"added"`` if the column was missing (and was either added
            now or — under ``dry_run=True`` — *would* be added), else
            ``"already-present"``.
    """

    table: str
    column: str
    status: Literal["added", "already-present"]


@event.listens_for(Engine, "connect")
def _sqlite_fk_pragma(dbapi_connection, connection_record):
    """Phase 70 BLOCK-07/D-02: enable per-connection FK enforcement.

    SQLite FK constraints are declared at table-create time but only enforced
    when this PRAGMA is set. Without it, ON DELETE SET NULL is documentation.
    Attached at module level so the hook fires for every Engine in the process
    (including in-memory test engines built via create_engine directly).
    """
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
    finally:
        cursor.close()


# Allowlist pattern for migration column names — prevents SQL injection via column interpolation.
_SAFE_COL_RE = re.compile(r"^[a-z][a-z0-9_]*$")
# Phase 70 BLOCK-08/D-06: allowlist pattern for migration `col_type` DDL fragments.
# Defense-in-depth — current values are hardcoded literals, but the f-string
# interpolation surface remains a future-contributor risk. Bounded VARCHAR(d{1,4}).
_SAFE_COL_TYPE_RE = re.compile(r"^(TEXT|INTEGER|REAL|BOOLEAN|DATETIME|VARCHAR\(\d{1,4}\))$")


def _ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def _sqlite_url(db_path: str) -> str:
    """
    Build a SQLite URL from a path.
    - If db_path is relative, it’s relative to current working directory.
    """
    return f"sqlite:///{db_path}"


def get_engine(db_path: str) -> Engine:
    """
    Create an Engine for the given sqlite db path.
    """
    _ensure_parent_dir(db_path)
    return create_engine(
        _sqlite_url(db_path),
        future=True,
        connect_args={"check_same_thread": False},
    )


# ---------- Phase 77 D-21 (api-cli-core/IN-06): generic _ensure_columns helper ----------
# Consolidates 8 prior per-feature ``_ensure_*_columns`` helpers (identity, GCP,
# v43 / DAT, email, broker, Phase 41 scan_error_category, Phase 46 chain_verified,
# Phase 54 QRAMM evidence_note) into a single SQLite ALTER-TABLE-IF-MISSING
# helper per RESEARCH Pattern 3. The 5 table-creating / FK-rebuild helpers
# (_ensure_qramm_profiles_fk, _ensure_qramm_tables, _ensure_scheduled_tables,
# _ensure_scan_jobs_table, _ensure_scan_checkpoints_table) intentionally remain
# UNTOUCHED — they use Base.metadata.create_all / raw FK rebuild (different
# pattern per RESEARCH inventory recommendation).
# Closes api-cli-core/IN-06.

# Per-feature column lists (column name, DDL fragment). DDL must satisfy
# _SAFE_COL_TYPE_RE; column names must satisfy _SAFE_COL_RE.
_IDENTITY_COLUMNS: tuple[tuple[str, str], ...] = (
    ("kerberos_scan_json", "TEXT"),  # Phase v4.2 identity scanner
    ("saml_scan_json",     "TEXT"),
    ("dnssec_scan_json",   "TEXT"),
    ("smime_scan_json",    "TEXT"),  # Phase 79 SMIME-03
    ("adcs_scan_json",     "TEXT"),  # Phase 80 ADCS-03
)
_GCP_COLUMNS: tuple[tuple[str, str], ...] = (
    ("gcs_scan_json", "TEXT"),  # Phase v4.3 GCP / GCS scanner
)
_V43_COLUMNS: tuple[tuple[str, str], ...] = (
    ("dat_scan_json", "TEXT"),         # Phase v4.3 data-at-rest
    ("severity",      "VARCHAR(16)"),
)
_EMAIL_COLUMNS: tuple[tuple[str, str], ...] = (
    ("email_scan_json", "TEXT"),  # Phase 32 email scanner
)
_BROKER_COLUMNS: tuple[tuple[str, str], ...] = (
    ("broker_scan_json", "TEXT"),  # Phase 33 broker scanner (BROKER-00)
)
_PHASE41_COLUMNS: tuple[tuple[str, str], ...] = (
    ("scan_error_category", "VARCHAR(32)"),  # Phase 41 D-11
)
_PHASE46_COLUMNS: tuple[tuple[str, str], ...] = (
    # SQLite stores BOOLEAN as INTEGER (0/1/NULL); fully compatible with
    # Python's tri-state None/True/False — see Phase 46 TLS-FIND-06.
    ("chain_verified", "BOOLEAN"),
)
_PHASE54_QRAMM_ANSWER_COLUMNS: tuple[tuple[str, str], ...] = (
    ("evidence_note", "TEXT"),  # Phase 54 QRAMM-10
)
_V54_SENSOR_COLUMNS: tuple[tuple[str, str], ...] = (
    # Phase 107 MODEL-01: nullable sensor tracking columns on crypto_endpoints.
    # NULL sensor_id = implicit local sensor (backward-compatible with pre-v5.4 rows).
    ("sensor_id", "TEXT"),
    ("segment",   "TEXT"),
)
_V55_SENSOR_TOKEN_COLUMNS: tuple[tuple[str, str], ...] = (
    # Phase 113 AUTH-02 / D-06: soft-revoke via additive nullable column.
    # None = active; set = revoked. No data rewrite, no destructive DDL.
    ("revoked_at", "DATETIME"),
)


def _ensure_columns(
    engine,
    table: str,
    expected: tuple[tuple[str, str], ...],
) -> None:
    """Generic SQLite ALTER-TABLE-IF-MISSING migration helper.

    Phase 77 D-21 / RESEARCH Pattern 3 — consolidates 8 prior per-feature
    helpers. Mirrors their inspector-first, idempotent shape:
      1. Read existing columns via SQLAlchemy inspector
      2. For each (col, ddl) in ``expected``:
         - reject names not matching ``_SAFE_COL_RE`` (defense in depth)
         - reject DDL fragments not matching ``_SAFE_COL_TYPE_RE``
         - skip if already present
         - otherwise ``ALTER TABLE {table} ADD COLUMN {col} {ddl}``

    Args:
        engine: SQLAlchemy Engine bound to the target SQLite database.
        table: Target table name (must already exist; create_all runs first).
        expected: Tuple of (column_name, ddl_fragment) pairs.
    """
    existing = {c["name"] for c in sa_inspect(engine).get_columns(table)}
    with engine.connect() as conn:
        for col, col_type in expected:
            if not _SAFE_COL_RE.match(col):
                raise ValueError(f"Unsafe column name in migration: {col!r}")
            if not _SAFE_COL_TYPE_RE.match(col_type):
                raise ValueError(f"Unsafe column type in migration: {col_type!r}")
            if col not in existing:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}"))
        conn.commit()


# ---------- Phase 85-01 LAUNCH-04: public additive-migration registry --------
#
# `_ADDITIVE_MIGRATIONS` enumerates every (table, columns) pair already
# governed by `_ensure_columns` callsites in `init_db`. It is the single
# source of truth shared by both `init_db` and `run_additive_migration`.
#
# Pure tables (those created via `Base.metadata.create_all` — qramm_*,
# scheduled_*, scan_jobs, scan_checkpoints) are intentionally NOT listed
# here: they are never "additively migrated", they are created whole or not
# at all by their `_ensure_*_table` helpers.
#
# Ordering preserved exactly from the prior 8-helper chain.
_ADDITIVE_MIGRATIONS: tuple[tuple[str, tuple[tuple[str, str], ...]], ...] = (
    ("crypto_endpoints", _IDENTITY_COLUMNS),   # identity scanner fields
    ("crypto_endpoints", _GCP_COLUMNS),         # GCP connector fields
    ("crypto_endpoints", _V43_COLUMNS),         # data-at-rest fields
    ("crypto_endpoints", _EMAIL_COLUMNS),       # Phase 32 email
    ("crypto_endpoints", _BROKER_COLUMNS),      # Phase 33 broker
    ("crypto_endpoints", _PHASE41_COLUMNS),     # Phase 41 D-11
    ("crypto_endpoints", _PHASE46_COLUMNS),     # Phase 46
    ("qramm_answers",    _PHASE54_QRAMM_ANSWER_COLUMNS),  # Phase 54
    ("crypto_endpoints", _V54_SENSOR_COLUMNS),  # Phase 107 MODEL-01
    ("sensor_tokens",    _V55_SENSOR_TOKEN_COLUMNS),  # Phase 113 AUTH-02
)


def run_additive_migration(
    engine,
    *,
    dry_run: bool = False,
) -> list[ColumnMigrationResult]:
    """Phase 85-01 LAUNCH-04: idempotent additive-only column migration.

    Walks every (table, column) pair in ``_ADDITIVE_MIGRATIONS``, classifies
    each as ``"added"`` (currently missing) or ``"already-present"``, and
    — unless ``dry_run`` is True — invokes the existing allowlist-guarded
    ``_ensure_columns`` installer to bring the schema current.

    Per D-LAUNCH-04: additive-only — this helper NEVER drops, renames, or
    retypes columns, and never raises on an `already-present` column. All
    SQL still flows through the ``_SAFE_COL_RE`` / ``_SAFE_COL_TYPE_RE``
    allowlists in ``_ensure_columns``; this function does not interpolate
    any DDL itself.

    Args:
        engine: SQLAlchemy Engine bound to the target SQLite database.
            Caller is responsible for ensuring the underlying base tables
            exist (typically via ``Base.metadata.create_all`` or
            ``init_db``).
        dry_run: When True, report what *would* be added but write nothing.

    Returns:
        One ``ColumnMigrationResult`` per (table, column) pair in
        ``_ADDITIVE_MIGRATIONS``, in declaration order.
    """
    results: list[ColumnMigrationResult] = []
    insp = sa_inspect(engine)
    for table, columns in _ADDITIVE_MIGRATIONS:
        existing = {c["name"] for c in insp.get_columns(table)}
        missing: list[tuple[str, str]] = []
        for col, col_type in columns:
            if col in existing:
                results.append(
                    ColumnMigrationResult(table=table, column=col, status="already-present")
                )
            else:
                results.append(
                    ColumnMigrationResult(table=table, column=col, status="added")
                )
                missing.append((col, col_type))
        if missing and not dry_run:
            # Reuse the existing allowlist-guarded installer for the
            # missing-only subset. _ensure_columns is itself idempotent,
            # but passing only the missing subset keeps the audit trail
            # tight and avoids a second inspector pass per table.
            _ensure_columns(engine, table, tuple(missing))
    return results


def _ensure_qramm_profiles_fk(engine) -> None:
    """Phase 70 BLOCK-07/D-01: retrofit FK on qramm_profiles.session_id.

    Pre-existing on-disk databases were created when QRAMMProfile.session_id
    had no DB-level FK declaration. SQLite does not support
    ALTER TABLE ... ADD CONSTRAINT, so we follow the canonical 12-step rebuild
    (https://sqlite.org/lang_altertable.html §7):
      1. PRAGMA foreign_keys=OFF (outside any transaction — Pitfall 3)
      2. BEGIN
      3. CREATE qramm_profiles_new with the FK clause
      4. INSERT ... SELECT (explicit column list — Pitfall 1)
      5. DROP qramm_profiles
      6. RENAME _new -> qramm_profiles
      7. COMMIT
      8. PRAGMA foreign_keys=ON

    Idempotent: skip when PRAGMA foreign_key_list('qramm_profiles') already
    lists a row referencing qramm_sessions.
    """
    # Idempotency check uses an ORM connection (auto-managed transaction is fine
    # for a read-only PRAGMA query).
    with engine.connect() as conn:
        fk_rows = conn.execute(
            text("PRAGMA foreign_key_list('qramm_profiles')")
        ).fetchall()
    if any(row[2] == "qramm_sessions" for row in fk_rows):
        return  # idempotent — FK already present

    # Pitfall 3: PRAGMA foreign_keys is a no-op inside a transaction.
    # SQLAlchemy 2.x auto-begins a transaction on the first execute via
    # engine.connect(), so we drop down to the raw DBAPI connection (which is
    # in autocommit mode by default for the SQLite driver) to issue PRAGMA
    # statements outside any transaction, then BEGIN/COMMIT explicitly.
    raw = engine.raw_connection()
    try:
        cursor = raw.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys=OFF")
            cursor.execute("BEGIN")
            try:
                cursor.execute(
                    """
                    CREATE TABLE qramm_profiles_new (
                        id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                        session_id INTEGER REFERENCES qramm_sessions(id) ON DELETE SET NULL,
                        industry VARCHAR(64),
                        org_size VARCHAR(32),
                        data_sensitivity VARCHAR(32),
                        regulatory_obligations TEXT,
                        geographic_scope VARCHAR(32),
                        multiplier FLOAT,
                        created_at DATETIME
                    )
                    """
                )
                cursor.execute(
                    "INSERT INTO qramm_profiles_new "
                    "(id, session_id, industry, org_size, data_sensitivity, "
                    "regulatory_obligations, geographic_scope, multiplier, created_at) "
                    "SELECT id, session_id, industry, org_size, data_sensitivity, "
                    "regulatory_obligations, geographic_scope, multiplier, created_at "
                    "FROM qramm_profiles"
                )
                cursor.execute("DROP TABLE qramm_profiles")
                cursor.execute(
                    "ALTER TABLE qramm_profiles_new RENAME TO qramm_profiles"
                )
                cursor.execute("COMMIT")
            except Exception:
                cursor.execute("ROLLBACK")
                raise
            finally:
                cursor.execute("PRAGMA foreign_keys=ON")
        finally:
            cursor.close()
    finally:
        raw.close()


def _ensure_qramm_tables(engine) -> None:
    """Phase 51 QRAMM-01: create QRAMM assessment tables if absent (idempotent).

    Uses Base.metadata.create_all with checkfirst=True. These are entirely
    new tables (qramm_sessions, qramm_answers, qramm_profiles) — not new
    columns on crypto_endpoints — so we use create_all rather than the
    ALTER TABLE pattern of the other _ensure_* functions.

    QRAMMSession/QRAMMAnswer/QRAMMProfile are registered on Base.metadata
    via the import of quirk.models at the top of this file (D-05).
    """
    Base.metadata.create_all(engine, checkfirst=True)


def _ensure_scheduled_tables(engine) -> None:
    """Phase 63 SCHED-01: create scheduled_scans and scheduled_runs tables if absent.

    Uses Base.metadata.create_all with checkfirst=True. ScheduledScan and
    ScheduledRun are registered on Base.metadata via import of quirk.models.
    New tables only — not new columns — so create_all is correct (not ALTER TABLE).
    """
    Base.metadata.create_all(engine, checkfirst=True)


def _ensure_scan_jobs_table(engine) -> None:
    """Phase 65 UI-SCAN-01: create scan_jobs table if absent (idempotent).

    ScanJob is registered on Base.metadata via import of quirk.models.
    Uses checkfirst=True per the same pattern as _ensure_scheduled_tables.
    """
    Base.metadata.create_all(engine, checkfirst=True)


def _ensure_scan_checkpoints_table(engine) -> None:
    """Phase 67 RESUME-01: create scan_checkpoints table if absent (idempotent).

    ScanCheckpoint is registered on Base.metadata via import of quirk.models.
    Uses checkfirst=True per the same pattern as _ensure_scan_jobs_table.
    """
    Base.metadata.create_all(engine, checkfirst=True)


def _ensure_integration_deliveries_table(engine) -> None:
    """Phase 101 NOTIFY-07: create integration_deliveries table if absent (idempotent).

    IntegrationDelivery is registered on Base.metadata via import of quirk.models.
    Uses Base.metadata.create_all with checkfirst=True — same pattern as
    _ensure_scheduled_tables. New table only — not new columns — so create_all is correct.
    Shared primitive for Phases 103 (SIEM), 104 (Jira), 105 (ServiceNow).
    """
    Base.metadata.create_all(engine, checkfirst=True)


def _ensure_merge_runs_table(engine) -> None:
    """Phase 110 MERGE-05: create merge_runs table if absent (idempotent).

    MergeRun is registered on Base.metadata via import of quirk.models.
    Uses Base.metadata.create_all with checkfirst=True — same pattern as
    _ensure_integration_deliveries_table. New table only — not new columns.
    """
    Base.metadata.create_all(engine, checkfirst=True)


def init_db(db_path: str) -> Engine:
    """
    Ensure the sqlite DB file exists on disk and all tables are created.

    Why this works:
    - SQLite creates the file when it is opened for read/write (and a connection is made).
    - We force an actual connection immediately.
    - Then we run Base.metadata.create_all(engine).
    """
    engine = get_engine(db_path)

    # Force file creation now (not "later when first used")
    with engine.connect() as conn:
        conn.commit()

    # Create schema (checkfirst=True prevents "table already exists" on restart)
    Base.metadata.create_all(engine, checkfirst=True)
    # Phase 77 D-21: column-adding migrations flow through the generic
    # `_ensure_columns(engine, table, expected)` helper.
    # Phase 85-01 LAUNCH-04: the (table, columns) tuples are now sourced from
    # `_ADDITIVE_MIGRATIONS` so `init_db` and `run_additive_migration` share
    # one registry. Ordering is preserved from the prior 8-helper chain.
    # The qramm_answers migration is split out so `_ensure_qramm_tables`
    # (which creates the table) runs *before* its ALTER TABLE step.
    for table, columns in _ADDITIVE_MIGRATIONS:
        if table == "qramm_answers":
            continue  # handled after _ensure_qramm_tables below
        _ensure_columns(engine, table, columns)
    _ensure_qramm_tables(engine)                                       # Phase 51 QRAMM-01
    _ensure_columns(engine, "qramm_answers", _PHASE54_QRAMM_ANSWER_COLUMNS)  # Phase 54
    _ensure_qramm_profiles_fk(engine)    # Phase 70 BLOCK-07/D-01 — FK retrofit
    _ensure_scheduled_tables(engine)     # Phase 63 — SCHED-01
    _ensure_scan_jobs_table(engine)      # Phase 65 — UI-SCAN-01
    _ensure_scan_checkpoints_table(engine)  # Phase 67 — RESUME-01
    _ensure_integration_deliveries_table(engine)  # Phase 101 — NOTIFY-07
    _ensure_merge_runs_table(engine)              # Phase 110 — MERGE-05
    # Phase 107 D-02: explicit idempotent index on crypto_endpoints.sensor_id.
    # Column(index=True) + create_all(checkfirst=True) does NOT retro-add an
    # index to a pre-existing table, so this step is required for backward
    # compatibility (MODEL-01). Index name, table, and column are hardcoded
    # literals — no user-controlled interpolation (T-107-02).
    with engine.connect() as conn:
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_crypto_endpoints_sensor_id"
            " ON crypto_endpoints (sensor_id)"
        ))
        conn.commit()
    return engine


@contextmanager
def get_session(db_path: str) -> Iterator:
    """
    Context manager that yields a SQLAlchemy session.

    Key setting: expire_on_commit=False
    - Prevents ORM instances from becoming "expired" after commit,
      which avoids DetachedInstanceError when you later read attributes
      after the session is closed.
    """
    engine = get_engine(db_path)

    Session = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        future=True,
        expire_on_commit=False,  # ✅ critical for your pipeline
    )

    session = Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()