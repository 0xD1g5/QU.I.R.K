"""Phase 195 Plan 04 (MAP-02) — GET /api/exposure-map route tests.

Covers:
  - the route is auth-gated like the rest of the dashboard API (T-195-01)
  - an empty DB returns 200 with nodes==[] and edges==[] (D-08 honest absence)
  - a seeded key-reuse cluster produces edges each with a non-empty evidence
    string and a vocabulary-valid edge_type (D-11)
"""
from __future__ import annotations

import datetime

from fastapi.testclient import TestClient

from quirk.dashboard.api.app import create_app
from quirk.db import get_session, init_db
from quirk.models import CryptoEndpoint


def _now():
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)


def _client(monkeypatch, db_path):
    monkeypatch.setenv("QUIRK_DB_PATH", db_path)
    app = create_app()
    return TestClient(app, headers={"X-Quirk-Request": "1"})


def test_empty_edges_response(tmp_path, monkeypatch):
    db_path = str(tmp_path / "empty.db")
    init_db(db_path)

    client = _client(monkeypatch, db_path)
    resp = client.get("/api/exposure-map")

    assert resp.status_code == 200
    data = resp.json()
    assert data["nodes"] == []
    assert data["edges"] == []


def test_seeded_key_reuse_cluster_returns_evidence_bearing_edges(tmp_path, monkeypatch):
    db_path = str(tmp_path / "seeded.db")
    init_db(db_path)
    fingerprint = "a" * 64
    with get_session(db_path) as session:
        session.add_all(
            [
                CryptoEndpoint(
                    host="host-a.example.com",
                    port=443,
                    protocol="TLS",
                    scanned_at=_now(),
                    cert_spki_fingerprint=fingerprint,
                    cert_subject="CN=host-a.example.com",
                    cert_pubkey_alg="RSA",
                    cert_pubkey_size=2048,
                ),
                CryptoEndpoint(
                    host="host-b.example.com",
                    port=443,
                    protocol="TLS",
                    scanned_at=_now(),
                    cert_spki_fingerprint=fingerprint,
                    cert_subject="CN=host-a.example.com",
                    cert_pubkey_alg="RSA",
                    cert_pubkey_size=2048,
                ),
            ]
        )
        session.commit()

    client = _client(monkeypatch, db_path)
    resp = client.get("/api/exposure-map")

    assert resp.status_code == 200
    data = resp.json()
    assert data["edges"], "expected at least one key-reuse edge"
    for edge in data["edges"]:
        assert edge["evidence"].strip()
        assert edge["edge_type"] in ("key_reuse", "hardware_bridge")
    assert data["nodes"], "expected nodes derived from edge endpoints"


def test_empty_derivation_is_honest_absence_not_unavailable(tmp_path, monkeypatch):
    """WR-02: a genuinely-empty but SUCCESSFUL derivation returns the honest
    empty shape (200, nodes==[]/edges==[]) with unavailable_reason==None."""
    db_path = str(tmp_path / "honest_empty.db")
    init_db(db_path)

    client = _client(monkeypatch, db_path)
    resp = client.get("/api/exposure-map")

    assert resp.status_code == 200
    data = resp.json()
    assert data["nodes"] == []
    assert data["edges"] == []
    assert data.get("unavailable_reason") is None


def test_derivation_failure_surfaces_unavailable_reason(tmp_path, monkeypatch):
    """WR-02: a derivation FAILURE must not masquerade as the honest-absence
    empty map — it returns unavailable_reason set (distinguishable on the wire),
    never a bare empty map that reads as 'zero verified exposure'."""
    db_path = str(tmp_path / "boom.db")
    init_db(db_path)

    def _boom(_db):
        raise RuntimeError("simulated derivation failure")

    # Patch at the route's import site so the guarded region catches it.
    monkeypatch.setattr(
        "quirk.dashboard.api.routes.exposure_map.derive_exposure_map", _boom
    )

    client = _client(monkeypatch, db_path)
    resp = client.get("/api/exposure-map")

    assert resp.status_code == 200
    data = resp.json()
    assert data["nodes"] == []
    assert data["edges"] == []
    # The failure MUST be distinguishable from honest absence.
    assert data["unavailable_reason"], "failure must set unavailable_reason"
    assert "computation error" in data["unavailable_reason"]


def test_exposure_map_requires_auth(tmp_path, monkeypatch):
    db_path = str(tmp_path / "auth.db")
    init_db(db_path)
    monkeypatch.setenv("QUIRK_API_TOKEN", "test-token")

    client = _client(monkeypatch, db_path)
    resp = client.get("/api/exposure-map")
    assert resp.status_code == 401

    resp_ok = client.get("/api/exposure-map", headers={"X-API-Key": "test-token"})
    assert resp_ok.status_code == 200
