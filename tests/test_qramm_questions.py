"""Tests for quirk/qramm/questions.py — QRAMM-03.

Verifies catalog count (120), schema completeness, dimension/practice
distribution, and verbatim CSNP source matching for spot-checked entries.
"""
from __future__ import annotations

from collections import Counter

from quirk.qramm.questions import QRAMM_QUESTIONS, get_question


REQUIRED_KEYS = {"question_number", "dimension", "practice_area", "text", "maturity_labels"}
VALID_DIMENSIONS = {"CVI", "SGRM", "DPE", "ITR"}
VALID_PRACTICE_AREAS = {
    "1.1", "1.2", "1.3",
    "2.1", "2.2", "2.3",
    "3.1", "3.2", "3.3",
    "4.1", "4.2", "4.3",
}


def test_question_count():
    """QRAMM-03: catalog must contain exactly 120 entries."""
    assert len(QRAMM_QUESTIONS) == 120, f"expected 120, got {len(QRAMM_QUESTIONS)}"


def test_question_schema():
    """Each entry has all required keys and 4 maturity labels."""
    for q in QRAMM_QUESTIONS:
        assert REQUIRED_KEYS.issubset(q.keys()), f"Q{q.get('question_number')} missing keys"
        assert isinstance(q["maturity_labels"], list)
        assert len(q["maturity_labels"]) == 4, f"Q{q['question_number']} has {len(q['maturity_labels'])} labels"
        assert isinstance(q["text"], str) and q["text"].strip()
        assert isinstance(q["question_number"], int)


def test_question_dimensions():
    """Each entry has a valid dimension and practice_area."""
    for q in QRAMM_QUESTIONS:
        assert q["dimension"] in VALID_DIMENSIONS, q
        assert q["practice_area"] in VALID_PRACTICE_AREAS, q


def test_question_distribution():
    """Distribution: 30 per dimension, 10 per practice area, sequential numbering."""
    nums = [q["question_number"] for q in QRAMM_QUESTIONS]
    assert nums == list(range(1, 121)), "question_numbers not sequential 1..120"

    dim_counts = Counter(q["dimension"] for q in QRAMM_QUESTIONS)
    assert dim_counts == {"CVI": 30, "SGRM": 30, "DPE": 30, "ITR": 30}, dim_counts

    pa_counts = Counter(q["practice_area"] for q in QRAMM_QUESTIONS)
    for pa in VALID_PRACTICE_AREAS:
        assert pa_counts[pa] == 10, f"{pa} count is {pa_counts[pa]}"


def test_q1_verbatim_csnp_text():
    """Q1 must match CSNP source verbatim (D-01 traceability anchor)."""
    q1 = get_question(1)
    assert q1["text"] == "How does your organization identify cryptographic assets?"
    assert q1["dimension"] == "CVI"
    assert q1["practice_area"] == "1.1"


def test_q120_verbatim_csnp_text():
    """Q120 must match CSNP source verbatim (D-01 traceability anchor)."""
    q120 = get_question(120)
    assert q120["text"] == (
        "How does your organization contribute to industry standards or "
        "best practices for validating cryptographic implementations?"
    )
    assert q120["dimension"] == "ITR"
    assert q120["practice_area"] == "4.3"


def test_get_question_out_of_range():
    """get_question raises IndexError for invalid question_number."""
    import pytest
    with pytest.raises(IndexError):
        get_question(0)
    with pytest.raises(IndexError):
        get_question(121)
