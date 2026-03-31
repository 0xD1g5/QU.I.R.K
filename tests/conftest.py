"""Shared fixtures for dashboard test suite."""
import pytest


@pytest.fixture
def dashboard_client():
    """FastAPI TestClient for the dashboard app with an in-memory test database.

    Overrides the get_db dependency to use a fresh in-memory SQLite DB so
    tests pass without requiring a real data/quirk.db file.
    """
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from quirk.dashboard.api.app import create_app
        from quirk.dashboard.api.deps import get_db
        from quirk.models import Base
        from fastapi.testclient import TestClient

        # Create a shared in-memory SQLite DB with all tables.
        # Use file::memory:?cache=shared so the same DB is accessible from
        # the worker thread FastAPI uses for sync route handlers.
        engine = create_engine(
            "sqlite:///file::memory:?cache=shared&uri=true",
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(engine)
        TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

        def override_get_db():
            db = TestingSession()
            try:
                yield db
            finally:
                db.close()

        app = create_app()
        app.dependency_overrides[get_db] = override_get_db
        return TestClient(app)
    except ImportError:
        pytest.skip("quirk.dashboard not yet implemented")
