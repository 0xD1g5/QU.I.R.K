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

Phase 197 / Plan 03 / PARITY-07: `quirk/dashboard/api/schemas.py` widened the
connectors delta-overlay with 37 residual detail fields (target lists,
endpoint/identifier strings, two timeouts, one boolean). RESEARCH verified
live that none of the 37 introduces a NEW secret — zero of them appear in
`CREDENTIAL_REGISTRY` (see `tests/test_connector_detail_identifier_boundary.py`
Test 1's disjointness proof). PARITY-07's job here is therefore a
**regression proof**, not new guard logic: `test_sentinel_regression_under_widened_overlay`
below re-runs this file's existing sentinel scenario with a populated
37-field detail overlay ALSO present in the same submission, and asserts the
registry-derived sentinel is still absent from the `ScanJob` row, the job
`config.yaml`, `run.log`, and every captured `LogRecord` — while the detail
values themselves ARE present in `config.yaml`. That second half is
DELIBERATE and CORRECT (D-04: the 37 fields are identifiers/config, not
secrets) — a test asserting detail values are absent from config.yaml would
be asserting the feature is broken, not proving a leak guard.
"""
from __future__ import annotations

import logging
import uuid

import yaml
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from quirk.config_redaction import CREDENTIAL_REGISTRY
from quirk.dashboard.api.app import create_app
from quirk.dashboard.api.connector_availability import ConnectorAvailability, probe_all_connectors
from quirk.dashboard.api.deps import get_db
from quirk.dashboard.api.schemas import _CONNECTOR_DETAIL_KEY_TYPES
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

    # 2b. Phase 193 review CR-02: the written YAML must survive a REAL
    #     `load_config` round-trip — text presence alone is not delivery.
    #     `broker_credentials` is a top-level AppConfig key (a fragment
    #     written under `connectors:` is silently discarded by the loader's
    #     unknown-connector-key filter), and `snmp_v3_credentials` is a
    #     genuine ConnectorsCfg field. Assert both parse back to the
    #     injected env-var NAMES.
    from quirk.config import load_config

    loaded_cfg = load_config(str(config_path))
    assert (
        loaded_cfg.broker_credentials["sentinel-host.example.com"].pass_env
        == "QUIRK_JOB_BROKER_SENTINEL_HOST_EXAMPLE_COM"
    ), loaded_cfg.broker_credentials
    assert (
        loaded_cfg.connectors.snmp_v3_credentials["sentinel-host.example.com"].auth_key_env
        == "QUIRK_JOB_SNMPV3_SENTINEL_HOST_EXAMPLE_COM_AUTH"
    ), loaded_cfg.connectors.snmp_v3_credentials

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


def _all_detail_fields_overlay() -> dict:
    """Build a fully-populated 37-field connectors detail overlay, one
    representative value per declared wire type, derived from
    `_CONNECTOR_DETAIL_KEY_TYPES` at run time — never a hand-typed 37-entry
    literal, so a future field addition is automatically exercised here."""
    overlay: dict = {}
    for key, expected_type in _CONNECTOR_DETAIL_KEY_TYPES.items():
        if key in ("gke_clusters", "aks_clusters"):
            overlay[key] = (
                [{"name": "cluster-a", "location": "us-central1"}]
                if key == "gke_clusters"
                else [{"name": "cluster-a", "resource_group": "rg-a"}]
            )
        elif expected_type is list:
            overlay[key] = [f"{key}-value-a.example.com"]
        elif expected_type is str:
            overlay[key] = f"{key}-value"
        elif expected_type is int:
            overlay[key] = 30
        elif expected_type is bool:
            overlay[key] = True
        else:  # pragma: no cover - defensive, every branch above is exhaustive today
            raise AssertionError(f"unhandled detail field type for {key!r}: {expected_type}")
    return overlay


def _all_available_probe_map() -> dict:
    real = probe_all_connectors()
    forced = {}
    for flag, entry in real.items():
        forced[flag] = ConnectorAvailability(
            flag=flag,
            available=True,
            reason="",
            install_hint=entry.install_hint,
            category=entry.category,
            label=entry.label,
        )
    return forced


def test_sentinel_regression_under_widened_overlay(monkeypatch, caplog):
    """Phase 197 / PARITY-07 Test 3: repeat
    `test_sentinel_absent_from_row_config_log_and_logrecords`'s scenario with
    a fully-populated 37-field connectors detail overlay ALSO present in the
    same submission. Both halves are asserted here, deliberately, so the
    identifier-vs-secret distinction cannot be misread later:

      - The registry-derived sentinel secret values remain absent from the
        `ScanJob` row, the job `config.yaml`, `run.log`, and every captured
        `LogRecord` — widening the overlay schema did not reopen a leak path.
      - The 37 detail overlay values themselves ARE present in `config.yaml`
        — that is D-04-correct behavior (they are config, not secrets), not
        a leak, and this test would be asserting the feature is broken if it
        required their absence instead.
    """
    sentinel = f"QUIRK-CRED-SENTINEL-{uuid.uuid4().hex}"
    fake_popen = _RecordingLoggingPopen()
    monkeypatch.setattr("quirk.dashboard.api.routes.jobs.subprocess.Popen", fake_popen)
    fake_probe_map = _all_available_probe_map()
    monkeypatch.setattr(
        "quirk.dashboard.api.connector_availability.probe_all_connectors",
        lambda: fake_probe_map,
    )

    _app, tc, TestingSession = _app_with_db()

    detail_overlay = _all_detail_fields_overlay()

    with caplog.at_level(logging.DEBUG):
        response = tc.post(
            "/api/jobs",
            json={
                "targets": "example.com",
                "profile": "quick",
                "connectors": detail_overlay,
                "credentials": _credential_payload_for_sentinel(sentinel),
            },
            headers={"X-Quirk-Request": "1"},
        )
    assert response.status_code == 201, response.text
    job_id = response.json()["job_id"]

    # Positive control, re-asserted against THIS request's recorded env.
    assert sentinel in fake_popen.last_env.values()

    # 1. ScanJob row — sentinel absent from every column.
    db = TestingSession()
    row = db.get(ScanJob, job_id)
    assert row is not None
    row_values = {c.name: getattr(row, c.name) for c in ScanJob.__table__.columns}
    db.close()
    assert sentinel not in str(row_values), f"sentinel leaked into ScanJob row: {row_values}"

    import quirk.dashboard.api.routes.jobs as jobs_module

    config_path = jobs_module._job_output_dir(job_id) / "config.yaml"
    config_text = config_path.read_text()

    # 2. Sentinel absent from config.yaml.
    assert sentinel not in config_text, "sentinel leaked into config.yaml under a widened overlay"

    # 2b. Detail overlay values ARE present in config.yaml — correct, D-04.
    #     Parsed (not substring-matched) so list/dict values are compared
    #     structurally rather than relying on YAML's serialization shape.
    parsed_connectors = yaml.safe_load(config_text).get("connectors", {})
    for key, value in detail_overlay.items():
        assert parsed_connectors.get(key) == value, (
            f"detail field {key!r} missing/altered in config.yaml connectors block "
            f"(D-04 requires it be present in cleartext)"
        )

    # 3. run.log — sentinel absent.
    log_path = jobs_module._job_output_dir(job_id) / "run.log"
    log_text = log_path.read_text()
    assert sentinel not in log_text, "sentinel leaked into run.log"
    assert "fake scan process started" in log_text

    # 4. Captured log records at DEBUG level — sentinel absent.
    for record in caplog.records:
        assert sentinel not in record.getMessage(), (
            f"sentinel leaked into a log record: {record.name} {record.getMessage()!r}"
        )
        if record.args:
            assert sentinel not in str(record.args), (
                f"sentinel leaked into a log record's args: {record.name} {record.args!r}"
            )
