"""Phase 65 — /api/jobs router tests (UI-SCAN-01/02/03).

Wave 0 stubs: each test pytest.skip()s with a TODO referencing the plan that
will implement it. Plans 03 and 04 replace the skip() calls with real bodies.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from quirk.dashboard.api.app import create_app
from quirk.dashboard.api.deps import get_db
from quirk.models import Base


def _make_test_engine():
    engine = create_engine(
        "sqlite:///file::memory:?cache=shared&uri=true",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    return engine


def _app_with_db():
    engine = _make_test_engine()
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    return app, TestClient(app, raise_server_exceptions=False)


def test_post_job_creates_row():
    pytest.skip("Implemented in Plan 03 — POST /api/jobs row insert")


def test_post_job_rejects_file_path():
    pytest.skip("Implemented in Plan 03 — @file rejection via ScanSubmitRequest")


def test_post_job_empty_targets():
    pytest.skip("Implemented in Plan 03 — empty targets validation")


def test_post_job_requires_auth():
    pytest.skip("Implemented in Plan 03 — auth dependency wiring")


def test_post_job_requires_csrf():
    pytest.skip("Implemented in Plan 03 — CSRF dependency wiring")


def test_get_job_status():
    pytest.skip("Implemented in Plan 03 — GET /api/jobs/{id} response shape")


def test_get_job_not_found():
    pytest.skip("Implemented in Plan 03 — 404 on unknown job_id")


def test_get_job_requires_auth():
    pytest.skip("Implemented in Plan 03 — GET auth dependency")


def test_stage_index_computation():
    pytest.skip("Implemented in Plan 03 — stage_index backend computation")


def test_cancel_job():
    pytest.skip("Implemented in Plan 03 — DELETE SIGTERM + cancelled state")


def test_stale_job_recovery():
    pytest.skip("Implemented in Plan 04 — lifespan _recover_stale_jobs")
