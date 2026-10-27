"""Phase 77-03 D-16 (api-cli-core/IN-01): QrammScoreResponse Pydantic model.

RESEARCH C-2 / Discretion D-16: narrow `Dict[str, Any]` -> `QrammScoreResponse` for
the public score endpoint only. Full TypedDict migration deferred to v5.0 per
CONTEXT Deferred Ideas.
"""
from __future__ import annotations

import inspect as _pyinspect

from pydantic import BaseModel


def test_qramm_score_response_model_exists() -> None:
    """D-16: QrammScoreResponse must be defined and subclass Pydantic BaseModel."""
    from quirk.dashboard.api.routes.qramm import QrammScoreResponse  # noqa: WPS433

    assert _pyinspect.isclass(QrammScoreResponse)
    assert issubclass(QrammScoreResponse, BaseModel)


def test_qramm_score_response_has_canonical_fields() -> None:
    """D-16: response model must mirror the keys produced by score_session.

    Canonical keys built at routes/qramm.py:424-430:
      session_id, overall, maturity, dimensions, profile_multiplier.
    """
    from quirk.dashboard.api.routes.qramm import QrammScoreResponse  # noqa: WPS433

    fields = set(QrammScoreResponse.model_fields.keys())
    expected = {"session_id", "overall", "maturity", "dimensions", "profile_multiplier"}
    # Phase 234 D-14 / D-15 (SCORE-10): four fields added ("N of 4 assessed"
    # disclosure and the answered counts persisted for stale detection).
    expected |= {
        "answered_by_dimension",
        "assessed_dimensions",
        "dimensions_assessed",
        "dimensions_total",
    }
    missing = expected - fields
    assert not missing, f"QrammScoreResponse missing fields: {missing}"


def test_qramm_score_response_overall_is_optional() -> None:
    """Phase 234 D-14: overall is None when no dimension is assessed, so the
    model must accept None (and still accept a float)."""
    from quirk.dashboard.api.routes.qramm import QrammScoreResponse  # noqa: WPS433

    base = {
        "session_id": 1,
        "maturity": "Indeterminate",
        "dimensions": {},
        "profile_multiplier": 1.0,
        "answered_by_dimension": {"CVI": 0, "SGRM": 0, "DPE": 0, "ITR": 0},
        "assessed_dimensions": [],
        "dimensions_assessed": 0,
        "dimensions_total": 4,
    }
    assert QrammScoreResponse(overall=None, **base).overall is None
    assert QrammScoreResponse(overall=0.6667, **base).overall == 0.6667


def test_score_endpoint_declares_response_model() -> None:
    """D-16: @router.post('/qramm/sessions/{session_id}/score') must declare
    response_model=QrammScoreResponse (AST/source gate)."""
    import pathlib

    src = pathlib.Path("quirk/dashboard/api/routes/qramm.py").read_text(encoding="utf-8")
    # Single canonical assertion: the score decorator must carry the response_model kwarg.
    assert "response_model=QrammScoreResponse" in src, (
        "D-16: @router.post('/qramm/sessions/{session_id}/score') must declare "
        "response_model=QrammScoreResponse"
    )
