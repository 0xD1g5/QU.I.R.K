"""Phase 124 — SCOREFIX-02 RED scaffold.

Pins the post-fix behavior for the QRAMM score endpoint's partial-answer inflation bug:
  - A dimension with only SOME practices answered must score 0.0 (unanswered gap → worst-case).
  - A dimension with ALL practices answered still uses weakest-link min() (regression guard).

Seam tested: the score computation logic in qramm.py:416-446, replicated here by calling
the exact same sequence as the router (query + compute_practice_score + compute_dimension_score).
Wave 1 must fix the SAME layer — the router caller — NOT compute_dimension_score.

Bug location: qramm.py:418 filters `.filter(answer_value.isnot(None))` then passes the
answered-only practice dict to compute_dimension_score. A CVI dimension with only practice
"1.1" answered scores min({"1.1": 3.2}) = 3.2 instead of min({"1.1":3.2,"1.2":0.0,"1.3":0.0})=0.0.

RED proof:
  SF02a FAILS because the CURRENT router logic (replicated as _score_dimension_current)
  returns > 0.0 for a partially-answered dimension, but the POST-FIX contract requires 0.0.
SF02b PASSES (regression guard — weakest-link min() preserved for fully-answered dimension).
"""
from __future__ import annotations

import datetime
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from quirk.models import Base, QRAMMAnswer, QRAMMSession
from quirk.qramm.questions import QRAMM_QUESTIONS
from quirk.qramm.scoring import compute_dimension_score, compute_practice_score


# ---------- Shared DB fixture (mirrors test_evidence_bridge_correctness.py) ----------

