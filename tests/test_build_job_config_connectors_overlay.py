"""Phase 193 / PARITY-02 — `build_job_config_dict`'s `connectors_overlay` kwarg.

D-13 (delta-only writes) and D-14 (explicit-toggle-wins precedence over the
Phase 121 custom-port-scope enable_email/enable_broker suppression). See
`quirk/dashboard/api/routes/jobs.py::build_job_config_dict` and
`.planning/phases/193-connector-credential-parity/193-05-PLAN.md`.

pytest -q tests/test_build_job_config_connectors_overlay.py
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from quirk.config import load_config
from quirk.dashboard.api.routes.jobs import build_job_config_dict
from quirk.engine.profiles import apply_profile


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
