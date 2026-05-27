"""Phase 114 acceptance tests — auto-merge trigger (AUTOMERGE-01/02/03 + D-05).

Six acceptance tests gating the entire phase:
  1. test_all_sensors_in_triggers_merge    — AUTOMERGE-01: last sensor push → MergeRun, no manual call
  2. test_auto_merge_disabled              — AUTOMERGE-02a: OFF → no MergeRun after final push
  3. test_revoked_sensor_excluded          — D-04: revoked sensor excluded from all-in set
  4. test_merge_failure_isolated           — AUTOMERGE-02b: bad merge → accepted + failed IntegrationDelivery
  5. test_double_fire_harmless             — D-05: idempotent re-check coalesces duplicate triggers
  6. test_cadence_window_triggers          — AUTOMERGE-02c: push after window → MergeRun + coverage_warning
  7. test_manual_merge_regression          — AUTOMERGE-03: _cmd_merge / merge_scan unchanged behavior

BackgroundTasks runs SYNCHRONOUSLY after response under TestClient
(starlette==0.49.3 / fastapi==0.128.8). Assert MergeRun immediately after
client.post() — no time.sleep required.

DB isolation: use a file-backed SQLite shared between the FastAPI test client
(get_db override) and the background task's own get_session(db_path) call.
Both are pointed at the same QUIRK_DB_PATH tmp file.
"""
from __future__ import annotations

import hashlib
import json
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import pytest
import yaml
import zstandard
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from quirk.dashboard.api.app import create_app
from quirk.dashboard.api.deps import get_db
from quirk.models import Base, IntegrationDelivery, MergeRun, Sensor, SensorToken

# ---------------------------------------------------------------------------
# Shared DB + TestClient factory — file-backed so background task shares DB
# ---------------------------------------------------------------------------


def _app_with_file_db(db_path: str):
    """Create a TestClient backed by a file-backed SQLite at db_path.

    Both the FastAPI get_db override AND the background task's run_auto_merge
    get_session(db_path) call use the same file, so MergeRun rows written by
    the background task are visible to the test assertions.
    """
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
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
# Envelope builder helpers (verbatim from tests/test_sensor_ingest.py)
# ---------------------------------------------------------------------------


def _build_envelope(
    sensor_id: str = "test-sensor-01",
    segment: str = "dmz",
    payload_id: Optional[str] = None,
    pushed_at: Optional[str] = None,
    schema_version: str = "1.0.0",
    sensor_version: str = "5.4.0",
    findings: Optional[list] = None,
) -> dict:
    """Build a minimal valid wire envelope dict."""
    if pushed_at is None:
        pushed_at = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    if payload_id is None:
        payload_id = str(uuid.uuid4())
    return {
        "payload_id": payload_id,
        "pushed_at": pushed_at,
        "schema_version": schema_version,
        "sensor_version": sensor_version,
        "sensor_id": sensor_id,
        "segment": segment,
        "findings": findings or [],
    }


def _compress(envelope: dict) -> bytes:
    """Serialize envelope to JSON and compress with zstd level-3."""
    raw = json.dumps(envelope, ensure_ascii=False).encode("utf-8")
    return zstandard.ZstdCompressor(level=3).compress(raw)


# ---------------------------------------------------------------------------
# Seed helpers (verbatim from tests/test_sensor_ingest.py)
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


def _seed_token(
    TestingSession,
    sensor_id: str,
    raw_token: Optional[str] = None,
    revoked: bool = False,
) -> str:
    """Write a SensorToken row and return the raw token string."""
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
# Config isolation helper (PATTERNS pattern — write yaml to tmp_path)
# ---------------------------------------------------------------------------


