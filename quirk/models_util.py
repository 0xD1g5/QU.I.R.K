"""Shared query helpers over ``quirk.models`` used by more than one call site.

Phase 154 WR-02: the "latest successful HardwareDevice row per (host, port)"
subquery + join + same-second tie-break dedupe block was hand-duplicated
verbatim across four call sites (dashboard findings/components projections,
merge/CBOM, CLI/PDF/DOCX report writer). Factoring it into a single helper
means there is now exactly one place that documents the
``HardwareDevice``-projection contract ("every reader filters on
``probe_status == 'success'``"), and exactly one place to unit-test the
tie-break/dedup logic instead of four.
"""

from __future__ import annotations

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from quirk.models import HardwareDevice


def latest_successful_hardware_devices(session: Session) -> list[HardwareDevice]:
    """Return one ``HardwareDevice`` row per ``(host, port)``: the most
    recent row with ``probe_status == "success"``.

    Phase 154 D-13/D-14: a currently-failing re-probe never displaces a
    device's last-known-good state — the device stays present with its most
    recent successful observation instead of vanishing. Pre-Phase-154 rows
    (``probe_status IS NULL``) are excluded until the device is re-scanned
    (D-06 append-only; no backfill). Scope is therefore "every device with a
    successful observation on record", not just the latest scan run —
    bounded by ``scan.hardware_history_retention_days``'s retention purge.

    Two rows for the same ``(host, port)`` can share an identical
    ``scanned_at`` (same-second writes); the highest-``id`` row is kept so
    the join never emits both (Phase 154 D-13 tie-break dedupe).

    Every writer of ``HardwareDevice`` must set ``probe_status`` for its
    rows to be visible here — see run_scan.py's SNMP-only bulk-fingerprint
    branch (Phase 154 CR-01) for the shape of a bug this contract catches.
    """
    latest_success = (
        session.query(
            HardwareDevice.host,
            HardwareDevice.port,
            func.max(HardwareDevice.scanned_at).label("max_ts"),
        )
        .filter(HardwareDevice.probe_status == "success")
        .group_by(HardwareDevice.host, HardwareDevice.port)
        .subquery()
    )
    devices = (
        session.query(HardwareDevice)
        .join(latest_success, and_(
            HardwareDevice.host == latest_success.c.host,
            HardwareDevice.port == latest_success.c.port,
            HardwareDevice.scanned_at == latest_success.c.max_ts,
        ))
        .all()
    )

    by_key: dict[tuple, HardwareDevice] = {}
    for device in devices:
        key = (device.host, device.port)
        if key not in by_key or device.id > by_key[key].id:
            by_key[key] = device
    return list(by_key.values())


def recent_successful_hardware_rows(session: Session, host: str, port: int, limit: int = 3) -> list[HardwareDevice]:
    """Return up to *limit* most recent ``HardwareDevice`` rows for one
    ``(host, port)``, newest first — the last M rows with
    ``probe_status == "success"`` (single home alongside
    ``latest_successful_hardware_devices()``, Phase 154 WR-02 lesson).
    Ordered ``scanned_at`` desc then ``id`` desc (highest-id tie-break).
    Extends LIMIT-1 to LIMIT M for Phase 155's N-of-M window (D-02).
    Returns ``[]`` when empty.
    """
    q = session.query(HardwareDevice).filter(HardwareDevice.host == host, HardwareDevice.port == port, HardwareDevice.probe_status == "success")
    return (
        q.order_by(HardwareDevice.scanned_at.desc(), HardwareDevice.id.desc())
        .limit(limit)
        .all()
    )
