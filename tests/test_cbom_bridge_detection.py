"""RED scaffold for HWCOMPAT-03 bridge detection invariants.

This file is intentionally RED and will fail with ImportError until
``quirk/cbom/bridge.py`` is created in Plan 129-01.  Do NOT attempt to fix
these failures at the scaffold stage — the ImportError is the correct outcome.
"""
from __future__ import annotations

from quirk.cbom.bridge import _detect_crypto_bridges  # RED: module does not exist yet


# ---------------------------------------------------------------------------
# Helper fixture
# ---------------------------------------------------------------------------


def _make_hw_dict(host: str, pqc_status: str) -> dict:
    return {
        "host": host,
        "port": 22,
        "vendor": "TestVendor",
        "model": "TestModel",
        "pqc_status": pqc_status,
        "remediation_tier": "Tier 1",
    }


# ---------------------------------------------------------------------------
# Test functions
# ---------------------------------------------------------------------------


def test_both_directly_reachable_is_partial_only():
    """HWCOMPAT-03 / D-04: both directly scanned on same /24 → partial_only."""
    devices = [
        _make_hw_dict("192.168.1.1", "supported"),
        _make_hw_dict("192.168.1.2", "unsupported"),
    ]
    result = _detect_crypto_bridges(devices)
    assert result[0]["bridge_status"] == "partial_only"
    assert result[1]["bridge_status"] == "partial_only"


def test_upstream_mitigated_not_auto_assigned():
    """HWCOMPAT-03 / D-04: upstream_mitigated is never auto-assigned; lone PQC device → None."""
    devices = [_make_hw_dict("192.168.1.1", "supported")]
    result = _detect_crypto_bridges(devices)
    assert result[0]["bridge_status"] is None


def test_cross_subnet_not_paired():
    """HWCOMPAT-03: devices on different /24 subnets must not be paired."""
    devices = [
        _make_hw_dict("192.168.1.1", "supported"),
        _make_hw_dict("10.0.0.1", "unsupported"),
    ]
    result = _detect_crypto_bridges(devices)
    assert result[0]["bridge_status"] is None
    assert result[1]["bridge_status"] is None


def test_pqc_status_case_insensitive():
    """HWCOMPAT-03 / Pitfall 4: pqc_status comparison must be case-insensitive."""
    devices = [
        _make_hw_dict("192.168.1.1", "partial"),
        _make_hw_dict("192.168.1.2", "VENDOR-SILENT"),
    ]
    result = _detect_crypto_bridges(devices)
    assert result[0]["bridge_status"] == "partial_only"
    assert result[1]["bridge_status"] == "partial_only"


def test_empty_devices_returns_empty():
    """HWCOMPAT-03: empty input returns empty output without error."""
    result = _detect_crypto_bridges([])
    assert result == []


def test_input_dicts_not_mutated():
    """HWCOMPAT-03 / D-02: input dicts must not be mutated; callers share them with HTML/PDF renderers."""
    device = _make_hw_dict("192.168.1.1", "supported")
    _detect_crypto_bridges([device])
    assert "bridge_status" not in device  # IN-01: check device itself, not a copy
