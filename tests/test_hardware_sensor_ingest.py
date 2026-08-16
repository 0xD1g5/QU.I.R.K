"""Phase 158 Plan 03 (HWLC-15) — console-side ingest of sensor-supplied
``hardware_devices``.

Covers the phase's central invariant: an envelope with the
``hardware_devices`` key **absent** (an old, pre-158 sensor) must never be
misread as a confirmed-zero observation. ``None`` (absent) means "no
observation, skip entirely" — zero ``HardwareDevice`` rows, zero
``HardwareDriftEvent`` rows, and ``persist_and_reconcile()`` is never called.
``[]`` (present, empty) means "confirmed zero devices" — the helper is still
invoked, with an empty list.

A real on-disk SQLite database (via ``quirk.db.init_db``) is used so
reconciliation reads freshly-committed rows through session queries, exactly
as production code does (mirrors ``tests/test_hardware_drift_wiring.py``).

No network I/O occurs anywhere in this module.
"""
from __future__ import annotations

import datetime as _dt
import uuid
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from sqlalchemy.orm import sessionmaker

from quirk.cli.console_cmd import _ingest_envelope
from quirk.db import get_session, init_db
from quirk.models import (
    CryptoEndpoint,
    HardwareDevice,
    HardwareDriftEvent,
    Sensor,
    SensorPush,
)


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _seed_sensor(db_path: str, sensor_id: str, segment: str = "dmz") -> None:
    """Write an enrolled Sensor row — required so the FK gate in
    _ingest_envelope() does not raise UnknownSensorError."""
    with get_session(db_path) as session:
        session.add(
            Sensor(
                sensor_id=sensor_id,
                segment=segment,
                enrolled_at=datetime.now(timezone.utc).replace(tzinfo=None),
                expected_cadence_minutes=60,
            )
        )
        session.commit()


def _device_dict(**overrides) -> dict:
    """A wire-shaped HardwareDevice dict with all required keys populated."""
    d = {
        "host": "10.0.0.10",
        "port": 22,
        "vendor": "Cisco",
        "model": "ISR4321",
        "pqc_status": "unsupported",
        "eol_date": "2027-01-01",
        "confidence": "high",
        "fingerprint_method": "ssh_banner",
        "raw_banner": "SSH-2.0-Cisco-1.25",
        "scanned_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "remediation_tier": "Tier 2",
        "snmp_sysdescr": "Cisco IOS Software",
        "snmp_sysname": "router1",
        "snmp_sysobjectid": "1.3.6.1.4.1.9.1.1",
        "snmp_vendor": "Cisco",
        "snmp_version": "v2c",
        "snmp_auth_protocol": None,
        "snmp_priv_protocol": None,
        "bridge_evidence_json": None,
        "bridge_confirmed_at": None,
        "modbus_vendor": None,
        "modbus_model": None,
        "modbus_firmware": "FW-1.2.3",
        "modbus_probe_state": None,
        "bacnet_vendor": "Johnson Controls",
        "bacnet_model": None,
        "bacnet_firmware": None,
        "bacnet_probe_state": None,
        "ssh_host_key_fingerprint": "SHA256:abc123deadbeef",
        "match_confidence": "high",
        "probe_status": "success",
    }
    d.update(overrides)
    return d


def _make_envelope(
    sensor_id: str,
    segment: str = "dmz",
    findings: list | None = None,
    hardware_devices=...,
) -> dict:
    """A valid wire envelope. hardware_devices is a sentinel-default kwarg:
    pass no value to omit the key entirely (None-vs-absent distinction)."""
    env: dict = {
        "payload_id": str(uuid.uuid4()),
        "pushed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "schema_version": "1.0.0",
        "sensor_version": "5.14.0",
        "sensor_id": sensor_id,
        "segment": segment,
        "findings": findings if findings is not None else [],
    }
    if hardware_devices is not ...:
        env["hardware_devices"] = hardware_devices
    return env


