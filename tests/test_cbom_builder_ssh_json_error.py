"""Phase 77 D-08 / cbom-intel-reports/IN-02 — _extract_ssh_algorithms must log
JSONDecodeError via safe_str() instead of swallowing silently.
"""
from __future__ import annotations

import logging

from quirk.cbom import builder as cbom_builder


def test_extract_ssh_algorithms_logs_jsondecodeerror(caplog) -> None:
    caplog.set_level(logging.WARNING, logger=cbom_builder.__name__)

    # Malformed JSON triggers JSONDecodeError inside _extract_ssh_algorithms.
    result = cbom_builder._extract_ssh_algorithms("{not-json")

    assert result == {}, "fallback return value preserved (return {} on parse failure)"

    warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert warning_records, (
        "Phase 77 D-08: _extract_ssh_algorithms must logger.warning() on JSONDecodeError, "
        "not silently swallow (cbom-intel-reports/IN-02)"
    )
    joined = " ".join(r.getMessage() for r in warning_records).lower()
    assert "ssh" in joined or "json" in joined, (
        "WARNING message should mention SSH algorithms or JSON parse context"
    )
