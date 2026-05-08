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


# ---------------- endpoint tests (direct function call) ----------------

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


class _FakeSession:
    """Stand-in for QRAMMSession ORM row for direct-call testing."""

    def __init__(self, score_json):
        self.score_json = score_json


def _call_compliance_map(monkeypatch, score_json):
    from quirk.dashboard.api.routes import qramm as routes

    fake = _FakeSession(score_json)
    monkeypatch.setattr(
        routes, "_get_session_or_404", lambda db, sid: fake
    )
    return routes.get_compliance_map(session_id=1, db=None)  # type: ignore[arg-type]


def test_endpoint_returns_96_rows_unscored(monkeypatch) -> None:
    rows = _call_compliance_map(monkeypatch, None)
    assert len(rows) == 12 * 8 == 96
    for row in rows:
        assert row.relevance_score is None


def test_endpoint_unscored_returns_null_relevance(monkeypatch) -> None:
    rows = _call_compliance_map(monkeypatch, None)
    nulls = sum(1 for r in rows if r.relevance_score is None)
    assert nulls == 96


def test_endpoint_scored_cvi_nonzero(monkeypatch) -> None:
    rows = _call_compliance_map(
        monkeypatch, _build_score_json(cvi=4.0, sgrm=4.0, dpe=4.0, itr=4.0)
    )
    cvi_rows = [r for r in rows if r.dimension == "CVI"]
    assert len(cvi_rows) == 3 * 8 == 24
    for r in cvi_rows:
        assert r.relevance_score is not None
        assert r.relevance_score > 0.0
        assert r.relevance_score <= r.static_weight  # capped at weight × 1.0
        assert r.scanner_informed is True


def test_endpoint_scored_sgrm_dpe_itr_zero(monkeypatch) -> None:
    rows = _call_compliance_map(
        monkeypatch, _build_score_json(cvi=4.0, sgrm=4.0, dpe=4.0, itr=4.0)
    )
    for dim in ("SGRM", "DPE", "ITR"):
        dim_rows = [r for r in rows if r.dimension == dim]
        assert len(dim_rows) == 3 * 8 == 24
        for r in dim_rows:
            assert r.relevance_score == 0.0
            assert r.scanner_informed is False


def test_endpoint_row_shape(monkeypatch) -> None:
    rows = _call_compliance_map(monkeypatch, None)
    sample = rows[0]
    expected_keys = {
        "practice_number", "practice_area", "dimension", "framework",
        "static_weight", "relevance_score", "scanner_informed",
    }
    assert set(sample.model_dump().keys()) == expected_keys


def test_endpoint_scanner_informed_matches_coverage(monkeypatch) -> None:
    rows = _call_compliance_map(monkeypatch, None)
    for r in rows:
        assert r.scanner_informed == (SCANNER_COVERAGE[r.dimension] > 0)


def test_endpoint_session_not_found_raises_404(monkeypatch) -> None:
    from fastapi import HTTPException
    from quirk.dashboard.api.routes import qramm as routes

    def boom(db, sid):
        raise HTTPException(status_code=404, detail="Session not found")
    monkeypatch.setattr(routes, "_get_session_or_404", boom)

    with pytest.raises(HTTPException) as exc:
        routes.get_compliance_map(session_id=999, db=None)  # type: ignore[arg-type]
    assert exc.value.status_code == 404
