"""Phase 102 AUTH-02 — X-API-Key header acceptance, precedence, rejection, and passthrough.

Covers:
  - test_x_api_key_accepted: X-API-Key=test-token accepted on protected GET route
  - test_x_api_key_precedence_over_bearer: X-API-Key wins over wrong bearer token
  - test_invalid_x_api_key_returns_401: wrong X-API-Key returns 401
  - test_bearer_still_works: bearer fallback path preserved when no X-API-Key
  - test_auth_disabled_passthrough: no QUIRK_API_TOKEN configured → no auth enforced
"""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from quirk.dashboard.api.app import create_app
from quirk.dashboard.api.deps import get_db
from quirk.models import Base


# --------------------------------------------------------------------------
# Shared DB + app factory helpers (mirrors test_api_auth.py)
# --------------------------------------------------------------------------

def _make_test_engine():
    engine = create_engine(
        "sqlite:///file::memory:?cache=shared&uri=true",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    return engine


def _app_with_db():
    """Create a fresh TestClient backed by an in-memory DB."""
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


# --------------------------------------------------------------------------
# X-API-Key functional tests (AUTH-02)
# --------------------------------------------------------------------------

def test_x_api_key_accepted(monkeypatch):
    """GET /api/scans with X-API-Key=test-token (auth enabled) returns non-401."""
    monkeypatch.setenv("QUIRK_API_TOKEN", "test-token")
    _, tc = _app_with_db()
    response = tc.get("/api/scans", headers={"X-API-Key": "test-token"})
    assert response.status_code != 401, (
        f"X-API-Key with correct token should not be 401, got {response.status_code}: {response.text}"
    )


def test_x_api_key_precedence_over_bearer(monkeypatch):
    """X-API-Key=test-token + Authorization: Bearer wrong-token → non-401 (X-API-Key wins)."""
    monkeypatch.setenv("QUIRK_API_TOKEN", "test-token")
    _, tc = _app_with_db()
    response = tc.get(
        "/api/scans",
        headers={
            "X-API-Key": "test-token",
            "Authorization": "Bearer wrong-token",
        },
    )
    assert response.status_code != 401, (
        f"X-API-Key should take precedence over wrong bearer; got {response.status_code}: {response.text}"
    )


def test_invalid_x_api_key_returns_401(monkeypatch):
    """X-API-Key with wrong value returns 401."""
    monkeypatch.setenv("QUIRK_API_TOKEN", "test-token")
    _, tc = _app_with_db()
    response = tc.get("/api/scans", headers={"X-API-Key": "wrong-token"})
    assert response.status_code == 401, (
        f"Wrong X-API-Key should return 401, got {response.status_code}: {response.text}"
    )


def test_bearer_still_works(monkeypatch):
    """Bearer fallback preserved: no X-API-Key + Authorization: Bearer test-token → non-401."""
    monkeypatch.setenv("QUIRK_API_TOKEN", "test-token")
    _, tc = _app_with_db()
    response = tc.get(
        "/api/scans",
        headers={"Authorization": "Bearer test-token"},
    )
    assert response.status_code != 401, (
        f"Valid bearer with no X-API-Key should not be 401, got {response.status_code}: {response.text}"
    )


def test_auth_disabled_passthrough(monkeypatch):
    """No QUIRK_API_TOKEN configured → GET /api/scans returns non-401 with no auth header."""
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)
    # Patch load_config to return an object with no api_token so YAML path also resolves empty
    import quirk.dashboard.api.middleware.auth as auth_module

    def _no_token():
        return ""

    monkeypatch.setattr(auth_module, "_get_configured_token", _no_token)
    _, tc = _app_with_db()
    response = tc.get("/api/scans")
    assert response.status_code != 401, (
        f"Auth disabled (no token configured) should not be 401, got {response.status_code}: {response.text}"
    )
