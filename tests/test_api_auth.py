"""Auth + CSRF + rate-limit + CORS + GET-route auth + pdf port-clamp integration tests.

Phase 58 Plan 04 — HARDEN-API-01/02/03/05
Covers:
  - Bearer token auth enforcement on mutating and read-only routes (D-03, D-04, D-05)
  - CSRF header enforcement on mutating routes (D-07)
  - Rate-limit 60/min/IP with Retry-After (HARDEN-API-03)
  - CORS allowlist enforcement (HARDEN-API-02)
  - Route-introspection regression gate (D-06) — fails CI when any new mutating route lacks auth
  - PDF port-range clamp functional test (D-11 / HARDEN-API-05)
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
# Shared DB + app factory helpers
# --------------------------------------------------------------------------

def _make_test_engine():
    engine = create_engine(
        "sqlite:///file::memory:?cache=shared&uri=true",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    return engine


def _app_with_db():
    """Create a fresh TestClient backed by an in-memory DB, no auth by default."""
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
# Fixtures
# --------------------------------------------------------------------------

@pytest.fixture
def client(monkeypatch):
    """TestClient with QUIRK_API_TOKEN unset — auth disabled."""
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)
    _app, tc = _app_with_db()
    return tc


@pytest.fixture
def authed_client(monkeypatch):
    """TestClient with QUIRK_API_TOKEN=test-token — auth enabled."""
    monkeypatch.setenv("QUIRK_API_TOKEN", "test-token")
    _app, tc = _app_with_db()
    return _app, tc


# --------------------------------------------------------------------------
# Health exemption
# --------------------------------------------------------------------------

def test_health_endpoint_exempt_from_auth(monkeypatch):
    """GET /api/health returns 200 with no auth token even when QUIRK_API_TOKEN is set."""
    monkeypatch.setenv("QUIRK_API_TOKEN", "test-token")
    _, tc = _app_with_db()
    response = tc.get("/api/health")
    assert response.status_code == 200, (
        f"GET /api/health should be 200 (auth-exempt), got {response.status_code}"
    )


# --------------------------------------------------------------------------
# Auth enforcement — mutating routes
# --------------------------------------------------------------------------

def test_mutating_route_returns_401_without_token(monkeypatch):
    """POST /api/qramm/sessions without Authorization header returns 401 when token is configured."""
    monkeypatch.setenv("QUIRK_API_TOKEN", "test-token")
    _, tc = _app_with_db()
    response = tc.post(
        "/api/qramm/sessions",
        json={},
        headers={"X-Quirk-Request": "1"},
    )
    assert response.status_code == 401, (
        f"POST without auth should be 401, got {response.status_code}: {response.text}"
    )


def test_mutating_route_accepts_valid_token(monkeypatch):
    """POST /api/qramm/sessions with correct Bearer token does not return 401."""
    monkeypatch.setenv("QUIRK_API_TOKEN", "test-token")
    _, tc = _app_with_db()
    response = tc.post(
        "/api/qramm/sessions",
        json={},
        headers={
            "Authorization": "Bearer test-token",
            "X-Quirk-Request": "1",
        },
    )
    assert response.status_code != 401, (
        f"POST with valid token should not be 401, got {response.status_code}: {response.text}"
    )


def test_invalid_token_returns_401(monkeypatch):
    """Wrong bearer token returns 401 with QRK-DASHBOARD-001 error code."""
    monkeypatch.setenv("QUIRK_API_TOKEN", "test-token")
    _, tc = _app_with_db()
    response = tc.post(
        "/api/qramm/sessions",
        json={},
        headers={
            "Authorization": "Bearer wrong-token",
            "X-Quirk-Request": "1",
        },
    )
    assert response.status_code == 401
    assert "QRK-DASHBOARD-001" in response.json()["detail"]


def test_auth_disabled_when_no_token_configured(client):
    """POST routes return non-401 when QUIRK_API_TOKEN env var is unset."""
    response = client.post(
        "/api/qramm/sessions",
        json={},
        headers={"X-Quirk-Request": "1"},
    )
    assert response.status_code != 401, (
        f"Auth disabled — should not be 401, got {response.status_code}"
    )


# --------------------------------------------------------------------------
# CSRF enforcement
# --------------------------------------------------------------------------

def test_csrf_missing_header_returns_403(monkeypatch):
    """POST with valid auth but without X-Quirk-Request returns 403."""
    monkeypatch.setenv("QUIRK_API_TOKEN", "test-token")
    _, tc = _app_with_db()
    response = tc.post(
        "/api/qramm/sessions",
        json={},
        headers={"Authorization": "Bearer test-token"},
        # No X-Quirk-Request header
    )
    assert response.status_code == 403, (
        f"POST without CSRF header should be 403, got {response.status_code}: {response.text}"
    )


def test_csrf_present_passes(monkeypatch):
    """POST with valid auth AND X-Quirk-Request: 1 does not return 403."""
    monkeypatch.setenv("QUIRK_API_TOKEN", "test-token")
    _, tc = _app_with_db()
    response = tc.post(
        "/api/qramm/sessions",
        json={},
        headers={
            "Authorization": "Bearer test-token",
            "X-Quirk-Request": "1",
        },
    )
    assert response.status_code != 403, (
        f"POST with CSRF header should not be 403, got {response.status_code}: {response.text}"
    )


def test_csrf_body_content(monkeypatch):
    """403 response body has detail = 'Missing CSRF header: X-Quirk-Request'."""
    monkeypatch.setenv("QUIRK_API_TOKEN", "test-token")
    _, tc = _app_with_db()
    response = tc.post(
        "/api/qramm/sessions",
        json={},
        headers={"Authorization": "Bearer test-token"},
    )
    assert response.status_code == 403
    assert "QRK-DASHBOARD-002" in response.json()["detail"]


# --------------------------------------------------------------------------
# Rate limiting
# --------------------------------------------------------------------------

def test_rate_limit_allows_60_requests(monkeypatch):
    """60 POST requests from same IP within window all succeed (not 429)."""
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)
    # Use a distinct in-memory DB so rate-limit state is fresh
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
    tc = TestClient(app, raise_server_exceptions=False)

    results = []
    for _ in range(60):
        r = tc.post(
            "/api/qramm/sessions",
            json={},
            headers={"X-Quirk-Request": "1"},
        )
        results.append(r.status_code)

    rate_limited = [s for s in results if s == 429]
    assert len(rate_limited) == 0, (
        f"Expected 0 rate-limited requests in first 60, got {len(rate_limited)}: {results}"
    )


def test_rate_limit_blocks_61st_request(monkeypatch):
    """61st POST request returns 429 with Retry-After header."""
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)
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
    tc = TestClient(app, raise_server_exceptions=False)

    # Send 60 requests to fill the window
    for _ in range(60):
        tc.post(
            "/api/qramm/sessions",
            json={},
            headers={"X-Quirk-Request": "1"},
        )

    # 61st must be rejected
    response = tc.post(
        "/api/qramm/sessions",
        json={},
        headers={"X-Quirk-Request": "1"},
    )
    assert response.status_code == 429, (
        f"61st request should be 429, got {response.status_code}"
    )
    assert "retry-after" in response.headers, (
        "429 response must include Retry-After header"
    )


def test_health_exempt_from_rate_limit(monkeypatch):
    """GET /api/health never returns 429 regardless of count."""
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)
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
    tc = TestClient(app, raise_server_exceptions=False)

    # The rate limiter only applies to mutating methods; GET /api/health is always exempt.
    for _ in range(65):
        r = tc.get("/api/health")
        assert r.status_code != 429, "GET /api/health must never be rate-limited"


# --------------------------------------------------------------------------
# Route-introspection regression gate (D-06)
# --------------------------------------------------------------------------

def test_all_mutating_routes_have_auth_dependency(monkeypatch):
    """D-06 gate: every POST/PUT/DELETE/PATCH (except /api/health) must have an auth dependency.

    This test enumerates app.routes and asserts that either require_auth (operator auth)
    or require_sensor_auth (per-sensor auth, Phase 113) is present in the dependency
    chain of every mutating route. It fails CI automatically if any future developer
    adds a mutating route without wiring auth.

    Phase 113 split (D-01/D-02):
    - POST /api/sensor/push intentionally uses require_sensor_auth (not require_auth).
      Operator tokens do not authenticate sensor pushes; sensor tokens do not authorize
      operator routes. Both are valid auth dependencies for the D-06 gate.
    """
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)
    from fastapi.routing import APIRoute
    from quirk.dashboard.api.middleware.auth import require_auth
    from quirk.dashboard.api.middleware.sensor_auth import require_sensor_auth

    app = create_app()
    mutating_methods = {"POST", "PUT", "DELETE", "PATCH"}
    violations: list[str] = []
    # Accepted auth dependencies: operator auth OR per-sensor auth (D-01/D-02 split)
    auth_deps = {require_auth, require_sensor_auth}

    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        route_methods = route.methods or set()
        if not (route_methods & mutating_methods):
            continue
        # Skip the health endpoint — it is explicitly exempt (D-05)
        if route.path in {"/api/health", "/api/health/"}:
            continue

        # Collect dependency callables from the route's dependency list
        dep_callables = {dep.dependency for dep in route.dependencies}
        if not (dep_callables & auth_deps):
            violations.append(
                f"{sorted(route_methods & mutating_methods)} {route.path} — missing require_auth"
            )

    assert violations == [], (
        "The following mutating routes are missing require_auth (D-06 violation):\n"
        + "\n".join(violations)
    )


# --------------------------------------------------------------------------
# GET route auth (D-05 — read routes are not exempt)
# --------------------------------------------------------------------------

def test_get_routes_require_auth(monkeypatch):
    """GET /api/scans and GET /api/trends return 401 without auth token when token is configured."""
    monkeypatch.setenv("QUIRK_API_TOKEN", "test-token")
    _, tc = _app_with_db()

    for path in ("/api/scans", "/api/trends"):
        response = tc.get(path)
        assert response.status_code == 401, (
            f"GET {path} without auth should be 401, got {response.status_code}: {response.text}"
        )


# --------------------------------------------------------------------------
# CORS
# --------------------------------------------------------------------------

def test_cors_allows_loopback_origin(monkeypatch):
    """OPTIONS to any route with Origin: http://127.0.0.1 → response includes Access-Control-Allow-Origin."""
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)
    monkeypatch.delenv("QUIRK_CORS_ORIGINS", raising=False)
    _, tc = _app_with_db()

    response = tc.options(
        "/api/health",
        headers={
            "Origin": "http://127.0.0.1",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert "access-control-allow-origin" in response.headers, (
        f"Loopback preflight should include Access-Control-Allow-Origin, "
        f"got headers: {dict(response.headers)}"
    )


def test_cors_blocks_foreign_origin(monkeypatch):
    """OPTIONS to any route with Origin: http://evil.example.com → no Access-Control-Allow-Origin."""
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)
    monkeypatch.delenv("QUIRK_CORS_ORIGINS", raising=False)
    _, tc = _app_with_db()

    response = tc.options(
        "/api/health",
        headers={
            "Origin": "http://evil.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert "access-control-allow-origin" not in response.headers, (
        f"Foreign origin preflight must NOT include Access-Control-Allow-Origin, "
        f"got headers: {dict(response.headers)}"
    )


# --------------------------------------------------------------------------
# PDF port-clamp functional coverage (D-11 / HARDEN-API-05)
# --------------------------------------------------------------------------

def test_pdf_port_clamp_rejects_privileged_port(monkeypatch):
    """POST /api/export/pdf with QUIRK_SERVE_PORT=80 returns 500 with port-range error body.

    This is the functional pytest coverage for the guard in
    quirk/dashboard/api/routes/pdf.py (D-11 / HARDEN-API-05 from Plan 03).

    We mock sync_playwright to a non-None sentinel so the Playwright-not-installed
    check (which returns 503) does not short-circuit before the port-clamp check.
    """
    monkeypatch.setenv("QUIRK_SERVE_PORT", "80")
    monkeypatch.setenv("QUIRK_API_TOKEN", "test-token")

    # Patch sync_playwright to a non-None sentinel so the 503-Playwright-missing
    # guard does not fire before the port-clamp check at line 54-62 of pdf.py.
    import quirk.dashboard.api.routes.pdf as pdf_module
    monkeypatch.setattr(pdf_module, "sync_playwright", object(), raising=False)

    _, tc = _app_with_db()

    response = tc.post(
        "/api/export/pdf",
        headers={
            "Authorization": "Bearer test-token",
            "X-Quirk-Request": "1",
        },
    )
    assert response.status_code == 500, (
        f"Privileged port should return 500, got {response.status_code}: {response.text}"
    )
    assert response.json() == {
        "detail": "QUIRK_SERVE_PORT is out of allowed range (1024–65535)."
    }, f"Unexpected body: {response.json()}"
