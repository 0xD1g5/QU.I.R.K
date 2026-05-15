"""Phase 71 / Plan 71-05 contract tests.

Covers WR-11 (unified extras messaging), WR-12 (motion_concurrency knob),
WR-13 (discovery/tls_scanner.py deletion), WR-14 (target_expander cap +
stable dedup + IP normalization).
"""

from __future__ import annotations

import importlib
import importlib.util
import inspect
import ipaddress
from dataclasses import dataclass, field
from typing import List

import pytest

from quirk.config import ScanCfg
from quirk.scanner import broker_scanner, container_scanner, email_scanner, source_scanner
from quirk.scanner import target_expander


# ---------------------------------------------------------------------------
# Test cfg helpers
# ---------------------------------------------------------------------------

@dataclass
class _Targets:
    fqdns: List[str] = field(default_factory=list)
    cidrs: List[str] = field(default_factory=list)
    include_ips: List = field(default_factory=list)
    exclude_ips: List = field(default_factory=list)


@dataclass
class _Scan:
    ports_tls: List[int] = field(default_factory=lambda: [443])


@dataclass
class _Cfg:
    targets: _Targets = field(default_factory=_Targets)
    scan: _Scan = field(default_factory=_Scan)


# ---------------------------------------------------------------------------
# WR-11: unified extras messaging
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("mod", [email_scanner, broker_scanner, container_scanner, source_scanner])
def test_extras_messages_use_unified_format(mod):
    src = inspect.getsource(mod)
    assert "is not installed — pip install 'quirk[" in src, (
        f"{mod.__name__} missing unified extras-error message format"
    )


# ---------------------------------------------------------------------------
# WR-12: ScanCfg.motion_concurrency + scanner wiring
# ---------------------------------------------------------------------------

def test_scancfg_motion_concurrency_default_is_50():
    cfg = ScanCfg(concurrency=10, ports_tls=[443])
    assert cfg.motion_concurrency == 50


def test_scancfg_motion_concurrency_configurable():
    cfg = ScanCfg(concurrency=10, ports_tls=[443], motion_concurrency=10)
    assert cfg.motion_concurrency == 10


def test_email_scanner_uses_motion_concurrency():
    src = inspect.getsource(email_scanner)
    assert "motion_concurrency" in src
    assert "min(len(tasks), 50)" not in src


def test_broker_scanner_uses_motion_concurrency():
    src = inspect.getsource(broker_scanner)
    assert src.count("motion_concurrency") >= 3  # 3 functions × (param + use)
    assert "min(len(tasks), 50)" not in src
    assert "min(len(all_tasks), 50)" not in src


# ---------------------------------------------------------------------------
# WR-13: discovery/tls_scanner.py deletion
# ---------------------------------------------------------------------------

def test_discovery_tls_scanner_deleted():
    assert importlib.util.find_spec("quirk.discovery.tls_scanner") is None


def test_scanner_tls_scanner_still_imports():
    from quirk.scanner import tls_scanner as live_tls  # noqa: F401
    assert live_tls is not None


# ---------------------------------------------------------------------------
# WR-14: target_expander cap + stable dedup + IP normalization
# ---------------------------------------------------------------------------

def test_expand_targets_caps_large_cidr():
    cfg = _Cfg(targets=_Targets(cidrs=["10.0.0.0/8"]))
    with pytest.raises(ValueError, match="refusing to scan more than 1024"):
        target_expander.expand_targets(cfg)


def test_expand_targets_allows_small_cidr():
    cfg = _Cfg(targets=_Targets(cidrs=["192.168.1.0/24"]))
    out = target_expander.expand_targets(cfg)
    # /24 -> 254 usable hosts × 1 port
    assert 250 <= len(out) <= 254
    assert all(p == 443 for _, p in out)


def test_expand_targets_stable_dedup():
    cfg = _Cfg(targets=_Targets(include_ips=["1.1.1.1", "2.2.2.2", "1.1.1.1", "3.3.3.3"]))
    out = target_expander.expand_targets(cfg)
    ips_in_order = [ip for ip, _ in out]
    assert ips_in_order == ["1.1.1.1", "2.2.2.2", "3.3.3.3"]


def test_expand_targets_normalizes_ip_types():
    cfg = _Cfg(targets=_Targets(
        include_ips=["1.1.1.1"],
        exclude_ips=[ipaddress.IPv4Address("1.1.1.1")],
    ))
    out = target_expander.expand_targets(cfg)
    assert all(ip != "1.1.1.1" for ip, _ in out)


def test_expand_targets_at_22_boundary_allowed():
    # /22 is exactly 1024 addresses; cap is `> 1024` so /22 must pass.
    cfg = _Cfg(targets=_Targets(cidrs=["10.0.0.0/22"]))
    out = target_expander.expand_targets(cfg)
    # /22 -> 1022 usable hosts
    assert 1000 <= len(out) <= 1022


# ---------------------------------------------------------------------------
# AUDIT-TASKS ledger flip verification
# ---------------------------------------------------------------------------

def test_audit_rows_flipped_to_phase_71():
    import pathlib
    import re
    root = pathlib.Path(__file__).resolve().parent.parent
    audit = (root / ".planning/audit-2026-05-08/AUDIT-TASKS.md").read_text(encoding="utf-8")
    for wr in ("WR-11", "WR-12", "WR-13", "WR-14"):
        pattern = rf"scanners-protocol/{wr}.*Phase 71.*\[x\] closed"
        assert re.search(pattern, audit), f"AUDIT-TASKS row for {wr} not flipped"
