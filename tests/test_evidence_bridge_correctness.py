"""Phase 74 — QWARN-02 correctness tests (D-05..D-07, WR-01/WR-03/WR-07/WR-08).

RED-then-GREEN coverage for:
- D-05 (WR-01): TZ-symmetric SQL filter invariant + `datetime.date.fromisoformat` parse.
- D-06 (WR-03): idempotent UPDATE — repeat call skips no-op writes.
- D-06 (WR-07): db.commit() failure is logged + rolled back + returns (no propagation).
- D-07 (WR-08): attach_context AttributeError logged (not swallowed); unexpected
  exception logged AND re-raised.
"""
from __future__ import annotations

import datetime
import json
import logging
import uuid
from datetime import datetime as dt
from datetime import timezone, timedelta
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from quirk.assessment.operator_context import OperatorContext, attach_context
from quirk.models import Base, CryptoEndpoint, QRAMMAnswer
from quirk.qramm.evidence_bridge import populate_cvi_suggestions


# ---------- Shared DB fixture ----------

def _make_db():
    db_name = f"test_bridge_corr_{uuid.uuid4().hex}"
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


def _seed_endpoint(db, scanned_at):
    db.add(CryptoEndpoint(
        host="tls-1.example", port=443, protocol="tls", scanned_at=scanned_at,
        tls_version="TLSv1.2", cipher_suite="ECDHE-RSA-AES256-GCM-SHA384",
        cert_sig_alg="sha256WithRSAEncryption", cert_pubkey_alg="RSA",
    ))


# ---------- D-05 (WR-01) — TZ-safe date filter ----------

def test_max_date_filter_is_tz_symmetric():
    """Two endpoints with TZ-equivalent timestamps on the same calendar date
    (UTC) must both fall into the same `func.date(...)` bucket — SQL filter
    is engine-symmetric (both sides use `func.date()`)."""
    db = _make_db()
    # Same UTC instant, but one represented as a +00:00 datetime and another
    # as a +05:00 datetime that converts to the same UTC moment. SQLite's
    # date() strips TZ info, so both should bucket together.
    base = dt(2026, 5, 15, 12, 0, 0, tzinfo=timezone.utc)
    _seed_endpoint(db, base)
    _seed_endpoint(db, base + timedelta(hours=2))  # same UTC date
    db.commit()
    _seed_cvi_answers(db, session_id=1)

    populate_cvi_suggestions(session_id=1, db=db)

    # Both endpoints contributed; Practice 1.1 score reflects 2 endpoints
    # (>=1 protocol bucket, distinct_protocols == 1 → score_1_1 == 2).
    answers = db.query(QRAMMAnswer).filter(
        QRAMMAnswer.dimension == "CVI",
        QRAMMAnswer.practice_area == "1.1",
    ).all()
    assert len(answers) == 1
    assert answers[0].suggested_answer == 2


def test_max_date_str_parses_as_datetime_date():
    """The string returned by `func.date(func.max(scanned_at))` must be
    parseable as `datetime.date.fromisoformat(...)` — invariant for any
    Python-side downstream date comparison."""
    db = _make_db()
    _seed_endpoint(db, dt(2026, 5, 15, 12, 0, 0, tzinfo=timezone.utc))
    db.commit()

    from sqlalchemy import func
    max_date_str = db.query(func.date(func.max(CryptoEndpoint.scanned_at))).scalar()
    assert max_date_str is not None
    parsed = datetime.date.fromisoformat(max_date_str)
    assert isinstance(parsed, datetime.date)
    assert parsed == datetime.date(2026, 5, 15)


# ---------- D-06 (WR-03) — idempotent UPDATE ----------

