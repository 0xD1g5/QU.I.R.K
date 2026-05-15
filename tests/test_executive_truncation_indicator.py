"""Phase 77 D-12 / cbom-intel-reports/IN-06 — Migration Paths truncation at 10
must append "... and {remaining} more (see full report)" indicator when the
total exceeds 10.
"""
from __future__ import annotations

from unittest.mock import patch

from quirk.reports import executive


class _IntelligenceCfg:
    profile = "balanced"
    calibration_overrides = None


class _AssessCfg:
    name = "Test"
    report_owner = "owner"
    data_classification = "CONFIDENTIAL"


class _Cfg:
    intelligence = _IntelligenceCfg()
    assessment = _AssessCfg()


def _make_recs(n: int):
    return [
        {
            "path": f"path-{i}",
            "recommendation": f"recommendation-{i}",
            "host": f"host{i}",
            "port": 443,
            "severity": "MEDIUM",
        }
        for i in range(n)
    ]


def test_migration_paths_truncation_indicator_emitted_when_over_10() -> None:
    recs = _make_recs(15)
    with patch.object(executive, "recommend_migration_paths", return_value=recs):
        md = executive.build_exec_markdown(_Cfg(), endpoints=[], findings=[])
    assert "and 5 more" in md, (
        "Phase 77 D-12: Migration Paths truncation must append "
        "'... and {remaining} more (see full report)' (cbom-intel-reports/IN-06)"
    )
    assert "see full report" in md


def test_migration_paths_no_indicator_when_at_or_below_10() -> None:
    recs = _make_recs(10)
    with patch.object(executive, "recommend_migration_paths", return_value=recs):
        md = executive.build_exec_markdown(_Cfg(), endpoints=[], findings=[])
    assert "and 0 more" not in md
    assert "see full report" not in md
