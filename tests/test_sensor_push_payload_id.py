"""Phase 229 FIND-13 (D-12): sensor-ingested endpoints carry the payload_id of
the push that delivered them, on both the HTTPS and import-results paths."""
from __future__ import annotations

import inspect
import json
import uuid
from datetime import datetime, timezone

import pytest
import zstandard

from quirk.cli.console_cmd import _ingest_envelope
from quirk.db import get_session, init_db
from quirk.models import CryptoEndpoint, Sensor


def _seed_sensor(db_path: str, sensor_id: str, segment: str = "dmz") -> None:
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


def _finding(host: str) -> dict:
    return {
        "host": host,
        "port": 443,
        "protocol": "tls",
        "scanned_at": "2026-10-15T12:00:00",
        "tls_version": "TLSv1.3",
    }


def _make_envelope(sensor_id: str, hosts: list, segment: str = "dmz") -> dict:
    return {
        "payload_id": str(uuid.uuid4()),
        "pushed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "schema_version": "1.0.0",
        "sensor_version": "5.28.0",
        "sensor_id": sensor_id,
        "segment": segment,
        "findings": [_finding(h) for h in hosts],
    }


def _rows(db_path: str) -> list:
    with get_session(db_path) as session:
        rows = session.query(CryptoEndpoint).order_by(CryptoEndpoint.host).all()
        out = [(r.host, r.sensor_id, r.push_payload_id) for r in rows]
    return out


@pytest.fixture
def db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "p229.db")
    init_db(db_path)
    monkeypatch.setattr("quirk.dashboard.api.deps._default_db_path", lambda: db_path)
    return db_path


def test_ingest_stamps_every_endpoint_with_payload_id(db) -> None:
    sid = str(uuid.uuid4())
    _seed_sensor(db, sid)
    env = _make_envelope(sid, ["h0", "h1", "h2"])
    _ingest_envelope(env, config_path="", skip_replay_window=True)
    rows = _rows(db)
    assert len(rows) == 3
    assert all(r[1] == sid and r[2] == env["payload_id"] for r in rows)


def test_two_pushes_are_not_cross_tagged(db) -> None:
    sid = str(uuid.uuid4())
    _seed_sensor(db, sid)
    e1 = _make_envelope(sid, ["a0", "a1"])
    e2 = _make_envelope(sid, ["b0"])
    _ingest_envelope(e1, config_path="", skip_replay_window=True)
    _ingest_envelope(e2, config_path="", skip_replay_window=True)
    tags = {h: p for h, _s, p in _rows(db)}
    assert tags == {
        "a0": e1["payload_id"],
        "a1": e1["payload_id"],
        "b0": e2["payload_id"],
    }


def test_duplicate_payload_writes_no_extra_rows(db) -> None:
    sid = str(uuid.uuid4())
    _seed_sensor(db, sid)
    env = _make_envelope(sid, ["h0", "h1"])
    _ingest_envelope(env, config_path="", skip_replay_window=True)
    # _ingest_envelope converts the internal DuplicatePayloadError to SystemExit(1)
    # on its CLI path (the HTTPS route calls it with the exception surfaced).
    with pytest.raises(SystemExit):
        _ingest_envelope(env, config_path="", skip_replay_window=True)
    assert len(_rows(db)) == 2


def test_import_results_path_stamps_payload_id(db, tmp_path) -> None:
    from quirk.cli.console_cmd import _cmd_import_results

    sid = str(uuid.uuid4())
    _seed_sensor(db, sid, segment="air-gap")
    env = _make_envelope(sid, ["ag0"], segment="air-gap")
    qpush = tmp_path / "x.qpush"
    qpush.write_bytes(
        zstandard.ZstdCompressor(level=3).compress(json.dumps(env).encode("utf-8"))
    )

    class Args:
        file = str(qpush)
        config = "config.yaml"

    _cmd_import_results(Args())
    assert _rows(db) == [("ag0", sid, env["payload_id"])]


def test_https_route_calls_ingest_envelope() -> None:
    import quirk.dashboard.api.routes.sensor as sensor_routes

    src = inspect.getsource(sensor_routes)
    assert "_ingest_envelope(" in src
