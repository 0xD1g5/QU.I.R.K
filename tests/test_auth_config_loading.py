"""Operator-token configuration loading for the dashboard API and `quirk serve`."""
from __future__ import annotations

import logging
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from quirk.dashboard.api.app import create_app
from quirk.dashboard.api.deps import get_db
from tests.conftest import make_isolated_memory_engine

TOKEN = "cfg-token-value"


def _client() -> TestClient:
    engine = make_isolated_memory_engine()
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def cfg(tmp_path, monkeypatch):
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)
    path = tmp_path / "config.yaml"
    monkeypatch.setenv("QUIRK_CONFIG_PATH", str(path))
    return path


def test_security_only_file_enables_auth(cfg):
    cfg.write_text(f"security:\n  api_token: {TOKEN}\n")
    tc = _client()
    assert tc.get("/api/scans").status_code == 401
    ok = tc.get("/api/scans", headers={"Authorization": f"Bearer {TOKEN}"})
    assert ok.status_code == 200


def test_malformed_yaml_answers_503_and_logs_reason(cfg, caplog):
    sentinel = f"SENTINEL-{uuid.uuid4().hex}"
    cfg.write_text(f"security:\n  api_token: {sentinel}\n bad: [\n")
    tc = _client()
    with caplog.at_level(logging.ERROR):
        resp = tc.get("/api/scans")
    assert resp.status_code == 503
    assert "DASHBOARD-014" in resp.text
    assert sentinel not in resp.text
    assert str(cfg) in caplog.text
    assert "YAMLError" in caplog.text or "Error" in caplog.text
    assert sentinel not in caplog.text


def test_top_level_not_a_mapping_answers_503(cfg):
    cfg.write_text("- a\n- b\n")
    assert _client().get("/api/scans").status_code == 503


def test_security_not_a_mapping_answers_503(cfg):
    cfg.write_text("security: [1, 2]\n")
    assert _client().get("/api/scans").status_code == 503


def test_complete_config_with_token_enforces_auth(cfg):
    from pathlib import Path

    text = (Path(__file__).resolve().parent.parent / "config.yaml").read_text()
    assert "api_token" not in text
    text = text.replace(
        "security:\n  allow_internal_targets: true",
        f"security:\n  allow_internal_targets: true\n  api_token: {TOKEN}",
    )
    cfg.write_text(text)
    tc = _client()
    assert tc.get("/api/scans").status_code == 401
    ok = tc.get("/api/scans", headers={"Authorization": f"Bearer {TOKEN}"})
    assert ok.status_code == 200


def test_empty_file_means_auth_off(cfg):
    cfg.write_text("")
    assert _client().get("/api/scans").status_code == 200


def test_comment_only_file_means_auth_off(cfg):
    cfg.write_text("# nothing configured\n")
    assert _client().get("/api/scans").status_code == 200


def test_absent_file_means_auth_off(cfg):
    assert not cfg.exists()
    assert _client().get("/api/scans").status_code == 200


def test_env_token_is_authoritative_over_unreadable_file(cfg, monkeypatch):
    cfg.write_text("security:\n  api_token: x\n bad: [\n")
    monkeypatch.setenv("QUIRK_API_TOKEN", "env-token")
    tc = _client()
    assert tc.get("/api/scans").status_code == 401
    ok = tc.get("/api/scans", headers={"Authorization": "Bearer env-token"})
    assert ok.status_code == 200


@pytest.mark.parametrize("host", ["127.0.0.1", "0.0.0.0"])
def test_serve_refuses_unreadable_config(cfg, monkeypatch, capsys, host):
    uvicorn = pytest.importorskip("uvicorn")
    sentinel = f"SENTINEL-{uuid.uuid4().hex}"
    cfg.write_text(f"security:\n  api_token: {sentinel}\n bad: [\n")
    calls = []
    monkeypatch.setattr(uvicorn, "run", lambda *a, **k: calls.append(1))
    from quirk.dashboard.server import serve

    with pytest.raises(SystemExit) as exc:
        serve(host=host, no_open=True)
    assert exc.value.code == 2
    err = capsys.readouterr()
    text = err.err + err.out
    assert str(cfg) in err.err
    assert "Error" in err.err
    assert "DASHBOARD-014" in err.err
    assert "network-reachable" not in text
    assert sentinel not in text
    assert calls == []


