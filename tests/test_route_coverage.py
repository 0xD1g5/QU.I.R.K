"""Phase 102 AUTH-02 — route-coverage CI gate (all data-returning routes).

Ensures every APIRoute except /api/health has require_auth in its dependencies.
This gate runs on every CI build to prevent new unprotected routes from shipping.

Mirrors the D-06 mutating-routes gate in test_api_auth.py but drops the
mutating-methods filter so GET routes are also covered.
"""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from quirk.dashboard.api.app import create_app


def test_all_data_routes_have_auth_dependency(monkeypatch):
    """AUTH-02 gate: every APIRoute except /api/health must have an auth dependency.

    Introspects app.routes and collects all APIRoute instances that are not
    the health endpoint. Any route missing an auth dependency in its dependency
    list causes this test to fail, preventing the route from shipping without auth.

    Phase 113 D-01/D-02 split: POST /api/sensor/push intentionally uses
    require_sensor_auth (per-sensor token) rather than require_auth (operator token).
    Both are valid auth dependencies for this gate — the invariant is that EVERY
    route has SOME authentication, not that they all share the same auth mechanism.
    """
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)
    from fastapi.routing import APIRoute
    from quirk.dashboard.api.middleware.auth import require_auth
    from quirk.dashboard.api.middleware.sensor_auth import require_sensor_auth

    app = create_app()
    # Accepted auth dependencies: operator auth OR per-sensor auth (D-01/D-02 split)
    auth_deps = {require_auth, require_sensor_auth}
    violations: list[str] = []

    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        # Only gate API data routes — static files and catch-all SPA route are exempt
        if not route.path.startswith("/api/"):
            continue
        # Health endpoint is explicitly exempt from auth (D-05)
        if route.path in {"/api/health", "/api/health/"}:
            continue
        dep_callables = {dep.dependency for dep in route.dependencies}
        if not (dep_callables & auth_deps):
            violations.append(
                f"{sorted(route.methods or set())} {route.path} — missing require_auth"
            )

    assert violations == [], (
        "The following routes are missing require_auth (AUTH-02 violation):\n"
        + "\n".join(violations)
    )
