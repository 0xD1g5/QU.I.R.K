"""Phase 194 Plan 01 (VERDICT-01 / D-20): absent-rating sentinel.

`ScoreData.rating` is widened from `str` to `Optional[str] = None`. A
`score_raw` dict genuinely missing the `rating` key must yield
`ScoreData.rating is None`, distinguishable from a computed `"POOR"` — this
is the honest-absence prerequisite for the Executive Verdict layer's
"never computed" branch.
"""
from __future__ import annotations

from quirk.dashboard.api.schemas import ScoreData, SubScores


def test_score_raw_without_rating_key_yields_none():
    score_raw = {"score": None, "subscores": {}, "drivers": []}
    score = ScoreData(
        score=score_raw.get("score"),
        rating=score_raw.get("rating"),
        subscores=SubScores(),
        drivers=score_raw.get("drivers", []),
    )
    assert score.rating is None


def test_score_raw_with_computed_poor_rating_is_distinguishable():
    score_raw = {"score": 12, "rating": "POOR", "subscores": {}, "drivers": []}
    score = ScoreData(
        score=score_raw.get("score"),
        rating=score_raw.get("rating"),
        subscores=SubScores(),
        drivers=score_raw.get("drivers", []),
    )
    assert score.rating == "POOR"


def test_none_and_computed_poor_are_not_the_same_value():
    absent = ScoreData(score=None, rating=None, subscores=SubScores(), drivers=[])
    computed = ScoreData(score=10, rating="POOR", subscores=SubScores(), drivers=[])
    assert absent.rating is None
    assert computed.rating == "POOR"
    assert absent.rating != computed.rating


def test_widened_field_accepts_none_without_validation_error():
    score = ScoreData(score=None, rating=None, subscores=SubScores(), drivers=[])
    assert score.rating is None
    assert score.score is None


def test_rating_cap_reason_still_passes_through_unchanged():
    score = ScoreData(
        score=50,
        rating="MODERATE",
        rating_cap_reason="capped due to unassessed domain",
        subscores=SubScores(),
        drivers=[],
    )
    assert score.rating_cap_reason == "capped due to unassessed domain"
