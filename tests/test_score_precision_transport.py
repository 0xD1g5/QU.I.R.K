"""Phase 199 / TRIAGE-10: fractional-score transport regression suite.

`quirk.intelligence.scoring.compute_readiness_score` is LOCKED (it always
returns an `int`), but four read surfaces each truncate or fabricate a `0`
when handed a fractional or absent score today:

- `GET /api/merge/latest` (per-segment AND overall) truncates via
  `int(result["score"])` and fabricates `0` on an absent score or a
  per-segment scoring exception (`quirk/dashboard/api/routes/merge.py`).
- `GET /api/trends/timeline` truncates/fabricates via
  `score=int(score_dict["score"] or 0)` (`quirk/dashboard/api/routes/trends.py`).
- `GET /api/scans` rejects a fractional score outright because
  `ScanSession.score` is `Optional[int]` (Pydantic 2 does not silently widen).

An unassessed score must render as honest absence (`None`/`null`), never a
fabricated `0` (CONTEXT.md). This file monkeypatches each CONSUMING module's
imported `compute_readiness_score` symbol (never the locked source module) to
inject a fractional (71.4) or `None` score and asserts it survives to the
wire, or is honestly absent, on all four surfaces.

This is the RED half of TRIAGE-10 (ROADMAP Phase 199 success criterion 1): it
is written and run BEFORE any production fix lands, and is expected to FAIL
against the current, unfixed tree. Plan 199-02 makes it pass by widening the
`Optional[int]`/`Dict[str, int]` schema fields to `Optional[float]` and
removing the truncation/fabrication call sites. The single named exception is
`test_trend_report_null_scores_stay_null_contract_lock`, which is expected to
PASS pre-fix (see its own docstring).

Run: pytest -q tests/test_score_precision_transport.py
"""
from __future__ import annotations

import itertools
from datetime import datetime, timedelta, timezone

import pytest

# ---------------------------------------------------------------------------
# Shared fixtures — copied from tests/test_dashboard_merge_latest.py, with the
# db_name prefix changed to avoid shared-cache collisions with that file.
# ---------------------------------------------------------------------------

_db_counter = itertools.count(100)


