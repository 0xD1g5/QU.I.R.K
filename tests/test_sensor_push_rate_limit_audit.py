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


def test_rate_limited_audit_rows_coalesce_per_source_and_window(monkeypatch):
    """Repeated refusals from one source write one row per window, and the
    next row carries the number of refusals it stands in for."""
    import quirk.dashboard.api.middleware.rate_limit as rl

    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)
    clock = [1000.0]
    monkeypatch.setattr(rl.time, "monotonic", lambda: clock[0])
    client, Session = _app()
    _exhaust(client, "/api/sensor/push")
    for _ in range(25):
        assert client.post("/api/sensor/push", content=b"x").status_code == 429
    limited = [r for r in _rows(Session) if r.status == "rate_limited"]
    assert len(limited) == 1
    assert limited[0].error_summary == "rate_limited"

    # Next window: the source is still flooding, so the bucket refills and
    # refusals resume; exactly one more row, counting the 24 coalesced ones.
    clock[0] += rl._WINDOW_SECONDS + 1
    _exhaust(client, "/api/sensor/push")
    for _ in range(5):
        assert client.post("/api/sensor/push", content=b"x").status_code == 429
    limited = [r for r in _rows(Session) if r.status == "rate_limited"]
    assert len(limited) == 2
    assert "24 further" in limited[1].error_summary
    assert limited[1].client_ip == "testclient"


def test_rate_limit_audit_state_is_bounded(monkeypatch):
    import quirk.dashboard.api.middleware.rate_limit as rl

    mw = rl.RateLimitMiddleware(app=None)
    for i in range(rl._MAX_AUDIT_SOURCES + 50):
        mw._note_refusal(f"198.51.100.{i}", float(i))
    assert len(mw._audited) <= rl._MAX_AUDIT_SOURCES
