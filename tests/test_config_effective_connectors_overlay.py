"""GET /api/config/effective?connectors=... — Phase 193 / PARITY-02 / D-16.

Task 2 of 193-05: threads a JSON-encoded connectors delta overlay through
`resolve_effective_config` into the same YAML round-trip a real submission
uses, so the Effective-config panel can live-update as connector toggles
change before submit.

pytest -q tests/test_config_effective_connectors_overlay.py
"""
from __future__ import annotations

import json

from sqlalchemy.orm import sessionmaker

from fastapi.testclient import TestClient

from quirk.dashboard.api.app import create_app
from quirk.dashboard.api.deps import get_db
from tests.conftest import make_isolated_memory_engine


def _app_with_db():
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


def _connectors_field(body: dict, name: str) -> dict:
    section = next(s for s in body["sections"] if s["name"] == "connectors")
    return next(f for f in section["fields"] if f["name"] == name)


def test_no_connectors_param_is_regression_identical(monkeypatch):
    """No `connectors` query param at all -> response identical to
    pre-Phase-193 behavior (regression guard)."""
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)
    monkeypatch.delenv("VAULT_TOKEN", raising=False)
    _, tc = _app_with_db()

    first = tc.get("/api/config/effective", params={"targets": "example.com"})
    second = tc.get("/api/config/effective", params={"targets": "example.com"})
    assert first.status_code == 200
    assert second.status_code == 200
    # output.directory/db_path are a fresh tempfile.TemporaryDirectory per
    # call and expected to differ; every other section (targets, connectors,
    # scan, ...) must be stable across repeated calls with identical
    # selections — the connectors overlay plumbing must not perturb them.
    first_body, second_body = first.json(), second.json()
    assert first_body["profile"] == second_body["profile"]
    assert first_body["vertical"] == second_body["vertical"]
    for section_name in ("targets", "connectors", "scan", "assessment", "intelligence", "security"):
        first_section = next(s for s in first_body["sections"] if s["name"] == section_name)
        second_section = next(s for s in second_body["sections"] if s["name"] == section_name)
        assert first_section == second_section


def test_connectors_overlay_reflects_as_user_provenance(monkeypatch):
    """connectors={"enable_adcs": true} -> enable_adcs shows true with
    provenance 'user'."""
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)
    monkeypatch.delenv("VAULT_TOKEN", raising=False)
    _, tc = _app_with_db()

    response = tc.get(
        "/api/config/effective",
        params={"connectors": json.dumps({"enable_adcs": True})},
    )
    assert response.status_code == 200, response.text
    field = _connectors_field(response.json(), "enable_adcs")
    assert field["value"] is True
    assert field["provenance"] == "user"


def test_connectors_overlay_beats_preset_provenance(monkeypatch):
    """Under a profile whose preset would otherwise flip the flag, the
    operator's overlay value still wins and still reads 'user' (D-16 + D-13
    through the preview path)."""
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)
    monkeypatch.delenv("VAULT_TOKEN", raising=False)
    _, tc = _app_with_db()

    response = tc.get(
        "/api/config/effective",
        params={
            "profile": "deep",
            "connectors": json.dumps({"enable_broker": False}),
        },
    )
    assert response.status_code == 200, response.text
    field = _connectors_field(response.json(), "enable_broker")
    assert field["value"] is False
    assert field["provenance"] == "user"


def test_malformed_json_returns_422(monkeypatch):
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)
    _, tc = _app_with_db()

    response = tc.get("/api/config/effective", params={"connectors": "{not json"})
    assert response.status_code == 422, response.text
    assert "JSON object" in response.json()["detail"]


def test_non_boolean_value_returns_422(monkeypatch):
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)
    _, tc = _app_with_db()

    response = tc.get(
        "/api/config/effective",
        params={"connectors": json.dumps({"enable_adcs": "yes"})},
    )
    assert response.status_code == 422, response.text


def test_unknown_connector_key_returns_422_naming_it(monkeypatch):
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)
    _, tc = _app_with_db()

    response = tc.get(
        "/api/config/effective",
        params={"connectors": json.dumps({"enable_bogus": True})},
    )
    assert response.status_code == 422, response.text
    assert "enable_bogus" in response.json()["detail"]


def test_malformed_advanced_ports_tls_returns_422_not_500(monkeypatch):
    """Phase 194 / WR-01: a malformed advanced.ports_tls must surface as 422
    on the GET preview path, exactly as the submit path (POST /api/jobs)
    already does -- never an unhandled 500. build_advanced_overlays ->
    parse_port_spec raises ValueError, which the preview handler must convert
    to 422 so preview and submit can never disagree on what is valid (D-03/D-16).
    """
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)
    _, tc = _app_with_db()

    response = tc.get(
        "/api/config/effective",
        params={"advanced": json.dumps({"ports_tls": "443,abc"})},
    )
    assert response.status_code == 422, response.text


def test_out_of_range_advanced_ports_tls_returns_422_not_500(monkeypatch):
    """A numerically out-of-range port (>65535) likewise returns 422, not 500."""
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)
    _, tc = _app_with_db()

    response = tc.get(
        "/api/config/effective",
        params={"advanced": json.dumps({"ports_tls": "99999"})},
    )
    assert response.status_code == 422, response.text


def test_credential_redaction_unaffected_by_connectors_overlay(monkeypatch):
    """Credential fields still render REDACTED_SET/REDACTED_UNSET markers,
    never a raw value, when a connectors overlay is supplied."""
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)
    monkeypatch.setenv("VAULT_TOKEN", "s.realsecret")
    _, tc = _app_with_db()

    response = tc.get(
        "/api/config/effective",
        params={"connectors": json.dumps({"enable_adcs": True})},
    )
    assert response.status_code == 200, response.text
    assert "s.realsecret" not in response.text

    body = response.json()
    vault_field = _connectors_field(body, "vault_token")
    assert vault_field["redacted"] is True
    assert vault_field["credential_status"] == "set"