def _make_isolated_client():
    """Return a (TestClient, TestingSession) pair using a unique in-memory SQLite DB."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from quirk.dashboard.api.app import create_app
    from quirk.dashboard.api.deps import get_db
    from quirk.models import Base
    from fastapi.testclient import TestClient

    db_name = f"precision_test_{next(_db_counter)}"
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
                          cert_pubkey_alg="RSA", severity=None, scan_run_id=None):
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
        severity=severity,
        scan_run_id=scan_run_id,
    )
    db.add(ep)
    db.commit()
    return ep


# ---------------------------------------------------------------------------
# Fractional / null fake score_dict payloads. Carries every key any of the
# four consumers reads (timeline reads ["subscores"]; scan.py reads
# .get("rating", "") and .get("rating_cap_reason")).
# ---------------------------------------------------------------------------

_FRACTIONAL = {
    "score": 71.4,
    "subscores": {k: 10 for k in (
        "hygiene", "modern_tls", "identity_trust",
        "agility_signals", "data_at_rest", "data_in_motion")},
    "rating": "",
    "drivers": [],
}


# ===========================================================================
# Surface 1: GET /api/merge/latest (per-segment + overall)
# ===========================================================================

def test_fractional_score_round_trips_merge_per_segment(monkeypatch):
    """Injected 71.4 must survive per-segment; pre-fix truncates to 71."""
    monkeypatch.setattr(
        "quirk.dashboard.api.routes.merge.compute_readiness_score",
        lambda evidence: dict(_FRACTIONAL),
    )
    client, TestingSession = _make_isolated_client()
    db = TestingSession()
    _seed_merge_run(db)
    _seed_crypto_endpoint(db, host="dmz1.example", segment="dmz", sensor_id="s1")
    _seed_crypto_endpoint(db, host="corp1.example", segment="corp", sensor_id="s2")
    db.close()

    resp = client.get("/api/merge/latest")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["merge"]["per_segment_scores"]["dmz"] == 71.4


def test_fractional_score_round_trips_merge_overall(monkeypatch):
    """Injected 71.4 must survive on the overall `score`; pre-fix truncates to 71."""
    monkeypatch.setattr(
        "quirk.dashboard.api.routes.merge.compute_readiness_score",
        lambda evidence: dict(_FRACTIONAL),
    )
    client, TestingSession = _make_isolated_client()
    db = TestingSession()
    _seed_merge_run(db)
    _seed_crypto_endpoint(db, host="dmz1.example", segment="dmz", sensor_id="s1")
    _seed_crypto_endpoint(db, host="corp1.example", segment="corp", sensor_id="s2")
    db.close()

    resp = client.get("/api/merge/latest")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["merge"]["score"] == 71.4


def test_absent_score_stays_null_not_zero_merge(monkeypatch):
    """Injected `None` must stay `None` on both surfaces; pre-fix fabricates `0`."""
    monkeypatch.setattr(
        "quirk.dashboard.api.routes.merge.compute_readiness_score",
        lambda evidence: {**_FRACTIONAL, "score": None},
    )
    client, TestingSession = _make_isolated_client()
    db = TestingSession()
    _seed_merge_run(db)
    _seed_crypto_endpoint(db, host="dmz1.example", segment="dmz", sensor_id="s1")
    _seed_crypto_endpoint(db, host="corp1.example", segment="corp", sensor_id="s2")
    db.close()

    resp = client.get("/api/merge/latest")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["merge"]["per_segment_scores"]["dmz"] is None
    assert data["merge"]["score"] is None


def test_per_segment_scoring_failure_yields_null_not_zero(monkeypatch):
    """A per-segment scoring exception must yield `None`, not a fabricated `0`.

    Segments are grouped in first-seen order from `_assemble_union`'s
    endpoint list (a defaultdict keyed by `ep.segment`); seeding `dmz` before
    `corp` means the first `compute_readiness_score` call scores `dmz`.
    """
    call_counter = itertools.count()

    def _raise_once_then_fractional(evidence):
        if next(call_counter) == 0:
            raise RuntimeError("synthetic per-segment scoring failure")
        return dict(_FRACTIONAL)

    monkeypatch.setattr(
        "quirk.dashboard.api.routes.merge.compute_readiness_score",
        _raise_once_then_fractional,
    )
    client, TestingSession = _make_isolated_client()
    db = TestingSession()
    _seed_merge_run(db)
    _seed_crypto_endpoint(db, host="dmz1.example", segment="dmz", sensor_id="s1")
    _seed_crypto_endpoint(db, host="corp1.example", segment="corp", sensor_id="s2")
    db.close()

    resp = client.get("/api/merge/latest")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["merge"]["per_segment_scores"]["dmz"] is None
    assert data["merge"]["per_segment_scores"]["corp"] == 71.4


# ===========================================================================
# Surface 2: GET /api/trends/timeline
# ===========================================================================

def test_fractional_score_round_trips_timeline(monkeypatch):
    """Injected 71.4 must survive on a timeline point; pre-fix truncates to 71."""
    monkeypatch.setattr(
        "quirk.dashboard.api.routes.trends.compute_readiness_score",
        lambda evidence: dict(_FRACTIONAL),
    )
    client, TestingSession = _make_isolated_client()
    db = TestingSession()
    ts1 = datetime(2026, 5, 1, 9, 0, 0)
    ts2 = datetime(2026, 5, 2, 9, 0, 0)
    _seed_crypto_endpoint(db, host="a.example", scanned_at=ts1)
    _seed_crypto_endpoint(db, host="b.example", scanned_at=ts2)
    db.close()

    resp = client.get("/api/trends/timeline")
    assert resp.status_code == 200, resp.text
    points = resp.json()["sessions"]
    assert points, "expected at least one timeline point"
    assert points[0]["score"] == 71.4


def test_timeline_absent_score_stays_null_not_zero(monkeypatch):
    """Injected `None` must stay `None` on a timeline point; pre-fix fabricates `0`."""
    monkeypatch.setattr(
        "quirk.dashboard.api.routes.trends.compute_readiness_score",
        lambda evidence: {**_FRACTIONAL, "score": None},
    )
    client, TestingSession = _make_isolated_client()
    db = TestingSession()
    ts1 = datetime(2026, 5, 1, 9, 0, 0)
    ts2 = datetime(2026, 5, 2, 9, 0, 0)
    _seed_crypto_endpoint(db, host="a.example", scanned_at=ts1)
    _seed_crypto_endpoint(db, host="b.example", scanned_at=ts2)
    db.close()

    resp = client.get("/api/trends/timeline")
    assert resp.status_code == 200, resp.text
    points = resp.json()["sessions"]
    assert points, "expected at least one timeline point"
    assert points[0]["score"] is None


# ===========================================================================
# Surface 3: GET /api/trends (trend report)
# ===========================================================================

def _make_ordered_fractional_side_effect(first_score, second_score):
    """Return a side_effect distinguishing by CALL ORDER.

    `compute_trend_report` scores the current session before the previous
    session (`_score_for_session(current_eps)` then `_score_for_session(previous_eps)`),
    so the first call corresponds to `current_score` and the second to
    `previous_score`.
    """
    counter = itertools.count()

    def _side_effect(evidence):
        idx = next(counter)
        value = first_score if idx == 0 else second_score
        return {**_FRACTIONAL, "score": value}

    return _side_effect


def test_fractional_scores_round_trip_trend_report(monkeypatch):
    """current_score/previous_score preserve fractional precision; delta uses approx."""
    monkeypatch.setattr(
        "quirk.intelligence.trends.compute_readiness_score",
        _make_ordered_fractional_side_effect(71.4, 60.2),
    )
    client, TestingSession = _make_isolated_client()
    db = TestingSession()
    ts_prev = datetime(2026, 4, 25, 9, 0, 0)
    ts_curr = datetime(2026, 4, 26, 9, 0, 0)
    _seed_crypto_endpoint(db, host="a.example", scanned_at=ts_prev)
    _seed_crypto_endpoint(db, host="a.example", scanned_at=ts_curr)
    db.close()

    resp = client.get("/api/trends")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["current_score"] == 71.4
    assert data["previous_score"] == 60.2
    assert data["score_delta"] == pytest.approx(11.2)


def test_trend_report_null_scores_stay_null_contract_lock(monkeypatch):
    """CONTRACT LOCK — expected to PASS pre-fix, by design.

    `quirk/intelligence/trends.py:293-295` already guards `score_delta` on
    `current_score is not None and previous_score is not None`, and
    `TrendReport`/`TrendReportResponse` already type these fields as
    `Optional[int]`, which accepts `None` without coercion. This surface
    fabricates no `0` today — there is nothing to fix here. This test exists
    to LOCK the widened `Optional[float]` contract plan 199-02 introduces, so
    a future narrowing back to `Optional[int]`-with-`or 0` cannot land green.
    Its green result pre-fix is not a gap in the RED evidence.
    """
    monkeypatch.setattr(
        "quirk.intelligence.trends.compute_readiness_score",
        lambda evidence: {**_FRACTIONAL, "score": None},
    )
    client, TestingSession = _make_isolated_client()
    db = TestingSession()
    ts_prev = datetime(2026, 4, 25, 9, 0, 0)
    ts_curr = datetime(2026, 4, 26, 9, 0, 0)
    _seed_crypto_endpoint(db, host="a.example", scanned_at=ts_prev)
    _seed_crypto_endpoint(db, host="a.example", scanned_at=ts_curr)
    db.close()

    resp = client.get("/api/trends")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["current_score"] is None
    assert data["previous_score"] is None
    assert data["score_delta"] is None


# ===========================================================================
# Surface 4: GET /api/scans (scan-session history)
# ===========================================================================

def test_fractional_score_round_trips_scan_session(monkeypatch):
    """Injected 71.4 must survive on a scan-history row.

    Pre-fix `ScanSession.score` is `Optional[int]` — Pydantic 2 rejects a
    fractional value into that field outright (500), it does not silently
    truncate. Assert on the response body value; if the pre-fix run instead
    yields a 500, that is the RED signature and must not be softened away.
    """
    monkeypatch.setattr(
        "quirk.dashboard.api.routes.scan.compute_readiness_score",
        lambda evidence, profile=None: dict(_FRACTIONAL),
    )
    client, TestingSession = _make_isolated_client()
    db = TestingSession()
    _seed_crypto_endpoint(db, host="scan1.example", severity="HIGH")
    db.close()

    resp = client.get("/api/scans")
    assert resp.status_code == 200, resp.text
    items = resp.json()
    assert items, "expected at least one scan session"
    assert items[0]["score"] == 71.4


def test_scan_session_absent_score_stays_null(monkeypatch):
    """SECOND CONTRACT LOCK — expected to PASS pre-fix, by design.

    Discovered live during this plan's RED run (not hypothesized in advance):
    `quirk/dashboard/api/routes/scan.py` already passes `score_dict["score"]`
    through UNCHANGED with no `or 0` coercion (see its own inline comment at
    :1414-1420, which explicitly names trends.py and merge.py as the routes
    still carrying that fabrication, and calls scan.py's None-passthrough
    already correct). `ScanSession.score: Optional[int]` already accepts
    `None` without a Pydantic error. This surface fabricates no `0` today for
    the null case — only the FRACTIONAL case is a genuine pre-fix defect here
    (`Optional[int]` rejects 71.4 with `int_from_float`). This test locks the
    already-honest None-passthrough contract so a future regression cannot
    reintroduce an `or 0` on this route. Its green result pre-fix is not a
    gap in the RED evidence.
    """
    monkeypatch.setattr(
        "quirk.dashboard.api.routes.scan.compute_readiness_score",
        lambda evidence, profile=None: {**_FRACTIONAL, "score": None},
    )
    client, TestingSession = _make_isolated_client()
    db = TestingSession()
    _seed_crypto_endpoint(db, host="scan1.example", severity="HIGH")
    db.close()

    resp = client.get("/api/scans")
    assert resp.status_code == 200, resp.text
    items = resp.json()
    assert items, "expected at least one scan session"
    assert items[0]["score"] is None
