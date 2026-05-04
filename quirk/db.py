import os
import re
from contextlib import contextmanager
from typing import Iterator, Optional

from sqlalchemy import create_engine, inspect as sa_inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from quirk.models import Base  # Declarative Base from quirk/models.py

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

    # Create schema
    Base.metadata.create_all(engine)
    _ensure_identity_columns(engine)  # v4.2: add identity columns if missing
    _ensure_gcp_columns(engine)  # v4.3: add GCP columns if missing
    _ensure_v43_columns(engine)  # v4.3: add data-at-rest columns if missing
    _ensure_email_columns(engine)  # v4.4 Phase 32: add email scanner column
    _ensure_broker_columns(engine)      # v4.4 Phase 33 — BROKER-00
    _ensure_phase41_columns(engine)     # Phase 41 D-11 — scan_error_category
    _ensure_phase46_columns(engine)     # Phase 46 — TLS-FIND-06 chain_verified
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