"""QRAMM CRUD router — Phase 51 QRAMM-02.

Five endpoint families:
  POST   /api/qramm/sessions                       create session (201)
  GET    /api/qramm/sessions/{session_id}          read session (200/404)
  POST   /api/qramm/sessions/{session_id}/answers  bulk upsert answers (200/404)
  POST   /api/qramm/sessions/{session_id}/score    compute & persist score (200/404)
  DELETE /api/qramm/sessions/{session_id}          delete session + answers (204/404)

Per CONTEXT.md D-11: Pydantic models live inline (consistent with scan.py).
Per CONTEXT.md D-10: score endpoint persists computed score to score_json.
Per RESEARCH.md Pitfall 2: SQLite FK cascade is NOT enforced — DELETE
endpoint explicitly removes QRAMMAnswer rows first.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from quirk.errors import format_error

from fastapi import APIRouter, Depends, HTTPException, Query
from quirk.dashboard.api.middleware.auth import require_auth
from quirk.dashboard.api.middleware.csrf import require_csrf
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from quirk.dashboard.api.deps import get_db
from quirk.models import QRAMMAnswer, QRAMMProfile, QRAMMSession
from quirk.qramm.compliance_map import (
    FRAMEWORK_KEYS,
    PRACTICE_AREA_TO_DIMENSION,
    QRAMM_COMPLIANCE_WEIGHTS,
    SCANNER_COVERAGE,
    SCANNER_COVERAGE_STATUS,
)
from quirk.qramm.evidence_bridge import populate_cvi_suggestions
from quirk.qramm.model_meta import QRAMM_MODEL
from quirk.qramm.questions import QRAMM_QUESTIONS, get_question
from quirk.qramm.scoring import (
    compute_dimension_score,
    compute_overall_score,
    compute_practice_score,
)

router = APIRouter(dependencies=[Depends(require_auth), Depends(require_csrf)])
logger = logging.getLogger(__name__)


# ---------- Pydantic models (inline per D-11) ----------

class CreateSessionRequest(BaseModel):
    org_name: Optional[str] = Field(default=None, max_length=255)
    model_version: Optional[str] = Field(default=None, max_length=32)


class CreateSessionResponse(BaseModel):
    session_id: int
    org_name: Optional[str]
    created_at: Optional[str]
    status: str
    model_version: str


class SessionRead(BaseModel):
    session_id: int
    org_name: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]
    status: Optional[str]
    model_version: Optional[str]
    score: Optional[Dict[str, Any]] = None
    answers_count: int


class AnswerItem(BaseModel):
    question_number: int = Field(ge=1, le=120)
    answer_value: int = Field(ge=1, le=4)


class SaveAnswersRequest(BaseModel):
    answers: List[AnswerItem] = Field(max_length=120)


class SaveAnswersResponse(BaseModel):
    session_id: int
    saved_count: int
    total_answered: int


class ScoreRequest(BaseModel):
    # Range matches the spec and _compute_multiplier clamp (RESEARCH A4: 0.8–1.5).
    profile_multiplier: Optional[float] = Field(
        default=None,
        description="Profile risk multiplier. Valid range: [0.8, 1.5]. "
                    "Values outside this range return HTTP 400 (QRK-DASHBOARD-010).",
    )


# ---------- Phase 54 Plan 01: new Pydantic models ----------

class SessionSummary(BaseModel):
    session_id: int
    org_name: Optional[str]
    created_at: Optional[str]
    status: Optional[str]
    answers_count: int


class CreateProfileRequest(BaseModel):
    session_id: int
    industry: str
    org_size: str
    geographic_scope: str
    data_sensitivity: str
    regulatory_obligations: List[str]


class CreateProfileResponse(BaseModel):
    profile_id: int
    session_id: int
    multiplier: float


class DraftAnswerRequest(BaseModel):
    session_id: int
    question_number: int = Field(ge=1, le=120)
    answer_value: Optional[int] = Field(default=None, ge=1, le=4)
    evidence_note: Optional[str] = Field(default=None, max_length=2000)


class AnswerRead(BaseModel):
    question_number: int
    answer_value: Optional[int]
    suggested_answer: Optional[int]
    confirmed_at: Optional[str]
    evidence_note: Optional[str]


# ---------- Phase 55 Plan 01: compliance map model ----------

class ComplianceMapRow(BaseModel):
    practice_number: str            # e.g. "1.1-NIST_PQC" — practice_area + framework joined
    practice_area: str              # e.g. "1.1"
    dimension: str                  # "CVI" | "SGRM" | "DPE" | "ITR"
    framework: str                  # one of FRAMEWORK_KEYS
    static_weight: float            # 0.0 .. 1.0
    relevance_score: Optional[float]
    scanner_informed: bool
    # Phase 74-03 D-10 (WR-11): coverage status for this row's dimension.
    # 'covered' | 'partial' | 'pending' | 'n/a'. 'pending'/'n/a' rows are
    # excluded from the rollup; 'partial' contributes at half-weight.
    coverage_status: Optional[str] = None


# ---------- Phase 54 Plan 01: multiplier helper ----------

_INDUSTRY_BASE = {
    "financial_services": 1.20,
    "healthcare":         1.15,
    "government":         1.20,
    "technology":         1.05,
    "retail":             0.95,
    "energy":             1.10,
    "other":              1.00,
}
_SENSITIVITY_DELTA = {
    "public":              -0.10,
    "internal":             0.00,
    "confidential":         0.10,
    "restricted_secret":    0.20,
    "restricted":           0.20,  # alias
}


def _compute_multiplier(industry: str, data_sensitivity: str) -> float:
    """Compute profile risk multiplier from industry + data sensitivity (Phase 54 RESEARCH A4)."""
    base = _INDUSTRY_BASE.get(industry, 1.00)
    delta = _SENSITIVITY_DELTA.get(data_sensitivity, 0.0)
    value = base + delta
    # Clamp to spec range 0.8-1.5
    return max(0.8, min(1.5, round(value, 2)))


# ---------- Helpers ----------

def _now_iso() -> datetime:
    return datetime.now(timezone.utc)


def _iso_str(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt is not None else None


def _get_session_or_404(db: Session, session_id: int) -> QRAMMSession:
    session = db.get(QRAMMSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=format_error("DASHBOARD-009"))
    return session


# ---------- Endpoints ----------

@router.post("/qramm/sessions", status_code=201, response_model=CreateSessionResponse)
def create_session(
    payload: CreateSessionRequest,
    db: Session = Depends(get_db),
) -> CreateSessionResponse:
    now = _now_iso()
    model_version = payload.model_version or QRAMM_MODEL["qramm_version"]
    session = QRAMMSession(
        org_name=payload.org_name,
        created_at=now,
        updated_at=now,
        model_version=model_version,
        status="draft",
    )
    db.add(session)
    db.flush()  # Phase 53: get session.id without committing yet

    # Phase 53 (QRAMM-12): pre-create 30 blank CVI QRAMMAnswer rows so the bridge
    # can bulk-update them, and so the UI can render all 30 questions even when
    # the bridge skips silently (D-02).
    for q in QRAMM_QUESTIONS:
        if q["dimension"] != "CVI":
            continue
        db.add(QRAMMAnswer(
            session_id=session.id,
            question_number=q["question_number"],
            dimension=q["dimension"],
            practice_area=q["practice_area"],
            answer_value=None,
            suggested_answer=None,
        ))
    db.commit()
    db.refresh(session)

    # Phase 53 (QRAMM-12): synchronous evidence bridge — derives suggested_answer
    # for the 30 CVI rows from the SESSION_BRACKET scan cohort. Skips silently
    # (D-02) when no scan data exists. Errors are logged but do NOT prevent the
    # 201 response; the session is valid and caller always receives a session_id.
    try:
        populate_cvi_suggestions(session.id, db)
    except Exception:  # noqa: BLE001
        logger.exception(
            "evidence_bridge: failed to populate CVI suggestions for session %s; "
            "session created successfully with blank suggestions",
            session.id,
        )

    return CreateSessionResponse(
        session_id=session.id,
        org_name=session.org_name,
        created_at=_iso_str(session.created_at),
        status=session.status or "draft",
        model_version=session.model_version or model_version,
    )


@router.get("/qramm/sessions/{session_id}", response_model=SessionRead)
def read_session(session_id: int, db: Session = Depends(get_db)) -> SessionRead:
    session = _get_session_or_404(db, session_id)
    answers_count = (
        db.query(QRAMMAnswer)
        .filter(QRAMMAnswer.session_id == session_id, QRAMMAnswer.answer_value.isnot(None))
        .count()
    )
    score: Optional[Dict[str, Any]] = None
    if session.score_json:
        try:
            score = json.loads(session.score_json)
        except (TypeError, ValueError):
            score = None
    return SessionRead(
        session_id=session.id,
        org_name=session.org_name,
        created_at=_iso_str(session.created_at),
        updated_at=_iso_str(session.updated_at),
        status=session.status,
        model_version=session.model_version,
        score=score,
        answers_count=answers_count,
    )


@router.post("/qramm/sessions/{session_id}/answers", response_model=SaveAnswersResponse)
def save_answers(
    session_id: int,
    payload: SaveAnswersRequest,
    db: Session = Depends(get_db),
) -> SaveAnswersResponse:
    session = _get_session_or_404(db, session_id)
    saved = 0
    for item in payload.answers:
        meta = get_question(item.question_number)
        existing = (
            db.query(QRAMMAnswer)
            .filter(
                QRAMMAnswer.session_id == session_id,
                QRAMMAnswer.question_number == item.question_number,
            )
            .one_or_none()
        )
        if existing is None:
            db.add(
                QRAMMAnswer(
                    session_id=session_id,
                    question_number=item.question_number,
                    dimension=meta["dimension"],
                    practice_area=meta["practice_area"],
                    answer_value=item.answer_value,
                )
            )
        else:
            existing.answer_value = item.answer_value
            existing.dimension = meta["dimension"]
            existing.practice_area = meta["practice_area"]
            # Phase 53 D-09 (QRAMM-13/14): auto-confirm a suggested answer when
            # the human writes answer_value. Badge state (QRAMM-14) is implicit
            # in (suggested_answer IS NOT NULL AND answer_value IS NULL).
            if existing.suggested_answer is not None and item.answer_value is not None:
                existing.confirmed_at = _now_iso()
        saved += 1
    session.updated_at = _now_iso()
    db.commit()
    total_answered = (
        db.query(QRAMMAnswer)
        .filter(QRAMMAnswer.session_id == session_id, QRAMMAnswer.answer_value.isnot(None))
        .count()
    )
    return SaveAnswersResponse(
        session_id=session_id,
        saved_count=saved,
        total_answered=total_answered,
    )


@router.post("/qramm/sessions/{session_id}/score")
def score_session(
    session_id: int,
    payload: Optional[ScoreRequest] = None,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    # Validate multiplier BEFORE DB lookup so out-of-range values always return
    # 400 (not 404) regardless of whether the session exists (D-04/D-05/D-06).
    multiplier = (payload.profile_multiplier if payload and payload.profile_multiplier is not None else 1.0)
    if payload is not None and payload.profile_multiplier is not None:
        if not (0.8 <= multiplier <= 1.5):
            raise HTTPException(
                status_code=400,
                detail=format_error("DASHBOARD-010"),
            )
    session = _get_session_or_404(db, session_id)

    # Group answers by (dimension, practice_area)
    rows = (
        db.query(QRAMMAnswer)
        .filter(QRAMMAnswer.session_id == session_id, QRAMMAnswer.answer_value.isnot(None))
        .all()
    )
    if not rows:
        raise HTTPException(
            status_code=422,
            detail=format_error("DASHBOARD-011"),
        )
    practice_buckets: Dict[str, List[int]] = {}
    practice_to_dim: Dict[str, str] = {}
    for r in rows:
        practice_buckets.setdefault(r.practice_area, []).append(int(r.answer_value))
        practice_to_dim[r.practice_area] = r.dimension

    # Compute practice scores
    practice_scores: Dict[str, float] = {
        pa: compute_practice_score(vals) for pa, vals in practice_buckets.items()
    }

    # Group practice scores by dimension; apply weakest-link min()
    dim_to_practices: Dict[str, Dict[str, float]] = {"CVI": {}, "SGRM": {}, "DPE": {}, "ITR": {}}
    for pa, score in practice_scores.items():
        dim = practice_to_dim.get(pa)
        if dim in dim_to_practices:
            dim_to_practices[dim][pa] = score

    dimension_scores: Dict[str, float] = {}
    for dim, pmap in dim_to_practices.items():
        dimension_scores[dim] = compute_dimension_score(list(pmap.values())) if pmap else 0.0

    # Overall via scoring.compute_overall_score (applies multiplier + maturity)
    overall_block = compute_overall_score(dimension_scores, multiplier=multiplier)

    # Build per-dimension breakdown response
    dim_breakdown: Dict[str, Any] = {}
    for dim in ("CVI", "SGRM", "DPE", "ITR"):
        dim_breakdown[dim] = {
            "score": round(dimension_scores.get(dim, 0.0), 4),
            "weighted": overall_block["dimensions"][dim],
            "practices": dim_to_practices.get(dim, {}),
        }

    response: Dict[str, Any] = {
        "session_id": session_id,
        "overall": overall_block["overall"],
        "maturity": overall_block["maturity"],
        "dimensions": dim_breakdown,
        "profile_multiplier": float(multiplier),
    }

    # Persist
    session.score_json = json.dumps(response, default=str)
    session.status = "scored"
    session.updated_at = _now_iso()
    db.commit()
    return response


@router.delete("/qramm/sessions/{session_id}", status_code=204)
def delete_session(session_id: int, db: Session = Depends(get_db)) -> None:
    session = _get_session_or_404(db, session_id)
    # Phase 70 BLOCK-07/D-04: FK-safe ordering.
    session.profile_id = None
    db.flush()
    db.query(QRAMMProfile).filter(QRAMMProfile.session_id == session_id).delete()
    db.query(QRAMMAnswer).filter(QRAMMAnswer.session_id == session_id).delete()
    db.delete(session)
    db.commit()
    return None


# ---------- Phase 54 Plan 04: question catalog endpoint ----------

class QuestionItem(BaseModel):
    question_number: int
    dimension: str
    practice_area: str
    text: str
    maturity_labels: List[str]


@router.get("/qramm/questions", response_model=List[QuestionItem])
def list_questions() -> List[QuestionItem]:
    """Return the full 120-question QRAMM catalog (versioned constant from quirk.qramm.questions)."""
    return [QuestionItem(**q) for q in QRAMM_QUESTIONS]


# ---------- Phase 54 Plan 01: 4 new endpoints ----------

@router.get("/qramm/sessions", response_model=List[SessionSummary])
def list_sessions(db: Session = Depends(get_db), limit: int = Query(default=50, ge=1, le=200)) -> List[SessionSummary]:
    """Gap 1 — D-03: list assessment sessions, most-recent first (default limit 50).

    Uses a single GROUP BY subquery to count answered questions per session,
    replacing the previous N+1 per-session COUNT loop.
    """
    answered_sq = (
        db.query(
            QRAMMAnswer.session_id,
            func.count(QRAMMAnswer.id).label("cnt"),
        )
        .filter(QRAMMAnswer.answer_value.isnot(None))
        .group_by(QRAMMAnswer.session_id)
        .subquery()
    )
    rows = (
        db.query(QRAMMSession, func.coalesce(answered_sq.c.cnt, 0).label("answers_count"))
        .outerjoin(answered_sq, QRAMMSession.id == answered_sq.c.session_id)
        .order_by(QRAMMSession.created_at.desc(), QRAMMSession.id.desc())
        .limit(limit)
        .all()
    )
    return [
        SessionSummary(
            session_id=s.id,
            org_name=s.org_name,
            created_at=_iso_str(s.created_at),
            status=s.status,
            answers_count=count,
        )
        for s, count in rows
    ]


@router.post("/qramm/profiles", status_code=201, response_model=CreateProfileResponse)
def create_profile(
    payload: CreateProfileRequest,
    db: Session = Depends(get_db),
) -> CreateProfileResponse:
    """Gap 2 — QRAMM-09: upsert org profile, compute multiplier, link to session.

    Uses upsert semantics: if a profile row for this session already exists it
    is updated in-place rather than creating a second orphaned row.
    """
    session = _get_session_or_404(db, payload.session_id)
    multiplier = _compute_multiplier(payload.industry, payload.data_sensitivity)
    existing = (
        db.query(QRAMMProfile)
        .filter(QRAMMProfile.session_id == payload.session_id)
        .one_or_none()
    )
    if existing:
        existing.industry = payload.industry
        existing.org_size = payload.org_size
        existing.geographic_scope = payload.geographic_scope
        existing.data_sensitivity = payload.data_sensitivity
        existing.regulatory_obligations = json.dumps(payload.regulatory_obligations)
        existing.multiplier = multiplier
        db.commit()
        db.refresh(existing)
        return CreateProfileResponse(
            profile_id=existing.id,
            session_id=payload.session_id,
            multiplier=multiplier,
        )
    profile = QRAMMProfile(
        session_id=payload.session_id,
        industry=payload.industry,
        org_size=payload.org_size,
        geographic_scope=payload.geographic_scope,
        data_sensitivity=payload.data_sensitivity,
        regulatory_obligations=json.dumps(payload.regulatory_obligations),
        multiplier=multiplier,
        created_at=_now_iso(),
    )
    db.add(profile)
    db.flush()
    session.profile_id = profile.id
    db.commit()
    db.refresh(profile)
    return CreateProfileResponse(
        profile_id=profile.id,
        session_id=payload.session_id,
        multiplier=multiplier,
    )


@router.post("/qramm/assessment/draft", response_model=Dict[str, Any])
def draft_answer(
    payload: DraftAnswerRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Gap 3 — QRAMM-10: debounced single-answer upsert with auto-confirm on suggested."""
    _get_session_or_404(db, payload.session_id)
    meta = get_question(payload.question_number)
    existing = (
        db.query(QRAMMAnswer)
        .filter(
            QRAMMAnswer.session_id == payload.session_id,
            QRAMMAnswer.question_number == payload.question_number,
        )
        .one_or_none()
    )
    if existing is None:
        row = QRAMMAnswer(
            session_id=payload.session_id,
            question_number=payload.question_number,
            dimension=meta["dimension"],
            practice_area=meta["practice_area"],
            answer_value=payload.answer_value,
            evidence_note=payload.evidence_note,
        )
        db.add(row)
    else:
        if payload.answer_value is not None:
            existing.answer_value = payload.answer_value
        if payload.evidence_note is not None:
            existing.evidence_note = payload.evidence_note
        # D-04/D-05: set confirmed_at when consultant overrides a suggested answer
        if existing.suggested_answer is not None and payload.answer_value is not None:
            existing.confirmed_at = _now_iso()
    db.commit()
    return {"saved": True}


