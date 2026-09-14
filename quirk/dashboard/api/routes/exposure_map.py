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
import os
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from quirk.dashboard.api.deps import get_db
from quirk.dashboard.api.middleware.auth import require_auth
from quirk.dashboard.api.schemas import ExposureEdge, ExposureMapResponse, ExposureNode
from quirk.intelligence.exposure_map import derive_exposure_map

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(require_auth)])


def _declared_crown_jewels() -> list:
    """Operator-declared crown jewels from config, or ``[]``.

    Mirrors the lazy-import + QUIRK_CONFIG_PATH + broad-except idiom
    `routes/jobs.py` already uses for `security.trusted_targets`.

    Fails to ``[]`` on ANY error, which is the honest direction for this field:
    an unreadable config must mark nothing rather than mark something
    arbitrary, and a crown-jewel badge is a claim about what the client cares
    about. Marking the wrong node is worse than marking none.
    """
    try:
        from quirk.config import load_config  # lazy import — avoids cycles

        cfg_path = os.environ.get("QUIRK_CONFIG_PATH", "./config.yaml")
        cfg = load_config(cfg_path)
        return list(getattr(cfg.assessment, "crown_jewels", None) or [])
    except Exception:
        logger.debug("crown-jewel declaration unreadable; marking none", exc_info=True)
        return []


@router.get("/exposure-map", response_model=ExposureMapResponse)
def get_exposure_map(
    scan_id: Optional[str] = Query(
        default=None,
        description="ISO timestamp scan_run_id to map; omit for the latest scan",
    ),
    db: Session = Depends(get_db),
) -> ExposureMapResponse:
    """GET /api/exposure-map — verified-only nodes/edges (MAP-02).

    Auth: inherited from router-level require_auth (do NOT add per-route).

    Without ``?scan_id=``: maps the LATEST scan. With it: maps that scan, so
    the map can be pinned to whichever scan another surface is displaying.
    Until 2026-09-14 this route aggregated every scan in the database, which
    rendered 1225 edges across 27 nodes on a 24-scan database — 32% of them
    self-edges and 95% duplicates — against 19 edges across 12 nodes for the
    single scan actually being shown.

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
        result = derive_exposure_map(
            db, scan_run_id=scan_id, crown_jewels=_declared_crown_jewels()
        )
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
