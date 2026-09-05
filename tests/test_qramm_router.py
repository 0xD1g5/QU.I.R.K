"""TestClient smoke tests for /api/qramm/* — Phase 51 QRAMM-01 + QRAMM-02.

Covers all 5 endpoint families with HTTP status assertions, score persistence
round-trip, validation errors, and table-existence verification for QRAMM-01.

Pattern: UUID-named shared-cache in-memory SQLite per test (avoids Pitfall 4
shared-cache collisions in test_dashboard_trends.py).
"""
from __future__ import annotations

import ast
import pathlib
import uuid
from typing import List, Tuple

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

import quirk


def _make_qramm_client() -> Tuple[TestClient, object]:
    """Build a TestClient with isolated UUID-named in-memory SQLite DB."""
    from quirk.dashboard.api.app import create_app
    from quirk.dashboard.api.deps import get_db
    from quirk.models import Base

    db_name = f"test_qramm_{uuid.uuid4().hex}"
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


# ---------- QRAMM-01: tables exist after init_db() ----------

def test_qramm_tables_exist_after_init_db(tmp_path):
    """QRAMM-01: init_db() creates qramm_sessions/qramm_answers/qramm_profiles."""
    from quirk.db import init_db

    db_path = str(tmp_path / "init_check.db")
    engine = init_db(db_path)
    table_names = set(inspect(engine).get_table_names())
    assert {"qramm_sessions", "qramm_answers", "qramm_profiles"}.issubset(table_names), table_names


def test_qramm_init_db_idempotent(tmp_path):
    """QRAMM-01: re-running init_db() does not error and does not duplicate tables."""
    from quirk.db import init_db

    db_path = str(tmp_path / "idem_check.db")
    init_db(db_path)
    engine = init_db(db_path)  # second call — must not raise
    table_names = set(inspect(engine).get_table_names())
    assert {"qramm_sessions", "qramm_answers", "qramm_profiles"}.issubset(table_names)


# ---------- QRAMM-02: 5 endpoint families ----------

def test_create_session():
    client, _ = _make_qramm_client()
    resp = client.post("/api/qramm/sessions", json={"org_name": "TestOrg"})
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert "session_id" in body
    assert body["org_name"] == "TestOrg"
    assert body["status"] == "draft"


def test_create_session_empty_body():
    client, _ = _make_qramm_client()
    resp = client.post("/api/qramm/sessions", json={})
    assert resp.status_code == 201, resp.text
    assert "session_id" in resp.json()


def test_read_session_round_trip():
    client, _ = _make_qramm_client()
    create_resp = client.post("/api/qramm/sessions", json={"org_name": "RoundTrip"})
    sid = create_resp.json()["session_id"]
    read_resp = client.get(f"/api/qramm/sessions/{sid}")
    assert read_resp.status_code == 200, read_resp.text
    body = read_resp.json()
    assert body["session_id"] == sid
    assert body["org_name"] == "RoundTrip"
    assert body["answers_count"] == 0
    assert body["score"] is None


def test_read_session_not_found():
    client, _ = _make_qramm_client()
    resp = client.get("/api/qramm/sessions/9999")
    assert resp.status_code == 404
    assert "QRK-DASHBOARD-009" in resp.json()["detail"]


