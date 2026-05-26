"""GET /api/merge/latest — Phase 111 DASH-03: merged scan result with per-segment scores.

Returns the latest MergeRun row plus per-segment scores recomputed on read (Option A).
Read-only — no db.add/flush/commit anywhere in this module (Trap T6).

Security contract:
- Router-level Depends(require_auth) — no per-handler bypass possible (T-111-01).
- coverage_warning_json deserialization wrapped in try/except (T-111-03 / Trap T8).
- No SQL string interpolation — _assemble_union uses ORM only.
- No db writes (T-111-04 / Trap T6).
"""
from __future__ import annotations

import json
import logging
from collections import defaultdict
from typing import Dict, List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from quirk.dashboard.api.deps import get_db
from quirk.dashboard.api.middleware.auth import require_auth
from quirk.dashboard.api.schemas import MergeLatestData, MergeLatestResponse
from quirk.intelligence.evidence import build_evidence_summary
from quirk.intelligence.scoring import compute_readiness_score
from quirk.merge.scan import _assemble_union
from quirk.models import CryptoEndpoint, MergeRun

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Router — router-level auth (M2M read endpoint — T-111-01)
# ---------------------------------------------------------------------------
router = APIRouter(dependencies=[Depends(require_auth)])


# ---------------------------------------------------------------------------
# GET /api/merge/latest
# ---------------------------------------------------------------------------

@router.get("/merge/latest")
def get_merge_latest(db: Session = Depends(get_db)) -> dict:
    """GET /api/merge/latest — return latest MergeRun + per-segment Option-A scores.

    Graceful no-merge: returns {"merge": null} when no merge_run row exists.
    Per-segment recompute groups endpoints by ep.segment (NOT ep.sensor_id) — Trap T5.
    Read-only — never calls db.add/flush/commit — Trap T6.
    """
    # ------------------------------------------------------------------
    # Fetch latest MergeRun row (most recent by merged_at)
    # ------------------------------------------------------------------
    latest_run: MergeRun | None = (
        db.query(MergeRun).order_by(MergeRun.merged_at.desc()).first()
    )
    if latest_run is None:
        return MergeLatestResponse(merge=None).model_dump()

    # ------------------------------------------------------------------
    # Parse coverage_warning_json (Trap T8: malformed JSON → None, no 500)
    # ------------------------------------------------------------------
    coverage_warning = None
    if latest_run.coverage_warning_json is not None:
        try:
            coverage_warning = json.loads(latest_run.coverage_warning_json)
        except (ValueError, TypeError):
            logger.debug(
                "merge/latest: failed to parse coverage_warning_json for scan_id=%s",
                latest_run.scan_id,
            )

    # ------------------------------------------------------------------
    # Assemble endpoint union for per-segment recompute (read-only — T6)
    # ------------------------------------------------------------------
    endpoints: List[CryptoEndpoint] = _assemble_union(db)

    # ------------------------------------------------------------------
    # Per-segment recompute: group by ep.segment, NOT ep.sensor_id — Trap T5
    # One Option-A score per distinct non-null segment.
    # ------------------------------------------------------------------
    segment_eps: Dict[str, List[CryptoEndpoint]] = defaultdict(list)
    for ep in endpoints:
        if ep.segment is not None:
            segment_eps[ep.segment].append(ep)

    per_segment_scores: Dict[str, int] = {}
    for seg, eps in segment_eps.items():
        try:
            evidence = build_evidence_summary(eps, findings=None)
            result = compute_readiness_score(evidence)
            per_segment_scores[seg] = int(result["score"]) if result.get("score") is not None else 0
        except Exception:
            per_segment_scores[seg] = 0

    # ------------------------------------------------------------------
    # Build response
    # ------------------------------------------------------------------
    merge_data = MergeLatestData(
        scan_id=latest_run.scan_id,
        merged_at=latest_run.merged_at,
        score=latest_run.score,
        endpoint_count=latest_run.endpoint_count or 0,
        sensor_count=latest_run.sensor_count or 0,
        coverage_warning=coverage_warning,
        per_segment_scores=per_segment_scores,
    )
    return MergeLatestResponse(merge=merge_data).model_dump()
