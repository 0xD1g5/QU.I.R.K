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


def test_fuzz_002_cause_agrees_with_max_fuzz_budget():
    """Phase 172 code review WR-02: FUZZ-002's cause/fix strings must derive
    from quirk.scanner.rest_fuzzer.MAX_FUZZ_BUDGET, not restate it as a bare
    literal -- a second hand-maintained copy is exactly how SAFE-02's
    original prose-only ceiling drifted from the enforced code.

    Falsifiability: bump MAX_FUZZ_BUDGET in rest_fuzzer.py to any other value
    without touching errors.py -- this fails because the old literal would no
    longer appear in the (now-stale) cause/fix strings, while this assertion
    (which reads the live constant) would still expect the new value.
    """
    from quirk.scanner.rest_fuzzer import MAX_FUZZ_BUDGET

    entry = ERROR_REGISTRY["FUZZ-002"]
    assert str(MAX_FUZZ_BUDGET) in entry.cause, (
        f"FUZZ-002 cause does not mention MAX_FUZZ_BUDGET ({MAX_FUZZ_BUDGET}): {entry.cause!r}"
    )
    assert str(MAX_FUZZ_BUDGET) in entry.fix, (
        f"FUZZ-002 fix does not mention MAX_FUZZ_BUDGET ({MAX_FUZZ_BUDGET}): {entry.fix!r}"
    )
