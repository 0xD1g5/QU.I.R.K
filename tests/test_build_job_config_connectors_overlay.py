"""Phase 193 / PARITY-02 — `build_job_config_dict`'s `connectors_overlay` kwarg.

D-13 (delta-only writes) and D-14 (explicit-toggle-wins precedence over the
Phase 121 custom-port-scope enable_email/enable_broker suppression). See
`quirk/dashboard/api/routes/jobs.py::build_job_config_dict` and
`.planning/phases/193-connector-credential-parity/193-05-PLAN.md`.

Phase 197 / Plan 03 / D-14 success criterion 4: `test_enable_toggle_no_longer_noop_at_job_yaml_level`
proves — at the job's ON-DISK `config.yaml`, read through a real
`POST /api/jobs` submission, not through `build_job_config_dict`'s return
value directly — that toggling `enable_jwt`/`enable_container`/
`enable_source`/`enable_kerberos` on TOGETHER WITH their target list is no
longer a no-op (the audit finding these connectors "short-circuit on an
empty target list" — see `run_scan.py`'s `if not cfg.connectors.X_targets:
return _recorder.skip(...)` guards for jwt/container/source/kerberos).
`test_enable_toggle_without_targets_is_still_a_documented_noop` is the
contrast case: enabling the connector WITHOUT its target list still writes
no `*_targets` key — this is the pre-phase no-op state the phase fixes when
an operator supplies both.

pytest -q tests/test_build_job_config_connectors_overlay.py
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from quirk.config import load_config
from quirk.dashboard.api.app import create_app
from quirk.dashboard.api.connector_availability import ConnectorAvailability, probe_all_connectors
from quirk.dashboard.api.deps import get_db
from quirk.dashboard.api.routes.jobs import build_job_config_dict
from quirk.engine.profiles import apply_profile
from tests.conftest import make_isolated_memory_engine


@pytest.mark.parametrize("port_scope", ["common", "top1000", "all", "custom"])
def test_connectors_overlay_none_is_byte_identical_regression(tmp_path, port_scope):
    """connectors_overlay=None must produce a config dict identical to today's
    output for every port_scope value — a regression guard for existing
    callers that never pass the new kwarg."""
    kwargs = {}
    if port_scope == "custom":
        kwargs["custom_ports"] = "443,8443"

    output_dir = tmp_path / "out"
    without_kwarg = build_job_config_dict(
        output_dir, "example.com", "db.sqlite", "balanced",
        port_scope=port_scope, **kwargs,
    )
    with_none_overlay = build_job_config_dict(
        output_dir, "example.com", "db.sqlite", "balanced",
        port_scope=port_scope, connectors_overlay=None, **kwargs,
    )
    assert without_kwarg == with_none_overlay


def test_connectors_overlay_delta_only_writes_single_key(tmp_path):
    """D-13: a single-key overlay yields a single-key connectors block, not
    the full 25-key ConnectorsCfg surface."""
    output_dir = tmp_path / "out"
    config = build_job_config_dict(
        output_dir, "example.com", "db.sqlite", "balanced",
        port_scope="top1000",
        connectors_overlay={"enable_adcs": True},
    )
    assert config["connectors"] == {"enable_adcs": True}
    assert len(config["connectors"]) == 1


def test_connectors_overlay_wins_over_custom_scope_suppression():
    """D-14: an explicit operator toggle for enable_broker overrides the
    custom-port-scope suppression, while the untouched enable_email flag
    stays False from that same suppression."""
    config = build_job_config_dict(
        Path("/tmp/quirk-test-out"), "example.com", "db.sqlite", "balanced",
        port_scope="custom", custom_ports="443",
        connectors_overlay={"enable_broker": True},
    )
    assert config["connectors"]["enable_broker"] is True
    assert config["connectors"]["enable_email"] is False


def test_connectors_overlay_unknown_key_raises_value_error():
    with pytest.raises(ValueError, match="enable_bogus"):
        build_job_config_dict(
            Path("/tmp/quirk-test-out"), "example.com", "db.sqlite", "balanced",
            port_scope="top1000",
            connectors_overlay={"enable_bogus": True},
        )


def test_connectors_overlay_non_toggle_key_raises_value_error():
    """A key that IS a real ConnectorsCfg field but is not an enable_* toggle
    (e.g. a credential field) must be rejected the same way an unknown key
    is — the overlay is toggles-only."""
    with pytest.raises(ValueError, match="adcs_password"):
        build_job_config_dict(
            Path("/tmp/quirk-test-out"), "example.com", "db.sqlite", "balanced",
            port_scope="top1000",
            connectors_overlay={"adcs_password": True},
        )


def test_connectors_overlay_user_set_field_survives_apply_profile(tmp_path):
    """D-13/D-14 end-to-end: the overlay is written into real YAML, re-parsed
    by load_config (populating _user_set_fields from the raw keys), and the
    operator's value survives apply_profile even under a profile that would
    otherwise flip it.

    The "deep"/"standard" profiles auto-enable enable_broker to True when it
    is not in _user_set_fields (quirk/engine/profiles.py). Overlaying an
    explicit False must survive that flip.
    """
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    config = build_job_config_dict(
        output_dir, "example.com", str(tmp_path / "db.sqlite"), "balanced",
        port_scope="top1000",
        connectors_overlay={"enable_broker": False},
    )
    config_path = tmp_path / "config.yaml"
    with open(config_path, "w", encoding="utf-8") as fh:
        yaml.dump(config, fh, default_flow_style=False)

    cfg = load_config(str(config_path))
    assert "enable_broker" in cfg.connectors._user_set_fields
    assert cfg.connectors.enable_broker is False

    apply_profile(cfg, "deep")

    # The operator's explicit False must survive — not just the key's
    # presence in _user_set_fields, but the actual surviving VALUE.
    assert cfg.connectors.enable_broker is False


def test_connectors_overlay_none_and_empty_dict_byte_identical(tmp_path):
    """Phase 197 / D-08: an absent (None) connectors delta and an explicitly
    empty ({}) connectors delta must produce byte-identical job config.yaml
    output -- the widened overlay must not perturb this pre-phase guarantee
    even though `validate_connectors_overlay` now does substantially more
    work than the old `enable_*`-only gate."""
    output_dir = tmp_path / "out"
    with_none = build_job_config_dict(
        output_dir, "example.com", "db.sqlite", "balanced",
        port_scope="top1000", connectors_overlay=None,
    )
    with_empty = build_job_config_dict(
        output_dir, "example.com", "db.sqlite", "balanced",
        port_scope="top1000", connectors_overlay={},
    )
    assert with_none == with_empty


def test_connectors_overlay_detail_field_reaches_job_yaml_with_toggle():
    """Phase 197 / PARITY-05 / D-14 success criterion 4: an operator toggling
    enable_jwt on AND setting jwt_targets in the SAME overlay must land BOTH
    keys in the job config's connectors block -- proving enable_jwt is no
    longer a no-op (the RESEARCH-cited audit finding: "the scan short-
    circuits on an empty target list... toggling it on alone does nothing")."""
    config = build_job_config_dict(
        Path("/tmp/quirk-test-out"), "example.com", "db.sqlite", "balanced",
        port_scope="top1000",
        connectors_overlay={"enable_jwt": True, "jwt_targets": ["a.example.com"]},
    )
    assert config["connectors"]["enable_jwt"] is True
    assert config["connectors"]["jwt_targets"] == ["a.example.com"]
    assert len(config["connectors"]) == 2


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


# (enable_flag, targets_field, sample_targets) — jwt/container/source are the
# three success-criterion-4-named connectors whose run_scan.py skip guard was
# cited by RESEARCH; kerberos is the identity-connector family member added
# per the plan's acceptance criteria (>= 4 pairs, parametrized not copy-pasted).
D14_TOGGLE_TARGET_PAIRS = [
    ("enable_jwt", "jwt_targets", ["api.example.com", "auth.example.com"]),
    ("enable_container", "container_targets", ["registry.example.com/app:latest"]),
    ("enable_source", "source_targets", ["/repo/path-a", "/repo/path-b"]),
    ("enable_kerberos", "kerberos_targets", ["kdc.example.com"]),
]


@pytest.mark.parametrize("enable_flag,targets_field,sample_targets", D14_TOGGLE_TARGET_PAIRS)
def test_enable_toggle_no_longer_noop_at_job_yaml_level(
    monkeypatch, enable_flag, targets_field, sample_targets
):
    """Phase 197 / D-14 success criterion 4: a full `POST /api/jobs`
    submission with `{enable_flag: true, targets_field: [...]}` writes a job
    `config.yaml` that, read from DISK via `yaml.safe_load`, carries both the
    toggle and the operator's target list under `connectors:` — proving the
    toggle is no longer a no-op for all four families named in the success
    criterion."""
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
            "connectors": {enable_flag: True, targets_field: sample_targets},
        },
        headers={"X-Quirk-Request": "1"},
    )
    assert response.status_code == 201, response.text
    job_id = response.json()["job_id"]

    import quirk.dashboard.api.routes.jobs as jobs_module

    config_path = jobs_module._job_output_dir(job_id) / "config.yaml"
    on_disk = yaml.safe_load(config_path.read_text())
    connectors_block = on_disk.get("connectors", {})

    assert connectors_block.get(enable_flag) is True
    assert connectors_block.get(targets_field) == sample_targets


def test_enable_toggle_without_targets_is_still_a_documented_noop(monkeypatch):
    """Phase 197 / D-14 no-op contrast: the SAME submission WITHOUT the
    target list writes a `config.yaml` `connectors:` block containing
    `enable_jwt: true` and NO `jwt_targets` key (delta-only, D-08) —
    documenting the pre-phase no-op state (run_scan.py's
    `if not cfg.connectors.jwt_targets: return _recorder.skip(...)` guard)
    that the phase fixes only when an operator ALSO supplies targets."""
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
            "connectors": {"enable_jwt": True},
        },
        headers={"X-Quirk-Request": "1"},
    )
    assert response.status_code == 201, response.text
    job_id = response.json()["job_id"]

    import quirk.dashboard.api.routes.jobs as jobs_module

    config_path = jobs_module._job_output_dir(job_id) / "config.yaml"
    on_disk = yaml.safe_load(config_path.read_text())
    connectors_block = on_disk.get("connectors", {})

    assert connectors_block.get("enable_jwt") is True
    assert "jwt_targets" not in connectors_block
