"""Phase 181 Plan 04 (SURF-03): closure state and burndown surfaced on the
dashboard's existing roadmap surface, behind the existing advisory-only
`_derive_*` firewall (`quirk/dashboard/api/routes/scan.py`).

Covers:
- `_derive_roadmap()` join-by-slug behavior, including the no-db backward
  compatibility path and lookup-failure degradation.
- `_derive_closure_burndown()` honest-absence and firewall behavior.
- The `/api/scan/latest` route: 200 (never 500) on a closure-lookup failure,
  and no `total`/`percent` key anywhere in the serialized burndown payload.
"""
from __future__ import annotations

import datetime
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from quirk.dashboard.api.routes.scan import _derive_closure_burndown, _derive_roadmap
from quirk.models import Base, CryptoEndpoint, RemediationItem, RemediationItemFingerprint


def _make_session():
    db_name = f"test_closure_burndown_{uuid.uuid4().hex}"
    engine = create_engine(
        f"sqlite:///file:{db_name}?mode=memory&cache=shared&uri=true",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return engine, TestingSession


# ---------------------------------------------------------------------------
# _derive_roadmap — join-by-slug behavior
# ---------------------------------------------------------------------------


def _fake_roadmap_items(titles_and_phases):
    return {
        "items": [
            {"phase": phase, "title": title, "why": "because", "timeframe": None}
            for title, phase in titles_and_phases
        ]
    }


def test_derive_roadmap_no_db_backward_compat(monkeypatch):
    """No db/scan_run_id supplied — every node's closure_state/slug stay None,
    matching pre-Phase-181 behavior exactly (every existing 2-arg call site)."""
    monkeypatch.setattr(
        "quirk.intelligence.roadmap.build_phased_roadmap",
        lambda evidence, scoring: _fake_roadmap_items(
            [("Remove plaintext HTTP exposure", "NOW")]
        ),
    )
    result = _derive_roadmap({}, {})
    assert len(result.nodes) == 1
    assert result.nodes[0].closure_state is None


def test_derive_roadmap_joins_known_title_to_persisted_state(monkeypatch):
    """A node whose raw title maps through slug_for_title() to a persisted
    RemediationItem row carries that row's state."""
    monkeypatch.setattr(
        "quirk.intelligence.roadmap.build_phased_roadmap",
        lambda evidence, scoring: _fake_roadmap_items(
            [("Remove plaintext HTTP exposure", "NOW")]
        ),
    )
    engine, TestingSession = _make_session()
    db = TestingSession()
    try:
        db.add(RemediationItem(
            slug="plaintext-http-exposure",
            scan_run_id="scan-1",
            title="Remove plaintext HTTP exposure",
            phase="NOW",
            state="closed",
        ))
        db.commit()

        result = _derive_roadmap({}, {}, db=db, scan_run_id="scan-1")
        assert len(result.nodes) == 1
        assert result.nodes[0].slug == "plaintext-http-exposure"
        assert result.nodes[0].closure_state == "closed"
    finally:
        db.close()
        engine.dispose()


def test_derive_roadmap_unmapped_title_stays_none(monkeypatch):
    """A node whose title has no slug carries closure_state=None and slug=None,
    even with a db and scan_run_id supplied."""
    monkeypatch.setattr(
        "quirk.intelligence.roadmap.build_phased_roadmap",
        lambda evidence, scoring: _fake_roadmap_items(
            [("Some brand-new title never mapped", "NOW")]
        ),
    )
    engine, TestingSession = _make_session()
    db = TestingSession()
    try:
        result = _derive_roadmap({}, {}, db=db, scan_run_id="scan-1")
        assert len(result.nodes) == 1
        assert result.nodes[0].slug is None
        assert result.nodes[0].closure_state is None
    finally:
        db.close()
        engine.dispose()


def test_derive_roadmap_node_id_never_used_as_lookup_key(monkeypatch):
    """The generated display node_id (phase-prefixed, truncated) must never be
    used as the closure-state lookup key — only slug_for_title() output is."""
    monkeypatch.setattr(
        "quirk.intelligence.roadmap.build_phased_roadmap",
        lambda evidence, scoring: _fake_roadmap_items(
            [("Remove plaintext HTTP exposure", "NOW")]
        ),
    )
    engine, TestingSession = _make_session()
    db = TestingSession()
    try:
        # Seed a row keyed by the NODE_ID string rather than the real slug —
        # if the lookup ever used node_id, this would (wrongly) match.
        db.add(RemediationItem(
            slug="now-remove-plaintext-http-e",  # node_id-shaped, NOT the real slug
            scan_run_id="scan-1",
            title="Remove plaintext HTTP exposure",
            phase="NOW",
            state="closed",
        ))
        db.commit()

        result = _derive_roadmap({}, {}, db=db, scan_run_id="scan-1")
        # Real slug has no persisted row under it, so closure_state stays None.
        assert result.nodes[0].slug == "plaintext-http-exposure"
        assert result.nodes[0].closure_state is None
    finally:
        db.close()
        engine.dispose()


def test_derive_roadmap_lookup_failure_degrades_to_no_closure_state(monkeypatch):
    """Any exception inside the closure lookup leaves closure_state as None and
    never propagates past _derive_roadmap — the roadmap itself still renders."""
    monkeypatch.setattr(
        "quirk.intelligence.roadmap.build_phased_roadmap",
        lambda evidence, scoring: _fake_roadmap_items(
            [("Remove plaintext HTTP exposure", "NOW")]
        ),
    )

    class _ExplodingSession:
        def query(self, *args, **kwargs):
            raise RuntimeError("simulated DB failure")

    result = _derive_roadmap({}, {}, db=_ExplodingSession(), scan_run_id="scan-1")
    assert len(result.nodes) == 1
    assert result.nodes[0].closure_state is None
    assert result.nodes[0].slug == "plaintext-http-exposure"


# ---------------------------------------------------------------------------
# _derive_closure_burndown — honest absence + firewall
# ---------------------------------------------------------------------------


def test_derive_closure_burndown_no_scan_run_id_returns_unavailable():
    engine, TestingSession = _make_session()
    db = TestingSession()
    try:
        result = _derive_closure_burndown(db, None)
        assert result is not None
        assert result.buckets == []
        assert result.unavailable_reason
    finally:
        db.close()
        engine.dispose()


def test_derive_closure_burndown_zero_fingerprint_rows_returns_unavailable():
    """compute_burndown() always returns all three buckets even with zero rows
    (D-35) — the explicit row-existence check is what prevents a zero-filled
    table being shown as a measured clean result."""
    engine, TestingSession = _make_session()
    db = TestingSession()
    try:
        result = _derive_closure_burndown(db, "scan-empty")
        assert result is not None
        assert result.buckets == []
        assert result.unavailable_reason
        assert "not" in result.unavailable_reason.lower() or "no" in result.unavailable_reason.lower()
    finally:
        db.close()
        engine.dispose()


def test_derive_closure_burndown_with_fingerprints_returns_unmapped_bucket():
    """Fingerprint rows exist, but no matching CryptoEndpoint (or unmapped
    algorithms) resolves to unmapped — and unmapped must be present, not
    filtered out."""
    engine, TestingSession = _make_session()
    db = TestingSession()
    try:
        db.add(RemediationItemFingerprint(
            scan_run_id="scan-2",
            slug="plaintext-http-exposure",
            finding_fingerprint="abc123",
            host="10.0.0.1",
            port=80,
            state="open",
        ))
        db.commit()

        result = _derive_closure_burndown(db, "scan-2")
        assert result is not None
        assert result.unavailable_reason is None
        bucket_names = {b.bucket for b in result.buckets}
        assert "unmapped" in bucket_names
        assert "key_establishment" in bucket_names
        assert "digital_signature" in bucket_names

        unmapped = next(b for b in result.buckets if b.bucket == "unmapped")
        assert unmapped.fingerprints == 1
        assert unmapped.open == 1
    finally:
        db.close()
        engine.dispose()


def test_derive_closure_burndown_raise_injection_returns_none(monkeypatch):
    """A raise inside compute_burndown logs and returns None — never raises,
    proving the advisory firewall on the aggregation path."""
    engine, TestingSession = _make_session()
    db = TestingSession()
    try:
        db.add(RemediationItemFingerprint(
            scan_run_id="scan-3",
            slug="plaintext-http-exposure",
            finding_fingerprint="def456",
            host="10.0.0.1",
            port=80,
            state="open",
        ))
        db.commit()

        def _boom(session, *, scan_run_id):
            raise RuntimeError("simulated burndown aggregation failure")

        monkeypatch.setattr("quirk.intelligence.burndown.compute_burndown", _boom)

        result = _derive_closure_burndown(db, "scan-3")
        assert result is None
    finally:
        db.close()
        engine.dispose()


# ---------------------------------------------------------------------------
# Route-level: firewall proven end-to-end, and no total/percent key
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


def _seed_scan(TestingSession, scan_run_id: str, scanned_at: datetime.datetime, with_fingerprint: bool = True):
    db = TestingSession()
    try:
        db.add(CryptoEndpoint(
            host="10.0.0.1",
            port=443,
            protocol="TLS",
            scanned_at=scanned_at,
            scan_run_id=scan_run_id,
        ))
        if with_fingerprint:
            db.add(RemediationItemFingerprint(
                scan_run_id=scan_run_id,
                slug="plaintext-http-exposure",
                finding_fingerprint="ghi789",
                host="10.0.0.1",
                port=443,
                state="open",
            ))
        db.commit()
    finally:
        db.close()


def test_scan_latest_returns_200_with_burndown_on_closure_failure(monkeypatch):
    """Raise-injection at the route level: compute_burndown blows up, and the
    endpoint still returns 200 (never 500) with burndown null."""
    client, TestingSession, engine = _client_and_session()
    try:
        scanned_at = datetime.datetime(2026, 9, 1, 12, 0, 0)
        scan_run_id = scanned_at.isoformat()
        _seed_scan(TestingSession, scan_run_id, scanned_at)

        def _boom(session, *, scan_run_id):
            raise RuntimeError("simulated burndown aggregation failure")

        monkeypatch.setattr("quirk.intelligence.burndown.compute_burndown", _boom)

        resp = client.get("/api/scan/latest")
        assert resp.status_code == 200
        data = resp.json()
        assert data["burndown"] is None
    finally:
        client.close()
        engine.dispose()


def test_scan_latest_burndown_has_no_total_or_percent_key():
    client, TestingSession, engine = _client_and_session()
    try:
        scanned_at = datetime.datetime(2026, 9, 1, 13, 0, 0)
        scan_run_id = scanned_at.isoformat()
        _seed_scan(TestingSession, scan_run_id, scanned_at)

        resp = client.get("/api/scan/latest")
        assert resp.status_code == 200
        data = resp.json()
        assert data["burndown"] is not None
        assert "total" not in data["burndown"]
        assert "percent" not in data["burndown"]
        for bucket in data["burndown"]["buckets"]:
            assert "total" not in bucket
            assert "percent" not in bucket
            assert "severity" not in bucket
            assert "host" not in bucket
            assert "port" not in bucket
    finally:
        client.close()
        engine.dispose()


def test_scan_latest_no_fingerprint_rows_yields_unavailable_reason_not_zero_table():
    client, TestingSession, engine = _client_and_session()
    try:
        scanned_at = datetime.datetime(2026, 9, 1, 14, 0, 0)
        scan_run_id = scanned_at.isoformat()
        _seed_scan(TestingSession, scan_run_id, scanned_at, with_fingerprint=False)

        resp = client.get("/api/scan/latest")
        assert resp.status_code == 200
        data = resp.json()
        assert data["burndown"]["buckets"] == []
        assert data["burndown"]["unavailable_reason"]
    finally:
        client.close()
        engine.dispose()


def test_scan_latest_roadmap_nodes_carry_closure_state_field():
    """RoadmapNode entries in the live route response include the new
    closure_state/slug keys (even if None), proving the schema round-trips."""
    client, TestingSession, engine = _client_and_session()
    try:
        scanned_at = datetime.datetime(2026, 9, 1, 15, 0, 0)
        scan_run_id = scanned_at.isoformat()
        _seed_scan(TestingSession, scan_run_id, scanned_at, with_fingerprint=False)

        resp = client.get("/api/scan/latest")
        assert resp.status_code == 200
        data = resp.json()
        assert "roadmap" in data
        for node in data["roadmap"]["nodes"]:
            assert "closure_state" in node
            assert "slug" in node
    finally:
        client.close()
        engine.dispose()
