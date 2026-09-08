"""Phase 191 Plan 02 (SPKI-01) — end-to-end round trip of
``cert_spki_fingerprint`` across the sensor push path.

ROADMAP success criterion 4 and the v5.8 B-01 recurrence guard: three
hand-maintained projections (``sensor_cmd.py::_endpoint_to_dict`` ->
JSON envelope transit -> ``console_cmd.py::_ingest_envelope``) sit between a
sensor-observed certificate and the console DB row, with no shared schema
enforcing that a field survives all three hops. A missed key at any hop
silently NULLs the field for every sensor-pushed endpoint while local scans
look perfectly correct.

Deliberately going past ``PushEnvelope`` parsing: stopping at
``PushEnvelope(**envelope)`` construction would be a VACUOUS PASS, because
``PushEnvelope.findings`` is an untyped list that never inspects per-finding
keys -- that boundary passes identically whether or not the B-01 bug is
present. Every assertion in this module reads a ``cert_spki_fingerprint``
value back off an actual, persisted ``CryptoEndpoint`` DB row, not off the
envelope or dict in memory.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from quirk.cli.console_cmd import _ingest_envelope
from quirk.cli.sensor_cmd import _endpoint_to_dict
from quirk.db import get_session, init_db
from quirk.merge.scan import _assemble_union
from quirk.models import CryptoEndpoint, Sensor

SENTINEL_FINGERPRINT = "a" * 63 + "1"  # 64-char lowercase hex sentinel


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


def _make_envelope(sensor_id: str, findings: list, segment: str = "dmz") -> dict:
    return {
        "payload_id": str(uuid.uuid4()),
        "pushed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "schema_version": "1.0.0",
        "sensor_version": "5.21.0",
        "sensor_id": sensor_id,
        "segment": segment,
        "findings": findings,
    }


def _seeded_endpoint(host: str, port: int, fingerprint) -> CryptoEndpoint:
    """A local (in-memory, un-persisted) CryptoEndpoint ORM row shaped like
    what tls_scanner.py would produce, carrying `fingerprint` in the column
    Plan 191-01 added."""
    return CryptoEndpoint(
        host=host,
        port=port,
        protocol="tls",
        scanned_at=datetime.now(timezone.utc).replace(tzinfo=None),
        tls_version="TLSv1.3",
        cipher_suite="TLS_AES_256_GCM_SHA384",
        cert_subject="CN=example.com",
        cert_issuer="CN=Example CA",
        cert_sans="DNS:example.com",
        cert_sig_alg="ecdsa-with-SHA256",
        cert_pubkey_alg="EC",
        cert_pubkey_size=256,
        cert_spki_fingerprint=fingerprint,
        cert_not_before=None,
        cert_not_after=None,
    )


def _query_endpoint(db_path: str, host: str, port: int) -> CryptoEndpoint:
    with get_session(db_path) as session:
        row = (
            session.query(CryptoEndpoint)
            .filter_by(host=host, port=port)
            .one()
        )
        # Detach values we need before the session closes.
        session.expunge(row)
        return row


def test_sensor_push_round_trip_preserves_spki_fingerprint(
    tmp_path, monkeypatch
) -> None:
    """Test A: _endpoint_to_dict -> JSON transit -> _ingest_envelope -> a
    queried DB row all carry the sentinel fingerprint unchanged."""
    db_path = str(tmp_path / "spki_roundtrip.db")
    init_db(db_path)
    sensor_id = str(uuid.uuid4())
    _seed_sensor(db_path, sensor_id)

    monkeypatch.setattr(
        "quirk.dashboard.api.deps._default_db_path", lambda: db_path
    )

    local_ep = _seeded_endpoint("spki-a.example", 443, SENTINEL_FINGERPRINT)
    finding = _endpoint_to_dict(local_ep)
    assert finding["cert_spki_fingerprint"] == SENTINEL_FINGERPRINT

    # Round-trip through JSON, exactly like the wire envelope.
    wire_finding = json.loads(json.dumps(finding))

    env = _make_envelope(sensor_id, findings=[wire_finding])
    _ingest_envelope(env, config_path="", skip_replay_window=True)

    row = _query_endpoint(db_path, "spki-a.example", 443)
    assert row.cert_spki_fingerprint == SENTINEL_FINGERPRINT


def test_sensor_push_omitting_key_ingests_with_null_no_exception(
    tmp_path, monkeypatch
) -> None:
    """Test B (falsifiability / D-11 tolerance / B-01 sensitivity): a finding
    dict with the cert_spki_fingerprint key deleted still ingests cleanly,
    with the column left NULL and no exception raised. This is the control
    that proves Test A's assertion is actually sensitive to the key being
    carried -- if _ingest_envelope used finding["cert_spki_fingerprint"]
    (subscript) instead of .get(), this test would raise KeyError instead of
    passing, and if the ingest projection line were removed entirely, Test A
    above would fail while this test would still (trivially) pass."""
    db_path = str(tmp_path / "spki_roundtrip_omit.db")
    init_db(db_path)
    sensor_id = str(uuid.uuid4())
    _seed_sensor(db_path, sensor_id)

    monkeypatch.setattr(
        "quirk.dashboard.api.deps._default_db_path", lambda: db_path
    )

    local_ep = _seeded_endpoint("spki-b.example", 443, SENTINEL_FINGERPRINT)
    finding = _endpoint_to_dict(local_ep)
    del finding["cert_spki_fingerprint"]
    assert "cert_spki_fingerprint" not in finding

    wire_finding = json.loads(json.dumps(finding))

    env = _make_envelope(sensor_id, findings=[wire_finding])
    # Must not raise (KeyError or otherwise).
    _ingest_envelope(env, config_path="", skip_replay_window=True)

    row = _query_endpoint(db_path, "spki-b.example", 443)
    assert row.cert_spki_fingerprint is None


def test_merge_union_preserves_spki_fingerprint(tmp_path) -> None:
    """Test C (merge pass-through): after ingest, quirk.merge.scan's
    _assemble_union returns the sensor-origin endpoint with its fingerprint
    intact -- proving (not assuming) that _assemble_union's whole-ORM-row
    .all() queries carry the new column through with no per-column
    projection to update."""
    db_path = str(tmp_path / "spki_merge.db")
    init_db(db_path)
    sensor_id = str(uuid.uuid4())
    _seed_sensor(db_path, sensor_id)

    with get_session(db_path) as session:
        session.add(
            CryptoEndpoint(
                host="spki-c.example",
                port=443,
                protocol="tls",
                scanned_at=datetime.now(timezone.utc).replace(tzinfo=None),
                tls_version="TLSv1.3",
                cipher_suite="TLS_AES_256_GCM_SHA384",
                cert_subject="CN=example.com",
                cert_issuer="CN=Example CA",
                cert_pubkey_alg="EC",
                cert_pubkey_size=256,
                cert_spki_fingerprint=SENTINEL_FINGERPRINT,
                sensor_id=sensor_id,
                segment="dmz",
            )
        )
        session.commit()

    with get_session(db_path) as session:
        union = _assemble_union(session)

    matches = [ep for ep in union if ep.host == "spki-c.example"]
    assert len(matches) == 1
    assert matches[0].cert_spki_fingerprint == SENTINEL_FINGERPRINT
