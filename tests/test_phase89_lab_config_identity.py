"""Phase 89 LAB-06 / D-04: Verify config.yaml exposes identity connector keys.

These are non-slow, pure-config tests — no network, no Docker required.
They assert that the top-level config.yaml (the EXISTING scan config, per D-04)
contains the Kerberos / SAML / DNSSEC connector keys in their enabled state and
that the target lists + resolver override are present.

The identity evidence chain is already wired in evidence.py and scoring.py
(BACK-78 / Phase 89 RESEARCH); this test confirms the scan config is complete
so the human-verify checkpoint can confirm non-zero evidence counters against
the live lab profiles.
"""

import os
import pathlib

import pytest
import yaml


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

CONFIG_PATH = pathlib.Path(__file__).parent.parent / "config.yaml"


def _load_config() -> dict:
    """Load config.yaml and return the top-level dict."""
    if not CONFIG_PATH.exists():
        pytest.fail(f"config.yaml not found at expected path: {CONFIG_PATH}")
    with CONFIG_PATH.open() as fh:
        return yaml.safe_load(fh)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_config_yaml_has_connectors_block():
    """config.yaml must have a 'connectors:' top-level key."""
    cfg = _load_config()
    assert "connectors" in cfg, (
        "config.yaml is missing the 'connectors:' block — identity connector "
        "keys cannot be present without it"
    )


def test_enable_kerberos_true():
    """config.yaml connectors.enable_kerberos must be set to True (D-04 / LAB-06)."""
    cfg = _load_config()
    connectors = cfg.get("connectors", {})
    assert connectors.get("enable_kerberos") is True, (
        "config.yaml connectors.enable_kerberos must be True to exercise the "
        "identity evidence chain against the lab kerberos profile"
    )


def test_kerberos_targets_present_and_non_empty():
    """config.yaml connectors.kerberos_targets must be a non-empty list."""
    cfg = _load_config()
    connectors = cfg.get("connectors", {})
    targets = connectors.get("kerberos_targets", [])
    assert isinstance(targets, list) and len(targets) > 0, (
        "config.yaml connectors.kerberos_targets must be a non-empty list "
        "(e.g. ['127.0.0.1'] for the lab samba-dc)"
    )


def test_enable_saml_true():
    """config.yaml connectors.enable_saml must be set to True (D-04 / LAB-06)."""
    cfg = _load_config()
    connectors = cfg.get("connectors", {})
    assert connectors.get("enable_saml") is True, (
        "config.yaml connectors.enable_saml must be True to exercise the "
        "identity evidence chain against the lab saml profile"
    )


def test_saml_targets_present_and_non_empty():
    """config.yaml connectors.saml_targets must be a non-empty list."""
    cfg = _load_config()
    connectors = cfg.get("connectors", {})
    targets = connectors.get("saml_targets", [])
    assert isinstance(targets, list) and len(targets) > 0, (
        "config.yaml connectors.saml_targets must be a non-empty list "
        "(e.g. ['http://localhost:8080/simplesaml/saml2/idp/metadata.php'])"
    )


def test_enable_dnssec_true():
    """config.yaml connectors.enable_dnssec must be set to True (D-04 / LAB-06)."""
    cfg = _load_config()
    connectors = cfg.get("connectors", {})
    assert connectors.get("enable_dnssec") is True, (
        "config.yaml connectors.enable_dnssec must be True to exercise the "
        "identity evidence chain against the lab dnssec profile"
    )


def test_dnssec_targets_present_and_non_empty():
    """config.yaml connectors.dnssec_targets must be a non-empty list."""
    cfg = _load_config()
    connectors = cfg.get("connectors", {})
    targets = connectors.get("dnssec_targets", [])
    assert isinstance(targets, list) and len(targets) > 0, (
        "config.yaml connectors.dnssec_targets must be a non-empty list "
        "(e.g. ['weak.example.com', 'unsigned.example.com'])"
    )


def test_dnssec_resolver_present_and_contains_15353():
    """config.yaml connectors.dnssec_resolver must be set and point to port 15353.

    The lab's bind9-dnssec listens on 127.0.0.1:15353.  Without this key, the
    scanner uses the system resolver (port 53) and cannot reach the lab zone.
    """
    cfg = _load_config()
    connectors = cfg.get("connectors", {})
    resolver = connectors.get("dnssec_resolver", "")
    assert resolver, (
        "config.yaml connectors.dnssec_resolver is missing — set it to "
        "'127.0.0.1:15353' so the DNSSEC scanner reaches the lab bind9"
    )
    assert "15353" in str(resolver), (
        f"config.yaml connectors.dnssec_resolver is '{resolver}' — expected it "
        "to target port 15353 (the lab bind9-dnssec listener)"
    )


def test_dnssec_scanner_accepts_resolver_kwarg():
    """scan_dnssec_targets must accept a 'resolver' keyword argument (Phase 89 port override)."""
    import inspect
    from quirk.scanner.dnssec_scanner import scan_dnssec_targets

    sig = inspect.signature(scan_dnssec_targets)
    assert "resolver" in sig.parameters, (
        "scan_dnssec_targets does not accept a 'resolver' keyword argument — "
        "the port-override capability required by Phase 89 LAB-06 is missing"
    )


def test_dnssec_scanner_parse_resolver_port():
    """_parse_resolver must correctly extract host and port from a host:port string."""
    from quirk.scanner.dnssec_scanner import _parse_resolver

    host, port = _parse_resolver("127.0.0.1:15353")
    assert host == "127.0.0.1", f"Expected host '127.0.0.1', got '{host}'"
    assert port == 15353, f"Expected port 15353, got {port}"


def test_dnssec_scanner_parse_resolver_default():
    """_parse_resolver must return (None, 53) when no resolver is specified."""
    from quirk.scanner.dnssec_scanner import _parse_resolver

    host, port = _parse_resolver(None)
    assert host is None, f"Expected None host for None resolver, got '{host}'"
    assert port == 53, f"Expected port 53 as default, got {port}"


def test_connectors_cfg_accepts_dnssec_resolver():
    """ConnectorsCfg dataclass must accept dnssec_resolver as an Optional[str] field."""
    from quirk.config import ConnectorsCfg

    cfg = ConnectorsCfg(
        enable_dnssec=True,
        dnssec_targets=["weak.example.com"],
        dnssec_resolver="127.0.0.1:15353",
    )
    assert cfg.dnssec_resolver == "127.0.0.1:15353", (
        "ConnectorsCfg.dnssec_resolver did not store the expected value"
    )


def test_connectors_cfg_dnssec_resolver_defaults_none():
    """ConnectorsCfg.dnssec_resolver must default to None (backwards-compatible)."""
    from quirk.config import ConnectorsCfg

    cfg = ConnectorsCfg()
    assert cfg.dnssec_resolver is None, (
        "ConnectorsCfg.dnssec_resolver must default to None so existing "
        "configs without the key continue to use the system resolver"
    )
