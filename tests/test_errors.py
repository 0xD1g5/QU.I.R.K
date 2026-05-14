"""Phase 68 UX-01: unit tests for quirk/errors.py canonical registry."""
from __future__ import annotations

import dataclasses

import pytest

from quirk.errors import (
    CATEGORY_TO_CODE,
    ERROR_REGISTRY,
    ErrorEntry,
    format_error,
)


REQUIRED_CODES = {
    # INSTALL domain
    "INSTALL-001", "INSTALL-002", "INSTALL-003", "INSTALL-004", "INSTALL-005",
    "INSTALL-006", "INSTALL-007", "INSTALL-008", "INSTALL-009", "INSTALL-010",
    # DASHBOARD domain
    "DASHBOARD-001", "DASHBOARD-002", "DASHBOARD-003", "DASHBOARD-004",
    "DASHBOARD-005", "DASHBOARD-006", "DASHBOARD-007", "DASHBOARD-008",
    "DASHBOARD-009", "DASHBOARD-010", "DASHBOARD-011", "DASHBOARD-012", "DASHBOARD-013",
    # SCHED domain
    "SCHED-001", "SCHED-002", "SCHED-003", "SCHED-004",
    # CBOM domain
    "CBOM-001",
}


def test_format_error_wire_format():
    got = format_error("INSTALL-001")
    assert got == (
        "[QRK-INSTALL-001] Optional scanner package not installed. "
        "Fix: Run `pip install quirk[<extra>]` to enable this scanner."
    )


def test_format_error_unknown_code():
    assert format_error("BOGUS-999") == "[QRK-BOGUS-999] Unknown error code."


def test_format_error_all_codes_have_fix_segment():
    for code in ERROR_REGISTRY:
        msg = format_error(code)
        assert msg.startswith(f"[QRK-{code}]"), msg
        assert " Fix: " in msg, msg


def test_error_entry_is_frozen():
    entry = next(iter(ERROR_REGISTRY.values()))
    with pytest.raises(dataclasses.FrozenInstanceError):
        entry.cause = "tampered"  # type: ignore[misc]


def test_registry_has_required_codes():
    missing = REQUIRED_CODES - set(ERROR_REGISTRY.keys())
    assert not missing, f"Missing required codes: {missing}"


def test_category_to_code_mapping():
    assert CATEGORY_TO_CODE["missing_extra"] == "INSTALL-001"
    assert CATEGORY_TO_CODE["coverage_gap"] == "CBOM-001"


def test_no_newlines_in_cause_or_fix():
    offenders = [
        code for code, entry in ERROR_REGISTRY.items()
        if "\n" in entry.cause or "\n" in entry.fix
    ]
    assert not offenders, f"Entries with newlines: {offenders}"


def test_install_004_includes_lsof_hint():
    msg = format_error("INSTALL-004")
    assert "lsof -i" in msg
    assert "port" in msg.lower()


def test_dashboard_010_qramm_multiplier_range():
    msg = format_error("DASHBOARD-010")
    assert "0.8" in msg and "1.5" in msg


def test_registry_keys_match_entry_code_field():
    for key, entry in ERROR_REGISTRY.items():
        assert key == entry.code, f"Key {key} != entry.code {entry.code}"


def test_category_to_code_values_are_registered():
    for category, code in CATEGORY_TO_CODE.items():
        assert code in ERROR_REGISTRY, f"CATEGORY_TO_CODE[{category!r}]={code!r} not in registry"
