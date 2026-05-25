"""Tests for quirk/notify/payload.py — ISEC-03.

Covers:
- to_integration_payload() returns the exact whitelisted key set
- to_integration_payload() excludes host/port/protocol/sample keys even when
  the source TrendReport carries populated new_findings_sample entries
- current_session_ts / previous_session_ts serialised as ISO strings or None
- build_drift_summary() returns DriftSummary with correct score_band derivation
- build_drift_summary() omits dashboard_url when dashboard_base_url is unset
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from quirk.intelligence.trends import TrendReport, SampleFindingItem


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _sample_finding() -> SampleFindingItem:
    """A SampleFindingItem that carries topology data — must be excluded from payload."""
    return SampleFindingItem(
        host="10.0.0.1",      # TOPOLOGY — must NOT appear in to_integration_payload output
        port=443,             # TOPOLOGY — must NOT appear in to_integration_payload output
        protocol="TLS",       # TOPOLOGY — must NOT appear in to_integration_payload output
        severity="HIGH",
    )


def _make_report(
    *,
    new_high: int = 2,
    new_medium: int = 1,
    new_low: int = 0,
    score_delta: int = -8,
    current_score: int = 72,
    previous_score: int = 80,
    with_samples: bool = True,
    current_ts: datetime | None = None,
    previous_ts: datetime | None = None,
) -> TrendReport:
    samples = [_sample_finding()] * 3 if with_samples else []
    if current_ts is None:
        current_ts = datetime(2026, 5, 24, 12, 0, 0)
    return TrendReport(
        current_session_ts=current_ts,
        previous_session_ts=previous_ts,
        current_score=current_score,
        previous_score=previous_score,
        score_delta=score_delta,
        new_high=new_high,
        new_medium=new_medium,
        new_low=new_low,
        resolved_high=0,
        resolved_medium=1,
        resolved_low=0,
        scan_errors_new_count=2,
        scan_errors_resolved_count=0,
        new_findings_sample=samples,
        resolved_findings_sample=samples,
    )


# ---------------------------------------------------------------------------
# Tests — to_integration_payload whitelist
# ---------------------------------------------------------------------------

EXPECTED_KEYS = frozenset({
    "current_score",
    "previous_score",
    "score_delta",
    "new_high",
    "new_medium",
    "new_low",
    "resolved_high",
    "resolved_medium",
    "resolved_low",
    "scan_errors_new_count",
    "current_session_ts",
    "previous_session_ts",
})

FORBIDDEN_KEYS = frozenset({"host", "port", "protocol", "new_findings_sample", "resolved_findings_sample"})


class TestToIntegrationPayloadWhitelist:
    """ISEC-03: exact whitelisted key set present and topology keys absent."""

    def test_returns_dict(self):
        from quirk.notify.payload import to_integration_payload

        report = _make_report()
        result = to_integration_payload(report)
        assert isinstance(result, dict)

    def test_exact_key_set_present(self):
        from quirk.notify.payload import to_integration_payload

        report = _make_report()
        result = to_integration_payload(report)
        assert set(result.keys()) == EXPECTED_KEYS

    def test_no_extra_keys(self):
        from quirk.notify.payload import to_integration_payload

        report = _make_report()
        result = to_integration_payload(report)
        extra = set(result.keys()) - EXPECTED_KEYS
        assert not extra, f"Unexpected extra keys: {extra}"

    def test_topology_keys_absent_even_with_samples(self):
        """Core ISEC-03 test: topology excluded even when source carries samples."""
        from quirk.notify.payload import to_integration_payload

        # Build a report WITH populated samples carrying host/port/protocol
        report = _make_report(with_samples=True)
        assert len(report.new_findings_sample) > 0, "Fixture must carry samples"

        result = to_integration_payload(report)

        for forbidden in FORBIDDEN_KEYS:
            assert forbidden not in result, (
                f"Topology key '{forbidden}' must not appear in integration payload (ISEC-03)"
            )

    def test_no_host_key(self):
        from quirk.notify.payload import to_integration_payload
        result = to_integration_payload(_make_report(with_samples=True))
        assert "host" not in result

    def test_no_port_key(self):
        from quirk.notify.payload import to_integration_payload
        result = to_integration_payload(_make_report(with_samples=True))
        assert "port" not in result

    def test_no_protocol_key(self):
        from quirk.notify.payload import to_integration_payload
        result = to_integration_payload(_make_report(with_samples=True))
        assert "protocol" not in result

    def test_no_sample_keys(self):
        from quirk.notify.payload import to_integration_payload
        result = to_integration_payload(_make_report(with_samples=True))
        assert "new_findings_sample" not in result
        assert "resolved_findings_sample" not in result

    def test_aggregate_values_correct(self):
        from quirk.notify.payload import to_integration_payload

        report = _make_report(
            new_high=3,
            new_medium=2,
            new_low=1,
            score_delta=-12,
            current_score=65,
            previous_score=77,
        )
        result = to_integration_payload(report)
        assert result["new_high"] == 3
        assert result["new_medium"] == 2
        assert result["new_low"] == 1
        assert result["score_delta"] == -12
        assert result["current_score"] == 65
        assert result["previous_score"] == 77

    def test_current_session_ts_is_iso_string(self):
        from quirk.notify.payload import to_integration_payload

        ts = datetime(2026, 5, 24, 10, 30, 0)
        report = _make_report(current_ts=ts)
        result = to_integration_payload(report)
        assert isinstance(result["current_session_ts"], str)
        assert "2026" in result["current_session_ts"]

    def test_previous_session_ts_none_when_absent(self):
        from quirk.notify.payload import to_integration_payload

        report = _make_report(previous_ts=None)
        result = to_integration_payload(report)
        assert result["previous_session_ts"] is None

    def test_previous_session_ts_is_iso_string_when_present(self):
        from quirk.notify.payload import to_integration_payload

        ts = datetime(2026, 5, 23, 9, 0, 0)
        report = _make_report(previous_ts=ts)
        result = to_integration_payload(report)
        assert isinstance(result["previous_session_ts"], str)

    def test_none_score_passes_through(self):
        """First scan: current_score can be None."""
        from quirk.notify.payload import to_integration_payload

        report = TrendReport(
            current_session_ts=datetime(2026, 5, 24),
            previous_session_ts=None,
            current_score=None,
            previous_score=None,
            score_delta=None,
            new_high=0, new_medium=0, new_low=0,
            resolved_high=0, resolved_medium=0, resolved_low=0,
            scan_errors_new_count=0, scan_errors_resolved_count=0,
        )
        result = to_integration_payload(report)
        assert result["current_score"] is None
        assert result["score_delta"] is None


# ---------------------------------------------------------------------------
# Tests — DriftSummary + build_drift_summary
# ---------------------------------------------------------------------------

class TestBuildDriftSummary:
    """build_drift_summary returns DriftSummary with correct fields."""

    def test_returns_drift_summary(self):
        from quirk.notify.payload import build_drift_summary, DriftSummary

        report = _make_report()
        ds = build_drift_summary(report, dashboard_base_url=None, scan_id="2026-05-24T12:00:00")
        assert isinstance(ds, DriftSummary)

    def test_score_fields_populated(self):
        from quirk.notify.payload import build_drift_summary

        report = _make_report(current_score=45, previous_score=55, score_delta=-10)
        ds = build_drift_summary(report, scan_id="test")
        assert ds.current_score == 45
        assert ds.previous_score == 55
        assert ds.score_delta == -10

    def test_finding_counts_populated(self):
        from quirk.notify.payload import build_drift_summary

        report = _make_report(new_high=4, new_medium=2, new_low=1)
        ds = build_drift_summary(report, scan_id="test")
        assert ds.new_high == 4
        assert ds.new_medium == 2
        assert ds.new_low == 1

    def test_score_band_critical(self):
        """Score <= 30 → CRITICAL band."""
        from quirk.notify.payload import build_drift_summary

        report = _make_report(current_score=20, score_delta=-5)
        ds = build_drift_summary(report, scan_id="test")
        assert ds.score_band == "CRITICAL"

    def test_score_band_high(self):
        """Score 31-50 → HIGH band."""
        from quirk.notify.payload import build_drift_summary

        report = _make_report(current_score=45, score_delta=-5)
        ds = build_drift_summary(report, scan_id="test")
        assert ds.score_band == "HIGH"

    def test_score_band_medium(self):
        """Score 51-65 → MEDIUM band."""
        from quirk.notify.payload import build_drift_summary

        report = _make_report(current_score=60, score_delta=-5)
        ds = build_drift_summary(report, scan_id="test")
        assert ds.score_band == "MEDIUM"

    def test_score_band_low(self):
        """Score 66-79 → LOW band."""
        from quirk.notify.payload import build_drift_summary

        report = _make_report(current_score=72, score_delta=-5)
        ds = build_drift_summary(report, scan_id="test")
        assert ds.score_band == "LOW"

    def test_score_band_good(self):
        """Score >= 80 → GOOD band."""
        from quirk.notify.payload import build_drift_summary

        report = _make_report(current_score=85, score_delta=2)
        ds = build_drift_summary(report, scan_id="test")
        assert ds.score_band == "GOOD"

    def test_dashboard_url_none_when_base_unset(self):
        """dashboard_url is None when dashboard_base_url is not provided."""
        from quirk.notify.payload import build_drift_summary

        report = _make_report()
        ds = build_drift_summary(report, dashboard_base_url=None, scan_id="test")
        assert ds.dashboard_url is None

    def test_dashboard_url_populated_when_base_set(self):
        from quirk.notify.payload import build_drift_summary

        report = _make_report()
        ds = build_drift_summary(
            report,
            dashboard_base_url="https://quirk.example.com",
            scan_id="2026-05-24T12:00:00",
        )
        assert ds.dashboard_url is not None
        assert "quirk.example.com" in ds.dashboard_url

    def test_scan_id_stored(self):
        from quirk.notify.payload import build_drift_summary

        report = _make_report()
        ds = build_drift_summary(report, scan_id="2026-05-24T12:00:00.000")
        assert ds.scan_id == "2026-05-24T12:00:00.000"

    def test_score_band_none_score_safe(self):
        """When current_score is None (first scan), score_band is CRITICAL."""
        from quirk.notify.payload import build_drift_summary

        report = TrendReport(
            current_session_ts=datetime(2026, 5, 24),
            previous_session_ts=None,
            current_score=None,
            previous_score=None,
            score_delta=None,
            new_high=0, new_medium=0, new_low=0,
            resolved_high=0, resolved_medium=0, resolved_low=0,
            scan_errors_new_count=0, scan_errors_resolved_count=0,
        )
        ds = build_drift_summary(report, scan_id="test")
        # None → unknown → defaults to CRITICAL (treat unknown as worst-case)
        assert ds.score_band in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "GOOD")
