"""Phase 155 (HWLC-08) — EOL/EOS catalog staleness gate, correlation, and
state-classification tests.

Mirrors tests/test_cve_staleness.py 1:1 with names substituted
(is_eol_table_stale, EOL_TABLE_META, EOL_TABLE), boundary values adjusted to
365 (not stale) / 366 (stale), and honoring QUIRK_CI_STALENESS_OVERRIDE_DATE
the same way. This catalog ships no CLI command, so the CLI-smoke section is
intentionally omitted (unlike test_cve_staleness.py's `cve status` subprocess
tests).
"""
from __future__ import annotations

import datetime
import os

import pytest


# ---------------- HWLC-08: table shape ----------------

def test_eol_table_meta_shape() -> None:
    from quirk.scanner.hardware_eol import EOL_TABLE_META, STALENESS_THRESHOLD_DAYS

    required_keys = {"last_verified", "source", "source_url"}
    assert required_keys.issubset(EOL_TABLE_META.keys()), (
        f"EOL_TABLE_META missing required keys: "
        f"{required_keys - set(EOL_TABLE_META.keys())}"
    )

    # last_verified must be a parseable ISO date.
    datetime.date.fromisoformat(EOL_TABLE_META["last_verified"])

    assert isinstance(STALENESS_THRESHOLD_DAYS, int)
    assert STALENESS_THRESHOLD_DAYS == 365  # D-15: matches bacnet_vendors/compliance cadence


# ---------------- HWLC-08: staleness gate + boundary math ----------------

def _check_staleness(today: datetime.date) -> int:
    from quirk.scanner.hardware_eol import EOL_TABLE_META
    last_verified = datetime.date.fromisoformat(EOL_TABLE_META["last_verified"])
    return (today - last_verified).days


def test_eol_table_not_stale() -> None:
    """Production gate: with no override, current EOL_TABLE_META must be FRESH."""
    from quirk.scanner.hardware_eol import EOL_TABLE_META, STALENESS_THRESHOLD_DAYS

    override = os.environ.get("QUIRK_CI_STALENESS_OVERRIDE_DATE")
    today = (
        datetime.date.fromisoformat(override)
        if override
        else datetime.date.today()
    )
    age = _check_staleness(today)
    assert age <= STALENESS_THRESHOLD_DAYS, (
        f"EOL_TABLE_META.last_verified is {age} days old "
        f"(>{STALENESS_THRESHOLD_DAYS}). Re-verify against vendor EOL/EOS "
        f"bulletins and bump last_verified in quirk/scanner/hardware_eol.py."
    )


def test_eol_staleness_boundary_365_days_not_stale() -> None:
    """Exactly 365 days old is NOT stale (strict `>`)."""
    from quirk.scanner.hardware_eol import (
        EOL_TABLE_META, STALENESS_THRESHOLD_DAYS, is_eol_table_stale,
    )
    last_verified = datetime.date.fromisoformat(EOL_TABLE_META["last_verified"])
    fake_today = last_verified + datetime.timedelta(days=STALENESS_THRESHOLD_DAYS)
    assert is_eol_table_stale(today=fake_today) is False


def test_eol_staleness_boundary_366_days_is_stale() -> None:
    """366 days old IS stale."""
    from quirk.scanner.hardware_eol import (
        EOL_TABLE_META, STALENESS_THRESHOLD_DAYS, is_eol_table_stale,
    )
    last_verified = datetime.date.fromisoformat(EOL_TABLE_META["last_verified"])
    fake_today = last_verified + datetime.timedelta(days=STALENESS_THRESHOLD_DAYS + 1)
    assert is_eol_table_stale(today=fake_today) is True


# ---------------- HWLC-09: correlate_eol() ----------------

def test_correlate_eol_known_key_returns_parsed_dates() -> None:
    import datetime as d
    from quirk.scanner.hardware_eol import EOL_TABLE, correlate_eol

    key = next(iter(EOL_TABLE))
    result = correlate_eol(*key)
    assert result.attempted is True
    assert result.eol_date is None or isinstance(result.eol_date, d.date)


def test_correlate_eol_unknown_vendor_and_model_never_raises() -> None:
    from quirk.scanner.hardware_eol import correlate_eol

    result = correlate_eol("NoSuchVendor", "NoSuchModel")
    assert result.attempted is True
    assert result.eol_date is None
    assert result.eos_date is None


def test_correlate_eol_none_model_never_raises() -> None:
    from quirk.scanner.hardware_eol import correlate_eol

    result = correlate_eol("Unknown", None)
    assert result.attempted is True
    assert result.eol_date is None


def test_correlate_eol_malformed_date_yields_none_not_raise() -> None:
    """A catalog entry with a malformed date string yields eol_date=None
    rather than raising (fail-closed parse)."""
    from quirk.scanner.hardware_eol import _parse_iso_date

    assert _parse_iso_date("not-a-date") is None
    assert _parse_iso_date(None) is None
    assert _parse_iso_date("") is None


# ---------------- HWLC-09: eol_state() ----------------

def test_eol_state_passed() -> None:
    from quirk.scanner.hardware_eol import eol_state
    assert eol_state(datetime.date(2020, 1, 1), today=datetime.date(2026, 8, 14)) == "passed"


def test_eol_state_approaching() -> None:
    from quirk.scanner.hardware_eol import eol_state
    assert eol_state(datetime.date(2027, 1, 1), today=datetime.date(2026, 8, 14)) == "approaching"


def test_eol_state_beyond_window_is_none() -> None:
    from quirk.scanner.hardware_eol import eol_state
    assert eol_state(datetime.date(2030, 1, 1), today=datetime.date(2026, 8, 14)) is None


def test_eol_state_none_input_is_none() -> None:
    from quirk.scanner.hardware_eol import eol_state
    assert eol_state(None) is None


# ---------------- HWLC-08/09: catalog content invariants ----------------

def test_eol_table_has_pre_and_post_2030_entries() -> None:
    """At least one entry has eol_date before 2030-01-01, and at least one
    has eol_date on or after 2030-01-01 (so plan 155-04 can test both sides
    of assign_tier()'s EOL override)."""
    import datetime as d
    from quirk.scanner.hardware_eol import EOL_TABLE

    dates = [
        d.date.fromisoformat(entry["eol_date"])
        for entry in EOL_TABLE.values()
        if entry.get("eol_date")
    ]
    assert any(x < d.date(2030, 1, 1) for x in dates)
    assert any(x >= d.date(2030, 1, 1) for x in dates)


def test_eol_table_entries_have_https_source_url() -> None:
    from quirk.scanner.hardware_eol import EOL_TABLE

    for key, entry in EOL_TABLE.items():
        source_url = entry.get("source_url")
        assert isinstance(source_url, str) and source_url.startswith("https://"), (
            f"EOL_TABLE{key} missing a valid https:// source_url"
        )


def test_eol_table_minimum_entries() -> None:
    from quirk.scanner.hardware_eol import EOL_TABLE
    assert len(EOL_TABLE) >= 3, len(EOL_TABLE)
