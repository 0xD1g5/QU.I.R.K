"""Tests for quirk.engine.profiles — Phase 72 D-02 / D-03 / WR-11 / WR-12.

Covers:
- D-02 (WR-11): apply_profile respects cfg.connectors._user_set_fields for
  enable_email / enable_broker. User-explicit values from YAML are not flipped.
- D-03 (WR-12): standard branch no-op _set_if_default calls were removed.
"""
from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Optional, List

import quirk.engine.profiles as profiles_mod
from quirk.engine.profiles import apply_profile


# ---------------------------------------------------------------------------
# Minimal cfg stubs (avoid importing the full AppConfig surface)
# ---------------------------------------------------------------------------

@dataclass
class _TimeoutsStub:
    fingerprint_seconds: int = 4
    tls_seconds: int = 6
    ssh_seconds: int = 6
    db_connect_seconds: int = 5
    vault_seconds: int = 10


@dataclass
class _ScanStub:
    timeout_seconds: Optional[int] = None
    concurrency: Optional[int] = None
    fingerprint_concurrency: int = 200
    tls_concurrency: int = 150
    ssh_concurrency: int = 100
    fingerprint_timeout_seconds: Optional[int] = None
    tls_timeout_seconds: Optional[int] = None
    ssh_timeout_seconds: Optional[int] = None
    tls_enum_mode: Optional[str] = None
    timeouts: _TimeoutsStub = field(default_factory=_TimeoutsStub)


@dataclass
class _ConnStub:
    enable_email: bool = False
    enable_broker: bool = False
    _user_set_fields: frozenset = field(default_factory=frozenset)


@dataclass
class _CfgStub:
    scan: _ScanStub = field(default_factory=_ScanStub)
    connectors: _ConnStub = field(default_factory=_ConnStub)


# ---------------------------------------------------------------------------
# D-02 / WR-11: respect user-explicit enable_email / enable_broker
# ---------------------------------------------------------------------------

def test_profiles_respects_user_explicit_enable_email_false():
    """User wrote `enable_email: false` in YAML — standard profile must NOT flip it."""
    cfg = _CfgStub()
    cfg.connectors.enable_email = False
    cfg.connectors._user_set_fields = frozenset({"enable_email"})
    apply_profile(cfg, "standard")
    assert cfg.connectors.enable_email is False


def test_profiles_flips_enable_email_when_not_user_set():
    """User omitted enable_email — standard profile defaults it to True."""
    cfg = _CfgStub()
    cfg.connectors.enable_email = False
    cfg.connectors._user_set_fields = frozenset()
    apply_profile(cfg, "standard")
    assert cfg.connectors.enable_email is True


def test_profiles_respects_user_explicit_enable_broker_false():
    """User wrote `enable_broker: false` in YAML — deep profile must NOT flip it."""
    cfg = _CfgStub()
    cfg.connectors.enable_broker = False
    cfg.connectors._user_set_fields = frozenset({"enable_broker"})
    apply_profile(cfg, "deep")
    assert cfg.connectors.enable_broker is False


def test_profiles_flips_enable_broker_when_not_user_set():
    """User omitted enable_broker — deep profile defaults it to True."""
    cfg = _CfgStub()
    cfg.connectors.enable_broker = False
    cfg.connectors._user_set_fields = frozenset()
    apply_profile(cfg, "deep")
    assert cfg.connectors.enable_broker is True


# ---------------------------------------------------------------------------
# D-03 / WR-12: standard branch no-op _set_if_default calls removed
# ---------------------------------------------------------------------------

def test_profiles_standard_branch_no_op_calls_removed():
    """Standard branch should contain at most 1 _set_if_default call (ssh_concurrency,
    which differs from the ScanCfg default of 100). The 5 no-op calls matching
    dataclass defaults were removed per D-03."""
    src = inspect.getsource(profiles_mod)
    # Split into pre-`else:` (deep + quick branches) vs `else:` (standard branch).
    # The standard branch lives after the final `else:` and before the safe-mode block.
    idx = src.rfind("        # standard")
    safe_mode_idx = src.find("safe-mode adjustments", idx)
    standard_src = src[idx:safe_mode_idx]
    # Only count uncommented call sites — comments referencing the removed calls
    # are intentionally retained as audit-evidence breadcrumbs (D-03 / WR-12).
    count = sum(
        1 for line in standard_src.splitlines()
        if "_set_if_default(" in line and not line.lstrip().startswith("#")
    )
    # Pre-Phase-72 baseline was 6 calls; post-fix should be 1 (ssh_concurrency).
    assert count == 1, (
        f"Expected exactly 1 _set_if_default call in standard branch "
        f"(ssh_concurrency=150 differs from ScanCfg default 100); found {count}.\n"
        f"Standard branch source:\n{standard_src}"
    )
