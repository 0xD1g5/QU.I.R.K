import os
import re
from contextlib import contextmanager
from typing import Iterator, Optional

from sqlalchemy import create_engine, event, inspect as sa_inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from quirk.models import Base  # Declarative Base from quirk/models.py


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
            if not _SAFE_COL_RE.match(col):
                raise ValueError(f"Unsafe column name in migration: {col!r}")
            if col not in existing:
                conn.execute(text(f"ALTER TABLE crypto_endpoints ADD COLUMN {col} TEXT"))
        conn.commit()


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


_V43_COLUMN_DDLS = {
    "dat_scan_json": "TEXT",
    "severity": "VARCHAR(16)",
}


def _ensure_v43_columns(engine) -> None:
    """Add v4.3 data-at-rest columns (dat_scan_json TEXT, severity VARCHAR(16)) if absent.

    Called from init_db() after _ensure_gcp_columns(). Phases 28-30 write to
    dat_scan_json; no new columns needed for subsequent phases.
    """
    existing = {c["name"] for c in sa_inspect(engine).get_columns("crypto_endpoints")}
    with engine.connect() as conn:
        for col, col_type in _V43_COLUMN_DDLS.items():
            if not _SAFE_COL_RE.match(col):
                raise ValueError(f"Unsafe column name in migration: {col!r}")
            if col not in existing:
                conn.execute(text(f"ALTER TABLE crypto_endpoints ADD COLUMN {col} {col_type}"))
        conn.commit()


_EMAIL_COLUMNS = ["email_scan_json"]


def _ensure_email_columns(engine) -> None:
    """Add v4.4 email scanner column (email_scan_json TEXT) if absent (idempotent).

    Phase 32 — uses SQLAlchemy inspector to check existing columns before ALTER TABLE.
    Called from init_db() after _ensure_v43_columns().
    See _EMAIL_COLUMNS for the column list managed by _ensure_email_columns.
    """
    existing = {c["name"] for c in sa_inspect(engine).get_columns("crypto_endpoints")}
    with engine.connect() as conn:
        for col in _EMAIL_COLUMNS:
            if not _SAFE_COL_RE.match(col):
                raise ValueError(f"Unsafe column name in migration: {col!r}")
            if col not in existing:
                conn.execute(text(f"ALTER TABLE crypto_endpoints ADD COLUMN {col} TEXT"))
        conn.commit()


_BROKER_COLUMNS = ["broker_scan_json"]


def _ensure_broker_columns(engine) -> None:
    """Add v4.4 broker scanner column (broker_scan_json TEXT) if absent (idempotent).

    Phase 33 / BROKER-00. Mirrors _ensure_email_columns shape exactly.
    Called from init_db() after _ensure_email_columns().
    """
    existing = {c["name"] for c in sa_inspect(engine).get_columns("crypto_endpoints")}
    with engine.connect() as conn:
        for col in _BROKER_COLUMNS:
            if not _SAFE_COL_RE.match(col):
                raise ValueError(f"Unsafe column name in migration: {col!r}")
            if col not in existing:
                conn.execute(text(f"ALTER TABLE crypto_endpoints ADD COLUMN {col} TEXT"))
        conn.commit()


_PHASE41_COLUMN_DDLS = {
    "scan_error_category": "VARCHAR(32)",
}


def _ensure_phase41_columns(engine) -> None:
    """Phase 41 D-11: add scan_error_category column to crypto_endpoints (idempotent).

    Mirrors the _ensure_v43_columns shape exactly. Called from init_db()
    after _ensure_broker_columns(). Producers populate this alongside
    scan_error so trends.py (D-15) can filter category="missing_extra"
    out of regression-error counts.
    """
    existing = {c["name"] for c in sa_inspect(engine).get_columns("crypto_endpoints")}
    with engine.connect() as conn:
        for col, col_type in _PHASE41_COLUMN_DDLS.items():
            if not _SAFE_COL_RE.match(col):
                raise ValueError(f"Unsafe column name in migration: {col!r}")
            if col not in existing:
                conn.execute(text(f"ALTER TABLE crypto_endpoints ADD COLUMN {col} {col_type}"))
        conn.commit()


_PHASE46_COLUMN_DDLS = {
    "chain_verified": "BOOLEAN",
}


def _ensure_phase46_columns(engine) -> None:
    """Phase 46 TLS-FIND-06: add chain_verified column (idempotent).

    Mirrors _ensure_phase41_columns shape. Called from init_db()
    after _ensure_phase41_columns. SQLite stores BOOLEAN as INTEGER
    (0/1/NULL) — fully compatible with Python's tri-state None/True/False.
    """
    existing = {c["name"] for c in sa_inspect(engine).get_columns("crypto_endpoints")}
    with engine.connect() as conn:
        for col, col_type in _PHASE46_COLUMN_DDLS.items():
            if not _SAFE_COL_RE.match(col):
                raise ValueError(f"Unsafe column name in migration: {col!r}")
            if col not in existing:
                conn.execute(text(f"ALTER TABLE crypto_endpoints ADD COLUMN {col} {col_type}"))
        conn.commit()


_PHASE54_QRAMM_ANSWER_DDLS = {
    "evidence_note": "TEXT",
}


def _ensure_phase54_qramm_columns(engine) -> None:
    """Phase 54 QRAMM-10: add evidence_note column to qramm_answers (idempotent).

    Mirrors _ensure_phase46_columns shape. Called from init_db()
    after _ensure_qramm_tables(). SQLite TEXT column, nullable.
    """
    existing = {c["name"] for c in sa_inspect(engine).get_columns("qramm_answers")}
    with engine.connect() as conn:
        for col, col_type in _PHASE54_QRAMM_ANSWER_DDLS.items():
            if not _SAFE_COL_RE.match(col):
                raise ValueError(f"Unsafe column name in migration: {col!r}")
            if col not in existing:
                conn.execute(text(f"ALTER TABLE qramm_answers ADD COLUMN {col} {col_type}"))
        conn.commit()


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
    _ensure_identity_columns(engine)  # v4.2: add identity columns if missing
    _ensure_gcp_columns(engine)  # v4.3: add GCP columns if missing
    _ensure_v43_columns(engine)  # v4.3: add data-at-rest columns if missing
    _ensure_email_columns(engine)  # v4.4 Phase 32: add email scanner column
    _ensure_broker_columns(engine)      # v4.4 Phase 33 — BROKER-00
    _ensure_phase41_columns(engine)     # Phase 41 D-11 — scan_error_category
    _ensure_phase46_columns(engine)     # Phase 46 — TLS-FIND-06 chain_verified
    _ensure_qramm_tables(engine)         # Phase 51 — QRAMM-01
    _ensure_phase54_qramm_columns(engine)  # Phase 54 — evidence_note column
    _ensure_qramm_profiles_fk(engine)    # Phase 70 BLOCK-07/D-01 — FK retrofit
    _ensure_scheduled_tables(engine)     # Phase 63 — SCHED-01
    _ensure_scan_jobs_table(engine)      # Phase 65 — UI-SCAN-01
    _ensure_scan_checkpoints_table(engine)  # Phase 67 — RESUME-01
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