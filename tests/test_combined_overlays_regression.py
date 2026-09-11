"""Phase 199 / Plan 03 / TRIAGE-11 — combined connectors + advanced-scan-fields
overlay regression coverage.

v5.22 milestone-audit tech-debt item: both overlays are covered individually
today (`tests/test_build_job_config_connectors_overlay.py`,
`tests/test_advanced_scan_fields_overlay.py`) but nothing proved they coexist
on ONE scan submission — a regression where one overlay clobbers the other's
config block would ship green. This file closes that gap: one `POST
/api/jobs` submission carrying both overlays, read back from the on-disk job
`config.yaml`; one `GET /api/config/effective` call carrying both query
params, asserted on a single response body; and a direct
`build_job_config_dict` call proving neither overlay's keys are lost when
both are applied together.

pytest -q tests/test_combined_overlays_regression.py
"""
from __future__ import annotations

import json

import yaml
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from quirk.dashboard.api.app import create_app
from quirk.dashboard.api.connector_availability import ConnectorAvailability, probe_all_connectors
from quirk.dashboard.api.deps import get_db
from quirk.dashboard.api.routes.jobs import build_job_config_dict
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
    return app, TestClient(app, raise_server_exceptions=False)


class _FakeProc:
    def __init__(self):
        self.pid = 99999
        self.returncode = None

    def poll(self):
        return self.returncode


def _fake_popen(*args, **kwargs):
    return _FakeProc()


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


def test_combined_overlays_land_in_job_yaml(monkeypatch):
    """One POST /api/jobs submission carrying BOTH a connectors overlay and an
    advanced-scan-fields overlay must write a job config.yaml reflecting both
    simultaneously (ROADMAP criterion 3)."""
    monkeypatch.setattr("quirk.dashboard.api.routes.jobs.subprocess.Popen", _fake_popen)
    fake_map = _all_available_probe_map()
    monkeypatch.setattr(
        "quirk.dashboard.api.connector_availability.probe_all_connectors",
        lambda: fake_map,
    )

    _app, tc = _app_with_db()
    response = tc.post(
        "/api/jobs",
        json={
            "targets": "example.com",
            "profile": "quick",
            "connectors": {"enable_jwt": True, "jwt_targets": ["api.example.com"]},
            "advanced": {"tls_enum_mode": "deep", "motion_concurrency": 25},
        },
        headers={"X-Quirk-Request": "1"},
    )
    assert response.status_code == 201, response.text
    job_id = response.json()["job_id"]

    import quirk.dashboard.api.routes.jobs as jobs_module

    on_disk = yaml.safe_load((jobs_module._job_output_dir(job_id) / "config.yaml").read_text())
    # BOTH overlays asserted on the SAME on-disk document — simultaneity is
    # the whole point of this test.
    assert on_disk["connectors"]["enable_jwt"] is True
    assert on_disk["connectors"]["jwt_targets"] == ["api.example.com"]
    assert on_disk["scan"]["tls_enum_mode"] == "deep"
    assert on_disk["scan"]["motion_concurrency"] == 25


def test_combined_overlays_reflected_in_effective_config():
    """One GET /api/config/effective call carrying both query params must
    reflect both overlays, each badged with user provenance, in a single
    response body — neither overlay clobbers the other's section."""
    _app, tc = _app_with_db()
    response = tc.get(
        "/api/config/effective",
        params={
            "connectors": json.dumps({"enable_jwt": True}),
            "advanced": json.dumps({"tls_enum_mode": "deep"}),
        },
        headers={"X-Quirk-Request": "1"},
    )
    assert response.status_code == 200, response.text
    data = response.json()

    connectors_section = next(s for s in data["sections"] if s["name"] == "connectors")
    connectors_field = next(f for f in connectors_section["fields"] if f["name"] == "enable_jwt")
    assert connectors_field["provenance"] == "user"
    assert connectors_field["value"] is True

    scan_section = next(s for s in data["sections"] if s["name"] == "scan")
    scan_field = next(f for f in scan_section["fields"] if f["name"] == "tls_enum_mode")
    assert scan_field["provenance"] == "user"
    assert scan_field["value"] == "deep"


def test_neither_overlay_clobbers_the_other_in_build_job_config_dict(tmp_path):
    """A direct build_job_config_dict call with both a connectors_overlay and
    a scan_overlay in one call leaves each overlay's keys intact — the
    delta-only discipline the single-overlay tests already assert, now under
    simultaneous application."""
    output_dir = tmp_path / "out"
    config = build_job_config_dict(
        output_dir, "example.com", "db.sqlite", "balanced",
        port_scope="top1000",
        connectors_overlay={"enable_jwt": True, "jwt_targets": ["api.example.com"]},
        scan_overlay={"tls_enum_mode": "deep", "motion_concurrency": 25},
    )
    assert config["connectors"] == {
        "enable_jwt": True,
        "jwt_targets": ["api.example.com"],
    }
    assert config["scan"]["tls_enum_mode"] == "deep"
    assert config["scan"]["motion_concurrency"] == 25
