"""Phase 192 / PARITY-01 / D-05 / D-06 / D-07 — redaction registry guard tests.

Two families of guarantees:

1. The credential registry, fail-closed pattern net, and presence helper
   behave per D-05/D-06 (Task 1).
2. `redact_config()` never leaks a raw credential value, and a run-time
   source-scan (not a hand-maintained list) proves every credential-shaped
   field on the live dataclasses is either registered or explicitly
   dispositioned safe (Task 2) — per CLAUDE.md's standing rule that a
   hand-derived enumeration list is not a safeguard.
"""

import dataclasses
import json
import os

import pytest

from quirk.config import (
    AppConfig,
    AssessmentCfg,
    BrokerCredential,
    ConnectorsCfg,
    IntelligenceCfg,
    OutputCfg,
    ScanCfg,
    SecurityCfg,
    SnmpV3Credential,
    TargetsCfg,
)
from quirk.config_redaction import (
    CREDENTIAL_NAME_PATTERN,
    CREDENTIAL_NAME_SAFE_FIELDS,
    CREDENTIAL_REGISTRY,
    REDACTED_SET,
    REDACTED_UNSET,
    credential_is_set,
    is_credential_field,
    redact_config,
)


def _make_app_config(**overrides) -> AppConfig:
    base = dict(
        assessment=AssessmentCfg(
            name="test", data_classification="internal", report_owner="me", timezone="UTC"
        ),
        scan=ScanCfg(concurrency=10, ports_tls=[443]),
        targets=TargetsCfg(fqdns=[], cidrs=[], include_ips=[], exclude_ips=[]),
        connectors=ConnectorsCfg(),
        output=OutputCfg(directory="out", db_path="out/quirk.db"),
        intelligence=IntelligenceCfg(),
        security=SecurityCfg(),
        broker_credentials={},
        remediation_aliases={},
    )
    base.update(overrides)
    return AppConfig(**base)


# ---------------------------------------------------------------------------
# Task 1: registry, fail-closed pattern net, presence helper
# ---------------------------------------------------------------------------


def test_registry_has_at_least_six_entries():
    assert len(CREDENTIAL_REGISTRY) >= 6


def test_registry_hit_is_credential_field():
    assert is_credential_field("connectors", "vault_token") is True


def test_pattern_net_catches_unregistered_credential_shaped_field():
    # Fail-closed: not in the registry, but matches the pattern net.
    assert is_credential_field("connectors", "fictional_new_password") is True


def test_non_credential_field_is_not_flagged():
    assert is_credential_field("connectors", "jwt_targets") is False


def test_safe_listed_env_var_name_field_is_not_flagged():
    # pass_env holds an env-var NAME, not a secret.
    assert is_credential_field("connectors", "pass_env") is False


def test_bare_key_token_not_in_pattern():
    assert CREDENTIAL_NAME_PATTERN.search("azure_keyvault_urls") is None
    assert CREDENTIAL_NAME_PATTERN.search("ssh_key_types") is None


def test_credential_is_set_true_from_env_fallback(monkeypatch):
    monkeypatch.setenv("VAULT_TOKEN", "s.abc123")
    assert credential_is_set("connectors", "vault_token", None) is True


def test_credential_is_set_false_when_absent(monkeypatch):
    monkeypatch.delenv("VAULT_TOKEN", raising=False)
    assert credential_is_set("connectors", "vault_token", None) is False


def test_credential_is_set_false_for_empty_string():
    assert credential_is_set("security", "api_token", "") is False


def test_credential_is_set_true_for_nonempty_value():
    assert credential_is_set("security", "api_token", "abc") is True


# ---------------------------------------------------------------------------
# Phase 193 / PARITY-03 / D-09 / D-10: every registry entry has a live
# env_fallback (run-time-derived, not a hand-listed count), plus precedence
# coverage for the four newly-added fields.
# ---------------------------------------------------------------------------


