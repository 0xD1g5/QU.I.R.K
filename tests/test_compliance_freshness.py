"""Phase 49 D-04 gate 3 (COMPLY-07): no entry older than STALENESS_THRESHOLD_DAYS.

QC-05 update: tests now call the production check_compliance_staleness() function
rather than duplicating the parse-and-continue logic inline.
"""
from __future__ import annotations

import datetime

import pytest


def test_no_entry_older_than_threshold():
    """All compliance entries are within the freshness window."""
    from quirk.compliance import check_compliance_staleness

    # Should not raise — all current entries are fresh.
    violations = check_compliance_staleness()
    assert violations == [], (
        "check_compliance_staleness() returned violations but should have been empty: "
        f"{violations}"
    )


def test_malformed_date_fails_gate():
    """A malformed last_verified date must NOT silently pass the gate (QC-05)."""
    from quirk.compliance import check_compliance_staleness

    with pytest.raises(RuntimeError, match="malformed"):
        check_compliance_staleness.__wrapped__ if hasattr(check_compliance_staleness, "__wrapped__") else None
        # Inject a synthetic entry with a malformed date to exercise the gate.
        # We call the function with a monkey-patched COMPLIANCE_MAP.
        import quirk.compliance as _mod
        original = _mod.COMPLIANCE_MAP
        try:
            _mod.COMPLIANCE_MAP = {
                "test-title": [
                    {
                        "framework": "TEST",
                        "control": "T.1",
                        "version": "1.0",
                        "last_verified": "not-a-date",
                        "source_url": "https://example.com",
                    }
                ]
            }
            check_compliance_staleness(today=datetime.date(2026, 6, 12))
        finally:
            _mod.COMPLIANCE_MAP = original


def test_stale_entry_fails_gate():
    """An entry older than STALENESS_THRESHOLD_DAYS must raise RuntimeError (QC-05)."""
    from quirk.compliance import check_compliance_staleness, STALENESS_THRESHOLD_DAYS

    import quirk.compliance as _mod
    original = _mod.COMPLIANCE_MAP
    stale_date = (
        datetime.date(2026, 6, 12) - datetime.timedelta(days=STALENESS_THRESHOLD_DAYS + 1)
    ).isoformat()
    try:
        _mod.COMPLIANCE_MAP = {
            "stale-title": [
                {
                    "framework": "TEST",
                    "control": "T.2",
                    "version": "1.0",
                    "last_verified": stale_date,
                    "source_url": "https://example.com",
                }
            ]
        }
        with pytest.raises(RuntimeError, match="stale"):
            check_compliance_staleness(today=datetime.date(2026, 6, 12))
    finally:
        _mod.COMPLIANCE_MAP = original
