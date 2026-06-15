"""RED contract tests for Phase 133 SNMP fingerprinting.

These tests define the full acceptance contract for SNMP-01, SNMP-02, SNMP-03,
and SNMP-05. ALL tests FAIL against the pre-Phase-133 codebase because:

  - quirk.scanner.snmp_scanner does not exist yet
  - HardwareDevice has no snmp_* ORM columns
  - quirk.scanner.snmp_meta does not exist yet
  - CBOM builder does not emit quirk:hw-snmp-oid

Plans 01–04 must turn these tests GREEN. Do NOT add implementation here.

Marked tests:
  - test_install_all_excludes_pysnmp: @pytest.mark.slow (pip resolver round-trip)
"""
from __future__ import annotations

import importlib
import sys
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Contract 1 — snmp_scanner module surface (SNMP-01)
# ---------------------------------------------------------------------------

def test_snmp_scanner_module_exists() -> None:
    """quirk.scanner.snmp_scanner must export the three required callables."""
    import quirk.scanner.snmp_scanner as snmp_mod  # noqa: F401 — will fail until Plan 01

    assert callable(getattr(snmp_mod, "probe_snmp_target", None)), (
        "probe_snmp_target must be a callable in quirk.scanner.snmp_scanner"
    )
    assert callable(getattr(snmp_mod, "scan_snmp_targets", None)), (
        "scan_snmp_targets must be a callable in quirk.scanner.snmp_scanner"
    )
    assert callable(getattr(snmp_mod, "parse_sysdescr", None)), (
        "parse_sysdescr must be a callable in quirk.scanner.snmp_scanner"
    )


def test_probe_snmp_target_returns_dict() -> None:
    """probe_snmp_target('127.0.0.1', 'public', 1) must return a dict with SNMP keys.

    The host 127.0.0.1 has no SNMP agent in test context — result values may
    all be None, but the dict must be returned without raising.
    """
    from quirk.scanner.snmp_scanner import probe_snmp_target  # noqa — will fail until Plan 01

    result = probe_snmp_target("127.0.0.1", "public", 1)

    assert isinstance(result, dict), (
        f"probe_snmp_target must return a dict, got {type(result)}"
    )
    for key in ("snmp_sysdescr", "snmp_sysname", "snmp_sysobjectid"):
        assert key in result, (
            f"Result dict is missing required key '{key}'. Got keys: {sorted(result)}"
        )


def test_advisory_import_guard() -> None:
    """When pysnmp is NOT installed, probe_snmp_target must return a dict with all-None values.

    This implements the D-03 advisory import guard: operators without [hw]
    extras installed must never see ImportError at scan runtime.
    """
    # Simulate pysnmp being absent by patching it out of sys.modules
    # and making the import raise ImportError.
    saved = sys.modules.copy()

    # Force pysnmp to appear uninstalled during the probe call
    sys.modules["pysnmp"] = None  # type: ignore[assignment]
    sys.modules["pysnmp.hlapi"] = None  # type: ignore[assignment]
    sys.modules["pysnmp.hlapi.asyncio"] = None  # type: ignore[assignment]

    try:
        # Re-import to pick up the patched sys.modules state
        if "quirk.scanner.snmp_scanner" in sys.modules:
            del sys.modules["quirk.scanner.snmp_scanner"]

        from quirk.scanner.snmp_scanner import probe_snmp_target  # noqa — Plan 01

        # Must not raise even with pysnmp effectively absent
        result = probe_snmp_target("127.0.0.1", "public", 1)

        assert isinstance(result, dict), (
            "probe_snmp_target must return a dict even when pysnmp is missing"
        )
        for key in ("snmp_sysdescr", "snmp_sysname", "snmp_sysobjectid"):
            assert key in result, (
                f"Missing key '{key}' in advisory-guard fallback dict. Keys: {sorted(result)}"
            )
            assert result[key] is None, (
                f"Key '{key}' must be None when pysnmp is absent, got: {result[key]!r}"
            )
    finally:
        # Restore sys.modules so we don't poison other tests
        sys.modules.clear()
        sys.modules.update(saved)


# ---------------------------------------------------------------------------
# Contract 2 — parse_sysdescr vendor extraction (SNMP-01 / D-07)
# ---------------------------------------------------------------------------

def test_sysdescr_parse_cisco_ios() -> None:
    """Cisco IOS sysDescr must map to vendor='Cisco'."""
    from quirk.scanner.snmp_scanner import parse_sysdescr  # noqa — Plan 01

    result = parse_sysdescr(
        "Cisco IOS Software, Version 15.2(4)M3, RELEASE SOFTWARE (fc2) "
        "Technical Support: http://www.cisco.com/techsupport"
    )
    assert isinstance(result, dict), "parse_sysdescr must return a dict"
    assert result.get("vendor") == "Cisco", (
        f"Expected vendor='Cisco' for Cisco IOS sysDescr, got: {result.get('vendor')!r}"
    )


