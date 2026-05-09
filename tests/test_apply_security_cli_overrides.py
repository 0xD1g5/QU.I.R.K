"""Tests for apply_security_cli_overrides in run_scan.py — Phase 57 / WR-06.

Verifies the critical security invariant: a YAML-loaded True flag MUST NOT be
revoked when the corresponding CLI argument is absent (False default).
"""
from types import SimpleNamespace

from run_scan import apply_security_cli_overrides


def test_apply_security_cli_overrides_yaml_true_not_revoked():
    """WR-06: absent CLI flags (False) must not override YAML-loaded True values."""
    cfg = SimpleNamespace(security=SimpleNamespace(
        allow_insecure_jwks=True,
        allow_internal_targets=True,
        allow_cleartext_broker_probe=True,
    ))
    args = SimpleNamespace(
        allow_insecure_jwks=False,
        allow_internal_targets=False,
        allow_cleartext_broker_probe=False,
    )
    apply_security_cli_overrides(cfg, args)
    assert cfg.security.allow_insecure_jwks is True
    assert cfg.security.allow_internal_targets is True
    assert cfg.security.allow_cleartext_broker_probe is True


def test_apply_security_cli_overrides_cli_true_escalates():
    """CLI True flags escalate a False YAML value to True (opt-in path)."""
    cfg = SimpleNamespace(security=SimpleNamespace(
        allow_insecure_jwks=False,
        allow_internal_targets=False,
        allow_cleartext_broker_probe=False,
    ))
    args = SimpleNamespace(
        allow_insecure_jwks=True,
        allow_internal_targets=True,
        allow_cleartext_broker_probe=True,
    )
    apply_security_cli_overrides(cfg, args)
    assert cfg.security.allow_insecure_jwks is True
    assert cfg.security.allow_internal_targets is True
    assert cfg.security.allow_cleartext_broker_probe is True
