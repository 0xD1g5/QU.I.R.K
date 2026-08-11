"""Phase 147 (DRAIN-02, per user decision D-147-02-A option (a)): curated
BACnet vendor-ID -> vendor-name (+ model -> product-family) resolution.

Fourth instance of the curated-catalog + staleness-gate triad already
established by ``quirk/compliance/__init__.py`` (Phase 49),
``quirk/qramm/model_meta.py`` (Phase 51), and ``quirk/scanner/hw_cve.py``
(Phase 142). Zero network calls, stdlib only (``datetime``).

This module exists so BACnet's raw numeric vendorID (e.g. ``"5"``) resolves
to a real vendor name (``"Johnson Controls"``), and a raw model string
(e.g. ``"FX16"``) resolves to the product family QUIRK's curated CVE catalog
is keyed on (``"Facility Explorer"``), BEFORE ``quirk.scanner.hw_cve.
correlate_device()`` is ever called. Resolution is deliberately the CALL
SITE's responsibility (``quirk/scanner/hardware_scanner.py``'s BACnet Step 5
block) — this module never imports ``hw_cve`` and never gates anything
itself; it is a pair of pure lookup helpers.
"""
from __future__ import annotations

import datetime
from typing import Optional

# ASHRAE vendor-ID assignments are append-only and effectively immutable
# once issued — a long cadence is appropriate here, matching
# quirk/compliance/__init__.py's 365-day cadence (unlike CVE data, which
# churns much faster and uses a 30-day cadence in hw_cve.py).
# See CLAUDE.md "Staleness Review Cadence" for the re-verification bump
# procedure.
STALENESS_THRESHOLD_DAYS: int = 365

BACNET_VENDOR_TABLE_META = {
    "last_verified": "2026-08-11",
    "source": "ASHRAE/BACnet Committee",
    "source_url": "https://bacnet.org/assigned-vendor-ids/",
}


def is_bacnet_vendor_table_stale(today: Optional[datetime.date] = None) -> bool:
    """Returns True when the vendor-ID table has not been re-verified within
    ``STALENESS_THRESHOLD_DAYS`` (365) days of ``today`` (default: ``today()``).

    Boundary: ``age > STALENESS_THRESHOLD_DAYS`` (strict greater-than), so
    exactly 365 days is NOT stale — mirrors
    ``quirk.scanner.hw_cve.is_cve_table_stale``'s boundary semantics exactly.
    """
    reference = today or datetime.date.today()
    last_verified = datetime.date.fromisoformat(
        BACNET_VENDOR_TABLE_META["last_verified"]
    )
    age = (reference - last_verified).days
    return age > STALENESS_THRESHOLD_DAYS


# ---------------------------------------------------------------------------
# Curated vendor-ID table — a SUBSET, not the full 1000+-entry ASHRAE
# registry (Don't-Hand-Roll: no bulk ingestion). Vendor ID "5" is mandatory
# (resolves the existing hw_cve.py ("Johnson Controls", "Facility Explorer")
# CVE entry). Every entry here has been individually cross-checked against
# https://bacnet.org/assigned-vendor-ids/ at implementation time — an
# unverified numeric ID is never added, because a wrong guess silently
# mislabels a real device (worse than no label at all).
#
# Unknown/unrecognized vendor IDs are NOT an error — the call site falls
# back to the raw numeric string exactly as it did before this module
# existed (no regression path).
# ---------------------------------------------------------------------------
BACNET_VENDOR_TABLE: dict = {
    "5": "Johnson Controls",
}

# Maps (vendor_name, raw_model) -> CVE_TABLE product-family key. Mandatory
# entry: Johnson Controls FX16 field controllers register under the
# "Facility Explorer" / Tridium Niagara product family in JCI's documented
# CVE history — no NVD/CISA advisory names "FX16" directly (see
# quirk/scanner/hw_cve.py lines 122-129 for the full citation).
BACNET_MODEL_FAMILY_TABLE: dict = {
    ("Johnson Controls", "FX16"): "Facility Explorer",
}


def resolve_bacnet_vendor(vendor_id) -> Optional[str]:
    """Resolves a raw BACnet numeric vendor ID to a curated vendor name.

    Accepts either a string or an int (coerced via ``str()``). Returns
    ``None`` on a miss or on ``None`` input — never raises. The caller is
    responsible for falling back to the raw value when this returns
    ``None`` (preserves today's exact display behavior for unrecognized
    vendors).
    """
    if vendor_id is None:
        return None
    return BACNET_VENDOR_TABLE.get(str(vendor_id))


def resolve_bacnet_model_family(
    vendor_name: Optional[str], model: Optional[str]
) -> Optional[str]:
    """Resolves a (vendor_name, raw_model) pair to a curated CVE_TABLE
    product-family key. Returns ``None`` on a miss or on ``None`` input —
    never raises.
    """
    if vendor_name is None or model is None:
        return None
    return BACNET_MODEL_FAMILY_TABLE.get((vendor_name, model))


__all__ = [
    "STALENESS_THRESHOLD_DAYS",
    "BACNET_VENDOR_TABLE_META",
    "BACNET_VENDOR_TABLE",
    "BACNET_MODEL_FAMILY_TABLE",
    "is_bacnet_vendor_table_stale",
    "resolve_bacnet_vendor",
    "resolve_bacnet_model_family",
]
