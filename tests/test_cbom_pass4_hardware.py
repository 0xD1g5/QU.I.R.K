"""Tests for CBOM Pass 4 DEVICE parent + FIRMWARE child hierarchy.

Phase 134 (CBOM-01): hardware endpoints emit a top-level ComponentType.DEVICE
containing one nested ComponentType.FIRMWARE child via Component.components.
The DEVICE carries only quirk:hw-tier; FIRMWARE carries all quirk:hw-* props.
"""
from __future__ import annotations

import json

from cyclonedx.schema import SchemaVersion
from cyclonedx.validation.json import JsonStrictValidator
from cyclonedx.model.component import ComponentType

from quirk.cbom.builder import build_cbom
from quirk.cbom import write_cbom_files


# ---------------------------------------------------------------------------
# Helper fixture
# ---------------------------------------------------------------------------


def _hw_dict(
    host: str = "192.168.1.22",
    pqc_status: str = "unsupported",
    bridge_status=None,
    snmp_sysdescr=None,
    snmp_sysobjectid=None,
    vendor: str = "Cisco",
    model: str = "ASA-5506",
) -> dict:
    d = {
        "host": host,
        "port": 22,
        "vendor": vendor,
        "model": model,
        "pqc_status": pqc_status,
        "remediation_tier": "Tier 1",
        "confidence": "high",
    }
    if bridge_status is not None:
        d["bridge_status"] = bridge_status
    if snmp_sysdescr is not None:
        d["snmp_sysdescr"] = snmp_sysdescr
    if snmp_sysobjectid is not None:
        d["snmp_sysobjectid"] = snmp_sysobjectid
    return d


def _firmware_child(bom):
    """Return the first nested FIRMWARE component from the first DEVICE in bom."""
    device = next(
        (c for c in bom.components if c.type == ComponentType.DEVICE), None
    )
    assert device is not None, "No DEVICE component found in bom.components"
    fw = next(
        (child for child in device.components if child.type == ComponentType.FIRMWARE),
        None,
    )
    assert fw is not None, "No FIRMWARE child found in DEVICE.components"
    return fw


# ---------------------------------------------------------------------------
# Test functions
# ---------------------------------------------------------------------------


def test_pass4_emits_firmware_component():
    """CBOM-01: build_cbom with hw_devices emits top-level DEVICE containing nested FIRMWARE."""
    bom = build_cbom([], hw_devices=[_hw_dict()])
    # Top-level must have a DEVICE component
    assert any(c.type == ComponentType.DEVICE for c in bom.components)
    # No top-level FIRMWARE — it is nested inside DEVICE
    assert not any(c.type == ComponentType.FIRMWARE for c in bom.components)
    # The DEVICE has the expected bom_ref
    device = next(
        (c for c in bom.components if str(c.bom_ref) == "hw/device/192.168.1.22:22"),
        None,
    )
    assert device is not None, "Expected DEVICE bom_ref hw/device/192.168.1.22:22 not found"
    # DEVICE contains exactly one FIRMWARE child via .components
    assert any(child.type == ComponentType.FIRMWARE for child in device.components)


def test_device_name_vendor_model():
    """CBOM-01/D-05: DEVICE name = 'Vendor Model' for known vendor/model."""
    bom = build_cbom([], hw_devices=[_hw_dict()])
    device = next(c for c in bom.components if c.type == ComponentType.DEVICE)
    assert device.name == "Cisco ASA-5506"


def test_device_name_unknown_fallback():
    """CBOM-01/D-05: DEVICE name falls back to 'Unknown Device at host:port' when both Unknown."""
    bom = build_cbom([], hw_devices=[_hw_dict(vendor="Unknown", model="Unknown")])
    device = next(c for c in bom.components if c.type == ComponentType.DEVICE)
    assert device.name == "Unknown Device at 192.168.1.22:22"


