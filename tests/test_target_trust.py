"""Tests for quirk/util/target_trust.py — Phase 143 / TAIL-02.

Covers the allowlist matcher (``is_target_trusted``) and the single CLI-side
enforcement chokepoint (``enforce_trusted_targets``), per D-03 (empty =
allow-all) and D-06 (exact host/IP + CIDR containment only, no wildcards).
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from quirk.util.target_trust import RC_NOT_IN_ALLOWLIST, enforce_trusted_targets, is_target_trusted


def test_empty_allowlist_allows_all():
    """D-03: an empty/absent trusted_targets list allows everything."""
    result = is_target_trusted("1.2.3.4", [])
    assert result.ok is True


def test_exact_and_cidr_matching():
    """D-06: exact string membership and CIDR containment both match."""
    exact = is_target_trusted("host.example.com", ["host.example.com"])
    assert exact.ok is True

    cidr_match = is_target_trusted("10.0.0.5", ["10.0.0.0/24"])
    assert cidr_match.ok is True

    cidr_miss = is_target_trusted("192.168.9.9", ["10.0.0.0/24"])
    assert cidr_miss.ok is False
    assert cidr_miss.reason == RC_NOT_IN_ALLOWLIST


def test_cli_entry_point_enforces():
    """enforce_trusted_targets() raises for out-of-allowlist CLI targets, is a
    no-op when trusted_targets is empty (D-03)."""
    cfg = SimpleNamespace(
        security=SimpleNamespace(trusted_targets=["10.0.0.0/24"]),
        targets=SimpleNamespace(fqdns=[], cidrs=["192.168.9.0/24"]),
    )
    with pytest.raises(ValueError):
        enforce_trusted_targets(cfg)

    cfg_open = SimpleNamespace(
        security=SimpleNamespace(trusted_targets=[]),
        targets=SimpleNamespace(fqdns=["anything.example.com"], cidrs=[]),
    )
    enforce_trusted_targets(cfg_open)  # must not raise


def test_enforce_trusted_targets_rejects_out_of_allowlist_broker_host():
    """T-190-01 (Phase 190): a connectors.broker_targets host outside the
    allowlist is rejected by the same chokepoint as targets.fqdns/cidrs."""
    cfg = SimpleNamespace(
        security=SimpleNamespace(trusted_targets=["10.0.0.0/24"]),
        targets=SimpleNamespace(fqdns=[], cidrs=[]),
        connectors=SimpleNamespace(broker_targets=["evil.example.com:29092"]),
    )
    with pytest.raises(ValueError):
        enforce_trusted_targets(cfg)


def test_enforce_trusted_targets_allows_in_allowlist_broker_host():
    cfg = SimpleNamespace(
        security=SimpleNamespace(trusted_targets=["kafka.internal"]),
        targets=SimpleNamespace(fqdns=[], cidrs=[]),
        connectors=SimpleNamespace(broker_targets=["kafka.internal:29092"]),
    )
    enforce_trusted_targets(cfg)  # must not raise


def test_enforce_trusted_targets_empty_allowlist_allows_broker_host():
    """D-03: empty allowlist is allow-all, including for broker_targets hosts."""
    cfg = SimpleNamespace(
        security=SimpleNamespace(trusted_targets=[]),
        targets=SimpleNamespace(fqdns=[], cidrs=[]),
        connectors=SimpleNamespace(broker_targets=["anything.example.com:29092"]),
    )
    enforce_trusted_targets(cfg)  # must not raise


def test_enforce_trusted_targets_unchanged_with_no_broker_targets():
    """Backward compatibility: cfg with no connectors attribute at all behaves
    exactly as before (no AttributeError, no behavior change)."""
    cfg = SimpleNamespace(
        security=SimpleNamespace(trusted_targets=["10.0.0.0/24"]),
        targets=SimpleNamespace(fqdns=[], cidrs=["10.0.0.0/24"]),
    )
    enforce_trusted_targets(cfg)  # must not raise; no connectors attr present
