"""Phase 70 BLOCK-07: integration tests for FK-safe delete_session behavior.

Asserts that DELETE /api/qramm/sessions/{id} on a session with a linked
QRAMMProfile completes with HTTP 204, raises no IntegrityError, and leaves
zero qramm_profiles rows for that session_id — under PRAGMA foreign_keys=ON.

Reuses the UUID-named shared-cache in-memory SQLite fixture pattern from
tests/test_qramm_router.py::_make_qramm_client. The module-level connect
event listener (D-02) attaches to the SQLAlchemy Engine class and fires for
this engine too; D-03 (declarative ForeignKey) makes the FK present at
Base.metadata.create_all time.
"""
from __future__ import annotations

import uuid
from typing import Tuple

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def _make_qramm_client() -> Tuple[TestClient, object]:
    """Build a TestClient with isolated UUID-named in-memory SQLite DB.

    Mirrors tests/test_qramm_router.py::_make_qramm_client.
    """
    from quirk.dashboard.api.app import create_app
    from quirk.dashboard.api.deps import get_db
    from quirk.models import Base

    db_name = f"test_qramm_fk_{uuid.uuid4().hex}"
    engine = create_engine(
        f"sqlite:///file:{db_name}?mode=memory&cache=shared&uri=true",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def _override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = _override_get_db
    return TestClient(app, headers={"X-Quirk-Request": "1"}), TestingSession


def _attach_profile(TestingSession, session_id: int) -> int:
    """Create a QRAMMProfile row linked to session_id and set the reverse pointer."""
    from quirk.models import QRAMMProfile, QRAMMSession

    db = TestingSession()
    try:
        profile = QRAMMProfile(session_id=session_id, industry="healthcare")
        db.add(profile)
        db.flush()
        profile_id = profile.id
        sess = db.query(QRAMMSession).filter(QRAMMSession.id == session_id).one()
        sess.profile_id = profile_id
        db.commit()
        return profile_id
    finally:
        db.close()


def test_delete_session_with_profile_clears_fk():
    """BLOCK-07 CR-04+CR-05: deleting a session with a linked profile must
    succeed (HTTP 204), raise no IntegrityError, and leave zero qramm_profiles
    rows for that session_id — even with PRAGMA foreign_keys=ON.
    """
    from quirk.models import QRAMMProfile

    client, TestingSession = _make_qramm_client()
    sid = client.post("/api/qramm/sessions", json={}).json()["session_id"]
    _attach_profile(TestingSession, sid)

    # Pre-condition: at least one profile row for this session.
    db = TestingSession()
    try:
        pre = db.query(QRAMMProfile).filter(QRAMMProfile.session_id == sid).count()
    finally:
        db.close()
    assert pre >= 1, "Setup failed — no profile attached"

    resp = client.delete(f"/api/qramm/sessions/{sid}")
    assert resp.status_code == 204, resp.text

    # Post-condition: zero profile rows for this session_id.
    db = TestingSession()
    try:
        post = db.query(QRAMMProfile).filter(QRAMMProfile.session_id == sid).count()
    finally:
        db.close()
    assert post == 0, "Linked QRAMMProfile rows must be removed by delete_session"


def test_delete_session_with_profile_and_answers():
    """BLOCK-07: delete_session removes profile + answer rows + session itself."""
    from quirk.models import QRAMMAnswer, QRAMMProfile, QRAMMSession

    client, TestingSession = _make_qramm_client()
    sid = client.post("/api/qramm/sessions", json={}).json()["session_id"]
    _attach_profile(TestingSession, sid)
    client.post(
        f"/api/qramm/sessions/{sid}/answers",
        json={"answers": [{"question_number": 5, "answer_value": 2}]},
    )

    db = TestingSession()
    try:
        assert db.query(QRAMMProfile).filter(QRAMMProfile.session_id == sid).count() >= 1
        assert db.query(QRAMMAnswer).filter(QRAMMAnswer.session_id == sid).count() >= 1
    finally:
        db.close()

    resp = client.delete(f"/api/qramm/sessions/{sid}")
    assert resp.status_code == 204, resp.text

    db = TestingSession()
    try:
        assert db.query(QRAMMProfile).filter(QRAMMProfile.session_id == sid).count() == 0
        assert db.query(QRAMMAnswer).filter(QRAMMAnswer.session_id == sid).count() == 0
        assert db.query(QRAMMSession).filter(QRAMMSession.id == sid).count() == 0
    finally:
        db.close()