def test_resolver_indirection_is_live(cfg, monkeypatch):
    import quirk.dashboard.api.middleware.auth as auth_module
    from quirk.util.server_config import TokenState

    tc = _client()
    monkeypatch.setattr(
        auth_module, "_resolve_token_state", lambda: TokenState("", None)
    )
    assert tc.get("/api/scans").status_code == 200
    monkeypatch.setattr(
        auth_module, "_resolve_token_state", lambda: TokenState("", "x: Error")
    )
    assert tc.get("/api/scans").status_code == 503


# ---------------------------------------------------------------------------
# Only a missing file means "no config". A path that exists but cannot be
# reached, and a populated file that disappears or is emptied while the
# process runs, are the DASHBOARD-014 state.
# ---------------------------------------------------------------------------


def test_permission_error_on_stat_answers_503(cfg, monkeypatch):
    import os as _os

    import quirk.util.server_config as sc

    real_stat = _os.stat

    def denied(path, *a, **k):
        if str(path) == str(cfg):
            raise PermissionError(13, "Permission denied", str(path))
        return real_stat(path, *a, **k)

    monkeypatch.setattr(sc.os, "stat", denied)
    state = sc.resolve_operator_token()
    assert state.token == "" and state.error and "PermissionError" in state.error
    assert sc.load_server_security().error
    assert _client().get("/api/scans").status_code == 503


def test_untraversable_parent_directory_answers_503(tmp_path, monkeypatch):
    import quirk.util.server_config as sc

    locked = tmp_path / "locked"
    locked.mkdir()
    (locked / "config.yaml").write_text(f"security:\n  api_token: {TOKEN}\n")
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)
    monkeypatch.setenv("QUIRK_CONFIG_PATH", str(locked / "config.yaml"))
    locked.chmod(0)
    try:
        assert sc.resolve_operator_token().error
        assert _client().get("/api/scans").status_code == 503
    finally:
        locked.chmod(0o755)


def test_path_is_a_directory_answers_503(tmp_path, monkeypatch):
    import quirk.util.server_config as sc

    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)
    monkeypatch.setenv("QUIRK_CONFIG_PATH", str(tmp_path))
    state = sc.resolve_operator_token()
    assert state.token == "" and state.error
    assert sc.load_server_security().error
    assert _client().get("/api/scans").status_code == 503


def test_dangling_symlink_answers_503(cfg):
    import quirk.util.server_config as sc

    cfg.symlink_to(cfg.parent / "moved-away.yaml")
    assert sc.resolve_operator_token().error
    assert _client().get("/api/scans").status_code == 503


@pytest.mark.parametrize("change", ["removed", "emptied", "unreadable"])
def test_running_server_refuses_when_config_changes_after_token_seen(cfg, change):
    cfg.write_text(f"security:\n  api_token: {TOKEN}\n")
    tc = _client()
    hdr = {"Authorization": f"Bearer {TOKEN}"}
    assert tc.get("/api/scans", headers=hdr).status_code == 200
    if change == "removed":
        cfg.unlink()
    elif change == "emptied":
        cfg.write_text("")
    else:
        cfg.unlink()
        cfg.mkdir()
    assert tc.get("/api/scans").status_code == 503
    assert tc.get("/api/scans", headers=hdr).status_code == 503


def test_config_removed_after_serve_start_answers_503(cfg, monkeypatch):
    uvicorn = pytest.importorskip("uvicorn")
    cfg.write_text(f"security:\n  api_token: {TOKEN}\n")
    monkeypatch.setattr(uvicorn, "run", lambda *a, **k: None)
    from quirk.dashboard.server import serve

    serve(host="0.0.0.0", no_open=True)
    cfg.unlink()
    assert _client().get("/api/scans").status_code == 503


def test_fresh_install_states_stay_auth_off(tmp_path, monkeypatch):
    """Positive control: never-populated absent/empty/comment files are auth off."""
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)
    for name, body in (("absent.yaml", None), ("empty.yaml", ""), ("c.yaml", "# x\n")):
        path = tmp_path / name
        if body is not None:
            path.write_text(body)
        monkeypatch.setenv("QUIRK_CONFIG_PATH", str(path))
        assert _client().get("/api/scans").status_code == 200, name