def test_sysdescr_parse_juniper() -> None:
    """Juniper Junos sysDescr must map to vendor='Juniper'."""
    from quirk.scanner.snmp_scanner import parse_sysdescr  # noqa — Plan 01

    result = parse_sysdescr(
        "Juniper Networks, Inc. SRX300 internet router, kernel JUNOS 20.2R3"
    )
    assert isinstance(result, dict), "parse_sysdescr must return a dict"
    assert result.get("vendor") == "Juniper", (
        f"Expected vendor='Juniper' for Juniper sysDescr, got: {result.get('vendor')!r}"
    )


def test_sysdescr_parse_fortinet() -> None:
    """Fortinet FortiGate sysDescr must map to vendor='Fortinet'."""
    from quirk.scanner.snmp_scanner import parse_sysdescr  # noqa — Plan 01

    result = parse_sysdescr(
        "FortiGate-60F (FG-60F) v7.4.3,build2573 (GA)"
    )
    assert isinstance(result, dict), "parse_sysdescr must return a dict"
    assert result.get("vendor") == "Fortinet", (
        f"Expected vendor='Fortinet' for FortiGate sysDescr, got: {result.get('vendor')!r}"
    )


def test_sysdescr_parse_unknown() -> None:
    """Unrecognized sysDescr must map to vendor='Unknown' (no raise)."""
    from quirk.scanner.snmp_scanner import parse_sysdescr  # noqa — Plan 01

    result = parse_sysdescr("Some random network device v1.2")
    assert isinstance(result, dict), "parse_sysdescr must return a dict"
    assert result.get("vendor") == "Unknown", (
        f"Expected vendor='Unknown' for unrecognized sysDescr, got: {result.get('vendor')!r}"
    )


def test_sysdescr_parse_none_safe() -> None:
    """parse_sysdescr(None) must return vendor='Unknown' without raising TypeError."""
    from quirk.scanner.snmp_scanner import parse_sysdescr  # noqa — Plan 01

    result = parse_sysdescr(None)  # type: ignore[arg-type]
    assert isinstance(result, dict), "parse_sysdescr(None) must return a dict"
    assert result.get("vendor") == "Unknown", (
        f"Expected vendor='Unknown' for None input, got: {result.get('vendor')!r}"
    )


# ---------------------------------------------------------------------------
# Contract 3 — ORM schema: HardwareDevice snmp_* columns (SNMP-02)
# ---------------------------------------------------------------------------

def test_hardware_device_has_snmp_fields() -> None:
    """HardwareDevice ORM must have all four SNMP columns after Plan 02 migration.

    Currently HardwareDevice has: id, scan_id, host, port, vendor, model,
    pqc_status, eol_date, confidence, fingerprint_method, raw_banner,
    scanned_at, remediation_tier — no snmp_* fields.
    """
    from quirk.models import HardwareDevice  # noqa — import works; columns will fail

    column_names = {col.key for col in HardwareDevice.__table__.columns}
    required_snmp_columns = {
        "snmp_sysdescr",
        "snmp_sysname",
        "snmp_sysobjectid",
        "snmp_vendor",
    }
    missing = required_snmp_columns - column_names
    assert not missing, (
        f"HardwareDevice is missing SNMP ORM columns: {sorted(missing)}. "
        "Plan 02 must add these columns with an additive migration."
    )


# ---------------------------------------------------------------------------
# Contract 4 — CBOM Pass 4: quirk:hw-snmp-oid property (SNMP-03 / D-11)
# ---------------------------------------------------------------------------

def _build_cbom_for_hw(hw_device_dict: dict[str, Any]) -> Any:
    """Helper: call build_cbom with a single hw_devices entry and return the BOM."""
    from quirk.cbom.builder import build_cbom  # noqa

    bom = build_cbom(endpoints=[], hw_devices=[hw_device_dict])
    return bom


def _all_property_names(bom: Any) -> list[str]:
    """Extract all Property.name values across all BOM components."""
    names: list[str] = []
    for component in getattr(bom, "components", []):
        for prop in getattr(component, "properties", []):
            names.append(getattr(prop, "name", ""))
    return names


