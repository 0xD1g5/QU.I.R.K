from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from qcscan.models import Base

_ENGINE_CACHE = {}


def _ensure_sqlite_columns(db_path: str) -> None:
    """
    Lightweight schema migration for SQLite:
    - Adds missing columns on crypto_endpoints via ALTER TABLE
    """
    path = db_path
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

    conn = sqlite3.connect(path)
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(crypto_endpoints);")
        cols = {row[1] for row in cur.fetchall()}  # row[1] = column name

        if not cols:
            return

        desired = {
            "tls_supported_versions": "TEXT",
            "tls_supported_ciphers_sample": "TEXT",
            "tls_weak_ciphers_present": "BOOLEAN DEFAULT 0",
            "tls_pfs_supported": "BOOLEAN DEFAULT 0",
            "tls_enum_mode": "TEXT",
            "tls_enum_notes": "TEXT",
        }

        for name, ddl in desired.items():
            if name not in cols:
                cur.execute(f"ALTER TABLE crypto_endpoints ADD COLUMN {name} {ddl};")

        conn.commit()
    finally:
        conn.close()


def init_db(db_path: str) -> None:
    """
    Initialize DB and apply lightweight SQLite migrations.
    """
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    Base.metadata.create_all(engine)

    # Ensure new columns exist after table creation
    _ensure_sqlite_columns(db_path)

    _ENGINE_CACHE[db_path] = engine


def get_engine(db_path: str):
    engine = _ENGINE_CACHE.get(db_path)
    if engine is None:
        init_db(db_path)
        engine = _ENGINE_CACHE[db_path]
    return engine


@contextmanager
def get_session(db_path: str):
    """
    IMPORTANT:
    expire_on_commit=False prevents DetachedInstanceError when we
    commit and then continue to use ORM objects (endpoints) for reporting.
    """
    engine = get_engine(db_path)
    Session = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        future=True,
        expire_on_commit=False,  # ✅ key fix
    )
    session = Session()
    try:
        yield session
    finally:
        session.close()
