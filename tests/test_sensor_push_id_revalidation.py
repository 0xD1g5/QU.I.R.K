"""RED test — AUDIT-08: sensor push endpoint must re-validate sensor_id shape.

Contract: the token-resolved sensor_id (request.state.sensor_id, set by
require_sensor_auth) must be re-validated as a UUID4-shaped string BEFORE
any DB write.  A malformed sensor_id (e.g. "../etc/evil", "abc", path
traversal strings) must be rejected with HTTP 400 and produce no
SensorPush/CryptoEndpoint rows.

Current state: sensor.py trusts the token-resolved sensor_id without
shape-checking it against the UUID regex.  These tests MUST FAIL because:
  - The route does not re-validate sensor_id shape before DB operations.
  - A malformed sensor_id would either hit a DB FK error (unrelated 500)
    or proceed to the ingest path and write rows with a garbage sensor_id.

Wave 2 (plan 131-02) will add UUID shape re-validation immediately after
the token-resolved sensor_id is read from request.state.

Mirrors harness from tests/test_sensor_auth_per_sensor.py.

pytest -q tests/test_sensor_push_id_revalidation.py
"""
from __future__ import annotations

import hashlib
import json
import secrets
import uuid
from datetime import datetime, timezone

import pytest
import zstandard
from fastapi import Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from quirk.dashboard.api.app import create_app
from quirk.dashboard.api.deps import get_db
from quirk.dashboard.api.middleware.sensor_auth import require_sensor_auth
from quirk.models import Base, Sensor, SensorPush, SensorToken


# ---------------------------------------------------------------------------
# Shared DB + TestClient factory (mirrors test_sensor_auth_per_sensor.py)
# ---------------------------------------------------------------------------

def _make_test_engine():
    engine = create_engine(
        "sqlite:///file::memory:?cache=shared&uri=true",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    return engine


def _app_with_db():
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
# Envelope builder + compress helpers (mirrors test_sensor_ingest.py)
# ---------------------------------------------------------------------------

def _build_envelope(
    sensor_id: str,
    payload_id: str | None = None,
    pushed_at: str | None = None,
) -> dict:
    if pushed_at is None:
        pushed_at = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    if payload_id is None:
        payload_id = str(uuid.uuid4())
    return {
        "payload_id": payload_id,
        "pushed_at": pushed_at,
        "schema_version": "1.0.0",
        "sensor_version": "5.8.0",
        "sensor_id": sensor_id,
        "segment": "dmz",
        "findings": [],
    }


def _compress(envelope: dict) -> bytes:
    raw = json.dumps(envelope, ensure_ascii=False).encode("utf-8")
    return zstandard.ZstdCompressor(level=3).compress(raw)


# ---------------------------------------------------------------------------
# Seed helpers (mirrors test_sensor_auth_per_sensor.py)
# ---------------------------------------------------------------------------

def _seed_sensor(TestingSession, sensor_id: str) -> None:
    db = TestingSession()
    try:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        db.add(Sensor(
            sensor_id=sensor_id,
            segment="dmz",
            engagement=None,
            enrolled_at=now,
            last_push_at=None,
            expected_cadence_minutes=1440,
            sensor_version=None,
        ))
        db.commit()
    finally:
        db.close()


def _seed_token(TestingSession, sensor_id: str) -> str:
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    db = TestingSession()
    try:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        db.add(SensorToken(
            sensor_id=sensor_id,
            token_hash=token_hash,
            created_at=now,
            revoked_at=None,
        ))
        db.commit()
    finally:
        db.close()
    return raw_token


# ---------------------------------------------------------------------------
# Sensor auth override: inject a MALFORMED sensor_id into request.state
# This simulates the case where an auth token somehow resolves to a
# malformed sensor_id (e.g., legacy data or a pathological edge case).
# ---------------------------------------------------------------------------

def _make_malformed_sensor_id_override(malformed_id: str):
    """Return a dependency override that injects malformed sensor_id into request.state."""
    async def _override(request: Request):
        request.state.sensor_id = malformed_id
    return _override


# ---------------------------------------------------------------------------
# Test 1 (RED): path-traversal sensor_id rejected with 400 before any DB write
# ---------------------------------------------------------------------------

def test_malformed_sensor_id_path_traversal_rejected(monkeypatch):
    """AUDIT-08 RED: a path-traversal sensor_id must be rejected with 400.

    The token-resolved sensor_id "../etc/evil" is not a valid UUID.
    The push route must check the UUID shape and return 400 BEFORE any
    DB write (no SensorPush row created).

    EXPECTED FAILURE: the current route does not re-validate sensor_id shape;
    it will proceed to the sensor lookup (finding no row → 404, or if a sensor
    with that id existed, would write a row with a garbage sensor_id).
    """
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)

    malformed_id = "../etc/evil"
    app, client, engine, TestingSession = _app_with_db()

    # Override the sensor auth to inject our malformed sensor_id
    app.dependency_overrides[require_sensor_auth] = _make_malformed_sensor_id_override(malformed_id)

    env = _build_envelope(sensor_id=malformed_id)
    body = _compress(env)

    resp = client.post(
        "/api/sensor/push",
        content=body,
        headers={"Authorization": "Bearer fake-token-not-checked-by-override"},
    )

    # AUDIT-08 CONTRACT: malformed sensor_id must be rejected with 400
    assert resp.status_code == 400, (
        f"AUDIT-08 RED: expected 400 for malformed sensor_id {malformed_id!r}, "
        f"got {resp.status_code}: {resp.text}. "
        "Wave 2 (131-02) will add UUID shape validation before any DB access."
    )

    # No SensorPush row must have been created
    db = TestingSession()
    try:
        push_count = db.query(SensorPush).count()
        assert push_count == 0, (
            f"AUDIT-08 RED: {push_count} SensorPush row(s) found; malformed sensor_id "
            "must not result in any DB write."
        )
    finally:
        db.close()


