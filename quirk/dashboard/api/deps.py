"""FastAPI dependency injection for database sessions."""
from __future__ import annotations

import os
from typing import Generator

from sqlalchemy.orm import Session, sessionmaker

from quirk.db import init_db


def _default_db_path() -> str:
    """Resolve default SQLite path.

    Priority:
    1. QUIRK_DB_PATH env var (explicit override)
    2. Most recently modified quirk.db among common output locations
    3. ./quirk.db fallback
    """
    if val := os.environ.get("QUIRK_DB_PATH"):
        return val
    candidates = ["./quirk.db", "./output/quirk.db", "./quirk-output/quirk.db"]
    existing = [(p, os.path.getmtime(p)) for p in candidates if os.path.isfile(p)]
    if existing:
        return max(existing, key=lambda x: x[1])[0]
    return "./quirk.db"


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
