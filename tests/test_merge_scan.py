"""Unit tests for quirk.merge.scan.merge_scan() — MERGE-01/02/04/05.

RED → GREEN: tests added before implementation exists.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from quirk.intelligence.evidence import build_evidence_summary
from quirk.intelligence.scoring import compute_readiness_score
from quirk.models import CryptoEndpoint, MergeRun, Sensor


# ---------------------------------------------------------------------------
# Helpers / factories
# ---------------------------------------------------------------------------

def _tls_ep(**overrides) -> CryptoEndpoint:
    """TLS CryptoEndpoint with sensible defaults."""
    defaults = dict(
        host="example.com",
        port=443,
        protocol=None,
        tls_version="TLSv1.2",
        cipher_suite="TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384",
        cert_pubkey_alg="RSA",
        cert_pubkey_size=2048,
        cert_sig_alg="sha256WithRSAEncryption",
        cert_subject="CN=example.com",
        cert_issuer="CN=Example CA",
        cert_not_before=None,
        cert_not_after=None,
        tls_capabilities_json=None,
        ssh_audit_json=None,
        sensor_id=None,
        segment="local",
        scanned_at=datetime(2026, 5, 25, 12, 0, 0),
    )
    defaults.update(overrides)
    return CryptoEndpoint(**defaults)


def _sensor(sensor_id: str, last_push_at, cadence_minutes: int = 60) -> Sensor:
    """Sensor row with controlled last_push_at for overdue tests."""
    return Sensor(
        sensor_id=sensor_id,
        segment="test-seg",
        enrolled_at=datetime(2026, 1, 1),
        last_push_at=last_push_at,
        expected_cadence_minutes=cadence_minutes,
        sensor_version="test",
    )


def _make_db(endpoints, sensors=None):
    """Build a minimal mock SQLAlchemy session for merge_scan tests."""
    db = MagicMock()

    # Build sensor list
    sensor_list = sensors or []

    # Build sensor subquery mock (latest-per-sensor rows)
    # For sensors that have endpoints, return the latest-per-sensor eps.
    # For NULL-sensor rows, return all.
    sensor_eps = [ep for ep in endpoints if ep.sensor_id is not None]
    local_eps = [ep for ep in endpoints if ep.sensor_id is None]

    # Track what scanned_ats were BEFORE merge (for preservation test)
    original_scanned_ats = {id(ep): ep.scanned_at for ep in endpoints}

    # We need the db.query chain to work.
    # We'll use a real SQLite in-memory DB approach for most tests.
    return db, original_scanned_ats


# ---------------------------------------------------------------------------
# Use a real in-memory DB for accurate tests
# ---------------------------------------------------------------------------

def _setup_real_db(tmp_path, endpoints, sensors=None):
    """Set up a real SQLite DB with given endpoints and sensors."""
    db_path = str(tmp_path / "test_merge.db")
    os.environ["QUIRK_DB_PATH"] = db_path

    from quirk.db import init_db, get_session

    engine = init_db(db_path)

    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False,
                           expire_on_commit=False)

    with Session() as session:
        for ep in endpoints:
            session.add(ep)
        if sensors:
            for s in sensors:
                session.add(s)
        session.commit()

    return db_path, engine


# ---------------------------------------------------------------------------
# MERGE-01: merge_scan calls build_evidence_summary → compute_readiness_score → build_cbom
# ---------------------------------------------------------------------------

def test_merge_pipeline_uses_existing_engines(tmp_path):
    """MERGE-01: merge_scan() calls the canonical engine chain over the union."""
    from quirk.merge.scan import merge_scan

    ts = datetime(2026, 5, 25, 12, 0, 0)
    eps = [
        _tls_ep(host="10.0.1.1", sensor_id="s1", scanned_at=ts),
        _tls_ep(host="10.0.2.1", sensor_id="s2", scanned_at=ts),
    ]
    sensors = [
        _sensor("s1", last_push_at=datetime(2026, 5, 25, 11, 55, 0)),
        _sensor("s2", last_push_at=datetime(2026, 5, 25, 11, 55, 0)),
    ]

    db_path, _ = _setup_real_db(tmp_path, eps, sensors)
    now = datetime(2026, 5, 25, 12, 30, 0)

    with patch("quirk.merge.scan.build_evidence_summary") as mock_ev, \
         patch("quirk.merge.scan.compute_readiness_score") as mock_sc, \
         patch("quirk.merge.scan.build_cbom") as mock_cbom:
        # Set up mock return values
        mock_ev.return_value = {"totals": {}, "protocol_counts": {}}
        mock_sc.return_value = {
            "score": 72, "rating": "MODERATE", "subscores": {}, "drivers": []
        }
        mock_cbom.return_value = MagicMock()

        from quirk.db import get_session
        with get_session(db_path) as db:
            result = merge_scan(db, now=now)

    # Engine chain was called
    assert mock_ev.call_count == 1
    assert mock_sc.call_count == 1
    assert mock_cbom.call_count == 1

    # Result has expected keys
    assert "score" in result
    assert "rating" in result
    assert "subscores" in result
    assert "scan_id" in result
    assert "endpoint_count" in result


# ---------------------------------------------------------------------------
# MERGE-02 / Option A: score is computed over the full union, never averaged
# ---------------------------------------------------------------------------

def test_option_a_score_not_averaged(tmp_path):
    """MERGE-02: merge_scan() runs ONE score computation over the full union.

    The union score must equal compute_readiness_score(build_evidence_summary(union))
    and NOT equal the mean of per-segment scores when those differ.
    """
    from quirk.merge.scan import merge_scan

    ts = datetime(2026, 5, 25, 12, 0, 0)
    # Segment A: all good TLS → high subscore
    eps_a = [_tls_ep(host="10.0.1.1", sensor_id="s1", scanned_at=ts,
                     tls_version="TLSv1.3", cert_pubkey_alg="ECDSA",
                     cert_pubkey_size=256, cert_sig_alg="ecdsa-with-SHA256")]
    # Segment B: weak TLS → low subscore
    eps_b = [_tls_ep(host="10.0.2.1", sensor_id="s2", scanned_at=ts,
                     tls_version="TLSv1.0", cert_pubkey_alg="RSA",
                     cert_pubkey_size=1024, cert_sig_alg="sha1WithRSAEncryption")]

    sensors = [
        _sensor("s1", last_push_at=datetime(2026, 5, 25, 11, 55, 0)),
        _sensor("s2", last_push_at=datetime(2026, 5, 25, 11, 55, 0)),
    ]

    db_path, _ = _setup_real_db(tmp_path, eps_a + eps_b, sensors)
    now = datetime(2026, 5, 25, 12, 30, 0)

    # Compute expected union score directly
    union = eps_a + eps_b
    evidence = build_evidence_summary(union, findings=None)
    expected_score = compute_readiness_score(evidence)["score"]

    # Compute per-segment scores to verify they differ from union
    score_a = compute_readiness_score(build_evidence_summary(eps_a))["score"]
    score_b = compute_readiness_score(build_evidence_summary(eps_b))["score"]
    naive_avg = round((score_a + score_b) / 2)

    from quirk.db import get_session
    with get_session(db_path) as db:
        result = merge_scan(db, now=now)

    assert result["score"] == expected_score, (
        f"Expected union score {expected_score}, got {result['score']}"
    )
    # If segment scores differ, confirm we're NOT averaging
    if score_a != score_b and expected_score != naive_avg:
        assert result["score"] != naive_avg, (
            f"Score {result['score']} looks like an average of {score_a} and {score_b}"
        )


# ---------------------------------------------------------------------------
# MERGE-04: coverage_warning for overdue / never-pushed sensors
# ---------------------------------------------------------------------------

def test_coverage_warning_overdue_sensor(tmp_path):
    """MERGE-04: a sensor with last_push_at older than now-2×cadence → coverage_warning."""
    from quirk.merge.scan import merge_scan

    ts = datetime(2026, 5, 25, 12, 0, 0)
    now = datetime(2026, 5, 25, 12, 30, 0)
    eps = [_tls_ep(host="10.0.1.1", sensor_id="s1", scanned_at=ts)]
    # s2 was enrolled recently (today), has never pushed — should be flagged as overdue
    # (WR-02: stale check uses enrolled_at; enrolled today is well within stale_days=30)
    sensors = [
        _sensor("s1", last_push_at=datetime(2026, 5, 25, 11, 55, 0), cadence_minutes=60),
        Sensor(
            sensor_id="s2",
            segment="test-seg",
            enrolled_at=datetime(2026, 5, 25, 12, 0, 0),  # enrolled today — not stale
            last_push_at=None,
            expected_cadence_minutes=60,
            sensor_version="test",
        ),
    ]

    db_path, _ = _setup_real_db(tmp_path, eps, sensors)

    from quirk.db import get_session
    with get_session(db_path) as db:
        result = merge_scan(db, now=now)

    cw = result["coverage_warning"]
    assert cw is not None, "Expected coverage_warning for never-pushed sensor enrolled today"
    assert "s2" in cw["missing_sensors"]
    assert cw["reason"]


def test_coverage_warning_overdue_by_cadence(tmp_path):
    """MERGE-04: a sensor whose last_push_at > 2×cadence ago is overdue."""
    from quirk.merge.scan import merge_scan

    ts = datetime(2026, 5, 25, 12, 0, 0)
    eps = [_tls_ep(host="10.0.1.1", sensor_id="s1", scanned_at=ts)]
    # s2 pushed 3 hours ago with 60-min cadence → 3h > 2×60min = overdue
    sensors = [
        _sensor("s1", last_push_at=datetime(2026, 5, 25, 11, 55, 0), cadence_minutes=60),
        _sensor("s2", last_push_at=datetime(2026, 5, 25, 9, 0, 0), cadence_minutes=60),
    ]

    db_path, _ = _setup_real_db(tmp_path, eps, sensors)
    now = datetime(2026, 5, 25, 12, 30, 0)

    from quirk.db import get_session
    with get_session(db_path) as db:
        result = merge_scan(db, now=now)

    cw = result["coverage_warning"]
    assert cw is not None
    assert "s2" in cw["missing_sensors"]


def test_coverage_warning_null_when_current(tmp_path):
    """MERGE-04: all sensors within 2×cadence → coverage_warning is None."""
    from quirk.merge.scan import merge_scan

    ts = datetime(2026, 5, 25, 12, 0, 0)
    eps = [
        _tls_ep(host="10.0.1.1", sensor_id="s1", scanned_at=ts),
        _tls_ep(host="10.0.2.1", sensor_id="s2", scanned_at=ts),
    ]
    sensors = [
        # Both pushed recently (within 2×60-min cadence of now=12:30)
        _sensor("s1", last_push_at=datetime(2026, 5, 25, 12, 20, 0), cadence_minutes=60),
        _sensor("s2", last_push_at=datetime(2026, 5, 25, 12, 25, 0), cadence_minutes=60),
    ]

    db_path, _ = _setup_real_db(tmp_path, eps, sensors)
    now = datetime(2026, 5, 25, 12, 30, 0)

    from quirk.db import get_session
    with get_session(db_path) as db:
        result = merge_scan(db, now=now)

    assert result["coverage_warning"] is None


# ---------------------------------------------------------------------------
# MERGE-05: source endpoint scanned_at is NOT rewritten by merge_scan
# ---------------------------------------------------------------------------

def test_scanned_at_preserved(tmp_path):
    """MERGE-05: merge_scan must NOT mutate source CryptoEndpoint.scanned_at."""
    from quirk.merge.scan import merge_scan

    original_ts = datetime(2026, 5, 25, 10, 0, 0)
    eps = [
        _tls_ep(host="10.0.1.1", sensor_id="s1", scanned_at=original_ts),
        _tls_ep(host="10.0.2.1", sensor_id="s2", scanned_at=original_ts),
    ]
    sensors = [
        _sensor("s1", last_push_at=datetime(2026, 5, 25, 9, 55, 0), cadence_minutes=60),
        _sensor("s2", last_push_at=datetime(2026, 5, 25, 9, 55, 0), cadence_minutes=60),
    ]

    db_path, engine = _setup_real_db(tmp_path, eps, sensors)
    now = datetime(2026, 5, 25, 12, 30, 0)

    from quirk.db import get_session
    with get_session(db_path) as db:
        merge_scan(db, now=now)

    # Re-query the source rows and check scanned_at is unchanged
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False,
                           expire_on_commit=False)
    with Session() as verify_db:
        s1_eps = verify_db.query(CryptoEndpoint).filter(
            CryptoEndpoint.host == "10.0.1.1"
        ).all()
        s2_eps = verify_db.query(CryptoEndpoint).filter(
            CryptoEndpoint.host == "10.0.2.1"
        ).all()

    for ep in s1_eps + s2_eps:
        assert ep.scanned_at == original_ts, (
            f"scanned_at mutated: expected {original_ts}, got {ep.scanned_at}"
        )


# ---------------------------------------------------------------------------
# Pitfall 4 / T-110-03: empty union must not silently return score 100
# ---------------------------------------------------------------------------

def test_empty_union_guarded(tmp_path):
    """Pitfall 4 / T-110-03: no enrolled sensors, no local rows → coverage_warning."""
    from quirk.merge.scan import merge_scan

    db_path, _ = _setup_real_db(tmp_path, endpoints=[], sensors=[])
    now = datetime(2026, 5, 25, 12, 30, 0)

    from quirk.db import get_session
    with get_session(db_path) as db:
        result = merge_scan(db, now=now)

    cw = result["coverage_warning"]
    assert cw is not None, "Empty union must produce a coverage_warning, not a clean score"
    # Should not silently return 100 (complete) with no data
    # A score of 100 with no endpoints is misleading
    assert result["endpoint_count"] == 0


# ---------------------------------------------------------------------------
# Persistence: merge_runs row is written
# ---------------------------------------------------------------------------

def test_merge_run_persisted(tmp_path):
    """merge_scan() persists a MergeRun row with correct fields."""
    from quirk.merge.scan import merge_scan

    ts = datetime(2026, 5, 25, 12, 0, 0)
    eps = [_tls_ep(host="10.0.1.1", sensor_id="s1", scanned_at=ts)]
    sensors = [_sensor("s1", last_push_at=datetime(2026, 5, 25, 11, 55, 0), cadence_minutes=60)]

    db_path, engine = _setup_real_db(tmp_path, eps, sensors)
    now = datetime(2026, 5, 25, 12, 30, 0)

    from quirk.db import get_session
    with get_session(db_path) as db:
        result = merge_scan(db, now=now)

    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False,
                           expire_on_commit=False)
    with Session() as verify_db:
        row = verify_db.query(MergeRun).filter(
            MergeRun.scan_id == result["scan_id"]
        ).first()

    assert row is not None, "MergeRun row should have been persisted"
    assert row.endpoint_count >= 0
    assert row.sensor_count >= 0
    assert row.merged_at is not None


# ---------------------------------------------------------------------------
# CR-01: CBOM artifact is written to disk when output_dir is supplied
# ---------------------------------------------------------------------------

def test_cbom_artifact_written_on_merge_run(tmp_path):
    """CR-01: merge_scan() must write the CBOM artifacts to disk and return
    cbom_json_path / cbom_xml_path in the result dict.
    """
    from quirk.merge.scan import merge_scan

    ts = datetime(2026, 5, 25, 12, 0, 0)
    eps = [_tls_ep(host="10.0.1.1", sensor_id="s1", scanned_at=ts)]
    sensors = [_sensor("s1", last_push_at=datetime(2026, 5, 25, 11, 55, 0), cadence_minutes=60)]

    db_path, _ = _setup_real_db(tmp_path, eps, sensors)
    now = datetime(2026, 5, 25, 12, 30, 0)
    out_dir = str(tmp_path / "cbom_out")
    os.makedirs(out_dir, exist_ok=True)

    from quirk.db import get_session
    with get_session(db_path) as db:
        result = merge_scan(db, now=now, output_dir=out_dir)

    # Result dict must expose paths
    assert "cbom_json_path" in result, "result must have cbom_json_path key"
    assert "cbom_xml_path" in result, "result must have cbom_xml_path key"
    assert result["cbom_json_path"] is not None, "cbom_json_path must be set when output_dir supplied"
    assert result["cbom_xml_path"] is not None, "cbom_xml_path must be set when output_dir supplied"

    # Files must exist on disk
    assert os.path.isfile(result["cbom_json_path"]), (
        f"CBOM JSON file not found at {result['cbom_json_path']}"
    )
    assert os.path.isfile(result["cbom_xml_path"]), (
        f"CBOM XML file not found at {result['cbom_xml_path']}"
    )


def test_cbom_paths_none_without_output_dir(tmp_path):
    """CR-01: when output_dir is not supplied, cbom paths in result dict are None."""
    from quirk.merge.scan import merge_scan

    ts = datetime(2026, 5, 25, 12, 0, 0)
    eps = [_tls_ep(host="10.0.1.1", sensor_id="s1", scanned_at=ts)]
    sensors = [_sensor("s1", last_push_at=datetime(2026, 5, 25, 11, 55, 0), cadence_minutes=60)]

    db_path, _ = _setup_real_db(tmp_path, eps, sensors)
    now = datetime(2026, 5, 25, 12, 30, 0)

    from quirk.db import get_session
    with get_session(db_path) as db:
        result = merge_scan(db, now=now)  # no output_dir

    assert result.get("cbom_json_path") is None
    assert result.get("cbom_xml_path") is None


# ---------------------------------------------------------------------------
# DIST-01 / CD-05 (Phase 125): same-second scanned_at tiebreak
# ---------------------------------------------------------------------------

def _union_rows(tmp_path, eps, sensors, pushes):
    """Seed Sensor, SensorPush and endpoint rows; return [(sensor_id, host, id)] twice."""
    from quirk.models import SensorPush
    from quirk.merge.scan import _assemble_union
    from quirk.db import get_session

    db_path, _ = _setup_real_db(tmp_path, [], sensors)
    with get_session(db_path) as db:
        for sid, pid, rec in pushes:
            db.add(SensorPush(payload_id=pid, sensor_id=sid, received_at=rec))
        db.commit()
        for ep in eps:
            db.add(ep)
        db.commit()
    out = []
    with get_session(db_path) as db:
        for _ in range(2):
            out.append([(e.sensor_id, e.host, e.id) for e in _assemble_union(db)])
    return out


def _tag(host, sid, pid, T):
    return _tls_ep(host=host, sensor_id=sid, push_payload_id=pid, scanned_at=T)


def test_union_keeps_every_endpoint_of_latest_push(tmp_path):
    """FIND-13 (D-13): all hosts of the latest push kept, older push excluded;
    two calls return the identical ordered list (CD-05 determinism)."""
    T = datetime(2026, 6, 1, 12, 0, 0)
    eps = [_tag("x", "s1", "p1", T), _tag("y", "s1", "p1", T)] + [
        _tag(h, "s1", "p2", T + timedelta(hours=1)) for h in ("a", "b", "c")
    ]
    first, second = _union_rows(
        tmp_path, eps, [_sensor("s1", T)],
        [("s1", "p1", T), ("s1", "p2", T + timedelta(hours=1))],
    )
    assert sorted(h for _, h, _ in first) == ["a", "b", "c"]
    assert first == second
    assert [i for _, _, i in first] == sorted(i for _, _, i in first)


def test_same_received_at_resolves_to_higher_pushid(tmp_path):
    T = datetime(2026, 6, 1, 12, 0, 0)
    eps = [_tag("old", "s1", "p1", T), _tag("new", "s1", "p2", T)]
    first, _ = _union_rows(
        tmp_path, eps, [_sensor("s1", T)], [("s1", "p1", T), ("s1", "p2", T)],
    )
    assert [h for _, h, _ in first] == ["new"]


def test_empty_latest_push_contributes_zero_rows(tmp_path):
    T = datetime(2026, 6, 1, 12, 0, 0)
    eps = [_tag("old", "s1", "p1", T)]
    first, _ = _union_rows(
        tmp_path, eps, [_sensor("s1", T)],
        [("s1", "p1", T), ("s1", "p2", T + timedelta(hours=1))],
    )
    assert first == []


def test_legacy_sensor_same_second_rows_all_kept(tmp_path):
    """Untagged (pre-Phase-229) rows fall back to the session bracket; the old
    DIST-01 same-second shape now keeps all rows, in stable id order."""
    T = datetime(2026, 6, 1, 12, 0, 0)
    eps = [
        _tls_ep(host="host-a.example", sensor_id="s1", scanned_at=T),
        _tls_ep(host="host-b.example", sensor_id="s1", scanned_at=T),
        _tls_ep(host="stale.example", sensor_id="s1", scanned_at=T - timedelta(hours=2)),
    ]
    first, second = _union_rows(tmp_path, eps, [_sensor("s1", T)], [])
    assert [h for _, h, _ in first] == ["host-a.example", "host-b.example"]
    assert first == second


def test_legacy_sensor_with_only_null_scanned_at_is_skipped_not_crashed(tmp_path):
    """229-REVIEW WR-01: an untagged sensor whose every row has scanned_at NULL
    used to raise TypeError (None - timedelta). It contributes zero rows; other
    sensors are unaffected."""
    T = datetime(2026, 6, 1, 12, 0, 0)
    eps = [
        _tls_ep(host="null-a", sensor_id="s0", scanned_at=None),
        _tls_ep(host="null-b", sensor_id="s0", scanned_at=None),
        _tag("s1-real", "s1", "p1", T),
        _tls_ep(host="legacy", sensor_id="s2", scanned_at=T),
    ]
    first, second = _union_rows(
        tmp_path, eps, [_sensor("s0", T), _sensor("s1", T), _sensor("s2", T)],
        [("s1", "p1", T)],
    )
    assert [(s, h) for s, h, _ in first] == [("s1", "s1-real"), ("s2", "legacy")]
    assert first == second


def test_forged_tag_does_not_leak_across_sensors(tmp_path):
    T = datetime(2026, 6, 1, 12, 0, 0)
    eps = [
        _tag("s1-real", "s1", "p1", T),
        _tag("s2-forged", "s2", "p1", T),  # s2 row carrying s1's payload id
        _tag("s2-real", "s2", "p2", T),
    ]
    first, _ = _union_rows(
        tmp_path, eps, [_sensor("s1", T), _sensor("s2", T)],
        [("s1", "p1", T), ("s2", "p2", T)],
    )
    assert [(s, h) for s, h, _ in first] == [("s1", "s1-real"), ("s2", "s2-real")]


# ---------------------------------------------------------------------------
# Phase 228 (XSURF-07, D-10): merge score derives findings over the union
# ---------------------------------------------------------------------------

def _ceiling_endpoints():
    """4 sensors, one TLS row each (one per sensor_id so the union keeps all);
    sensor s0's cert is expired (CRITICAL)."""
    eps = []
    for i in range(4):
        eps.append(_tls_ep(
            host=f"h{i}.example", protocol="TLS", sensor_id=f"s{i}",
            cert_not_after=datetime(2020, 1, 1) if i == 0 else None,
            scanned_at=datetime(2026, 5, 25, 12, 0, 0),
        ))
    return eps