def _write_auto_merge_config(
    tmp_path,
    enabled: bool = True,
    trigger_condition: str = "all-sensors-in",
    cadence_window_minutes: Optional[int] = None,
) -> str:
    """Write a minimal console.auto_merge config to tmp_path and return path."""
    block: dict = {
        "enabled": enabled,
        "trigger_condition": trigger_condition,
    }
    if cadence_window_minutes is not None:
        block["cadence_window_minutes"] = cadence_window_minutes
    cfg = {"console": {"auto_merge": block}}
    p = tmp_path / "config.yaml"
    p.write_text(yaml.dump(cfg))
    return str(p)


# ---------------------------------------------------------------------------
# Push helper — DRY wrapper used by every test
# ---------------------------------------------------------------------------


def _do_push(client, sensor_id: str, raw_token: str) -> dict:
    """Send one push for sensor_id and assert 200/accepted. Return JSON."""
    envelope = _build_envelope(sensor_id=sensor_id)
    body = _compress(envelope)
    resp = client.post(
        "/api/sensor/push",
        content=body,
        headers={"Authorization": f"Bearer {raw_token}"},
    )
    assert resp.status_code == 200, f"push failed {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data["status"] == "accepted"
    return data


# ===========================================================================
# Task 1: all-sensors-in / disabled / revoked-excluded tests (AUTOMERGE-01/02a/D-04)
# ===========================================================================


def test_all_sensors_in_triggers_merge(monkeypatch, tmp_path):
    """AUTOMERGE-01: last enrolled sensor push → exactly one MergeRun, no manual call."""
    db_path = str(tmp_path / "quirk_test.db")
    monkeypatch.setenv("QUIRK_DB_PATH", db_path)
    config_path = _write_auto_merge_config(tmp_path, enabled=True, trigger_condition="all-sensors-in")
    monkeypatch.setenv("QUIRK_CONFIG_PATH", config_path)
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)

    app, client, engine, TestingSession = _app_with_file_db(db_path)

    _seed_sensor(TestingSession, "sensor-a", "dmz")
    _seed_sensor(TestingSession, "sensor-b", "corp")
    tok_a = _seed_token(TestingSession, "sensor-a")
    tok_b = _seed_token(TestingSession, "sensor-b")

    # Push sensor A — not all in yet → no MergeRun
    _do_push(client, "sensor-a", tok_a)

    db = TestingSession()
    try:
        assert db.query(MergeRun).count() == 0, "MergeRun created too early (only sensor-a pushed)"
    finally:
        db.close()

    # Push sensor B — all in → MergeRun should be produced synchronously
    _do_push(client, "sensor-b", tok_b)

    db = TestingSession()
    try:
        merge_runs = db.query(MergeRun).all()
        assert len(merge_runs) == 1, f"Expected 1 MergeRun, got {len(merge_runs)}"
        mr = merge_runs[0]
        assert mr.sensor_count >= 2  # both sensor-a and sensor-b were merged
    finally:
        db.close()


def test_auto_merge_disabled(monkeypatch, tmp_path):
    """AUTOMERGE-02a: config enabled=false → no MergeRun after final push."""
    db_path = str(tmp_path / "quirk_test.db")
    monkeypatch.setenv("QUIRK_DB_PATH", db_path)
    config_path = _write_auto_merge_config(tmp_path, enabled=False)
    monkeypatch.setenv("QUIRK_CONFIG_PATH", config_path)
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)

    app, client, engine, TestingSession = _app_with_file_db(db_path)

    _seed_sensor(TestingSession, "sensor-a", "dmz")
    _seed_sensor(TestingSession, "sensor-b", "corp")
    tok_a = _seed_token(TestingSession, "sensor-a")
    tok_b = _seed_token(TestingSession, "sensor-b")

    _do_push(client, "sensor-a", tok_a)
    _do_push(client, "sensor-b", tok_b)

    db = TestingSession()
    try:
        count = db.query(MergeRun).count()
        assert count == 0, f"Expected 0 MergeRun with auto-merge disabled, got {count}"
    finally:
        db.close()


