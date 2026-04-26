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
