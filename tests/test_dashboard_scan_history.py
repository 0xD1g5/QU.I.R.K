"""Dashboard API integration tests for GET /api/scans and GET /api/compare.

Wave 0 scaffold — all tests are RED at creation because:
- /api/scans does not yet return score, profile, calibration, target, finding_counts
  and still has LIMIT 10 (Plan 02 adds these)
- /api/compare does not exist yet (Plan 02 adds it)

Plans 02 and 03 will turn each test GREEN.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from quirk.dashboard.api.app import create_app
from quirk.dashboard.api.deps import get_db
from quirk.models import Base, CryptoEndpoint, ScanJob


def _make_client_and_session():
    db_name = f"test_scan_history_{uuid.uuid4().hex}"
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
    return TestClient(app), TestingSession


def _seed_session(TestingSession, scanned_at: datetime, endpoints: list[dict]):
    """Helper: create CryptoEndpoint rows for a given scanned_at timestamp.

    CryptoEndpoint rows are grouped by second-precision scanned_at. The ScanJob
    join uses ScanJob.scan_run_id (not a CryptoEndpoint field).
    """
    db = TestingSession()
    try:
        for ep in endpoints:
            db.add(CryptoEndpoint(
                scanned_at=scanned_at,
                **ep,
            ))
        db.commit()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# UI-HIST-01: GET /api/scans — scan history list
# ---------------------------------------------------------------------------

def test_list_scans_schema():
    """UI-HIST-01: GET /api/scans returns 200 with enriched session schema."""
    client, Session = _make_client_and_session()
    ts = datetime.now(timezone.utc)
    _seed_session(Session, ts, [
        {"host": "10.0.0.1", "port": 443, "protocol": "tls", "severity": "HIGH"},
        {"host": "10.0.0.2", "port": 443, "protocol": "tls", "severity": "MEDIUM"},
    ])

    resp = client.get("/api/scans")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) >= 1
    item = items[0]
    # These keys are added by Plan 02 — they will cause a RED failure until then
    for key in ("scan_id", "scanned_at", "total_endpoints", "score", "profile",
                "calibration", "target", "finding_counts"):
        assert key in item, f"Missing key {key!r} in /api/scans response item"
    # finding_counts must have high/medium/low buckets
    fc = item["finding_counts"]
    for bucket in ("high", "medium", "low"):
        assert bucket in fc, f"Missing bucket {bucket!r} in finding_counts"


def test_list_scans_no_limit():
    """UI-HIST-01: GET /api/scans returns all sessions — no LIMIT 10 cap."""
    client, Session = _make_client_and_session()
    base_ts = datetime.now(timezone.utc)
    for i in range(12):
        ts = base_ts - timedelta(minutes=i)
        _seed_session(Session, ts, [
            {"host": f"host-{i}.example.com", "port": 443, "protocol": "tls",
             "severity": "HIGH"},
        ])

    resp = client.get("/api/scans")
    assert resp.status_code == 200
    # Plan 02 removes the LIMIT 10 — currently 10 max so this will fail RED
    assert len(resp.json()) == 12, (
        f"Expected 12 sessions (no cap); got {len(resp.json())} — "
        "LIMIT 10 must be removed by Plan 02"
    )


def test_clone_data_recovery():
    """UI-HIST-01: GET /api/scans recovers profile/calibration/target from ScanJob."""
    client, Session = _make_client_and_session()
    ts = datetime.now(timezone.utc)
    scan_run_id = ts.isoformat()
    _seed_session(Session, ts, [
        {"host": "dashboard.example.com", "port": 443, "protocol": "tls",
         "severity": "INFO"},
    ])
    # Seed a matching ScanJob so clone data is recoverable
    db = Session()
    try:
        db.add(ScanJob(
            job_id=str(uuid.uuid4()),
            status="completed",
            target="dashboard.example.com",
            profile="full",
            calibration="thorough",
            scan_run_id=scan_run_id,
        ))
        db.commit()
    finally:
        db.close()

    resp = client.get("/api/scans")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) >= 1
    item = items[0]
    # Plan 02 adds ScanJob join — these will fail RED until then
    assert item.get("target") == "dashboard.example.com", (
        f"Expected target='dashboard.example.com'; got {item.get('target')!r}"
    )
    assert item.get("profile") == "full", (
        f"Expected profile='full'; got {item.get('profile')!r}"
    )
    assert item.get("calibration") == "thorough", (
        f"Expected calibration='thorough'; got {item.get('calibration')!r}"
    )


def test_clone_reconstruction():
    """UI-HIST-01: GET /api/scans reconstructs target from hosts when no ScanJob."""
    client, Session = _make_client_and_session()
    ts = datetime.now(timezone.utc)
    _seed_session(Session, ts, [
        {"host": "cli-a.example.com", "port": 443, "protocol": "tls", "severity": "HIGH"},
        {"host": "cli-b.example.com", "port": 443, "protocol": "tls", "severity": "MEDIUM"},
    ])
    # Intentionally NO ScanJob row — CLI-launched scan

    resp = client.get("/api/scans")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) >= 1
    item = items[0]
    # Plan 02 adds reconstruction logic — these will fail RED until then
    assert item.get("profile") is None, (
        f"Expected profile=None for CLI scan; got {item.get('profile')!r}"
    )
    assert item.get("calibration") is None, (
        f"Expected calibration=None for CLI scan; got {item.get('calibration')!r}"
    )
    target = item.get("target", "")
    assert "cli-a.example.com" in target, (
        f"Expected 'cli-a.example.com' in reconstructed target; got {target!r}"
    )
    assert "cli-b.example.com" in target, (
        f"Expected 'cli-b.example.com' in reconstructed target; got {target!r}"
    )


# ---------------------------------------------------------------------------
# UI-HIST-02: GET /api/compare — scan comparison
# ---------------------------------------------------------------------------

def test_compare_schema():
    """UI-HIST-02: GET /api/compare returns 200 with full comparison schema."""
    client, Session = _make_client_and_session()
    ts_a = datetime.now(timezone.utc)
    ts_b = ts_a - timedelta(hours=1)
    _seed_session(Session, ts_a, [
        {"host": "newer.example.com", "port": 443, "protocol": "tls", "severity": "HIGH"},
    ])
    _seed_session(Session, ts_b, [
        {"host": "older.example.com", "port": 443, "protocol": "tls", "severity": "HIGH"},
    ])

    resp = client.get(
        f"/api/compare?a={ts_a.isoformat()}&b={ts_b.isoformat()}"
    )
    # /api/compare does not exist yet — will return 404 RED until Plan 02 adds it
    assert resp.status_code == 200, (
        f"Expected 200 from /api/compare; got {resp.status_code} — "
        "endpoint added by Plan 02"
    )
    data = resp.json()
    for key in ("scan_a", "scan_b", "score_delta", "subscore_deltas",
                "added_findings", "removed_findings", "endpoints_only_in_a",
                "endpoints_only_in_b", "changed_endpoints"):
        assert key in data, f"Missing key {key!r} in /api/compare response"
    # subscore_deltas must include all 6 pillar keys
    sd = data["subscore_deltas"]
    for pillar in ("hygiene", "modern_tls", "identity_trust",
                   "agility_signals", "data_at_rest", "data_in_motion"):
        assert pillar in sd, f"Missing subscore pillar {pillar!r} in subscore_deltas"


def test_compare_self():
    """UI-HIST-02: GET /api/compare returns 400 when a == b (same scan)."""
    client, Session = _make_client_and_session()
    ts = datetime.now(timezone.utc)
    _seed_session(Session, ts, [
        {"host": "self.example.com", "port": 443, "protocol": "tls", "severity": "INFO"},
    ])

    resp = client.get(
        f"/api/compare?a={ts.isoformat()}&b={ts.isoformat()}"
    )
    # /api/compare does not exist yet — will return 404 RED until Plan 02 adds it
    assert resp.status_code == 400, (
        f"Expected 400 for self-compare; got {resp.status_code}"
    )
    assert resp.json()["detail"] == "Cannot compare a scan to itself.", (
        f"Expected detail='Cannot compare a scan to itself.'; got {resp.json()!r}"
    )


def test_compare_score_delta():
    """UI-HIST-02: score_delta and subscore_deltas reflect posture differences between sessions.

    Session A uses ECDSA (agility bonus) while session B uses RSA-only (agility penalty).
    The agility subscore delta must be > 0 (A better than B), even if overall score is 100
    for both sessions due to the scoring model's additive clamp at 100.
    """
    client, Session = _make_client_and_session()
    ts_a = datetime.now(timezone.utc)
    ts_b = ts_a - timedelta(hours=1)
    # Session A: ECDSA certs (agility bonus)
    _seed_session(Session, ts_a, [
        {"host": "good.example.com", "port": 443, "protocol": "tls",
         "tls_version": "TLSv1.3",
         "cert_pubkey_alg": "ECDSA",
         "severity": "INFO"},
    ])
    # Session B: RSA-only certs (agility penalty)
    _seed_session(Session, ts_b, [
        {"host": "rsa.example.com", "port": 443, "protocol": "tls",
         "tls_version": "TLSv1.3",
         "cert_pubkey_alg": "RSA",
         "severity": "HIGH"},
    ])

    resp = client.get(
        f"/api/compare?a={ts_a.isoformat()}&b={ts_b.isoformat()}"
    )
    assert resp.status_code == 200, (
        f"Expected 200 from /api/compare; got {resp.status_code}"
    )
    data = resp.json()
    # Overall score may be 100 for both (scoring model clamps at 100); check subscore delta
    assert data["score_delta"] >= 0, (
        f"Expected score_delta >= 0 (A has ECDSA vs B has RSA); got {data['score_delta']}"
    )
    # Agility subscore: ECDSA bonus (+4) vs RSA penalty (-8); A should be higher than B
    agility_delta = data["subscore_deltas"]["agility_signals"]
    assert agility_delta > 0, (
        f"Expected agility_signals delta > 0 (A:ECDSA vs B:RSA); got {agility_delta}"
    )


def test_compare_finding_diff():
    """UI-HIST-02: added_findings and removed_findings are non-empty for different sessions."""
    client, Session = _make_client_and_session()
    ts_a = datetime.now(timezone.utc)
    ts_b = ts_a - timedelta(hours=1)
    _seed_session(Session, ts_a, [
        {"host": "x.example.com", "port": 443, "protocol": "tls", "severity": "HIGH"},
    ])
    _seed_session(Session, ts_b, [
        {"host": "y.example.com", "port": 443, "protocol": "tls", "severity": "HIGH"},
    ])

    resp = client.get(
        f"/api/compare?a={ts_a.isoformat()}&b={ts_b.isoformat()}"
    )
    # /api/compare does not exist yet — RED until Plan 02 adds it
    assert resp.status_code == 200, (
        f"Expected 200 from /api/compare; got {resp.status_code}"
    )
    data = resp.json()
    assert len(data["added_findings"]) >= 1, (
        f"Expected >= 1 added_finding (x.example.com in A not B); got {data['added_findings']}"
    )
    assert len(data["removed_findings"]) >= 1, (
        f"Expected >= 1 removed_finding (y.example.com in B not A); got {data['removed_findings']}"
    )


def test_compare_endpoint_diff():
    """UI-HIST-02: endpoints_only_in_a, endpoints_only_in_b, changed_endpoints correct."""
    client, Session = _make_client_and_session()
    ts_a = datetime.now(timezone.utc)
    ts_b = ts_a - timedelta(hours=1)
    # Session A: shared + only-a
    _seed_session(Session, ts_a, [
        {"host": "shared.example.com", "port": 443, "protocol": "tls",
         "tls_version": "TLSv1.3", "severity": "INFO"},
        {"host": "only-a.example.com", "port": 443, "protocol": "tls",
         "severity": "HIGH"},
    ])
    # Session B: shared (different tls_version) + only-b
    _seed_session(Session, ts_b, [
        {"host": "shared.example.com", "port": 443, "protocol": "tls",
         "tls_version": "TLSv1.0", "severity": "HIGH"},
        {"host": "only-b.example.com", "port": 443, "protocol": "tls",
         "severity": "HIGH"},
    ])

    resp = client.get(
        f"/api/compare?a={ts_a.isoformat()}&b={ts_b.isoformat()}"
    )
    # /api/compare does not exist yet — RED until Plan 02 adds it
    assert resp.status_code == 200, (
        f"Expected 200 from /api/compare; got {resp.status_code}"
    )
    data = resp.json()
    assert "only-a.example.com" in data["endpoints_only_in_a"], (
        f"Expected 'only-a.example.com' in endpoints_only_in_a; "
        f"got {data['endpoints_only_in_a']}"
    )
    assert "only-b.example.com" in data["endpoints_only_in_b"], (
        f"Expected 'only-b.example.com' in endpoints_only_in_b; "
        f"got {data['endpoints_only_in_b']}"
    )
    changed_hosts = [e["host"] for e in data.get("changed_endpoints", [])]
    assert "shared.example.com" in changed_hosts, (
        f"Expected 'shared.example.com' in changed_endpoints; got {changed_hosts}"
    )
