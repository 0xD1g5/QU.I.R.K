"""Phase 127 — HWCOMPAT-02 staleness gate, override, and boundary tests."""
from __future__ import annotations

import datetime
import os

import pytest


# ------------ shape helpers (Phase 203, D-02) ------------

# D-02 part 1: ``last_verified`` is a REQUIRED per-entry key. Every entry carried
# one before Phase 203, but nothing *required* it — so a 9th vendor could be added
# without one, silently reintroducing the borrowed-attestation hazard that D-01
# exists to close.
_ENTRY_REQUIRED_KEYS = frozenset(
    {
        "vendor",
        "model_pattern",
        "pqc_status",
        "eol_date",
        "last_verified",
        "source_url",
        "notes",
    }
)


def _missing_entry_keys(matrix: dict) -> dict:
    """Map ``vendor -> missing required keys`` for every deficient entry.

    Returns an empty mapping when every entry carries the full required key set.
    Takes a matrix-shaped dict rather than reading the module global so the rule
    can be exercised against a violating fixture (see the violation tests below)
    — a rule that has never been observed failing is not a safeguard.
    """
    missing: dict = {}
    for entry in matrix["entries"]:
        absent = _ENTRY_REQUIRED_KEYS - set(entry.keys())
        if absent:
            missing[entry.get("vendor", "<entry with no vendor field>")] = absent
    return missing


def _top_level_min_violation(matrix: dict) -> str | None:
    """Return ``None`` when the top-level date equals ``min()`` of the entry dates.

    Otherwise return a self-documenting failure message.

    D-01/D-02 part 2. The top-level ``last_verified`` is a COMPUTED value — the
    oldest per-vendor attestation — never a date bumped in its own right. That is
    what makes the staleness gate structurally unable to read greener than the
    weakest vendor: one vendor's real re-verification can never cover another
    vendor's unverified entry. The answer is regenerated from the entry data on
    every run rather than trusted from a convention.
    """
    observed = datetime.date.fromisoformat(matrix["last_verified"])
    entry_dates = {
        entry["vendor"]: datetime.date.fromisoformat(entry["last_verified"])
        for entry in matrix["entries"]
    }
    expected = min(entry_dates.values())
    if observed == expected:
        return None
    weakest = sorted(v for v, d in entry_dates.items() if d == expected)
    return (
        f"HARDWARE_MATRIX['last_verified'] is {observed.isoformat()} but the oldest "
        f"per-vendor attestation is {expected.isoformat()} "
        f"(held by: {', '.join(weakest)}). "
        f"Fix quirk/scanner/hardware_meta.py: the top-level last_verified is COMPUTED "
        f"as min() of the entries' own last_verified dates and is never bumped "
        f"independently — bumping it would let one vendor's verification cover "
        f"another's unverified entry (Phase 203 D-01)."
    )


# ------------ shape test ------------

def test_hardware_matrix_shape() -> None:
    from quirk.scanner.hardware_meta import HARDWARE_MATRIX, STALENESS_THRESHOLD_DAYS

    required_keys = {"last_verified", "source_url", "entries"}
    assert required_keys.issubset(HARDWARE_MATRIX.keys()), (
        f"HARDWARE_MATRIX missing required keys: "
        f"{required_keys - set(HARDWARE_MATRIX.keys())}"
    )
    datetime.date.fromisoformat(HARDWARE_MATRIX["last_verified"])
    assert isinstance(STALENESS_THRESHOLD_DAYS, int)
    assert STALENESS_THRESHOLD_DAYS == 90
    assert len(HARDWARE_MATRIX["entries"]) >= 8  # D-10 minimum vendor set

    missing = _missing_entry_keys(HARDWARE_MATRIX)
    assert not missing, (
        f"HARDWARE_MATRIX entries missing required keys: {missing}. "
        f"Add them in quirk/scanner/hardware_meta.py — note last_verified became a "
        f"required per-entry key in Phase 203 (D-02), since the top-level date is "
        f"computed from these."
    )


def test_hardware_matrix_top_level_is_min_of_entries() -> None:
    """The top-level attestation cannot read greener than the weakest vendor.

    Phase 203 D-01/D-02. The top-level ``last_verified`` is ``min()`` of the
    per-vendor dates, so a partially-verified catalog keeps the staleness gate
    red rather than borrowing a verified vendor's date to cover an unverified
    one. The invariant is recomputed from the entry data on every run — a
    written convention is not a safeguard.
    """
    from quirk.scanner.hardware_meta import HARDWARE_MATRIX

    violation = _top_level_min_violation(HARDWARE_MATRIX)
    assert violation is None, violation