def test_save_answers_basic():
    client, _ = _make_qramm_client()
    sid = client.post("/api/qramm/sessions", json={}).json()["session_id"]
    resp = client.post(
        f"/api/qramm/sessions/{sid}/answers",
        json={"answers": [
            {"question_number": 1, "answer_value": 3},
            {"question_number": 2, "answer_value": 2},
        ]},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["saved_count"] == 2
    assert body["total_answered"] == 2


def test_save_answers_upsert_overwrites():
    client, _ = _make_qramm_client()
    sid = client.post("/api/qramm/sessions", json={}).json()["session_id"]
    client.post(f"/api/qramm/sessions/{sid}/answers", json={"answers": [{"question_number": 1, "answer_value": 2}]})
    client.post(f"/api/qramm/sessions/{sid}/answers", json={"answers": [{"question_number": 1, "answer_value": 4}]})
    read = client.get(f"/api/qramm/sessions/{sid}").json()
    assert read["answers_count"] == 1  # still 1 distinct question, not duplicated


def test_save_answers_validation_rejects_out_of_range():
    """Pydantic Field(ge=1, le=4) on answer_value rejects 5 with 422."""
    client, _ = _make_qramm_client()
    sid = client.post("/api/qramm/sessions", json={}).json()["session_id"]
    resp = client.post(
        f"/api/qramm/sessions/{sid}/answers",
        json={"answers": [{"question_number": 1, "answer_value": 5}]},
    )
    assert resp.status_code == 422, resp.text


def test_save_answers_validation_rejects_question_out_of_range():
    """Pydantic Field(ge=1, le=120) on question_number rejects 121 with 422."""
    client, _ = _make_qramm_client()
    sid = client.post("/api/qramm/sessions", json={}).json()["session_id"]
    resp = client.post(
        f"/api/qramm/sessions/{sid}/answers",
        json={"answers": [{"question_number": 121, "answer_value": 3}]},
    )
    assert resp.status_code == 422, resp.text


def test_save_answers_session_not_found():
    client, _ = _make_qramm_client()
    resp = client.post(
        "/api/qramm/sessions/9999/answers",
        json={"answers": [{"question_number": 1, "answer_value": 2}]},
    )
    assert resp.status_code == 404


def test_score_session_full_120_answers():
    """Seed all 120 answers with value=2, expect overall=2.0 'Developing'."""
    client, _ = _make_qramm_client()
    sid = client.post("/api/qramm/sessions", json={}).json()["session_id"]
    answers = [{"question_number": n, "answer_value": 2} for n in range(1, 121)]
    save_resp = client.post(f"/api/qramm/sessions/{sid}/answers", json={"answers": answers})
    assert save_resp.status_code == 200
    score_resp = client.post(f"/api/qramm/sessions/{sid}/score", json={})
    assert score_resp.status_code == 200, score_resp.text
    body = score_resp.json()
    assert body["session_id"] == sid
    assert 1.0 <= body["overall"] <= 4.0
    assert body["overall"] == 2.0
    assert body["maturity"] == "Developing"
    assert set(body["dimensions"].keys()) == {"CVI", "SGRM", "DPE", "ITR"}
    assert body["profile_multiplier"] == 1.0


def test_score_session_persistence_round_trip():
    """D-10: score is persisted to score_json and returned by GET."""
    client, _ = _make_qramm_client()
    sid = client.post("/api/qramm/sessions", json={}).json()["session_id"]
    answers = [{"question_number": n, "answer_value": 3} for n in range(1, 121)]
    client.post(f"/api/qramm/sessions/{sid}/answers", json={"answers": answers})
    score_body = client.post(f"/api/qramm/sessions/{sid}/score", json={}).json()
    read_body = client.get(f"/api/qramm/sessions/{sid}").json()
    assert read_body["status"] == "scored"
    assert read_body["score"] is not None
    assert read_body["score"]["overall"] == score_body["overall"]
    assert read_body["score"]["maturity"] == score_body["maturity"]


def test_score_session_with_multiplier():
    """profile_multiplier in request body is applied to dimensions."""
    client, _ = _make_qramm_client()
    sid = client.post("/api/qramm/sessions", json={}).json()["session_id"]
    answers = [{"question_number": n, "answer_value": 2} for n in range(1, 121)]
    client.post(f"/api/qramm/sessions/{sid}/answers", json={"answers": answers})
    body = client.post(f"/api/qramm/sessions/{sid}/score", json={"profile_multiplier": 1.2}).json()
    assert body["profile_multiplier"] == 1.2
    # Each dimension score is min of 3 practices = 2.0; weighted = 2.0 * 1.2 = 2.4
    assert body["dimensions"]["CVI"]["weighted"] == pytest.approx(2.4)


def test_score_session_not_found():
    client, _ = _make_qramm_client()
    resp = client.post("/api/qramm/sessions/9999/score", json={})
    assert resp.status_code == 404


def test_delete_session():
    client, _ = _make_qramm_client()
    sid = client.post("/api/qramm/sessions", json={}).json()["session_id"]
    resp = client.delete(f"/api/qramm/sessions/{sid}")
    assert resp.status_code == 204
    # Verify gone
    assert client.get(f"/api/qramm/sessions/{sid}").status_code == 404


def test_delete_session_cascades_answers():
    """Pitfall 2: SQLite FK not enforced; explicit cascade in DELETE handler removes answers."""
    from quirk.models import QRAMMAnswer

    client, TestingSession = _make_qramm_client()
    sid = client.post("/api/qramm/sessions", json={}).json()["session_id"]
    client.post(
        f"/api/qramm/sessions/{sid}/answers",
        json={"answers": [{"question_number": 1, "answer_value": 3}]},
    )
    # Confirm answer row exists pre-delete
    db = TestingSession()
    try:
        pre_count = db.query(QRAMMAnswer).filter(QRAMMAnswer.session_id == sid).count()
    finally:
        db.close()
    assert pre_count >= 1  # Phase 53: create_session pre-seeds 30 CVI rows; total is 31

    assert client.delete(f"/api/qramm/sessions/{sid}").status_code == 204

    db = TestingSession()
    try:
        post_count = db.query(QRAMMAnswer).filter(QRAMMAnswer.session_id == sid).count()
    finally:
        db.close()
    assert post_count == 0, "Answer rows must cascade-delete with session"


def test_delete_session_not_found():
    client, _ = _make_qramm_client()
    resp = client.delete("/api/qramm/sessions/9999")
    assert resp.status_code == 404


# ---------- Phase 54 Plan 01: 4 new endpoints ----------

def test_list_sessions():
    """Test 1: GET /api/qramm/sessions returns list with session_id and answers_count."""
    client, _ = _make_qramm_client()
    create_resp = client.post("/api/qramm/sessions", json={"org_name": "ListOrg"})
    assert create_resp.status_code == 201
    sid = create_resp.json()["session_id"]

    resp = client.get("/api/qramm/sessions")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) >= 1
    session_ids = [s["session_id"] for s in body]
    assert sid in session_ids
    # answers_count must be an int
    match = next(s for s in body if s["session_id"] == sid)
    assert isinstance(match["answers_count"], int)


