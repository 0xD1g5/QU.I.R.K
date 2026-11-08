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


def test_scan_coverage_serves_missing_binary_skip_verbatim(tmp_path, monkeypatch):
    """Phase 235.1 D-05: missing-binary skipped rows (semgrep + syft) are served as-is."""
    scan_run_id = "run-cov-mb"
    db_path = str(tmp_path / "coverage_mb.db")
    init_db(db_path)
    with get_session(db_path) as session:
        session.add_all([
            ScanPhaseRecord(
                scan_run_id=scan_run_id, phase_name="source_scanning",
                status="skipped", reason="missing-binary",
                detail="semgrep is not installed (QRK-INSTALL-008)",
                recorded_at=_now(),
            ),
            ScanPhaseRecord(
                scan_run_id=scan_run_id, phase_name="container_scanning",
                status="skipped", reason="missing-binary",
                detail="syft is not installed (QRK-INSTALL-007)",
                recorded_at=_now(),
            ),
        ])
        session.commit()
    client = _client(monkeypatch, db_path)

    resp = client.get(f"/api/scans/{scan_run_id}/coverage")
    assert resp.status_code == 200
    data = resp.json()
    assert data["recorded"] is True
    assert data["skipped"] == 2
    by_name = {p["phase_name"]: p for p in data["phases"]}
    src = by_name["source_scanning"]
    assert src["status"] == "skipped"
    assert src["reason"] == "missing-binary"
    assert src["detail"] == "semgrep is not installed (QRK-INSTALL-008)"
    ctr = by_name["container_scanning"]
    assert ctr["reason"] == "missing-binary"
    assert "QRK-INSTALL-007" in ctr["detail"]


def _latest_client(monkeypatch, db_path, scan_run_id):
    """TestClient whose get_db is bound to the seeded file DB, with a completed
    ScanJob so /api/scan/latest resolves *scan_run_id*."""
    from quirk.db import get_engine

    Session = sessionmaker(bind=get_engine(db_path), autoflush=False, autocommit=False)
    with Session() as s:
        s.add(ScanJob(
            job_id="job-" + scan_run_id, status="completed", target="127.0.0.1",
            profile="standard", calibration="balanced", scan_run_id=scan_run_id,
            completed_at=_now(),
        ))
        s.commit()

    def override_get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr("quirk.dashboard.api.routes.scan._default_db_path", lambda: db_path)
    return TestClient(app, headers={"X-Quirk-Request": "1"})


def test_scan_coverage_serves_internal_target_and_auth_failed_verbatim(tmp_path, monkeypatch):
    """Phase 235.3 D-09: the two new skip reasons are served as-is by the coverage
    route and carried identically on /api/scan/latest.coverage."""
    from quirk.models import CryptoEndpoint

    scan_run_id = "run-cov-new"
    db_path = str(tmp_path / "coverage_new.db")
    init_db(db_path)
    jwt_detail = (
        "1 of 1 targets were refused by the internal-target guard: "
        "http://localhost:20001 (refused: loopback); "
        "security.allow_internal_targets is false"
    )
    s3_detail = "https://s3.example.com (auth_failed: InvalidAccessKeyId)"
    with get_session(db_path) as session:
        session.add_all([
            ScanPhaseRecord(
                scan_run_id=scan_run_id, phase_name="tls_scanning", status="ran",
                duration_sec=1.0, recorded_at=_now(),
            ),
            ScanPhaseRecord(
                scan_run_id=scan_run_id, phase_name="jwt_scanning", status="skipped",
                reason="internal-target-refused", detail=jwt_detail, recorded_at=_now(),
            ),
            ScanPhaseRecord(
                scan_run_id=scan_run_id, phase_name="s3_scanning", status="skipped",
                reason="auth-failed", detail=s3_detail, recorded_at=_now(),
            ),
            CryptoEndpoint(
                host="10.0.0.5", port=443, protocol="TLS", tls_version="TLSv1.3",
                scan_run_id=scan_run_id,
            ),
        ])
        session.commit()
    client = _latest_client(monkeypatch, db_path, scan_run_id)

    resp = client.get(f"/api/scans/{scan_run_id}/coverage")
    assert resp.status_code == 200
    data = resp.json()
    assert data["skipped"] == 2 and data["ran"] == 1
    by_name = {p["phase_name"]: p for p in data["phases"]}
    assert by_name["jwt_scanning"]["reason"] == "internal-target-refused"
    assert by_name["jwt_scanning"]["detail"] == jwt_detail
    assert by_name["s3_scanning"]["reason"] == "auth-failed"
    assert by_name["s3_scanning"]["detail"] == s3_detail

    latest = client.get("/api/scan/latest")
    assert latest.status_code == 200
    lat = {p["phase_name"]: p for p in latest.json()["coverage"]["phases"]}
    for name in ("jwt_scanning", "s3_scanning"):
        assert lat[name]["reason"] == by_name[name]["reason"]
        assert lat[name]["detail"] == by_name[name]["detail"]