def _ceiling_sensors():
    return [_sensor(f"s{i}", datetime(2026, 5, 25, 12, 0, 0)) for i in range(4)]


# Scoring 4.0 (Phase 234): 27 -> 31, still capped <= 34 (POOR) by the CRITICAL ceiling.
PINNED_MERGE_CEILING_SCORE = 31


def test_merge_score_applies_critical_ceiling(tmp_path):
    from quirk.db import get_session
    from quirk.engine.findings_evaluator import derive_report_findings
    from quirk.intelligence.evidence import build_evidence_summary
    from quirk.intelligence.scoring import compute_readiness_score
    from quirk.merge.scan import merge_scan, _assemble_union

    db_path, _ = _setup_real_db(tmp_path, _ceiling_endpoints(), _ceiling_sensors())
    with get_session(db_path) as db:
        union = _assemble_union(db)
        assert len(union) == 4
        result = merge_scan(db, stale_days=30)
        expected = compute_readiness_score(
            build_evidence_summary(union, derive_report_findings(union)),
            profile="balanced",
        )["score"]
    assert result["score"] == expected
    assert result["score"] <= 34
    assert result["rating"] == "POOR"
    assert result["score"] == PINNED_MERGE_CEILING_SCORE


def test_merge_cli_prints_band_at_or_below_floor(tmp_path, capsys):
    import argparse
    import re

    from quirk.cli.sensor_cmd import _cmd_merge

    db_path, _ = _setup_real_db(tmp_path, _ceiling_endpoints(), _ceiling_sensors())
    with pytest.raises(SystemExit) as exc:
        _cmd_merge(argparse.Namespace(db=db_path, stale_days=30))
    assert exc.value.code == 0
    out = capsys.readouterr().out
    m = re.search(r"Score: (\d+) \((\w+)\)", out)
    assert m, out
    assert m.group(2) == "POOR"
    assert int(m.group(1)) <= 34


