import os
from contextlib import contextmanager
from typing import Iterator, Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from quirk.models import Base  # Declarative Base from quirk/models.py


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