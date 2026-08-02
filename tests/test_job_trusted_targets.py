"""Phase 143 / TAIL-02 — POST /api/jobs trusted-targets enforcement.

Mirrors tests/test_scan_submit_request_no_internal.py's server-side-config-load
pattern: force ``quirk.config.load_config`` to a fake cfg exposing
``security.trusted_targets`` and assert the dashboard entry point rejects
out-of-allowlist targets with 422 (no DB row / subprocess) BEFORE the
CIDR-size-cap block, and proceeds (201) when the allowlist is empty or the
target matches.
"""
from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from quirk.dashboard.api.app import create_app
from quirk.dashboard.api.deps import get_db
from quirk.models import Base, ScanJob


class _FakeProc:
    def __init__(self, pid=99999):
        self.pid = pid


def _fake_popen(*args, **kwargs):
    return _FakeProc()


def _app_with_db():
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
    return app, TestClient(app, raise_server_exceptions=False), TestingSession


class _FakeSecurity:
    allow_internal_targets = False
    trusted_targets: list = []


class _FakeCfg:
    security = _FakeSecurity()


def _fake_load_config_factory(trusted_targets):
    class _Security(_FakeSecurity):
        pass

    _Security.trusted_targets = trusted_targets

    class _Cfg(_FakeCfg):
        security = _Security()

    def _fake_load(*args, **kwargs):
        return _Cfg()

    return _fake_load


def test_post_jobs_rejects_target_outside_trusted_targets(monkeypatch):
    monkeypatch.setattr("quirk.dashboard.api.routes.jobs.subprocess.Popen", _fake_popen)
    monkeypatch.setattr(
        "quirk.config.load_config", _fake_load_config_factory(["10.0.0.0/24"])
    )

    _, tc, TestingSession = _app_with_db()
    response = tc.post(
        "/api/jobs",
        json={"targets": "example.com"},
        headers={"X-Quirk-Request": "1"},
    )
    assert response.status_code == 422, response.text
    assert "trusted-targets" in response.text or "trusted_targets" in response.text

    db = TestingSession()
    assert db.query(ScanJob).count() == 0
    db.close()


def test_post_jobs_allows_when_trusted_targets_empty(monkeypatch):
    monkeypatch.setattr("quirk.dashboard.api.routes.jobs.subprocess.Popen", _fake_popen)
    monkeypatch.setattr("quirk.config.load_config", _fake_load_config_factory([]))

    _, tc, TestingSession = _app_with_db()
    response = tc.post(
        "/api/jobs",
        json={"targets": "example.com"},
        headers={"X-Quirk-Request": "1"},
    )
    assert response.status_code == 201, response.text
    job_id = response.json()["job_id"]

    db = TestingSession()
    assert db.get(ScanJob, job_id) is not None
    db.close()


def test_post_jobs_allows_when_target_matches_trusted_targets(monkeypatch):
    monkeypatch.setattr("quirk.dashboard.api.routes.jobs.subprocess.Popen", _fake_popen)
    monkeypatch.setattr(
        "quirk.config.load_config", _fake_load_config_factory(["example.com"])
    )

    _, tc, TestingSession = _app_with_db()
    response = tc.post(
        "/api/jobs",
        json={"targets": "example.com"},
        headers={"X-Quirk-Request": "1"},
    )
    assert response.status_code == 201, response.text
    job_id = response.json()["job_id"]

    db = TestingSession()
    assert db.get(ScanJob, job_id) is not None
    db.close()