def test_cbom_hw_snmp_oid_property() -> None:
    """build_cbom must emit quirk:hw-snmp-oid when snmp_sysdescr is non-null.

    Follows the existing quirk:hw-bridge-status conditional pattern in
    builder.py L1044–1046. Plan 04 must add the parallel snmp_sysdescr guard.
    """
    hw_device = {
        "host": "10.0.0.1",
        "port": 161,
        "vendor": "Cisco",
        "model": "ASA5505",
        "pqc_status": "unsupported",
        "confidence": "high",
        "fingerprint_method": "snmp",
        "raw_banner": "Cisco IOS Software, Version 15.2(4)M3",
        "remediation_tier": "Tier 1",
        "snmp_sysdescr": "Cisco IOS Software, Version 15.2(4)M3, RELEASE SOFTWARE (fc2)",
        "snmp_sysname": "core-router-01",
        "snmp_sysobjectid": "1.3.6.1.4.1.9.1.1045",
        "snmp_vendor": "Cisco",
        "bridge_status": None,
    }

    bom = _build_cbom_for_hw(hw_device)
    prop_names = _all_property_names(bom)

    assert "quirk:hw-snmp-oid" in prop_names, (
        "CBOM builder must emit a Property(name='quirk:hw-snmp-oid') when "
        "snmp_sysdescr is non-null. Plan 04 must add this conditional property "
        f"to the hw_devices loop. Found properties: {sorted(set(prop_names))}"
    )


def test_cbom_no_snmp_oid_when_null() -> None:
    """build_cbom must NOT emit quirk:hw-snmp-oid when snmp_sysdescr is None.

    Non-SNMP hw_devices (fingerprinted via ssh_banner or http_mgmt only) must
    not get a spurious SNMP property. The D-11 guard is conditional on non-null.

    This test has a two-part structure:
    1. First build with a NON-NULL snmp_sysdescr to verify the property CAN be
       emitted (proving the builder actually knows about snmp_sysdescr — not a
       vacuous pass). This part will FAIL until Plan 04 adds SNMP support.
    2. Then verify the property is absent when snmp_sysdescr is None.
    """
    # Part 1: build with non-null snmp_sysdescr to confirm the builder emits
    # the property AT ALL (prevents vacuous pass before Plan 04).
    hw_with_snmp = {
        "host": "10.0.0.3",
        "port": 161,
        "vendor": "Cisco",
        "model": "ASA5505",
        "pqc_status": "unsupported",
        "confidence": "high",
        "fingerprint_method": "snmp",
        "raw_banner": "Cisco IOS Software",
        "remediation_tier": "Tier 1",
        "snmp_sysdescr": "Cisco IOS Software, Version 15.2(4)M3",
        "snmp_sysname": "router-a",
        "snmp_sysobjectid": "1.3.6.1.4.1.9",
        "snmp_vendor": "Cisco",
        "bridge_status": None,
    }
    bom_with = _build_cbom_for_hw(hw_with_snmp)
    prop_names_with = _all_property_names(bom_with)
    assert "quirk:hw-snmp-oid" in prop_names_with, (
        "PREREQUISITE FAILED: build_cbom must emit quirk:hw-snmp-oid when "
        "snmp_sysdescr is non-null. Plan 04 must add this. Without confirming "
        "the builder can emit the property, the null-guard assertion below is "
        f"vacuously true. Properties found: {sorted(set(prop_names_with))}"
    )

    # Part 2: now verify it is absent when snmp_sysdescr is None.
    hw_device = {
        "host": "10.0.0.2",
        "port": 22,
        "vendor": "Cisco",
        "model": "ASA5505",
        "pqc_status": "unsupported",
        "confidence": "medium",
        "fingerprint_method": "ssh_banner",
        "raw_banner": "SSH-2.0-Cisco-1.25",
        "remediation_tier": "Tier 1",
        "snmp_sysdescr": None,
        "snmp_sysname": None,
        "snmp_sysobjectid": None,
        "snmp_vendor": None,
        "bridge_status": None,
    }

    bom = _build_cbom_for_hw(hw_device)
    prop_names = _all_property_names(bom)

    assert "quirk:hw-snmp-oid" not in prop_names, (
        "CBOM builder must NOT emit quirk:hw-snmp-oid when snmp_sysdescr is None. "
        f"Found properties: {sorted(set(prop_names))}"
    )


# ---------------------------------------------------------------------------
# Contract 5 — snmp_meta staleness gate (SNMP-05)
# ---------------------------------------------------------------------------