def test_merge_uses_supplied_deriver(tmp_path):
    from quirk.db import get_session
    from quirk.merge.scan import merge_scan

    db_path, _ = _setup_real_db(tmp_path, _ceiling_endpoints(), _ceiling_sensors())
    seen = []

    def _deriver(eps):
        seen.append(len(list(eps)))
        return []

    with get_session(db_path) as db:
        result = merge_scan(db, stale_days=30, findings_deriver=_deriver)
    assert seen == [4]
    assert result["score"] > 34


def _divergent_union_endpoints():
    """3 healthy TLS rows plus one Kerberos weak-etype row: the dashboard and report
    pipelines disagree on this union (the Kerberos finding is dashboard-only)."""
    eps = [
        _tls_ep(host=f"h{i}.example", protocol="TLS", sensor_id=f"s{i}",
                scanned_at=datetime(2026, 5, 25, 12, 0, 0))
        for i in range(3)
    ]
    eps.append(_tls_ep(
        host="dc.example", port=88, protocol="KERBEROS", sensor_id="s3",
        tls_version=None, cipher_suite=None, cert_pubkey_alg="rc4-hmac",
        cert_pubkey_size=None, cert_sig_alg=None, cert_subject=None, cert_issuer=None,
        service_detail="etype:23:rc4-hmac:CRITICAL",
        scanned_at=datetime(2026, 5, 25, 12, 0, 0),
    ))
    return eps