# ------------ violation detection (Phase 203, D-02 red-proof) ------------
#
# These exist because all 8 real entries shared 2026-06-13 when the invariant was
# written: min() == max() == any entry, so a green result against live data could
# not distinguish a correct implementation from several incorrect ones. Per this
# project's standing rule, an unproven green test is not evidence.


def _fixture(top_level: str, entry_dates: dict, drop_last_verified: str | None = None) -> dict:
    """Build a matrix-shaped dict: {vendor: ISO date}, optionally dropping a key."""
    entries = []
    for vendor, date_str in entry_dates.items():
        entry = {
            "vendor": vendor,
            "model_pattern": vendor,
            "pqc_status": "partial",
            "eol_date": None,
            "last_verified": date_str,
            "source_url": f"https://example.invalid/{vendor}",
            "notes": "fixture",
        }
        if vendor == drop_last_verified:
            del entry["last_verified"]
        entries.append(entry)
    return {
        "last_verified": top_level,
        "source_url": "https://example.invalid/",
        "entries": entries,
    }


def test_missing_key_detected_when_entry_omits_last_verified() -> None:
    matrix = _fixture(
        "2026-01-01",
        {"Alpha": "2026-01-01", "Bravo": "2026-02-01", "Ghost": "2026-03-01"},
        drop_last_verified="Ghost",
    )
    missing = _missing_entry_keys(matrix)
    assert "Ghost" in missing
    assert missing["Ghost"] == {"last_verified"}


def test_min_violation_detected_when_top_level_is_newer() -> None:
    """Top-level ahead of the oldest entry — the borrowed-attestation failure."""
    matrix = _fixture(
        "2026-03-01",
        {"Alpha": "2026-01-01", "Bravo": "2026-02-01", "Charlie": "2026-03-01"},
    )
    violation = _top_level_min_violation(matrix)
    assert violation is not None
    assert "2026-01-01" in violation
    assert "Alpha" in violation
    assert "quirk/scanner/hardware_meta.py" in violation


def test_min_violation_detected_when_top_level_is_older() -> None:
    """Guards against ``<=`` written where ``==`` was meant."""
    matrix = _fixture(
        "2025-12-01",
        {"Alpha": "2026-01-01", "Bravo": "2026-02-01"},
    )
    assert _top_level_min_violation(matrix) is not None


def test_no_min_violation_when_dates_diverge_but_top_level_is_oldest() -> None:
    """Divergent-but-consistent — the case that discriminates min() from max().

    This is the shape the real catalog takes AFTER per-vendor verification:
    entries carry different dates and the top-level equals the earliest. Today's
    all-identical live data cannot catch a max()-by-mistake implementation; this
    fixture can.
    """
    matrix = _fixture(
        "2026-01-01",
        {"Alpha": "2026-01-01", "Bravo": "2026-05-05", "Charlie": "2026-09-09"},
    )
    assert _top_level_min_violation(matrix) is None


# ------------ not-stale gate ------------

def test_hardware_matrix_not_stale() -> None:
    from quirk.scanner.hardware_meta import (
        HARDWARE_MATRIX, STALENESS_THRESHOLD_DAYS,
    )
    override = os.environ.get("QUIRK_CI_STALENESS_OVERRIDE_DATE")
    today = (
        datetime.date.fromisoformat(override)
        if override
        else datetime.date.today()
    )
    last_verified = datetime.date.fromisoformat(HARDWARE_MATRIX["last_verified"])
    age = (today - last_verified).days
    assert age <= STALENESS_THRESHOLD_DAYS, (
        f"HARDWARE_MATRIX.last_verified is {age} days old "
        f"(>{STALENESS_THRESHOLD_DAYS}). "
        f"Re-verify against {HARDWARE_MATRIX['source_url']} and bump "
        f"last_verified in quirk/scanner/hardware_meta.py."
    )


# ------------ boundary tests ------------

def test_hardware_staleness_override_fresh() -> None:
    """Override to last_verified + 30 days -> FRESH."""
    from quirk.scanner.hardware_meta import HARDWARE_MATRIX, STALENESS_THRESHOLD_DAYS
    last_verified = datetime.date.fromisoformat(HARDWARE_MATRIX["last_verified"])
    fake_today = last_verified + datetime.timedelta(days=30)
    age = (fake_today - last_verified).days
    assert age <= STALENESS_THRESHOLD_DAYS


def test_hardware_staleness_override_stale() -> None:
    """Override to last_verified + 100 days -> STALE (age > 90)."""
    from quirk.scanner.hardware_meta import HARDWARE_MATRIX, STALENESS_THRESHOLD_DAYS
    last_verified = datetime.date.fromisoformat(HARDWARE_MATRIX["last_verified"])
    fake_today = last_verified + datetime.timedelta(days=100)
    age = (fake_today - last_verified).days
    assert age > STALENESS_THRESHOLD_DAYS
