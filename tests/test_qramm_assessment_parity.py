"""Phase 231 D-09 parity gate (pytest half).

The vitest half is
src/dashboard/src/components/qramm/__tests__/qramm-assessment-parity.test.tsx;
both read the same contract fixture,
src/dashboard/src/lib/__fixtures__/qramm-assessment-contract.json, so either
side drifting turns CI red. Hand-authored test input, not a generator
artifact: it is NOT a generator-drift gate.

This half drives the real API through TestClient: it seeds the fixture's
answers, scores the session, and asserts GET /compliance-map returns exactly
the fixture's rows and per-dimension states (QRAMM-19, D-01..D-04, D-02a,
D-08). It also proves the persisted score is reachable through
GET /api/qramm/sessions/{id}, the server half of the print-page fix (D-20).

Scenario: 3 CVI questions answered (scanner-measured), all 30 SGRM
(self-assessed), 5 DPE (self-assessed although partially answered, D-08),
no ITR (not assessed).
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Dict, Tuple

import pytest

from quirk.qramm.assessment_state import question_dimension_map

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTRACT_PATH = (
    REPO_ROOT / "src" / "dashboard" / "src" / "lib" / "__fixtures__"
    / "qramm-assessment-contract.json"
)

_DIMS = ("CVI", "SGRM", "DPE", "ITR")

# Row coverage_status -> display state. Mirrors the UI-SPEC vocabulary table
# (231-UI-SPEC.md, "Assessment-State Vocabulary").
_STATUS_TO_STATE: Dict[str, str] = {
    "covered": "scanner-measured",
    "partial": "scanner-measured",
    "self-assessed": "self-assessed",
    "pending": "not-assessed",
    "n/a": "not-assessed",
}


def _contract() -> dict:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def _make_qramm_client():
    """Build a TestClient with isolated UUID-named in-memory SQLite DB.

    Copied verbatim from tests/test_qramm_router.py (no cross-file private
    helper imports).
    """
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

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


def _seed_contract_session(contract: dict) -> Tuple[object, int]:
    client, _ = _make_qramm_client()
    sid = client.post("/api/qramm/sessions", json={}).json()["session_id"]
    resp = client.post(
        f"/api/qramm/sessions/{sid}/answers",
        json={"answers": contract["answers"]},
    )
    assert resp.status_code == 200, resp.text
    resp = client.post(f"/api/qramm/sessions/{sid}/score")
    assert resp.status_code == 200, resp.text
    return client, sid


def _assert_rows_equal(got: list, want: list) -> None:
    assert len(got) == len(want) == 96
    for g, w in zip(got, want):
        assert set(g.keys()) == set(w.keys()), w["practice_number"]
        for key in w:
            if key == "relevance_score":
                if w[key] is None:
                    assert g[key] is None, w["practice_number"]
                else:
                    assert g[key] is not None, w["practice_number"]
                    assert g[key] == pytest.approx(w[key], abs=1e-9), (
                        w["practice_number"]
                    )
            else:
                assert g[key] == w[key], (w["practice_number"], key)


def test_contract_catalog_matches_question_catalog() -> None:
    contract = _contract()
    got = {int(k): v for k, v in contract["question_dimensions"].items()}
    assert got == question_dimension_map()
    # Every answered question in the contract maps through that catalog.
    for a in contract["answers"]:
        assert a["question_number"] in got


def test_endpoint_rows_match_contract() -> None:
    contract = _contract()
    client, sid = _seed_contract_session(contract)
    resp = client.get(f"/api/qramm/sessions/{sid}/compliance-map")
    assert resp.status_code == 200, resp.text
    _assert_rows_equal(resp.json(), contract["rows"])


def test_endpoint_dimension_states_match_contract() -> None:
    contract = _contract()
    client, sid = _seed_contract_session(contract)
    rows = client.get(f"/api/qramm/sessions/{sid}/compliance-map").json()
    statuses: Dict[str, set] = {d: set() for d in _DIMS}
    for r in rows:
        statuses[r["dimension"]].add(r["coverage_status"])
    # One status per dimension: the state is a dimension property.
    for dim in _DIMS:
        assert len(statuses[dim]) == 1, (dim, statuses[dim])
    got_status = {d: next(iter(statuses[d])) for d in _DIMS}
    assert got_status == contract["expected_coverage_status"]
    got_state = {d: _STATUS_TO_STATE[s] for d, s in got_status.items()}
    assert got_state == contract["expected_dimension_state"]
    assert contract["expected_dimension_state"] == {
        "CVI": "scanner-measured",
        "SGRM": "self-assessed",
        "DPE": "self-assessed",
        "ITR": "not-assessed",
    }


def test_contract_self_assessed_rows_follow_d03_formula() -> None:
    """Independent of the endpoint, so the fixture is not just a recording."""
    contract = _contract()
    states = contract["expected_dimension_state"]
    checked = 0
    for r in contract["rows"]:
        state = states[r["dimension"]]
        if state == "self-assessed":
            dim_score = contract["score"][r["dimension"]]["score"]
            expected = r["static_weight"] * dim_score / 4.0
            assert r["relevance_score"] == pytest.approx(expected, abs=1e-9)
            assert r["scanner_informed"] is False
            assert r["coverage_status"] == "self-assessed"
            checked += 1
        elif state == "not-assessed":
            assert r["relevance_score"] is None
            assert r["coverage_status"] in ("pending", "n/a")
    assert checked == 2 * 3 * 8  # SGRM + DPE, 3 practice areas, 8 frameworks
    # The SGRM self-assessed rows carry real, non-zero scores.
    assert any(
        r["relevance_score"] for r in contract["rows"]
        if r["dimension"] == "SGRM"
    )


def test_session_endpoint_returns_persisted_score_dict() -> None:
    """D-20 server half: the print page reads the persisted score from
    GET /api/qramm/sessions/{id} (GET /score is a POST-only route)."""
    contract = _contract()
    client, sid = _seed_contract_session(contract)
    resp = client.get(f"/api/qramm/sessions/{sid}")
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"].startswith("application/json")
    score = resp.json()["score"]
    assert isinstance(score, dict)
    for dim in _DIMS:
        want = contract["score"][dim]
        got = score["dimensions"][dim]
        assert got["score"] == pytest.approx(want["score"], abs=1e-9), dim
        assert got["weighted"] == pytest.approx(want["weighted"], abs=1e-9), dim
