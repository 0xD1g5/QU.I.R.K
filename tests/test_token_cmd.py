"""Phase 102 AUTH-01 — token CLI: generate / rotate / show / no-clobber."""
from __future__ import annotations

import os
import pytest
import yaml

from quirk.cli.token_cmd import run_token, _write_token_to_config


def _make_config(tmp_path, extra: dict = None) -> str:
    """Write a minimal config.yaml with optional extra keys."""
    data = {
        "assessment": {"name": "test"},
        "security": {"api_token": ""},
    }
    if extra:
        data.update(extra)
    path = str(tmp_path / "config.yaml")
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False)
    return path


def test_token_generate_writes_config(tmp_path):
    """generate subcommand writes a non-empty token to security.api_token."""
    path = _make_config(tmp_path)
    with pytest.raises(SystemExit) as exc_info:
        run_token(["generate", "--config", path])
    assert exc_info.value.code == 0

    with open(path) as f:
        reloaded = yaml.safe_load(f)
    assert reloaded["security"]["api_token"] != ""


def test_token_rotate_overwrites(tmp_path):
    """Running generate twice produces two different tokens."""
    path = _make_config(tmp_path)

    with pytest.raises(SystemExit) as exc_info:
        run_token(["generate", "--config", path])
    assert exc_info.value.code == 0

    with open(path) as f:
        first_token = yaml.safe_load(f)["security"]["api_token"]

    with pytest.raises(SystemExit) as exc_info:
        run_token(["generate", "--config", path])
    assert exc_info.value.code == 0

    with open(path) as f:
        second_token = yaml.safe_load(f)["security"]["api_token"]

    assert first_token != second_token


def test_token_show(tmp_path, capsys, monkeypatch):
    """show subcommand prints the persisted YAML token to stdout."""
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)
    known_token = "test-known-token-abc123"
    path = _make_config(tmp_path)

    with open(path) as f:
        raw = yaml.safe_load(f)
    raw["security"]["api_token"] = known_token
    with open(path, "w") as f:
        yaml.dump(raw, f, default_flow_style=False)

    with pytest.raises(SystemExit) as exc_info:
        run_token(["show", "--config", path])
    assert exc_info.value.code == 0

    captured = capsys.readouterr()
    assert known_token in captured.out


def test_token_generate_preserves_other_keys(tmp_path):
    """generate must not clobber other config keys (YAML round-trip safety)."""
    path = _make_config(tmp_path, extra={
        "targets": [{"host": "192.168.1.1"}],
    })

    with pytest.raises(SystemExit) as exc_info:
        run_token(["generate", "--config", path])
    assert exc_info.value.code == 0

    with open(path) as f:
        reloaded = yaml.safe_load(f)

    assert reloaded["assessment"] == {"name": "test"}
    assert reloaded["targets"] == [{"host": "192.168.1.1"}]
    assert reloaded["security"]["api_token"] != ""
