"""POST /api/sensor/push contract tests — Phase 109 CONSOLE-01..05.

Covers:
  (a) test_push_endpoint_exists         — route registered (CONSOLE-01)
  (b) test_push_requires_auth           — 401 without auth (CONSOLE-02)
  (c) test_push_413_body_too_large      — 413 on oversized body (CONSOLE-03)
  (d) test_push_409_duplicate_payload   — 409 on second push of same payload_id (CONSOLE-03)
  (e) test_push_422_replay_window       — 422 + console_utc on stale pushed_at (CONSOLE-03)
  (f) test_push_200_accepted            — 200 + SensorPush row + last_push_at + CryptoEndpoint rows (CONSOLE-03)
  (g) test_audit_row_written            — IntegrationDelivery row on success AND failure (CONSOLE-04)
  (h) test_extra_fields_ignored         — extra field in envelope → 200 (CONSOLE-05)
  (i) test_version_skew_graceful        — mismatched schema_version → not 422/500 (CONSOLE-05)
  (j) test_unknown_sensor_id_4xx        — unregistered sensor_id → 4xx + audited

pytest -k "sensor_push or ingest or valid or unauth or size or replay or skew or audit
          or version_skew or extra_ignore" selects all tests.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import zstandard
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from quirk.dashboard.api.app import create_app
from quirk.dashboard.api.deps import get_db
from quirk.models import Base, IntegrationDelivery, Sensor, SensorPush, CryptoEndpoint

# ---------------------------------------------------------------------------
# Shared DB + TestClient factory
# ---------------------------------------------------------------------------

def _make_test_engine():
    engine = create_engine(
        "sqlite:///file::memory:?cache=shared&uri=true",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    return engine


def _app_with_db():
    """Create a fresh TestClient backed by an in-memory SQLite DB."""
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
    return app, TestClient(app, raise_server_exceptions=False), engine, TestingSession


# ---------------------------------------------------------------------------
# Envelope builder helpers (mirrors quirk/cli/sensor_cmd._build_compressed_payload)
# ---------------------------------------------------------------------------

def _build_envelope(
    sensor_id: str = "test-sensor-01",
    segment: str = "dmz",
    payload_id: str | None = None,
    pushed_at: str | None = None,
    schema_version: str = "1.0.0",
    sensor_version: str = "5.4.0",
    findings: list | None = None,
    extra_field: str | None = None,
) -> dict:
    """Build a minimal valid wire envelope dict."""
    if pushed_at is None:
        pushed_at = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    if payload_id is None:
        payload_id = str(uuid.uuid4())
    env: dict = {
        "payload_id": payload_id,
        "pushed_at": pushed_at,
        "schema_version": schema_version,
        "sensor_version": sensor_version,
        "sensor_id": sensor_id,
        "segment": segment,
        "findings": findings or [],
    }
    if extra_field is not None:
        env["_extra_unknown_field"] = extra_field
    return env


def _compress(envelope: dict) -> bytes:
    """Serialize envelope to JSON and compress with zstd level-3 (canonical body)."""
    raw = json.dumps(envelope, ensure_ascii=False).encode("utf-8")
    return zstandard.ZstdCompressor(level=3).compress(raw)


def _seed_sensor(
    TestingSession,
    sensor_id: str = "test-sensor-01",
    segment: str = "dmz",
) -> None:
    """Write a Sensor row so push tests have a known enrolled sensor_id."""
    db = TestingSession()
    try:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        db.add(Sensor(
            sensor_id=sensor_id,
            segment=segment,
            engagement=None,
            enrolled_at=now,
            last_push_at=None,
            expected_cadence_minutes=1440,
            sensor_version=None,
        ))
        db.commit()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# (a) test_push_endpoint_exists — CONSOLE-01
# ---------------------------------------------------------------------------

def test_push_endpoint_exists(monkeypatch):
    """CONSOLE-01: POST /api/sensor/push route is registered in the app."""
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)
    app, _, _, _ = _app_with_db()
    from fastapi.routing import APIRoute
    route_paths = [r.path for r in app.routes if isinstance(r, APIRoute)]
    assert "/api/sensor/push" in route_paths, (
        f"/api/sensor/push not found in routes: {route_paths}"
    )


# ---------------------------------------------------------------------------
# (b) test_push_requires_auth — CONSOLE-02
# ---------------------------------------------------------------------------

def test_push_requires_auth(monkeypatch):
    """CONSOLE-02: POST /api/sensor/push without auth header returns 401."""
    monkeypatch.setenv("QUIRK_API_TOKEN", "test-token")
    _, client, _, _ = _app_with_db()
    # No Authorization header supplied
    resp = client.post("/api/sensor/push", content=b"data")
    assert resp.status_code == 401, (
        f"Expected 401 when unauthenticated, got {resp.status_code}: {resp.text}"
    )


# ---------------------------------------------------------------------------
# (c) test_push_413_body_too_large — CONSOLE-03
# ---------------------------------------------------------------------------

def test_push_413_body_too_large(monkeypatch):
    """CONSOLE-03: POST /api/sensor/push with Content-Length > 10 MB returns 413."""
    monkeypatch.setenv("QUIRK_API_TOKEN", "test-token")
    _, client, _, _ = _app_with_db()
    # Lie about Content-Length — easier than sending 10+ MB in tests
    oversized_bytes = 11 * 1024 * 1024
    resp = client.post(
        "/api/sensor/push",
        content=b"x",
        headers={
            "Authorization": "Bearer test-token",
            "Content-Length": str(oversized_bytes),
        },
    )
    assert resp.status_code == 413, (
        f"Expected 413 for oversized body, got {resp.status_code}: {resp.text}"
    )


# ---------------------------------------------------------------------------
# (d) test_push_409_duplicate_payload — CONSOLE-03
# ---------------------------------------------------------------------------

def test_push_409_duplicate_payload(monkeypatch):
    """CONSOLE-03: Pushing the same payload_id twice returns 200 then 409."""
    monkeypatch.setenv("QUIRK_API_TOKEN", "test-token")
    _, client, _, TestingSession = _app_with_db()
    _seed_sensor(TestingSession, sensor_id="sensor-dedup-01")

    payload_id = str(uuid.uuid4())
    env = _build_envelope(sensor_id="sensor-dedup-01", payload_id=payload_id)
    body = _compress(env)

    resp1 = client.post(
        "/api/sensor/push",
        content=body,
        headers={"Authorization": "Bearer test-token"},
    )
    assert resp1.status_code == 200, (
        f"First push should be 200, got {resp1.status_code}: {resp1.text}"
    )

    resp2 = client.post(
        "/api/sensor/push",
        content=body,
        headers={"Authorization": "Bearer test-token"},
    )
    assert resp2.status_code == 409, (
        f"Second push with same payload_id should be 409, got {resp2.status_code}: {resp2.text}"
    )


# ---------------------------------------------------------------------------
# (e) test_push_422_replay_window — CONSOLE-03
# ---------------------------------------------------------------------------

def test_push_422_replay_window(monkeypatch):
    """CONSOLE-03: pushed_at > 15 min from now returns 422 with console_utc in body."""
    monkeypatch.setenv("QUIRK_API_TOKEN", "test-token")
    _, client, _, _ = _app_with_db()

    stale_pushed_at = (
        datetime.utcnow() - timedelta(minutes=30)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")
    env = _build_envelope(sensor_id="nonexistent-sensor", pushed_at=stale_pushed_at)
    body = _compress(env)

    resp = client.post(
        "/api/sensor/push",
        content=body,
        headers={"Authorization": "Bearer test-token"},
    )
    assert resp.status_code == 422, (
        f"Expected 422 for replay window violation, got {resp.status_code}: {resp.text}"
    )
    data = resp.json()
    detail = data.get("detail", {})
    # detail should be a dict with console_utc key
    assert "console_utc" in str(detail), (
        f"Expected 'console_utc' in detail, got: {detail}"
    )


# ---------------------------------------------------------------------------
# (f) test_push_200_accepted — CONSOLE-03
# ---------------------------------------------------------------------------

def test_push_200_accepted(monkeypatch):
    """CONSOLE-03: Valid authenticated push returns 200; persists SensorPush,
    updates sensors.last_push_at, and writes CryptoEndpoint rows for findings."""
    monkeypatch.setenv("QUIRK_API_TOKEN", "test-token")
    _, client, engine, TestingSession = _app_with_db()
    _seed_sensor(TestingSession, sensor_id="sensor-ok-01")

    finding = {
        "host": "10.0.0.1",
        "port": 443,
        "protocol": "TLS",
        "scanned_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tls_version": "TLSv1.3",
        "cipher_suite": "TLS_AES_256_GCM_SHA384",
        "cert_subject": "CN=test",
        "cert_issuer": "CN=test-ca",
        "cert_sans": None,
        "cert_sig_alg": "sha256WithRSAEncryption",
        "cert_pubkey_alg": "RSA",
        "cert_pubkey_size": 2048,
        "cert_not_before": None,
        "cert_not_after": None,
    }
    payload_id = str(uuid.uuid4())
    env = _build_envelope(
        sensor_id="sensor-ok-01",
        payload_id=payload_id,
        findings=[finding],
    )
    body = _compress(env)

    resp = client.post(
        "/api/sensor/push",
        content=body,
        headers={"Authorization": "Bearer test-token"},
    )
    assert resp.status_code == 200, (
        f"Expected 200 for valid push, got {resp.status_code}: {resp.text}"
    )
    data = resp.json()
    assert data.get("status") == "accepted", f"Unexpected response body: {data}"

    # Assert SensorPush row exists
    db = TestingSession()
    try:
        push_row = db.query(SensorPush).filter(SensorPush.payload_id == payload_id).first()
        assert push_row is not None, "SensorPush row missing after accepted push"

        # Assert sensors.last_push_at was updated
        sensor_row = db.query(Sensor).filter(Sensor.sensor_id == "sensor-ok-01").first()
        assert sensor_row is not None
        assert sensor_row.last_push_at is not None, (
            "sensors.last_push_at not updated after accepted push"
        )

        # Assert CryptoEndpoint row exists tagged with sensor_id and segment
        ep_row = db.query(CryptoEndpoint).filter(
            CryptoEndpoint.sensor_id == "sensor-ok-01"
        ).first()
        assert ep_row is not None, "CryptoEndpoint row missing after accepted push"
        assert ep_row.segment == "dmz", f"CryptoEndpoint.segment expected 'dmz', got {ep_row.segment}"
    finally:
        db.close()


# ---------------------------------------------------------------------------
# (g) test_audit_row_written — CONSOLE-04
# ---------------------------------------------------------------------------

def test_audit_row_written(monkeypatch):
    """CONSOLE-04: IntegrationDelivery row with destination='sensor_push' is written
    on both a success (status='ok') and a failure (status='failed', e.g. 422)."""
    monkeypatch.setenv("QUIRK_API_TOKEN", "test-token")
    _, client, engine, TestingSession = _app_with_db()
    _seed_sensor(TestingSession, sensor_id="sensor-audit-01")

    # --- Success path → status="ok" ---
    payload_id = str(uuid.uuid4())
    env = _build_envelope(sensor_id="sensor-audit-01", payload_id=payload_id)
    body = _compress(env)

    resp = client.post(
        "/api/sensor/push",
        content=body,
        headers={"Authorization": "Bearer test-token"},
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    db = TestingSession()
    try:
        ok_rows = (
            db.query(IntegrationDelivery)
            .filter(
                IntegrationDelivery.destination == "sensor_push",
                IntegrationDelivery.status == "ok",
            )
            .all()
        )
        assert len(ok_rows) >= 1, (
            f"Expected at least one ok IntegrationDelivery row, found {len(ok_rows)}"
        )
    finally:
        db.close()

    # --- Failure path (422 replay window) → status="failed" ---
    stale_pushed_at = (
        datetime.utcnow() - timedelta(minutes=30)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")
    env_fail = _build_envelope(sensor_id="nonexistent-sensor", pushed_at=stale_pushed_at)
    body_fail = _compress(env_fail)

    resp_fail = client.post(
        "/api/sensor/push",
        content=body_fail,
        headers={"Authorization": "Bearer test-token"},
    )
    assert resp_fail.status_code == 422, (
        f"Expected 422 for failure path, got {resp_fail.status_code}: {resp_fail.text}"
    )

    db = TestingSession()
    try:
        fail_rows = (
            db.query(IntegrationDelivery)
            .filter(
                IntegrationDelivery.destination == "sensor_push",
                IntegrationDelivery.status == "failed",
            )
            .all()
        )
        assert len(fail_rows) >= 1, (
            f"Expected at least one failed IntegrationDelivery row, found {len(fail_rows)}"
        )
    finally:
        db.close()


# ---------------------------------------------------------------------------
# (h) test_extra_fields_ignored — CONSOLE-05 (extra='ignore')
# ---------------------------------------------------------------------------

def test_extra_fields_ignored(monkeypatch):
    """CONSOLE-05: Envelope with an unknown extra field still parses and returns 200."""
    monkeypatch.setenv("QUIRK_API_TOKEN", "test-token")
    _, client, engine, TestingSession = _app_with_db()
    _seed_sensor(TestingSession, sensor_id="sensor-extra-01")

    env = _build_envelope(
        sensor_id="sensor-extra-01",
        extra_field="some-future-field-from-newer-sensor",
    )
    body = _compress(env)

    resp = client.post(
        "/api/sensor/push",
        content=body,
        headers={"Authorization": "Bearer test-token"},
    )
    assert resp.status_code == 200, (
        f"Extra fields should be silently ignored (extra='ignore'), got {resp.status_code}: {resp.text}"
    )


# ---------------------------------------------------------------------------
# (i) test_version_skew_graceful — CONSOLE-05 (schema_version mismatch warn-only)
# ---------------------------------------------------------------------------

def test_version_skew_graceful(monkeypatch):
    """CONSOLE-05: Mismatched schema_version is warn-only — must not return 422 or 500."""
    monkeypatch.setenv("QUIRK_API_TOKEN", "test-token")
    _, client, engine, TestingSession = _app_with_db()
    _seed_sensor(TestingSession, sensor_id="sensor-skew-01")

    env = _build_envelope(
        sensor_id="sensor-skew-01",
        schema_version="99.99.99",   # far-future version skew
        sensor_version="99.0.0",
    )
    body = _compress(env)

    resp = client.post(
        "/api/sensor/push",
        content=body,
        headers={"Authorization": "Bearer test-token"},
    )
    assert resp.status_code not in (422, 500), (
        f"Version skew must not cause 422 or 500; got {resp.status_code}: {resp.text}"
    )


# ---------------------------------------------------------------------------
# (j) test_unknown_sensor_id_4xx — unknown sensor → 4xx + audited
# ---------------------------------------------------------------------------

def test_unknown_sensor_id_4xx(monkeypatch):
    """Push with an unregistered sensor_id returns 4xx and writes a failed audit row."""
    monkeypatch.setenv("QUIRK_API_TOKEN", "test-token")
    _, client, engine, TestingSession = _app_with_db()
    # Do NOT seed a sensor for this test

    env = _build_envelope(sensor_id="no-such-sensor-xyz")
    body = _compress(env)

    resp = client.post(
        "/api/sensor/push",
        content=body,
        headers={"Authorization": "Bearer test-token"},
    )
    assert 400 <= resp.status_code < 500, (
        f"Unknown sensor_id should return 4xx, got {resp.status_code}: {resp.text}"
    )

    db = TestingSession()
    try:
        fail_rows = (
            db.query(IntegrationDelivery)
            .filter(
                IntegrationDelivery.destination == "sensor_push",
                IntegrationDelivery.status == "failed",
            )
            .all()
        )
        assert len(fail_rows) >= 1, (
            f"Expected at least one failed audit row for unknown sensor_id, found {len(fail_rows)}"
        )
    finally:
        db.close()
