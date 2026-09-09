"""Phase 192 Plan 09 (OBS-02) — GET /api/scans/{scan_run_id}/coverage and
GET /api/jobs/{job_id}/coverage.

Covers:
  - recorded scan returns the load_scan_coverage() payload verbatim
  - a scan_run_id with no ScanPhaseRecord rows returns 200 recorded:false, not 404
  - the job variant resolves scan_run_id via ScanJob and 404s on unknown job_id
  - the route is auth-gated like the rest of scan.py's router
"""
from __future__ import annotations

import datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from quirk.dashboard.api.app import create_app
from quirk.dashboard.api.deps import get_db
from quirk.db import get_session, init_db
from quirk.models import Base, ScanJob, ScanPhaseRecord
from tests.conftest import make_isolated_memory_engine


def _now():
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)


def _seed_coverage_db(tmp_path, scan_run_id="run-cov-1"):
    db_path = tmp_path / "coverage.db"
    init_db(str(db_path))
    with get_session(str(db_path)) as session:
        session.add_all(
            [
                ScanPhaseRecord(
                    scan_run_id=scan_run_id,
                    phase_name="tls_scanning",
                    status="ran",
                    duration_sec=4.2,
                    recorded_at=_now(),
                ),
                ScanPhaseRecord(
                    scan_run_id=scan_run_id,
                    phase_name="vault_scanning",
                    status="skipped",
                    reason="missing-credentials",
                    detail="VAULT_TOKEN not set",
                    recorded_at=_now(),
                ),
            ]
        )
        session.commit()
    return str(db_path)


def _client(monkeypatch, db_path, scan_job_engine=None):
    app = create_app()
    if scan_job_engine is not None:
        TestingSession = sessionmaker(bind=scan_job_engine, autoflush=False, autocommit=False)

        def override_get_db():
            db = TestingSession()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db

    monkeypatch.setattr("quirk.dashboard.api.routes.scan._default_db_path", lambda: db_path)
    return TestClient(app, headers={"X-Quirk-Request": "1"})


def test_scan_coverage_recorded_matches_loader_payload(tmp_path, monkeypatch):
    db_path = _seed_coverage_db(tmp_path)
    client = _client(monkeypatch, db_path)

    resp = client.get("/api/scans/run-cov-1/coverage")
    assert resp.status_code == 200
    data = resp.json()
    assert data["recorded"] is True
    assert data["ran"] == 1
    assert data["skipped"] == 1
    phase_names = {p["phase_name"] for p in data["phases"]}
    assert phase_names == {"tls_scanning", "vault_scanning"}
    vault = next(p for p in data["phases"] if p["phase_name"] == "vault_scanning")
    assert vault["reason"] == "missing-credentials"
    assert vault["detail"] == "VAULT_TOKEN not set"


def test_scan_coverage_no_rows_returns_200_not_404(tmp_path, monkeypatch):
    db_path = str(tmp_path / "empty.db")
    init_db(db_path)
    client = _client(monkeypatch, db_path)

    resp = client.get("/api/scans/nonexistent-run/coverage")
    assert resp.status_code == 200
    data = resp.json()
    assert data["recorded"] is False
    assert data["ran"] == 0
    assert data["skipped"] == 0
    assert data["phases"] == []


def test_job_coverage_resolves_scan_run_id(tmp_path, monkeypatch):
    db_path = _seed_coverage_db(tmp_path, scan_run_id="run-cov-2")
    engine = make_isolated_memory_engine()
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = TestingSession()
    try:
        db.add(ScanJob(
            job_id="job-1",
            status="completed",
            target="example.com",
            profile="standard",
            calibration="balanced",
            scan_run_id="run-cov-2",
        ))
        db.commit()
    finally:
        db.close()

    client = _client(monkeypatch, db_path, scan_job_engine=engine)
    resp = client.get("/api/jobs/job-1/coverage")
    assert resp.status_code == 200
    data = resp.json()
    assert data["recorded"] is True
    assert data["ran"] == 1
    assert data["skipped"] == 1


def test_job_coverage_unknown_job_id_returns_404(tmp_path, monkeypatch):
    db_path = str(tmp_path / "empty2.db")
    init_db(db_path)
    engine = make_isolated_memory_engine()
    Base.metadata.create_all(engine)

    client = _client(monkeypatch, db_path, scan_job_engine=engine)
    resp = client.get("/api/jobs/does-not-exist/coverage")
    assert resp.status_code == 404


def test_scan_coverage_requires_auth(tmp_path, monkeypatch):
    db_path = _seed_coverage_db(tmp_path)
    monkeypatch.setenv("QUIRK_API_TOKEN", "test-token")
    client = _client(monkeypatch, db_path)

    resp = client.get("/api/scans/run-cov-1/coverage")
    assert resp.status_code == 401

    resp_ok = client.get(
        "/api/scans/run-cov-1/coverage",
        headers={"X-API-Key": "test-token"},
    )
    assert resp_ok.status_code == 200
