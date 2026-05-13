"""Phase 65 — /api/jobs router tests (UI-SCAN-01/02/03).

Plan 03 fills in 10 of the 11 test bodies. test_stale_job_recovery remains
a skip stub until Plan 04 lands the lifespan _recover_stale_jobs function.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from quirk.dashboard.api.app import create_app
from quirk.dashboard.api.deps import get_db
from quirk.models import Base, ScanJob


def _make_test_engine():
    engine = create_engine(
        "sqlite:///file::memory:?cache=shared&uri=true",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    return engine


def _app_with_db():
    engine = _make_test_engine()
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


# --------------------------------------------------------------------------
# Fake Popen helper — prevents actual scan subprocess spawning in tests
# --------------------------------------------------------------------------

class _FakeProc:
    def __init__(self, pid=99999):
        self.pid = pid


def _fake_popen(*args, **kwargs):
    return _FakeProc()


# --------------------------------------------------------------------------
# Test 1: POST /api/jobs creates a scan_jobs row
# --------------------------------------------------------------------------

def test_post_job_creates_row(monkeypatch):
    """POST /api/jobs creates a ScanJob row and returns 201 with job_id + status."""
    monkeypatch.setattr("quirk.dashboard.api.routes.jobs.subprocess.Popen", _fake_popen)

    app, tc, TestingSession = _app_with_db()
    response = tc.post(
        "/api/jobs",
        json={"targets": "example.com", "profile": "quick"},
        headers={"X-Quirk-Request": "1"},
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "running"

    # Confirm DB row created
    db = TestingSession()
    row = db.get(ScanJob, data["job_id"])
    assert row is not None
    assert row.status == "running"
    assert row.target == "example.com"
    assert row.profile == "quick"
    db.close()


# --------------------------------------------------------------------------
# Test 2: POST /api/jobs rejects @file targets (422)
# --------------------------------------------------------------------------

def test_post_job_rejects_file_path():
    """POST /api/jobs with @file target returns 422 with the rejection message."""
    _app, tc, _ = _app_with_db()
    response = tc.post(
        "/api/jobs",
        json={"targets": "@/tmp/x.txt"},
        headers={"X-Quirk-Request": "1"},
    )
    assert response.status_code == 422, response.text
    # The validator message must mention @file
    body = response.text
    assert "@file" in body or "not supported" in body


# --------------------------------------------------------------------------
# Test 3: POST /api/jobs rejects empty targets (422)
# --------------------------------------------------------------------------

def test_post_job_empty_targets():
    """POST /api/jobs with empty targets string returns 422."""
    _app, tc, _ = _app_with_db()
    response = tc.post(
        "/api/jobs",
        json={"targets": ""},
        headers={"X-Quirk-Request": "1"},
    )
    assert response.status_code == 422, response.text


# --------------------------------------------------------------------------
# Test 4: POST /api/jobs requires auth (401 when QUIRK_API_TOKEN set)
# --------------------------------------------------------------------------

def test_post_job_requires_auth(monkeypatch):
    """POST /api/jobs without Authorization header returns 401 when token is configured."""
    monkeypatch.setenv("QUIRK_API_TOKEN", "test-secret-token")
    _app, tc, _ = _app_with_db()
    response = tc.post(
        "/api/jobs",
        json={"targets": "example.com"},
        headers={"X-Quirk-Request": "1"},
        # No Authorization header
    )
    assert response.status_code == 401, response.text


# --------------------------------------------------------------------------
# Test 5: POST /api/jobs requires CSRF header (403 without it)
# --------------------------------------------------------------------------

def test_post_job_requires_csrf(monkeypatch):
    """POST /api/jobs without X-Quirk-Request returns 403."""
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)
    _app, tc, _ = _app_with_db()
    response = tc.post(
        "/api/jobs",
        json={"targets": "example.com"},
        # No X-Quirk-Request header
    )
    assert response.status_code == 403, response.text


# --------------------------------------------------------------------------
# Test 6: GET /api/jobs/{id} returns JobStatusResponse with stage_index
# --------------------------------------------------------------------------

def test_get_job_status():
    """GET /api/jobs/{id} returns 200 with correct JobStatusResponse shape including stage_index=2 for tls."""
    from datetime import datetime, timezone

    app, tc, TestingSession = _app_with_db()

    # Insert a ScanJob row directly via the test DB session
    db = TestingSession()
    job_id = "test-job-001"
    row = ScanJob(
        job_id=job_id,
        status="running",
        current_stage="tls",
        target="example.com",
        profile="standard",
        calibration="balanced",
        enable_nmap=False,
        started_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(row)
    db.commit()
    db.close()

    response = tc.get(f"/api/jobs/{job_id}")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["job_id"] == job_id
    assert data["status"] == "running"
    assert data["current_stage"] == "tls"
    assert data["stage_index"] == 2
    assert data["stage_total"] == 7


# --------------------------------------------------------------------------
# Test 7: GET /api/jobs/{id} returns 404 for unknown job_id
# --------------------------------------------------------------------------

def test_get_job_not_found():
    """GET /api/jobs/{id} with unknown job_id returns 404 with 'Job not found'."""
    _app, tc, _ = _app_with_db()
    response = tc.get("/api/jobs/nonexistent-uuid-abcd1234")
    assert response.status_code == 404, response.text
    data = response.json()
    assert "Job not found" in data["detail"]


# --------------------------------------------------------------------------
# Test 8: GET /api/jobs/{id} requires auth but NOT CSRF
# --------------------------------------------------------------------------

def test_get_job_requires_auth(monkeypatch):
    """GET /api/jobs/{id} requires auth; a request with auth but no CSRF header must NOT return 403."""
    monkeypatch.setenv("QUIRK_API_TOKEN", "test-secret-token")
    _app, tc, _ = _app_with_db()

    # Without auth → 401
    response_no_auth = tc.get("/api/jobs/some-id")
    assert response_no_auth.status_code == 401, response_no_auth.text

    # With valid auth, no CSRF header → should get 404 (not found) NOT 403 (GET is CSRF-exempt)
    authed_client = TestClient(
        _app,
        headers={"Authorization": "Bearer test-secret-token"},
        raise_server_exceptions=False,
    )
    response_authed = authed_client.get("/api/jobs/some-unknown-id")
    assert response_authed.status_code == 404, (
        f"Expected 404 for unknown job (not 403); got {response_authed.status_code}: {response_authed.text}"
    )


# --------------------------------------------------------------------------
# Test 9: _stage_index direct unit test
# --------------------------------------------------------------------------

def test_stage_index_computation():
    """Direct unit test of _stage_index covering all documented mappings."""
    from quirk.dashboard.api.routes.jobs import _stage_index

    assert _stage_index(None, "queued") == 0
    assert _stage_index("discovery", "running") == 1
    assert _stage_index("tls", "running") == 2
    assert _stage_index("ssh", "running") == 3
    assert _stage_index("api", "running") == 4
    assert _stage_index("identity", "running") == 5
    assert _stage_index("data_at_rest", "running") == 6
    assert _stage_index("reports", "running") == 7
    assert _stage_index(None, "completed") == 7
    assert _stage_index("unknown_stage", "running") == 0


# --------------------------------------------------------------------------
# Test 10: DELETE /api/jobs/{id} sends SIGTERM and flips status to cancelled
# --------------------------------------------------------------------------

def test_cancel_job(monkeypatch):
    """DELETE /api/jobs/{id} sends SIGTERM, sets status=cancelled, sets completed_at."""
    from datetime import datetime, timezone

    # Mock os.kill and subprocess.Popen to avoid real signals
    killed_pids = []
    monkeypatch.setattr("quirk.dashboard.api.routes.jobs.os.kill", lambda pid, sig: killed_pids.append(pid))
    monkeypatch.setattr("quirk.dashboard.api.routes.jobs.subprocess.Popen", _fake_popen)

    app, tc, TestingSession = _app_with_db()

    # Insert a running ScanJob with pid=12345
    db = TestingSession()
    job_id = "cancel-job-001"
    row = ScanJob(
        job_id=job_id,
        pid=12345,
        status="running",
        current_stage="tls",
        target="example.com",
        profile="standard",
        calibration="balanced",
        enable_nmap=False,
        started_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(row)
    db.commit()
    db.close()

    # DELETE the job
    response = tc.delete(
        f"/api/jobs/{job_id}",
        headers={"X-Quirk-Request": "1"},
    )
    assert response.status_code == 204, response.text

    # Verify DB row updated
    db = TestingSession()
    updated = db.get(ScanJob, job_id)
    assert updated.status == "cancelled"
    assert updated.completed_at is not None
    db.close()

    # Verify os.kill was called (SIGTERM sent)
    assert 12345 in killed_pids


# --------------------------------------------------------------------------
# Test 11: stale_job_recovery — deferred to Plan 04
# --------------------------------------------------------------------------

def test_stale_job_recovery():
    pytest.skip("Implemented in Plan 04 — lifespan _recover_stale_jobs")