def test_list_sessions_orders_desc():
    """Test 2: GET /api/qramm/sessions returns most-recently-created session first."""
    client, _ = _make_qramm_client()
    sid1 = client.post("/api/qramm/sessions", json={"org_name": "First"}).json()["session_id"]
    sid2 = client.post("/api/qramm/sessions", json={"org_name": "Second"}).json()["session_id"]

    resp = client.get("/api/qramm/sessions")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body) >= 2
    # Most recent session should be first
    assert body[0]["session_id"] == sid2


def test_create_profile():
    """QRAMM-09: Test 3: POST /api/qramm/profiles returns 201 with profile_id, session_id, multiplier in 0.8-1.5."""
    client, TestingSession = _make_qramm_client()
    sid = client.post("/api/qramm/sessions", json={}).json()["session_id"]

    resp = client.post("/api/qramm/profiles", json={
        "session_id": sid,
        "industry": "healthcare",
        "org_size": "medium",
        "geographic_scope": "national",
        "data_sensitivity": "confidential",
        "regulatory_obligations": ["HIPAA", "SOC2"],
    })
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert "profile_id" in body
    assert body["session_id"] == sid
    assert isinstance(body["multiplier"], float)
    assert 0.8 <= body["multiplier"] <= 1.5

    # Session.profile_id must be updated
    db = TestingSession()
    try:
        from quirk.models import QRAMMSession
        session = db.get(QRAMMSession, sid)
        assert session.profile_id == body["profile_id"]
    finally:
        db.close()


def test_create_profile_multiplier_varies():
    """QRAMM-09: Test 4: Different industry+data_sensitivity combos produce different multipliers."""
    client, _ = _make_qramm_client()
    sid1 = client.post("/api/qramm/sessions", json={}).json()["session_id"]
    sid2 = client.post("/api/qramm/sessions", json={}).json()["session_id"]

    resp_high = client.post("/api/qramm/profiles", json={
        "session_id": sid1,
        "industry": "financial_services",
        "org_size": "large",
        "geographic_scope": "global",
        "data_sensitivity": "restricted_secret",
        "regulatory_obligations": [],
    })
    resp_low = client.post("/api/qramm/profiles", json={
        "session_id": sid2,
        "industry": "other",
        "org_size": "small",
        "geographic_scope": "local",
        "data_sensitivity": "public",
        "regulatory_obligations": [],
    })
    assert resp_high.status_code == 201
    assert resp_low.status_code == 201
    assert resp_high.json()["multiplier"] != resp_low.json()["multiplier"]


def test_draft_answer_creates_row():
    """Test 5: POST /api/qramm/assessment/draft creates row; GET /answers shows it."""
    client, _ = _make_qramm_client()
    sid = client.post("/api/qramm/sessions", json={}).json()["session_id"]

    draft_resp = client.post("/api/qramm/assessment/draft", json={
        "session_id": sid,
        "question_number": 1,
        "answer_value": 3,
        "evidence_note": "note text",
    })
    assert draft_resp.status_code == 200, draft_resp.text
    assert draft_resp.json()["saved"] is True

    answers_resp = client.get(f"/api/qramm/sessions/{sid}/answers")
    assert answers_resp.status_code == 200, answers_resp.text
    answers = answers_resp.json()
    q1 = next((a for a in answers if a["question_number"] == 1), None)
    assert q1 is not None
    assert q1["answer_value"] == 3
    assert q1["evidence_note"] == "note text"


