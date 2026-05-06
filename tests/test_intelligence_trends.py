"""Tests for Phase 31 compute_trend_report() — TREND-01/02/03 + D-03/D-04/D-05/D-13.

These tests are RED at creation: quirk/intelligence/trends.py is not yet implemented.
Wave 1 (Plan 02) implements compute_trend_report() to make these tests pass.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from quirk.models import Base, CryptoEndpoint
from quirk.intelligence.trends import compute_trend_report


@pytest.fixture
def db():
    """In-memory SQLite session for trend unit tests."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


def _make_ep(
    db,
    host: str,
    port: int,
    protocol: str,
    severity: str,
    scanned_at: Optional[datetime] = None,
    scan_error: Optional[str] = None,
) -> CryptoEndpoint:
    """Create and persist a CryptoEndpoint with the minimum fields the trend
    module reads. Returns the persisted instance after commit."""
    ep = CryptoEndpoint(
        host=host,
        port=port,
        protocol=protocol,
        severity=severity,
        scanned_at=scanned_at,
        scan_error=scan_error,
    )
    db.add(ep)
    db.commit()
    return ep


PREV_TS = datetime(2026, 4, 25, 9, 0, 0)
CURR_TS = datetime(2026, 4, 26, 9, 0, 0)


def test_score_delta_computed(db):
    """TREND-01: score_delta is non-null when two sessions exist."""
    # Seed 3 endpoints in PREV_TS session
    _make_ep(db, "a.example", 443, "TLS", "HIGH", scanned_at=PREV_TS)
    _make_ep(db, "b.example", 443, "TLS", "MEDIUM", scanned_at=PREV_TS)
    _make_ep(db, "c.example", 22, "SSH", "LOW", scanned_at=PREV_TS)
    # Seed 3 endpoints in CURR_TS session — same hosts, but one severity dropped
    _make_ep(db, "a.example", 443, "TLS", "MEDIUM", scanned_at=CURR_TS)  # was HIGH
    _make_ep(db, "b.example", 443, "TLS", "MEDIUM", scanned_at=CURR_TS)
    _make_ep(db, "c.example", 22, "SSH", "LOW", scanned_at=CURR_TS)

    report = compute_trend_report(CURR_TS, PREV_TS, db)

    assert report.score_delta is not None
    assert isinstance(report.score_delta, int)


def test_single_session_null_delta(db):
    """TREND-01 / D-06: score_delta is None when only one session exists."""
    _make_ep(db, "a.example", 443, "TLS", "HIGH", scanned_at=CURR_TS)
    _make_ep(db, "b.example", 22, "SSH", "MEDIUM", scanned_at=CURR_TS)

    report = compute_trend_report(CURR_TS, None, db)

    assert report.score_delta is None
    assert report.previous_session_ts is None
    assert report.previous_score is None
    assert report.new_high == 0
    assert report.new_medium == 0
    assert report.new_low == 0
    assert report.resolved_high == 0
    assert report.resolved_medium == 0
    assert report.resolved_low == 0


def test_new_findings_counted(db):
    """TREND-02: new findings counted correctly by severity."""
    # Seed 1 endpoint at PREV_TS
    _make_ep(db, "a.example", 443, "TLS", "HIGH", scanned_at=PREV_TS)
    # Seed 3 endpoints at CURR_TS: same plus 2 new
    _make_ep(db, "a.example", 443, "TLS", "HIGH", scanned_at=CURR_TS)
    _make_ep(db, "b.example", 443, "TLS", "HIGH", scanned_at=CURR_TS)   # new
    _make_ep(db, "c.example", 22, "SSH", "MEDIUM", scanned_at=CURR_TS)  # new

    report = compute_trend_report(CURR_TS, PREV_TS, db)

    assert report.new_high == 1    # b.example
    assert report.new_medium == 1  # c.example
    assert report.new_low == 0


def test_resolved_findings_counted(db):
    """TREND-03: resolved findings counted correctly by severity."""
    # Seed 3 endpoints at PREV_TS
    _make_ep(db, "a.example", 443, "TLS", "HIGH", scanned_at=PREV_TS)
    _make_ep(db, "b.example", 443, "TLS", "MEDIUM", scanned_at=PREV_TS)
    _make_ep(db, "c.example", 22, "SSH", "LOW", scanned_at=PREV_TS)
    # Seed 1 endpoint at CURR_TS: only a.example remains
    _make_ep(db, "a.example", 443, "TLS", "HIGH", scanned_at=CURR_TS)

    report = compute_trend_report(CURR_TS, PREV_TS, db)

    assert report.resolved_high == 0
    assert report.resolved_medium == 1  # b.example gone
    assert report.resolved_low == 1     # c.example gone


