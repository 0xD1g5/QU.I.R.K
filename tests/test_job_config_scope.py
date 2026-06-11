"""
Tests for Phase 121-01 — _write_job_config scope translation (PORT-05).

Covers:
- 'common' scope writes CONSULTING_TLS_PORTS (17 ports), no nmap_port_scope key
- 'top1000' scope writes nmap_port_scope='top1000'
- 'all' scope writes nmap_port_scope='all'
- 'custom' scope writes parse_port_spec of the custom string as ports_tls
"""
from __future__ import annotations

import yaml
import pytest
from pathlib import Path

from quirk.dashboard.api.routes.jobs import _write_job_config


def _load_cfg(path: str) -> dict:
    with open(path) as fh:
        return yaml.safe_load(fh)


def test_write_job_config_common_scope(tmp_path: Path) -> None:
    """'common' scope: ports_tls has 17 entries including 443; no nmap_port_scope (PORT-05)."""
    cfg_path = _write_job_config(
        tmp_path, "example.com", "/tmp/q.db", "balanced",
        allow_internal_targets=False, port_scope="common",
    )
    cfg = _load_cfg(cfg_path)
    assert 443 in cfg["scan"]["ports_tls"]
    assert len(cfg["scan"]["ports_tls"]) == 17
    assert "nmap_port_scope" not in cfg["scan"]


def test_write_job_config_top1000_scope(tmp_path: Path) -> None:
    """'top1000' scope: nmap_port_scope key is 'top1000' (PORT-05)."""
    cfg_path = _write_job_config(
        tmp_path, "example.com", "/tmp/q.db", "balanced",
        allow_internal_targets=False, port_scope="top1000",
    )
    cfg = _load_cfg(cfg_path)
    assert cfg["scan"]["nmap_port_scope"] == "top1000"


def test_write_job_config_all_scope(tmp_path: Path) -> None:
    """'all' scope: nmap_port_scope key is 'all' (PORT-05)."""
    cfg_path = _write_job_config(
        tmp_path, "example.com", "/tmp/q.db", "balanced",
        allow_internal_targets=False, port_scope="all",
    )
    cfg = _load_cfg(cfg_path)
    assert cfg["scan"]["nmap_port_scope"] == "all"


def test_write_job_config_custom_scope(tmp_path: Path) -> None:
    """'custom' scope: ports_tls equals parse_port_spec of custom string (PORT-05)."""
    cfg_path = _write_job_config(
        tmp_path, "example.com", "/tmp/q.db", "balanced",
        allow_internal_targets=False,
        port_scope="custom", custom_ports="443,8443",
    )
    cfg = _load_cfg(cfg_path)
    assert cfg["scan"]["ports_tls"] == [443, 8443]
    assert "nmap_port_scope" not in cfg["scan"]
