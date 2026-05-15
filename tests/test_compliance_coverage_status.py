"""Phase 74-03 (D-10, WR-11): SCANNER_COVERAGE_STATUS invariant tests.

Parallel dict to SCANNER_COVERAGE distinguishing "covered" from "pending"
(zero-weight not-yet-covered) and "n/a" (intentionally out-of-scope).
"""
from __future__ import annotations

from quirk.qramm.compliance_map import (
    SCANNER_COVERAGE,
    SCANNER_COVERAGE_STATUS,
)


_VALID_VALUES = {"covered", "partial", "pending", "n/a"}


def test_coverage_status_keys_match_scanner_coverage() -> None:
    """Key parity invariant: every dimension in SCANNER_COVERAGE has a status."""
    assert set(SCANNER_COVERAGE_STATUS.keys()) == set(SCANNER_COVERAGE.keys())


def test_coverage_status_values_valid() -> None:
    """Every status value is a member of the Literal type."""
    for dim, status in SCANNER_COVERAGE_STATUS.items():
        assert status in _VALID_VALUES, f"{dim}={status!r} not in {_VALID_VALUES}"


def test_coverage_status_cvi_covered() -> None:
    """CVI is the only currently-covered dimension in v4.8."""
    assert SCANNER_COVERAGE_STATUS["CVI"] == "covered"


def test_coverage_status_zero_weight_dimensions_pending() -> None:
    """SGRM/DPE/ITR (weight=0.0) map to 'pending', not 'covered'."""
    assert SCANNER_COVERAGE_STATUS["SGRM"] == "pending"
    assert SCANNER_COVERAGE_STATUS["DPE"] == "pending"
    assert SCANNER_COVERAGE_STATUS["ITR"] == "pending"