@router.get("/qramm/sessions/{session_id}/answers", response_model=List[AnswerRead])
def read_answers(session_id: int, db: Session = Depends(get_db)) -> List[AnswerRead]:
    """Gap 4 — QRAMM-10: return all answer rows for a session with suggested/confirmed state."""
    _get_session_or_404(db, session_id)
    rows = (
        db.query(QRAMMAnswer)
        .filter(QRAMMAnswer.session_id == session_id)
        .all()
    )
    return [
        AnswerRead(
            question_number=r.question_number,
            answer_value=r.answer_value,
            suggested_answer=r.suggested_answer,
            confirmed_at=_iso_str(r.confirmed_at),
            evidence_note=r.evidence_note,
        )
        for r in rows
    ]


# ---------- Phase 55 Plan 01: compliance map endpoint ----------

@router.get(
    "/qramm/sessions/{session_id}/compliance-map",
    response_model=List[ComplianceMapRow],
)
def get_compliance_map(
    session_id: int,
    db: Session = Depends(get_db),
) -> List[ComplianceMapRow]:
    """Phase 55 QRAMM-15: per-practice × per-framework relevance scores.

    Returns 96 rows (12 practice areas × 8 frameworks). When the session has
    no score_json, every row carries relevance_score=None (HTTP 200 — never
    404/409 per Phase 55 D-03). When scored, raw = static_weight ×
    dimension_score, capped at SCANNER_COVERAGE[dimension] × static_weight
    per Phase 55 D-07.
    """
    session = _get_session_or_404(db, session_id)

    score_data: Optional[Dict[str, Any]] = None
    if session.score_json:
        try:
            score_data = json.loads(session.score_json)
        except (TypeError, ValueError):
            score_data = None

    rows: List[ComplianceMapRow] = []
    # Sort practice areas for stable ordering across responses.
    for practice_area in sorted(QRAMM_COMPLIANCE_WEIGHTS.keys()):
        dimension = PRACTICE_AREA_TO_DIMENSION[practice_area]
        ceiling = SCANNER_COVERAGE.get(dimension, 0.0)
        scanner_informed = ceiling > 0.0
        # Phase 74-03 D-10 (WR-11): explicit coverage status.
        coverage_status = SCANNER_COVERAGE_STATUS.get(dimension)

        # Read raw dimension score (0.0–4.0 scale) — see Phase 55
        # RESEARCH Pitfall 2: read ["score"], NOT ["weighted"].
        dim_score: Optional[float] = None
        if score_data is not None:
            try:
                dim_score = float(
                    score_data["dimensions"][dimension]["score"]
                )
            except (KeyError, TypeError, ValueError):
                dim_score = None

        for framework in FRAMEWORK_KEYS:
            static_weight = float(
                QRAMM_COMPLIANCE_WEIGHTS[practice_area][framework]
            )
            if dim_score is None:
                relevance_score: Optional[float] = None
            elif coverage_status in ("pending", "n/a"):
                # Phase 74-03 D-10: pending / n/a rows excluded from rollup.
                relevance_score = None
            else:
                # Normalize dim_score from 0.0–4.0 to 0.0–1.0 before
                # multiplying by weight, so output stays in 0.0–1.0 range.
                normalized = dim_score / 4.0
                raw = static_weight * normalized
                cap = ceiling * static_weight
                relevance_score = min(raw, cap)
                # Phase 74-03 D-10a: 'partial' contributes at half-weight.
                if coverage_status == "partial":
                    relevance_score = relevance_score * 0.5

            rows.append(
                ComplianceMapRow(
                    practice_number=f"{practice_area}-{framework}",
                    practice_area=practice_area,
                    dimension=dimension,
                    framework=framework,
                    static_weight=static_weight,
                    relevance_score=relevance_score,
                    scanner_informed=scanner_informed,
                    coverage_status=coverage_status,
                )
            )

    return rows
