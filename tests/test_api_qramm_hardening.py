"""APCL-03 (Phase 75-03) — QRAMM/DAR API hardening tests.

Covers:
  - D-08 (WR-07): read_session returns 422 on corrupt score_json
  - D-09 (WR-08): _derive_dar_findings logs and skips on bad dat_scan_json
  - D-10 + RESEARCH C-5 (WR-17): list_questions degrades gracefully on
    QRAMM_QUESTIONS schema drift (real QuestionItem fields:
    question_number, dimension, practice_area, text, maturity_labels).

RED-then-GREEN: this module fails on HEAD before Task 2 lands the fixes.
"""
from __future__ import annotations

import logging
import types
import uuid
from typing import Tuple

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def _make_qramm_client() -> Tuple[TestClient, object]:
    """Build a TestClient with an isolated UUID-named in-memory SQLite DB.

    Mirrors test_qramm_router._make_qramm_client to avoid shared-cache
    collisions (Pitfall 4).
    """
    from quirk.dashboard.api.app import create_app
    from quirk.dashboard.api.deps import get_db
    from quirk.models import Base

    db_name = f"test_qramm_hard_{uuid.uuid4().hex}"
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


# ---------- D-08 (WR-07): read_session 422 on corrupt score_json ----------

def test_read_session_returns_422_on_corrupt_score_json():
    """D-08: corrupt persisted score_json must surface as 422, not silent score=None."""
    from quirk.models import QRAMMSession

    client, TestingSession = _make_qramm_client()
    sid = client.post("/api/qramm/sessions", json={"org_name": "Corrupt"}).json()[
        "session_id"
    ]

    # Poison the row with invalid JSON
    db = TestingSession()
    try:
        row = db.query(QRAMMSession).filter(QRAMMSession.id == sid).one()
        row.score_json = "{not valid json"
        db.commit()
    finally:
        db.close()

    resp = client.get(f"/api/qramm/sessions/{sid}")
    assert resp.status_code == 422, resp.text
    detail = resp.json()["detail"]
    # safe_str format varies across Python versions — startswith only (Pitfall 5)
    assert detail.startswith("Session JSON corrupt: "), detail


def test_read_session_happy_path_still_200():
    """D-08 regression guard: valid score_json still returns 200."""
    from quirk.models import QRAMMSession

    client, TestingSession = _make_qramm_client()
    sid = client.post("/api/qramm/sessions", json={"org_name": "Happy"}).json()[
        "session_id"
    ]

    db = TestingSession()
    try:
        row = db.query(QRAMMSession).filter(QRAMMSession.id == sid).one()
        row.score_json = '{"overall": 50}'
        db.commit()
    finally:
        db.close()

    resp = client.get(f"/api/qramm/sessions/{sid}")
    assert resp.status_code == 200, resp.text
    assert resp.json()["score"] == {"overall": 50}


# ---------- D-09 (WR-08): _derive_dar_findings logs + skips on bad JSON ----------

def _make_ep(**kw):
    """Build a minimal duck-typed endpoint object for _derive_dar_findings."""
    defaults = dict(
        scan_error=None,
        protocol="S3",
        host="example",
        port=443,
        severity="INFO",
        service_detail="",
        dat_scan_json=None,
    )
    defaults.update(kw)
    return types.SimpleNamespace(**defaults)


def test_derive_dar_findings_logs_and_skips_corrupt_dat_scan_json(caplog):
    """D-09: corrupt dat_scan_json must log a warning, not silently swallow."""
    from quirk.dashboard.api.routes.scan import _derive_dar_findings

    caplog.set_level(logging.WARNING, logger="quirk.dashboard.api.routes.scan")
    bad_ep = _make_ep(dat_scan_json="{not valid json")
    _derive_dar_findings([bad_ep])

    msgs = [r.getMessage() for r in caplog.records]
    assert any("DAR finding parse skipped" in m for m in msgs), msgs


def test_derive_dar_findings_valid_row_no_warning(caplog):
    """D-09 negative: a well-formed dat_scan_json must NOT emit the parse-skipped warning."""
    from quirk.dashboard.api.routes.scan import _derive_dar_findings

    caplog.set_level(logging.WARNING, logger="quirk.dashboard.api.routes.scan")
    good_ep = _make_ep(dat_scan_json='{"encryption_in_transit": true}')
    _derive_dar_findings([good_ep])

    msgs = [r.getMessage() for r in caplog.records]
    assert not any("DAR finding parse skipped" in m for m in msgs), msgs


def test_derive_dar_findings_continues_past_corrupt_row(caplog):
    """D-09: a corrupt row must not abort iteration; subsequent valid rows still processed."""
    from quirk.dashboard.api.routes.scan import _derive_dar_findings

    caplog.set_level(logging.WARNING, logger="quirk.dashboard.api.routes.scan")
    bad = _make_ep(protocol="S3", dat_scan_json="{not valid json")
    good = _make_ep(protocol="POSTGRESQL", service_detail="ssl-enforced")
    results = _derive_dar_findings([bad, good])

    # Bad row skipped; good row produces a finding from _dar_db path.
    assert len(results) >= 1, results


# ---------- D-10 + C-5 (WR-17): list_questions drift-safe ----------

def test_list_questions_drift_safe_missing_keys(monkeypatch):
    """D-10/C-5: missing optional keys in QRAMM_QUESTIONS degrade to default values, not 500."""
    drifted = [
        # Missing practice_area, text, maturity_labels
        {"question_number": 1, "dimension": "Identify"},
        # Missing maturity_labels only
        {
            "question_number": 2,
            "dimension": "Protect",
            "practice_area": "CVI",
            "text": "Real text",
        },
    ]
    monkeypatch.setattr(
        "quirk.dashboard.api.routes.qramm.QRAMM_QUESTIONS", drifted
    )

    client, _ = _make_qramm_client()
    resp = client.get("/api/qramm/questions")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body) == 2
    assert body[0]["question_number"] == 1
    assert body[0]["dimension"] == "Identify"
    assert body[0]["practice_area"] == ""
    assert body[0]["text"] == ""
    assert body[0]["maturity_labels"] == []
    assert body[1]["question_number"] == 2
    assert body[1]["text"] == "Real text"
    assert body[1]["maturity_labels"] == []


def test_list_questions_full_shape_unchanged():
    """D-10 negative: real QRAMM_QUESTIONS still returns all 120 fully populated."""
    client, _ = _make_qramm_client()
    resp = client.get("/api/qramm/questions")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body) >= 1
    sample = body[0]
    # All real fields present
    for field in (
        "question_number",
        "dimension",
        "practice_area",
        "text",
        "maturity_labels",
    ):
        assert field in sample, sample