def test_persisted_merge_score_is_independent_of_entry_point(tmp_path):
    """228-REVIEW CR-01: `quirk sensor merge` and the dashboard auto-merge persist the
    same MergeRun.score for the same union (run_auto_merge mirrors _cmd_merge, D-02)."""
    import argparse

    from quirk.cli.sensor_cmd import _cmd_merge
    from quirk.dashboard.api.routes.scan import derive_dashboard_scoring_findings
    from quirk.dashboard.api.routes.sensor import run_auto_merge
    from quirk.db import get_session
    from quirk.engine.findings_evaluator import derive_report_findings
    from quirk.merge.scan import _assemble_union

    cli_dir, auto_dir = tmp_path / "cli", tmp_path / "auto"
    cli_dir.mkdir()
    auto_dir.mkdir()
    cli_db, _ = _setup_real_db(cli_dir, _divergent_union_endpoints(), _ceiling_sensors())
    auto_db, _ = _setup_real_db(auto_dir, _divergent_union_endpoints(), _ceiling_sensors())

    # Non-vacuity: the two pipelines must disagree on this union, or the test proves nothing.
    with get_session(cli_db) as db:
        union = _assemble_union(db)
        dash = compute_readiness_score(
            build_evidence_summary(union, derive_dashboard_scoring_findings(union)))["score"]
        rep = compute_readiness_score(
            build_evidence_summary(union, derive_report_findings(union)))["score"]
    assert dash != rep

    with pytest.raises(SystemExit):
        _cmd_merge(argparse.Namespace(db=cli_db, stale_days=30))
    run_auto_merge(auto_db, str(tmp_path / "absent-config.yaml"))

    scores = []
    for path in (cli_db, auto_db):
        with get_session(path) as db:
            row = db.query(MergeRun).order_by(MergeRun.merged_at.desc()).first()
            assert row is not None, f"no MergeRun persisted in {path}"
            scores.append(row.score)
    assert scores[0] == scores[1] == rep
