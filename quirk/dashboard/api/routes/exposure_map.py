"""GET /api/exposure-map — read-only quantum exposure map surface.

Phase 195 (MAP-02): exposes ``quirk.intelligence.exposure_map.derive_exposure_map``
over a stable, auth-gated JSON contract. The map tab's defensibility rests on
every edge being a VERIFIED relationship with cited evidence and zero
inference (D-03) — this route never adds its own logic on top of the
orchestrator, it only serializes the orchestrator's dict shape into typed
Pydantic models.

Advisory-only (D-10 firewall, machine-enforced by
tests/test_exposure_map_score_guard.py): this module must never import the
scoring engine or the readiness-assessment module, and must never reference
the scoring-weights constant.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from quirk.dashboard.api.deps import get_db
from quirk.dashboard.api.middleware.auth import require_auth
from quirk.dashboard.api.schemas import ExposureEdge, ExposureMapResponse, ExposureNode
from quirk.intelligence.exposure_map import derive_exposure_map

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(require_auth)])


@router.get("/exposure-map", response_model=ExposureMapResponse)
def get_exposure_map(db: Session = Depends(get_db)) -> ExposureMapResponse:
    """GET /api/exposure-map — verified-only nodes/edges (MAP-02).

    Auth: inherited from router-level require_auth (do NOT add per-route).

    Calls the importable ``derive_exposure_map`` orchestrator (never
    reimplements derivation logic route-side). When there are zero verified
    edges, returns ``ExposureMapResponse(nodes=[], edges=[])`` with
    ``unavailable_reason=None`` — both lists always present, never omitted,
    never fabricated (D-08). Any derivation OR serialization error degrades to
    a 200 whose ``unavailable_reason`` is set (WR-02) rather than a 500 that
    could leak internals; that field keeps a computation failure distinct from
    the honest-absence empty map so a bug never reads as "zero verified
    exposure" (mirrors hardware_drift/scan.py bridge handling).
    """
    try:
        result = derive_exposure_map(db)
        nodes = [ExposureNode(**node) for node in result.get("nodes", [])]
        edges = [ExposureEdge(**edge) for edge in result.get("edges", [])]
    except Exception:
        logger.exception("exposure-map derivation failed; surfacing as unavailable (not empty)")
        # WR-02: a failure must NOT collapse into the byte-identical honest-absence
        # empty map (D-08). Set unavailable_reason so the client can distinguish
        # "computation failed / not measured" from "zero verified exposure".
        return ExposureMapResponse(
            nodes=[],
            edges=[],
            unavailable_reason=(
                "Exposure-map derivation failed; this is a computation error, not a "
                "verified zero-exposure result. See the API server log for the cause."
            ),
        )

    return ExposureMapResponse(nodes=nodes, edges=edges)
