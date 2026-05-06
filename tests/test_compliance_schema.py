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


# ---------------------------------------------------------------------------
# Phase 52 COMPLY-11/12 — SOC2 + ISO 27001:2022 stubs (RED — fail until Plan 03)
# ---------------------------------------------------------------------------

def test_soc2_entries_present():
    """COMPLY-11 (D-05/D-06): COMPLIANCE_MAP must have >= 3 SOC2 CC6.x control IDs."""
    from quirk.compliance import COMPLIANCE_MAP
    cc6_controls = [
        entry["control"]
        for entries in COMPLIANCE_MAP.values()
        for entry in entries
        if entry.get("framework") == "SOC2 CC" and entry.get("control", "").startswith("CC6.")
    ]
    assert len(cc6_controls) >= 3, (
        f"Expected >= 3 SOC2 CC6.x control IDs, got {len(cc6_controls)}: {cc6_controls}"
    )


def test_iso_entries_present():
    """COMPLY-12 (D-07): COMPLIANCE_MAP must have >= 3 ISO 27001:2022 entries."""
    from quirk.compliance import COMPLIANCE_MAP
    iso_controls = [
        entry["control"]
        for entries in COMPLIANCE_MAP.values()
        for entry in entries
        if entry.get("framework") == "ISO 27001:2022"
    ]
    assert len(iso_controls) >= 3, (
        f"Expected >= 3 ISO 27001:2022 entries, got {len(iso_controls)}"
    )


def test_iso_rejects_legacy_control_ids():
    """COMPLY-12 (D-07): No ISO 27001:2013-style A.x.x control IDs allowed."""
    from quirk.compliance import COMPLIANCE_MAP
    offenders = [
        (title, entry["control"])
        for title, entries in COMPLIANCE_MAP.items()
        for entry in entries
        if entry.get("framework") == "ISO 27001:2022" and entry.get("control", "").startswith("A.")
    ]
    assert not offenders, (
        f"Legacy ISO 27001:2013 A.x.x control IDs found: {offenders}. "
        f"Use 8.x clause numbering (ISO 27001:2022)."
    )


def test_iso_version_string_exact():
    """COMPLY-12 (D-07): ISO version field must be exactly 'ISO 27001:2022'."""
    from quirk.compliance import COMPLIANCE_MAP
    offenders = [
        (title, entry.get("version"))
        for title, entries in COMPLIANCE_MAP.items()
        for entry in entries
        if entry.get("framework") == "ISO 27001:2022" and entry.get("version") != "ISO 27001:2022"
    ]
    assert not offenders, (
        f"ISO version field not exactly 'ISO 27001:2022': {offenders}"
    )
