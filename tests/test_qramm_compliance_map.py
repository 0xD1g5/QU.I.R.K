"""Phase 55 QRAMM-15 — compliance_map data + endpoint tests."""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from quirk.qramm.compliance_map import (
    FRAMEWORK_DISPLAY_NAMES,
    FRAMEWORK_KEYS,
    PRACTICE_AREA_NAMES,
    PRACTICE_AREA_TO_DIMENSION,
    QRAMM_COMPLIANCE_WEIGHTS,
    SCANNER_COVERAGE,
)
from quirk.qramm.questions import QRAMM_QUESTIONS


# ---------------- structural tests (no DB) ----------------

def test_compliance_weights_keys_match_questions() -> None:
    expected = {q["practice_area"] for q in QRAMM_QUESTIONS}
    assert set(QRAMM_COMPLIANCE_WEIGHTS.keys()) == expected


def test_all_weight_values_in_range() -> None:
    for pa, fw_map in QRAMM_COMPLIANCE_WEIGHTS.items():
        assert set(fw_map.keys()) == set(FRAMEWORK_KEYS), (
            f"Missing framework keys for {pa}: have {set(fw_map.keys())}"
        )
        for fw, weight in fw_map.items():
            assert isinstance(weight, float), f"{pa}.{fw} not float"
            assert 0.0 <= weight <= 1.0, (
                f"{pa}.{fw} weight {weight} out of [0.0, 1.0]"
            )


def test_scanner_coverage_structure() -> None:
    assert SCANNER_COVERAGE == {
        "CVI": 1.0, "SGRM": 0.0, "DPE": 0.0, "ITR": 0.0,
    }


def test_framework_display_names_match_keys() -> None:
    assert set(FRAMEWORK_DISPLAY_NAMES.keys()) == set(FRAMEWORK_KEYS)


def test_practice_area_to_dimension_map() -> None:
    assert PRACTICE_AREA_TO_DIMENSION["1.1"] == "CVI"
    assert PRACTICE_AREA_TO_DIMENSION["2.1"] == "SGRM"
    assert PRACTICE_AREA_TO_DIMENSION["3.1"] == "DPE"
    assert PRACTICE_AREA_TO_DIMENSION["4.1"] == "ITR"
    assert set(PRACTICE_AREA_TO_DIMENSION.keys()) == set(
        QRAMM_COMPLIANCE_WEIGHTS.keys()
    )


def test_practice_area_names_complete() -> None:
    assert set(PRACTICE_AREA_NAMES.keys()) == set(
        QRAMM_COMPLIANCE_WEIGHTS.keys()
    )
    for v in PRACTICE_AREA_NAMES.values():
        assert isinstance(v, str) and len(v) > 0


def test_no_engine_imports_in_compliance_map() -> None:
    import quirk.qramm.compliance_map as cm
    src = open(cm.__file__).read()
    # Only check import lines — filter to lines that are actual import statements,
    # ignoring comments and docstrings that may reference forbidden modules by name.
    import_lines = [
        ln for ln in src.splitlines()
        if ln.lstrip().startswith("import ") or ln.lstrip().startswith("from ")
    ]
    import_code = "\n".join(import_lines)
    assert "risk_engine" not in import_code, (
        "compliance_map.py must not import risk_engine"
    )
    assert "quirk.scanner" not in import_code, (
        "compliance_map.py must not import from quirk.scanner"
    )


# ---------------- row builder tests (pure function, no DB) ----------------

def _build_score_json(cvi: float, sgrm: float, dpe: float, itr: float) -> str:
    return json.dumps({
        "overall": (cvi + sgrm + dpe + itr) / 4.0,
        "maturity": "Developing",
        "dimensions": {
            "CVI": {"score": cvi, "weighted": cvi, "practices": {}},
            "SGRM": {"score": sgrm, "weighted": sgrm, "practices": {}},
            "DPE": {"score": dpe, "weighted": dpe, "practices": {}},
            "ITR": {"score": itr, "weighted": itr, "practices": {}},
        },
        "profile_multiplier": 1.0,
    })


def _answered(cvi: int = 0, sgrm: int = 0, dpe: int = 0, itr: int = 0) -> dict:
    """Per-dimension answered-question counts (Phase 231 D-02)."""
    return {"CVI": cvi, "SGRM": sgrm, "DPE": dpe, "ITR": itr}


def _rows(score_json, answered):
    """Call the pure row builder the endpoint delegates to (Phase 231).

    The endpoint itself now queries the session's answers, so the old
    db=None direct call cannot see them; the live path is covered by
    test_compliance_map_endpoint_reads_live_answers below.
    """
    from quirk.dashboard.api.routes import qramm as routes

    score_data = json.loads(score_json) if score_json else None
    return routes.build_compliance_rows(score_data, answered)


