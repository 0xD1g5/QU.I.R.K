"""RED scaffold for HWCOMPAT-05 CBOM Pass 4 FIRMWARE component emission.

This file is intentionally RED and will fail until ``build_cbom()`` is
extended in Plan 129-02 to accept the ``hw_devices`` keyword argument and
emit ``ComponentType.FIRMWARE`` components.  Do NOT attempt to fix these
failures at the scaffold stage — the ImportError (or TypeError) is the
correct outcome.
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
) -> dict:
    d = {
        "host": host,
        "port": 22,
        "vendor": "Cisco",
        "model": "ASA-5506",
        "pqc_status": pqc_status,
        "remediation_tier": "Tier 1",
        "confidence": "high",
    }
    if bridge_status is not None:
        d["bridge_status"] = bridge_status
    return d


# ---------------------------------------------------------------------------
# Test functions
# ---------------------------------------------------------------------------


def test_pass4_emits_firmware_component():
    """HWCOMPAT-05: build_cbom with hw_devices must emit ComponentType.FIRMWARE component."""
    bom = build_cbom([], hw_devices=[_hw_dict()])
    assert any(c.type == ComponentType.FIRMWARE for c in bom.components)


def test_firmware_properties_present():
    """HWCOMPAT-05: FIRMWARE component must carry quirk:hw-vendor, quirk:hw-pqc-supported, quirk:hw-remediation-tier properties."""
    bom = build_cbom([], hw_devices=[_hw_dict()])
    fw_comp = next(
        (c for c in bom.components if c.bom_ref == "hw/192.168.1.22:22"), None
    )
    assert fw_comp is not None
    prop_names = {p.name for p in fw_comp.properties}
    assert "quirk:hw-vendor" in prop_names
    assert "quirk:hw-pqc-supported" in prop_names
    assert "quirk:hw-remediation-tier" in prop_names


def test_firmware_schema_validates():
    """HWCOMPAT-05: CBOM with FIRMWARE hardware components must pass CycloneDX 1.6 JSON schema validation."""
    from cyclonedx.output.json import JsonV1Dot6

    bom = build_cbom([], hw_devices=[_hw_dict(bridge_status="partial_only")])
    json_str = JsonV1Dot6(bom).output_as_string()
    json_v = JsonStrictValidator(SchemaVersion.V1_6)
    j_err = json_v.validate_str(json_str)
    assert j_err is None


def test_no_hw_backward_compat():
    """HWCOMPAT-05: build_cbom() with no hw_devices kwarg must produce zero FIRMWARE components (backward compat)."""
    bom = build_cbom([])
    assert not any(c.type == ComponentType.FIRMWARE for c in bom.components)
