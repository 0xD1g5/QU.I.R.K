"""Phase 240-03 (D-25) - SNMP vendor matrix age gate, boundary, override and min() rule.

Every test function name here MUST contain the substring "staleness" - CI's
gate step filters with `-k "staleness or freshness"`, so a differently-named
test would be listed in the workflow file and then silently never run.
"""
from __future__ import annotations

import datetime
import os

import pytest


def _reference_date() -> datetime.date:
    """Today, or QUIRK_CI_STALENESS_OVERRIDE_DATE when the CI override is set."""
    override = os.environ.get("QUIRK_CI_STALENESS_OVERRIDE_DATE")
    return datetime.date.fromisoformat(override) if override else datetime.date.today()


def _top_level_matches_min(matrix: dict) -> bool:
    dates = [e["last_verified"] for e in matrix["entries"]]
    return matrix["last_verified"] == min(dates)


def test_snmp_vendor_matrix_boundary_staleness() -> None:
    from quirk.scanner.snmp_meta import (
        SNMP_VENDOR_MATRIX,
        STALENESS_THRESHOLD_DAYS,
        is_snmp_vendor_matrix_stale,
    )

    last_verified = datetime.date.fromisoformat(SNMP_VENDOR_MATRIX["last_verified"])
    fresh = last_verified + datetime.timedelta(days=STALENESS_THRESHOLD_DAYS)
    stale = last_verified + datetime.timedelta(days=STALENESS_THRESHOLD_DAYS + 1)
    assert is_snmp_vendor_matrix_stale(today=fresh) is False
    assert is_snmp_vendor_matrix_stale(today=stale) is True


def test_snmp_vendor_matrix_override_staleness(monkeypatch: pytest.MonkeyPatch) -> None:
    from quirk.scanner import snmp_meta

    monkeypatch.setitem(snmp_meta.SNMP_VENDOR_MATRIX, "last_verified", "2026-09-02")

    monkeypatch.setenv("QUIRK_CI_STALENESS_OVERRIDE_DATE", "2026-12-02")
    assert snmp_meta.is_snmp_vendor_matrix_stale(today=_reference_date()) is True

    monkeypatch.setenv("QUIRK_CI_STALENESS_OVERRIDE_DATE", "2026-12-01")
    assert snmp_meta.is_snmp_vendor_matrix_stale(today=_reference_date()) is False


def test_snmp_vendor_matrix_not_stale_staleness() -> None:
    """Production gate: with no override, the live catalog must be fresh."""
    from quirk.scanner.snmp_meta import (
        SNMP_VENDOR_MATRIX,
        STALENESS_THRESHOLD_DAYS,
        is_snmp_vendor_matrix_stale,
    )

    reference = _reference_date()
    last_verified = datetime.date.fromisoformat(SNMP_VENDOR_MATRIX["last_verified"])
    age = (reference - last_verified).days
    assert not is_snmp_vendor_matrix_stale(today=reference), (
        f"SNMP_VENDOR_MATRIX.last_verified is {age} days old "
        f"(>{STALENESS_THRESHOLD_DAYS}). Re-verify against each source_url and "
        f"bump last_verified in quirk/scanner/snmp_meta.py."
    )


def test_snmp_vendor_matrix_top_level_is_min_staleness() -> None:
    from quirk.scanner.snmp_meta import SNMP_VENDOR_MATRIX

    assert _top_level_matches_min(SNMP_VENDOR_MATRIX), (
        "top-level last_verified must equal the oldest per-vendor last_verified"
    )
    violating = {
        "last_verified": "2026-10-01",
        "entries": [
            {"last_verified": "2026-09-02"},
            {"last_verified": "2026-10-01"},
        ],
    }
    assert not _top_level_matches_min(violating)