def test_snmp_meta_staleness_coverage() -> None:
    """quirk.scanner.snmp_meta must have SNMP_VENDOR_MATRIX with >= 4 vendor entries.

    Mirrors the HARDWARE_MATRIX pattern in hardware_meta.py:
      - SNMP_VENDOR_MATRIX["last_verified"] must be present
      - SNMP_VENDOR_MATRIX["entries"] must be a list
      - At least 4 entries: Cisco, Juniper, Fortinet, Linux

    Plan 01 (or a dedicated snmp_meta.py) must define this structure.
    """
    from quirk.scanner.snmp_meta import SNMP_VENDOR_MATRIX  # noqa — will fail until Plan 01

    assert "last_verified" in SNMP_VENDOR_MATRIX, (
        "SNMP_VENDOR_MATRIX must have a 'last_verified' key (ISO date string). "
        "Mirrors hardware_meta.py HARDWARE_MATRIX['last_verified']."
    )
    assert "entries" in SNMP_VENDOR_MATRIX, (
        "SNMP_VENDOR_MATRIX must have an 'entries' key containing the vendor list."
    )
    entries = SNMP_VENDOR_MATRIX["entries"]
    assert isinstance(entries, list), (
        f"SNMP_VENDOR_MATRIX['entries'] must be a list, got: {type(entries)}"
    )
    assert len(entries) >= 4, (
        f"SNMP_VENDOR_MATRIX must have >= 4 entries (Cisco, Juniper, Fortinet, Linux). "
        f"Got {len(entries)} entries."
    )


def test_snmp_meta_staleness_threshold() -> None:
    """quirk.scanner.snmp_meta must define STALENESS_THRESHOLD_DAYS = 90.

    Matches hardware_meta.py quarterly cadence. CI staleness check enforces this.
    """
    import quirk.scanner.snmp_meta as snmp_meta  # noqa — will fail until Plan 01

    assert hasattr(snmp_meta, "STALENESS_THRESHOLD_DAYS"), (
        "snmp_meta must export STALENESS_THRESHOLD_DAYS (int, value 90)"
    )
    assert snmp_meta.STALENESS_THRESHOLD_DAYS == 90, (
        f"STALENESS_THRESHOLD_DAYS must be 90 (quarterly cadence), "
        f"got: {snmp_meta.STALENESS_THRESHOLD_DAYS}"
    )


# ---------------------------------------------------------------------------
# Contract 6 — D-08: [hw] extras NOT in [all] (pip guard — @pytest.mark.slow)
# ---------------------------------------------------------------------------

@pytest.mark.slow
def test_install_all_excludes_pysnmp(tmp_path: "Path") -> None:  # type: ignore[name-defined]  # noqa: F821
    """D-08 guard: quirk[all] must NOT transitively pull pysnmp or sysdescrparser.

    pysnmp is a large optional dependency; SNMP scanning requires explicit
    operator opt-in via ``quirk[hw]``. This mirrors test_install_all_excludes_impacket.py.

    If this test fails, someone added quirk[hw] to the [all] meta-extra in
    pyproject.toml. Revert that change. Operators who need SNMP fingerprinting
    must install quirk[hw] explicitly in their environment.
    """
    import json
    import subprocess
    from pathlib import Path as _Path

    REPO_ROOT = _Path(__file__).resolve().parent.parent
    report_path = tmp_path / "report.json"

    cmd = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--dry-run",
        "--ignore-installed",
        "--quiet",
        "--report",
        str(report_path),
        "-e",
        f"{REPO_ROOT}[all]",
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=180,
    )

    assert result.returncode == 0, (
        "pip install --dry-run -e <repo>[all] FAILED. "
        "D-08: the [all] meta-extra must resolve cleanly. "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )

    combined_output = (result.stdout or "") + (result.stderr or "")
    assert "does not provide the extra 'all'" not in combined_output, (
        "pyproject.toml does not define the [all] meta-extra yet. "
        "D-08: the [all] extra must be defined in pyproject.toml."
    )

    assert report_path.exists(), (
        "pip --report did not write a JSON file; check pip version "
        "(>= 22.2 required for --report)."
    )

    report = json.loads(report_path.read_text())
    installed = {
        item["metadata"]["name"].lower()
        for item in report.get("install", [])
        if item.get("metadata", {}).get("name")
    }

    # Sanity check: [all] must actually expand to component extras.
    expected_from_all = {
        "kubernetes",       # from [cloud]
        "psycopg2-binary",  # from [db]
        "redis",            # from [redis]/[broker]
        "fastapi",          # from [dashboard]
    }
    missing_expected = expected_from_all - installed
    assert not missing_expected, (
        f"quirk[all] resolved but is missing expected component packages "
        f"{sorted(missing_expected)}. "
        f"Resolved packages: {sorted(installed)}"
    )

    # Core assertion: [hw] extras must NOT appear in [all]
    assert "pysnmp" not in installed, (
        "REGRESSION (D-08): pysnmp is present in the resolved set for quirk[all]. "
        "pysnmp must only be in the [hw] extras group, never in [all]. "
        "Remove quirk[hw] from the [all] meta-extra in pyproject.toml. "
        f"Resolved packages: {sorted(installed)}"
    )

    assert "sysdescrparser" not in installed, (
        "REGRESSION (D-08): sysdescrparser is present in the resolved set for quirk[all]. "
        "sysdescrparser must only be in the [hw] extras group, never in [all]. "
        f"Resolved packages: {sorted(installed)}"
    )
