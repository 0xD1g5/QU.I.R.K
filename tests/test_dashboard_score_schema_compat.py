"""Phase 188 SCORE-06 / RQ-3 — dashboard score schema compatibility proof.

CONTEXT.md's "RQ-3 RESOLVED" clause makes the exact schema shape for the
zero-assessed/Optional[int] score discretionary, but MANDATES an explicit
compatibility check: widening ``ScoreData.score`` (and every field that
embeds or mirrors a score) to ``Optional[int]`` must not break any consumer
that constructs these models from a pre-188-shaped payload (no new required
field), and a not-computed / partially-assessed score must survive a
round-trip through ``model_validate`` without raising.

This file also proves the delta-arithmetic guard added at 188-04 Task 1:
``CompareResponse.score_delta`` / ``SubscoreDelta`` fields are ``None`` when
either side of a comparison is unassessed, never a coerced-to-zero delta
(T-188-14 — an Optional score must not crash, and must not fabricate, a
delta/arithmetic route path).
"""
from __future__ import annotations

from quirk.dashboard.api.schemas import (
    CompareResponse,
    CompareScanSummary,
    ScanSession,
    ScoreData,
    SubScores,
    SubscoreDelta,
)


def _full_subscores(**overrides) -> SubScores:
    base = dict(
        hygiene=25, modern_tls=25, identity_trust=25,
        agility_signals=25, data_at_rest=25, data_in_motion=25,
    )
    base.update(overrides)
    return SubScores(**base)


class TestScoreDataOptionalScore:
    """RQ-3: ScoreData.score is Optional[int]; None is the honest "not
    computed" sentinel, never a fabricated 0."""

    def test_none_score_validates_and_round_trips_as_null(self):
        s = ScoreData(
            score=None,
            rating="NOT_ASSESSED",
            subscores=SubScores(
                hygiene=None, modern_tls=None, identity_trust=None,
                agility_signals=None, data_at_rest=None, data_in_motion=None,
            ),
            drivers=[],
        )
        dumped = s.model_dump()
        assert dumped["score"] is None
        # 188 review IN-01: pin the model's known default exactly — a
        # dual-accept (None or 0) would let a serialization change pass silently.
        assert dumped["domains_assessed"] is None
        assert dumped["domains_total"] is None

    def test_partial_coverage_subscore_survives_as_none(self):
        """An individually-unassessed category (e.g. data_in_motion) must
        survive construction and round-trip as None, not as a fabricated 0."""
        s = ScoreData(
            score=81,
            rating="GOOD",
            subscores=SubScores(
                hygiene=24, modern_tls=24, identity_trust=None,
                agility_signals=25, data_at_rest=None, data_in_motion=None,
            ),
            drivers=[],
            domains_assessed=3,
            domains_total=6,
            coverage_disclosure="3 of 6 domains assessed",
        )
        assert s.subscores.identity_trust is None
        assert s.subscores.data_at_rest is None
        assert s.subscores.data_in_motion is None
        assert s.model_dump()["subscores"]["identity_trust"] is None

    def test_pre_188_shaped_payload_still_validates(self):
        """A payload shaped exactly like a pre-188 response (no coverage keys,
        every subscore an int) must remain valid -- no new REQUIRED field."""
        payload = {
            "score": 82,
            "rating": "GOOD",
            "subscores": {
                "hygiene": 25, "modern_tls": 20,
                "identity_trust": 18, "agility_signals": 19,
            },
            "drivers": [],
        }
        s = ScoreData.model_validate(payload)
        assert s.score == 82
        assert s.rating == "GOOD"
        # Fields absent from the pre-188 payload default sanely, not KeyError.
        assert s.domains_assessed is None
        assert s.coverage_disclosure is None
        # SubScores fields not present in the pre-188 payload (data_at_rest,
        # data_in_motion) default to None, not KeyError/ValidationError.
        assert s.subscores.data_at_rest is None
        assert s.subscores.data_in_motion is None

    def test_full_coverage_score_still_validates_as_int(self):
        """A fully-assessed scan (the common case) still produces a plain
        int score -- widening to Optional must not turn a real int into a
        surprising type at the call site."""
        s = ScoreData(score=90, rating="EXCELLENT", subscores=_full_subscores(), drivers=[])
        assert s.score == 90
        assert isinstance(s.score, int)


class TestScanSessionOptionalScore:
    """188 review CR-04: ScanSession.score is Optional[int]; a not-computed
    scan appears in the scan-history list as score=None (rendered as a
    placeholder by the UI), never a fabricated 0 beside rating NOT_ASSESSED."""

    def test_none_score_validates_and_round_trips_as_null(self):
        s = ScanSession(
            scan_id="2026-09-07T00:00:00",
            scanned_at="2026-09-07T00:00:00Z",
            total_endpoints=5,
            score=None,
            rating="NOT_ASSESSED",
        )
        assert s.score is None
        assert s.model_dump()["score"] is None

    def test_int_score_still_validates(self):
        """Phase 199 / TRIAGE-10: ScanSession.score widened Optional[int] ->
        Optional[float] so a fractional score round-trips unchanged. An
        integral input now yields a float value (82 -> 82.0) rather than an
        int -- update, don't drop, the assertion (bool explicitly excluded
        since isinstance(True, (int, float)) would otherwise pass)."""
        s = ScanSession(
            scan_id="2026-09-07T00:00:00",
            scanned_at="2026-09-07T00:00:00Z",
            total_endpoints=5,
            score=82,
        )
        assert s.score == 82
        assert isinstance(s.score, (int, float)) and not isinstance(s.score, bool)

    def test_score_field_omitted_defaults_to_none_not_zero(self):
        """The pre-CR-04 default was 0 — an int the schema could not
        distinguish from a real worst-case score. The default is now the
        honest None sentinel."""
        s = ScanSession.model_validate({
            "scan_id": "x",
            "scanned_at": "2026-09-07T00:00:00Z",
            "total_endpoints": 0,
        })
        assert s.score is None


class TestCompareArithmeticNeverFabricatesZero:
    """T-188-14: an unassessed side must yield an explicit null delta, never
    a coerced-to-zero one, on the /api/compare comparison surface."""

    def test_subscore_delta_none_when_either_side_unassessed(self):
        d = SubscoreDelta(hygiene=None, modern_tls=3)
        assert d.hygiene is None
        assert d.modern_tls == 3

    def test_compare_response_score_delta_optional(self):
        resp = CompareResponse(
            scan_a=CompareScanSummary(
                scan_id="a", scanned_at="2026-01-01T00:00:00Z", score=None,
            ),
            scan_b=CompareScanSummary(
                scan_id="b", scanned_at="2026-01-02T00:00:00Z", score=85,
            ),
            score_delta=None,
            subscore_deltas=SubscoreDelta(),
        )
        assert resp.scan_a.score is None
        assert resp.score_delta is None

    def test_compare_scan_summary_pre_188_shaped_payload_still_validates(self):
        """A payload with an int score (the pre-188 shape) must remain valid."""
        summary = CompareScanSummary.model_validate({
            "scan_id": "x",
            "scanned_at": "2026-01-01T00:00:00Z",
            "score": 77,
        })
        assert summary.score == 77