def test_draft_answer_updates_row():
    """Test 6: Second POST draft for same (session, question_number) overwrites the first."""
    client, _ = _make_qramm_client()
    sid = client.post("/api/qramm/sessions", json={}).json()["session_id"]

    client.post("/api/qramm/assessment/draft", json={
        "session_id": sid,
        "question_number": 5,
        "answer_value": 1,
    })
    client.post("/api/qramm/assessment/draft", json={
        "session_id": sid,
        "question_number": 5,
        "answer_value": 4,
    })
    answers = client.get(f"/api/qramm/sessions/{sid}/answers").json()
    q5_rows = [a for a in answers if a["question_number"] == 5]
    # Only one row for question 5; the second call's value wins
    assert len(q5_rows) == 1
    assert q5_rows[0]["answer_value"] == 4


def test_draft_answer_confirms_when_suggested():
    """Test 7: When existing row has suggested_answer, providing answer_value sets confirmed_at."""
    from quirk.models import QRAMMAnswer

    client, TestingSession = _make_qramm_client()
    sid = client.post("/api/qramm/sessions", json={}).json()["session_id"]

    # Pre-insert a row with suggested_answer, no answer_value (simulating auto-fill).
    # Use question 31 (SGRM) — create_session only pre-seeds CVI (questions 1-30),
    # so question 31 will not collide with pre-seeded rows.
    db = TestingSession()
    try:
        row = QRAMMAnswer(
            session_id=sid,
            question_number=31,
            dimension="SGRM",
            practice_area="2.1",
            suggested_answer=2,
            answer_value=None,
        )
        db.add(row)
        db.commit()
    finally:
        db.close()

    client.post("/api/qramm/assessment/draft", json={
        "session_id": sid,
        "question_number": 31,
        "answer_value": 3,
    })

    db = TestingSession()
    try:
        existing = (
            db.query(QRAMMAnswer)
            .filter(QRAMMAnswer.session_id == sid, QRAMMAnswer.question_number == 31)
            .one_or_none()
        )
        assert existing is not None
        assert existing.confirmed_at is not None, "confirmed_at should be set after overriding suggested_answer"
    finally:
        db.close()


def test_draft_answer_validation():
    """Test 8: Pydantic validation rejects out-of-range question_number and answer_value."""
    client, _ = _make_qramm_client()
    sid = client.post("/api/qramm/sessions", json={}).json()["session_id"]

    # question_number=0 → 422
    resp = client.post("/api/qramm/assessment/draft", json={
        "session_id": sid,
        "question_number": 0,
        "answer_value": 2,
    })
    assert resp.status_code == 422, resp.text

    # question_number=121 → 422
    resp = client.post("/api/qramm/assessment/draft", json={
        "session_id": sid,
        "question_number": 121,
        "answer_value": 2,
    })
    assert resp.status_code == 422, resp.text

    # answer_value=5 → 422
    resp = client.post("/api/qramm/assessment/draft", json={
        "session_id": sid,
        "question_number": 5,
        "answer_value": 5,
    })
    assert resp.status_code == 422, resp.text


def test_read_answers_includes_suggested():
    """Test 9: GET /api/qramm/sessions/{id}/answers includes suggested_answer field."""
    from quirk.models import QRAMMAnswer

    client, TestingSession = _make_qramm_client()
    sid = client.post("/api/qramm/sessions", json={}).json()["session_id"]

    # Use question 32 (SGRM) — not pre-seeded by create_session (CVI only, q1-30).
    db = TestingSession()
    try:
        row = QRAMMAnswer(
            session_id=sid,
            question_number=32,
            dimension="SGRM",
            practice_area="2.1",
            suggested_answer=2,
        )
        db.add(row)
        db.commit()
    finally:
        db.close()

    answers_resp = client.get(f"/api/qramm/sessions/{sid}/answers")
    assert answers_resp.status_code == 200, answers_resp.text
    answers = answers_resp.json()
    q32 = next((a for a in answers if a["question_number"] == 32), None)
    assert q32 is not None
    assert q32["suggested_answer"] == 2


def test_read_answers_404():
    """Test 10: GET /api/qramm/sessions/99999/answers → 404."""
    client, _ = _make_qramm_client()
    resp = client.get("/api/qramm/sessions/99999/answers")
    assert resp.status_code == 404


# ---------- Phase 54 Plan 04: GET /api/qramm/questions ----------

