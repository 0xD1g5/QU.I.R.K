"""Phase 121 live-UAT regression — /api/jobs/{id}/result-summary window semantics.

The original implementation counted endpoints in a same-second window anchored
on ScanJob.scan_run_id (the run START timestamp). Endpoints carry per-probe
scanned_at values spread across the whole run, so any scan longer than ~1s
counted zero and the dashboard showed a false "no endpoints found" message
(caught live: job ae77122d, 44 endpoints, reported 0). The endpoint must count
over the job's own [started_at, completed_at] lifetime window.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from quirk.dashboard.api.app import create_app
from quirk.dashboard.api.deps import get_db
from quirk.models import Base, CryptoEndpoint, ScanJob


def _app_with_db():
    # StaticPool: single shared connection so the in-memory schema is visible
    # to every session (plain sqlite:// gives each connection its own DB).
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
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
    return app, TestClient(app, raise_server_exceptions=False), TestingSession


def _seed_job(session, *, job_id, started_at, completed_at, scan_run_id):
    session.add(ScanJob(
        job_id=job_id,
        status="completed",
        current_stage="reports",
        target="127.0.0.1",
        profile="deep",
        calibration="balanced",
        enable_nmap=True,
        started_at=started_at,
        completed_at=completed_at,
        scan_run_id=scan_run_id,
    ))


def test_counts_endpoints_spread_across_run_window():
    """Endpoints probed minutes after run start must still be counted."""
    _, client, Session = _app_with_db()
    start = datetime(2026, 6, 11, 23, 59, 33, 528595)
    end = start + timedelta(minutes=2)
    with Session() as s:
        _seed_job(
            s,
            job_id="job-spread",
            started_at=start,
            completed_at=end,
            scan_run_id="2026-06-11T23:59:34.705134+00:00",
        )
        # Per-probe timestamps: 12s and 108s after run start — both outside
        # the old same-second window on scan_run_id.
        for i, offset in enumerate((12, 108)):
            s.add(CryptoEndpoint(
                host="127.0.0.1",
                port=15000 + i,
                protocol="TLS",
                scanned_at=start + timedelta(seconds=offset),
            ))
        s.commit()

    resp = client.get("/api/jobs/job-spread/result-summary")
    assert resp.status_code == 200
    assert resp.json() == {"endpoint_count": 2}


def test_zero_when_no_endpoints_in_window():
    """A genuinely empty scan reports zero (zero-result signal intact)."""
    _, client, Session = _app_with_db()
    start = datetime(2026, 6, 11, 10, 0, 0)
    with Session() as s:
        _seed_job(
            s,
            job_id="job-empty",
            started_at=start,
            completed_at=start + timedelta(minutes=1),
            scan_run_id="2026-06-11T10:00:01+00:00",
        )
        # Endpoint from an unrelated earlier scan — outside this job's window.
        s.add(CryptoEndpoint(
            host="10.0.0.1",
            port=443,
            protocol="TLS",
            scanned_at=start - timedelta(hours=3),
        ))
        s.commit()

    resp = client.get("/api/jobs/job-empty/result-summary")
    assert resp.status_code == 200
    assert resp.json() == {"endpoint_count": 0}


def test_failsafe_zero_when_started_at_missing():
    _, client, Session = _app_with_db()
    with Session() as s:
        _seed_job(
            s,
            job_id="job-nostart",
            started_at=None,
            completed_at=None,
            scan_run_id=None,
        )
        s.commit()

    resp = client.get("/api/jobs/job-nostart/result-summary")
    assert resp.status_code == 200
    assert resp.json() == {"endpoint_count": 0}


def test_unknown_job_404():
    _, client, _ = _app_with_db()
    assert client.get("/api/jobs/nope/result-summary").status_code == 404


def test_scan_latest_falls_back_to_job_window_for_scan_run_id():
    """/api/scan/latest?scan_id=<scan_run_id> must not 404 for real jobs.

    useJobStatus sets selectedScanId = scan_run_id (run START) on completion.
    No endpoint shares that second, so the same-second window is empty; the
    endpoint must fall back to the owning job's [started_at, completed_at]
    window (second live-UAT defect, Phase 121 — old useScanData 404 message).
    """
    _, client, Session = _app_with_db()
    scan_run_id = "2026-06-12T00:17:36.889351+00:00"
    start = datetime(2026, 6, 12, 0, 17, 35, 670448)
    end = datetime(2026, 6, 12, 0, 19, 29, 327216)
    with Session() as s:
        _seed_job(
            s,
            job_id="job-nav",
            started_at=start,
            completed_at=end,
            scan_run_id=scan_run_id,
        )
        # Endpoint probed ~80s after run start — outside the scan_run_id second.
        s.add(CryptoEndpoint(
            host="127.0.0.1",
            port=443,
            protocol="TLS",
            scanned_at=start + timedelta(seconds=80),
            tls_version="TLSv1.3",
        ))
        s.commit()

    resp = client.get(f"/api/scan/latest?scan_id={scan_run_id.replace('+', '%2B')}")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["meta"]["total_endpoints"] == 1


def test_scan_latest_unknown_scan_id_still_404():
    """A scan_id matching neither endpoints nor any job keeps the 404 contract."""
    _, client, Session = _app_with_db()
    with Session() as s:
        s.commit()
    resp = client.get("/api/scan/latest?scan_id=2030-01-01T00:00:00")
    assert resp.status_code == 404
