"""DASH-07 regression guard: the empty-database landing-route contract.

Phase 174, Plan 02 / D-02 (locked decision): "zero console errors" is read as "no
UNHANDLED application error" — which is already true on `main` — not as "zero
browser network-panel entries". The empty-database probe re-executed for this
phase (`.planning/phases/174-dashboard-api-correctness/174-EMPTY-DB-EVIDENCE.md`)
confirmed that `GET /api/scan/latest` is the ONLY non-2xx response the SPA's
landing route triggers against a genuinely empty database, and that it returns
the documented, error-coded `QRK-DASHBOARD-006` body -- not a crash, not a
missing route, not a missing asset.

This test locks that contract as a regression guard:

Falsifiability -- this test goes RED if, and only if, someone:
  1. Changes `GET /api/scan/latest`'s empty-database response from 404 to 200
     (the exact backend contract change D-02 explicitly rejected), OR
  2. Removes or renames the `QRK-DASHBOARD-006` error code / its message body, OR
  3. Makes any of `GET /api/scans`, `GET /api/config`, or `GET /api/health` fail
     (non-2xx) against an empty database, breaking the "empty state is served,
     not crashed" guarantee the frontend's empty-state rendering depends on.

If none of the above changed, this test has nothing to catch and would not be a
real test -- which is why it pins BOTH the one intentional 404 and the three
routes that must stay 200, rather than asserting either half alone.

What this test deliberately does NOT assert (and cannot):
  This test does NOT and CANNOT assert that a browser logs zero DevTools
  console/network-panel entries. Browser DevTools logs a
  "Failed to load resource: the server responded with a status of 404" line
  for ANY non-2xx fetch()/XHR response at the network layer, independent of
  whether application JavaScript catches and handles it gracefully (it does,
  per `src/dashboard/src/hooks/useScanData.ts:36-59`, read-only reference, not
  modified by this plan). That network-panel behaviour lives beneath
  `fetch()` in the browser itself; pytest has no access to it, and
  jsdom/vitest fetch mocks do not reproduce it either. That half of DASH-07 is
  evidence-based only -- recorded verbatim in
  `.planning/phases/174-dashboard-api-correctness/174-EMPTY-DB-EVIDENCE.md` --
  and is not, and must not be, faked as a pytest assertion here.
"""
from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from quirk.dashboard.api.app import create_app
from quirk.dashboard.api.deps import get_db
from quirk.models import Base


def _make_client_and_session():
    """In-memory, zero-row SQLite harness. Seeding nothing gives a genuinely
    empty database -- copied from tests/test_dashboard_scan_history.py's
    established pattern.
    """
    db_name = f"test_empty_state_{uuid.uuid4().hex}"
    engine = create_engine(
        f"sqlite:///file:{db_name}?mode=memory&cache=shared&uri=true",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def _override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = _override_get_db
    return TestClient(app), TestingSession


def test_scan_latest_returns_404_with_documented_error_code_on_empty_db():
    """GET /api/scan/latest on a zero-row database returns 404 with the
    documented QRK-DASHBOARD-006 error code in its detail body.

    This is the exact, deliberate, D-02-locked contract: a real, intentional,
    already-coded 404 -- not a bug, and not to be silenced by a backend
    contract change.
    """
    client, _Session = _make_client_and_session()

    resp = client.get("/api/scan/latest")

    assert resp.status_code == 404, (
        f"Expected 404 for GET /api/scan/latest against an empty database; "
        f"got {resp.status_code}. This is the D-02-locked contract -- do not "
        f"change this to 200 to silence the DevTools network-panel line."
    )
    detail = resp.json().get("detail", "")
    assert "DASHBOARD-006" in detail, (
        f"Expected the documented QRK-DASHBOARD-006 error code in the 404 "
        f"body; got: {detail!r}"
    )


def test_landing_route_endpoints_stay_200_on_empty_db():
    """GET /api/scans, /api/config, /api/health each return 200 against the
    same zero-row database -- the empty state is served (correct empty-state
    payloads), not crashed.
    """
    client, _Session = _make_client_and_session()

    scans_resp = client.get("/api/scans")
    assert scans_resp.status_code == 200, (
        f"Expected 200 for GET /api/scans on an empty database (empty list "
        f"response), got {scans_resp.status_code}"
    )
    assert scans_resp.json() == [], (
        f"Expected an empty list for GET /api/scans on a zero-row database, "
        f"got {scans_resp.json()!r}"
    )

    config_resp = client.get("/api/config")
    assert config_resp.status_code == 200, (
        f"Expected 200 for GET /api/config regardless of scan data presence, "
        f"got {config_resp.status_code}"
    )

    health_resp = client.get("/api/health")
    assert health_resp.status_code == 200, (
        f"Expected 200 for GET /api/health regardless of scan data presence, "
        f"got {health_resp.status_code}"
    )
