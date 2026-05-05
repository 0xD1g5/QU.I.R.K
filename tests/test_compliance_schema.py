"""Phase 49 D-04 gate 1 (COMPLY-06): every COMPLIANCE_MAP entry has required
keys + ISO date + https:// source_url.
"""
from __future__ import annotations

import datetime

_REQUIRED = {"framework", "control", "version", "last_verified", "source_url"}


def test_module_imports():
    """quirk.compliance must export the 5 public symbols Plan 49-02 ships."""
    from quirk.compliance import (  # noqa: F401
        COMPLIANCE_MAP,
        UNMAPPED_TITLES,
        TITLE_PREFIX_ALIASES,
        STALENESS_THRESHOLD_DAYS,
        status_report,
    )


def test_every_entry_has_required_keys():
    from quirk.compliance import COMPLIANCE_MAP

    offenders: list[tuple[str, set[str]]] = []
    for title, entries in COMPLIANCE_MAP.items():
        for entry in entries:
            missing = _REQUIRED - set(entry.keys())
            if missing:
                offenders.append((title, missing))
    assert not offenders, (
        f"Compliance entries missing required keys: {offenders}. "
        f"Each entry must include {sorted(_REQUIRED)}."
    )


def test_last_verified_parses_as_iso_date():
    from quirk.compliance import COMPLIANCE_MAP

    offenders: list[tuple[str, str]] = []
    for title, entries in COMPLIANCE_MAP.items():
        for entry in entries:
            value = entry.get("last_verified", "")
            try:
                datetime.date.fromisoformat(value)
            except (TypeError, ValueError):
                offenders.append((title, value))
    assert not offenders, (
        f"Non-ISO last_verified dates: {offenders}. Use YYYY-MM-DD format."
    )


def test_source_url_is_https():
    from quirk.compliance import COMPLIANCE_MAP

    offenders: list[tuple[str, str]] = []
    for title, entries in COMPLIANCE_MAP.items():
        for entry in entries:
            url = entry.get("source_url", "")
            if not isinstance(url, str) or not url.startswith("https://"):
                offenders.append((title, url))
    assert not offenders, (
        f"source_url entries not using https://: {offenders}. "
        f"All citations must point to authoritative HTTPS URLs."
    )