def _hw_rows(db_path, host=None, port=None):
    with get_session(db_path) as session:
        q = session.query(HardwareDevice)
        if host is not None:
            q = q.filter_by(host=host)
        if port is not None:
            q = q.filter_by(port=port)
        return q.all()


def _drift_events(db_path, host=None, port=None):
    with get_session(db_path) as session:
        q = session.query(HardwareDriftEvent)
        if host is not None:
            q = q.filter_by(host=host)
        if port is not None:
            q = q.filter_by(port=port)
        return q.all()


def _endpoint_count(db_path):
    with get_session(db_path) as session:
        return session.query(CryptoEndpoint).count()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_populated_hardware_devices_are_persisted(tmp_path, monkeypatch) -> None:
    """One device dict in -> exactly one HardwareDevice row out, with
    SNMP/Modbus/BACnet/identity fields preserved and scanned_at parsed."""
    db_path = str(tmp_path / "hw_ingest.db")
    init_db(db_path)
    sensor_id = str(uuid.uuid4())
    _seed_sensor(db_path, sensor_id)

    monkeypatch.setattr(
        "quirk.dashboard.api.deps._default_db_path", lambda: db_path
    )

    env = _make_envelope(sensor_id, hardware_devices=[_device_dict()])
    _ingest_envelope(env, config_path="", skip_replay_window=True)

    rows = _hw_rows(db_path, host="10.0.0.10", port=22)
    assert len(rows) == 1
    row = rows[0]
    assert row.snmp_sysdescr == "Cisco IOS Software"
    assert row.modbus_firmware == "FW-1.2.3"
    assert row.bacnet_vendor == "Johnson Controls"
    assert row.ssh_host_key_fingerprint == "SHA256:abc123deadbeef"
    assert isinstance(row.scanned_at, datetime)