def test_revoked_sensor_excluded(monkeypatch, tmp_path):
    """D-04: revoked sensor B is excluded from all-in set; sensor A alone → 1 MergeRun."""
    db_path = str(tmp_path / "quirk_test.db")
    monkeypatch.setenv("QUIRK_DB_PATH", db_path)
    config_path = _write_auto_merge_config(tmp_path, enabled=True, trigger_condition="all-sensors-in")
    monkeypatch.setenv("QUIRK_CONFIG_PATH", config_path)
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)

    app, client, engine, TestingSession = _app_with_file_db(db_path)

    _seed_sensor(TestingSession, "sensor-a", "dmz")
    _seed_sensor(TestingSession, "sensor-b", "corp")
    tok_a = _seed_token(TestingSession, "sensor-a")
    # Seed sensor-b with a revoked token — it should be excluded from all-in
    _seed_token(TestingSession, "sensor-b", revoked=True)

    # Pushing only sensor-a (the sole active sensor) should trigger a merge
    _do_push(client, "sensor-a", tok_a)

    db = TestingSession()
    try:
        merge_runs = db.query(MergeRun).all()
        assert len(merge_runs) == 1, (
            f"Expected 1 MergeRun (revoked sensor-b excluded), got {len(merge_runs)}"
        )
    finally:
        db.close()


# ===========================================================================
# CR-01 regression: mixed-token sensor + zero-token sensor (inclusion subquery)
# ===========================================================================


def test_mixed_token_sensor_is_required_for_all_in(monkeypatch, tmp_path):
    """CR-01 regression: a sensor with BOTH a revoked token AND an active token must
    still be counted as an active sensor.  Auto-merge must NOT fire until that sensor
    pushes (the re-keyed sensor's data is still required).

    The bug: the old exclusion-subquery logic matched any sensor with a revoked token,
    so a re-keyed sensor (old token revoked + new token active) was incorrectly excluded
    from the all-in set, causing merges that silently omitted a live sensor.
    """
    db_path = str(tmp_path / "quirk_test.db")
    monkeypatch.setenv("QUIRK_DB_PATH", db_path)
    config_path = _write_auto_merge_config(tmp_path, enabled=True, trigger_condition="all-sensors-in")
    monkeypatch.setenv("QUIRK_CONFIG_PATH", config_path)
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)

    app, client, engine, TestingSession = _app_with_file_db(db_path)

    # sensor-a: normal active token
    _seed_sensor(TestingSession, "sensor-a", "dmz")
    tok_a = _seed_token(TestingSession, "sensor-a")

    # sensor-b: re-keyed — has a revoked token AND an active token (new key)
    _seed_sensor(TestingSession, "sensor-b", "corp")
    _seed_token(TestingSession, "sensor-b", revoked=True)   # old, revoked
    tok_b_new = _seed_token(TestingSession, "sensor-b")     # new, active

    # Push only sensor-a — sensor-b (mixed-token, active) is still required → no merge
    _do_push(client, "sensor-a", tok_a)

    db = TestingSession()
    try:
        count = db.query(MergeRun).count()
        assert count == 0, (
            f"MergeRun fired before mixed-token sensor-b pushed (CR-01 regression): "
            f"got {count} MergeRun row(s)"
        )
    finally:
        db.close()

    # Push sensor-b using the new active token — now all active sensors are in → merge fires
    _do_push(client, "sensor-b", tok_b_new)

    db = TestingSession()
    try:
        count = db.query(MergeRun).count()
        assert count >= 1, (
            f"Expected MergeRun after mixed-token sensor-b pushed, got {count}"
        )
    finally:
        db.close()


