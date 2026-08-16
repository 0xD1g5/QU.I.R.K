"""Phase 157 (HWLC-18): render-time-only EOL/tier forecast narrative.

D-01 forward-only: this module reads ONLY the current ``HardwareDevice``
snapshot projection passed in as plain dicts (the same shape
``quirk/reports/writer.py`` already builds); it makes NO retrospective
claims and never reads drift-event history. That is why ROADMAP success
criterion #5 ("the forecast never implies visibility into a period the
retention sweep has already purged") holds BY CONSTRUCTION rather than by
coordination with the drift-event retention purge (Plan 157-01) — this
module has no database session at all, so it physically cannot reach
purged rows. Future contributors: adding a read of drift-event history
here reintroduces that coupling risk. Do not do it.

Advisory-only: this module never feeds the readiness score. It never
references the scoring engine's weight table and never imports the
scoring module.

Pure, no-I/O module — imports only ``datetime``, ``typing``, and
``EOL_TABLE_META`` / ``is_eol_table_stale`` from
``quirk.scanner.hardware_eol`` (plus ``TIER_ORDER`` from
``quirk.scanner.hardware_tier`` for deterministic tier ordering).
"""
from __future__ import annotations

import datetime
from typing import Optional

from quirk.scanner.hardware_eol import EOL_TABLE_META, is_eol_table_stale
from quirk.scanner.hardware_tier import TIER_ORDER

# ---------------------------------------------------------------------------
# Bucket definitions — ordered (label, low_days, high_days_or_None).
# "already passed" is handled separately (eol_date < today) and always
# emitted first when populated.
# ---------------------------------------------------------------------------
_FORECAST_BUCKETS = (
    ("0-3 months", 0, 90),
    ("3-6 months", 91, 180),
    ("6-12 months", 181, 365),
    ("12+ months", 366, None),
)

_ALREADY_PASSED_LABEL = "already passed"

# Deterministic tier fragment ordering for bucket sentences — mirrors
# TIER_ORDER's severity ranking rather than dict-insertion order.
_TIER_LABEL_ORDER = tuple(
    sorted(TIER_ORDER, key=lambda label: TIER_ORDER[label])
)


def _parse_eol(raw) -> Optional[datetime.date]:
    """Fail-closed EOL-date parse. Accepts an ISO string or a ``date``
    object; returns ``None`` on any missing/unparseable input, never
    raises. ``writer.py`` hands over ISO strings; direct ORM callers might
    hand over ``date`` objects."""
    if raw is None:
        return None
    if isinstance(raw, datetime.date):
        return raw
    try:
        return datetime.date.fromisoformat(raw)
    except (ValueError, TypeError):
        return None


def _bucket_for_eol(eol_date: datetime.date, today: datetime.date) -> str:
    """Classifies *eol_date* relative to *today* into a bucket label.
    Mirrors ``hardware_eol.eol_state()``'s date-math shape."""
    if eol_date < today:
        return _ALREADY_PASSED_LABEL
    delta_days = (eol_date - today).days
    for label, low_days, high_days in _FORECAST_BUCKETS:
        if high_days is None:
            if delta_days >= low_days:
                return label
        elif low_days <= delta_days <= high_days:
            return label
    # Defensive fallback — should be unreachable given the bucket table
    # above covers [0, inf).
    return "12+ months"


def _bucket_sentence(label: str, tier_counts: dict, last_verified: str) -> str:
    """Builds one hedged sentence carrying the total count, the tier
    breakdown, and the inline catalog citation. Never uses the unqualified
    word "will"."""
    count = sum(tier_counts.values())
    tier_fragments = [
        f"{tier_counts[tier]} {tier}"
        for tier in _TIER_LABEL_ORDER
        if tier_counts.get(tier)
    ]
    tier_breakdown = ", ".join(tier_fragments)
    citation = f"based on vendor-published dates verified as of {last_verified}"

    device_word = "device" if count == 1 else "devices"

    if label == _ALREADY_PASSED_LABEL:
        return (
            f"{count} {device_word} ({tier_breakdown}) have already passed "
            f"their vendor-published end-of-life date, {citation}."
        )

    verb = "is projected to" if count == 1 else "are projected to"
    return (
        f"{count} {device_word} ({tier_breakdown}) {verb} reach vendor "
        f"end-of-life within {label}, {citation}."
    )


__all__ = ["build_eol_forecast"]


def build_eol_forecast(devices: list, today: Optional[datetime.date] = None) -> dict:
    """Builds a bucketed, tier-annotated, hedged, catalog-cited 12-month EOL
    forecast from *devices* — a list of plain dicts matching
    ``quirk/reports/writer.py``'s device-row shape (at minimum
    ``remediation_tier`` and ``eol_date`` keys).

    Returns a dict with exactly these keys:
        "narrative": str            — joined hedged prose, "" when no
                                       bucket populated
        "buckets": list[dict]       — ordered, one entry per NON-EMPTY
                                       bucket, each
                                       {"label", "count", "tier_counts",
                                        "sentence"}
        "catalog_last_verified": str
        "catalog_stale": bool
        "total_devices_with_eol": int
    """
    reference = today or datetime.date.today()

    # bucket_label -> tier_label -> count, insertion-ordered by first
    # occurrence but re-ordered deterministically at emission time.
    bucket_tier_counts: dict = {}
    total_devices_with_eol = 0

    for device in devices:
        eol_date = _parse_eol(device.get("eol_date"))
        if eol_date is None:
            continue
        total_devices_with_eol += 1

        tier = device.get("remediation_tier") or "Tier N/A"
        label = _bucket_for_eol(eol_date, reference)
        tier_counts = bucket_tier_counts.setdefault(label, {})
        tier_counts[tier] = tier_counts.get(tier, 0) + 1

    last_verified = EOL_TABLE_META["last_verified"]
    ordered_labels = (_ALREADY_PASSED_LABEL,) + tuple(
        label for label, _low, _high in _FORECAST_BUCKETS
    )

    buckets = []
    sentences = []
    for label in ordered_labels:
        tier_counts = bucket_tier_counts.get(label)
        if not tier_counts:
            continue
        sentence = _bucket_sentence(label, tier_counts, last_verified)
        buckets.append(
            {
                "label": label,
                "count": sum(tier_counts.values()),
                "tier_counts": dict(tier_counts),
                "sentence": sentence,
            }
        )
        sentences.append(sentence)

    return {
        "narrative": " ".join(sentences),
        "buckets": buckets,
        "catalog_last_verified": last_verified,
        "catalog_stale": is_eol_table_stale(today),
        "total_devices_with_eol": total_devices_with_eol,
    }