def test_omitted_hardware_devices_writes_nothing(tmp_path, monkeypatch) -> None:
    """Envelope built WITHOUT the key -> zero HardwareDevice/HardwareDriftEvent
    rows, while the one finding still ingests normally."""
    db_path = str(tmp_path / "hw_ingest.db")
    init_db(db_path)
    sensor_id = str(uuid.uuid4())
    _seed_sensor(db_path, sensor_id)

    monkeypatch.setattr(
        "quirk.dashboard.api.deps._default_db_path", lambda: db_path
    )

    finding = {
        "host": "10.0.0.11",
        "port": 443,
        "protocol": "tls",
        "scanned_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    env = _make_envelope(sensor_id, findings=[finding])  # no hardware_devices key
    assert "hardware_devices" not in env

    _ingest_envelope(env, config_path="", skip_replay_window=True)

    assert _hw_rows(db_path) == []
    assert _drift_events(db_path) == []
    assert _endpoint_count(db_path) == 1


def test_omitted_hardware_devices_does_not_call_persist_and_reconcile(
    tmp_path, monkeypatch
) -> None:
    db_path = str(tmp_path / "hw_ingest.db")
    init_db(db_path)
    sensor_id = str(uuid.uuid4())
    _seed_sensor(db_path, sensor_id)

    monkeypatch.setattr(
        "quirk.dashboard.api.deps._default_db_path", lambda: db_path
    )

    env = _make_envelope(sensor_id)  # no hardware_devices key

    with patch(
        "quirk.scanner.hardware_drift.persist_and_reconcile"
    ) as mock_persist:
        _ingest_envelope(env, config_path="", skip_replay_window=True)

    assert mock_persist.call_count == 0


def test_empty_hardware_devices_still_calls_persist_and_reconcile(
    tmp_path, monkeypatch
) -> None:
    """[] is a confirmed-zero observation, structurally distinct from
    absent. Row counts cannot distinguish the two cases (both zero rows) --
    this is exactly why the call itself is asserted."""
    db_path = str(tmp_path / "hw_ingest.db")
    init_db(db_path)
    sensor_id = str(uuid.uuid4())
    _seed_sensor(db_path, sensor_id)

    monkeypatch.setattr(
        "quirk.dashboard.api.deps._default_db_path", lambda: db_path
    )

    env = _make_envelope(sensor_id, hardware_devices=[])

    with patch(
        "quirk.scanner.hardware_drift.persist_and_reconcile"
    ) as mock_persist:
        _ingest_envelope(env, config_path="", skip_replay_window=True)

    assert mock_persist.call_count == 1
    _, call_devices, _cfg, _logger = mock_persist.call_args[0]
    assert call_devices == []


def test_sensor_hardware_produces_drift_events_end_to_end(
    tmp_path, monkeypatch
) -> None:
    """Pre-seeded device history + an ingested device with a changed tier
    produces HardwareDriftEvent rows for that (host, port) -- proving
    sensor-origin devices get identical treatment to console-direct ones."""
    db_path = str(tmp_path / "hw_ingest.db")
    init_db(db_path)
    sensor_id = str(uuid.uuid4())
    _seed_sensor(db_path, sensor_id)

    monkeypatch.setattr(
        "quirk.dashboard.api.deps._default_db_path", lambda: db_path
    )

    host, port = "10.0.0.20", 22
    base = _dt.datetime(2026, 8, 1)
    with get_session(db_path) as session:
        # Mirrors tests/test_hardware_drift_wiring.py's seeding shape: an
        # older Tier 2 row, then a Tier 1 row -- so the ingested Tier 1
        # reading below is the second confirmation (N-of-M=2-of-3) of the
        # tier change, with the oldest Tier 2 row as the differing baseline.
        session.add(
            HardwareDevice(
                host=host,
                port=port,
                vendor="Cisco",
                pqc_status="unsupported",
                confidence="high",
                fingerprint_method="ssh_banner",
                probe_status="success",
                scanned_at=base,
                remediation_tier="Tier 2",
            )
        )
        session.add(
            HardwareDevice(
                host=host,
                port=port,
                vendor="Cisco",
                pqc_status="unsupported",
                confidence="high",
                fingerprint_method="ssh_banner",
                probe_status="success",
                scanned_at=base + _dt.timedelta(days=1),
                remediation_tier="Tier 1",
            )
        )
        session.commit()

    env = _make_envelope(
        sensor_id,
        hardware_devices=[
            _device_dict(
                host=host,
                port=port,
                remediation_tier="Tier 1",
                scanned_at=(base + _dt.timedelta(days=2)).strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                ),
            )
        ],
    )
    _ingest_envelope(env, config_path="", skip_replay_window=True)

    events = _drift_events(db_path, host=host, port=port)
    assert len(events) >= 1


def test_stray_identity_keys_do_not_break_ingest(tmp_path, monkeypatch) -> None:
    """A device dict carrying stray sensor_id/segment keys (no corresponding
    columns on HardwareDevice) ingests without raising and still writes the
    row (RESEARCH.md Pitfall 4 regression guard)."""
    db_path = str(tmp_path / "hw_ingest.db")
    init_db(db_path)
    sensor_id = str(uuid.uuid4())
    _seed_sensor(db_path, sensor_id)

    monkeypatch.setattr(
        "quirk.dashboard.api.deps._default_db_path", lambda: db_path
    )

    env = _make_envelope(
        sensor_id,
        hardware_devices=[
            _device_dict(
                host="10.0.0.30",
                sensor_id=sensor_id,
                segment="dmz",
            )
        ],
    )
    _ingest_envelope(env, config_path="", skip_replay_window=True)

    rows = _hw_rows(db_path, host="10.0.0.30")
    assert len(rows) == 1


