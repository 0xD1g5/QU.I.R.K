"""Sensor push audit rows: source address, sensor id, and rate-limited pushes (225.1 D-12)."""
from __future__ import annotations

import logging

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from quirk.dashboard.api.app import create_app
from quirk.dashboard.api.deps import get_db
from quirk.models import IntegrationDelivery
from tests.conftest import make_isolated_memory_engine
from tests.test_sensor_auth_per_sensor import (
    _build_envelope,
    _compress,
    _seed_sensor,
    _seed_token,
)

_SENSOR = "c0000001-0000-4000-8000-000000000001"


def _app(commit_fails: bool = False):
    engine = make_isolated_memory_engine()
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = Session()
        if commit_fails:
            def boom():
                raise RuntimeError("commit boom")
            db.commit = boom  # type: ignore[method-assign]
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app, raise_server_exceptions=False), Session


def _rows(Session):
    db = Session()
    try:
        return db.query(IntegrationDelivery).order_by(IntegrationDelivery.id).all()
    finally:
        db.close()


def test_missing_token_row_records_client_ip_only(monkeypatch):
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)
    client, Session = _app()
    resp = client.post("/api/sensor/push", content=_compress(_build_envelope()))
    assert resp.status_code == 401
    rows = _rows(Session)
    assert len(rows) == 1
    assert rows[0].error_summary == "missing_sensor_token"
    assert rows[0].client_ip == "testclient"
    assert rows[0].sensor_id is None


def test_post_auth_rejection_and_ok_rows_record_sensor_id(monkeypatch):
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)
    client, Session = _app()
    _seed_sensor(Session, sensor_id=_SENSOR)
    tok = _seed_token(Session, sensor_id=_SENSOR)
    hdr = {"Authorization": f"Bearer {tok}"}

    stale = _build_envelope(sensor_id=_SENSOR, pushed_at="2020-01-01T00:00:00Z")
    assert client.post("/api/sensor/push", content=_compress(stale), headers=hdr).status_code == 422
    ok = _build_envelope(sensor_id=_SENSOR)
    assert client.post("/api/sensor/push", content=_compress(ok), headers=hdr).status_code == 200

    rows = _rows(Session)
    assert [r.status for r in rows] == ["failed", "ok"]
    for r in rows:
        assert r.client_ip == "testclient"
        assert r.sensor_id == _SENSOR


def _exhaust(client, path, n=60):
    for _ in range(n):
        client.post(path, content=b"x")


def test_rate_limited_push_writes_audit_row(monkeypatch):
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)
    client, Session = _app()
    _exhaust(client, "/api/sensor/push")
    before = len([r for r in _rows(Session) if r.status == "rate_limited"])
    assert before == 0
    resp = client.post("/api/sensor/push", content=b"x")
    assert resp.status_code == 429
    limited = [r for r in _rows(Session) if r.status == "rate_limited"]
    assert len(limited) == 1
    assert limited[0].destination == "sensor_push"
    assert limited[0].client_ip == "testclient"
    assert limited[0].sensor_id is None


def test_rate_limit_on_other_route_writes_no_audit_row(monkeypatch):
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)
    client, Session = _app()
    _exhaust(client, "/api/jobs")
    resp = client.post("/api/jobs", content=b"x")
    assert resp.status_code == 429
    assert [r for r in _rows(Session) if r.status == "rate_limited"] == []


def test_rate_limit_audit_failure_still_429(monkeypatch, caplog):
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)
    client, _ = _app(commit_fails=True)
    _exhaust(client, "/api/sensor/push")
    with caplog.at_level(logging.WARNING):
        resp = client.post("/api/sensor/push", content=b"x")
    assert resp.status_code == 429
    assert "Rate-limit audit row failed" in caplog.text
