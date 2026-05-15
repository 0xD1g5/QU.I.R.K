"""D-07 / WR-09: `_build_interpretation` guards score['score'] access (Phase 73)."""
from quirk.reports.executive import _INTERPRETATION_UNAVAILABLE, _build_interpretation


def test_build_interpretation_with_full_score_dict():
    """Happy path: score dict has both 'score' and 'rating' keys."""
    result = _build_interpretation(
        evidence={}, score={"score": 75, "rating": "Good"}, endpoints=[], findings=[]
    )
    joined = " ".join(result["bullets"])
    assert "75" in joined
    assert "Good" in joined
    assert _INTERPRETATION_UNAVAILABLE not in joined


def test_build_interpretation_with_none_score():
    """None score returns fallback shape (no KeyError)."""
    result = _build_interpretation(
        evidence={}, score=None, endpoints=[], findings=[]
    )
    assert result == {"bullets": [_INTERPRETATION_UNAVAILABLE]}


def test_build_interpretation_with_empty_dict():
    """Empty dict (missing 'score' key) returns fallback shape."""
    result = _build_interpretation(
        evidence={}, score={}, endpoints=[], findings=[]
    )
    assert result == {"bullets": [_INTERPRETATION_UNAVAILABLE]}


def test_build_interpretation_with_non_dict():
    """Non-dict (e.g., string) returns fallback shape (no AttributeError)."""
    result = _build_interpretation(
        evidence={}, score="not a dict", endpoints=[], findings=[]
    )
    assert result == {"bullets": [_INTERPRETATION_UNAVAILABLE]}


def test_build_interpretation_with_missing_rating_key():
    """Score present, rating missing → default rating used, no fallback."""
    result = _build_interpretation(
        evidence={}, score={"score": 50}, endpoints=[], findings=[]
    )
    joined = " ".join(result["bullets"])
    assert "50" in joined
    assert "Unknown" in joined
    assert _INTERPRETATION_UNAVAILABLE not in joined
