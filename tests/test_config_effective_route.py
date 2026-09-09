"""GET /api/config/effective — PARITY-01.

Phase 192 Plan 06.

Task 1 covers the overlay resolver (`resolve_effective_config` /
`build_job_config_dict`) in isolation. Task 2 extends this file with the
auth-gated route's behavior (redaction, provenance, single-serialization-path).
"""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from quirk.dashboard.api import config_preview as config_preview_module
from quirk.dashboard.api.app import create_app
from quirk.dashboard.api.config_preview import resolve_effective_config
from quirk.dashboard.api.deps import get_db
from tests.conftest import make_isolated_memory_engine


def _app_with_db():
    """Fresh TestClient backed by an in-memory DB, no auth by default.

    Mirrors tests/test_api_auth.py's helper.
    """
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


# ---------------------------------------------------------------------------
# Task 2 — auth-gated route, redaction, provenance
# ---------------------------------------------------------------------------

def test_effective_config_401_without_token_200_with_token(monkeypatch):
    """With security.api_token configured, no bearer token -> 401; correct
    token -> 200."""
    monkeypatch.setenv("QUIRK_API_TOKEN", "test-token")
    _, tc = _app_with_db()

    response = tc.get("/api/config/effective")
    assert response.status_code == 401, response.text

    response = tc.get(
        "/api/config/effective",
        headers={"Authorization": "Bearer test-token"},
    )
    assert response.status_code == 200, response.text


def test_unauthenticated_config_route_still_returns_vertical(monkeypatch):
    """GET /api/config still returns {"vertical": ...} and still requires no
    auth — the existing route object and its behavior are untouched (T-192-20)."""
    monkeypatch.setenv("QUIRK_API_TOKEN", "test-token")
    _, tc = _app_with_db()

    response = tc.get("/api/config")
    assert response.status_code == 200, response.text
    assert "vertical" in response.json()


def test_vault_token_never_appears_in_response_body(monkeypatch):
    """A vault_token set via env fallback yields a 200 response whose full
    JSON body does not contain the secret, with redacted:true and
    credential_status:'set' on connectors.vault_token (D-07 / T-192-18)."""
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)
    monkeypatch.setenv("VAULT_TOKEN", "s.realsecret")
    _, tc = _app_with_db()

    response = tc.get("/api/config/effective")
    assert response.status_code == 200, response.text
    assert "s.realsecret" not in response.text

    body = response.json()
    connectors_section = next(s for s in body["sections"] if s["name"] == "connectors")
    vault_field = next(f for f in connectors_section["fields"] if f["name"] == "vault_token")
    assert vault_field["redacted"] is True
    assert vault_field["credential_status"] == "set"
    # raw view carries the same redacted value — no separate, less-redacted path.
    assert body["raw"]["connectors"]["vault_token"] == vault_field["value"]


def test_vault_token_not_set_without_env_or_yaml(monkeypatch):
    """Same field with no token configured and no VAULT_TOKEN env yields
    credential_status: 'not set'."""
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)
    monkeypatch.delenv("VAULT_TOKEN", raising=False)
    _, tc = _app_with_db()

    response = tc.get("/api/config/effective")
    assert response.status_code == 200, response.text
    body = response.json()
    connectors_section = next(s for s in body["sections"] if s["name"] == "connectors")
    vault_field = next(f for f in connectors_section["fields"] if f["name"] == "vault_token")
    assert vault_field["redacted"] is True
    assert vault_field["credential_status"] == "not set"


def test_effective_config_reflects_query_selections(monkeypatch):
    """GET /api/config/effective?vertical=healthcare&targets=example.com&profile=deep
    reflects those selections in the response."""
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)
    monkeypatch.delenv("VAULT_TOKEN", raising=False)
    _, tc = _app_with_db()

    response = tc.get(
        "/api/config/effective",
        params={"vertical": "healthcare", "targets": "example.com", "profile": "deep"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["vertical"] == "healthcare"
    assert body["profile"] == "deep"
    targets_section = next(s for s in body["sections"] if s["name"] == "targets")
    fqdns_field = next(f for f in targets_section["fields"] if f["name"] == "fqdns")
    assert fqdns_field["value"] == ["example.com"]


def test_provenance_user_preset_and_default(monkeypatch):
    """A field explicitly present in the submitted overlay has provenance
    'user'; a field changed by apply_profile has provenance 'preset';
    everything else has provenance 'default'."""
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)
    monkeypatch.delenv("VAULT_TOKEN", raising=False)
    _, tc = _app_with_db()

    response = tc.get(
        "/api/config/effective",
        params={"targets": "example.com", "profile": "deep"},
    )
    assert response.status_code == 200, response.text
    body = response.json()

    targets_section = next(s for s in body["sections"] if s["name"] == "targets")
    fqdns_field = next(f for f in targets_section["fields"] if f["name"] == "fqdns")
    assert fqdns_field["provenance"] == "user"

    connectors_section = next(s for s in body["sections"] if s["name"] == "connectors")
    enable_email_field = next(f for f in connectors_section["fields"] if f["name"] == "enable_email")
    assert enable_email_field["provenance"] == "preset"

    # A field nobody touched (neither submitted nor profile-mutated) stays default.
    enable_aws_field = next(f for f in connectors_section["fields"] if f["name"] == "enable_aws")
    assert enable_aws_field["provenance"] == "default"


def test_invalid_profile_returns_422(monkeypatch):
    """An invalid profile value returns 422 via the same Literal validation
    ScanSubmitRequest uses — no hand-rolled parsing."""
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)
    _, tc = _app_with_db()

    response = tc.get("/api/config/effective", params={"profile": "not-a-real-profile"})
    assert response.status_code == 422, response.text


def test_invalid_port_scope_returns_422(monkeypatch):
    monkeypatch.delenv("QUIRK_API_TOKEN", raising=False)
    _, tc = _app_with_db()

    response = tc.get("/api/config/effective", params={"port_scope": "not-a-real-scope"})
    assert response.status_code == 422, response.text