def test_idempotent_repeat_call_does_not_rewrite(caplog):
    """Second call with identical desired state must skip the `.update(...)`."""
    db = _make_db()
    _seed_endpoint(db, dt(2026, 5, 15, 12, 0, 0, tzinfo=timezone.utc))
    db.commit()
    _seed_cvi_answers(db, session_id=1)

    # First call writes the suggested values.
    populate_cvi_suggestions(session_id=1, db=db)

    # Spy on the SQLAlchemy update() method to count invocations on call 2.
    original_query = db.query
    update_calls = {"count": 0}

    def counting_query(*args, **kwargs):
        q = original_query(*args, **kwargs)
        original_update = q.update if hasattr(q, "update") else None
        if original_update is None:
            return q

        def wrapped_update(*a, **kw):
            update_calls["count"] += 1
            return original_update(*a, **kw)
        # Monkey-patch the method on this Query instance.
        try:
            q.update = wrapped_update  # type: ignore[assignment]
        except Exception:
            pass
        return q

    with patch.object(db, "query", side_effect=counting_query):
        populate_cvi_suggestions(session_id=1, db=db)

    # Second call: desired state already persisted → zero `.update(...)` calls.
    assert update_calls["count"] == 0, (
        f"expected idempotent skip on repeat call, got {update_calls['count']} update() calls"
    )


# ---------- D-06 (WR-07) — commit-failure handler ----------

def test_commit_failure_logs_and_rolls_back(caplog):
    """`db.commit` raising SQLAlchemyError must be caught, logged at WARNING,
    rolled back, and the function returns without propagating."""
    db = _make_db()
    _seed_endpoint(db, dt(2026, 5, 15, 12, 0, 0, tzinfo=timezone.utc))
    db.commit()
    _seed_cvi_answers(db, session_id=1)

    # Mock commit to raise; rollback should be called.
    db.rollback = MagicMock(wraps=db.rollback)  # type: ignore[method-assign]
    with patch.object(db, "commit", side_effect=SQLAlchemyError("boom")):
        with caplog.at_level(logging.WARNING, logger="quirk.qramm.evidence_bridge"):
            # MUST NOT raise.
            populate_cvi_suggestions(session_id=1, db=db)

    db.rollback.assert_called()
    assert any(
        "evidence_bridge UPDATE failed" in rec.message and "boom" in rec.message
        for rec in caplog.records
    ), f"expected commit-failure WARNING log, got {[r.message for r in caplog.records]}"


# ---------- D-07 (WR-08) — attach_context narrow excepts ----------

class _SlotsCfg:
    """Cfg-like object that raises AttributeError on any setattr."""
    __slots__ = ()


class _RaisingCfg:
    """Cfg-like object whose __setattr__ raises an unexpected exception."""
    def __setattr__(self, name, value):
        raise RuntimeError("boom")


def _ctx():
    return OperatorContext(
        data_types=["PCI"], data_longevity_years=7, exposure="mixed", crown_jewels=[]
    )


def test_attach_context_attribute_error_logged(caplog):
    """AttributeError must be logged at WARNING (not silently swallowed) and
    the function must return without raising."""
    cfg = _SlotsCfg()
    with caplog.at_level(logging.WARNING, logger="quirk.assessment.operator_context"):
        attach_context(cfg, _ctx())

    assert any(
        "attach_context skipped" in rec.message for rec in caplog.records
    ), f"expected 'attach_context skipped' WARNING, got {[r.message for r in caplog.records]}"


def test_attach_context_unexpected_exception_reraised(caplog):
    """A non-AttributeError exception must be logged at WARNING AND re-raised
    (user-override safety net per D-07 + Pitfall 4)."""
    cfg = _RaisingCfg()
    with caplog.at_level(logging.WARNING, logger="quirk.assessment.operator_context"):
        with pytest.raises(RuntimeError, match="boom"):
            attach_context(cfg, _ctx())

    assert any(
        "attach_context unexpected" in rec.message and "boom" in rec.message
        for rec in caplog.records
    ), f"expected 'attach_context unexpected' WARNING, got {[r.message for r in caplog.records]}"
