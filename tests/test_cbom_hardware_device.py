"""Phase 141 Plan 05 (OTICS-05) — CBOM FIRMWARE modbus/bacnet property tests.

Confirms the CBOM builder's FIRMWARE child emits quirk:hw-modbus-*/hw-bacnet-*
properties for hw_devices dicts carrying modbus_*/bacnet_* fields, mirroring
the existing quirk:hw-snmp-* conditional-emit pattern (Phase 139).

Run selectively via: pytest tests/test_cbom_hardware_device.py -k modbus_or_bacnet
"""
from __future__ import annotations

from cyclonedx.model.component import ComponentType

from quirk.cbom.builder import build_cbom


def _hw_dict(
    host: str = "10.0.5.9",
    vendor: str = "Schneider Electric",
    model: str = "M221",
    modbus_vendor=None,
    modbus_model=None,
    modbus_firmware=None,
    bacnet_vendor=None,
    bacnet_model=None,
    bacnet_firmware=None,
) -> dict:
    d = {
        "host": host,
        "port": 502,
        "vendor": vendor,
        "model": model,
        "pqc_status": "unsupported",
        "remediation_tier": "Tier 1",
        "confidence": "high",
    }
    if modbus_vendor is not None:
        d["modbus_vendor"] = modbus_vendor
    if modbus_model is not None:
        d["modbus_model"] = modbus_model
    if modbus_firmware is not None:
        d["modbus_firmware"] = modbus_firmware
    if bacnet_vendor is not None:
        d["bacnet_vendor"] = bacnet_vendor
    if bacnet_model is not None:
        d["bacnet_model"] = bacnet_model
    if bacnet_firmware is not None:
        d["bacnet_firmware"] = bacnet_firmware
    return d


def _firmware_child(bom):
    device = next((c for c in bom.components if c.type == ComponentType.DEVICE), None)
    assert device is not None, "No DEVICE component found in bom.components"
    fw = next(
        (child for child in device.components if child.type == ComponentType.FIRMWARE),
        None,
    )
    assert fw is not None, "No FIRMWARE child found in DEVICE.components"
    return fw, device


def test_cbom_firmware_emits_modbus_or_bacnet_props():
    """OTICS-05: hw_devices dict with modbus_*/bacnet_* fields produces a
    FIRMWARE component whose properties include quirk:hw-modbus-vendor/model/
    firmware and quirk:hw-bacnet-vendor/model/firmware, with the DEVICE/
    FIRMWARE hierarchy containing the device."""
    dev = _hw_dict(
        modbus_vendor="Schneider Electric",
        modbus_model="M221",
        modbus_firmware="1.6",
        bacnet_vendor="Honeywell",
        bacnet_model="XL Web II",
        bacnet_firmware="2.0",
    )
    bom = build_cbom([], hw_devices=[dev])

    fw, device = _firmware_child(bom)
    assert str(device.bom_ref) == "hw/device/10.0.5.9:502"
    prop_by_name = {p.name: p.value for p in fw.properties}

    assert prop_by_name.get("quirk:hw-modbus-vendor") == "Schneider Electric"
    assert prop_by_name.get("quirk:hw-modbus-model") == "M221"
    assert prop_by_name.get("quirk:hw-modbus-firmware") == "1.6"
    assert prop_by_name.get("quirk:hw-bacnet-vendor") == "Honeywell"
    assert prop_by_name.get("quirk:hw-bacnet-model") == "XL Web II"
    assert prop_by_name.get("quirk:hw-bacnet-firmware") == "2.0"


def test_cbom_firmware_omits_modbus_or_bacnet_props_when_absent():
    """When a device has no modbus_*/bacnet_* fields (e.g. SSH/HTTP/SNMP-only
    fingerprint), no quirk:hw-modbus-*/hw-bacnet-* properties are emitted."""
    dev = _hw_dict()
    bom = build_cbom([], hw_devices=[dev])

    fw, _ = _firmware_child(bom)
    prop_names = {p.name for p in fw.properties}
    for name in (
        "quirk:hw-modbus-vendor",
        "quirk:hw-modbus-model",
        "quirk:hw-modbus-firmware",
        "quirk:hw-bacnet-vendor",
        "quirk:hw-bacnet-model",
        "quirk:hw-bacnet-firmware",
    ):
        assert name not in prop_names
