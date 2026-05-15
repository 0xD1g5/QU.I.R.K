"""Phase 77 D-11 / cbom-intel-reports/IN-05 — baseline-governance item must
be emitted BOTH when no baseline-governance item exists AND when total
item count < min_items.

Baseline-governance item title: "Establish crypto governance review"
"""
from __future__ import annotations

from typing import Any, Dict

from quirk.intelligence.roadmap import build_phased_roadmap


_GOVERNANCE_TITLE = "Establish crypto governance review"


def _evidence_with_many_drivers() -> Dict[str, Any]:
    """Evidence shape that drives >= min_items non-baseline candidates."""
    return {
        "totals": {"endpoints": 100},
        "certificates": {
            "expiring_30d": 5,
            "self_signed": 3,
        },
        "tls": {
            "legacy_versions": 5,
            "enum_coverage_pct": 50.0,
        },
        "auth": {
            "rsa_only": 10,
            "mtls_present": 2,
        },
    }


def _minimal_evidence() -> Dict[str, Any]:
    return {"totals": {"endpoints": 50}}


def _scoring() -> Dict[str, Any]:
    return {"drivers": []}


def test_governance_item_added_when_below_min_items() -> None:
    """Path A: total items < min_items — governance baseline must appear."""
    result = build_phased_roadmap(_minimal_evidence(), _scoring(), min_items=6)
    titles = [item["title"] for item in result["items"]]
    assert _GOVERNANCE_TITLE in titles, (
        "Phase 77 D-11: baseline-governance must be emitted when len(items) < min_items "
        "(cbom-intel-reports/IN-05)"
    )


def test_governance_item_added_when_missing_even_above_min_items() -> None:
    """Path B: count >= min_items but no governance item — must still add it."""
    # Force min_items=1 so the candidate-driver loop alone satisfies the count;
    # then assert the governance item is STILL present (D-11 OR clause).
    result = build_phased_roadmap(_evidence_with_many_drivers(), _scoring(), min_items=1)
    titles = [item["title"] for item in result["items"]]
    assert _GOVERNANCE_TITLE in titles, (
        "Phase 77 D-11: baseline-governance must be emitted whenever it is missing, "
        "even when total item count >= min_items (cbom-intel-reports/IN-05)"
    )