def test_malformed_datetime_fields_do_not_abort_ingest(
    tmp_path, monkeypatch
) -> None:
    """A malformed eol_date/scanned_at string ingests without raising and
    the row is still written: eol_date (nullable) is written as None, while
    scanned_at (NOT NULL on HardwareDevice) falls back to ingest time rather
    than dropping the row entirely."""
    db_path = str(tmp_path / "hw_ingest.db")
    init_db(db_path)
    sensor_id = str(uuid.uuid4())
    _seed_sensor(db_path, sensor_id)

    monkeypatch.setattr(
        "quirk.dashboard.api.deps._default_db_path", lambda: db_path
    )

    env = _make_envelope(
        sensor_id,
        hardware_devices=[
            _device_dict(
                host="10.0.0.40",
                scanned_at="not-a-date",
                eol_date="2026-13-99",
            )
        ],
    )
    _ingest_envelope(env, config_path="", skip_replay_window=True)

    rows = _hw_rows(db_path, host="10.0.0.40")
    assert len(rows) == 1
    assert rows[0].scanned_at is not None
    assert rows[0].eol_date is None


def test_injected_session_path_persists_hardware(tmp_path) -> None:
    """Pass an injected session (db=) and assert the HardwareDevice row is
    durable after the caller commits -- covers the HTTPS-route branch."""
    db_path = str(tmp_path / "hw_ingest.db")
    engine = init_db(db_path)
    sensor_id = str(uuid.uuid4())
    _seed_sensor(db_path, sensor_id)

    Session = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
    )
    session = Session()
    try:
        env = _make_envelope(
            sensor_id, hardware_devices=[_device_dict(host="10.0.0.50")]
        )
        _ingest_envelope(
            env, config_path="", skip_replay_window=True, db=session
        )
        session.commit()
    finally:
        session.close()

    rows = _hw_rows(db_path, host="10.0.0.50")
    assert len(rows) == 1


def test_injected_session_hw_failure_does_not_wipe_caller_pending_rows(
    tmp_path,
) -> None:
    """CR-01 regression guard (Phase 158 review iteration 1 -> 2, WR-01).

    Reproduces the exact shared-session failure path CR-01 was about: an
    injected session (``db=``, HTTPS sensor-push route shape) already has a
    ``SensorPush`` row added+flushed by ``_ingest_envelope()`` itself before
    the hardware-devices block runs. If ``persist_and_reconcile()`` fails
    internally (here: ``purge_stale_hardware_history`` raises) and CR-01
    regressed back to an unconditional ``session.rollback()`` inside
    ``persist_and_reconcile`` regardless of ``owns_session``, that rollback
    would silently discard the caller's already-flushed ``SensorPush`` row
    from the session's pending state -- so even though the caller (this
    test, mirroring the route) commits afterward, nothing would be durably
    written. With the CR-01 fix (``owns_session=False`` skips
    ``session.rollback()``), the caller's row survives untouched and is
    written normally when the caller commits.
    """
    db_path = str(tmp_path / "hw_ingest.db")
    engine = init_db(db_path)
    sensor_id = str(uuid.uuid4())
    _seed_sensor(db_path, sensor_id)

    Session = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
    )
    session = Session()
    try:
        env = _make_envelope(
            sensor_id, hardware_devices=[_device_dict(host="10.0.0.60")]
        )
        with patch(
            "quirk.scanner.hardware_drift.purge_stale_hardware_history",
            side_effect=RuntimeError("simulated hardware persist failure"),
        ):
            # Must not raise -- persist_and_reconcile() is advisory-only and
            # swallows the internal failure, returning (0, []); the caller's
            # SensorPush row (already added+flushed above by
            # _ingest_envelope itself) must remain pending/committable.
            _ingest_envelope(
                env, config_path="", skip_replay_window=True, db=session
            )
        # Mirrors the HTTPS route: caller commits its own session after
        # _ingest_envelope() returns for an injected session.
        session.commit()
    finally:
        session.close()

    # The hardware device itself was never persisted (purge raised before
    # any commit), but the caller's own SensorPush row -- proof the shared
    # session's pending work was never silently rolled back -- is durable.
    with get_session(db_path) as verify_session:
        pushes = verify_session.query(SensorPush).filter_by(
            sensor_id=sensor_id
        ).all()
        assert len(pushes) == 1

    assert _hw_rows(db_path, host="10.0.0.60") == []
