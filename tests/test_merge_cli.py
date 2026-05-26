"""Tests for quirk sensor merge CLI dispatch (Phase 110 MERGE-05).

Verifies that `quirk sensor merge` is a thin wrapper over merge_scan():
- Dispatches to merge_scan() and prints scan_id + score + rating; exits 0.
- Prints a WARNING block when coverage_warning is non-null.
- No merge/scoring logic inlined in the CLI (T-110-08 grep gate).
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_merge_result(*, coverage_warning=None, score=72, rating="Moderate"):
    """Return a minimal merge_scan()-like result dict."""
    return {
        "scan_id": "2026-05-25 12:00:00",
        "score": score,
        "rating": rating,
        "subscores": {},
        "drivers": [],
        "coverage_warning": coverage_warning,
        "endpoint_count": 5,
        "sensor_count": 2,
    }


def _make_ctx_manager(return_value=None):
    """Return a MagicMock usable as a context manager."""
    mock_ctx = MagicMock()
    mock_ctx.__enter__ = MagicMock(return_value=return_value or MagicMock())
    mock_ctx.__exit__ = MagicMock(return_value=False)
    return mock_ctx


# ---------------------------------------------------------------------------
# test_merge_cli_dispatch — MERGE-05 (basic dispatch path)
# ---------------------------------------------------------------------------


def test_merge_cli_dispatch(capsys):
    """MERGE-05: run_sensor(['merge']) dispatches to merge_scan and prints scan_id/score/rating; exits 0."""
    fake_result = _make_merge_result()

    with (
        patch("quirk.merge.scan.merge_scan", return_value=fake_result) as mock_merge,
        patch("quirk.dashboard.api.deps._default_db_path", return_value="/tmp/quirk_test.db"),
        patch("quirk.db.init_db", return_value=None),
        patch("quirk.db.get_session", return_value=_make_ctx_manager()),
    ):
        from quirk.cli.sensor_cmd import run_sensor

        with pytest.raises(SystemExit) as exc_info:
            run_sensor(["merge"])

    assert exc_info.value.code == 0

    captured = capsys.readouterr()
    assert "2026-05-25 12:00:00" in captured.out
    assert "72" in captured.out
    assert "Moderate" in captured.out
    assert "WARNING" not in captured.out

    # Confirm merge_scan was called exactly once (thin wrapper — no logic duplicated)
    mock_merge.assert_called_once()


# ---------------------------------------------------------------------------
# test_merge_cli_coverage_warning
# ---------------------------------------------------------------------------


def test_merge_cli_coverage_warning(capsys):
    """When merge_scan returns a non-null coverage_warning, CLI prints WARNING + missing sensors."""
    warning = {
        "missing_sensors": ["sensor-alpha", "sensor-beta"],
        "reason": "2 enrolled sensor(s) have not pushed within 2x their expected cadence",
    }
    fake_result = _make_merge_result(coverage_warning=warning)

    with (
        patch("quirk.merge.scan.merge_scan", return_value=fake_result),
        patch("quirk.dashboard.api.deps._default_db_path", return_value="/tmp/quirk_test.db"),
        patch("quirk.db.init_db", return_value=None),
        patch("quirk.db.get_session", return_value=_make_ctx_manager()),
    ):
        from quirk.cli.sensor_cmd import run_sensor

        with pytest.raises(SystemExit) as exc_info:
            run_sensor(["merge"])

    assert exc_info.value.code == 0

    captured = capsys.readouterr()
    assert "WARNING" in captured.out
    assert "2 enrolled sensor(s)" in captured.out
    assert "  - sensor-alpha" in captured.out
    assert "  - sensor-beta" in captured.out


# ---------------------------------------------------------------------------
# test_merge_cli_custom_db_and_stale_days
# ---------------------------------------------------------------------------


def test_merge_cli_custom_db_and_stale_days():
    """--db and --stale-days args are forwarded to merge_scan."""
    fake_result = _make_merge_result()

    with (
        patch("quirk.merge.scan.merge_scan", return_value=fake_result) as mock_merge,
        patch("quirk.db.init_db", return_value=None),
        patch("quirk.db.get_session", return_value=_make_ctx_manager()),
    ):
        from quirk.cli.sensor_cmd import run_sensor

        with pytest.raises(SystemExit):
            run_sensor(["merge", "--db", "/tmp/custom.db", "--stale-days", "14"])

    # merge_scan was called with stale_days=14
    call_kwargs = mock_merge.call_args[1]
    assert call_kwargs["stale_days"] == 14


# ---------------------------------------------------------------------------
# test_merge_cli_no_merge_logic_inlined — T-110-08 grep gate
# ---------------------------------------------------------------------------


def test_merge_cli_no_merge_logic_inlined():
    """T-110-08: _cmd_merge contains no inlined union/scoring logic.

    Grep gate: sensor_cmd.py must not contain 'build_evidence_summary' or
    'compute_readiness_score' — those live exclusively in merge_scan().
    """
    import inspect
    import quirk.cli.sensor_cmd as mod

    src = inspect.getsource(mod)
    assert "build_evidence_summary" not in src, (
        "CLI must not inline build_evidence_summary — use merge_scan() (T-110-08)"
    )
    assert "compute_readiness_score" not in src, (
        "CLI must not inline compute_readiness_score — use merge_scan() (T-110-08)"
    )
