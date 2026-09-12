"""GET /api/findings/{finding_id}/storyline — Phase 202 / Plan 03 (STORY-01).

Auth-gated (T-202-07), matching the identical router construction
`connectors.py` (Phase 193) already uses. Returns the narrative section of
one finding's storyline, assembled server-side from the existing Phase-99
`ALGO_IMPACT_MAP` / `REMEDIATION_CATALOG` catalogs (D-05) — no fourth
narrative generator, no new catalog content written here or anywhere in the
dashboard layer.

D-06: `FindingItem.id` IS `CryptoEndpoint.id`, reused across every finding
`findings_for_endpoint` derives from that one endpoint row — so `id` alone
would silently return the wrong finding's storyline. `title` is therefore a
REQUIRED query parameter and the (id, title) pair is the real lookup key,
resolved via `finding_by_id_and_title`.

D-07: a finding whose text carries no catalog keyword returns `narrative`,
`quantum_impact`, and `remediation_guidance` all `None` with a 200 — this is
the COMMON case (most TLS finding classes carry no algorithm keyword), not
an error.

This plan populates finding_id/narrative/quantum_impact/remediation_guidance
only. The six theme_*/finding_position fields stay `None` here — 202-05
fills them from the remediation-theme join.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from quirk.dashboard.api.deps import get_db
from quirk.dashboard.api.middleware.auth import require_auth
from quirk.dashboard.api.routes.scan import finding_by_id_and_title
from quirk.dashboard.api.schemas import FindingStoryline
from quirk.reports.content_model import ALGO_IMPACT_MAP, REMEDIATION_CATALOG, _classify_finding

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(require_auth)])

# T-202-08: fixed detail strings only. Never the exception's own message,
# never the submitted title, never a filesystem path — the connectors.py:38-44
# (T-193-15) precedent this whole pattern is copied from.
_DETAIL_NO_SUCH_ENDPOINT = "Finding not found"
_DETAIL_NO_SUCH_TITLE = "Finding not found for the given title"
_DETAIL_INTERNAL_ERROR = "Storyline lookup failed"


@router.get(
    "/findings/{finding_id}/storyline",
    response_model=FindingStoryline,
)
def get_finding_storyline(
    finding_id: int,
    title: str = Query(..., min_length=1, max_length=512),
    db: Session = Depends(get_db),
) -> FindingStoryline:
    """Return one finding's catalog-sourced storyline, keyed by (id, title).

    FastAPI's own `int` path coercion yields 422 on a non-numeric
    `finding_id`; the required `Query(...)` yields 422 on an omitted
    `title`. Neither is hand-validated here — no custom validator that
    would risk echoing the value back into an error message.
    """
    try:
        ep, finding = finding_by_id_and_title(db, finding_id, title)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 — deliberate catch-all, see T-202-08
        logger.exception("Storyline lookup failed for finding_id=%s", finding_id)
        raise HTTPException(status_code=500, detail=_DETAIL_INTERNAL_ERROR) from exc

    if ep is None:
        # No such CryptoEndpoint.id at all.
        raise HTTPException(status_code=404, detail=_DETAIL_NO_SUCH_ENDPOINT)
    if finding is None:
        # Endpoint exists, but no finding on it matches the given title —
        # a DIFFERENT fixed detail, distinguishable in logs/tests, still
        # containing neither the submitted title nor a path (T-202-09).
        raise HTTPException(status_code=404, detail=_DETAIL_NO_SUCH_TITLE)

    try:
        narrative: Optional[str] = None
        quantum_impact: Optional[str] = None
        remediation_guidance: Optional[str] = None

        # _classify_finding reads severity/title/description/category/
        # check_id (quirk/reports/content_model.py:690-710). FindingItem has
        # no `category` or `check_id` counterpart, so only the three fields
        # it actually carries are supplied.
        classify_input: Dict[str, Any] = {
            "severity": finding.severity,
            "title": finding.title,
            "description": finding.description or "",
        }
        crypto_class = _classify_finding(classify_input)

        if crypto_class is not None:
            # ALGO_IMPACT_MAP[key] is a 3-tuple:
            # (risk_label, impact_sentence, quantum_risk_sentence)
            # (quirk/reports/content_model.py:230-232).
            #
            # narrative: composed the same way the executive report composes
            # risk_label + impact_sentence — mirrors the markdown join at
            # quirk/reports/executive.py:432
            # (f"- **{risk.risk_label}** — {risk.impact_sentence}"), minus
            # the markdown emphasis since this is a plain-text API field.
            #
            # quantum_impact: index [2] verbatim — the same composition
            # findings_evaluator._build_finding uses for its own
            # `quantum_risk` field (quirk/engine/findings_evaluator.py:122-125).
            #
            # remediation_guidance: REMEDIATION_CATALOG[key] verbatim — the
            # same composition findings_evaluator._build_finding uses for its
            # own `recommendation` field when a catalog entry exists
            # (quirk/engine/findings_evaluator.py:115-116). No fallback
            # boilerplate (NIST_IR_8547_DEPRECATION) is appended here: that
            # branch only fires in _build_finding when there is NO catalog
            # match, which is exactly the case this route leaves as honest
            # `None` per D-07 rather than authoring new text.
            if crypto_class in ALGO_IMPACT_MAP:
                risk_label, impact_sentence, quantum_risk_sentence = ALGO_IMPACT_MAP[crypto_class]
                narrative = f"{risk_label} — {impact_sentence}"
                quantum_impact = quantum_risk_sentence
            if crypto_class in REMEDIATION_CATALOG:
                remediation_guidance = REMEDIATION_CATALOG[crypto_class]

        return FindingStoryline(
            finding_id=finding_id,
            narrative=narrative,
            quantum_impact=quantum_impact,
            remediation_guidance=remediation_guidance,
        )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 — deliberate catch-all, see T-202-08
        logger.exception("Storyline narrative assembly failed for finding_id=%s", finding_id)
        raise HTTPException(status_code=500, detail=_DETAIL_INTERNAL_ERROR) from exc
