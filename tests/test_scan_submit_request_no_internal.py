"""Phase 120 / Plan 01 / Task 2 — AC-03 regression test.

Verifies that ``allow_internal_targets`` is no longer a client-controllable field on
``ScanSubmitRequest`` (it is server-policy only, sourced from ``quirk.config``).

Three assertions:
  1. Schema: ``"allow_internal_targets" not in ScanSubmitRequest.model_fields``.
  2. Construction with the extra key drops it (``extra="ignore"``); the resulting
     instance exposes no ``allow_internal_targets`` attribute.
  3. POST /api/jobs with the field in the JSON body produces a job whose config
     file was written with ``security.allow_internal_targets`` matching the
     SERVER config — NOT the client-supplied value.
"""
from __future__ import annotations

from pathlib import Path

import yaml
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from quirk.dashboard.api.app import create_app
from quirk.dashboard.api.deps import get_db
from quirk.dashboard.api.schemas import ScanSubmitRequest
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


# ---------------------------------------------------------------------------
# Schema-level assertions
# ---------------------------------------------------------------------------

def test_schema_has_no_allow_internal_targets_field():
    """AC-03: the field must be removed from the request schema entirely."""
    assert "allow_internal_targets" not in ScanSubmitRequest.model_fields


def test_client_supplied_allow_internal_targets_is_dropped():
    """Pydantic extra='ignore' silently drops the field — instance has no attribute."""
    req = ScanSubmitRequest(
        targets="example.com",
        allow_internal_targets=True,  # type: ignore[call-arg]
    )
    assert getattr(req, "allow_internal_targets", None) is None


# ---------------------------------------------------------------------------
# Route-level assertion
# ---------------------------------------------------------------------------

def test_post_jobs_ignores_client_allow_internal_and_uses_server_config(monkeypatch, tmp_path):
    """POST /api/jobs with allow_internal_targets=true must NOT enable internal targeting.

    The route must source the value from the server's config (which we monkey-patch
    to False) regardless of the client-supplied true.
    """
    monkeypatch.setattr("quirk.dashboard.api.routes.jobs.subprocess.Popen", _fake_popen)

    # Force the server-side config to allow_internal_targets=False.
    class _FakeSecurity:
        allow_internal_targets = False

    class _FakeCfg:
        security = _FakeSecurity()

    def _fake_load(*args, **kwargs):
        return _FakeCfg()

    # The route's lazy import resolves at call time — patch the canonical name.
    monkeypatch.setattr("quirk.config.load_config", _fake_load)

    _, tc, TestingSession = _app_with_db()
    response = tc.post(
        "/api/jobs",
        json={"targets": "example.com", "allow_internal_targets": True},
        headers={"X-Quirk-Request": "1"},
    )
    assert response.status_code == 201, response.text
    job_id = response.json()["job_id"]

    # Inspect the written config YAML — that is the durable record of the value
    # the spawned scanner would honour.
    cfg_path = Path("output/jobs") / job_id / "config.yaml"
    assert cfg_path.exists(), f"job config not written at {cfg_path}"
    with open(cfg_path) as fh:
        written = yaml.safe_load(fh)
    assert written["security"]["allow_internal_targets"] is False, (
        "client-supplied allow_internal_targets=true must NOT propagate to scan config"
    )

    # Sanity: row created.
    db = TestingSession()
    assert db.get(ScanJob, job_id) is not None
    db.close()


def test_post_jobs_without_field_still_works(monkeypatch):
    """Regression guard: omitting the field still produces a valid job."""
    monkeypatch.setattr("quirk.dashboard.api.routes.jobs.subprocess.Popen", _fake_popen)

    class _FakeSecurity:
        allow_internal_targets = False

    class _FakeCfg:
        security = _FakeSecurity()

    monkeypatch.setattr("quirk.config.load_config", lambda *a, **k: _FakeCfg())

    _, tc, _ = _app_with_db()
    response = tc.post(
        "/api/jobs",
        json={"targets": "example.com"},
        headers={"X-Quirk-Request": "1"},
    )
    assert response.status_code == 201, response.text
