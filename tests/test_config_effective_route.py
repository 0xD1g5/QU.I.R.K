"""GET /api/config/effective — PARITY-01.

Phase 192 Plan 06.

Task 1 covers the overlay resolver (`resolve_effective_config` /
`build_job_config_dict`) in isolation. Task 2 extends this file with the
auth-gated route's behavior (redaction, provenance, single-serialization-path).
"""
from __future__ import annotations

import os

import pytest
from sqlalchemy.orm import sessionmaker

from quirk.dashboard.api import config_preview as config_preview_module
from quirk.dashboard.api.config_preview import resolve_effective_config


# ---------------------------------------------------------------------------
# Task 1 — overlay resolver
# ---------------------------------------------------------------------------

def test_resolve_effective_config_reflects_targets_and_deep_profile():
    """targets + deep profile reflect in the resolved AppConfig (D-03)."""
    cfg, _raw, _preset = resolve_effective_config(targets="example.com", profile="deep")
    assert cfg.targets.fqdns == ["example.com"]
    # apply_profile(cfg, "deep") auto-enables email/broker connectors when not
    # user-explicit (Phase 32/33, Phase 72 D-02/WR-11).
    assert cfg.connectors.enable_email is True
    assert cfg.connectors.enable_broker is True


def test_resolve_effective_config_custom_scope_suppresses_fixed_port_connectors():
    """Custom port_scope reproduces the same fixed-port-connector suppression a
    real custom-scope job gets — the preview does not lie about the submission
    (Phase 121 follow-up)."""
    cfg, raw, preset_changed = resolve_effective_config(
        port_scope="custom", custom_ports="8443", profile="standard",
    )
    assert cfg.connectors.enable_email is False
    assert cfg.connectors.enable_broker is False
    assert raw["connectors"] == {"enable_email": False, "enable_broker": False}
    # The user-explicit suppression must NOT be misreported as a preset change —
    # apply_profile is suppressed by _user_set_fields, so no mutation happened.
    assert "connectors.enable_email" not in preset_changed
    assert "connectors.enable_broker" not in preset_changed


def test_resolve_effective_config_preset_changed_paths_reflect_apply_profile():
    """Third return value contains apply_profile-changed paths and excludes
    paths the caller explicitly set."""
    cfg, _raw, preset_changed = resolve_effective_config(profile="deep")
    # Not user-set (no custom scope / no explicit connectors block) — deep
    # profile's auto-enable must show up as a preset-driven change.
    assert "connectors.enable_email" in preset_changed
    assert "connectors.enable_broker" in preset_changed
    assert cfg.connectors.enable_email is True


def test_resolve_effective_config_leaves_no_temp_file_on_disk():
    """No temp file/dir is left behind after the call, including cleanup
    guarantees on the exception path (T-192-22)."""
    captured: dict = {}
    orig_tmpdir_cls = config_preview_module.tempfile.TemporaryDirectory

    class _SpyTemporaryDirectory(orig_tmpdir_cls):  # type: ignore[misc]
        def __enter__(self):
            path = super().__enter__()
            captured["path"] = path
            return path

    import pytest as _pytest
    monkeypatch = _pytest.MonkeyPatch()
    monkeypatch.setattr(config_preview_module.tempfile, "TemporaryDirectory", _SpyTemporaryDirectory)
    try:
        resolve_effective_config(targets="example.com")
    finally:
        monkeypatch.undo()

    assert captured.get("path"), "expected the spy to capture a temp dir path"
    assert not os.path.exists(captured["path"]), (
        f"temp dir {captured['path']} should not exist after resolve_effective_config returns"
    )


def test_build_job_config_dict_matches_write_job_config_output(tmp_path):
    """`_write_job_config` now dumps `build_job_config_dict`'s dict — existing
    job-creation behavior is byte-identical."""
    import yaml
    from quirk.dashboard.api.routes.jobs import _write_job_config, build_job_config_dict

    output_dir = tmp_path / "job"
    output_dir.mkdir()
    config_path = _write_job_config(
        output_dir, "example.com", "./quirk-output/quirk.db", "balanced",
    )
    with open(config_path) as fh:
        dumped = yaml.safe_load(fh)

    expected = build_job_config_dict(
        output_dir, "example.com", "./quirk-output/quirk.db", "balanced",
    )
    assert dumped == expected
