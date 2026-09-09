"""Phase 193 / Plan 06 / Task 2 — credential env-var injection at the Popen
spawn site (D-09/D-10/D-11/D-12/D-15).

Credentials submitted in `ScanSubmitRequest.credentials` must reach the scan
subprocess ONLY via a merged `Popen(env=...)` dict — never a bare dict of
only the injected vars (would drop PATH/PYTHONPATH/QUIRK_CONFIG_PATH and
break every scan), never an `os.environ[...] =` mutation of the server
process (a race under FastAPI's threadpool). Env-var NAMES are derived from
`quirk.config_redaction.CREDENTIAL_REGISTRY` at call time, never a literal
name table in `jobs.py`.
"""
from __future__ import annotations

import dataclasses

from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from quirk.config_redaction import CREDENTIAL_REGISTRY, CredentialField
from quirk.dashboard.api.app import create_app
from quirk.dashboard.api.connector_availability import ConnectorAvailability, probe_all_connectors
from quirk.dashboard.api.deps import get_db
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


class _RecordingPopen:
    """Captures the `env=` kwarg of the last Popen() call, never spawns anything real."""

    last_call: dict = {}

    def __call__(self, *args, **kwargs):
        _RecordingPopen.last_call = {"args": args, "kwargs": kwargs}
        return _FakeProc()


def _patch_probe_available(monkeypatch, *flags):
    """Force specific enable_* flags' availability True, real probe otherwise
    (mirrors tests/test_jobs_connector_422_gate.py's honest-override style).
    """
    real = probe_all_connectors()
    for flag in flags:
        entry = real[flag]
        real[flag] = ConnectorAvailability(
            flag=flag, available=True, reason="", install_hint="",
            category=entry.category, label=entry.label,
        )
    monkeypatch.setattr(
        "quirk.dashboard.api.connector_availability.probe_all_connectors",
        lambda: real,
    )


# ---------------------------------------------------------------------------
# 1 & 4. env= kwarg present and is a superset of os.environ (Pitfall 1),
#        including the no-credentials regression case.
# ---------------------------------------------------------------------------

def test_env_kwarg_is_superset_of_parent_environment(monkeypatch):
    import os

    recording = _RecordingPopen()
    monkeypatch.setattr("quirk.dashboard.api.routes.jobs.subprocess.Popen", recording)

    _app, tc, _Session = _app_with_db()
    response = tc.post(
        "/api/jobs",
        json={"targets": "example.com", "profile": "quick"},
        headers={"X-Quirk-Request": "1"},
    )
    assert response.status_code == 201, response.text

    env_used = _RecordingPopen.last_call["kwargs"]["env"]
    for key, value in os.environ.items():
        assert env_used.get(key) == value


def test_no_credentials_submission_still_gets_env_kwarg_and_succeeds(monkeypatch):
    import os

    recording = _RecordingPopen()
    monkeypatch.setattr("quirk.dashboard.api.routes.jobs.subprocess.Popen", recording)

    _app, tc, _Session = _app_with_db()
    response = tc.post(
        "/api/jobs",
        json={"targets": "example.com", "profile": "quick"},
        headers={"X-Quirk-Request": "1"},
    )
    assert response.status_code == 201, response.text
    env_used = _RecordingPopen.last_call["kwargs"]["env"]
    assert env_used == dict(os.environ)


# ---------------------------------------------------------------------------
# 2. Injected credential names are present in env= with submitted values
# ---------------------------------------------------------------------------

def test_injected_credential_present_in_env(monkeypatch):
    recording = _RecordingPopen()
    monkeypatch.setattr("quirk.dashboard.api.routes.jobs.subprocess.Popen", recording)
    _patch_probe_available(monkeypatch, "enable_adcs")

    _app, tc, _Session = _app_with_db()
    response = tc.post(
        "/api/jobs",
        json={
            "targets": "example.com",
            "profile": "quick",
            "connectors": {"enable_adcs": True},
            "credentials": {"adcs_password": "s3cr3t-sentinel-value"},
        },
        headers={"X-Quirk-Request": "1"},
    )
    assert response.status_code == 201, response.text
    env_used = _RecordingPopen.last_call["kwargs"]["env"]
    assert env_used["QUIRK_ADCS_PASSWORD"] == "s3cr3t-sentinel-value"


