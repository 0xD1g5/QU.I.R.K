"""FastAPI dependency injection for database sessions."""
from __future__ import annotations

import os
from typing import Generator

from sqlalchemy.orm import Session, sessionmaker

from quirk.db import init_db


def _default_db_path() -> str:
    """Resolve default SQLite path (Phase 75 D-03 / WR-03).

    Priority:
    1. ``QUIRK_DB_PATH`` env var — explicit override, returned verbatim.
    2. Canonical path ``./quirk-output/quirk.db`` (RESEARCH A1 / Phase 74 D-05).
    3. Legacy compatibility — if exactly one legacy DB exists in the historical
       search dirs, return it.
    4. If multiple legacy DBs exist, raise ``ValueError`` — fail loud. Operator
       must disambiguate via ``QUIRK_DB_PATH``. Mirrors Phase 71 D-06.
    """
    if val := os.environ.get("QUIRK_DB_PATH"):
        return val
    canonical = "./quirk-output/quirk.db"
    candidates = ["./quirk.db", "./output/quirk.db", canonical]
    found = [p for p in candidates if os.path.isfile(p)]
    if len(found) > 1:
        raise ValueError(
            f"Multiple QU.I.R.K. DBs found at {sorted(found)}; "
            "set QUIRK_DB_PATH explicitly"
        )
    if len(found) == 1:
        return found[0]
    return canonical


def get_db() -> Generator[Session, None, None]:
    """FastAPI Depends() dependency — yields a SQLAlchemy session.

    Usage:
        @router.get("/endpoint")
        def my_endpoint(db: Session = Depends(get_db)):
            ...
    """
    db_path = _default_db_path()
    engine = init_db(db_path)
    SessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