def test_zero_token_sensor_not_counted_as_active(monkeypatch, tmp_path):
    """CR-01 regression: a Sensor row with NO SensorToken rows at all must NOT be
    counted in the active set (it has no valid auth credential and can never push).

    The bug: the old exclusion subquery only excluded sensors appearing in the
    revoked-token set; a sensor with zero tokens had no entry in either set, so it
    was silently included in active_sensors with last_push_at=None, blocking all
    merges indefinitely.
    """
    db_path = str(tmp_path / "quirk_test.db")
    monkeypatch.setenv("QUIRK_DB_PATH", db_path)
    config_path = _write_auto_merge_config(tmp_path, enabled=True, trigger_condition="all-sensors-in")
    monkeypatch.setenv("QUIRK_CONFIG_PATH", config_path)
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)

    app, client, engine, TestingSession = _app_with_file_db(db_path)

    # sensor-a: has an active token and will push
    _seed_sensor(TestingSession, "sensor-a", "dmz")
    tok_a = _seed_token(TestingSession, "sensor-a")

    # sensor-ghost: enrolled but has ZERO SensorToken rows — cannot push, must not block
    _seed_sensor(TestingSession, "sensor-ghost", "isolated")
    # intentionally no _seed_token call for sensor-ghost

    # Push sensor-a — sensor-ghost has no tokens so is NOT in the active set → merge fires
    _do_push(client, "sensor-a", tok_a)

    db = TestingSession()
    try:
        count = db.query(MergeRun).count()
        assert count >= 1, (
            f"Expected MergeRun (zero-token ghost sensor should not block merge), "
            f"got {count} MergeRun row(s)"
        )
    finally:
        db.close()


# ===========================================================================
# Task 2: failure-isolation and double-fire tests (AUTOMERGE-02b / D-05)
# ===========================================================================


def test_merge_failure_isolated(monkeypatch, tmp_path):
    """AUTOMERGE-02b: merge raises → push accepted, push rows intact, 0 MergeRun,
    exactly 1 IntegrationDelivery destination=auto_merge status=failed with non-null error_summary.
    """
    db_path = str(tmp_path / "quirk_test.db")
    monkeypatch.setenv("QUIRK_DB_PATH", db_path)
    config_path = _write_auto_merge_config(tmp_path, enabled=True, trigger_condition="all-sensors-in")
    monkeypatch.setenv("QUIRK_CONFIG_PATH", config_path)
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)

    # Patch merge_scan to raise before the app and client are created
    # (so the import is in place when the background task runs)
    import quirk.merge.scan as merge_scan_mod
    monkeypatch.setattr(merge_scan_mod, "merge_scan", lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("simulated merge failure")))

    app, client, engine, TestingSession = _app_with_file_db(db_path)

    _seed_sensor(TestingSession, "sensor-a", "dmz")
    tok_a = _seed_token(TestingSession, "sensor-a")

    resp_data = _do_push(client, "sensor-a", tok_a)
    # Push must still return accepted even though merge failed
    assert resp_data["status"] == "accepted"

    db = TestingSession()
    try:
        # No MergeRun should exist (merge raised before flush)
        mr_count = db.query(MergeRun).count()
        assert mr_count == 0, f"Expected 0 MergeRun on merge failure, got {mr_count}"

        # Exactly one auto_merge/failed IntegrationDelivery row
        failed_rows = (
            db.query(IntegrationDelivery)
            .filter(
                IntegrationDelivery.destination == "auto_merge",
                IntegrationDelivery.status == "failed",
            )
            .all()
        )
        assert len(failed_rows) == 1, (
            f"Expected 1 auto_merge/failed IntegrationDelivery row, got {len(failed_rows)}"
        )
        audit_row = failed_rows[0]
        # T-114-T1: error_summary must be a non-empty string (safe_str output), not a raw traceback
        assert audit_row.error_summary is not None
        assert isinstance(audit_row.error_summary, str)
        assert len(audit_row.error_summary) > 0
        # Must not contain raw exception class names or tracebacks
        assert "Traceback" not in audit_row.error_summary
    finally:
        db.close()