def test_list_questions_returns_120():
    client, _ = _make_qramm_client()
    resp = client.get("/api/qramm/questions")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body) == 120
    required_keys = {"question_number", "dimension", "practice_area", "text", "maturity_labels"}
    for item in body:
        assert required_keys.issubset(item.keys())
    numbers = sorted(item["question_number"] for item in body)
    assert numbers == list(range(1, 121))


# ---------- DEBT-01 / SCORE-03 zero-utcnow gate (Phase 184.3 D-04) ----------
#
# Generalized 2026-09-05 from the QRAMM-only `test_no_utcnow_in_qramm_module`
# gate (Phase 51 DEBT-01) to cover all of quirk/, per SCORE-03/D-04. quirk/'s
# `datetime.utcnow()` count was independently VERIFIED zero on 2026-09-05; this
# gate exists so that zero is locked derivationally (a run-time, package-
# rooted, recursive AST scan) rather than remaining true by coincidence.
#
# Deviation from the plan as literally written (Rule 1 - bug, recorded in
# 184.3-04-SUMMARY.md): the plan directed keeping the original text/comment-
# stripping filter (`line.lstrip().startswith("#")`) unchanged. That filter
# only strips lines beginning with a literal "#", so widening the scan root
# to all of quirk/ (which the plan also directs) causes it to false-positive
# on the two Phase 51 DEBT-01 *documentation* comments living inside module
# DOCSTRINGS (not "#"-comments) at quirk/cli/qramm_cmd.py:9 and
# quirk/cli/cve_cmd.py:10 -- both literally contain the substring
# "datetime.utcnow()" as prose. Verified directly: the old filter leaves
# "utcnow()" in `non_comment` for both files. An AST-based scan (matching
# only genuine `ast.Call` nodes whose callee attribute is `utcnow`) excludes
# docstring/comment/string-literal text categorically, with no allowlist and
# no per-file exemption -- matching this phase's anti-allowlist gate design
# (see threat T-184.3-12).


def _find_utcnow_call_sites(root: pathlib.Path) -> List[str]:
    """Recursively scan `root` for real `datetime.utcnow()` call sites.

    Uses AST parsing rather than text/comment stripping so that docstrings,
    comments, and string literals that merely mention "utcnow()" (e.g. the
    Phase 51 DEBT-01 documentation comments in quirk/cli/qramm_cmd.py and
    quirk/cli/cve_cmd.py) are never misidentified as real calls -- only a
    genuine `ast.Call` node whose callee attribute is `utcnow` is reported.
    Collects ALL offending sites before returning, so a caller can report a
    multi-site regression in one assertion rather than one offender per run.
    """
    offenders: List[str] = []
    for py in sorted(root.rglob("*.py")):
        try:
            text = py.read_text(encoding="utf-8")
            tree = ast.parse(text, filename=str(py))
        except (SyntaxError, UnicodeDecodeError):  # pragma: no cover - defensive
            continue
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "utcnow"
            ):
                offenders.append(f"{py}:{node.lineno}")
    return offenders


def test_no_utcnow_anywhere_in_quirk():
    """DEBT-01 / SCORE-03 (D-04): zero real `datetime.utcnow()` call sites
    anywhere under quirk/. Generalizes the former QRAMM-only
    `test_no_utcnow_in_qramm_module` gate (Phase 51) to the whole package,
    per Phase 184.3's SCORE-03 requirement. quirk/'s zero was VERIFIED
    2026-09-05 -- this gate locks that zero derivationally (root resolved
    from the live imported `quirk` package at test-run time, scanned
    recursively) instead of trusting it stays true by coincidence.
    """
    pkg_root = pathlib.Path(quirk.__file__).parent
    offenders = _find_utcnow_call_sites(pkg_root)
    assert not offenders, (
        "datetime.utcnow() call(s) found under quirk/ (forbidden per DEBT-01 "
        "and SCORE-03 -- use datetime.now(timezone.utc) instead):\n"
        + "\n".join(offenders)
    )


def test_utcnow_gate_detects_synthetic_offender(tmp_path):
    """Non-vacuousness self-test: proves `_find_utcnow_call_sites` actually
    detects a real `datetime.utcnow()` call rather than merely reporting
    "no offenders" because nothing was scanned."""
    offender_file = tmp_path / "synthetic_offender.py"
    offender_file.write_text(
        "from datetime import datetime\n\nx = datetime.utcnow()\n",
        encoding="utf-8",
    )
    offenders = _find_utcnow_call_sites(tmp_path)
    assert len(offenders) == 1
    assert "synthetic_offender.py" in offenders[0]
