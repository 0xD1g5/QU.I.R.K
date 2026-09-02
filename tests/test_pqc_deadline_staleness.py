"""Phase 180-02 (CLOSE-03) — PQC deadline catalog staleness gate, override, and
boundary tests.

Mirrors tests/test_cve_staleness.py's shape (D-09/D-10/D-12 precedent) with
pqc_deadline names substituted. Every test function name here MUST contain the
substring "staleness" — CI's gate step filters with `-k "staleness or freshness"`,
so a differently-named test would be added to the file list and then silently
never run.
"""
from __future__ import annotations

import datetime
import os

# ---------------- table shape ----------------


def test_pqc_deadline_table_meta_shape_staleness() -> None:
    from quirk.scanner.pqc_deadlines import (
        PQC_DEADLINE_TABLE_META,
        STALENESS_THRESHOLD_DAYS,
    )

    required_keys = {"last_verified", "source", "source_url"}
    assert required_keys.issubset(PQC_DEADLINE_TABLE_META.keys()), (
        f"PQC_DEADLINE_TABLE_META missing required keys: "
        f"{required_keys - set(PQC_DEADLINE_TABLE_META.keys())}"
    )

    # last_verified must be a parseable ISO date.
    datetime.date.fromisoformat(PQC_DEADLINE_TABLE_META["last_verified"])

    assert isinstance(STALENESS_THRESHOLD_DAYS, int)
    assert STALENESS_THRESHOLD_DAYS == 90


# ---------------- staleness gate ----------------


def _check_staleness(today: datetime.date) -> int:
    from quirk.scanner.pqc_deadlines import PQC_DEADLINE_TABLE_META

    last_verified = datetime.date.fromisoformat(
        PQC_DEADLINE_TABLE_META["last_verified"]
    )
    return (today - last_verified).days


def test_pqc_deadline_table_not_stale_staleness() -> None:
    """Production gate: with no override, the current table must be FRESH."""
    from quirk.scanner.pqc_deadlines import (
        PQC_DEADLINE_TABLE_META,
        STALENESS_THRESHOLD_DAYS,
    )

    override = os.environ.get("QUIRK_CI_STALENESS_OVERRIDE_DATE")
    today = (
        datetime.date.fromisoformat(override) if override else datetime.date.today()
    )
    age = _check_staleness(today)
    assert age <= STALENESS_THRESHOLD_DAYS, (
        f"PQC_DEADLINE_TABLE_META.last_verified is {age} days old "
        f"(>{STALENESS_THRESHOLD_DAYS}). Re-verify against the Federal Register "
        f"source_url and bump last_verified in quirk/scanner/pqc_deadlines.py."
    )


def test_pqc_deadline_staleness_boundary_is_strict() -> None:
    """Exactly 90 days old is NOT stale; 91 days old IS stale (strict `>`)."""
    from quirk.scanner.pqc_deadlines import (
        PQC_DEADLINE_TABLE_META,
        STALENESS_THRESHOLD_DAYS,
        is_pqc_deadline_table_stale,
    )

    last_verified = datetime.date.fromisoformat(
        PQC_DEADLINE_TABLE_META["last_verified"]
    )
    fresh_boundary = last_verified + datetime.timedelta(
        days=STALENESS_THRESHOLD_DAYS
    )
    stale_boundary = last_verified + datetime.timedelta(
        days=STALENESS_THRESHOLD_DAYS + 1
    )
    assert is_pqc_deadline_table_stale(today=fresh_boundary) is False
    assert is_pqc_deadline_table_stale(today=stale_boundary) is True


# ---------------- CNSA 2.0 omission guard ----------------


def test_pqc_deadline_table_omits_cnsa_staleness() -> None:
    """No CNSA 2.0 date literal anywhere in the catalog's own values — the 403
    is recorded as a known gap in the module docstring, never papered over with
    a secondary-source date."""
    from quirk.scanner import pqc_deadlines

    forbidden_tokens = ("2033", "2035", "cnsa")
    for key, entry in pqc_deadlines.PQC_DEADLINES.items():
        for field_name, value in entry.items():
            if value is None:
                continue
            lowered = str(value).lower()
            for token in forbidden_tokens:
                assert token not in lowered, (
                    f"PQC_DEADLINES[{key!r}][{field_name!r}] contains forbidden "
                    f"token {token!r} — CNSA 2.0 dates must never be added "
                    f"(media.defense.gov 403s; see module docstring)."
                )
