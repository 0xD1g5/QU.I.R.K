"""Phase 65 — /api/jobs router tests (UI-SCAN-01/02/03).

Plan 03 fills in 10 of the 11 test bodies. test_stale_job_recovery remains
a skip stub until Plan 04 lands the lifespan _recover_stale_jobs function.
"""
from __future__ import annotations

import sys

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
    def __init__(self, pid=99999, returncode=None):
        self.pid = pid
        self.returncode = returncode

    def poll(self):
        return self.returncode


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
    assert "QRK-DASHBOARD-008" in data["detail"]


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
# Test 11: stale_job_recovery — Plan 04 lifespan + _recover_stale_jobs
# --------------------------------------------------------------------------

def test_stale_job_recovery(tmp_path):
    """Phase 65 D-12: _recover_stale_jobs flips running jobs to failed."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from quirk.dashboard.api.app import _recover_stale_jobs
    from quirk.models import Base, ScanJob

    db_file = str(tmp_path / "test.db")
    engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)

    # Seed two rows: one running, one already completed
    with Session() as db:
        db.add(ScanJob(
            job_id="stale-1", status="running", target="x.com",
            profile="standard", calibration="balanced", enable_nmap=False,
        ))
        db.add(ScanJob(
            job_id="done-1", status="completed", target="y.com",
            profile="standard", calibration="balanced", enable_nmap=False,
        ))
        db.commit()

    _recover_stale_jobs(db_file)

    with Session() as db:
        stale = db.get(ScanJob, "stale-1")
        done = db.get(ScanJob, "done-1")
        assert stale.status == "failed"
        assert stale.error_message == "API restarted — job lost"
        assert stale.completed_at is not None
        # Completed row must NOT be touched
        assert done.status == "completed"
        assert done.error_message is None


# --------------------------------------------------------------------------
# Test 12: POST /api/jobs captures subprocess output to a per-job log file
# --------------------------------------------------------------------------

def test_post_job_captures_subprocess_output(monkeypatch, tmp_path):
    """Popen must receive a real stdout file (not DEVNULL) and create run.log."""
    import subprocess as _sp

    monkeypatch.chdir(tmp_path)  # keep output/jobs/ inside the tmp dir
    captured = {}

    def _recording_popen(cmd, **kwargs):
        captured.update(kwargs)
        return _FakeProc()

    monkeypatch.setattr("quirk.dashboard.api.routes.jobs.subprocess.Popen", _recording_popen)

    _app, tc, _ = _app_with_db()
    response = tc.post(
        "/api/jobs",
        json={"targets": "example.com", "profile": "quick"},
        headers={"X-Quirk-Request": "1"},
    )
    assert response.status_code == 201, response.text
    job_id = response.json()["job_id"]

    # stdout is a writable file object, stderr folds into it — not DEVNULL.
    assert captured["stdout"] is not _sp.DEVNULL
    assert hasattr(captured["stdout"], "write")
    assert captured["stderr"] == _sp.STDOUT

    log_path = tmp_path / "output" / "jobs" / job_id / "run.log"
    assert log_path.exists()


# --------------------------------------------------------------------------
# Test 13: GET /api/jobs/{id} reconciles a dead subprocess to `failed`
# --------------------------------------------------------------------------

def test_get_job_reconciles_dead_process(monkeypatch):
    """A `running` job whose registered subprocess has exited flips to `failed`."""
    import quirk.dashboard.api.routes.jobs as jobs_mod

    dead = _FakeProc(pid=424242, returncode=3)
    monkeypatch.setattr(jobs_mod, "_PROCS", {"dead-1": dead}, raising=False)

    _app, tc, TestingSession = _app_with_db()
    db = TestingSession()
    db.add(ScanJob(
        job_id="dead-1", pid=424242, status="running", target="x.com",
        profile="quick", calibration="balanced", enable_nmap=False,
    ))
    db.commit()
    db.close()

    response = tc.get("/api/jobs/dead-1")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "failed"
    assert data["completed_at"] is not None
    assert "run.log" in data["error_message"]
    assert "exit code 3" in data["error_message"]
    # Reconciled procs leave the registry so the handle is not held forever.
    assert "dead-1" not in jobs_mod._PROCS


# --------------------------------------------------------------------------
# Test 14: GET /api/jobs/{id} keeps `running` while the subprocess is alive
# --------------------------------------------------------------------------

def test_get_job_keeps_running_when_alive(monkeypatch):
    """A registered subprocess with poll() == None must not be reconciled away."""
    import quirk.dashboard.api.routes.jobs as jobs_mod

    alive = _FakeProc(pid=12345, returncode=None)
    monkeypatch.setattr(jobs_mod, "_PROCS", {"alive-1": alive}, raising=False)

    _app, tc, TestingSession = _app_with_db()
    db = TestingSession()
    db.add(ScanJob(
        job_id="alive-1", pid=12345, status="running", target="x.com",
        profile="quick", calibration="balanced", enable_nmap=False,
    ))
    db.commit()
    db.close()

    response = tc.get("/api/jobs/alive-1")
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "running"
    assert "alive-1" in jobs_mod._PROCS


# --------------------------------------------------------------------------
# Test 15: GET /api/jobs/{id} leaves unregistered running jobs alone
# --------------------------------------------------------------------------

def test_get_job_unregistered_proc_left_to_startup_sweep(monkeypatch):
    """A `running` row with no registry entry (API restarted since spawn) is
    not reconciled here — the startup sweep (_recover_stale_jobs) owns it."""
    import quirk.dashboard.api.routes.jobs as jobs_mod

    monkeypatch.setattr(jobs_mod, "_PROCS", {}, raising=False)

    _app, tc, TestingSession = _app_with_db()
    db = TestingSession()
    db.add(ScanJob(
        job_id="orphan-1", pid=424242, status="running", target="x.com",
        profile="quick", calibration="balanced", enable_nmap=False,
    ))
    db.commit()
    db.close()

    response = tc.get("/api/jobs/orphan-1")
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "running"


# --------------------------------------------------------------------------
# Test 16: POST /api/jobs registers the Popen handle for liveness checks
# --------------------------------------------------------------------------

def test_create_job_registers_proc(monkeypatch, tmp_path):
    """create_job must keep the Popen handle in _PROCS keyed by job_id."""
    import quirk.dashboard.api.routes.jobs as jobs_mod

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(jobs_mod, "_PROCS", {}, raising=False)
    fake = _FakeProc()
    monkeypatch.setattr("quirk.dashboard.api.routes.jobs.subprocess.Popen", lambda *a, **k: fake)

    _app, tc, _ = _app_with_db()
    response = tc.post(
        "/api/jobs",
        json={"targets": "example.com", "profile": "quick"},
        headers={"X-Quirk-Request": "1"},
    )
    assert response.status_code == 201, response.text
    job_id = response.json()["job_id"]
    assert jobs_mod._PROCS.get(job_id) is fake


# --------------------------------------------------------------------------
# Test 17: zombie regression — an exited-but-unreaped child must reconcile
# --------------------------------------------------------------------------

@pytest.mark.skipif(sys.platform != "linux", reason="zombie-state check reads /proc")
def test_get_job_reconciles_real_zombie(monkeypatch, tmp_path):
    """Regression for the zombie bug: the server never wait()s its children, so
    a crashed scan sits as a zombie. os.kill(zombie, 0) succeeds — pid-based
    liveness reports it alive forever. poll()-based liveness must reap it and
    flip the job to failed."""
    import subprocess as _sp
    import time

    import quirk.dashboard.api.routes.jobs as jobs_mod

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(jobs_mod, "_PROCS", {}, raising=False)

    spawned = {}
    # jobs.py imports the subprocess *module*, so patching its Popen mutates the
    # shared module — grab the real constructor first to avoid self-recursion.
    real_popen = _sp.Popen

    def _spawn_short_lived(cmd, **kwargs):
        proc = real_popen(
            [sys.executable, "-c", "import sys; sys.exit(7)"],
            stdin=kwargs.get("stdin"),
            stdout=kwargs.get("stdout"),
            stderr=kwargs.get("stderr"),
        )
        spawned["proc"] = proc
        return proc

    monkeypatch.setattr("quirk.dashboard.api.routes.jobs.subprocess.Popen", _spawn_short_lived)

    _app, tc, _ = _app_with_db()
    response = tc.post(
        "/api/jobs",
        json={"targets": "example.com", "profile": "quick"},
        headers={"X-Quirk-Request": "1"},
    )
    assert response.status_code == 201, response.text
    job_id = response.json()["job_id"]
    pid = spawned["proc"].pid

    # Wait for the child to exit WITHOUT reaping it (no wait/poll here): its
    # /proc stat state must reach Z (zombie).
    for _ in range(100):
        with open(f"/proc/{pid}/stat") as fh:
            state = fh.read().rsplit(")", 1)[1].split()[0]
        if state == "Z":
            break
        time.sleep(0.05)
    else:
        pytest.fail("child never reached zombie state")

    resp = tc.get(f"/api/jobs/{job_id}")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "failed", (
        "zombie child must reconcile to failed — pid-based liveness cannot see it"
    )
    assert "exit code 7" in data["error_message"]
