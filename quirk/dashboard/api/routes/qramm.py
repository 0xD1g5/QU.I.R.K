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

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from quirk.dashboard.api.deps import get_db
from quirk.models import QRAMMAnswer, QRAMMSession
from quirk.qramm.evidence_bridge import populate_cvi_suggestions
from quirk.qramm.model_meta import QRAMM_MODEL
from quirk.qramm.questions import QRAMM_QUESTIONS, get_question
from quirk.qramm.scoring import (
    compute_dimension_score,
    compute_overall_score,
    compute_practice_score,
)

router = APIRouter()
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
    profile_multiplier: Optional[float] = Field(default=None, ge=0.5, le=2.0)


# ---------- Helpers ----------

def _now_iso() -> datetime:
    return datetime.now(timezone.utc)


def _iso_str(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt is not None else None


def _get_session_or_404(db: Session, session_id: int) -> QRAMMSession:
    session = db.get(QRAMMSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
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
    session = _get_session_or_404(db, session_id)
    multiplier = (payload.profile_multiplier if payload and payload.profile_multiplier is not None else 1.0)

    # Group answers by (dimension, practice_area)
    rows = (
        db.query(QRAMMAnswer)
        .filter(QRAMMAnswer.session_id == session_id, QRAMMAnswer.answer_value.isnot(None))
        .all()
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
    # Explicit cascade — SQLite FK enforcement is per-connection PRAGMA only.
    db.query(QRAMMAnswer).filter(QRAMMAnswer.session_id == session_id).delete()
    db.delete(session)
    db.commit()
    return None
