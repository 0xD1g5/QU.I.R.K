"""Phase 193 / Plan 06 / Task 1 — D-08 server-side connector-availability gate.

`POST /api/jobs` must reject a submission that would run an unavailable
connector, whether the operator toggled it explicitly (`payload.connectors`)
or a profile preset (e.g. `deep`) silently enabled it (T-193-23/T-193-24).
The gate calls the SAME `probe_all_connectors()` helper the GET
`/api/connectors/availability` route calls (RESEARCH Pitfall 4 — never a
second ad hoc availability check).
"""
from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from quirk.dashboard.api.app import create_app
from quirk.dashboard.api.connector_availability import ConnectorAvailability, probe_all_connectors
from quirk.dashboard.api.deps import get_db
from quirk.models import ScanJob
from tests.conftest import make_isolated_memory_engine


def _make_test_engine():
    return make_isolated_memory_engine()


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


class _FakeProc:
    def __init__(self):
        self.pid = 99999
        self.returncode = None

    def poll(self):
        return self.returncode


def _fake_popen(*args, **kwargs):
    return _FakeProc()


def _availability_with_overrides(**overrides) -> dict:
    """Real probe results with specific flags' `available`/`reason` overridden.

    Never a hand-listed fake map for the whole 25-connector surface — start
    from the real probe (whatever this environment's real availability is)
    and override only the flags the test cares about, so the fake stays
    honest about every other connector.
    """
    real = probe_all_connectors()
    for flag, (available, reason) in overrides.items():
        entry = real[flag]
        real[flag] = ConnectorAvailability(
            flag=flag,
            available=available,
            reason=reason,
            install_hint=entry.install_hint,
            category=entry.category,
            label=entry.label,
        )
    return real


def _patch_probe(monkeypatch, **overrides):
    fake_map = _availability_with_overrides(**overrides)
    monkeypatch.setattr(
        "quirk.dashboard.api.connector_availability.probe_all_connectors",
        lambda: fake_map,
    )


# ---------------------------------------------------------------------------
# 1. Unavailable connector explicitly toggled -> 422 naming the reason
# ---------------------------------------------------------------------------

def test_unavailable_connector_toggle_rejected_422(monkeypatch):
    monkeypatch.setattr("quirk.dashboard.api.routes.jobs.subprocess.Popen", _fake_popen)
    _patch_probe(monkeypatch, enable_db=(False, "psycopg2 is not importable"))

    _app, tc, _Session = _app_with_db()
    response = tc.post(
        "/api/jobs",
        json={"targets": "example.com", "profile": "quick", "connectors": {"enable_db": True}},
        headers={"X-Quirk-Request": "1"},
    )
    assert response.status_code == 422, response.text
    assert "psycopg2 is not importable" in response.text


# ---------------------------------------------------------------------------
# 2. Same submission, probe reports available -> normal success
# ---------------------------------------------------------------------------

def test_available_connector_toggle_succeeds(monkeypatch):
    monkeypatch.setattr("quirk.dashboard.api.routes.jobs.subprocess.Popen", _fake_popen)
    _patch_probe(monkeypatch, enable_db=(True, ""))

    _app, tc, _Session = _app_with_db()
    response = tc.post(
        "/api/jobs",
        json={"targets": "example.com", "profile": "quick", "connectors": {"enable_db": True}},
        headers={"X-Quirk-Request": "1"},
    )
    assert response.status_code == 201, response.text


# ---------------------------------------------------------------------------
# 3. Multiple unavailable connectors -> single 422 naming all of them
# ---------------------------------------------------------------------------

def test_multiple_unavailable_connectors_named_in_one_422(monkeypatch):
    monkeypatch.setattr("quirk.dashboard.api.routes.jobs.subprocess.Popen", _fake_popen)
    _patch_probe(
        monkeypatch,
        enable_db=(False, "psycopg2 is not importable"),
        enable_kerberos=(False, "impacket is not importable"),
    )

    _app, tc, _Session = _app_with_db()
    response = tc.post(
        "/api/jobs",
        json={
            "targets": "example.com",
            "profile": "quick",
            "connectors": {"enable_db": True, "enable_kerberos": True},
        },
        headers={"X-Quirk-Request": "1"},
    )
    assert response.status_code == 422, response.text
    body = response.text
    assert "Database TLS" in body
    assert "Kerberos" in body


# ---------------------------------------------------------------------------
# 4. Rejected submission leaves no ScanJob row and writes no config.yaml
# ---------------------------------------------------------------------------

def test_rejected_submission_writes_no_row_or_config(monkeypatch, tmp_path):
    monkeypatch.setattr("quirk.dashboard.api.routes.jobs.subprocess.Popen", _fake_popen)
    _patch_probe(monkeypatch, enable_db=(False, "psycopg2 is not importable"))

    _app, tc, TestingSession = _app_with_db()
    db_before = TestingSession()
    count_before = db_before.query(ScanJob).count()
    db_before.close()

    response = tc.post(
        "/api/jobs",
        json={"targets": "example.com", "profile": "quick", "connectors": {"enable_db": True}},
        headers={"X-Quirk-Request": "1"},
    )
    assert response.status_code == 422

    db_after = TestingSession()
    count_after = db_after.query(ScanJob).count()
    db_after.close()
    assert count_after == count_before

    # No NEW job output directory was created for this rejected submission.
    # The gate runs before job_id/output_dir are even allocated, so comparing
    # a before/after snapshot of output/jobs/ (which may already contain
    # debris from unrelated successful job-creation tests sharing this
    # process's cwd) is the only sound check — a bare existence assertion
    # would false-fail on that pre-existing debris.
    import quirk.dashboard.api.routes.jobs as jobs_module

    jobs_dir = jobs_module._job_output_dir("does-not-exist").parent
    before_children = set(jobs_dir.iterdir()) if jobs_dir.exists() else set()

    response2 = tc.post(
        "/api/jobs",
        json={"targets": "example.com", "profile": "quick", "connectors": {"enable_db": True}},
        headers={"X-Quirk-Request": "1"},
    )
    assert response2.status_code == 422

    after_children = set(jobs_dir.iterdir()) if jobs_dir.exists() else set()
    assert after_children == before_children


# ---------------------------------------------------------------------------
# 5. Preset-enabled path: deep profile auto-enables email/broker; if the
#    probe reports one unavailable, the gate still 422s even with no
#    explicit `connectors` delta in the payload (T-193-24 / open question 1).
# ---------------------------------------------------------------------------

def test_preset_enabled_unavailable_connector_rejected_422(monkeypatch):
    monkeypatch.setattr("quirk.dashboard.api.routes.jobs.subprocess.Popen", _fake_popen)
    _patch_probe(monkeypatch, enable_email=(False, "sslyze is not importable"))

    _app, tc, _Session = _app_with_db()
    response = tc.post(
        "/api/jobs",
        json={"targets": "example.com", "profile": "deep"},
        headers={"X-Quirk-Request": "1"},
    )
    assert response.status_code == 422, response.text
    assert "sslyze is not importable" in response.text


# ---------------------------------------------------------------------------
# 6. Available-connector / no-connectors-field submissions are unaffected —
#    regression guard against the existing happy path.
# ---------------------------------------------------------------------------

def test_no_connectors_field_submission_unaffected(monkeypatch):
    monkeypatch.setattr("quirk.dashboard.api.routes.jobs.subprocess.Popen", _fake_popen)

    _app, tc, _Session = _app_with_db()
    response = tc.post(
        "/api/jobs",
        json={"targets": "example.com", "profile": "quick"},
        headers={"X-Quirk-Request": "1"},
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "running"