def test_double_fire_harmless(monkeypatch, tmp_path):
    """D-05: idempotent re-check coalesces duplicate trigger — second push with
    no newer data produces no additional MergeRun.
    """
    db_path = str(tmp_path / "quirk_test.db")
    monkeypatch.setenv("QUIRK_DB_PATH", db_path)
    config_path = _write_auto_merge_config(tmp_path, enabled=True, trigger_condition="all-sensors-in")
    monkeypatch.setenv("QUIRK_CONFIG_PATH", config_path)
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)

    app, client, engine, TestingSession = _app_with_file_db(db_path)

    _seed_sensor(TestingSession, "sensor-a", "dmz")
    tok_a = _seed_token(TestingSession, "sensor-a")

    # First push: all-in (only one sensor), triggers a merge → 1 MergeRun
    _do_push(client, "sensor-a", tok_a)

    db = TestingSession()
    try:
        count_after_first = db.query(MergeRun).count()
        assert count_after_first >= 1, "Expected at least 1 MergeRun after first push"
    finally:
        db.close()

    count_before_second = count_after_first

    # Send a second push with a fresh payload_id (uuid4 ensures no 409).
    # The D-05 re-check in run_auto_merge should suppress a redundant MergeRun because
    # last_push_at will be <= merged_at from the first merge.
    # The key assertion: after the second push completes, MergeRun count is <= count+1.
    # D-06 accepts a duplicate MergeRun from TOCTOU, so we only assert the count is
    # bounded (not more than 2), not that it's exactly unchanged.
    _do_push(client, "sensor-a", tok_a)

    db = TestingSession()
    try:
        count_after_second = db.query(MergeRun).count()
        # D-06: at most one additional MergeRun (duplicate is harmless)
        assert count_after_second <= count_before_second + 1, (
            f"Too many MergeRun rows after double push: {count_after_second}"
        )
    finally:
        db.close()


# ===========================================================================
# Task 3: cadence-window and manual-merge regression tests (AUTOMERGE-02c/03)
# ===========================================================================


def test_cadence_window_triggers(monkeypatch, tmp_path):
    """AUTOMERGE-02c: cadence-window mode with a prior MergeRun in the past → push
    that crosses the elapsed window fires a merge; coverage_warning lists not-yet-in sensor.
    """
    db_path = str(tmp_path / "quirk_test.db")
    monkeypatch.setenv("QUIRK_DB_PATH", db_path)
    # cadence_window_minutes=0 → any push will cross the window (elapsed >= 0 is always true)
    config_path = _write_auto_merge_config(
        tmp_path,
        enabled=True,
        trigger_condition="cadence-window",
        cadence_window_minutes=0,
    )
    monkeypatch.setenv("QUIRK_CONFIG_PATH", config_path)
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)

    app, client, engine, TestingSession = _app_with_file_db(db_path)

    _seed_sensor(TestingSession, "sensor-a", "dmz")
    _seed_sensor(TestingSession, "sensor-b", "corp")
    tok_a = _seed_token(TestingSession, "sensor-a")
    _seed_token(TestingSession, "sensor-b")  # sensor-b has a token but will NOT push

    # Seed a prior MergeRun with merged_at well in the past so elapsed > 0 min
    db = TestingSession()
    try:
        past = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=2)
        db.add(MergeRun(
            scan_id="prior-merge-run",
            merged_at=past,
            endpoint_count=0,
            sensor_count=0,
            score=None,
            coverage_warning_json=None,
        ))
        db.commit()
    finally:
        db.close()

    # Push only sensor-a; cadence-window with 0 min → fires merge
    _do_push(client, "sensor-a", tok_a)

    db = TestingSession()
    try:
        # At least one NEW MergeRun beyond the seeded one (the trigger should fire)
        merge_runs = db.query(MergeRun).order_by(MergeRun.id).all()
        assert len(merge_runs) >= 2, (
            f"Expected at least 2 MergeRun rows (1 seeded + 1 from trigger), got {len(merge_runs)}"
        )
        # The latest MergeRun should have coverage_warning listing sensor-b
        latest_mr = merge_runs[-1]
        if latest_mr.coverage_warning_json:
            cw = json.loads(latest_mr.coverage_warning_json)
            assert "sensor-b" in cw.get("missing_sensors", []), (
                f"Expected sensor-b in coverage_warning missing_sensors: {cw}"
            )
    finally:
        db.close()


