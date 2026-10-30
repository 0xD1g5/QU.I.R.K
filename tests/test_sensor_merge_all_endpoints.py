"""FIND-13 / SC#3: quirk sensor merge keeps every endpoint of each sensor's latest push.

Real DB end to end: console import-results -> ingest (stamps push_payload_id)
-> `quirk sensor merge` -> merge_runs + merged CBOM. Nothing on the merge path
is mocked.
"""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone

import pytest

from quirk.cli.console_cmd import run_console
from quirk.cli.sensor_cmd import (
    _build_compressed_payload,
    _build_envelope,
    run_sensor,
)
from quirk.db import get_session, init_db
from quirk.models import CryptoEndpoint, MergeRun, Sensor


def _enroll(db_path: str, sensor_id: str, segment: str) -> None:
    with get_session(db_path) as s:
        s.add(Sensor(
            sensor_id=sensor_id, segment=segment,
            enrolled_at=datetime.now(timezone.utc).replace(tzinfo=None),
            expected_cadence_minutes=1440, sensor_version="5.28.0",
        ))
        s.commit()


def _eps(hosts):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    return [
        CryptoEndpoint(
            host=h, port=443, protocol="TLS", tls_version="TLSv1.2",
            cipher_suite="ECDHE-RSA-AES128-GCM-SHA256", cert_subject=f"CN={h}",
            cert_pubkey_alg="RSA", cert_pubkey_size=2048, scanned_at=now,
        )
        for h in hosts
    ]


def _import(tmp_path, sensor_id, segment, hosts):
    env = _build_envelope(
        {"sensor_version": "5.28.0", "sensor_id": sensor_id, "segment": segment},
        _eps(hosts),
    )
    q = tmp_path / f"{uuid.uuid4()}.qpush"
    header = json.dumps({"hmac-sha256": "hmac-sha256=" + "0" * 64}).encode() + b"\n"
    q.write_bytes(header + _build_compressed_payload(env))
    run_console(["import-results", str(q)])


def _merge(db_path):
    with pytest.raises(SystemExit) as exc:
        run_sensor(["merge", "--db", db_path])
    assert exc.value.code == 0


def _setup(tmp_path, monkeypatch):
    db_path = str(tmp_path / "console.db")
    init_db(db_path)
    monkeypatch.setattr("quirk.dashboard.api.deps._default_db_path", lambda: db_path)
    return db_path


def _latest_run(db_path):
    with get_session(db_path) as s:
        r = s.query(MergeRun).order_by(MergeRun.id.desc()).first()
        s.expunge(r)
        return r


def _cbom_hosts(tmp_path):
    out = set()
    for p in tmp_path.glob("cbom-*.cdx.json"):
        out |= set(re.findall(r"(h\d\.internal|[a-z]+-\d\.internal)", p.read_text()))
    return out


def test_one_sensor_qpush_three_hosts_merges_all_three(tmp_path, monkeypatch):
    db_path = _setup(tmp_path, monkeypatch)
    sid = str(uuid.uuid4())
    _enroll(db_path, sid, "dmz")
    _import(tmp_path, sid, "dmz", [f"h{i}.internal" for i in range(3)])
    _merge(db_path)
    assert _latest_run(db_path).endpoint_count == 3
    assert _cbom_hosts(tmp_path) == {"h0.internal", "h1.internal", "h2.internal"}


def test_two_sensors_multi_endpoint_cli_merge(tmp_path, monkeypatch):
    db_path = _setup(tmp_path, monkeypatch)
    s1, s2 = str(uuid.uuid4()), str(uuid.uuid4())
    _enroll(db_path, s1, "dmz")
    _enroll(db_path, s2, "core")
    _import(tmp_path, s1, "dmz", ["stale-1.internal", "stale-2.internal"])
    _import(tmp_path, s2, "core", ["stale-3.internal"])
    _import(tmp_path, s1, "dmz", [f"h{i}.internal" for i in range(3)])
    _import(tmp_path, s2, "core", ["a-1.internal", "a-2.internal"])
    _merge(db_path)
    assert _latest_run(db_path).endpoint_count == 5
    hosts = _cbom_hosts(tmp_path)
    assert {"h0.internal", "h1.internal", "h2.internal",
            "a-1.internal", "a-2.internal"} <= hosts
    assert not any(h.startswith("stale-") for h in hosts)
