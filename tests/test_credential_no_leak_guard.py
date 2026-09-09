"""Phase 193 / Plan 06 / Task 3 — sentinel-string no-leak guard (D-11).

The phase's highest-value test. A run-time-derived sentinel credential is
submitted through the real `POST /api/jobs` path and must provably reach the
subprocess environment (positive control) while provably appearing in NONE
of: the `ScanJob` row's columns, the written job `config.yaml`, `run.log`,
or any captured log record at DEBUG level.

Modeled on this repo's standing "run-time source scan, not a hand-derived
list" idiom (`tests/test_config_connector_drift.py`): the credential payload
is derived from `CREDENTIAL_REGISTRY` at test-run time, and the `ScanJob`
column set searched is derived from `ScanJob.__table__.columns` at test-run
time, so a future credential field or a future column is automatically
covered without a test edit.
"""
from __future__ import annotations

import logging
import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from quirk.config_redaction import CREDENTIAL_REGISTRY
from quirk.dashboard.api.app import create_app
from quirk.dashboard.api.deps import get_db
from quirk.models import ScanJob
from tests.conftest import make_isolated_memory_engine


def _app_with_db():
    engine = make_isolated_memory_engine()
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


class _RecordingLoggingPopen:
    """Records the `env=` kwarg and writes a line to the provided run.log
    file handle — proves the guard's absence assertions aren't vacuous
    because nothing ever reached the subprocess boundary.
    """

    last_env: dict = {}

    def __call__(self, cmd, **kwargs):
        _RecordingLoggingPopen.last_env = dict(kwargs.get("env") or {})
        log_fh = kwargs.get("stdout")
        if log_fh is not None:
            log_fh.write(b"fake scan process started\n")
            log_fh.flush()
        return _FakeProc()


def _credential_payload_for_sentinel(sentinel: str) -> dict:
    """Derive the credentials payload from CREDENTIAL_REGISTRY at run time —
    every 'connectors' section entry, plus one broker: and one snmpv3:auth
    per-host key, ALL set to the sentinel value.
    """
    payload = {
        entry.name: sentinel
        for entry in CREDENTIAL_REGISTRY
        if entry.section == "connectors"
    }
    payload["broker:sentinel-host.example.com"] = sentinel
    payload["snmpv3:sentinel-host.example.com:auth"] = sentinel
    return payload


def test_sentinel_reaches_subprocess_env(monkeypatch):
    """Positive control 1: without this, all absence assertions below could
    pass simply because the credential never reached the subprocess at all.
    """
    sentinel = f"QUIRK-CRED-SENTINEL-{uuid.uuid4().hex}"
    fake_popen = _RecordingLoggingPopen()
    monkeypatch.setattr("quirk.dashboard.api.routes.jobs.subprocess.Popen", fake_popen)

    _app, tc, _Session = _app_with_db()
    response = tc.post(
        "/api/jobs",
        json={
            "targets": "example.com",
            "profile": "quick",
            "credentials": _credential_payload_for_sentinel(sentinel),
        },
        headers={"X-Quirk-Request": "1"},
    )
    assert response.status_code == 201, response.text

    env_values = list(fake_popen.last_env.values())
    assert sentinel in env_values, "sentinel never reached the Popen env= kwarg"


def test_sentinel_search_helper_itself_works(tmp_path):
    """Positive control 2: proves the test's own grep-for-sentinel mechanism
    actually detects a sentinel when one IS present, before trusting its
    absence anywhere else.
    """
    sentinel = f"QUIRK-CRED-SENTINEL-{uuid.uuid4().hex}"
    scratch = tmp_path / "scratch.txt"
    scratch.write_text(f"unrelated line\n{sentinel}\nmore text\n")
    assert sentinel in scratch.read_text()


def test_sentinel_absent_from_row_config_log_and_logrecords(monkeypatch, caplog):
    sentinel = f"QUIRK-CRED-SENTINEL-{uuid.uuid4().hex}"
    fake_popen = _RecordingLoggingPopen()
    monkeypatch.setattr("quirk.dashboard.api.routes.jobs.subprocess.Popen", fake_popen)

    _app, tc, TestingSession = _app_with_db()

    with caplog.at_level(logging.DEBUG):
        response = tc.post(
            "/api/jobs",
            json={
                "targets": "example.com",
                "profile": "quick",
                "credentials": _credential_payload_for_sentinel(sentinel),
            },
            headers={"X-Quirk-Request": "1"},
        )
    assert response.status_code == 201, response.text
    job_id = response.json()["job_id"]

    # Positive control (belt-and-suspenders, re-asserted here against THIS
    # request's own recorded env, not a separate request's).
    assert sentinel in fake_popen.last_env.values()

    # 1. ScanJob row — every column, derived from __table__.columns at
    #    run time so a future column is automatically covered.
    db = TestingSession()
    row = db.get(ScanJob, job_id)
    assert row is not None
    row_values = {c.name: getattr(row, c.name) for c in ScanJob.__table__.columns}
    db.close()
    assert sentinel not in str(row_values), f"sentinel leaked into ScanJob row: {row_values}"

    # 2. Written job config.yaml — sentinel absent, but the expected env-var
    #    NAME for the broker credential IS present (proves the name-not-value
    #    idiom is actually in use, so the absence assertion isn't vacuous).
    import quirk.dashboard.api.routes.jobs as jobs_module

    config_path = jobs_module._job_output_dir(job_id) / "config.yaml"
    config_text = config_path.read_text()
    assert sentinel not in config_text, "sentinel leaked into config.yaml"
    assert "QUIRK_JOB_BROKER_SENTINEL_HOST_EXAMPLE_COM" in config_text

    # 3. run.log — sentinel absent.
    log_path = jobs_module._job_output_dir(job_id) / "run.log"
    log_text = log_path.read_text()
    assert sentinel not in log_text, "sentinel leaked into run.log"
    assert "fake scan process started" in log_text  # proves the file was actually written

    # 4. Captured log records at DEBUG level — sentinel absent from every
    #    record's message AND args.
    for record in caplog.records:
        assert sentinel not in record.getMessage(), (
            f"sentinel leaked into a log record: {record.name} {record.getMessage()!r}"
        )
        if record.args:
            assert sentinel not in str(record.args), (
                f"sentinel leaked into a log record's args: {record.name} {record.args!r}"
            )
