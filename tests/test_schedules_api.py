"""Tests for GET/POST/PATCH/DELETE /api/schedules — Phase 63 Plan 03 / SCHED-03.

Uses the shared `dashboard_client` fixture from conftest.py which:
  - provides an in-memory SQLite DB with all tables created
  - sets X-Quirk-Request: 1 on every request (CSRF satisfied)
  - does NOT set QUIRK_API_TOKEN (auth disabled by default)

Auth/CSRF negative-path tests use monkeypatch + fresh clients (same pattern as test_api_auth.py).
"""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from quirk.dashboard.api.app import create_app
from quirk.dashboard.api.deps import get_db
from quirk.models import Base, ScheduledRun


# --------------------------------------------------------------------------
# Helpers for auth/csrf negative-path tests
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


_VALID_PAYLOAD = {
    "name": "weekly-prod",
    "cron_expr": "0 2 * * 1",
    "target": "prod.example.com",
    "profile": "balanced",
}


# --------------------------------------------------------------------------
# Test 1: GET /api/schedules with empty DB returns []
# --------------------------------------------------------------------------

def test_get_schedules_empty(dashboard_client):
    """GET /api/schedules with no schedules returns 200 and empty list."""
    response = dashboard_client.get("/api/schedules")
    assert response.status_code == 200, response.text
    data = response.json()
    assert "schedules" in data
    assert data["schedules"] == []


# --------------------------------------------------------------------------
# Test 2: POST /api/schedules creates a schedule
# --------------------------------------------------------------------------

def test_post_schedule_creates(dashboard_client):
    """POST /api/schedules returns 201 with the new schedule."""
    response = dashboard_client.post("/api/schedules", json=_VALID_PAYLOAD)
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["name"] == "weekly-prod"
    assert data["cron_expr"] == "0 2 * * 1"
    assert data["target"] == "prod.example.com"
    assert data["profile"] == "balanced"
    assert data["enabled"] is True
    assert "id" in data
    assert data["id"] > 0


# --------------------------------------------------------------------------
# Test 3: POST with invalid cron returns 400
# --------------------------------------------------------------------------

def test_post_invalid_cron_returns_400(dashboard_client):
    """POST /api/schedules with a bad cron_expr returns 400 (not 500)."""
    payload = {**_VALID_PAYLOAD, "name": "bad-cron", "cron_expr": "not-a-cron"}
    response = dashboard_client.post("/api/schedules", json=payload)
    assert response.status_code == 400, response.text


# --------------------------------------------------------------------------
# Test 4: POST duplicate name returns 409
# --------------------------------------------------------------------------

def test_post_duplicate_name_returns_409(dashboard_client):
    """POSTing the same name twice returns 409 on the second attempt."""
    dashboard_client.post("/api/schedules", json={**_VALID_PAYLOAD, "name": "dup-test"})
    response = dashboard_client.post("/api/schedules", json={**_VALID_PAYLOAD, "name": "dup-test"})
    assert response.status_code == 409, response.text
    data = response.json()
    # T-63-16 / LEAK-02: error message must not stringify the exception
    assert "dup-test" in data["detail"]
    assert "IntegrityError" not in data["detail"]


# --------------------------------------------------------------------------
# Test 5: PATCH toggle enabled
# --------------------------------------------------------------------------

def test_patch_toggle_enabled(dashboard_client):
    """PATCH /api/schedules/{id} with enabled=false toggles the flag."""
    # Create a schedule
    create_resp = dashboard_client.post("/api/schedules", json={**_VALID_PAYLOAD, "name": "toggle-test"})
    assert create_resp.status_code == 201, create_resp.text
    schedule_id = create_resp.json()["id"]

    # Toggle off
    patch_resp = dashboard_client.patch(
        f"/api/schedules/{schedule_id}",
        json={"enabled": False},
    )
    assert patch_resp.status_code == 200, patch_resp.text
    assert patch_resp.json()["enabled"] is False

    # GET confirms persisted
    get_resp = dashboard_client.get("/api/schedules")
    schedules = get_resp.json()["schedules"]
    found = next((s for s in schedules if s["id"] == schedule_id), None)
    assert found is not None
    assert found["enabled"] is False


# --------------------------------------------------------------------------
# Test 6: PATCH requires CSRF header
# --------------------------------------------------------------------------

def test_patch_requires_csrf(monkeypatch):
    """PATCH without X-Quirk-Request: 1 returns 403."""
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)
    _app, tc = _app_with_db()

    # First create a schedule using the CSRF-bearing client
    csrf_client = TestClient(_app, headers={"X-Quirk-Request": "1"})
    create_resp = csrf_client.post("/api/schedules", json={**_VALID_PAYLOAD, "name": "csrf-test"})
    assert create_resp.status_code == 201, create_resp.text
    schedule_id = create_resp.json()["id"]

    # PATCH without CSRF header
    response = tc.patch(
        f"/api/schedules/{schedule_id}",
        json={"enabled": False},
        # No X-Quirk-Request header
    )
    assert response.status_code == 403, response.text


