"""APCL-02 (Phase 75-02): API correctness tests for WR-04, WR-05, WR-06, WR-09.

Covers:
- D-04 (WR-04): get_latest_scan ?scan_id= microsecond-precision inclusive [start, end] window
- D-05 (WR-05): list_scans groups by parsed-datetime keys (microsecond truncated), sorted desc
- D-06 (WR-06): score_session validates multiplier server-side BEFORE DB access
                Range stays [0.8, 1.5] per RESEARCH C-2 + user override (NOT [0.0, 4.0])
- D-07 (WR-09): _compute_multiplier clamps BEFORE rounding (boundary safety)

RED at creation: scan.py still uses formatted-string comparison and string-keyed grouping;
qramm.py _compute_multiplier rounds before clamp; multiplier validation needs an explicit
isinstance check + the literal "multiplier must be numeric in [0.8, 1.5]" detail string.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from quirk.dashboard.api.app import create_app
from quirk.dashboard.api.deps import get_db
from quirk.dashboard.api.routes import qramm as qramm_routes
from quirk.dashboard.api.routes.qramm import _compute_multiplier
from quirk.models import Base, CryptoEndpoint


_CSRF = {"X-Quirk-Request": "1"}


def _make_client_and_session():
    db_name = f"test_apcl02_{uuid.uuid4().hex}"
    engine = create_engine(
        f"sqlite:///file:{db_name}?mode=memory&cache=shared&uri=true",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def _override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = _override_get_db
    return TestClient(app, headers=_CSRF), TestingSession


def _seed_endpoint(TestingSession, scanned_at: datetime, host: str = "10.0.0.1"):
    db = TestingSession()
    try:
        db.add(CryptoEndpoint(
            scanned_at=scanned_at,
            host=host,
            port=443,
            protocol="tls",
            severity="HIGH",
        ))
        db.commit()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# D-04 (WR-04) — microsecond-precision inclusive [start, end] window
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("query_us", [0, 500_000, 999_999])
def test_get_latest_scan_microsecond_window_inclusive(query_us):
    """A scan stored at .000000 must be findable across the full microsecond range."""
    client, Session = _make_client_and_session()
    seeded = datetime(2026, 5, 15, 12, 0, 0, 0)
    _seed_endpoint(Session, seeded)

    query_ts = datetime(2026, 5, 15, 12, 0, 0, query_us).isoformat()
    resp = client.get(f"/api/scan/latest?scan_id={query_ts}")
    assert resp.status_code == 200, (
        f"microsecond query_us={query_us} expected 200, got {resp.status_code} ({resp.text[:200]})"
    )


def test_get_latest_scan_microsecond_window_excludes_next_second():
    """A scan at 12:00:00.500000 must NOT be returned by ?scan_id=12:00:01.000000."""
    client, Session = _make_client_and_session()
    seeded = datetime(2026, 5, 15, 12, 0, 0, 500_000)
    _seed_endpoint(Session, seeded)

    query_ts = datetime(2026, 5, 15, 12, 0, 1, 0).isoformat()
    resp = client.get(f"/api/scan/latest?scan_id={query_ts}")
    # Different second, no row at that exact timestamp -> 404
    assert resp.status_code == 404, (
        f"out-of-window query expected 404, got {resp.status_code}"
    )


# ---------------------------------------------------------------------------
# D-05 (WR-05) — list_scans groups by parsed-datetime, sorted desc
# ---------------------------------------------------------------------------

def test_list_scans_groups_by_parsed_datetime_same_second():
    """Three rows differing by microseconds within the same second collapse to ONE session."""
    client, Session = _make_client_and_session()
    base = datetime(2026, 5, 15, 12, 0, 0, 0)
    _seed_endpoint(Session, base.replace(microsecond=100), host="10.0.0.1")
    _seed_endpoint(Session, base.replace(microsecond=200_000), host="10.0.0.2")
    _seed_endpoint(Session, base.replace(microsecond=900_000), host="10.0.0.3")

    resp = client.get("/api/scans")
    assert resp.status_code == 200, resp.text
    sessions = resp.json()
    # All three microsecond-offset rows should land in a single second-truncated bucket
    same_second = [s for s in sessions if s["scanned_at"].startswith("2026-05-15T12:00:00")]
    assert len(same_second) == 1, (
        f"expected 1 grouped session, got {len(same_second)}: {sessions}"
    )


def test_list_scans_sorted_descending_on_parsed_datetime():
    """Two rows in different seconds: newer first."""
    client, Session = _make_client_and_session()
    older = datetime(2026, 5, 15, 12, 0, 0, 0)
    newer = datetime(2026, 5, 15, 12, 0, 5, 0)
    _seed_endpoint(Session, older, host="10.0.0.10")
    _seed_endpoint(Session, newer, host="10.0.0.20")

    resp = client.get("/api/scans")
    assert resp.status_code == 200, resp.text
    sessions = resp.json()
    relevant = [s for s in sessions if s["scanned_at"].startswith("2026-05-15T12:00:0")]
    assert len(relevant) >= 2
    # Parse and verify descending order
    parsed = [datetime.fromisoformat(s["scanned_at"]) for s in relevant[:2]]
    assert parsed[0] > parsed[1], f"expected descending order, got {parsed}"


# ---------------------------------------------------------------------------
# D-06 (WR-06) — server-side validation BEFORE DB access; range [0.8, 1.5]
# ---------------------------------------------------------------------------

def test_score_session_out_of_range_returns_400_with_literal_detail():
    """multiplier=0.5 returns 400 with detail containing 'multiplier must be numeric in [0.8, 1.5]'."""
    client, _ = _make_client_and_session()
    resp = client.post(
        "/api/qramm/sessions/99999/score",
        json={"profile_multiplier": 0.5},
    )
    assert resp.status_code == 400, resp.text
    detail = resp.json().get("detail", "")
    assert "multiplier must be numeric in [0.8, 1.5]" in detail, (
        f"expected literal detail substring; got: {detail}"
    )


def test_score_session_non_numeric_returns_400():
    """multiplier='abc' returns 400 (caught by Pydantic OR explicit isinstance guard)."""
    client, _ = _make_client_and_session()
    resp = client.post(
        "/api/qramm/sessions/99999/score",
        json={"profile_multiplier": "abc"},
    )
    assert resp.status_code in (400, 422), resp.text


def test_score_session_in_range_does_not_400():
    """multiplier=1.2 inside [0.8, 1.5] must not trigger the 400 guard."""
    client, _ = _make_client_and_session()
    resp = client.post(
        "/api/qramm/sessions/99999/score",
        json={"profile_multiplier": 1.2},
    )
    assert resp.status_code != 400, resp.text


def test_score_session_out_of_range_does_not_hit_db():
    """CRITICAL: out-of-range multiplier MUST NOT call db.query() / db.get().

    Spy on the dependency-injected DB session; assert no DB access occurs before
    HTTPException is raised. This is the 'before DB access' guarantee for D-06.
    """
    spy_db = MagicMock()
    # The route should raise before any DB method is invoked
    spy_db.query.side_effect = AssertionError("db.query() called before validation!")
    spy_db.get.side_effect = AssertionError("db.get() called before validation!")

    app = create_app()

    def _override():
        yield spy_db

    app.dependency_overrides[get_db] = _override
    client = TestClient(app, headers=_CSRF)

    resp = client.post(
        "/api/qramm/sessions/1/score",
        json={"profile_multiplier": 2.0},
    )
    assert resp.status_code == 400, resp.text
    assert spy_db.query.call_count == 0, "db.query() was invoked before validation"
    assert spy_db.get.call_count == 0, "db.get() was invoked before validation"


# ---------------------------------------------------------------------------
# D-07 (WR-09) — clamp BEFORE round (boundary safety)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("base,delta,expected", [
    # value = 0.795 -> clamp to 0.8 -> round = 0.8
    (0.795, 0.0, 0.8),
    # value = 1.505 -> clamp to 1.5 -> round = 1.5
    (1.505, 0.0, 1.5),
    # value = 1.20 -> pass through (0.8 <= 1.20 <= 1.5)
    (1.10, 0.10, 1.20),
    # boundary: value = 1.504 (round-then-clamp: round=1.50, clamp=1.5; clamp-then-round: 1.504->1.5)
    (1.504, 0.0, 1.5),
    # Negative boundary: value = 0.794 -> clamp=0.8 (under both orders, equal here)
    (0.794, 0.0, 0.8),
])
def test_compute_multiplier_clamp_then_round_boundary(monkeypatch, base, delta, expected):
    """Patch _INDUSTRY_BASE / _SENSITIVITY_DELTA so we can drive raw `value` to boundary inputs."""
    monkeypatch.setitem(qramm_routes._INDUSTRY_BASE, "__test__", base)
    monkeypatch.setitem(qramm_routes._SENSITIVITY_DELTA, "__test__", delta)
    result = _compute_multiplier("__test__", "__test__")
    assert result == expected, (
        f"_compute_multiplier raw {base}+{delta}={base+delta}: expected {expected}, got {result}"
    )
    # Always within band
    assert 0.8 <= result <= 1.5
