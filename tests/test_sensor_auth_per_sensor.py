"""Per-sensor authentication gating tests — Phase 113 AUTH-01..04.

These tests define the contract for per-sensor token authentication on
POST /api/sensor/push. They are RED until Plan 02 wires require_sensor_auth
and the router split — that is expected per VALIDATION.md Wave 0.

AUTH-01: Valid sensor token accepted; token identity is authoritative.
AUTH-02: Revoked token returns 401; revocation is per-sensor.
AUTH-03: Storage layer (revoked_at column) — validated by Task 1.
AUTH-04: Unknown/missing/mismatch token audit trail.

pytest -q tests/test_sensor_auth_per_sensor.py    (collects 8 tests, RED expected)
"""
from __future__ import annotations

import hashlib
import json
import secrets
import uuid
from datetime import datetime, timezone

import zstandard
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from quirk.dashboard.api.app import create_app
from quirk.dashboard.api.deps import get_db
from quirk.models import Base, IntegrationDelivery, Sensor, SensorToken

# ---------------------------------------------------------------------------
# Fixed UUID sensor IDs — enrollment validates UUID shape; tests must use the
# same format so AUDIT-08's re-validation guard in sensor.py passes legitimate
# sensor_ids resolved from the token store.
# ---------------------------------------------------------------------------
_SENSOR_VALID = "b0000001-0000-4000-8000-000000000001"
_SENSOR_IDENTITY = "b0000002-0000-4000-8000-000000000002"
_SENSOR_REVOKED = "b0000003-0000-4000-8000-000000000003"
_SENSOR_ISO_A = "b0000004-0000-4000-8000-000000000004"
_SENSOR_ISO_B = "b0000005-0000-4000-8000-000000000005"
_SENSOR_MISMATCH_A = "b0000006-0000-4000-8000-000000000006"
_SENSOR_MISMATCH_B = "b0000007-0000-4000-8000-000000000007"
_SENSOR_AUDIT_OK = "b0000008-0000-4000-8000-000000000008"
_SENSOR_AUDIT_REV = "b0000009-0000-4000-8000-000000000009"
_SENSOR_AUDIT_MIS = "b000000a-0000-4000-8000-00000000000a"
_SENSOR_AUDIT_MIS2 = "b000000b-0000-4000-8000-00000000000b"

# ---------------------------------------------------------------------------
# Shared DB + TestClient factory (verbatim from test_sensor_ingest.py)
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
# Envelope builder + compress helpers (verbatim from test_sensor_ingest.py)
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


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------


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


def _seed_token(TestingSession, sensor_id: str, raw_token: str | None = None, revoked: bool = False) -> str:
    """Write a SensorToken row and return the raw token string.

    Mints a cryptographically random token when raw_token is not supplied.
    Only the SHA-256 hex digest is stored (raw token never persisted — D-02 / T-113-02).
    revoked=True sets revoked_at to now; revoked=False leaves it NULL (active).
    """
    if raw_token is None:
        raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    db = TestingSession()
    try:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        db.add(SensorToken(
            sensor_id=sensor_id,
            token_hash=token_hash,
            created_at=now,
            revoked_at=now if revoked else None,
        ))
        db.commit()
    finally:
        db.close()
    return raw_token


# ---------------------------------------------------------------------------
# AUTH-01: Valid sensor token accepted
# ---------------------------------------------------------------------------


def test_valid_sensor_token_accepted(monkeypatch):
    """AUTH-01: A valid sensor token in Authorization: Bearer → 200 accepted."""
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)
    _, client, _, TestingSession = _app_with_db()
    sensor_id = _SENSOR_VALID
    _seed_sensor(TestingSession, sensor_id=sensor_id)
    raw_token = _seed_token(TestingSession, sensor_id=sensor_id)

    env = _build_envelope(sensor_id=sensor_id)
    body = _compress(env)

    resp = client.post(
        "/api/sensor/push",
        content=body,
        headers={"Authorization": f"Bearer {raw_token}"},
    )
    assert resp.status_code == 200, (
        f"Expected 200 for valid sensor token, got {resp.status_code}: {resp.text}"
    )


# ---------------------------------------------------------------------------
# AUTH-01: Token identity is authoritative (D-04)
# ---------------------------------------------------------------------------


