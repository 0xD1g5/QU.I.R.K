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
    eps = [_tls_ep(host="10.0.1.1", sensor_id="s1", scanned_at=ts)]
    # s2 is enrolled but has never pushed
    sensors = [
        _sensor("s1", last_push_at=datetime(2026, 5, 25, 11, 55, 0), cadence_minutes=60),
        _sensor("s2", last_push_at=None, cadence_minutes=60),  # never pushed
    ]

    db_path, _ = _setup_real_db(tmp_path, eps, sensors)
    now = datetime(2026, 5, 25, 12, 30, 0)

    from quirk.db import get_session
    with get_session(db_path) as db:
        result = merge_scan(db, now=now)

    cw = result["coverage_warning"]
    assert cw is not None, "Expected coverage_warning for never-pushed sensor"
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
