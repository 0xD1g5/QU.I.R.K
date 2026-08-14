"""Phase 155 (HWLC-08/HWLC-09): curated hardware vendor EOL/EOS catalog.

Fourth instance of this codebase's curated-catalog + staleness-gate pattern,
following ``quirk/compliance/__init__.py`` (Phase 49), ``quirk/qramm/model_meta.py``
(Phase 51), ``quirk/scanner/hw_cve.py`` (Phase 142), and
``quirk/scanner/bacnet_vendors.py`` (Phase 147). Zero network calls at runtime,
stdlib only (``datetime``).

Cadence rationale (D-15): unlike CVE disclosures (``hw_cve.py``, 30-day cadence —
continuously published, high churn), vendor end-of-life / end-of-support dates
are infrequent, pre-scheduled lifecycle events announced via dedicated bulletins
months or years in advance. A 365-day re-verification cadence matches
``quirk/compliance/__init__.py``'s and ``quirk/scanner/bacnet_vendors.py``'s
precedent for this class of slow-moving, citation-backed data.

Shape (D-14): ``EOL_TABLE`` maps each ``(vendor, model)`` key to exactly ONE
dict — a physical device has a single EOL/EOS date pair, unlike CVEs which are
many-per-device. Lookup is EXACT-tuple only (``EOL_TABLE.get((vendor, model))``),
matching ``hw_cve.py``: no vendor-wildcard fallback, no case-normalization.
Vendor ``"Unknown"`` gating is the CALLER's responsibility, not this module's —
exactly as documented in ``hw_cve.py``.

``correlate_eol()`` parses ISO date strings to ``datetime.date`` internally
(fail-closed try/except -> ``None`` on any malformed value) and NEVER returns a
raw string (D-16) — a leaked string would raise ``TypeError`` when compared
inside ``quirk/scanner/hardware_tier.py``'s ``assign_tier()``
(``eol_date < _PQC_WINDOW_START``).

``eol_state()`` is a pure, stateless read-time classifier (D-17) — it has no
stored column and performs no I/O; callers invoke it fresh against whatever
``eol_date`` they already have in hand.

IMPORTANT (D-18): populating a real pre-2030 ``eol_date`` on a
``HardwareDevice`` (wired in plan 155-04) will cause
``quirk/scanner/hardware_tier.py::assign_tier()``'s existing
``eol_date < date(2030, 1, 1)`` check to return ``"Tier N/A"`` for that
device on its next scan. This is an INTENTIONAL, pre-existing interaction
(that override already existed before this catalog shipped) — not a bug
introduced by this module.

Catalog coverage note: this module ships 4 citation-backed ``(vendor, model)``
entries, not the plan's stated 6-entry target. Every additional candidate
pair considered (Juniper/JUNOS, HPE/iLO, Thales/Luna, Schneider Electric/M221,
Johnson Controls/Facility Explorer) was investigated during implementation but
had no independently fetchable, dated public lifecycle bulletin available at
verification time — per this module's fail-closed policy, an entry is never
added on a guessed or unverifiable date. The 4 shipped entries (F5 BIG-IP,
Fortinet FortiGate/FortiOS, Palo Alto PAN-OS, Cisco IOS/IOS-XE) were each
individually verified live against vendor-published or vendor-sourced release
lifecycle data on 2026-08-14 (see each entry's ``source_url``).
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Optional

# ---------------------------------------------------------------------------
# Staleness gate (D-15) — mirrors quirk/scanner/bacnet_vendors.py's 365-day
# cadence: infrequent, pre-scheduled vendor bulletins vs. hw_cve.py's 30-day
# continuously-disclosed CVE cadence.
# See CLAUDE.md "Staleness Review Cadence" for the re-verification bump
# procedure.
# ---------------------------------------------------------------------------
STALENESS_THRESHOLD_DAYS: int = 365

EOL_TABLE_META = {
    "last_verified": "2026-08-14",
    "source": "Vendor published end-of-life / end-of-support bulletins",
    "source_url": "https://endoflife.date/",
}


def is_eol_table_stale(today: Optional[datetime.date] = None) -> bool:
    """Returns True when the EOL/EOS snapshot has not been re-verified within
    ``STALENESS_THRESHOLD_DAYS`` (365) days of ``today`` (default: ``today()``).

    Boundary: ``age > STALENESS_THRESHOLD_DAYS`` (strict greater-than), so
    exactly 365 days is NOT stale — mirrors ``hw_cve.is_cve_table_stale()``'s
    and ``bacnet_vendors.is_bacnet_vendor_table_stale()``'s boundary semantics
    exactly.
    """
    reference = today or datetime.date.today()
    last_verified = datetime.date.fromisoformat(EOL_TABLE_META["last_verified"])
    age = (reference - last_verified).days
    return age > STALENESS_THRESHOLD_DAYS


# ---------------------------------------------------------------------------
# Curated EOL/EOS table (D-14, D-16) — per-entry builder mirrors hw_cve.py's
# _cve() and compliance's _pci().
# ---------------------------------------------------------------------------


def _eol(
    eol_date: Optional[str],
    eos_date: Optional[str],
    source_url: str,
    notes: str = "",
) -> dict:
    """Per-entry EOL/EOS builder. ``eol_date``/``eos_date`` are ISO date
    strings (or ``None`` when the vendor has not published that milestone) —
    parsing to ``datetime.date`` happens later, inside ``correlate_eol()``
    (D-16), never here."""
    return {
        "eol_date": eol_date,
        "eos_date": eos_date,
        "last_verified": EOL_TABLE_META["last_verified"],
        "source_url": source_url,
        "notes": notes,
    }


# Each entry independently verified live on 2026-08-14 against vendor-sourced
# release-lifecycle data (F5/Cisco/Palo Alto direct vendor documentation;
# Fortinet cross-verified via endoflife.date/fortios, which aggregates from
# Fortinet's official EOL bulletins). Keys use vendor/model tokens the scanner
# can actually produce (HARDWARE_MATRIX model_pattern captures) and/or keys
# that already exist in hw_cve.py::CVE_TABLE.
EOL_TABLE: dict = {
    ("F5", "BIG-IP"): _eol(
        eol_date="2024-12-31",
        eos_date=None,
        source_url=(
            "https://techdocs.f5.com/kb/en-us/products/big-ip_ltm/releasenotes/"
            "related/relnote-supplement-bigip-15-1-10.html"
        ),
        notes=(
            "BIG-IP TMOS 15.1.x LTS release train — F5 official release-notes/"
            "EOL supplement page. No separately published EOS milestone for "
            "this train distinct from end-of-life."
        ),
    ),
    ("Fortinet", "FortiGate"): _eol(
        eol_date="2030-01-25",
        eos_date="2028-07-25",
        source_url="https://endoflife.date/fortios",
        notes=(
            "FortiOS 7.6.x release train. eos_date is Fortinet's active-support "
            "cutoff (mainstream support end); eol_date is the hard end-of-life "
            "date. Cross-verified against Fortinet's official lifecycle "
            "bulletins via endoflife.date/fortios (fetched live 2026-08-14)."
        ),
    ),
    ("Palo Alto", "PAN-OS"): _eol(
        eol_date="2022-07-16",
        eos_date=None,
        source_url=(
            "https://docs.paloaltonetworks.com/pan-os/10-0/pan-os-release-notes/"
            "pan-os-10-0-addressed-issues/pan-os-10-0-12-h6-addressed-issues"
        ),
        notes="PAN-OS 10.0.x release train — Palo Alto Networks official release-notes page.",
    ),
    ("Cisco", "IOS"): _eol(
        eol_date="2024-07-30",
        eos_date="2023-01-30",
        source_url=(
            "https://www.cisco.com/c/en/us/products/collateral/ios-nx-os-software/"
            "ios-xe-17/ios-xe-17-6-x-eol.html"
        ),
        notes=(
            "IOS-XE 17.6 LTS release train. eos_date is Cisco's end-of-support "
            "milestone (last date for software maintenance releases); eol_date "
            "is the last-day-of-support end-of-life date."
        ),
    ),
}


# ---------------------------------------------------------------------------
# EolMatchResult + correlate_eol() (D-01..D-04 style join, mirrors
# hw_cve.py::CveMatchResult / correlate_device())
# ---------------------------------------------------------------------------


@dataclass
class EolMatchResult:
    """Result of a ``correlate_eol()`` call. ``eol_date``/``eos_date`` are
    real ``datetime.date`` objects (or ``None``) — never raw strings (D-16)."""

    eol_date: Optional[datetime.date] = None
    eos_date: Optional[datetime.date] = None
    attempted: bool = False
    source_url: Optional[str] = None


def _parse_iso_date(raw: Optional[str]) -> Optional[datetime.date]:
    """Fail-closed ISO-date parse — mirrors
    ``hardware_scanner.py::_apply_entry()``'s try/except pattern. Returns
    ``None`` on any malformed or missing value, never raises."""
    if not raw:
        return None
    try:
        return datetime.date.fromisoformat(raw)
    except (ValueError, TypeError):
        return None


def correlate_eol(vendor: Optional[str], model: Optional[str]) -> EolMatchResult:
    """Looks up ``(vendor, model)`` in ``EOL_TABLE`` (exact-tuple match only —
    no vendor-wildcard fallback, no case-normalization, mirroring
    ``hw_cve.correlate_device()``).

    NOTE: this function does NOT gate on ``vendor == "Unknown"`` — that skip
    decision is the CALL SITE's responsibility, exactly as documented in
    ``hw_cve.py``. Calling this with an unidentified/absent vendor or model
    (including ``model=None``) simply yields a no-match result here; it never
    raises.

    Returns an ``EolMatchResult`` with ``attempted=True`` always (this
    function was invoked and completed), and ``eol_date``/``eos_date`` as
    parsed ``datetime.date`` objects (``None`` on miss or malformed source
    data — fail-closed, D-16).
    """
    entry = EOL_TABLE.get((vendor, model))
    if entry is None:
        return EolMatchResult(eol_date=None, eos_date=None, attempted=True, source_url=None)

    return EolMatchResult(
        eol_date=_parse_iso_date(entry.get("eol_date")),
        eos_date=_parse_iso_date(entry.get("eos_date")),
        attempted=True,
        source_url=entry.get("source_url"),
    )


# ---------------------------------------------------------------------------
# eol_state() — pure read-time classifier (D-17). No stored column, no I/O.
# ---------------------------------------------------------------------------

# 12-month "approaching EOL" advisory window (D-17).
_APPROACHING_WINDOW_DAYS = 365


def eol_state(
    eol_date: Optional[datetime.date], today: Optional[datetime.date] = None
) -> Optional[str]:
    """Classifies ``eol_date`` relative to ``today`` (default: ``today()``)
    into one of ``"passed"`` | ``"approaching"`` | ``None`` (D-17).

    - ``eol_date is None`` -> ``None`` (nothing to classify).
    - ``eol_date < today`` -> ``"passed"``.
    - ``0 <= (eol_date - today).days <= 365`` -> ``"approaching"``.
    - otherwise (more than 365 days in the future) -> ``None``.

    Pure function — no I/O, no stored column, no side effects.
    """
    if eol_date is None:
        return None
    reference = today or datetime.date.today()
    if eol_date < reference:
        return "passed"
    delta_days = (eol_date - reference).days
    if 0 <= delta_days <= _APPROACHING_WINDOW_DAYS:
        return "approaching"
    return None


__all__ = [
    "STALENESS_THRESHOLD_DAYS",
    "EOL_TABLE_META",
    "EOL_TABLE",
    "EolMatchResult",
    "is_eol_table_stale",
    "correlate_eol",
    "eol_state",
]
