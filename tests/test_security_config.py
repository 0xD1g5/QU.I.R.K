"""Tests for Phase 57 SecurityCfg + BrokerCredential config loading (D-04, D-05)."""
import pytest
from quirk.config import (
    config_from_dict,
    SecurityCfg,
    BrokerCredential,
)
from dataclasses import FrozenInstanceError
from types import SimpleNamespace


# Minimal-valid raw dict matching what config_from_dict requires.
# Sourced from tests/test_broker_config_and_profile.py _MINIMAL_RAW pattern.
def _base_raw() -> dict:
    return {
        "assessment": {
            "name": "test",
            "data_classification": "internal",
            "report_owner": "tester",
            "timezone": "UTC",
        },
        "scan": {
            "timeout_seconds": 5,
            "concurrency": 200,
            "ports_tls": [443],
        },
        "targets": {
            "fqdns": [],
            "cidrs": [],
            "include_ips": [],
            "exclude_ips": [],
        },
        "output": {
            "directory": "/tmp/quirk-test",
            "db_path": "/tmp/quirk-test.db",
        },
    }


def test_security_block_missing_defaults_safe():
    cfg = config_from_dict(_base_raw())
    assert cfg.security == SecurityCfg(False, False, False)


def test_security_block_partial_load():
    raw = _base_raw()
    raw["security"] = {"allow_insecure_jwks": True}
    cfg = config_from_dict(raw)
    assert cfg.security.allow_insecure_jwks is True
    assert cfg.security.allow_internal_targets is False
    assert cfg.security.allow_cleartext_broker_probe is False


def test_broker_credentials_load():
    raw = _base_raw()
    raw["broker_credentials"] = {
        "rabbit.lab:15672": {"user": "admin", "pass_env": "RABBIT_LAB_PASS"}
    }
    cfg = config_from_dict(raw)
    assert cfg.broker_credentials["rabbit.lab:15672"] == BrokerCredential(
        user="admin", pass_env="RABBIT_LAB_PASS"
    )


def test_broker_credentials_missing_defaults_empty():
    cfg = config_from_dict(_base_raw())
    assert cfg.broker_credentials == {}


def test_broker_credential_is_frozen():
    bc = BrokerCredential(user="x", pass_env="Y_PASS")
    with pytest.raises(FrozenInstanceError):
        bc.user = "z"  # type: ignore[misc]


def test_security_non_bool_coerced():
    """Non-bool YAML values are coerced via bool() and never raise."""
    raw = _base_raw()
    raw["security"] = {"allow_internal_targets": 1, "allow_cleartext_broker_probe": 0}
    cfg = config_from_dict(raw)
    assert cfg.security.allow_internal_targets is True
    assert cfg.security.allow_cleartext_broker_probe is False


def test_broker_credentials_non_dict_entry_skipped():
    """Non-dict credential entries are silently skipped (defensive loading)."""
    raw = _base_raw()
    raw["broker_credentials"] = {
        "bad.host:9999": "not-a-dict",
        "good.host:5672": {"user": "admin", "pass_env": "GOOD_PASS"},
    }
    cfg = config_from_dict(raw)
    assert "bad.host:9999" not in cfg.broker_credentials
    assert cfg.broker_credentials["good.host:5672"] == BrokerCredential(
        user="admin", pass_env="GOOD_PASS"
    )


# ---- CLI override tests (Task 2) ----

from run_scan import apply_security_cli_overrides


def test_cli_flag_flips_false_to_true():
    cfg = config_from_dict(_base_raw())
    args = SimpleNamespace(
        allow_internal_targets=True,
        allow_cleartext_broker_probe=False,
        allow_insecure_jwks=False,
    )
    apply_security_cli_overrides(cfg, args)
    assert cfg.security.allow_internal_targets is True
    assert cfg.security.allow_cleartext_broker_probe is False
    assert cfg.security.allow_insecure_jwks is False


def test_cli_absent_does_not_flip_true_to_false():
    raw = _base_raw()
    raw["security"] = {"allow_insecure_jwks": True}
    cfg = config_from_dict(raw)
    args = SimpleNamespace(
        allow_internal_targets=False,
        allow_cleartext_broker_probe=False,
        allow_insecure_jwks=False,  # CLI default
    )
    apply_security_cli_overrides(cfg, args)
    assert cfg.security.allow_insecure_jwks is True  # YAML wins, CLI didn't flip


def test_cli_help_mentions_three_flags():
    # smoke: the parser exposes the three flags
    import run_scan
    import pathlib
    src = pathlib.Path(run_scan.__file__).read_text()
    assert "--allow-internal-targets" in src
    assert "--allow-cleartext-broker-probe" in src
    assert "--allow-insecure-jwks" in src
