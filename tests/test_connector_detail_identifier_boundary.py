"""Phase 197 / Plan 03 / Task 1 — PARITY-07 D-04 identifier/secret boundary.

RESEARCH verified live that all 37 widened `connectors.*` detail fields
(`quirk/dashboard/api/schemas.py::_CONNECTOR_DETAIL_KEY_TYPES`) are
NON-SECRET — zero of them appear in
`quirk/config_redaction.py::CREDENTIAL_REGISTRY`. PARITY-07 is therefore not
"build new secret plumbing" (none exists to build); it is two standing
proofs that the widened overlay never blurs the identifier/secret boundary
(D-04):

  - Test 1 (disjointness): the 37 detail keys and the registry's
    `connectors`-section secret names never overlap, derived live from both
    sources so a future field added to either side that collides is caught
    automatically.
  - Test 2 (credential-path exclusion): identifier-shaped detail fields
    (`adcs_user`, `pg_scanner_user`, `mysql_scanner_user`, and others) land
    in the job `config.yaml` in CLEARTEXT — that is correct, D-04 behavior,
    not a leak — while NONE of them are ever routed through
    `_build_credential_env`'s env-var injection path.

pytest -q tests/test_connector_detail_identifier_boundary.py
"""
from __future__ import annotations

import yaml
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from quirk.config_redaction import CREDENTIAL_REGISTRY
from quirk.dashboard.api.app import create_app
from quirk.dashboard.api.connector_availability import ConnectorAvailability, probe_all_connectors
from quirk.dashboard.api.deps import get_db
from quirk.dashboard.api.routes.jobs import _build_credential_env
from quirk.dashboard.api.schemas import _CONNECTOR_DETAIL_KEY_TYPES
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


def test_widened_detail_keys_disjoint_from_credential_registry():
    """Test 1: `set(_CONNECTOR_DETAIL_KEY_TYPES)` and the registry's
    `connectors`-section secret names must never overlap. Both sets are
    computed HERE, from the live sources, at test-run time — never a
    hand-typed list of 37 or of 5 — so a future phase adding a detail field
    that IS a registry secret fails this test rather than silently reopening
    the leak path Phase 193 closed."""
    detail_keys = set(_CONNECTOR_DETAIL_KEY_TYPES)
    registry_connector_secrets = {
        entry.name for entry in CREDENTIAL_REGISTRY if entry.section == "connectors"
    }

    assert detail_keys, "live source produced zero detail keys — test would be vacuous"
    assert registry_connector_secrets, (
        "live source produced zero registry secrets — test would be vacuous"
    )
    overlap = detail_keys & registry_connector_secrets
    assert not overlap, (
        f"widened detail fields overlap CREDENTIAL_REGISTRY secrets: {overlap} — "
        "these must ride the env-var credential path, not the plaintext overlay"
    )


def test_identifier_detail_fields_never_reach_credential_env_path():
    """Test 2b: `_build_credential_env` is called in isolation with a
    credentials payload covering every real `CREDENTIAL_REGISTRY` connectors
    secret. None of the 37 widened detail key NAMES may appear as a key in
    its returned `injected_env` mapping or its returned YAML fragment — the
    detail fields never enter this function's input at all in real traffic
    (they ride `payload.connectors`, not `payload.credentials`), so this
    proves the function's own output surface stays clean even if a future
    caller mistakenly forwarded a detail key here."""
    credentials_payload = {
        entry.name: "sekrit-value"
        for entry in CREDENTIAL_REGISTRY
        if entry.section == "connectors"
    }
    injected_env, yaml_fragment = _build_credential_env(credentials_payload)

    detail_keys = set(_CONNECTOR_DETAIL_KEY_TYPES)
    assert not (detail_keys & set(injected_env)), (
        f"a detail key leaked into injected_env: {detail_keys & set(injected_env)}"
    )
    assert not (detail_keys & set(yaml_fragment)), (
        f"a detail key leaked into the credential YAML fragment: "
        f"{detail_keys & set(yaml_fragment)}"
    )


def test_detail_identifiers_land_in_config_yaml_cleartext_never_in_credential_env(monkeypatch):
    """Test 2a: a full submission setting `adcs_user`, `pg_scanner_user`,
    `mysql_scanner_user` (plus a couple of other detail fields) alongside a
    REAL credentials payload for the connected secrets must:

      (a) write every detail key/value into the job config.yaml's
          `connectors:` block in CLEARTEXT — D-04: these are identifiers,
          and CLI/YAML parity requires they be visible; and
      (b) never route any detail key name into `_build_credential_env`'s
          returned `injected_env` keys or connectors YAML fragment.

    Both halves are asserted in the SAME test so the identifier-vs-secret
    distinction cannot be misread later as "detail values in config.yaml are
    a leak" (they are not) or "detail values missing from config.yaml is
    fine" (it would not be — that would break PARITY-05)."""
    monkeypatch.setattr("quirk.dashboard.api.routes.jobs.subprocess.Popen", _fake_popen)
    fake_map = _all_available_probe_map()
    monkeypatch.setattr(
        "quirk.dashboard.api.connector_availability.probe_all_connectors",
        lambda: fake_map,
    )

    detail_overlay = {
        "enable_adcs": True,
        "enable_db": True,
        "adcs_user": "svc-adcs-reader",
        "pg_scanner_user": "svc-pg-reader",
        "mysql_scanner_user": "svc-mysql-reader",
        "vault_addr": "https://vault.example.com:8200",
        "smime_timeout": 45,
    }
    secret_credentials = {
        "adcs_password": "adcs-secret-value",
        "pg_scanner_password": "pg-secret-value",
        "mysql_scanner_password": "mysql-secret-value",
    }

    _app, tc = _app_with_db()
    response = tc.post(
        "/api/jobs",
        json={
            "targets": "example.com",
            "profile": "quick",
            "connectors": detail_overlay,
            "credentials": secret_credentials,
        },
        headers={"X-Quirk-Request": "1"},
    )
    assert response.status_code == 201, response.text
    job_id = response.json()["job_id"]

    import quirk.dashboard.api.routes.jobs as jobs_module

    config_path = jobs_module._job_output_dir(job_id) / "config.yaml"
    config_text = config_path.read_text()
    config_dict = yaml.safe_load(config_text)
    connectors_block = config_dict.get("connectors", {})

    # (a) Detail identifiers reach config.yaml in cleartext under connectors:.
    assert connectors_block.get("adcs_user") == "svc-adcs-reader"
    assert connectors_block.get("pg_scanner_user") == "svc-pg-reader"
    assert connectors_block.get("mysql_scanner_user") == "svc-mysql-reader"
    assert connectors_block.get("vault_addr") == "https://vault.example.com:8200"
    assert connectors_block.get("smime_timeout") == 45

    # (a-negative) The REAL secrets never reach config.yaml in cleartext —
    # this is the sentinel guard's domain (extended in
    # tests/test_credential_no_leak_guard.py), re-asserted here so this
    # test's own positive claims about connectors_block aren't misread as
    # implying secrets are also written there.
    assert "adcs-secret-value" not in config_text
    assert "pg-secret-value" not in config_text
    assert "mysql-secret-value" not in config_text

    # (b) None of the 37 detail key names is present in the credential env
    # path's own output surface for this same credentials payload.
    injected_env, yaml_fragment = _build_credential_env(secret_credentials)
    detail_keys = set(_CONNECTOR_DETAIL_KEY_TYPES)
    assert not (detail_keys & set(injected_env))
    assert not (detail_keys & set(yaml_fragment))