def test_severity_change_surfaces(db):
    """D-03: severity change surfaces as OLD resolved + NEW new."""
    # Seed at PREV_TS: HIGH finding
    _make_ep(db, "a.example", 443, "TLS", "HIGH", scanned_at=PREV_TS)
    # Seed at CURR_TS: same host/port/protocol but MEDIUM (severity downgraded)
    _make_ep(db, "a.example", 443, "TLS", "MEDIUM", scanned_at=CURR_TS)

    report = compute_trend_report(CURR_TS, PREV_TS, db)

    assert report.resolved_high == 1   # HIGH resolved
    assert report.new_medium == 1      # MEDIUM new


def test_scan_error_excluded_from_delta(db):
    """D-04: scan_error rows excluded from finding delta."""
    # Seed at PREV_TS: clean endpoint
    _make_ep(db, "a.example", 443, "TLS", "HIGH", scanned_at=PREV_TS, scan_error=None)
    # Seed at CURR_TS: same host but now has scan_error (host temporarily unreachable)
    _make_ep(
        db, "a.example", 443, "TLS", "HIGH",
        scanned_at=CURR_TS,
        scan_error="CONNECTION_REFUSED: port 443 unreachable",
    )

    report = compute_trend_report(CURR_TS, PREV_TS, db)

    # scan_error row in current must NOT cause the finding to appear resolved
    assert report.resolved_high == 0
    assert report.new_high == 0


def test_scan_error_counts_surfaced(db):
    """D-05: scan error counts tracked separately from finding delta."""
    # Seed at PREV_TS: 2 normal + 1 scan_error
    _make_ep(db, "a.example", 443, "TLS", "HIGH", scanned_at=PREV_TS)
    _make_ep(db, "b.example", 443, "TLS", "MEDIUM", scanned_at=PREV_TS)
    _make_ep(db, "err1.example", 443, "TLS", "HIGH", scanned_at=PREV_TS, scan_error="TIMEOUT: ...")
    # Seed at CURR_TS: 2 normal + 3 scan_errors
    _make_ep(db, "a.example", 443, "TLS", "HIGH", scanned_at=CURR_TS)
    _make_ep(db, "b.example", 443, "TLS", "MEDIUM", scanned_at=CURR_TS)
    _make_ep(db, "err1.example", 443, "TLS", "HIGH", scanned_at=CURR_TS, scan_error="CONNECTION_REFUSED: ...")
    _make_ep(db, "err2.example", 443, "TLS", "HIGH", scanned_at=CURR_TS, scan_error="CONNECTION_REFUSED: ...")
    _make_ep(db, "err3.example", 443, "TLS", "HIGH", scanned_at=CURR_TS, scan_error="CONNECTION_REFUSED: ...")

    report = compute_trend_report(CURR_TS, PREV_TS, db)

    assert report.scan_errors_new_count == 2       # 3 current - 1 previous = 2
    assert report.scan_errors_resolved_count == 0  # negative delta clamps to 0


def test_null_scanned_at_excluded(db):
    """D-13: NULL scanned_at rows excluded from session grouping."""
    # Seed 1 endpoint with scanned_at=None (simulates v4.2-era row)
    _make_ep(db, "legacy.example", 443, "TLS", "HIGH", scanned_at=None)
    # Seed normal endpoints for both sessions
    _make_ep(db, "a.example", 443, "TLS", "HIGH", scanned_at=PREV_TS)
    _make_ep(db, "a.example", 443, "TLS", "HIGH", scanned_at=CURR_TS)

    report = compute_trend_report(CURR_TS, PREV_TS, db)

    # legacy NULL row must not appear in either session set
    assert report.new_high == 0
    assert report.resolved_high == 0


def test_sample_arrays_shape(db):
    """TREND-02/TREND-03: sample arrays have correct shape with required attributes."""
    # Seed at PREV_TS: one endpoint that will be resolved
    _make_ep(db, "resolved.example", 443, "TLS", "HIGH", scanned_at=PREV_TS)
    # Seed at CURR_TS: one endpoint that is new
    _make_ep(db, "new.example", 443, "TLS", "MEDIUM", scanned_at=CURR_TS)

    report = compute_trend_report(CURR_TS, PREV_TS, db)

    assert len(report.new_findings_sample) >= 1
    assert len(report.resolved_findings_sample) >= 1

    for item in report.new_findings_sample:
        assert hasattr(item, "host")
        assert hasattr(item, "port")
        assert hasattr(item, "protocol")
        assert hasattr(item, "severity")

    for item in report.resolved_findings_sample:
        assert hasattr(item, "host")
        assert hasattr(item, "port")
        assert hasattr(item, "protocol")
        assert hasattr(item, "severity")


def test_sample_arrays_capped_at_5(db):
    """D-07: sample arrays capped at top 5; counts remain exact."""
    # Seed at CURR_TS: 7 distinct HIGH endpoints (all new — none in PREV_TS)
    for i in range(7):
        _make_ep(db, f"host{i}.example", 443 + i, "TLS", "HIGH", scanned_at=CURR_TS)
    # No endpoints at PREV_TS — all 7 are new

    report = compute_trend_report(CURR_TS, PREV_TS, db)

    assert len(report.new_findings_sample) == 5
    assert report.new_high == 7  # count is exact, sample is capped
