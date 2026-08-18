"""GET /api/hardware/drift — read-only hardware lifecycle drift surface.

Phase 156 HWLC-10 / D-04: `/api/scan/latest` is already a large aggregate
payload every consumer pays for, and drift events have their own
time-window semantics (D-09/D-10), so they get a dedicated endpoint here;
the scan-pair-scoped block lives on `CompareResponse` in scan.py instead.

Phase 160 HWLC-17: also hosts `GET /api/hardware/vendor-trends`, a
read-only, bounded, vendor-scoped projection of catalog-level PQC-status
trend events.

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
from quirk.dashboard.api.schemas import (
    HardwareDriftEventItem,
    HardwareDriftResponse,
    VendorPqcTrendEventItem,
    VendorPqcTrendResponse,
)
from quirk.models import HardwareDevice, HardwareDriftEvent, VendorPqcTrendEvent
from quirk.models_util import latest_successful_hardware_devices
from quirk.scanner.hardware_drift import tier_direction

router = APIRouter(dependencies=[Depends(require_auth)])


def build_device_lookup(
    db: Session,
) -> dict[tuple[str, int], tuple[Optional[str], Optional[str]]]:
    """Builds a ``(host, port) -> (vendor, model)`` lookup once from
    ``latest_successful_hardware_devices()`` — a device whose most recent
    probe failed still returns its last-known-good vendor/model (Phase 154
    D-13 invariant).

    Phase 159 WR-03 fix: this lookup is now scoped to vendor/model only.
    ``is_partial_scan`` is deliberately NOT sourced from here — a single
    current-state snapshot cannot correctly badge historical/windowed drift
    events (a later scan can supersede the device row and silently flip the
    badge for events that predate it). ``is_partial_scan`` is instead read
    directly off each ``HardwareDriftEvent`` row in ``serialize_drift_event``
    — captured at insert time by ``reconcile_device_history()`` from the
    probe that actually produced that specific event.
    """
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
    (RESEARCH.md Don't Hand-Roll).

    Phase 159 WR-03 fix: ``is_partial_scan`` is read directly off ``row``
    (the drift event itself, populated at insert time by
    ``reconcile_device_history()``) rather than joined through ``lookup``'s
    current-state device snapshot — see ``build_device_lookup()`` docstring.
    Coerced via ``bool(getattr(...))`` because the column is nullable with
    no DDL default (pre-fix rows read NULL -> False), never a bare
    ``row.is_partial_scan`` passthrough.
    """
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
        is_partial_scan=bool(getattr(row, "is_partial_scan", False)),
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
    # Phase 159 WR-01: scope the "latest" join to successful probes only.
    # HardwareDriftEvent.detected_at is always derived from a successful
    # probe's scanned_at (reconcile_device_history() only reconciles
    # recent_successful_hardware_rows()); a failed check-in probe in the
    # same batch can otherwise become the unfiltered global max and
    # silently blank this "latest" slice fleet-wide.
    latest_ts = (
        db.query(func.max(HardwareDevice.scanned_at))
        .filter(HardwareDevice.probe_status == "success")
        .scalar()
    )
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


def serialize_vendor_trend_event(row: VendorPqcTrendEvent) -> VendorPqcTrendEventItem:
    """Serializes one ``VendorPqcTrendEvent`` row into a
    ``VendorPqcTrendEventItem``. Pure field copy — no device lookup, since
    the row itself carries no host/port to enrich (vendor-scoped, Phase 160
    HWLC-17).
    """
    return VendorPqcTrendEventItem(
        vendor=row.vendor,
        event_type=row.event_type,
        old_value=row.old_value,
        new_value=row.new_value,
        detected_at=row.detected_at,
        confirmed_at=row.confirmed_at,
    )


@router.get("/hardware/vendor-trends", response_model=VendorPqcTrendResponse)
def get_vendor_pqc_trends(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> VendorPqcTrendResponse:
    """GET /api/hardware/vendor-trends — bounded, newest-first, vendor-scoped
    projection of ``vendor_pqc_trend_events`` (Phase 160 HWLC-17).

    Auth: inherited from router-level require_auth (do NOT add per-route).
    """
    rows = (
        db.query(VendorPqcTrendEvent)
        .order_by(VendorPqcTrendEvent.detected_at.desc(), VendorPqcTrendEvent.id.desc())
        .limit(limit + 1)
        .all()
    )
    truncated = len(rows) > limit
    events = [serialize_vendor_trend_event(r) for r in rows[:limit]]

    return VendorPqcTrendResponse(events=events, truncated=truncated)
