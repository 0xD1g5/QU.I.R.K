"""Phase 194 / Plan 02 / Tasks 2-3 — build_job_config_dict's scan_overlay /
assessment_overlay kwargs, and the effective-config preview's forwarding of
them (PARITY-04 / D-01 / D-02).

See `quirk/dashboard/api/routes/jobs.py::build_job_config_dict`,
`quirk/dashboard/api/config_preview.py::resolve_effective_config`, and
`quirk/dashboard/api/routes/config.py::get_effective_config`.

pytest -q tests/test_advanced_scan_fields_overlay.py
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from quirk.config import load_config
from quirk.dashboard.api.app import create_app
from quirk.dashboard.api.config_preview import resolve_effective_config
from quirk.dashboard.api.deps import get_db
from quirk.dashboard.api.routes.jobs import build_job_config_dict
from quirk.engine.profiles import apply_profile
from tests.conftest import make_isolated_memory_engine


# ---------------------------------------------------------------------------
# build_job_config_dict — scan_overlay / assessment_overlay
# ---------------------------------------------------------------------------


def test_no_overlay_is_byte_identical_regression(tmp_path):
    """An untouched form (no scan_overlay/assessment_overlay) must produce a
    config dict identical to what build_job_config_dict already produced
    before this phase."""
    output_dir = tmp_path / "out"
    without_kwargs = build_job_config_dict(
        output_dir, "example.com", "db.sqlite", "balanced", port_scope="top1000",
    )
    with_none_overlays = build_job_config_dict(
        output_dir, "example.com", "db.sqlite", "balanced", port_scope="top1000",
        scan_overlay=None, assessment_overlay=None,
    )
    assert without_kwargs == with_none_overlays


def test_scan_overlay_writes_only_touched_key(tmp_path):
    output_dir = tmp_path / "out"
    config = build_job_config_dict(
        output_dir, "example.com", "db.sqlite", "balanced", port_scope="top1000",
        scan_overlay={"tls_enum_mode": "deep"},
    )
    assert config["scan"]["tls_enum_mode"] == "deep"
    # port_scope-derived defaults untouched
    assert config["scan"]["include_sni"] is True
    from quirk.interactive import CONSULTING_TLS_PORTS
    assert config["scan"]["ports_tls"] == list(CONSULTING_TLS_PORTS)


def test_explicit_ports_tls_beats_common_scope_default(tmp_path):
    output_dir = tmp_path / "out"
    config = build_job_config_dict(
        output_dir, "example.com", "db.sqlite", "balanced", port_scope="common",
        scan_overlay={"ports_tls": [8443, 9443]},
    )
    assert config["scan"]["ports_tls"] == [8443, 9443]


def test_partial_timeouts_overlay_writes_only_named_subkeys(tmp_path):
    output_dir = tmp_path / "out"
    config = build_job_config_dict(
        output_dir, "example.com", "db.sqlite", "balanced", port_scope="top1000",
        scan_overlay={"timeouts": {"tls_seconds": 20}},
    )
    assert config["scan"]["timeouts"] == {"tls_seconds": 20}


def test_assessment_overlay_overrides_hardcoded_confidential(tmp_path):
    output_dir = tmp_path / "out"
    config = build_job_config_dict(
        output_dir, "example.com", "db.sqlite", "balanced", port_scope="top1000",
        assessment_overlay={"data_classification": "regulated"},
    )
    assert config["assessment"]["data_classification"] == "regulated"


def test_unrecognized_scan_overlay_key_raises_value_error(tmp_path):
    output_dir = tmp_path / "out"
    with pytest.raises(ValueError, match="not a recognized advanced scan field"):
        build_job_config_dict(
            output_dir, "example.com", "db.sqlite", "balanced", port_scope="top1000",
            scan_overlay={"bogus_field": 1},
        )


def test_unrecognized_assessment_overlay_key_raises_value_error(tmp_path):
    output_dir = tmp_path / "out"
    with pytest.raises(ValueError, match="not a recognized advanced scan field"):
        build_job_config_dict(
            output_dir, "example.com", "db.sqlite", "balanced", port_scope="top1000",
            assessment_overlay={"bogus_field": 1},
        )


def test_overlay_survives_apply_profile(tmp_path):
    """Round-trip through yaml.dump + load_config: overlaid keys are read
    back as real (non-None) values, so apply_profile's "only set if None"
    precedence rule (Phase 72 D-02/WR-11's ScanCfg-side equivalent — there is
    no separate `_user_set_fields` tracking on ScanCfg, unlike ConnectorsCfg)
    naturally leaves them alone. A "standard" profile run would otherwise set
    tls_enum_mode to "fast" when it is None."""
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    config = build_job_config_dict(
        output_dir, "example.com", str(tmp_path / "db.sqlite"), "balanced",
        port_scope="top1000",
        scan_overlay={"tls_enum_mode": "deep", "retry": {"retry_count": 3}},
    )
    config_path = tmp_path / "config.yaml"
    with open(config_path, "w", encoding="utf-8") as fh:
        yaml.dump(config, fh, default_flow_style=False)

    cfg = load_config(str(config_path))
    assert cfg.scan.tls_enum_mode == "deep"
    assert cfg.scan.retry.retry_count == 3

    apply_profile(cfg, "standard")
    assert cfg.scan.tls_enum_mode == "deep"
    assert cfg.scan.retry.retry_count == 3


# ---------------------------------------------------------------------------
# resolve_effective_config — forwarding
# ---------------------------------------------------------------------------


def test_resolve_effective_config_forwards_scan_overlay():
    cfg, overlay_dict, _preset = resolve_effective_config(
        targets="example.com",
        profile="standard",
        calibration="balanced",
        port_scope="top1000",
        scan_overlay={"tls_enum_mode": "deep"},
    )
    assert cfg.scan.tls_enum_mode == "deep"
    assert overlay_dict["scan"]["tls_enum_mode"] == "deep"


# ---------------------------------------------------------------------------
# GET /api/config/effective — advanced query param
# ---------------------------------------------------------------------------


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


def test_advanced_query_param_badges_user_provenance():
    _app, tc, _Session = _app_with_db()
    response = tc.get(
        '/api/config/effective?advanced={"tls_enum_mode":"deep"}',
        headers={"X-Quirk-Request": "1"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    scan_section = next(s for s in data["sections"] if s["name"] == "scan")
    field = next(f for f in scan_section["fields"] if f["name"] == "tls_enum_mode")
    assert field["provenance"] == "user"
    assert field["value"] == "deep"


def test_advanced_query_param_tls_enum_mode_off_rejected():
    _app, tc, _Session = _app_with_db()
    response = tc.get(
        '/api/config/effective?advanced={"tls_enum_mode":"off"}',
        headers={"X-Quirk-Request": "1"},
    )
    assert response.status_code == 422


def test_advanced_query_param_unknown_key_rejected():
    _app, tc, _Session = _app_with_db()
    response = tc.get(
        '/api/config/effective?advanced={"ports_ssh":[22]}',
        headers={"X-Quirk-Request": "1"},
    )
    assert response.status_code == 422


def test_advanced_query_param_malformed_json_rejected():
    _app, tc, _Session = _app_with_db()
    response = tc.get(
        "/api/config/effective?advanced=not-json",
        headers={"X-Quirk-Request": "1"},
    )
    assert response.status_code == 422


def test_advanced_query_param_omitted_matches_pre_phase_behavior():
    """Query-additive-only guard (Phase 193 D-16 precedent): omitting
    `advanced` entirely must not change the response shape."""
    _app, tc, _Session = _app_with_db()
    response = tc.get(
        "/api/config/effective?targets=example.com",
        headers={"X-Quirk-Request": "1"},
    )
    assert response.status_code == 200, response.text
