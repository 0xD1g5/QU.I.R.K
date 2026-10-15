"""Phase 143 / TAIL-02 — POST /api/jobs trusted-targets enforcement.

Mirrors tests/test_scan_submit_request_no_internal.py's server-side-config-load
pattern: force ``quirk.config.load_config`` to a fake cfg exposing
``security.trusted_targets`` and assert the dashboard entry point rejects
out-of-allowlist targets with 422 (no DB row / subprocess) BEFORE the
CIDR-size-cap block, and proceeds (201) when the allowlist is empty or the
target matches.
"""
from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from quirk.dashboard.api.app import create_app
from quirk.dashboard.api.deps import get_db
from quirk.models import Base, ScanJob
from tests.conftest import make_isolated_memory_engine


class _FakeProc:
    def __init__(self, pid=99999):
        self.pid = pid


def _fake_popen(*args, **kwargs):
    return _FakeProc()


def _app_with_db():
    # RVW-017: a per-test database. This used to be the process-wide
    # anonymous shared-cache DB, which every other test file also joined.
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


def _server_config(monkeypatch, tmp_path, trusted_targets, extra=""):
    """Point the server config at a tmp YAML (225.1: jobs read it through
    load_server_security, not a monkeypatched load_config)."""
    import yaml

    path = tmp_path / "server.yaml"
    path.write_text(
        yaml.safe_dump({"security": {"trusted_targets": list(trusted_targets)}}) + extra
    )
    monkeypatch.setenv("QUIRK_CONFIG_PATH", str(path))
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)
    return path


def _patch_probe_all_available(monkeypatch):
    """Pin the connector-availability probe to all-available (999.108).

    Phase 193's submit-time 422 gate rejects a job whose resolved config
    enables a connector unavailable in the running environment — and the
    standard profile auto-enables email/broker, so environments without
    sslyze (e.g. CI) would 422 these submissions. This file tests trusted-target enforcement,
    not connector gating, so the probe is pinned for determinism.
    """
    from quirk.dashboard.api.connector_availability import (
        ConnectorAvailability,
        probe_all_connectors,
    )

    fake = {
        flag: ConnectorAvailability(
            flag=flag,
            available=True,
            reason="",
            install_hint=entry.install_hint,
            category=entry.category,
            label=entry.label,
        )
        for flag, entry in probe_all_connectors().items()
    }
    monkeypatch.setattr(
        "quirk.dashboard.api.connector_availability.probe_all_connectors",
        lambda: fake,
    )


def test_post_jobs_rejects_target_outside_trusted_targets(monkeypatch, tmp_path):
    monkeypatch.setattr("quirk.dashboard.api.routes.jobs.subprocess.Popen", _fake_popen)
    _server_config(monkeypatch, tmp_path, ["10.0.0.0/24"])

    _, tc, TestingSession = _app_with_db()
    response = tc.post(
        "/api/jobs",
        json={"targets": "example.com"},
        headers={"X-Quirk-Request": "1"},
    )
    assert response.status_code == 422, response.text
    assert "trusted-targets" in response.text or "trusted_targets" in response.text

    db = TestingSession()
    assert db.query(ScanJob).count() == 0
    db.close()


def test_post_jobs_allows_when_trusted_targets_empty(monkeypatch, tmp_path):
    _patch_probe_all_available(monkeypatch)
    monkeypatch.setattr("quirk.dashboard.api.routes.jobs.subprocess.Popen", _fake_popen)
    _server_config(monkeypatch, tmp_path, [])

    _, tc, TestingSession = _app_with_db()
    response = tc.post(
        "/api/jobs",
        json={"targets": "example.com"},
        headers={"X-Quirk-Request": "1"},
    )
    assert response.status_code == 201, response.text
    job_id = response.json()["job_id"]

    db = TestingSession()
    assert db.get(ScanJob, job_id) is not None
    db.close()


def test_post_jobs_allows_when_target_matches_trusted_targets(monkeypatch, tmp_path):
    _patch_probe_all_available(monkeypatch)
    monkeypatch.setattr("quirk.dashboard.api.routes.jobs.subprocess.Popen", _fake_popen)
    _server_config(monkeypatch, tmp_path, ["example.com"])

    _, tc, TestingSession = _app_with_db()
    response = tc.post(
        "/api/jobs",
        json={"targets": "example.com"},
        headers={"X-Quirk-Request": "1"},
    )
    assert response.status_code == 201, response.text
    job_id = response.json()["job_id"]

    db = TestingSession()
    assert db.get(ScanJob, job_id) is not None
    db.close()


def test_build_job_config_dict_carries_trusted_targets(tmp_path):
    from quirk.dashboard.api.routes.jobs import build_job_config_dict

    d = build_job_config_dict(tmp_path, "a.example", "x.db", "balanced", trusted_targets=["a.example"])
    assert d["security"]["trusted_targets"] == ["a.example"]
    for empty in (None, []):
        d = build_job_config_dict(tmp_path, "a.example", "x.db", "balanced", trusted_targets=empty)
        assert "trusted_targets" not in d["security"]


def test_post_jobs_rejects_untrusted_overlay_host(monkeypatch, tmp_path):
    _patch_probe_all_available(monkeypatch)
    monkeypatch.setattr("quirk.dashboard.api.routes.jobs.subprocess.Popen", _fake_popen)
    _server_config(monkeypatch, tmp_path, ["127.0.0.1"])
    _, tc, TestingSession = _app_with_db()
    response = tc.post(
        "/api/jobs",
        json={"targets": "127.0.0.1", "connectors": {"broker_targets": ["10.9.9.9:5672"]}},
        headers={"X-Quirk-Request": "1"},
    )
    assert response.status_code == 422, response.text
    assert "broker_targets" in response.text
    db = TestingSession()
    assert db.query(ScanJob).count() == 0
    db.close()


def test_post_jobs_trusted_overlay_host_writes_trusted_targets_to_yaml(monkeypatch, tmp_path):
    import yaml

    _patch_probe_all_available(monkeypatch)
    monkeypatch.setattr("quirk.dashboard.api.routes.jobs.subprocess.Popen", _fake_popen)
    _server_config(monkeypatch, tmp_path, ["127.0.0.1"])
    captured = {}

    def spy_popen(cmd, *args, **kwargs):
        with open(cmd[cmd.index("--config") + 1]) as fh:
            captured["cfg"] = yaml.safe_load(fh)
        return _FakeProc()

    monkeypatch.setattr("quirk.dashboard.api.routes.jobs.subprocess.Popen", spy_popen)
    _, tc, _S = _app_with_db()
    response = tc.post(
        "/api/jobs",
        json={"targets": "127.0.0.1", "connectors": {"broker_targets": ["127.0.0.1:5672"]}},
        headers={"X-Quirk-Request": "1"},
    )
    assert response.status_code == 201, response.text
    assert captured["cfg"]["security"]["trusted_targets"] == ["127.0.0.1"]


def test_post_jobs_unreadable_server_config_is_503(monkeypatch, tmp_path):
    _patch_probe_all_available(monkeypatch)
    monkeypatch.setattr("quirk.dashboard.api.routes.jobs.subprocess.Popen", _fake_popen)
    bad = tmp_path / "bad.yaml"
    bad.write_text("security: [unclosed\n  - : :\n")
    monkeypatch.setenv("QUIRK_CONFIG_PATH", str(bad))
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)
    _, tc, TestingSession = _app_with_db()
    response = tc.post(
        "/api/jobs", json={"targets": "example.com"}, headers={"X-Quirk-Request": "1"}
    )
    assert response.status_code == 503, response.text
    assert "DASHBOARD-014" in response.text