def _dim_rows(rows, dim):
    out = [r for r in rows if r.dimension == dim]
    assert len(out) == 3 * 8 == 24, dim
    return out


def test_endpoint_returns_96_rows_unscored() -> None:
    rows = _rows(None, _answered())
    assert len(rows) == 12 * 8 == 96
    for row in rows:
        assert row.relevance_score is None
        assert row.coverage_status == "pending"


def test_endpoint_unscored_returns_null_relevance() -> None:
    rows = _rows(None, _answered())
    nulls = sum(1 for r in rows if r.relevance_score is None)
    assert nulls == 96


def test_endpoint_scored_cvi_nonzero() -> None:
    """An answered CVI keeps the scanner ceiling formula (D-02, D-04).

    Phase 231 D-02a: an UNanswered CVI is pending/null, so this fixture now
    states that CVI was assessed (one answered question).
    """
    rows = _rows(
        _build_score_json(cvi=4.0, sgrm=4.0, dpe=4.0, itr=4.0),
        _answered(cvi=1),
    )
    for r in _dim_rows(rows, "CVI"):
        assert r.relevance_score is not None
        assert r.relevance_score > 0.0
        assert r.relevance_score <= r.static_weight  # capped at weight x 1.0
        assert r.scanner_informed is True
        assert r.coverage_status == "covered"


def test_cvi_answered_uses_ceiling_formula() -> None:
    rows = _rows(
        _build_score_json(cvi=2.0, sgrm=0.0, dpe=0.0, itr=0.0),
        _answered(cvi=1),
    )
    ceiling = SCANNER_COVERAGE["CVI"]
    for r in _dim_rows(rows, "CVI"):
        expected = min(r.static_weight * 0.5, ceiling * r.static_weight)
        assert r.relevance_score == pytest.approx(expected, abs=1e-12)
        assert r.coverage_status == "covered"
        assert r.scanner_informed is True


def test_unanswered_manual_dimension_stays_pending() -> None:
    """Phase 74-03 D-10 kept for unanswered dimensions: pending rows are
    excluded from the rollup (relevance_score=None), even when score_json
    carries a number for the dimension (Phase 231 D-02, D-07)."""
    rows = _rows(
        _build_score_json(cvi=4.0, sgrm=4.0, dpe=4.0, itr=4.0),
        _answered(cvi=1),
    )
    for dim in ("SGRM", "DPE", "ITR"):
        for r in _dim_rows(rows, dim):
            assert r.relevance_score is None, dim
            assert r.scanner_informed is False, dim
            assert r.coverage_status == "pending", dim


def test_answered_manual_dimension_is_self_assessed() -> None:
    """Phase 231 D-01/D-02/D-04: an answered SGRM dimension is shown,
    marked self-assessed, and never scanner-informed."""
    rows = _rows(
        _build_score_json(cvi=0.0, sgrm=3.0, dpe=0.0, itr=0.0),
        _answered(sgrm=1),
    )
    for r in _dim_rows(rows, "SGRM"):
        assert r.coverage_status == "self-assessed"
        assert r.scanner_informed is False
        assert r.relevance_score is not None
    for dim in ("CVI", "DPE", "ITR"):
        for r in _dim_rows(rows, dim):
            assert r.coverage_status == "pending", dim
            assert r.relevance_score is None, dim


def test_self_assessed_score_is_full_weight_without_ceiling() -> None:
    """Phase 231 D-03: static_weight x (score / 4.0) — no SCANNER_COVERAGE
    cap (SGRM's ceiling is 0.0) and no D-10a half-weight."""
    assert SCANNER_COVERAGE["SGRM"] == 0.0
    rows = _rows(
        _build_score_json(cvi=0.0, sgrm=3.0, dpe=4.0, itr=1.0),
        _answered(sgrm=1, dpe=5, itr=30),
    )
    for dim, score in (("SGRM", 3.0), ("DPE", 4.0), ("ITR", 1.0)):
        for r in _dim_rows(rows, dim):
            expected = r.static_weight * (score / 4.0)
            assert r.relevance_score == pytest.approx(expected, abs=1e-12), (
                dim, r.practice_number,
            )
            assert r.relevance_score > 0.0 or r.static_weight == 0.0


