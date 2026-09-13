"""Phase 201 Plan 04 (LIFT-05): score_lift/projected_score wiring through
`_derive_roadmap()` and the `/api/scan/latest` endpoint.

Covers the 5 pinned behaviors:
1. A modelable item's node serializes a positive `score_lift`, keyed by slug.
2. A node whose slug has no modelable delta serializes `score_lift: None`
   (never 0, never omitted-as-0).
3. `projected_score` is present for an assessed scan and `null` for an
   unassessed one (base score None).
4. A `compute_item_lifts` failure degrades to a fully populated roadmap with
   every node's `score_lift` null — HTTP 200, never a crash.
5. A `compute_projected_score` failure degrades `projected_score` to null,
   leaving the rest of the payload unaffected — HTTP 200.

Both lift calls thread `profile=stored_profile` with NO weights, matching
the endpoint's own `compute_readiness_score(evidence, profile=stored_profile)`
call — the pre-existing CLI/dashboard calibration asymmetry is intentionally
not "fixed" here (RESEARCH Pitfall 4).
"""
from __future__ import annotations

import datetime
import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from quirk.dashboard.api.routes.scan import _derive_roadmap
from quirk.models import Base, CryptoEndpoint


def _make_session():
    db_name = f"test_scan_roadmap_score_lift_{uuid.uuid4().hex}"
    engine = create_engine(
        f"sqlite:///file:{db_name}?mode=memory&cache=shared&uri=true",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return engine, TestingSession


def _fake_roadmap_items(titles_and_phases):
    return {
        "items": [
            {"phase": phase, "title": title, "why": "because", "timeframe": None}
            for title, phase in titles_and_phases
        ]
    }


# ---------------------------------------------------------------------------
# Behaviors 1 + 2 — _derive_roadmap unit-level join-by-slug
# ---------------------------------------------------------------------------


def test_derive_roadmap_score_lift_positive_for_modelable_item(monkeypatch):
    """Behavior 1: a node whose slug has a positive lift entry serializes it,
    keyed by the same `slug_for_title()` id used elsewhere on the node."""
    monkeypatch.setattr(
        "quirk.intelligence.roadmap.build_phased_roadmap",
        lambda evidence, scoring: _fake_roadmap_items(
            [("Remove plaintext HTTP exposure", "NOW")]
        ),
    )
    monkeypatch.setattr(
        "quirk.dashboard.api.routes.scan.compute_item_lifts",
        lambda evidence, items, *, profile=None, weights=None: {"plaintext-http-exposure": 5},
    )

    result = _derive_roadmap({}, {}, profile="balanced")
    assert len(result.nodes) == 1
    assert result.nodes[0].slug == "plaintext-http-exposure"
    assert result.nodes[0].score_lift == 5


def test_derive_roadmap_score_lift_null_for_unmodelable_item(monkeypatch):
    """Behavior 2: a resolved slug with no entry in the lift map serializes
    `score_lift` as `None` — an `is None` check, not a falsy one, since a
    falsy check would also pass on 0."""
    monkeypatch.setattr(
        "quirk.intelligence.roadmap.build_phased_roadmap",
        lambda evidence, scoring: _fake_roadmap_items(
            [("Remove plaintext HTTP exposure", "NOW")]
        ),
    )
    monkeypatch.setattr(
        "quirk.dashboard.api.routes.scan.compute_item_lifts",
        lambda evidence, items, *, profile=None, weights=None: {},
    )

    result = _derive_roadmap({}, {}, profile="balanced")
    assert len(result.nodes) == 1
    assert result.nodes[0].slug == "plaintext-http-exposure"
    assert result.nodes[0].score_lift is None


# ---------------------------------------------------------------------------
# Behaviors 3, 4, 5 — route-level wiring and degradation
# ---------------------------------------------------------------------------


def _client_and_session():
    from fastapi.testclient import TestClient

    from quirk.dashboard.api.app import create_app
    from quirk.dashboard.api.deps import get_db

    engine, TestingSession = _make_session()

    def _override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = _override_get_db
    client = TestClient(app, headers={"X-Quirk-Request": "1"})
    return client, TestingSession, engine


def _seed_scan(TestingSession, scan_run_id: str, scanned_at: datetime.datetime):
    db = TestingSession()
    try:
        db.add(CryptoEndpoint(
            host="10.0.0.1",
            port=443,
            protocol="TLS",
            scanned_at=scanned_at,
            scan_run_id=scan_run_id,
        ))
        db.commit()
    finally:
        db.close()


def test_scan_latest_projected_score_present_when_assessed(monkeypatch):
    """Behavior 3 (assessed half): the endpoint's own `compute_projected_score`
    call site is exercised end to end and its return value (a positive-delta
    projection above the assessed base score) is surfaced verbatim."""
    client, TestingSession, engine = _client_and_session()
    try:
        scanned_at = datetime.datetime(2026, 9, 1, 12, 0, 0)
        scan_run_id = scanned_at.isoformat()
        _seed_scan(TestingSession, scan_run_id, scanned_at)

        def _fake_projection(evidence, items, *, profile=None, weights=None):
            return 99

        monkeypatch.setattr(
            "quirk.dashboard.api.routes.scan.compute_projected_score", _fake_projection
        )

        resp = client.get("/api/scan/latest")
        assert resp.status_code == 200
        data = resp.json()
        assert data["projected_score"] == 99
    finally:
        client.close()
        engine.dispose()


def test_scan_latest_projected_score_null_when_unassessed(monkeypatch):
    """Behavior 3 (unassessed half): when the projection cannot be modeled
    (base score None, SCORE-06), `projected_score` is null — never 0/fabricated."""
    client, TestingSession, engine = _client_and_session()
    try:
        scanned_at = datetime.datetime(2026, 9, 1, 13, 0, 0)
        scan_run_id = scanned_at.isoformat()
        _seed_scan(TestingSession, scan_run_id, scanned_at)

        def _fake_projection(evidence, items, *, profile=None, weights=None):
            return None

        monkeypatch.setattr(
            "quirk.dashboard.api.routes.scan.compute_projected_score", _fake_projection
        )

        resp = client.get("/api/scan/latest")
        assert resp.status_code == 200
        data = resp.json()
        assert data["projected_score"] is None
    finally:
        client.close()
        engine.dispose()


def test_scan_latest_lift_computation_failure_degrades_to_null_lifts(monkeypatch):
    """Behavior 4: a raising `compute_item_lifts` still returns 200 with a
    fully populated roadmap and every node's `score_lift` null."""
    client, TestingSession, engine = _client_and_session()
    try:
        scanned_at = datetime.datetime(2026, 9, 1, 14, 0, 0)
        scan_run_id = scanned_at.isoformat()
        _seed_scan(TestingSession, scan_run_id, scanned_at)

        def _boom(evidence, items, *, profile=None, weights=None):
            raise RuntimeError("simulated lift computation failure")

        monkeypatch.setattr("quirk.dashboard.api.routes.scan.compute_item_lifts", _boom)

        resp = client.get("/api/scan/latest")
        assert resp.status_code == 200
        data = resp.json()
        nodes = data["roadmap"]["nodes"]
        assert len(nodes) > 0
        for node in nodes:
            assert node["score_lift"] is None
    finally:
        client.close()
        engine.dispose()


def test_scan_latest_projection_failure_degrades_to_null_projected_score(monkeypatch):
    """Behavior 5: a raising `compute_projected_score` still returns 200 with
    `projected_score` null, leaving the rest of the payload (score, roadmap)
    unaffected."""
    client, TestingSession, engine = _client_and_session()
    try:
        scanned_at = datetime.datetime(2026, 9, 1, 15, 0, 0)
        scan_run_id = scanned_at.isoformat()
        _seed_scan(TestingSession, scan_run_id, scanned_at)

        def _boom(evidence, items, *, profile=None, weights=None):
            raise RuntimeError("simulated projection failure")

        monkeypatch.setattr("quirk.dashboard.api.routes.scan.compute_projected_score", _boom)

        resp = client.get("/api/scan/latest")
        assert resp.status_code == 200
        data = resp.json()
        assert data["projected_score"] is None
        assert "score" in data
        assert "roadmap" in data
        assert len(data["roadmap"]["nodes"]) > 0
    finally:
        client.close()
        engine.dispose()