def test_malformed_sensor_id_short_string_rejected(monkeypatch):
    """AUDIT-08 RED: a non-UUID sensor_id like "abc" must be rejected with 400.

    "abc" is clearly not a UUID4 and must fail shape validation.

    EXPECTED FAILURE: the current route trusts request.state.sensor_id.
    """
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)

    malformed_id = "abc"
    app, client, engine, TestingSession = _app_with_db()

    app.dependency_overrides[require_sensor_auth] = _make_malformed_sensor_id_override(malformed_id)

    env = _build_envelope(sensor_id=malformed_id)
    body = _compress(env)

    resp = client.post(
        "/api/sensor/push",
        content=body,
        headers={"Authorization": "Bearer fake-token"},
    )

    assert resp.status_code == 400, (
        f"AUDIT-08 RED: expected 400 for malformed sensor_id {malformed_id!r}, "
        f"got {resp.status_code}: {resp.text}."
    )

    db = TestingSession()
    try:
        push_count = db.query(SensorPush).count()
        assert push_count == 0, (
            f"AUDIT-08 RED: {push_count} SensorPush row(s) found after malformed id push."
        )
    finally:
        db.close()


def test_valid_uuid_sensor_id_not_rejected(monkeypatch):
    """Sanity check: a well-formed UUID sensor_id must NOT be rejected by the shape gate.

    This test verifies the gate is surgical (only blocks malformed ids).
    A valid UUID that is enrolled must proceed normally (200 accepted).

    NOTE: this test may PASS today (no shape validation = no false rejection).
    It is included to prevent regressions when Wave 2 adds validation.
    """
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)

    valid_id = str(uuid.uuid4())
    app, client, engine, TestingSession = _app_with_db()

    # Seed the sensor so the route can find it
    _seed_sensor(TestingSession, sensor_id=valid_id)

    # Override auth to inject the valid sensor_id
    app.dependency_overrides[require_sensor_auth] = _make_malformed_sensor_id_override(valid_id)

    env = _build_envelope(sensor_id=valid_id)
    body = _compress(env)

    resp = client.post(
        "/api/sensor/push",
        content=body,
        headers={"Authorization": "Bearer fake-token"},
    )

    # A valid UUID sensor_id must not be blocked by the shape gate
    assert resp.status_code not in (400,), (
        f"Valid UUID sensor_id {valid_id!r} must not be blocked by shape validation, "
        f"got {resp.status_code}: {resp.text}"
    )
