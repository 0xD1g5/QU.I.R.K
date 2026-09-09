"""GET /api/connectors/availability — Phase 193 / Plan 04 (PARITY-02).

Auth gating, payload shape, install-hint carry-through, and per-request
freshness (D-07) for the availability route added in plan 04. Mirrors
tests/test_config_effective_route.py's TestClient construction and auth
convention — the closest analog, since both routes share the identical
`APIRouter(dependencies=[Depends(require_auth)])` gate.
"""
from __future__ import annotations

import dataclasses

from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

import quirk.dashboard.api.routes.connectors as connectors_route
from quirk.config import ConnectorsCfg
from quirk.dashboard.api.app import create_app
from quirk.dashboard.api.connector_availability import ConnectorAvailability
from quirk.dashboard.api.deps import get_db
from tests.conftest import make_isolated_memory_engine

_UI_SPEC_CATEGORIES = {
    "Identity",
    "Cloud",
    "Database",
    "Email & Broker",
    "OT/ICS",
    "Source & API",
}


def _app_with_db():
    """Fresh TestClient backed by an in-memory DB, no auth by default.

    Mirrors tests/test_config_effective_route.py's helper.
    """
    engine = make_isolated_memory_engine()
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


def _enable_flag_names() -> set[str]:
    """Derived at run time from ConnectorsCfg, never a hand-written list."""
    return {
        f.name for f in dataclasses.fields(ConnectorsCfg) if f.name.startswith("enable_")
    }


def test_requires_auth(monkeypatch):
    monkeypatch.setenv("QUIRK_API_TOKEN", "test-token")
    _, tc = _app_with_db()

    response = tc.get("/api/connectors/availability")
    assert response.status_code in (401, 403), response.text

    response = tc.get(
        "/api/connectors/availability",
        headers={"Authorization": "Bearer test-token"},
    )
    assert response.status_code == 200, response.text


def test_returns_every_connector(monkeypatch):
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)
    _, tc = _app_with_db()

    response = tc.get("/api/connectors/availability")
    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body["connectors"]) == len(_enable_flag_names())


def test_entry_shape(monkeypatch):
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)
    _, tc = _app_with_db()

    response = tc.get("/api/connectors/availability")
    assert response.status_code == 200, response.text
    body = response.json()

    for entry in body["connectors"]:
        assert entry["flag"], entry
        assert entry["label"], entry
        assert entry["category"] in _UI_SPEC_CATEGORIES, entry
        if entry["available"] is False:
            assert entry["reason"], entry


def test_unavailable_entries_carry_install_hint(monkeypatch):
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)

    def _fake_probe_all_connectors():
        return {
            "enable_db": ConnectorAvailability(
                flag="enable_db",
                available=False,
                reason="optional extra 'db' is not installed",
                install_hint="pip install quirk[db]",
                category="Database",
                label="Database TLS (PostgreSQL/MySQL)",
            ),
        }

    monkeypatch.setattr(
        connectors_route, "probe_all_connectors", _fake_probe_all_connectors,
    )
    _, tc = _app_with_db()

    response = tc.get("/api/connectors/availability")
    assert response.status_code == 200, response.text
    assert "pip install quirk[db]" in response.text


def test_unavailable_count_matches(monkeypatch):
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)
    _, tc = _app_with_db()

    response = tc.get("/api/connectors/availability")
    assert response.status_code == 200, response.text
    body = response.json()

    expected = sum(1 for entry in body["connectors"] if entry["available"] is False)
    assert body["unavailable_count"] == expected


def test_probe_runs_on_every_request(monkeypatch):
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)

    call_count = {"n": 0}
    real_probe_all_connectors = connectors_route.probe_all_connectors

    def _counting_probe_all_connectors():
        call_count["n"] += 1
        return real_probe_all_connectors()

    monkeypatch.setattr(
        connectors_route, "probe_all_connectors", _counting_probe_all_connectors,
    )
    _, tc = _app_with_db()

    tc.get("/api/connectors/availability")
    tc.get("/api/connectors/availability")

    assert call_count["n"] == 2


def test_probe_failure_returns_500_without_leaking_detail(monkeypatch):
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)

    def _raising_probe_all_connectors():
        raise RuntimeError("/Users/secret/path/site-packages boom")

    monkeypatch.setattr(
        connectors_route, "probe_all_connectors", _raising_probe_all_connectors,
    )
    _, tc = _app_with_db()

    response = tc.get("/api/connectors/availability")
    assert response.status_code == 500, response.text
    assert "/Users/secret/path" not in response.text