def test_every_registry_entry_has_a_nonempty_env_fallback():
    """D-10: the registry stays the single machine-readable driver -- a
    future bare CredentialField (no env_fallback) is a CI failure, not a
    silent dashboard dead-end. Derived by iterating the live registry, never
    a hand-written list of names."""
    offenders = [
        (e.section, e.name) for e in CREDENTIAL_REGISTRY if not e.env_fallback
    ]
    assert not offenders, f"CREDENTIAL_REGISTRY entries missing env_fallback: {offenders}"


_NEW_FALLBACK_FIELDS = [
    ("connectors", "adcs_password", "QUIRK_ADCS_PASSWORD"),
    ("connectors", "pg_scanner_password", "QUIRK_PG_SCANNER_PASSWORD"),
    ("connectors", "mysql_scanner_password", "QUIRK_MYSQL_SCANNER_PASSWORD"),
    ("connectors", "snmp_community", "QUIRK_SNMP_COMMUNITY"),
]


@pytest.mark.parametrize("section,name,env_var", _NEW_FALLBACK_FIELDS)
def test_credential_is_set_true_when_only_env_var_present(monkeypatch, section, name, env_var):
    monkeypatch.setenv(env_var, "injected-value")
    assert credential_is_set(section, name, None) is True


@pytest.mark.parametrize("section,name,env_var", _NEW_FALLBACK_FIELDS)
def test_credential_is_set_false_when_neither_present(monkeypatch, section, name, env_var):
    monkeypatch.delenv(env_var, raising=False)
    assert credential_is_set(section, name, None) is False


@pytest.mark.parametrize("section,name,env_var", _NEW_FALLBACK_FIELDS)
def test_credential_is_set_true_when_config_set_and_env_unset(monkeypatch, section, name, env_var):
    monkeypatch.delenv(env_var, raising=False)
    assert credential_is_set(section, name, "configured-value") is True


def test_redact_config_reports_set_for_adcs_password_from_env_only(monkeypatch):
    """D-10: an env-only-populated credential renders as REDACTED_SET, not
    REDACTED_UNSET, in the effective-config preview."""
    monkeypatch.setenv("QUIRK_ADCS_PASSWORD", "injected-secret")
    cfg = _make_app_config(connectors=ConnectorsCfg(adcs_password=None))
    result = redact_config(cfg)
    assert result["connectors"]["adcs_password"] == REDACTED_SET
    assert result["connectors"]["adcs_password"] != REDACTED_UNSET


# ---------------------------------------------------------------------------
# Task 2: redact_config() dataclass walker
# ---------------------------------------------------------------------------


def test_redact_config_hides_raw_secret_value():
    cfg = _make_app_config(connectors=ConnectorsCfg(vault_token="s.realsecret"))
    result = redact_config(cfg)
    assert result["connectors"]["vault_token"] == REDACTED_SET
    assert "s.realsecret" not in json.dumps(result)


def test_redact_config_reports_not_set(monkeypatch):
    monkeypatch.delenv("VAULT_TOKEN", raising=False)
    cfg = _make_app_config(connectors=ConnectorsCfg(vault_token=None))
    result = redact_config(cfg)
    assert result["connectors"]["vault_token"] == REDACTED_UNSET


def test_every_registry_entry_redacts_in_output(monkeypatch):
    monkeypatch.setenv("VAULT_TOKEN", "s.env-fallback")
    cfg = _make_app_config(
        connectors=ConnectorsCfg(
            vault_token="s.secret",
            adcs_password="pw1",
            pg_scanner_password="pw2",
            mysql_scanner_password="pw3",
            snmp_community="private",
        ),
        security=SecurityCfg(api_token="tok"),
    )
    result = redact_config(cfg)
    for entry in CREDENTIAL_REGISTRY:
        value = result[entry.section][entry.name]
        assert value in (REDACTED_SET, REDACTED_UNSET), (entry.section, entry.name, value)


