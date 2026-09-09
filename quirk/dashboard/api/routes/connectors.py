"""GET /api/connectors/availability — Phase 193 / Plan 04 (PARITY-02).

Auth-gated (T-193-14), matching the identical router construction
`config.effective_router` already uses. Exposes plan 01's
`connector_availability.probe_all_connectors()` helper as a JSON payload the
React Connectors panel (plan 07) uses to render each of the 25 connectors'
available/reason/install_hint, and that plan 06's submit-time 422 gate calls
the SAME underlying helper for (D-05/D-08) — this route never reimplements
the probe.

D-07: probed fresh on every request. No memoizing decorator, no module-scope
memoization, no dependency-based caching anywhere in this file.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from quirk.dashboard.api.connector_availability import probe_all_connectors
from quirk.dashboard.api.middleware.auth import require_auth
from quirk.dashboard.api.schemas import (
    ConnectorAvailabilityEntry,
    ConnectorAvailabilityResponse,
)

router = APIRouter(dependencies=[Depends(require_auth)])


@router.get(
    "/connectors/availability",
    response_model=ConnectorAvailabilityResponse,
)
def get_connector_availability() -> ConnectorAvailabilityResponse:
    """GET /api/connectors/availability — per-connector available/reason/
    install_hint for all 25 connectors (PARITY-02)."""
    try:
        # D-07: no cache — every call re-probes via probe_all_connectors().
        results = probe_all_connectors()
    except Exception as exc:
        # T-193-15: never surface the exception's message — a probe
        # traceback can contain filesystem paths or sys.path entries.
        raise HTTPException(
            status_code=500,
            detail="Connector availability probe failed",
        ) from exc

    entries = sorted(
        (
            ConnectorAvailabilityEntry(
                flag=result.flag,
                label=result.label,
                category=result.category,
                available=result.available,
                reason=result.reason,
                install_hint=result.install_hint,
            )
            for result in results.values()
        ),
        key=lambda entry: (entry.category, entry.label),
    )
    unavailable_count = sum(1 for entry in entries if entry.available is False)

    return ConnectorAvailabilityResponse(
        connectors=entries,
        unavailable_count=unavailable_count,
    )