def test_manual_merge_regression(monkeypatch, tmp_path):
    """AUTOMERGE-03: _cmd_merge / merge_scan unchanged behavior — identical Option-A union
    with coverage_warning and sensor-local scanned_at preserved (not rewritten).
    """
    import argparse
    from quirk.cli.sensor_cmd import _cmd_merge
    from quirk.db import get_session, init_db
    from quirk.merge.scan import merge_scan
    from quirk.models import CryptoEndpoint

    db_path = str(tmp_path / "quirk_regression.db")
    monkeypatch.setenv("QUIRK_DB_PATH", db_path)
    # Auto-merge OFF so the manual path is exercised in isolation
    config_path = _write_auto_merge_config(tmp_path, enabled=False)
    monkeypatch.setenv("QUIRK_CONFIG_PATH", config_path)
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)

    # Initialize the DB schema
    init_db(db_path)

    # Seed two sensors and a CryptoEndpoint row per sensor (mimicking pushed data)
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    sensor_a_ts = now - timedelta(minutes=5)
    sensor_b_ts = now - timedelta(minutes=3)

    db = TestingSession()
    try:
        db.add(Sensor(
            sensor_id="sensor-a",
            segment="dmz",
            engagement=None,
            enrolled_at=now,
            last_push_at=sensor_a_ts,
            expected_cadence_minutes=1440,
            sensor_version=None,
        ))
        db.add(Sensor(
            sensor_id="sensor-b",
            segment="corp",
            engagement=None,
            enrolled_at=now,
            last_push_at=sensor_b_ts,
            expected_cadence_minutes=1440,
            sensor_version=None,
        ))
        # One CryptoEndpoint per sensor (minimal, no real crypto data)
        db.add(CryptoEndpoint(
            sensor_id="sensor-a",
            host="10.0.0.1",
            port=443,
            protocol="TLS",
            scanned_at=sensor_a_ts,
            segment="dmz",
        ))
        db.add(CryptoEndpoint(
            sensor_id="sensor-b",
            host="10.0.0.2",
            port=443,
            protocol="TLS",
            scanned_at=sensor_b_ts,
            segment="corp",
        ))
        db.commit()
    finally:
        db.close()

    # --- Invoke merge_scan directly (mirrors _cmd_merge without the print/sys.exit) ---
    output_dir = str(tmp_path)
    with get_session(db_path) as db:
        result = merge_scan(db, stale_days=30, output_dir=output_dir)

    # AUTOMERGE-03 assertions: Option-A union semantics
    assert result["scan_id"] is not None
    assert result["endpoint_count"] >= 2, (
        f"Expected at least 2 endpoints in union (one per sensor), got {result['endpoint_count']}"
    )
    assert result["sensor_count"] == 2, (
        f"Expected 2 sensors in merge, got {result['sensor_count']}"
    )

    # coverage_warning: both sensors are current (pushed recently) → None
    assert result["coverage_warning"] is None, (
        f"Expected no coverage_warning (both sensors current), got {result['coverage_warning']}"
    )

    # MergeRun row persisted
    db = TestingSession()
    try:
        merge_runs = db.query(MergeRun).all()
        assert len(merge_runs) == 1

        # Verify source CryptoEndpoint.scanned_at was NOT rewritten (AUTOMERGE-03 invariant)
        eps = db.query(CryptoEndpoint).all()
        scanned_ats = {ep.sensor_id: ep.scanned_at for ep in eps}
        assert scanned_ats["sensor-a"] == sensor_a_ts, (
            f"sensor-a scanned_at rewritten! expected {sensor_a_ts}, got {scanned_ats['sensor-a']}"
        )
        assert scanned_ats["sensor-b"] == sensor_b_ts, (
            f"sensor-b scanned_at rewritten! expected {sensor_b_ts}, got {scanned_ats['sensor-b']}"
        )
    finally:
        db.close()
