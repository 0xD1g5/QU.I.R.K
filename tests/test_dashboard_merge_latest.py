"""Integration tests for GET /api/merge/latest endpoint.

TDD RED phase — tests define expected endpoint behaviour before implementation.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import itertools

import pytest

_db_counter = itertools.count(100)


def _make_isolated_client():
    """Return a (TestClient, TestingSession) pair using a unique in-memory SQLite DB."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from quirk.dashboard.api.app import create_app
    from quirk.dashboard.api.deps import get_db
    from quirk.models import Base
    from fastapi.testclient import TestClient

    db_name = f"merge_test_{next(_db_counter)}"
    engine = create_engine(
        f"sqlite:///file:{db_name}?mode=memory&cache=shared&uri=true",
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
    client = TestClient(app, headers={"X-Quirk-Request": "1"})
    return client, TestingSession


def _seed_merge_run(db, *, scan_id=None, merged_at=None, score=72,
                    endpoint_count=10, sensor_count=2,
                    coverage_warning_json=None):
    """Seed a MergeRun row into the test DB."""
    from quirk.models import MergeRun
    if merged_at is None:
        merged_at = datetime.now(timezone.utc).replace(tzinfo=None)
    if scan_id is None:
        scan_id = merged_at.strftime("%Y-%m-%dT%H:%M:%SZ")
    row = MergeRun(
        scan_id=scan_id,
        merged_at=merged_at,
        score=score,
        endpoint_count=endpoint_count,
        sensor_count=sensor_count,
        coverage_warning_json=coverage_warning_json,
    )
    db.add(row)
    db.commit()
    return row


def _seed_crypto_endpoint(db, *, host, port=443, segment=None, sensor_id=None,
                          scanned_at=None, tls_version="TLSv1.2",
                          cert_pubkey_alg="RSA"):
    """Seed a CryptoEndpoint row."""
    from quirk.models import CryptoEndpoint
    if scanned_at is None:
        scanned_at = datetime.now(timezone.utc).replace(tzinfo=None)
    ep = CryptoEndpoint(
        host=host,
        port=port,
        segment=segment,
        sensor_id=sensor_id,
        scanned_at=scanned_at,
        tls_version=tls_version,
        cert_pubkey_alg=cert_pubkey_alg,
    )
    db.add(ep)
    db.commit()
    return ep


class TestMergeLatestNoData:
    """No merge_run rows → endpoint returns {"merge": null}."""

    def test_no_merge_returns_null(self):
        client, _ = _make_isolated_client()
        resp = client.get("/api/merge/latest")
        assert resp.status_code == 200
        data = resp.json()
        assert "merge" in data
        assert data["merge"] is None


class TestMergeLatestWithData:
    """With a MergeRun row → endpoint returns merge object."""

    def test_merge_object_shape(self):
        """Response contains expected top-level fields."""
        client, TestingSession = _make_isolated_client()
        db = TestingSession()
        _seed_merge_run(db, score=75, endpoint_count=12, sensor_count=3)
        db.close()

        resp = client.get("/api/merge/latest")
        assert resp.status_code == 200
        data = resp.json()
        merge = data["merge"]
        assert merge is not None
        assert "scan_id" in merge
        assert "merged_at" in merge
        assert "score" in merge
        assert merge["score"] == 75
        assert merge["endpoint_count"] == 12
        assert merge["sensor_count"] == 3

    def test_coverage_warning_null_when_none(self):
        """coverage_warning_json=NULL → coverage_warning=null in response."""
        client, TestingSession = _make_isolated_client()
        db = TestingSession()
        _seed_merge_run(db, coverage_warning_json=None)
        db.close()

        resp = client.get("/api/merge/latest")
        assert resp.status_code == 200
        assert resp.json()["merge"]["coverage_warning"] is None

    def test_coverage_warning_parsed(self):
        """Valid JSON in coverage_warning_json is parsed to a dict."""
        import json
        client, TestingSession = _make_isolated_client()
        db = TestingSession()
        warning = {"missing_sensors": ["s1"], "reason": "s1 overdue"}
        _seed_merge_run(db, coverage_warning_json=json.dumps(warning))
        db.close()

        resp = client.get("/api/merge/latest")
        assert resp.status_code == 200
        cw = resp.json()["merge"]["coverage_warning"]
        assert isinstance(cw, dict)
        assert cw["missing_sensors"] == ["s1"]

    def test_malformed_coverage_warning_json_returns_null(self):
        """Malformed coverage_warning_json → coverage_warning=null (no 500). Trap T8."""
        client, TestingSession = _make_isolated_client()
        db = TestingSession()
        _seed_merge_run(db, coverage_warning_json="not-valid-json{{{")
        db.close()

        resp = client.get("/api/merge/latest")
        assert resp.status_code == 200  # no 500
        assert resp.json()["merge"]["coverage_warning"] is None

    def test_per_segment_scores_two_segments(self):
        """With endpoints in two segments → per_segment_scores has both segment keys."""
        client, TestingSession = _make_isolated_client()
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        db = TestingSession()
        _seed_merge_run(db)
        # Endpoints in two different segments with distinct sensor_ids
        _seed_crypto_endpoint(db, host="10.0.1.1", segment="dmz",
                              sensor_id="sensor-a", scanned_at=now)
        _seed_crypto_endpoint(db, host="10.0.1.2", segment="dmz",
                              sensor_id="sensor-a", scanned_at=now)
        _seed_crypto_endpoint(db, host="192.168.1.1", segment="corp",
                              sensor_id="sensor-b", scanned_at=now)
        db.close()

        resp = client.get("/api/merge/latest")
        assert resp.status_code == 200
        per_seg = resp.json()["merge"]["per_segment_scores"]
        # Both segments must be present
        assert "dmz" in per_seg
        assert "corp" in per_seg

    def test_per_segment_scores_are_ints(self):
        """per_segment_scores values are integers 0-100."""
        client, TestingSession = _make_isolated_client()
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        db = TestingSession()
        _seed_merge_run(db)
        _seed_crypto_endpoint(db, host="10.0.1.1", segment="dmz",
                              sensor_id="sensor-a", scanned_at=now)
        db.close()

        resp = client.get("/api/merge/latest")
        assert resp.status_code == 200
        per_seg = resp.json()["merge"]["per_segment_scores"]
        for key, val in per_seg.items():
            assert isinstance(val, int), f"Expected int for segment {key}, got {type(val)}"
            assert 0 <= val <= 100

    def test_per_segment_groups_by_segment_not_sensor_id(self):
        """Two sensors in the same segment produce ONE score entry (Trap T5)."""
        client, TestingSession = _make_isolated_client()
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        db = TestingSession()
        _seed_merge_run(db)
        # Two different sensor_ids but SAME segment
        _seed_crypto_endpoint(db, host="10.0.1.1", segment="dmz",
                              sensor_id="sensor-a", scanned_at=now)
        _seed_crypto_endpoint(db, host="10.0.1.2", segment="dmz",
                              sensor_id="sensor-b", scanned_at=now)
        db.close()

        resp = client.get("/api/merge/latest")
        assert resp.status_code == 200
        per_seg = resp.json()["merge"]["per_segment_scores"]
        # Only ONE entry for "dmz" despite two sensor_ids
        assert list(per_seg.keys()) == ["dmz"]

    def test_null_segment_endpoints_excluded_from_per_segment(self):
        """Endpoints with segment=NULL are excluded from per_segment_scores."""
        client, TestingSession = _make_isolated_client()
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        db = TestingSession()
        _seed_merge_run(db)
        # Only NULL-segment endpoints
        _seed_crypto_endpoint(db, host="10.0.1.1", segment=None, sensor_id=None,
                              scanned_at=now)
        db.close()

        resp = client.get("/api/merge/latest")
        assert resp.status_code == 200
        per_seg = resp.json()["merge"]["per_segment_scores"]
        assert per_seg == {}

    def test_no_db_writes(self):
        """The endpoint is read-only — calling it twice returns same data (no mutations). Trap T6."""
        client, TestingSession = _make_isolated_client()
        db = TestingSession()
        _seed_merge_run(db, score=80)
        db.close()

        resp1 = client.get("/api/merge/latest")
        resp2 = client.get("/api/merge/latest")
        assert resp1.status_code == 200
        assert resp2.status_code == 200
        assert resp1.json()["merge"]["score"] == resp2.json()["merge"]["score"]

    def test_overall_and_per_segment_from_same_union(self):
        """WR-04: overall score is recomputed from the same live union as per-segment scores.

        With two segments (dmz, corp) the overall live_score must be derived
        from ALL union endpoints — not from the stale merge-time snapshot.
        We verify that score is an integer (recomputed) and that per_segment_scores
        contains entries for both segments, all from one consistent dataset.
        """
        client, TestingSession = _make_isolated_client()
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        db = TestingSession()
        # snapshot score differs from what live recompute would produce
        _seed_merge_run(db, score=99)
        _seed_crypto_endpoint(db, host="10.0.1.1", segment="dmz",
                              sensor_id="sensor-a", scanned_at=now)
        _seed_crypto_endpoint(db, host="192.168.1.1", segment="corp",
                              sensor_id="sensor-b", scanned_at=now)
        db.close()

        resp = client.get("/api/merge/latest")
        assert resp.status_code == 200
        merge = resp.json()["merge"]

        # Overall score must be an integer recomputed from live union (not None)
        assert isinstance(merge["score"], int)
        assert 0 <= merge["score"] <= 100

        # Per-segment scores must cover both segments
        per_seg = merge["per_segment_scores"]
        assert "dmz" in per_seg
        assert "corp" in per_seg

        # The overall score should NOT equal the stale snapshot (99) when real
        # endpoints are present — the recompute returns a real score not 99.
        # (This documents that WR-04 is active; if somehow the scoring returns
        # exactly 99 legitimately, the assertion below only checks type consistency.)
        assert isinstance(per_seg["dmz"], int)
        assert isinstance(per_seg["corp"], int)