def test_unanswered_cvi_is_pending_not_covered_zero() -> None:
    """Phase 231 D-02a: with only SGRM answered, CVI used to come back
    covered with a 0.0 score while the scorecard read "Not assessed"."""
    rows = _rows(
        _build_score_json(cvi=0.0, sgrm=3.0, dpe=0.0, itr=0.0),
        _answered(sgrm=1),
    )
    for r in _dim_rows(rows, "CVI"):
        assert r.coverage_status == "pending"
        assert r.relevance_score is None
        # D-04: scanner_informed describes scanner coverage, not this session.
        assert r.scanner_informed is True


def test_self_assessed_unscored_session_has_null_relevance() -> None:
    """Answered but not yet scored: the row is self-assessed, the score is
    unknown (relevance_score None), never 0.0."""
    rows = _rows(None, _answered(sgrm=1))
    for r in _dim_rows(rows, "SGRM"):
        assert r.coverage_status == "self-assessed"
        assert r.relevance_score is None


def test_endpoint_row_shape() -> None:
    rows = _rows(None, _answered())
    sample = rows[0]
    expected_keys = {
        "practice_number", "practice_area", "dimension", "framework",
        "static_weight", "relevance_score", "scanner_informed",
        "coverage_status",  # Phase 74-03 D-10 (WR-11)
    }
    assert set(sample.model_dump().keys()) == expected_keys


def test_endpoint_scanner_informed_matches_coverage() -> None:
    for answered in (_answered(), _answered(cvi=1, sgrm=1, dpe=1, itr=1)):
        rows = _rows(_build_score_json(2.0, 2.0, 2.0, 2.0), answered)
        for r in rows:
            assert r.scanner_informed == (SCANNER_COVERAGE[r.dimension] > 0)


# ---------------- live endpoint (TestClient, real answers) ----------------

def _make_qramm_client():
    """Build a TestClient with isolated UUID-named in-memory SQLite DB.

    Copied verbatim from tests/test_qramm_router.py (no cross-file private
    helper imports).
    """
    import uuid

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


def _first_qn_per_practice(dimension: str) -> list:
    """Lowest question number in each of the dimension's practice areas.

    One answer per practice area, because scoring is weakest-link over
    practices with 0.0 injected for unanswered ones (SCOREFIX-02): a single
    answer would leave the dimension score at 0.0.
    """
    firsts: dict = {}
    for q in QRAMM_QUESTIONS:
        if q["dimension"] == dimension:
            pa = q["practice_area"]
            firsts[pa] = min(firsts.get(pa, q["question_number"]),
                             q["question_number"])
    return sorted(firsts.values())


def test_compliance_map_endpoint_reads_live_answers() -> None:
    client, _ = _make_qramm_client()
    sid = client.post("/api/qramm/sessions", json={}).json()["session_id"]
    resp = client.post(
        f"/api/qramm/sessions/{sid}/answers",
        json={"answers": [
            {"question_number": qn, "answer_value": 3}
            for dim in ("CVI", "SGRM")
            for qn in _first_qn_per_practice(dim)
        ]},
    )
    assert resp.status_code == 200, resp.text
    score = client.post(f"/api/qramm/sessions/{sid}/score")
    assert score.status_code == 200, score.text

    resp = client.get(f"/api/qramm/sessions/{sid}/compliance-map")
    assert resp.status_code == 200, resp.text
    rows = resp.json()
    assert len(rows) == 96
    by_dim: dict = {}
    for r in rows:
        by_dim.setdefault(r["dimension"], []).append(r)
    for r in by_dim["CVI"]:
        assert r["coverage_status"] == "covered"
        assert r["scanner_informed"] is True
        assert r["relevance_score"] is not None
    for r in by_dim["SGRM"]:
        assert r["coverage_status"] == "self-assessed"
        assert r["scanner_informed"] is False
        assert r["relevance_score"] is not None
    nonzero_sgrm = [r for r in by_dim["SGRM"] if r["relevance_score"] > 0.0]
    assert nonzero_sgrm, "self-assessed SGRM rows must carry a real score"
    for dim in ("DPE", "ITR"):
        for r in by_dim[dim]:
            assert r["coverage_status"] == "pending", dim
            assert r["relevance_score"] is None, dim


def test_endpoint_session_not_found_raises_404(monkeypatch) -> None:
    from fastapi import HTTPException
    from quirk.dashboard.api.routes import qramm as routes

    def boom(db, sid):
        raise HTTPException(status_code=404, detail="Session not found")
    monkeypatch.setattr(routes, "_get_session_or_404", boom)

    with pytest.raises(HTTPException) as exc:
        routes.get_compliance_map(session_id=999, db=None)  # type: ignore[arg-type]
    assert exc.value.status_code == 404
