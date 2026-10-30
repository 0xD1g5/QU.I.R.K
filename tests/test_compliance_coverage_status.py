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


def test_static_status_dict_is_scanner_only() -> None:
    """Phase 231 D-02: 'self-assessed' is a per-session row status, never a
    scanner coverage status. QRAMM-F01 lifts scanner coverage here; operator
    self-assessment must not leak into this dict."""
    assert "self-assessed" not in SCANNER_COVERAGE_STATUS.values()
    assert set(SCANNER_COVERAGE_STATUS.values()) <= _VALID_VALUES


def test_row_status_values_include_self_assessed() -> None:
    """Phase 231 D-02: the per-row Literal carries every scanner status plus
    'self-assessed'."""
    import typing

    from quirk.qramm.compliance_map import RowCoverageStatus

    row_values = set(typing.get_args(RowCoverageStatus))
    assert "self-assessed" in row_values
    assert _VALID_VALUES <= row_values
