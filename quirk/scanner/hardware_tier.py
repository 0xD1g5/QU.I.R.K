"""CNSA 2.0 remediation tier assignment for hardware devices — Phase 128 (HWCOMPAT-04).

Pure function ``assign_tier()`` maps a HardwareDevice ORM object to one of four
consulting-grade tiers (D-05) with a confidence cap at Tier 2 for low/unknown
fingerprints (D-04 HWCOMPAT-CONFIDENCE-CAP).

Hardware tier assignment is advisory-only: no counter is added to SCORE_WEIGHTS
and ``compute_readiness_score()`` is not modified (D-01 / D-06 HWCOMPAT-SCORE-LOCK).

Phase 128 — HWCOMPAT-04.
"""
from __future__ import annotations

import logging
from datetime import date as _date

from quirk.models import HardwareDevice

_LOG = logging.getLogger(__name__)

# PQC migration window boundary (D-05: EOL before 2030 → Tier N/A)
_PQC_WINDOW_START = _date(2030, 1, 1)


def assign_tier(device: HardwareDevice) -> str:
    """Return CNSA-2.0 remediation tier for *device* (D-05, D-04).

    Pure function — no DB calls, no I/O, no side effects.
    Confidence cap: low/unknown confidence → Tier 2 max (D-04 HWCOMPAT-CONFIDENCE-CAP).

    Returns one of: ``"Tier 1"`` | ``"Tier 2"`` | ``"Tier 3"`` | ``"Tier N/A"``

    Tier taxonomy (D-05):
    - Tier N/A  — EOL date already passed OR EOL before 2030 (checked first, wins)
    - Tier 1    — pqc_status=unsupported, no EOL path, confidence >= medium
    - Tier 2    — pqc_status=partial; or unsupported with low/unknown confidence (cap);
                  or VENDOR-SILENT with confidence < high (conservative)
    - Tier 3    — pqc_status=supported; or VENDOR-SILENT + high confidence
    """
    # Use __dict__ for safe attribute access — works on both live ORM instances
    # (SQLAlchemy populates __dict__ on load) and test fixtures that set __dict__
    # directly via HardwareDevice.__new__ without mapper instrumentation.
    _d = device.__dict__ if hasattr(device, "__dict__") else {}
    confidence = (_d.get("confidence") or getattr(device, "confidence", None) or "unknown").lower()
    pqc_status = (_d.get("pqc_status") or getattr(device, "pqc_status", None) or "unknown").lower()
    eol_date   = _d.get("eol_date") if "eol_date" in _d else getattr(device, "eol_date", None)

    # --- 1. Tier N/A: EOL already passed or EOL before PQC migration window (D-05) ---
    if eol_date is not None and eol_date < _PQC_WINDOW_START:
        return "Tier N/A"

    # --- 2. D-04 confidence cap: low/unknown → Tier 2 max ---
    #    Exception: pqc_status=supported still earns Tier 3 even at low confidence.
    if confidence in ("low", "unknown"):
        if pqc_status == "supported":
            return "Tier 3"
        return "Tier 2"

    # --- 3. Full tier logic for medium/high confidence (D-05) ---
    if pqc_status == "supported":
        return "Tier 3"

    if pqc_status == "vendor-silent":
        # Conservative per CONTEXT.md D-43 edge: high confidence → Tier 3, else Tier 2
        return "Tier 3" if confidence == "high" else "Tier 2"

    if pqc_status == "partial":
        return "Tier 2"

    if pqc_status == "unsupported":
        return "Tier 1"

    # Conservative fallback for unrecognised pqc_status values
    return "Tier 2"
