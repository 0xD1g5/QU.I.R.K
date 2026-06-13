"""Phase 124 — SCOREFIX-05 RED scaffold.

Pins the post-fix behavior for evidence_bridge.populate_cvi_suggestions:
  - SF05a: session_created_at=T1 anchor must exclude endpoints scanned at T2 > T1.
    Currently the param does not exist → TypeError or wrong cohort. RED.
  - SF05b: session_created_at=None (default) falls back to global MAX behavior.
    Back-compat guard — must PASS before AND after the fix.

Reuses the _make_db() / _seed_endpoint / _seed_cvi_answers pattern from
tests/test_evidence_bridge_correctness.py (same in-memory SQLite URI pattern).

Current signature: populate_cvi_suggestions(session_id: int, db: Session) → None
Post-fix signature: populate_cvi_suggestions(session_id: int, db: Session, *,
                                               session_created_at: datetime|None = None) → None

RED: SF05a calls the function with session_created_at=T1, which does not exist
     yet → TypeError (unexpected keyword argument).
     Alternatively, if the keyword is accepted but the filter is not applied,
     the cohort includes T2 endpoints which violates the scoping contract.
"""
from __future__ import annotations

import uuid
from datetime import datetime as dt

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from quirk.models import Base, CryptoEndpoint, QRAMMAnswer
from quirk.qramm.evidence_bridge import populate_cvi_suggestions


# ---------- Shared DB fixture (mirrors test_evidence_bridge_correctness.py) ----------

def _make_db():
    db_name = f"test_sf05_{uuid.uuid4().hex}"
    engine = create_engine(
        f"sqlite:///file:{db_name}?mode=memory&cache=shared&uri=true",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return Session()


def _seed_cvi_answers(db, session_id: int) -> None:
    for i, practice in enumerate(("1.1", "1.2", "1.3"), start=1):
        db.add(QRAMMAnswer(
            session_id=session_id,
            question_number=i,
            dimension="CVI",
            practice_area=practice,
            answer_value=None,
        ))
    db.commit()


def _seed_endpoint(db, host: str, scanned_at: dt) -> None:
    db.add(CryptoEndpoint(
        host=host,
        port=443,
        protocol="tls",
        scanned_at=scanned_at,
        tls_version="TLSv1.3",
        cipher_suite="TLS_AES_256_GCM_SHA384",
        cert_sig_alg="ecdsa-with-SHA256",
        cert_pubkey_alg="EC",
    ))


def _get_evidence_source(db, session_id: int, practice: str) -> str | None:
    row = (
        db.query(QRAMMAnswer)
        .filter(
            QRAMMAnswer.session_id == session_id,
            QRAMMAnswer.dimension == "CVI",
            QRAMMAnswer.practice_area == practice,
        )
        .first()
    )
    return row.evidence_source if row else None


# ---------- SF05a: session_created_at anchor scopes cohort ----------

def test_session_created_at_excludes_later_scan_cohort():
    """populate_cvi_suggestions with session_created_at=T1 must not use T2 endpoints.

    Setup:
      T1 = 2026-06-01 12:00:00  — the session's creation time (temporal anchor)
      T2 = 2026-06-10 12:00:00  — a later scan from a different engagement

    T1 cohort: 2 endpoints at 2026-06-01 12:00
    T2 cohort: 3 endpoints at 2026-06-10 12:00 (different engagement, later date)

    Without the fix, MAX(date(scanned_at)) returns 2026-06-10 (T2 cohort) even when
    session was created at T1. Post-fix: MAX filtered by scanned_at <= T1 returns
    2026-06-01 (T1 cohort only).

    The evidence_source token encodes the max_date_str:
      "evidence_bridge:scan:2026-06-01:<version>" for T1-anchored call
      "evidence_bridge:scan:2026-06-10:<version>" for global-max call

    We assert the evidence_source after calling with session_created_at=T1 does NOT
    contain "2026-06-10" — proving T2 endpoints are excluded.

    RED: current signature has no session_created_at param → TypeError.
    """
    T1 = dt(2026, 6, 1, 12, 0, 0)   # session creation time
    T2 = dt(2026, 6, 10, 12, 0, 0)  # later scan (different engagement)

    db = _make_db()

    # T1 cohort: 2 endpoints from the session's own scan.
    _seed_endpoint(db, "t1-host-a.example", T1)
    _seed_endpoint(db, "t1-host-b.example", T1)

    # T2 cohort: 3 endpoints from a LATER engagement (must NOT be used).
    _seed_endpoint(db, "t2-host-a.example", T2)
    _seed_endpoint(db, "t2-host-b.example", T2)
    _seed_endpoint(db, "t2-host-c.example", T2)
    db.commit()

    # Pre-create CVI answer rows for session 1.
    _seed_cvi_answers(db, session_id=1)

    # Call with session_created_at=T1 — the post-fix keyword-only arg.
    # RED: currently raises TypeError: unexpected keyword argument 'session_created_at'.
    populate_cvi_suggestions(session_id=1, db=db, session_created_at=T1)

    # Post-fix: evidence_source must encode the T1 date (2026-06-01), NOT T2 (2026-06-10).
    evidence_source = _get_evidence_source(db, session_id=1, practice="1.1")
    assert evidence_source is not None, (
        "evidence_source must be set after populate_cvi_suggestions call"
    )
    assert "2026-06-10" not in evidence_source, (
        f"Session anchored at T1 must not use T2 cohort. "
        f"evidence_source: {evidence_source!r} contains '2026-06-10' — T2 contamination detected. "
        f"Post-fix must filter scanned_at <= session_created_at."
    )
    assert "2026-06-01" in evidence_source, (
        f"Session anchored at T1 must use T1 cohort (2026-06-01). "
        f"evidence_source: {evidence_source!r}"
    )


# SF05b: back-compat — session_created_at=None falls back to global MAX.
def test_no_session_created_at_falls_back_to_global_max():
    """populate_cvi_suggestions with NO session_created_at uses global MAX (back-compat).

    This back-compat guard must PASS before AND after the fix.
    Existing callers that omit session_created_at get the current behavior.
    """
    T1 = dt(2026, 5, 15, 12, 0, 0)
    T2 = dt(2026, 5, 20, 12, 0, 0)  # later (becomes global MAX)

    db = _make_db()
    _seed_endpoint(db, "older.example", T1)
    _seed_endpoint(db, "newer.example", T2)
    db.commit()
    _seed_cvi_answers(db, session_id=1)

    # Call without session_created_at — must use the global MAX date (T2).
    # This must work both before and after the fix (no regression on existing callers).
    populate_cvi_suggestions(session_id=1, db=db)

    evidence_source = _get_evidence_source(db, session_id=1, practice="1.1")
    assert evidence_source is not None, (
        "evidence_source must be set for back-compat call (no session_created_at)"
    )
    # Back-compat: global MAX is T2 date.
    assert "2026-05-20" in evidence_source, (
        f"Back-compat: no session_created_at → global MAX date (2026-05-20). "
        f"evidence_source: {evidence_source!r}"
    )
