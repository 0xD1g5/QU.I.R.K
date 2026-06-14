"""Phase 128 — HWCOMPAT-04 assign_tier() behavior contract tests (RED scaffold).

Tests pin the tier taxonomy (D-05) and confidence cap (D-04) boundary conditions
as executable assertions BEFORE the implementation in Plan 128-01.

This file is intentionally RED: `quirk/scanner/hardware_tier` does not exist yet.
All tests will fail with ImportError / ModuleNotFoundError until 128-01 creates
the module.

Fixture note: HardwareDevice.__new__(HardwareDevice) creates an uninstrumented
SQLAlchemy object. Attributes are set via dev.__dict__ to bypass ORM
instrumentation (avoids AttributeError on NoneType in SQLAlchemy 2.x when
there is no active mapper state — same pattern as tests/test_hardware_scanner.py).
"""
from __future__ import annotations

from datetime import date

from quirk.scanner.hardware_tier import assign_tier  # RED: module does not exist yet


def _make_device(pqc_status: str, confidence: str, eol_date=None):
    """Create a HardwareDevice fixture without DB/ORM setup."""
    from quirk.models import HardwareDevice
    dev = HardwareDevice.__new__(HardwareDevice)
    dev.__dict__["host"] = "10.0.0.1"
    dev.__dict__["port"] = 22
    dev.__dict__["vendor"] = "TestVendor"
    dev.__dict__["model"] = "TestModel"
    dev.__dict__["fingerprint_method"] = "ssh_banner"
    dev.__dict__["pqc_status"] = pqc_status
    dev.__dict__["confidence"] = confidence
    dev.__dict__["eol_date"] = eol_date
    return dev


# ------------ Tier 1: unsupported + high confidence, no EOL ------------

def test_tier1_unsupported_high_confidence() -> None:
    """pqc_status=unsupported, confidence=high, no EOL → Tier 1 (D-05)."""
    dev = _make_device(pqc_status="unsupported", confidence="high", eol_date=None)
    assert assign_tier(dev) == "Tier 1"


# ------------ Tier 2: partial PQC support ------------

def test_tier2_partial() -> None:
    """pqc_status=partial, confidence=high, no EOL → Tier 2 (D-05)."""
    dev = _make_device(pqc_status="partial", confidence="high", eol_date=None)
    assert assign_tier(dev) == "Tier 2"


# ------------ Tier 3: full PQC support ------------

def test_tier3_supported() -> None:
    """pqc_status=supported, confidence=high, no EOL → Tier 3 (D-05)."""
    dev = _make_device(pqc_status="supported", confidence="high", eol_date=None)
    assert assign_tier(dev) == "Tier 3"


# ------------ Tier N/A: EOL before 2030 wins over tier logic ------------

def test_tier_na_eol_before_2030() -> None:
    """pqc_status=unsupported, confidence=high, eol_date=2027-01-01 → Tier N/A.

    EOL gate is checked FIRST (D-05); Tier 1 classification is irrelevant when
    the device will be end-of-life before the PQC migration window.
    """
    dev = _make_device(
        pqc_status="unsupported", confidence="high", eol_date=date(2027, 1, 1)
    )
    assert assign_tier(dev) == "Tier N/A"


# ------------ D-04 confidence cap: low confidence → max Tier 2 ------------

def test_confidence_cap_low() -> None:
    """pqc_status=unsupported, confidence=low, no EOL → Tier 2, NOT Tier 1 (D-04 cap)."""
    dev = _make_device(pqc_status="unsupported", confidence="low", eol_date=None)
    assert assign_tier(dev) == "Tier 2"


def test_confidence_cap_unknown() -> None:
    """pqc_status=unsupported, confidence=unknown, no EOL → Tier 2, NOT Tier 1 (D-04 cap)."""
    dev = _make_device(pqc_status="unsupported", confidence="unknown", eol_date=None)
    assert assign_tier(dev) == "Tier 2"


# ------------ VENDOR-SILENT: high confidence → Tier 3 (Claude's discretion) ------------

def test_vendor_silent_high() -> None:
    """pqc_status=VENDOR-SILENT, confidence=high, no EOL → Tier 3.

    No known vulnerability; high-confidence fingerprint; treat as accept+monitor (D-05).
    """
    dev = _make_device(pqc_status="VENDOR-SILENT", confidence="high", eol_date=None)
    assert assign_tier(dev) == "Tier 3"


# ------------ VENDOR-SILENT: medium confidence → Tier 2 (more conservative) ------------

def test_vendor_silent_medium() -> None:
    """pqc_status=VENDOR-SILENT, confidence=medium, no EOL → Tier 2.

    Medium confidence with silent vendor; more conservative assignment (D-05 + CONTEXT).
    """
    dev = _make_device(pqc_status="VENDOR-SILENT", confidence="medium", eol_date=None)
    assert assign_tier(dev) == "Tier 2"