# ---------------------------------------------------------------------------
# 3. os.environ itself is byte-identical before and after create_job (Pitfall 2)
# ---------------------------------------------------------------------------

def test_os_environ_unchanged_across_create_job(monkeypatch):
    import os

    recording = _RecordingPopen()
    monkeypatch.setattr("quirk.dashboard.api.routes.jobs.subprocess.Popen", recording)
    _patch_probe_available(monkeypatch, "enable_adcs")

    before = dict(os.environ)
    _app, tc, _Session = _app_with_db()
    response = tc.post(
        "/api/jobs",
        json={
            "targets": "example.com",
            "profile": "quick",
            "connectors": {"enable_adcs": True},
            "credentials": {"adcs_password": "s3cr3t-sentinel-value"},
        },
        headers={"X-Quirk-Request": "1"},
    )
    assert response.status_code == 201, response.text
    after = dict(os.environ)
    assert before == after
    assert "QUIRK_ADCS_PASSWORD" not in os.environ


# ---------------------------------------------------------------------------
# 5. Env-var name derivation from CREDENTIAL_REGISTRY, never a literal in jobs.py
# ---------------------------------------------------------------------------

def test_env_var_name_derived_from_registry(monkeypatch):
    recording = _RecordingPopen()
    monkeypatch.setattr("quirk.dashboard.api.routes.jobs.subprocess.Popen", recording)
    _patch_probe_available(monkeypatch, "enable_adcs")

    patched_registry = tuple(
        CredentialField(entry.section, "adcs_password", "QUIRK_TEST_RENAMED_ADCS")
        if entry.name == "adcs_password"
        else entry
        for entry in CREDENTIAL_REGISTRY
    )
    monkeypatch.setattr("quirk.config_redaction.CREDENTIAL_REGISTRY", patched_registry)

    _app, tc, _Session = _app_with_db()
    response = tc.post(
        "/api/jobs",
        json={
            "targets": "example.com",
            "profile": "quick",
            "connectors": {"enable_adcs": True},
            "credentials": {"adcs_password": "s3cr3t-sentinel-value"},
        },
        headers={"X-Quirk-Request": "1"},
    )
    assert response.status_code == 201, response.text
    env_used = _RecordingPopen.last_call["kwargs"]["env"]
    assert env_used.get("QUIRK_TEST_RENAMED_ADCS") == "s3cr3t-sentinel-value"
    assert "QUIRK_ADCS_PASSWORD" not in env_used or env_used.get("QUIRK_ADCS_PASSWORD") != "s3cr3t-sentinel-value"


# ---------------------------------------------------------------------------
# 6. Host collision: two broker: credentials whose hosts sanitize identically -> 422
# ---------------------------------------------------------------------------

def test_broker_host_collision_rejected_422(monkeypatch):
    recording = _RecordingPopen()
    monkeypatch.setattr("quirk.dashboard.api.routes.jobs.subprocess.Popen", recording)
    _patch_probe_available(monkeypatch, "enable_broker")

    _app, tc, _Session = _app_with_db()
    response = tc.post(
        "/api/jobs",
        json={
            "targets": "example.com",
            "profile": "quick",
            "connectors": {"enable_broker": True},
            "credentials": {
                "broker:host-1": "pw-a",
                "broker:host_1": "pw-b",
            },
        },
        headers={"X-Quirk-Request": "1"},
    )
    assert response.status_code == 422, response.text
    assert "collision" in response.text.lower()


# ---------------------------------------------------------------------------
# 7. D-15: enabling a connector with blank credentials succeeds with a warning
# ---------------------------------------------------------------------------

def test_blank_credential_warns_not_blocks(monkeypatch):
    recording = _RecordingPopen()
    monkeypatch.setattr("quirk.dashboard.api.routes.jobs.subprocess.Popen", recording)
    _patch_probe_available(monkeypatch, "enable_adcs")

    _app, tc, _Session = _app_with_db()
    response = tc.post(
        "/api/jobs",
        json={
            "targets": "example.com",
            "profile": "quick",
            "connectors": {"enable_adcs": True},
        },
        headers={"X-Quirk-Request": "1"},
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert "credential_warnings" in data
    connectors_warned = {w["connector"] for w in data["credential_warnings"]}
    assert "enable_adcs" in connectors_warned
