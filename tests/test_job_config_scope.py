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


def test_custom_scope_disables_fixed_port_connectors(tmp_path: Path) -> None:
    """'custom' scope writes an explicit connectors block disabling email/broker.

    A custom port spec means "scan exactly these ports"; the email/broker
    connectors carry their own fixed service-port tables that the standard/deep
    profiles auto-enable independently of ports_tls, so without this they leak
    ~7 email ports the user never selected (Phase 121 live-UAT, UAT-121-05).
    """
    cfg_path = _write_job_config(
        tmp_path, "127.0.0.1", "/tmp/q.db", "balanced",
        allow_internal_targets=True,
        port_scope="custom", custom_ports="15449,16443",
    )
    cfg = _load_cfg(cfg_path)
    assert cfg["connectors"] == {"enable_email": False, "enable_broker": False}


@pytest.mark.parametrize("scope,custom", [
    ("common", None),
    ("top1000", None),
    ("all", None),
])
def test_non_custom_scopes_omit_connectors_block(tmp_path: Path, scope: str, custom) -> None:
    """Only custom scope suppresses connectors; common/top1000/all leave them to the profile.

    Common in particular MUST NOT disable connectors — CONSULTING_TLS_PORTS
    already curates in implicit-TLS email ports (993/995/465) by design.
    """
    cfg_path = _write_job_config(
        tmp_path, "example.com", "/tmp/q.db", "balanced",
        allow_internal_targets=False, port_scope=scope, custom_ports=custom,
    )
    cfg = _load_cfg(cfg_path)
    assert "connectors" not in cfg


def test_custom_connector_suppression_survives_deep_profile(tmp_path: Path) -> None:
    """The explicit False must survive apply_profile('deep') via _user_set_fields.

    This is the load-bearing guarantee (Phase 72 D-02/WR-11): the deep profile
    normally auto-enables email+broker, but an explicitly-set connectors value
    is recorded in ConnectorsCfg._user_set_fields and left untouched.
    """
    from quirk.config import config_from_dict
    from quirk.engine.profiles import apply_profile

    cfg_path = _write_job_config(
        tmp_path, "127.0.0.1", "/tmp/q.db", "balanced",
        allow_internal_targets=True,
        port_scope="custom", custom_ports="15449,16443",
    )
    cfg = config_from_dict(_load_cfg(cfg_path))
    apply_profile(cfg, "deep")
    assert cfg.connectors.enable_email is False
    assert cfg.connectors.enable_broker is False


def test_top1000_deep_profile_still_enables_email(tmp_path: Path) -> None:
    """Control: a non-custom scope leaves the deep profile free to enable email."""
    from quirk.config import config_from_dict
    from quirk.engine.profiles import apply_profile

    cfg_path = _write_job_config(
        tmp_path, "127.0.0.1", "/tmp/q.db", "balanced",
        allow_internal_targets=True, port_scope="top1000",
    )
    cfg = config_from_dict(_load_cfg(cfg_path))
    apply_profile(cfg, "deep")
    assert cfg.connectors.enable_email is True
