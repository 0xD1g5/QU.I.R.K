"""FastAPI dependency injection for database sessions."""
from __future__ import annotations

import os
from typing import Generator

from sqlalchemy.orm import Session, sessionmaker

from quirk.db import get_engine


def _default_db_path() -> str:
    """Resolve default SQLite path — same logic as run_scan.py."""
    return os.environ.get("QUIRK_DB_PATH", "data/quirk.db")


def get_db() -> Generator[Session, None, None]:
    """FastAPI Depends() dependency — yields a SQLAlchemy session.

    Usage:
        @router.get("/endpoint")
        def my_endpoint(db: Session = Depends(get_db)):
            ...
    """
    db_path = _default_db_path()
    engine = get_engine(db_path)
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
