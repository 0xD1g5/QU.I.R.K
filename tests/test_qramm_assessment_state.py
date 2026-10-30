"""Phase 231 QRAMM-18/19 (D-02, D-02a, D-07, D-09): assessed-state predicate.

``quirk.qramm.assessment_state`` is the one Python definition of "assessed"
per dimension: a dimension is assessed when at least one of its questions has
an answer. It is never a score test, because SCOREFIX-02 injects 0.0 for
unanswered practices (D-07). The dashboard's TS dialect is pinned to the same
contract by tests/test_qramm_assessment_parity.py.
"""
from __future__ import annotations

from quirk.qramm.questions import QRAMM_QUESTIONS

_DIMS = ("CVI", "SGRM", "DPE", "ITR")


def _qns(dimension: str) -> list:
    """Question numbers for a dimension, from the catalog (no range maths)."""
    return sorted(
        q["question_number"] for q in QRAMM_QUESTIONS
        if q["dimension"] == dimension
    )


def test_answered_by_dimension_empty() -> None:
    from quirk.qramm.assessment_state import answered_by_dimension

    assert answered_by_dimension([]) == {
        "CVI": 0, "SGRM": 0, "DPE": 0, "ITR": 0,
    }


def test_answered_by_dimension_counts_via_catalog() -> None:
    from quirk.qramm.assessment_state import answered_by_dimension

    cvi = _qns("CVI")
    sgrm = _qns("SGRM")
    got = answered_by_dimension([cvi[0], sgrm[0], sgrm[1]])
    assert got == {"CVI": 1, "SGRM": 2, "DPE": 0, "ITR": 0}


def test_answered_by_dimension_ignores_unknown_and_dedupes() -> None:
    from quirk.qramm.assessment_state import answered_by_dimension

    known = {q["question_number"] for q in QRAMM_QUESTIONS}
    unknown = max(known) + 1
    assert unknown not in known
    sgrm = _qns("SGRM")
    got = answered_by_dimension([sgrm[0], sgrm[0], unknown, 0, -3])
    assert got == {"CVI": 0, "SGRM": 1, "DPE": 0, "ITR": 0}


def test_is_dimension_assessed() -> None:
    from quirk.qramm.assessment_state import is_dimension_assessed

    assert is_dimension_assessed(0) is False
    assert is_dimension_assessed(1) is True
    assert is_dimension_assessed(30) is True


def test_row_coverage_status_cvi() -> None:
    from quirk.qramm.assessment_state import row_coverage_status

    # D-02a: an unanswered CVI is "Not assessed", not covered-at-zero.
    assert row_coverage_status("CVI", 0) == "pending"
    assert row_coverage_status("CVI", 1) == "covered"


def test_row_coverage_status_manual_dimensions() -> None:
    from quirk.qramm.assessment_state import row_coverage_status

    for dim in ("SGRM", "DPE", "ITR"):
        assert row_coverage_status(dim, 0) == "pending", dim
        assert row_coverage_status(dim, 1) == "self-assessed", dim
        assert row_coverage_status(dim, 30) == "self-assessed", dim


def test_question_dimension_map_is_catalog_copy() -> None:
    from quirk.qramm.assessment_state import question_dimension_map

    m = question_dimension_map()
    assert m == {q["question_number"]: q["dimension"] for q in QRAMM_QUESTIONS}
    assert len(m) == 120
    assert set(m.values()) == set(_DIMS)
    # A copy: mutating it must not change the module's map.
    m[1] = "XXX"
    assert question_dimension_map()[1] != "XXX"


def test_no_engine_imports_in_assessment_state() -> None:
    import quirk.qramm.assessment_state as mod
    with open(mod.__file__, encoding="utf-8") as fh:
        src = fh.read()
    import_lines = [
        ln for ln in src.splitlines()
        if ln.lstrip().startswith("import ") or ln.lstrip().startswith("from ")
    ]
    import_code = "\n".join(import_lines)
    for forbidden in ("risk_engine", "quirk.engine", "quirk.scanner",
                      "quirk.intelligence", "quirk.dashboard"):
        assert forbidden not in import_code, (
            f"assessment_state.py must not import {forbidden}"
        )
