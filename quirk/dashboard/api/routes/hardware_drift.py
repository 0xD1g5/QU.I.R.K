"""GET /api/hardware/drift — read-only hardware lifecycle drift surface.

Phase 156 HWLC-10 / D-04: `/api/scan/latest` is already a large aggregate
payload every consumer pays for, and drift events have their own
time-window semantics (D-09/D-10), so they get a dedicated endpoint here;
the scan-pair-scoped block lives on `CompareResponse` in scan.py instead.

Advisory-only (T-156-04 / HWLC-11 firewall, machine-enforced by
tests/test_cve_score_guard.py): this module must never import the scoring
engine or the readiness-assessment module, and must never reference the
scoring-weights constant.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import distinct, func
from sqlalchemy.orm import Session

from quirk.dashboard.api.deps import get_db
from quirk.dashboard.api.middleware.auth import require_auth
from quirk.dashboard.api.schemas import HardwareDriftEventItem, HardwareDriftResponse
from quirk.models import HardwareDevice, HardwareDriftEvent
from quirk.models_util import latest_successful_hardware_devices
from quirk.scanner.hardware_drift import tier_direction

router = APIRouter(dependencies=[Depends(require_auth)])


def build_device_lookup(db: Session) -> dict[tuple[str, int], tuple[Optional[str], Optional[str]]]:
    """Builds a ``(host, port) -> (vendor, model)`` lookup once from
    ``latest_successful_hardware_devices()`` — a device whose most recent
    probe failed still returns its last-known-good vendor/model
    (Phase 154 D-13 invariant)."""
    rows = latest_successful_hardware_devices(db)
    return {(row.host, row.port): (row.vendor, row.model) for row in rows}


def serialize_drift_event(
    row: HardwareDriftEvent,
    lookup: dict[tuple[str, int], tuple[Optional[str], Optional[str]]],
) -> HardwareDriftEventItem:
    """Serializes one ``HardwareDriftEvent`` row into a
    ``HardwareDriftEventItem``, deriving ``direction`` via
    ``tier_direction()`` for tier_crossing events and ``"neutral"`` for
    every other event type. Never reimplements direction logic
    (RESEARCH.md Don't Hand-Roll)."""
    if row.event_type == "tier_crossing":
        raw_direction = tier_direction(row.old_value, row.new_value)
        direction = raw_direction if raw_direction in ("improved", "worsened") else "neutral"
    else:
        direction = "neutral"

    vendor, model = lookup.get((row.host, row.port), (None, None))

    return HardwareDriftEventItem(
        host=row.host,
        port=row.port,
        event_type=row.event_type,
        old_value=row.old_value,
        new_value=row.new_value,
        direction=direction,
        detected_at=row.detected_at.isoformat(),
        vendor=vendor,
        model=model,
    )


@router.get("/hardware/drift", response_model=HardwareDriftResponse)
def get_hardware_drift(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> HardwareDriftResponse:
    """GET /api/hardware/drift — latest-scan drift slice plus a bounded
    historical list (HWLC-10).

    Auth: inherited from router-level require_auth (do NOT add per-route).
    """
    latest_ts = db.query(func.max(HardwareDevice.scanned_at)).scalar()
    distinct_scans = db.query(func.count(distinct(HardwareDevice.scanned_at))).scalar()
    has_prior_scan = (distinct_scans or 0) >= 2

    if latest_ts is None:
        return HardwareDriftResponse(has_prior_scan=False)

    lookup = build_device_lookup(db)

    latest_rows = (
        db.query(HardwareDriftEvent)
        .filter(HardwareDriftEvent.detected_at == latest_ts)
        .order_by(HardwareDriftEvent.host, HardwareDriftEvent.port, HardwareDriftEvent.event_type)
        .all()
    )
    latest_events = [serialize_drift_event(row, lookup) for row in latest_rows]

    historical_rows = (
        db.query(HardwareDriftEvent)
        .filter(HardwareDriftEvent.detected_at < latest_ts)
        .order_by(HardwareDriftEvent.detected_at.desc())
        .limit(limit + 1)
        .all()
    )
    historical_truncated = len(historical_rows) > limit
    historical_events = [serialize_drift_event(row, lookup) for row in historical_rows[:limit]]

    return HardwareDriftResponse(
        has_prior_scan=has_prior_scan,
        latest_scan_at=latest_ts.isoformat(),
        latest_events=latest_events,
        historical_events=historical_events,
        historical_truncated=historical_truncated,
    )