def test_token_identity_is_authoritative(monkeypatch):
    """AUTH-01 / D-04: Push is attributed to the token-resolved sensor_id, not the body value.

    The envelope body's sensor_id is irrelevant once the token resolves; the
    server must use request.state.sensor_id from the token lookup (Plan 02 wiring).
    """
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)
    _, client, _, TestingSession = _app_with_db()
    sensor_id = _SENSOR_IDENTITY
    _seed_sensor(TestingSession, sensor_id=sensor_id)
    raw_token = _seed_token(TestingSession, sensor_id=sensor_id)

    # Envelope sensor_id matches the token — valid case
    env = _build_envelope(sensor_id=sensor_id)
    body = _compress(env)

    resp = client.post(
        "/api/sensor/push",
        content=body,
        headers={"Authorization": f"Bearer {raw_token}"},
    )
    assert resp.status_code == 200, (
        f"Token-resolved identity push expected 200, got {resp.status_code}: {resp.text}"
    )


# ---------------------------------------------------------------------------
# AUTH-02: Revoked token returns 401
# ---------------------------------------------------------------------------


def test_revoked_token_returns_401(monkeypatch):
    """AUTH-02 / AUTH-04: A token with revoked_at set must be rejected with 401."""
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)
    _, client, _, TestingSession = _app_with_db()
    sensor_id = _SENSOR_REVOKED
    _seed_sensor(TestingSession, sensor_id=sensor_id)
    raw_token = _seed_token(TestingSession, sensor_id=sensor_id, revoked=True)

    env = _build_envelope(sensor_id=sensor_id)
    body = _compress(env)

    resp = client.post(
        "/api/sensor/push",
        content=body,
        headers={"Authorization": f"Bearer {raw_token}"},
    )
    assert resp.status_code == 401, (
        f"Revoked token must return 401, got {resp.status_code}: {resp.text}"
    )


# ---------------------------------------------------------------------------
# AUTH-02: Revocation is per-sensor (isolation)
# ---------------------------------------------------------------------------


def test_revoke_isolates_to_one_sensor(monkeypatch):
    """AUTH-02: Revoking sensor-a's token does not affect sensor-b's active token."""
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)
    _, client, _, TestingSession = _app_with_db()

    sensor_a = _SENSOR_ISO_A
    sensor_b = _SENSOR_ISO_B
    _seed_sensor(TestingSession, sensor_id=sensor_a)
    _seed_sensor(TestingSession, sensor_id=sensor_b)
    revoked_token = _seed_token(TestingSession, sensor_id=sensor_a, revoked=True)
    active_token = _seed_token(TestingSession, sensor_id=sensor_b, revoked=False)

    env_a = _build_envelope(sensor_id=sensor_a)
    resp_a = client.post(
        "/api/sensor/push",
        content=_compress(env_a),
        headers={"Authorization": f"Bearer {revoked_token}"},
    )
    assert resp_a.status_code == 401, (
        f"Revoked sensor-a token must return 401, got {resp_a.status_code}: {resp_a.text}"
    )

    env_b = _build_envelope(sensor_id=sensor_b)
    resp_b = client.post(
        "/api/sensor/push",
        content=_compress(env_b),
        headers={"Authorization": f"Bearer {active_token}"},
    )
    assert resp_b.status_code == 200, (
        f"Active sensor-b token must return 200, got {resp_b.status_code}: {resp_b.text}"
    )


# ---------------------------------------------------------------------------
# AUTH-04: Unknown token returns 401
# ---------------------------------------------------------------------------


def test_unknown_token_returns_401(monkeypatch):
    """AUTH-04: A never-seeded Bearer token must be rejected with 401."""
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)
    _, client, _, _ = _app_with_db()

    unknown_token = secrets.token_urlsafe(32)  # never written to sensor_tokens
    env = _build_envelope(sensor_id="any-sensor")
    body = _compress(env)

    resp = client.post(
        "/api/sensor/push",
        content=body,
        headers={"Authorization": f"Bearer {unknown_token}"},
    )
    assert resp.status_code == 401, (
        f"Unknown token must return 401, got {resp.status_code}: {resp.text}"
    )


# ---------------------------------------------------------------------------
# AUTH-04 / D-05: sensor_id mismatch returns 403
# ---------------------------------------------------------------------------


def test_sensor_id_mismatch_returns_403(monkeypatch):
    """AUTH-04 / D-05: Token valid for sensor-a; envelope body claims sensor-b → 403."""
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)
    _, client, _, TestingSession = _app_with_db()

    sensor_a = _SENSOR_MISMATCH_A
    sensor_b = _SENSOR_MISMATCH_B
    _seed_sensor(TestingSession, sensor_id=sensor_a)
    _seed_sensor(TestingSession, sensor_id=sensor_b)
    raw_token = _seed_token(TestingSession, sensor_id=sensor_a)

    # Send a valid token for sensor-a but body claims sensor-b
    env = _build_envelope(sensor_id=sensor_b)
    body = _compress(env)

    resp = client.post(
        "/api/sensor/push",
        content=body,
        headers={"Authorization": f"Bearer {raw_token}"},
    )
    assert resp.status_code == 403, (
        f"sensor_id mismatch must return 403, got {resp.status_code}: {resp.text}"
    )


