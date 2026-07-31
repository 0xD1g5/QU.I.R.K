"""Phase 141 Plan 04 — OTICS-01/02/05 fingerprint waterfall gating contract.

Verifies that Modbus (Step 4) and BACnet (Step 5) probes in
``fingerprint_one`` are independently flag-gated (D-01/D-02), that Modbus
additionally requires port-502 evidence (D-04), that BACnet's Who-Is/I-Am is
its own gate (no prior port evidence needed), that Modbus wins the headline
vendor/model over BACnet when both identify a device (first-match-wins,
D-03), and that neither step is nested under a vendor=="Unknown" gate
(D-01 — OT trigger is port/flag-based, not vendor-Unknown-based).

No network connections are made — probe_modbus_target/probe_bacnet_target
are patched at their import site inside quirk.scanner.hardware_scanner.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch


def _make_ep(host: str, port: int, service_detail: str | None = None):
    """Create a CryptoEndpoint fixture without DB/ORM setup."""
    from quirk.models import CryptoEndpoint

    ep = CryptoEndpoint.__new__(CryptoEndpoint)
    ep.__dict__["host"] = host
    ep.__dict__["port"] = port
    ep.__dict__["protocol"] = "TCP"
    ep.__dict__["service_detail"] = service_detail
    return ep


def _make_cfg(enable_modbus: bool = False, enable_bacnet: bool = False):
    connectors = SimpleNamespace(
        enable_modbus=enable_modbus,
        enable_bacnet=enable_bacnet,
        snmp_v3_credentials={},
    )
    return SimpleNamespace(connectors=connectors)


# ------------ Modbus gated off by default (D-02) ------------

def test_modbus_gated_off_by_default() -> None:
    from quirk.scanner.hardware_scanner import fingerprint_one

    ep = _make_ep("10.0.0.10", 502)
    cfg = _make_cfg(enable_modbus=False)

    with patch(
        "quirk.scanner.modbus_scanner.probe_modbus_target"
    ) as mock_probe:
        device = fingerprint_one(ep, timeout=1, cfg=cfg)

    mock_probe.assert_not_called()
    assert device.modbus_probe_state is None


# ------------ Modbus requires port-502 evidence (D-04) ------------

def test_modbus_requires_open_port() -> None:
    from quirk.scanner.hardware_scanner import fingerprint_one

    cfg = _make_cfg(enable_modbus=True)

    # Non-502 endpoint: flag on, but no 502 port evidence -> not called
    ep_other = _make_ep("10.0.0.11", 22)
    with patch(
        "quirk.scanner.modbus_scanner.probe_modbus_target"
    ) as mock_probe:
        device_other = fingerprint_one(ep_other, timeout=1, cfg=cfg)
    mock_probe.assert_not_called()
    assert device_other.modbus_probe_state is None

    # 502 endpoint: flag on + port evidence -> called, fields populated
    ep_502 = _make_ep("10.0.0.12", 502)
    with patch(
        "quirk.scanner.modbus_scanner.probe_modbus_target"
    ) as mock_probe:
        mock_probe.return_value = {
            "modbus_vendor": "Schneider Electric",
            "modbus_model": "M221",
            "modbus_firmware": "1.6",
            "modbus_probe_state": "identified",
        }
        device_502 = fingerprint_one(ep_502, timeout=1, cfg=cfg)

    mock_probe.assert_called_once()
    assert device_502.modbus_vendor == "Schneider Electric"
    assert device_502.modbus_model == "M221"
    assert device_502.modbus_probe_state == "identified"


# ------------ BACnet gated by flag only (Who-Is is its own gate) ------------

def test_bacnet_gated_by_flag_only() -> None:
    from quirk.scanner.hardware_scanner import fingerprint_one

    ep = _make_ep("10.0.0.20", 80)

    cfg_on = _make_cfg(enable_bacnet=True)
    with patch(
        "quirk.scanner.bacnet_scanner.probe_bacnet_target"
    ) as mock_probe:
        mock_probe.return_value = {
            "bacnet_vendor": "999",
            "bacnet_model": "BACnet Controller X",
            "bacnet_firmware": "2.3",
            "bacnet_probe_state": "identified",
        }
        device_on = fingerprint_one(ep, timeout=1, cfg=cfg_on)
    mock_probe.assert_called_once()
    assert device_on.bacnet_vendor == "999"

    cfg_off = _make_cfg(enable_bacnet=False)
    ep2 = _make_ep("10.0.0.21", 80)
    with patch(
        "quirk.scanner.bacnet_scanner.probe_bacnet_target"
    ) as mock_probe:
        device_off = fingerprint_one(ep2, timeout=1, cfg=cfg_off)
    mock_probe.assert_not_called()
    assert device_off.bacnet_probe_state is None


# ------------ First-match-wins headline: Modbus before BACnet (D-03) ------------

def test_first_match_wins_headline() -> None:
    from quirk.scanner.hardware_scanner import fingerprint_one

    ep = _make_ep("10.0.0.30", 502)
    cfg = _make_cfg(enable_modbus=True, enable_bacnet=True)

    with patch(
        "quirk.scanner.modbus_scanner.probe_modbus_target"
    ) as mock_modbus, patch(
        "quirk.scanner.bacnet_scanner.probe_bacnet_target"
    ) as mock_bacnet:
        mock_modbus.return_value = {
            "modbus_vendor": "Schneider Electric",
            "modbus_model": "M221",
            "modbus_firmware": "1.6",
            "modbus_probe_state": "identified",
        }
        mock_bacnet.return_value = {
            "bacnet_vendor": "999",
            "bacnet_model": "BACnet Controller X",
            "bacnet_firmware": "2.3",
            "bacnet_probe_state": "identified",
        }
        device = fingerprint_one(ep, timeout=1, cfg=cfg)

    # Headline comes from Modbus (runs first)
    assert device.vendor == "Schneider Electric"
    assert device.model == "M221"
    assert device.fingerprint_method == "modbus"

    # Both raw field sets are stored regardless
    assert device.modbus_vendor == "Schneider Electric"
    assert device.bacnet_vendor == "999"


# ------------ D-01: Steps 4/5 run even when vendor already known (not gated on Unknown) ------------

def test_step4_5_not_gated_on_unknown() -> None:
    from quirk.scanner.hardware_scanner import fingerprint_one

    # SSH banner identifies a known vendor in Step 1 (Cisco)
    ep = _make_ep("10.0.0.40", 502, service_detail="SSH-2.0-Cisco-1.25")
    cfg = _make_cfg(enable_modbus=True, enable_bacnet=True)

    with patch(
        "quirk.scanner.modbus_scanner.probe_modbus_target"
    ) as mock_modbus, patch(
        "quirk.scanner.bacnet_scanner.probe_bacnet_target"
    ) as mock_bacnet:
        mock_modbus.return_value = {
            "modbus_vendor": None,
            "modbus_model": None,
            "modbus_firmware": None,
            "modbus_probe_state": "no_response",
        }
        mock_bacnet.return_value = {
            "bacnet_vendor": None,
            "bacnet_model": None,
            "bacnet_firmware": None,
            "bacnet_probe_state": "no_response",
        }
        device = fingerprint_one(ep, timeout=1, cfg=cfg)

    # Step 1 already found a known vendor; Steps 4/5 must still run (D-01)
    assert device.vendor == "Cisco"
    mock_modbus.assert_called_once()
    mock_bacnet.assert_called_once()
    # Headline stays Cisco (Modbus/BACnet returned no identification here)
    assert device.modbus_probe_state == "no_response"
    assert device.bacnet_probe_state == "no_response"
