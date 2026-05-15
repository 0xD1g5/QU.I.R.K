"""Tests for Phase 54 QRAMM-10: evidence_note column on qramm_answers.

Verifies:
 1. After init_db(), the column exists in the DB schema.
 2. _ensure_phase54_qramm_columns is idempotent (second call does not raise).
 3. A QRAMMAnswer row can be round-tripped with evidence_note.

Uses in-memory SQLite engine (same UUID-named shared-cache pattern as
test_qramm_router.py) so tests do not write to disk.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import create_engine, inspect as sa_inspect
from sqlalchemy.orm import sessionmaker


def _make_engine():
    """Create a fresh isolated in-memory SQLite engine with QRAMM tables."""
    from quirk.models import Base

    db_name = f"test_qramm_answer_{uuid.uuid4().hex}"
    engine = create_engine(
        f"sqlite:///file:{db_name}?mode=memory&cache=shared&uri=true",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    return engine


def test_evidence_note_column_exists_after_migration():
    """Behavior 1: After _ensure_phase54_qramm_columns(), column 'evidence_note' exists."""
    # Phase 77 D-21: _ensure_phase54_qramm_columns consolidated into the
    # generic _ensure_columns helper + _PHASE54_QRAMM_ANSWER_COLUMNS tuple.
    from quirk.db import _PHASE54_QRAMM_ANSWER_COLUMNS, _ensure_columns

    engine = _make_engine()
    _ensure_columns(engine, "qramm_answers", _PHASE54_QRAMM_ANSWER_COLUMNS)

    col_names = {c["name"] for c in sa_inspect(engine).get_columns("qramm_answers")}
    assert "evidence_note" in col_names, (
        f"'evidence_note' column not found in qramm_answers; columns: {col_names}"
    )


def test_ensure_phase54_qramm_columns_idempotent():
    """Behavior 2: Calling _ensure_phase54_qramm_columns twice does not raise."""
    # Phase 77 D-21: _ensure_phase54_qramm_columns consolidated into the
    # generic _ensure_columns helper + _PHASE54_QRAMM_ANSWER_COLUMNS tuple.
    from quirk.db import _PHASE54_QRAMM_ANSWER_COLUMNS, _ensure_columns

    engine = _make_engine()
    _ensure_columns(engine, "qramm_answers", _PHASE54_QRAMM_ANSWER_COLUMNS)
    # Second call must be a no-op, not raise an OperationalError.
    _ensure_columns(engine, "qramm_answers", _PHASE54_QRAMM_ANSWER_COLUMNS)


def test_qramm_answer_evidence_note_round_trip():
    """Behavior 3: A QRAMMAnswer row inserted with evidence_note is read back with that value."""
    # Phase 77 D-21: consolidated into generic _ensure_columns helper.
    from quirk.db import _PHASE54_QRAMM_ANSWER_COLUMNS, _ensure_columns
    from quirk.models import QRAMMAnswer

    engine = _make_engine()
    _ensure_columns(engine, "qramm_answers", _PHASE54_QRAMM_ANSWER_COLUMNS)

    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = Session()
    try:
        row = QRAMMAnswer(
            session_id=42,
            question_number=1,
            dimension="CVI",
            practice_area="1.1",
            answer_value=3,
            evidence_note="hello",
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        fetched = db.get(QRAMMAnswer, row.id)
        assert fetched is not None
        assert fetched.evidence_note == "hello"
    finally:
        db.close()