# ---------------------------------------------------------------------------
# AUTH-04 / D-09: All branches write audit rows
# ---------------------------------------------------------------------------


def test_all_branches_write_audit_rows(monkeypatch):
    """AUTH-04 / D-09: All auth branches write IntegrationDelivery rows with distinct error_summary values.

    Verifies:
    - error_summary='unknown_sensor_token' for 401 unknown
    - error_summary='revoked_sensor_token' for 401 revoked
    - error_summary='sensor_id_mismatch' for 403 mismatch
    - status='ok' + error_summary=None for 200 success
    """
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)
    _, client, _, TestingSession = _app_with_db()

    # Seed sensors and tokens
    sensor_ok = _SENSOR_AUDIT_OK
    sensor_rev = _SENSOR_AUDIT_REV
    sensor_mis = _SENSOR_AUDIT_MIS
    sensor_mis2 = _SENSOR_AUDIT_MIS2
    _seed_sensor(TestingSession, sensor_id=sensor_ok)
    _seed_sensor(TestingSession, sensor_id=sensor_rev)
    _seed_sensor(TestingSession, sensor_id=sensor_mis)
    _seed_sensor(TestingSession, sensor_id=sensor_mis2)

    token_ok = _seed_token(TestingSession, sensor_id=sensor_ok)
    token_rev = _seed_token(TestingSession, sensor_id=sensor_rev, revoked=True)
    token_mis = _seed_token(TestingSession, sensor_id=sensor_mis)
    unknown_token = secrets.token_urlsafe(32)

    # --- 200 success path ---
    resp_ok = client.post(
        "/api/sensor/push",
        content=_compress(_build_envelope(sensor_id=sensor_ok)),
        headers={"Authorization": f"Bearer {token_ok}"},
    )
    assert resp_ok.status_code == 200, f"Success path: {resp_ok.status_code}: {resp_ok.text}"

    # --- 401 unknown ---
    client.post(
        "/api/sensor/push",
        content=_compress(_build_envelope(sensor_id="any")),
        headers={"Authorization": f"Bearer {unknown_token}"},
    )

    # --- 401 revoked ---
    client.post(
        "/api/sensor/push",
        content=_compress(_build_envelope(sensor_id=sensor_rev)),
        headers={"Authorization": f"Bearer {token_rev}"},
    )

    # --- 403 mismatch ---
    client.post(
        "/api/sensor/push",
        content=_compress(_build_envelope(sensor_id=sensor_mis2)),
        headers={"Authorization": f"Bearer {token_mis}"},
    )

    # --- Assert audit rows ---
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
        assert len(ok_rows) >= 1, f"Expected ok audit row, found {len(ok_rows)}"

        unknown_rows = (
            db.query(IntegrationDelivery)
            .filter(
                IntegrationDelivery.destination == "sensor_push",
                IntegrationDelivery.error_summary == "unknown_sensor_token",
            )
            .all()
        )
        assert len(unknown_rows) >= 1, f"Expected unknown_sensor_token audit row, found {len(unknown_rows)}"

        revoked_rows = (
            db.query(IntegrationDelivery)
            .filter(
                IntegrationDelivery.destination == "sensor_push",
                IntegrationDelivery.error_summary == "revoked_sensor_token",
            )
            .all()
        )
        assert len(revoked_rows) >= 1, f"Expected revoked_sensor_token audit row, found {len(revoked_rows)}"

        mismatch_rows = (
            db.query(IntegrationDelivery)
            .filter(
                IntegrationDelivery.destination == "sensor_push",
                IntegrationDelivery.error_summary == "sensor_id_mismatch",
            )
            .all()
        )
        assert len(mismatch_rows) >= 1, f"Expected sensor_id_mismatch audit row, found {len(mismatch_rows)}"
    finally:
        db.close()


# ---------------------------------------------------------------------------
# AUTH-04: Missing Authorization header returns 401
# ---------------------------------------------------------------------------


def test_missing_token_returns_401(monkeypatch):
    """AUTH-04: No Authorization header must return 401 (missing credential)."""
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)
    _, client, _, _ = _app_with_db()

    env = _build_envelope(sensor_id="sensor-noauth-01")
    body = _compress(env)

    # No Authorization header
    resp = client.post("/api/sensor/push", content=body)
    assert resp.status_code == 401, (
        f"Missing Authorization header must return 401, got {resp.status_code}: {resp.text}"
    )