def test_jwt_target_url_userinfo_never_survives_verbatim():
    """Review WR-08: connectors.jwt_targets entries are operator-supplied URLs;
    a URL with embedded basic-auth userinfo must not be emitted verbatim by
    redact_config — the userinfo component is scrubbed."""
    cfg = _make_app_config(
        connectors=ConnectorsCfg(
            jwt_targets=["https://svc:hunter2@api.example.com/token"],
        )
    )
    result = redact_config(cfg)
    dumped = json.dumps(result)
    assert "hunter2" not in dumped
    assert "svc:hunter2@" not in dumped
    # The host itself stays visible — only userinfo is collapsed.
    assert "api.example.com" in dumped


def test_plain_dict_credential_shaped_key_is_redacted():
    """Review WR-08: the D-06 fail-closed net must apply to plain-dict KEYS,
    not only dataclass fields — a credential-named key inside a plain dict
    value collapses to set/not-set."""
    from quirk.config_redaction import _redact_value

    result = _redact_value(
        {"api_token": "raw-secret-value", "endpoint": "https://api.example.com"},
        "connectors",
    )
    assert result["api_token"] == REDACTED_SET
    assert result["endpoint"] == "https://api.example.com"


def test_redact_config_output_is_json_serializable():
    cfg = _make_app_config()
    json.dumps(redact_config(cfg))  # must not raise


def test_redact_config_recurses_broker_credentials():
    cfg = _make_app_config(
        broker_credentials={"host:1234": BrokerCredential(user="alice", pass_env="BROKER_PW")}
    )
    result = redact_config(cfg)
    entry = result["broker_credentials"]["host:1234"]
    assert entry["user"] == "alice"
    assert entry["pass_env"] == "BROKER_PW"


def test_redact_config_recurses_snmp_v3_credentials():
    cfg = _make_app_config(
        connectors=ConnectorsCfg(
            snmp_v3_credentials={
                "10.0.0.1": SnmpV3Credential(
                    username="op", auth_key_env="SNMP_AUTH", priv_key_env="SNMP_PRIV"
                )
            }
        )
    )
    result = redact_config(cfg)
    entry = result["connectors"]["snmp_v3_credentials"]["10.0.0.1"]
    assert entry["username"] == "op"
    assert entry["auth_key_env"] == "SNMP_AUTH"
    assert entry["priv_key_env"] == "SNMP_PRIV"


def test_redact_config_never_emits_underscore_fields():
    cfg = _make_app_config()
    result = redact_config(cfg)
    assert "_user_set_fields" not in result["connectors"]


# ---------------------------------------------------------------------------
# Run-time source-scan guard (D-06 / CLAUDE.md: no hand-derived enumeration)
# ---------------------------------------------------------------------------

_SCANNED_DATACLASSES = {
    "connectors": ConnectorsCfg,
    "broker_credentials": BrokerCredential,
    "snmp_v3_credentials": SnmpV3Credential,
    "security": SecurityCfg,
    "app": AppConfig,
}


def test_every_credential_shaped_field_is_registered_or_safe_listed():
    """Enumerate live dataclasses.fields() at run time — not a literal list."""
    offenders = []
    for section, cls in _SCANNED_DATACLASSES.items():
        for f in dataclasses.fields(cls):
            name = f.name
            if name.startswith("_"):
                continue
            if not CREDENTIAL_NAME_PATTERN.search(name):
                continue
            if name in CREDENTIAL_NAME_SAFE_FIELDS:
                continue
            if any(e.section == section and e.name == name for e in CREDENTIAL_REGISTRY):
                continue
            offenders.append((section, name))
    assert not offenders, (
        "Found credential-shaped field(s) with no disposition: "
        f"{offenders}. Add a CREDENTIAL_REGISTRY entry (if a real secret) "
        "or a justified CREDENTIAL_NAME_SAFE_FIELDS entry (if not) — never "
        "relax CREDENTIAL_NAME_PATTERN."
    )