def test_firmware_properties_present():
    """CBOM-01: FIRMWARE child carries quirk:hw-vendor, quirk:hw-pqc-supported, quirk:hw-remediation-tier.
    DEVICE carries only quirk:hw-tier, NOT quirk:hw-vendor."""
    bom = build_cbom([], hw_devices=[_hw_dict()])
    # Locate DEVICE by bom_ref
    device = next(
        (c for c in bom.components if str(c.bom_ref) == "hw/device/192.168.1.22:22"),
        None,
    )
    assert device is not None, "DEVICE bom_ref hw/device/192.168.1.22:22 not found"
    # Locate FIRMWARE child nested inside DEVICE
    fw_child = next(
        (ch for ch in device.components if ch.type == ComponentType.FIRMWARE), None
    )
    assert fw_child is not None, "No FIRMWARE child nested in DEVICE.components"
    assert str(fw_child.bom_ref) == "hw/firmware/192.168.1.22:22"
    child_prop_names = {p.name for p in fw_child.properties}
    assert "quirk:hw-vendor" in child_prop_names
    assert "quirk:hw-pqc-supported" in child_prop_names
    assert "quirk:hw-remediation-tier" in child_prop_names
    # DEVICE itself carries only quirk:hw-tier — not quirk:hw-vendor
    device_prop_names = {p.name for p in device.properties}
    assert "quirk:hw-tier" in device_prop_names
    assert "quirk:hw-vendor" not in device_prop_names


def test_firmware_schema_validates():
    """CBOM-01: CBOM with nested DEVICE+FIRMWARE passes CycloneDX 1.6 JSON schema validation."""
    from cyclonedx.output.json import JsonV1Dot6

    bom = build_cbom([], hw_devices=[_hw_dict(bridge_status="partial_only")])
    json_str = JsonV1Dot6(bom).output_as_string()
    json_v = JsonStrictValidator(SchemaVersion.V1_6)
    j_err = json_v.validate_str(json_str)
    assert j_err is None


def test_no_hw_backward_compat():
    """CBOM-01: build_cbom() with no hw_devices kwarg must produce zero DEVICE and zero FIRMWARE."""
    bom = build_cbom([])
    assert not any(c.type == ComponentType.DEVICE for c in bom.components)
    assert not any(c.type == ComponentType.FIRMWARE for c in bom.components)


def test_bridge_status_property_emitted():
    """CBOM-01: bridge_status='partial_only' → quirk:hw-bridge-status on FIRMWARE child."""
    bom = build_cbom([], hw_devices=[_hw_dict(bridge_status="partial_only")])
    fw_comp = _firmware_child(bom)
    prop_names = {p.name for p in fw_comp.properties}
    assert "quirk:hw-bridge-status" in prop_names
    bridge_val = next(
        p.value for p in fw_comp.properties if p.name == "quirk:hw-bridge-status"
    )
    assert bridge_val == "partial_only"


def test_no_bridge_status_property_when_none():
    """CBOM-01: bridge_status absent → quirk:hw-bridge-status NOT on FIRMWARE child."""
    bom = build_cbom([], hw_devices=[_hw_dict(bridge_status=None)])
    fw_comp = _firmware_child(bom)
    prop_names = {p.name for p in fw_comp.properties}
    assert "quirk:hw-bridge-status" not in prop_names


def test_snmp_oid_on_firmware_child():
    """CBOM-01: snmp_sysdescr present → quirk:hw-snmp-oid on FIRMWARE child (not DEVICE)."""
    bom = build_cbom([], hw_devices=[_hw_dict(
        snmp_sysdescr="Cisco IOS Software, Version 15.2",
        snmp_sysobjectid="1.3.6.1.4.1.9.1.1",
    )])
    fw_comp = _firmware_child(bom)
    prop_names = {p.name for p in fw_comp.properties}
    assert "quirk:hw-snmp-oid" in prop_names
    oid_val = next(p.value for p in fw_comp.properties if p.name == "quirk:hw-snmp-oid")
    assert oid_val == "1.3.6.1.4.1.9.1.1"
    # DEVICE must NOT have snmp-oid
    device = next(c for c in bom.components if c.type == ComponentType.DEVICE)
    device_prop_names = {p.name for p in device.properties}
    assert "quirk:hw-snmp-oid" not in device_prop_names
