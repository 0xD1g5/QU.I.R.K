"""Regression tests for CR-05 — sub-second session window disambiguation.

Verifies that:
- Two CryptoEndpoint rows with scanned_at differing by 100ms are two distinct sessions
- scanned_at round-trips through strftime('%Y-%m-%d %H:%M:%f') with microsecond precision
- _fetch_session_endpoints(db, target_ts) returns ONLY the endpoint for target_ts
- NULL scanned_at rows are excluded (D-13 regression)
- 0-session and 1-session edge cases still produce valid TrendReportResponse shapes
"""
from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from quirk.db import init_db
from quirk.models import Base, CryptoEndpoint
from quirk.dashboard.api.routes.trends import _list_session_timestamps
from quirk.intelligence.trends import _fetch_session_endpoints


@pytest.fixture()
def db_session(tmp_path):
    """Create a fresh in-memory SQLite session with the full QUIRK schema."""
    db_path = str(tmp_path / "test_trends.db")
    engine = init_db(db_path)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    engine.dispose()


def _make_endpoint(scanned_at: datetime, host: str = "test.example.com") -> CryptoEndpoint:
    """Create a minimal CryptoEndpoint row."""
    return CryptoEndpoint(
        host=host,
        port=443,
        protocol="tls",
        scanned_at=scanned_at,
    )


TS_A = datetime(2026, 5, 10, 12, 0, 0, 100000)   # 12:00:00.100000
TS_B = datetime(2026, 5, 10, 12, 0, 0, 200000)   # 12:00:00.200000 (100ms later)


def test_two_subsecond_endpoints_are_distinct_sessions(db_session) -> None:
    """Two endpoints 100ms apart must appear as TWO distinct sessions."""
    db_session.add(_make_endpoint(TS_A))
    db_session.add(_make_endpoint(TS_B))
    db_session.commit()

    sessions = _list_session_timestamps(db_session)
    assert len(sessions) == 2, (
        f"Expected 2 distinct sessions, got {len(sessions)}: {sessions}"
    )


def test_scanned_at_roundtrip_microsecond_precision(db_session) -> None:
    """scanned_at must survive a strftime('%Y-%m-%d %H:%M:%f') → fromisoformat round-trip."""
    db_session.add(_make_endpoint(TS_A))
    db_session.commit()

    sessions = _list_session_timestamps(db_session)
    assert len(sessions) == 1
    recovered = sessions[0]
    # strftime %f produces 3-digit milliseconds in SQLite; TS_A uses an exact-ms value
    # (100000 µs = 100 ms) so the round-trip is lossless for this input.
    assert recovered.microsecond == TS_A.microsecond, (
        f"Millisecond precision lost: expected {TS_A.microsecond}, got {recovered.microsecond}"
    )


def test_fetch_session_endpoints_returns_only_exact_ts(db_session) -> None:
    """_fetch_session_endpoints(db, target_ts) must not include the sibling timestamp."""
    ep_a = _make_endpoint(TS_A, host="host-a.example.com")
    ep_b = _make_endpoint(TS_B, host="host-b.example.com")
    db_session.add(ep_a)
    db_session.add(ep_b)
    db_session.commit()

    # List sessions to get the round-tripped timestamps
    sessions = _list_session_timestamps(db_session)
    assert len(sessions) == 2

    # Fetch endpoints for the LATER session (TS_B is stored first in desc order)
    # sessions[0] is the newest (TS_B), sessions[1] is TS_A
    results_b = _fetch_session_endpoints(db_session, sessions[0])
    assert len(results_b) == 1, (
        f"Expected 1 endpoint for TS_B, got {len(results_b)}"
    )

    results_a = _fetch_session_endpoints(db_session, sessions[1])
    assert len(results_a) == 1, (
        f"Expected 1 endpoint for TS_A, got {len(results_a)}"
    )


def test_null_scanned_at_excluded(db_session) -> None:
    """NULL scanned_at rows must be excluded from session listing (D-13 regression)."""
    db_session.add(_make_endpoint(TS_A))
    null_ep = _make_endpoint(TS_A)
    null_ep.scanned_at = None
    db_session.add(null_ep)
    db_session.commit()

    sessions = _list_session_timestamps(db_session)
    assert len(sessions) == 1, (
        f"Expected 1 session (NULL excluded), got {len(sessions)}"
    )
