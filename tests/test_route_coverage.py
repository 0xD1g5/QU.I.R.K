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
    """AUTH-02 gate: every APIRoute except /api/health must have require_auth.

    Introspects app.routes and collects all APIRoute instances that are not
    the health endpoint. Any route missing require_auth in its dependency list
    causes this test to fail, preventing the route from shipping without auth.

    Expected to PASS immediately — all 7 data routers already use router-level
    Depends(require_auth). This is a regression guard, not net-new coverage.
    """
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)
    from fastapi.routing import APIRoute
    from quirk.dashboard.api.middleware.auth import require_auth

    app = create_app()
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
        if require_auth not in dep_callables:
            violations.append(
                f"{sorted(route.methods or set())} {route.path} — missing require_auth"
            )

    assert violations == [], (
        "The following routes are missing require_auth (AUTH-02 violation):\n"
        + "\n".join(violations)
    )
