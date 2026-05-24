"""Phase 98 D-06 / TRANS-03 — _check_congruence unit tests.

Covers all band/severity cases for the congruence guard that prevents a
contradictory exec headline from being emitted (e.g., "GOOD" over 7 CRITICAL).

Test node IDs from 98-VALIDATION.md:
  - test_good_band_with_critical_raises
  - test_fair_band_with_critical_ok
"""
from __future__ import annotations

import pytest

from quirk.reports.content_model import (
    ReportCongruenceError,
    _check_congruence,
    build_exec_content,
)

# ---------------------------------------------------------------------------
# Tests — exact VALIDATION.md node IDs
# ---------------------------------------------------------------------------


def test_good_band_with_critical_raises():
    """TRANS-03 / D-06: GOOD band with CRITICAL findings raises ReportCongruenceError.

    The congruence guard must make it structurally impossible to emit a "GOOD"
    headline while CRITICAL findings are open.
    Node ID: test_congruence_guard.py::test_good_band_with_critical_raises
    """
    with pytest.raises(ReportCongruenceError) as exc_info:
        _check_congruence("GOOD", {"CRITICAL": 3, "HIGH": 2})

    msg = str(exc_info.value)
    assert "GOOD" in msg, (
        "ReportCongruenceError message must include the band name 'GOOD'. "
        "TRANS-03 / UI-SPEC Copywriting Contract."
    )
    assert "3" in msg, (
        "ReportCongruenceError message must include the CRITICAL count '3'. "
        "TRANS-03 / UI-SPEC Copywriting Contract."
    )
    assert "CRITICAL" in msg, (
        "ReportCongruenceError message must include 'CRITICAL'. "
        "TRANS-03 / UI-SPEC Copywriting Contract."
    )


def test_excellent_band_with_critical_raises():
    """TRANS-03 / D-06: EXCELLENT band with any CRITICAL finding raises.

    EXCELLENT is a stricter band than GOOD; same restriction applies.
    """
    with pytest.raises(ReportCongruenceError) as exc_info:
        _check_congruence("EXCELLENT", {"CRITICAL": 1})

    msg = str(exc_info.value)
    assert "EXCELLENT" in msg, (
        "ReportCongruenceError message must include the band name 'EXCELLENT'. "
        "TRANS-03 / UI-SPEC Copywriting Contract."
    )
    assert "1" in msg, (
        "ReportCongruenceError message must include the CRITICAL count '1'. TRANS-03."
    )


def test_moderate_band_with_critical_raises():
    """TRANS-03 / D-06: MODERATE band with any CRITICAL finding raises.

    Per RESEARCH Pattern 2 / D-06 resolution: MODERATE is blocked by any CRITICAL.
    """
    with pytest.raises(ReportCongruenceError):
        _check_congruence("MODERATE", {"CRITICAL": 1})


def test_fair_band_with_critical_ok():
    """TRANS-03 / D-06: FAIR band with CRITICAL findings does NOT raise.

    FAIR band implies significant exposure — CRITICAL findings are consistent with it.
    Node ID: test_congruence_guard.py::test_fair_band_with_critical_ok
    """
    # Must not raise — no exception expected
    _check_congruence("FAIR", {"CRITICAL": 5, "HIGH": 10})


def test_poor_band_with_critical_ok():
    """TRANS-03 / D-06: POOR band with many CRITICAL findings does NOT raise.

    POOR band implies immediate remediation — CRITICAL findings are fully compatible.
    """
    _check_congruence("POOR", {"CRITICAL": 9, "HIGH": 5, "MEDIUM": 3})


def test_good_band_zero_critical_ok():
    """TRANS-03 / D-06: GOOD band with zero CRITICAL findings does NOT raise."""
    _check_congruence("GOOD", {"HIGH": 5, "MEDIUM": 3, "LOW": 10})


def test_congruence_error_message_matches_ui_spec():
    """TRANS-03: ReportCongruenceError message matches UI-SPEC Copywriting Contract.

    Expected format:
      "Report generation halted: executive headline '{band}' is inconsistent
       with {n} CRITICAL finding(s). Review findings before generating the report."
    """
    n = 7
    band = "GOOD"
    with pytest.raises(ReportCongruenceError) as exc_info:
        _check_congruence(band, {"CRITICAL": n})

    msg = str(exc_info.value)
    # Check all required phrases from the UI-SPEC Copywriting Contract
    assert "Report generation halted" in msg, (
        f"Message missing 'Report generation halted'. Got: {msg!r}. "
        "TRANS-03 / UI-SPEC Copywriting Contract."
    )
    assert f"'{band}'" in msg, (
        f"Message missing band name in quotes ('{band}'). Got: {msg!r}. "
        "TRANS-03 / UI-SPEC Copywriting Contract."
    )
    assert str(n) in msg, (
        f"Message missing count '{n}'. Got: {msg!r}. "
        "TRANS-03 / UI-SPEC Copywriting Contract."
    )
    assert "CRITICAL finding" in msg, (
        f"Message missing 'CRITICAL finding'. Got: {msg!r}. "
        "TRANS-03 / UI-SPEC Copywriting Contract."
    )
    assert "Review findings" in msg, (
        f"Message missing 'Review findings'. Got: {msg!r}. "
        "TRANS-03 / UI-SPEC Copywriting Contract."
    )


def test_congruence_guard_is_exception_subclass():
    """D-06: ReportCongruenceError is a subclass of ValueError (pattern from quirk/errors.py)."""
    assert issubclass(ReportCongruenceError, ValueError), (
        "ReportCongruenceError must subclass ValueError to match the custom exception pattern. "
        "D-06 / quirk/errors.py pattern."
    )


def test_build_exec_content_calls_guard_internally():
    """TRANS-03 / D-06: build_exec_content raises ReportCongruenceError when guard fires.

    The guard must be called before returning ExecContent — no I/O can occur first.
    """
    score_raw = {
        "score": 80,
        "rating": "GOOD",  # GOOD with CRITICAL -> guard fires
        "subscores": {
            "hygiene": 20, "modern_tls": 18, "identity_trust": 25,
            "agility_signals": 15, "data_at_rest": 22, "data_in_motion": 21,
        },
        "drivers": [],
    }
    findings = [
        {"title": "RSA cert", "severity": "CRITICAL", "category": "RSA"},
    ]

    with pytest.raises(ReportCongruenceError) as exc_info:
        build_exec_content(
            score_raw=score_raw,
            findings=findings,
            roadmap_items=[],
        )

    msg = str(exc_info.value)
    assert "GOOD" in msg, (
        "build_exec_content must propagate ReportCongruenceError from _check_congruence. "
        "TRANS-03 / D-06."
    )
