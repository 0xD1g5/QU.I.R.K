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


_PRECEDENCE_NOTE = (
    "a QUIRK_API_TOKEN set in the dashboard server's environment takes "
    "precedence over this file and is not changed by this command."
)


@pytest.mark.parametrize("action", ["generate", "rotate"])
def test_token_cmd_states_env_precedence_when_unset(tmp_path, capsys, monkeypatch, action):
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)
    path = _make_config(tmp_path)
    with pytest.raises(SystemExit):
        run_token([action, "--config", path])
    assert _PRECEDENCE_NOTE in capsys.readouterr().out


def test_token_cmd_precedence_note_once_when_env_set(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("QUIRK_API_TOKEN", "shell-token")
    path = _make_config(tmp_path)
    with pytest.raises(SystemExit):
        run_token(["rotate", "--config", path])
    out = capsys.readouterr().out
    assert out.count(_PRECEDENCE_NOTE) == 1
    assert "also set in this shell" in out


def test_token_rotate_help_does_not_promise_immediate_invalidation(capsys):
    with pytest.raises(SystemExit):
        run_token(["--help"])
    assert "immediately" not in capsys.readouterr().out


def test_generated_security_only_file_enforces_dashboard_auth(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import sessionmaker

    from quirk.dashboard.api.app import create_app
    from quirk.dashboard.api.deps import get_db
    from tests.conftest import make_isolated_memory_engine

    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)
    path = tmp_path / "fresh.yaml"
    with pytest.raises(SystemExit):
        run_token(["generate", "--config", str(path)])
    assert list(yaml.safe_load(path.read_text())) == ["security"]
    monkeypatch.setenv("QUIRK_CONFIG_PATH", str(path))

    session_factory = sessionmaker(bind=make_isolated_memory_engine())

    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    tc = TestClient(app, raise_server_exceptions=False)
    assert tc.get("/api/scans").status_code == 401
