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
class _Connectors:
    enable_modbus: bool = False


@dataclass
class _Cfg:
    targets: _Targets = field(default_factory=_Targets)
    scan: _Scan = field(default_factory=_Scan)
    connectors: _Connectors = field(default_factory=_Connectors)


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
# Phase 141 OTICS-01/D-04: 502 (Modbus/TCP) port injection
# ---------------------------------------------------------------------------

def test_expand_targets_injects_502_when_modbus_enabled():
    """Regression test: hardware_scanner.py Step 4 gates Modbus fingerprinting
    on `_port == 502`, but the run_scan.py 502-injection only wired into the
    optional nmap-discovery path. expand_targets() is the port list actually
    used whenever nmap discovery is skipped (the default, config.yaml-driven
    scan mode) — without this injection, no candidate at port 502 is ever
    generated, so Modbus fingerprinting silently never activates in that mode.
    Confirmed live against the otics-modbus chaos-lab simulator.
    """
    cfg = _Cfg(
        targets=_Targets(include_ips=["127.0.0.1"]),
        connectors=_Connectors(enable_modbus=True),
    )
    out = target_expander.expand_targets(cfg)
    assert ("127.0.0.1", 502) in out


def test_expand_targets_omits_502_when_modbus_disabled():
    """502 must NOT be injected when enable_modbus is False (default) — no
    unsolicited OT/ICS port probing without explicit opt-in (OTICS-01)."""
    cfg = _Cfg(targets=_Targets(include_ips=["127.0.0.1"]))
    out = target_expander.expand_targets(cfg)
    assert ("127.0.0.1", 502) not in out


def test_expand_targets_no_duplicate_502_already_in_ports_tls():
    """If 502 is already in ports_tls, injection must not create a duplicate
    (target_expander's stable dedup wouldn't catch a double-append here since
    the append happens before the per-host expansion, not after)."""
    cfg = _Cfg(
        targets=_Targets(include_ips=["127.0.0.1"]),
        scan=_Scan(ports_tls=[443, 502]),
        connectors=_Connectors(enable_modbus=True),
    )
    out = target_expander.expand_targets(cfg)
    assert out.count(("127.0.0.1", 502)) == 1


# ---------------------------------------------------------------------------
# Phase 144 / D-01/D-03/D-06: _chunked() + _expand_and_dedup_hosts() helpers
# ---------------------------------------------------------------------------

def test_chunked_empty_iterable_yields_nothing():
    assert list(target_expander._chunked(range(0), 1024)) == []


def test_chunked_yields_correct_batch_sizes():
    batches = list(target_expander._chunked(range(2050), 1024))
    assert [len(b) for b in batches] == [1024, 1024, 2]


def test_chunked_final_batch_may_be_shorter():
    batches = list(target_expander._chunked(range(5), 2))
    assert batches == [[0, 1], [2, 3], [4]]


def test_expand_and_dedup_hosts_small_cidr_ascending_no_dupes():
    out = list(target_expander._expand_and_dedup_hosts(["192.168.1.0/30"]))
    # /30 -> 2 usable hosts: .1, .2
    assert out == ["192.168.1.1", "192.168.1.2"]
    assert len(out) == len(set(out))


def test_expand_and_dedup_hosts_fqdn_and_bare_ip_passthrough():
    out = list(target_expander._expand_and_dedup_hosts(["example.com", "192.168.1.5"]))
    assert out == ["example.com", "192.168.1.5"]


def test_expand_and_dedup_hosts_cidr_and_explicit_ip_overlap_deduped():
    out = list(target_expander._expand_and_dedup_hosts(["192.168.1.0/30", "192.168.1.1"]))
    assert out.count("192.168.1.1") == 1


def test_expand_and_dedup_hosts_exclude_ips_omitted():
    out = list(target_expander._expand_and_dedup_hosts(
        ["192.168.1.0/30"], exclude_ips=["192.168.1.1"]
    ))
    assert "192.168.1.1" not in out
    assert "192.168.1.2" in out


def test_expand_and_dedup_hosts_yields_flat_host_strings_not_tuples():
    out = list(target_expander._expand_and_dedup_hosts(["192.168.1.0/29"]))
    assert all(isinstance(h, str) for h in out)


def test_expand_and_dedup_hosts_never_materializes_full_hosts_list():
    src = inspect.getsource(target_expander)
    assert "list(net.hosts())" not in src


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
