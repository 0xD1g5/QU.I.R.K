"""Unit tests for QRAMM score endpoint multiplier validation (SCORE-02).

Tests the 400 guard added by Phase 60 Plan 01, Task 01-03.
Per CONTEXT.md D-04, D-05.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from quirk.dashboard.api.app import app

client = TestClient(app, raise_server_exceptions=False)

# CSRF header required by Phase 58 middleware for all mutating requests
_CSRF_HEADERS = {"X-Quirk-Request": "1"}


@pytest.mark.parametrize("bad_multiplier", [0.0, 0.5, 0.79, 1.51, 2.0, 9.99, -1.0])
def test_out_of_range_multiplier_returns_400(bad_multiplier):
    """Values outside [0.8, 1.5] must return 400 with QRAMM_MULTIPLIER_OUT_OF_RANGE."""
    # Session 99999 almost certainly does not exist, but the multiplier guard
    # fires BEFORE the DB lookup, so we still get 400 not 404.
    resp = client.post(
        "/api/qramm/sessions/99999/score",
        json={"profile_multiplier": bad_multiplier},
        headers=_CSRF_HEADERS,
    )
    assert resp.status_code == 400, (
        f"multiplier={bad_multiplier}: expected 400, got {resp.status_code}. body={resp.text}"
    )
    body = resp.json()
    detail = body.get("detail", {})
    assert detail.get("error_code") == "QRAMM_MULTIPLIER_OUT_OF_RANGE", (
        f"Missing or wrong error_code in response: {body}"
    )
    assert detail.get("valid_range") == [0.8, 1.5]


@pytest.mark.parametrize("good_multiplier", [0.8, 1.0, 1.2, 1.5])
def test_in_range_multiplier_does_not_return_400(good_multiplier):
    """Values inside [0.8, 1.5] must NOT return 400 (may return 404/422 for missing session)."""
    resp = client.post(
        "/api/qramm/sessions/99999/score",
        json={"profile_multiplier": good_multiplier},
        headers=_CSRF_HEADERS,
    )
    assert resp.status_code != 400, (
        f"multiplier={good_multiplier}: should be accepted, got 400. body={resp.text}"
    )


def test_null_multiplier_does_not_return_400():
    """Omitting profile_multiplier should not trigger the 400 guard."""
    resp = client.post("/api/qramm/sessions/99999/score", json={}, headers=_CSRF_HEADERS)
    assert resp.status_code != 400, f"null multiplier triggered 400: {resp.text}"
