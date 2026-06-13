"""Phase 124 — SCOREFIX-01 RED scaffold.

Pins the post-fix behavior for coverage.py::quantum_readiness_score:
  - Finding missing 'severity' key must NOT raise KeyError (currently does → RED).
  - Finding with severity=None must NOT raise (currently does → RED).
  - Both cases must log a WARNING mentioning missing/invalid severity (D-01).

These tests FAIL against the unfixed source (coverage.py:18 does `f["severity"]`).
Wave 1 turns them GREEN by substituting `.get("severity") or "LOW"` + logger.warning.
"""
from __future__ import annotations

import logging

import pytest

from quirk.discovery.coverage import quantum_readiness_score

# Enough endpoints to avoid the <5-endpoint -20-point penalty (not the focus here).
_FIVE_ENDPOINTS = [object() for _ in range(5)]


# SF01a — missing 'severity' key: no KeyError, returns int, logs a warning.
def test_missing_severity_key_does_not_raise(caplog):
    """quantum_readiness_score with a finding that has no 'severity' key must not raise.

    RED: current source does `str(f["severity"])` at line 18 → KeyError.
    GREEN: after fix, `.get("severity") or "LOW"` gracefully defaults.
    """
    findings = [{"description": "some finding without severity"}]

    with caplog.at_level(logging.WARNING, logger="quirk.discovery.coverage"):
        result = quantum_readiness_score(findings, _FIVE_ENDPOINTS)

    # Post-fix: must return an integer (the score).
    assert isinstance(result, int), (
        f"expected int score, got {type(result).__name__}"
    )
    # Post-fix: must log a WARNING about the missing/invalid severity.
    warning_messages = [r.message for r in caplog.records if r.levelno >= logging.WARNING]
    assert any(
        "severity" in msg.lower() for msg in warning_messages
    ), (
        f"expected a WARNING mentioning 'severity' for missing key, got: {warning_messages}"
    )


# SF01b — severity=None: no exception, warning logged.
def test_none_severity_does_not_raise(caplog):
    """quantum_readiness_score with severity=None must not raise.

    RED: current source does `str(f["severity"])` → str(None) = "NONE" which
    does NOT match any severity branch (no penalty), but does NOT log a warning.
    The post-fix contract requires a warning when severity is None (D-01).

    Note: str(None) currently does not raise, but the guard (`.get() or "LOW"`)
    must also fire a warning for None per D-01 "missing/invalid severity".
    The current code does NOT log a warning for None severity → RED on the
    warning assertion.
    """
    findings = [{"severity": None, "description": "finding with null severity"}]

    with caplog.at_level(logging.WARNING, logger="quirk.discovery.coverage"):
        result = quantum_readiness_score(findings, _FIVE_ENDPOINTS)

    assert isinstance(result, int), (
        f"expected int score, got {type(result).__name__}"
    )
    # Post-fix must log a WARNING for None severity.
    warning_messages = [r.message for r in caplog.records if r.levelno >= logging.WARNING]
    assert any(
        "severity" in msg.lower() for msg in warning_messages
    ), (
        f"expected a WARNING mentioning 'severity' for None value, got: {warning_messages}"
    )
