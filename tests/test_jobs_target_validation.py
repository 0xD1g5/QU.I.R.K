"""RED test — AUDIT-07: POST /api/jobs must validate and normalize target tokens.

Contract:
  1. Targets containing empty, whitespace-only, or syntactically invalid tokens
     (not a valid IP, CIDR, or hostname) must be rejected with HTTP 422 and an
     error body identifying the bad tokens.
  2. Valid targets with leading/trailing whitespace must be stored stripped
     (no whitespace padding in the persisted target or config).

Both cases MUST FAIL against current main because create_job passes raw targets
to _write_job_config which splits on "," and strips whitespace-only tokens, but
does NOT shape-validate each token (e.g. "not-an-ip-or-hostname!" is currently
accepted and would be passed to a scan subprocess as a target). Wave 2
(plan 131-02) will wire parse_target_tokens into create_job.

pytest -q tests/test_jobs_target_validation.py
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from quirk.dashboard.api.app import create_app
from quirk.dashboard.api.deps import get_db
from quirk.models import Base, ScanJob


# ---------------------------------------------------------------------------
# Test DB + TestClient factory (mirrors test_jobs_api.py pattern)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Fake Popen stub — prevents actual scan subprocess spawning in tests
# ---------------------------------------------------------------------------

class _FakeProc:
    def __init__(self):
        self.pid = 99999
        self.returncode = None

    def poll(self):
        return self.returncode


def _fake_popen(*args, **kwargs):
    return _FakeProc()


# ---------------------------------------------------------------------------
# Test 1 (RED): invalid/empty targets rejected with 422
# ---------------------------------------------------------------------------

def test_invalid_targets_rejected_422(monkeypatch, tmp_path):
    """AUDIT-07 RED: POST /api/jobs with syntactically invalid targets must
    return 422 with the bad token(s) identified in the error body.

    Payload: ", 10.0.0.1 ,not-an-ip-or-hostname!" contains:
      - "" (empty after comma)
      - "10.0.0.1" (valid)
      - "not-an-ip-or-hostname!" (invalid: ! is not allowed in a hostname)

    EXPECTED FAILURE: current create_job does NOT validate token shapes;
    it passes the raw target string through to _write_job_config and then
    to the scan subprocess. The 422 will NOT be returned today.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("quirk.dashboard.api.routes.jobs.subprocess.Popen", _fake_popen)
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)

    _app, tc, _ = _app_with_db()
    response = tc.post(
        "/api/jobs",
        json={"targets": ", 10.0.0.1 ,not-an-ip-or-hostname!"},
        headers={"X-Quirk-Request": "1"},
    )

    assert response.status_code == 422, (
        f"AUDIT-07 RED: expected 422 for invalid targets, "
        f"got {response.status_code}: {response.text}. "
        "Wave 2 (131-02) will wire parse_target_tokens validation into create_job."
    )

    # Error body should identify the bad token
    body_text = response.text
    # The invalid token or some error description must appear
    assert (
        "not-an-ip-or-hostname!" in body_text
        or "invalid" in body_text.lower()
        or "target" in body_text.lower()
    ), (
        f"AUDIT-07 RED: 422 response body must identify the invalid token, got: {body_text!r}"
    )


def test_whitespace_only_target_rejected_422(monkeypatch, tmp_path):
    """AUDIT-07 RED: a targets string of only commas and whitespace must return 422.

    "  ,  ,  " yields no valid tokens after stripping; create_job should reject
    this as "no valid targets provided" rather than spawning a scan with an empty
    target list.

    EXPECTED FAILURE: current code spawns a scan with empty fqdns/cidrs list.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("quirk.dashboard.api.routes.jobs.subprocess.Popen", _fake_popen)
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)

    _app, tc, _ = _app_with_db()
    response = tc.post(
        "/api/jobs",
        json={"targets": "  ,  ,  "},
        headers={"X-Quirk-Request": "1"},
    )

    assert response.status_code == 422, (
        f"AUDIT-07 RED: expected 422 for whitespace-only targets, "
        f"got {response.status_code}: {response.text}. "
        "Wave 2 (131-02) will add empty-token guard."
    )


# ---------------------------------------------------------------------------
# Test 2 (RED): valid whitespace-padded targets stored stripped
# ---------------------------------------------------------------------------

def test_valid_targets_stored_stripped(monkeypatch, tmp_path):
    """AUDIT-07 RED: valid targets with whitespace padding must be stored stripped.

    Payload: " 10.0.0.1 ,example.com " — both tokens are valid but have
    leading/trailing whitespace.  After AUDIT-07 is fixed, the persisted
    ScanJob.target should have each token stripped (no padding).

    This test asserts the stored job.target contains stripped tokens.
    EXPECTED FAILURE: current code stores the raw comma-string with padding.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("quirk.dashboard.api.routes.jobs.subprocess.Popen", _fake_popen)
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)

    app, tc, TestingSession = _app_with_db()
    response = tc.post(
        "/api/jobs",
        json={"targets": " 10.0.0.1 ,example.com "},
        headers={"X-Quirk-Request": "1"},
    )

    # Job must be created (201) — both tokens are valid
    assert response.status_code == 201, (
        f"Valid padded targets must create a job (201), got {response.status_code}: {response.text}"
    )
    data = response.json()
    job_id = data["job_id"]

    # Fetch the persisted row
    db = TestingSession()
    try:
        row = db.get(ScanJob, job_id)
        assert row is not None, "ScanJob row must exist after POST /api/jobs"

        # After AUDIT-07 fix: stored target must be stripped
        # Currently stores the raw padded string " 10.0.0.1 ,example.com "
        stored_target = row.target
        tokens = [t for t in stored_target.split(",") if t]
        for tok in tokens:
            assert tok == tok.strip(), (
                f"AUDIT-07 RED: stored target token {tok!r} has leading/trailing whitespace. "
                "Wave 2 (131-02) will normalize tokens before storing."
            )
    finally:
        db.close()