# --------------------------------------------------------------------------
# Test 7: POST requires auth (401 when QUIRK_API_TOKEN is set)
# --------------------------------------------------------------------------

def test_post_requires_auth(monkeypatch):
    """POST without Authorization header returns 401 when QUIRK_API_TOKEN is set."""
    monkeypatch.setenv("QUIRK_API_TOKEN", "test-token")
    _app, tc = _app_with_db()

    response = tc.post(
        "/api/schedules",
        json=_VALID_PAYLOAD,
        headers={"X-Quirk-Request": "1"},
        # No Authorization header
    )
    assert response.status_code == 401, response.text


# --------------------------------------------------------------------------
# Test 8: DELETE removes the schedule
# --------------------------------------------------------------------------

def test_delete_schedule(dashboard_client):
    """DELETE /api/schedules/{id} returns 204; subsequent GET no longer includes that id."""
    create_resp = dashboard_client.post("/api/schedules", json={**_VALID_PAYLOAD, "name": "delete-test"})
    assert create_resp.status_code == 201, create_resp.text
    schedule_id = create_resp.json()["id"]

    delete_resp = dashboard_client.delete(f"/api/schedules/{schedule_id}")
    assert delete_resp.status_code == 204, delete_resp.text

    get_resp = dashboard_client.get("/api/schedules")
    schedules = get_resp.json()["schedules"]
    ids = [s["id"] for s in schedules]
    assert schedule_id not in ids


# --------------------------------------------------------------------------
# Test 9: GET includes next_run_at (computed from croniter)
# --------------------------------------------------------------------------

def test_get_includes_next_run(dashboard_client):
    """After POST with a valid cron_expr and no last_run_at, next_run_at is a non-null ISO-8601 string."""
    payload = {**_VALID_PAYLOAD, "name": "next-run-test"}
    dashboard_client.post("/api/schedules", json=payload)

    get_resp = dashboard_client.get("/api/schedules")
    schedules = get_resp.json()["schedules"]
    found = next((s for s in schedules if s["name"] == "next-run-test"), None)
    assert found is not None
    assert found["next_run_at"] is not None
    # Must be a parsable ISO-8601 string
    from datetime import datetime
    dt = datetime.fromisoformat(found["next_run_at"])
    assert dt is not None


# --------------------------------------------------------------------------
# Test 10: GET includes last_run_status from ScheduledRun
# --------------------------------------------------------------------------

def test_get_includes_last_run_status(dashboard_client):
    """Pre-seed a ScheduledRun row; GET response includes that schedule's last_run_status."""
    from datetime import datetime, timezone

    # Create schedule
    create_resp = dashboard_client.post("/api/schedules", json={**_VALID_PAYLOAD, "name": "run-status-test"})
    assert create_resp.status_code == 201, create_resp.text
    schedule_id = create_resp.json()["id"]

    # Directly seed a ScheduledRun row via the app's DB session
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    # Use the same in-memory DB via the shared-cache URI
    engine = create_engine(
        "sqlite:///file::memory:?cache=shared&uri=true",
        connect_args={"check_same_thread": False},
    )
    TestingSession = sessionmaker(bind=engine)
    db = TestingSession()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    run = ScheduledRun(
        schedule_id=schedule_id,
        dispatched_at=now,
        completed_at=now,
        status="completed",
        scan_output_path=None,
        scan_id=None,
    )
    db.add(run)
    db.commit()
    db.close()

    # GET should now include the run status
    get_resp = dashboard_client.get("/api/schedules")
    schedules = get_resp.json()["schedules"]
    found = next((s for s in schedules if s["id"] == schedule_id), None)
    assert found is not None
    assert found["last_run_status"] == "completed"


# --------------------------------------------------------------------------
# Test 11: test_no_unprotected_mutating_routes (route introspection)
# --------------------------------------------------------------------------

def test_no_unprotected_mutating_routes(monkeypatch):
    """D-06 gate: all POST/PATCH/DELETE /api/schedules routes have require_auth in dependencies.

    This mirrors the existing test_all_mutating_routes_have_auth_dependency test in
    test_api_auth.py but focuses on the new schedules routes. After Plan 03 lands,
    the original test will automatically pick up /api/schedules/* routes too.
    """
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)
    from fastapi.routing import APIRoute
    from quirk.dashboard.api.middleware.auth import require_auth

    app = create_app()
    mutating_methods = {"POST", "PUT", "DELETE", "PATCH"}
    schedules_violations: list[str] = []

    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        if not route.path.startswith("/api/schedules"):
            continue
        route_methods = route.methods or set()
        if not (route_methods & mutating_methods):
            continue

        dep_callables = {dep.dependency for dep in route.dependencies}
        if require_auth not in dep_callables:
            schedules_violations.append(
                f"{sorted(route_methods & mutating_methods)} {route.path} — missing require_auth"
            )

    assert schedules_violations == [], (
        "Schedules mutating routes missing require_auth:\n"
        + "\n".join(schedules_violations)
    )
