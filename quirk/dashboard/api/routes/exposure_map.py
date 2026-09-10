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
    edges, returns ``ExposureMapResponse(nodes=[], edges=[])`` — both keys
    always present, never omitted, never fabricated (D-08). Any derivation
    error degrades to an advisory-empty response rather than a 500 that
    could leak internals (mirrors hardware_drift/scan.py bridge handling).
    """
    try:
        result = derive_exposure_map(db)
    except Exception:
        logger.exception("exposure-map derivation failed; returning advisory-empty response")
        return ExposureMapResponse(nodes=[], edges=[])

    nodes = [ExposureNode(**node) for node in result.get("nodes", [])]
    edges = [ExposureEdge(**edge) for edge in result.get("edges", [])]
    return ExposureMapResponse(nodes=nodes, edges=edges)
