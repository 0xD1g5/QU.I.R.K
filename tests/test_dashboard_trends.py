"""Dashboard API integration tests for GET /api/trends — TREND-04 + D-06.

These tests are RED at creation: quirk/dashboard/api/routes/trends.py is not
yet registered with the FastAPI app. The first request returns 404. Wave 1
(Plan 02) registers the route and makes these tests pass.
"""
from __future__ import annotations

import pytest


def test_trends_endpoint_schema(dashboard_client):
    """TREND-04: GET /api/trends returns HTTP 200 with correct schema."""
    resp = dashboard_client.get("/api/trends")
    assert resp.status_code == 200
    data = resp.json()
    assert "current_session_ts" in data
    assert "previous_session_ts" in data
    assert "current_score" in data
    assert "previous_score" in data
    assert "score_delta" in data
    assert "new_high" in data
    assert "new_medium" in data
    assert "new_low" in data
    assert "resolved_high" in data
    assert "resolved_medium" in data
    assert "resolved_low" in data
    assert "scan_errors_new_count" in data
    assert "scan_errors_resolved_count" in data
    assert "new_findings_sample" in data
    assert "resolved_findings_sample" in data
    assert isinstance(data["new_findings_sample"], list)
    assert isinstance(data["resolved_findings_sample"], list)


def test_trends_single_session(dashboard_client):
    """D-06: GET /api/trends returns HTTP 200 with null delta when 0-1 sessions exist."""
    # Empty DB — fresh dashboard_client fixture; no rows seeded
    resp = dashboard_client.get("/api/trends")
    assert resp.status_code == 200
    data = resp.json()
    assert data["previous_session_ts"] is None
    assert data["score_delta"] is None
    assert data["new_high"] == 0
    assert data["new_medium"] == 0
    assert data["new_low"] == 0
    assert data["resolved_high"] == 0
    assert data["resolved_medium"] == 0
    assert data["resolved_low"] == 0
    assert data["new_findings_sample"] == []
    assert data["resolved_findings_sample"] == []


# ---------------------------------------------------------------------------
# UAT-31 / Phase 31 VERIFICATION: /api/trends flat wire format (seeded DB)
# Closes Phase 31 VERIFICATION row in .planning/STATE.md Deferred Items.
# Pattern: named shared-cache UUID URI (Pitfall 2 — dashboard_client fixture
# cannot seed). Distinct timestamps per Pitfall 5.
# ---------------------------------------------------------------------------

import uuid as _uuid_uat31
from datetime import datetime as _dt_uat31

from sqlalchemy import create_engine as _create_engine_uat31
from sqlalchemy.orm import sessionmaker as _sessionmaker_uat31
from fastapi.testclient import TestClient as _TestClient_uat31


_PREV_TS_UAT31 = _dt_uat31(2026, 4, 25, 9, 0, 0)
_CURR_TS_UAT31 = _dt_uat31(2026, 4, 26, 9, 0, 0)


def _make_uat31_client_and_session():
    from quirk.dashboard.api.app import create_app
    from quirk.dashboard.api.deps import get_db
    from quirk.models import Base

    db_name = f"test_uat31_{_uuid_uat31.uuid4().hex}"
    engine = _create_engine_uat31(
        f"sqlite:///file:{db_name}?mode=memory&cache=shared&uri=true",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    TestingSession = _sessionmaker_uat31(bind=engine, autoflush=False, autocommit=False)

    def _override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = _override_get_db
    return _TestClient_uat31(app), TestingSession


def test_uat_31_trends_two_sessions_flat_wire_format():
    """UAT-31 VERIFICATION: /api/trends returns the flat UAT-9-09 wire format
    when two distinct seeded sessions exist (one previous, one current).

    Asserts presence of all 12 documented top-level keys and verifies the
    new/resolved bucket logic for one new HIGH finding and one resolved MEDIUM
    finding."""
    from quirk.models import CryptoEndpoint

    client, SessionFactory = _make_uat31_client_and_session()
    db = SessionFactory()
    try:
        # Previous session: a HIGH, b MEDIUM
        db.add(CryptoEndpoint(
            host="a.example", port=443, protocol="TLS",
            severity="HIGH", scanned_at=_PREV_TS_UAT31,
        ))
        db.add(CryptoEndpoint(
            host="b.example", port=443, protocol="TLS",
            severity="MEDIUM", scanned_at=_PREV_TS_UAT31,
        ))
        # Current session: a HIGH (unchanged), c HIGH (new), b absent (resolved)
        db.add(CryptoEndpoint(
            host="a.example", port=443, protocol="TLS",
            severity="HIGH", scanned_at=_CURR_TS_UAT31,
        ))
        db.add(CryptoEndpoint(
            host="c.example", port=22, protocol="SSH",
            severity="HIGH", scanned_at=_CURR_TS_UAT31,
        ))
        db.commit()
    finally:
        db.close()

    resp = client.get("/api/trends")
    assert resp.status_code == 200, f"Expected 200; got {resp.status_code}: {resp.text}"
    data = resp.json()

    # Flat wire format — UAT-9-09: every key MUST be present at top level
    required_keys = (
        "current_session_ts", "previous_session_ts",
        "new_high", "new_medium", "new_low",
        "resolved_high", "resolved_medium", "resolved_low",
        "scan_errors_new_count", "scan_errors_resolved_count",
        "new_findings_sample", "resolved_findings_sample",
    )
    for key in required_keys:
        assert key in data, f"Missing required flat-wire-format key: {key!r}; got keys={list(data.keys())}"

    # Two-session diff produced: previous_session_ts and score_delta both non-null
    assert data["previous_session_ts"] is not None, (
        f"previous_session_ts must be non-null with two seeded sessions; got {data['previous_session_ts']!r}"
    )
    assert data.get("score_delta") is not None, (
        f"score_delta must be non-null with two seeded sessions; got {data.get('score_delta')!r}"
    )

    # New HIGH: c.example was added in current session
    assert data["new_high"] >= 1, (
        f"Expected new_high >= 1 (c.example SSH HIGH is new); got {data['new_high']}"
    )

    # Resolved MEDIUM: b.example MEDIUM was in previous but absent in current
    assert data["resolved_medium"] >= 1, (
        f"Expected resolved_medium >= 1 (b.example TLS MEDIUM is resolved); got {data['resolved_medium']}"
    )