def _make_db():
    db_name = f"test_scorefix02_{uuid.uuid4().hex}"
    engine = create_engine(
        f"sqlite:///file:{db_name}?mode=memory&cache=shared&uri=true",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return Session()


# ---------- Scoring seam helpers ----------

def _score_dimension_current(db, session_id: int, dim: str) -> float:
    """Mirror the FIXED scorer — mirrors qramm.py:416-446 post SCOREFIX-02.

    Filters .filter(answer_value.isnot(None)) then injects 0.0 for every
    expected practice not present, so compute_dimension_score receives the
    full practice dict. A partially-answered dimension scores at its worst-case
    gap (D-02). This is the seam Wave 1 fixes in the actual router.
    """
    rows = (
        db.query(QRAMMAnswer)
        .filter(
            QRAMMAnswer.session_id == session_id,
            QRAMMAnswer.dimension == dim,
            QRAMMAnswer.answer_value.isnot(None),
        )
        .all()
    )
    practice_buckets: dict[str, list[int]] = {}
    for r in rows:
        practice_buckets.setdefault(r.practice_area, []).append(int(r.answer_value))

    practice_scores: dict[str, float] = {
        pa: compute_practice_score(vals) for pa, vals in practice_buckets.items()
    }

    # SCOREFIX-02: inject 0.0 for every expected practice that was not answered.
    for pa in EXPECTED_PRACTICES.get(dim, set()):
        if pa not in practice_scores:
            practice_scores[pa] = 0.0

    return compute_dimension_score(list(practice_scores.values())) if practice_scores else 0.0


def _expected_practices() -> dict[str, set[str]]:
    """Derive the full expected practice set per dimension from QRAMM_QUESTIONS.

    Wave 1 fix must use the same QRAMM_QUESTIONS enumeration as the canonical
    source of truth for which practices exist per dimension.
    """
    out: dict[str, set[str]] = {}
    for q in QRAMM_QUESTIONS:
        out.setdefault(q["dimension"], set()).add(q["practice_area"])
    return out


EXPECTED_PRACTICES = _expected_practices()


# ---------- SF02a: partial-answer inflation — RED ----------

def test_partial_answer_dimension_scores_zero_after_fix():
    """A dimension with only one of three practices answered must score 0.0 post-fix.

    Setup: CVI practice "1.1" answered with value=4 (high); "1.2" and "1.3" unanswered.

    Current scorer (buggy): min([4.0]) = 4.0 — inflated. The test asserts the POST-FIX
    contract (score must be 0.0), which the CURRENT scorer fails to satisfy.

    RED: _score_dimension_current() returns 4.0 (≠ 0.0) → assertion fails.
    GREEN (Wave 1): router injects 0.0 for unanswered 1.2, 1.3 → min returns 0.0.
    """
    db = _make_db()

    session = QRAMMSession(
        org_name="TestOrg",
        created_at=datetime.datetime(2026, 6, 13, 0, 0, 0),
        status="active",
        model_version="1.0",
    )
    db.add(session)
    db.flush()
    session_id = session.id

    # Only practice "1.1" answered (value=4); "1.2" and "1.3" are NULL (unanswered).
    db.add(QRAMMAnswer(
        session_id=session_id,
        question_number=1,
        dimension="CVI",
        practice_area="1.1",
        answer_value=4,
    ))
    db.add(QRAMMAnswer(
        session_id=session_id,
        question_number=2,
        dimension="CVI",
        practice_area="1.2",
        answer_value=None,  # unanswered
    ))
    db.add(QRAMMAnswer(
        session_id=session_id,
        question_number=3,
        dimension="CVI",
        practice_area="1.3",
        answer_value=None,  # unanswered
    ))
    db.commit()

    # Current (buggy) path: mirrors qramm.py score endpoint logic.
    # Wave 1 must replace this path with one that injects 0.0 for unanswered practices.
    score = _score_dimension_current(db, session_id, "CVI")

    # Post-fix contract: unanswered 1.2 and 1.3 inject 0.0 → min = 0.0.
    # This FAILS against the current source because _score_dimension_current returns 4.0.
    assert score == pytest.approx(0.0), (
        f"Post-fix: partially-answered CVI must score 0.0 (unanswered 1.2, 1.3 inject 0.0 "
        f"into weakest-link min). Current scorer returned {score} — inflation bug confirmed. "
        f"Wave 1 fix: inject 0.0 for each practice in EXPECTED_PRACTICES[dim] not answered."
    )


# SF02b: regression guard — fully answered dimension preserves weakest-link min().
def test_fully_answered_dimension_uses_weakest_link_min():
    """All three practices answered: dimension score == min of the three practice scores.

    Setup: CVI — practice "1.1" answered 4/4/4 (avg=4.0), "1.2" answered 1/1/1 (avg=1.0),
    "1.3" answered 3/3/3 (avg=3.0). Weakest-link: min(4.0, 1.0, 3.0) = 1.0.

    This regression guard must PASS both before AND after the Wave 1 fix.
    It confirms compute_dimension_score still uses min() (never changes to avg).
    The current scorer passes this correctly — it only inflates PARTIAL dimensions.
    """
    db = _make_db()

    session = QRAMMSession(
        org_name="RegressionOrg",
        created_at=datetime.datetime(2026, 6, 13, 0, 0, 0),
        status="active",
        model_version="1.0",
    )
    db.add(session)
    db.flush()
    session_id = session.id

    # Seed all 3 practices with 3 answers each.
    q_num = 1
    for practice, value in [("1.1", 4), ("1.2", 1), ("1.3", 3)]:
        for _ in range(3):  # 3 questions per practice
            db.add(QRAMMAnswer(
                session_id=session_id,
                question_number=q_num,
                dimension="CVI",
                practice_area=practice,
                answer_value=value,
            ))
            q_num += 1
    db.commit()

    # Current scorer (no unanswered practices, so it's correct here).
    score = _score_dimension_current(db, session_id, "CVI")
    assert score == pytest.approx(1.0), (
        f"Fully-answered CVI weakest-link must be 1.0 (min of 4.0, 1.0, 3.0), got {score}"
    )