def test_scan_latest_failed_db_rows_two_failed_one_healthy(tmp_path, monkeypatch):
    """Phase 235.3 D-10: two failed + one healthy Postgres target -> three
    database DarFindings on /api/scan/latest, two carrying scan_error."""
    from quirk.models import CryptoEndpoint

    scan_run_id = "run-cov-db"
    db_path = str(tmp_path / "coverage_db.db")
    init_db(db_path)
    with get_session(db_path) as session:
        session.add_all([
            CryptoEndpoint(
                host="pg-ok.test", port=5432, protocol="POSTGRESQL",
                service_detail="PostgreSQL/ssl-enforced", scan_run_id=scan_run_id,
            ),
            CryptoEndpoint(
                host="pg-bad1.test", port=5432, protocol="POSTGRESQL",
                scan_error="connection-error: could not connect", scan_run_id=scan_run_id,
            ),
            CryptoEndpoint(
                host="pg-bad2.test", port=5432, protocol="POSTGRESQL",
                scan_error="connection-error: timed out", scan_run_id=scan_run_id,
            ),
        ])
        session.commit()
    client = _latest_client(monkeypatch, db_path, scan_run_id)

    resp = client.get("/api/scan/latest")
    assert resp.status_code == 200
    dar = [f for f in resp.json()["dar_findings"] if f["category"] == "database"]
    assert len(dar) == 3, dar
    failed = [f for f in dar if f.get("scan_error")]
    assert len(failed) == 2
    assert {f["host"] for f in failed} == {"pg-bad1.test", "pg-bad2.test"}
    assert all(f["title"] == "POSTGRESQL connection failed" for f in failed)


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


# ---------------------------------------------------------------------------
# 235.3 review C-WR-04: the dashboard tells the two "failed" writers apart
# ---------------------------------------------------------------------------

def _dashboard_no_target_answered_regex():
    import pathlib
    import re as _re

    src = (
        pathlib.Path(__file__).resolve().parents[1]
        / "src" / "dashboard" / "src" / "lib" / "coverage-reason.ts"
    ).read_text(encoding="utf-8")
    m = _re.search(r"export const NO_TARGET_ANSWERED_DETAIL = /(.+)/\n", src)
    assert m, "NO_TARGET_ANSWERED_DETAIL regex not found in coverage-reason.ts"
    return _re.compile(m.group(1))


def test_dashboard_failed_detail_regex_matches_the_real_unreachable_detail():
    """C-WR-04 contract: coverage-reason.ts reads a "failed" row as "no target
    answered" only when its detail has the shape run_scan writes for the
    every-target-unreachable path; a record_failed exception text must not
    match, or a scanner crash would point the operator at the network."""
    import run_scan
    from quirk.scanner.target_outcome import OUTCOME_UNREACHABLE, TargetOutcomes

    pattern = _dashboard_no_target_answered_regex()

    outcomes = TargetOutcomes(["db1:5432", "db2:5432"])
    for t in outcomes.expected:
        outcomes.record(t, OUTCOME_UNREACHABLE, "timed out")
    rec = run_scan._PhaseRecorder()
    run_scan._classify_connector_outcomes("db_scanner", outcomes, [], [], rec)
    assert rec._pending_reason == "failed"
    assert pattern.search(rec._pending_detail), rec._pending_detail

    rec.record_failed("db_scanning", "ModuleNotFoundError: No module named 'psycopg2'")
    crash = rec.rows()[-1]
    assert crash["reason"] == "failed"
    assert not pattern.search(crash["detail"])
