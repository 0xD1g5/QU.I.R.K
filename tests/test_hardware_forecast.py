"""Phase 157 (HWLC-18) — pure EOL forecast bucketing + hedged narrative.

RED scaffold: ``quirk/scanner/hardware_forecast.py`` does not exist yet.
Pins the full ``build_eol_forecast()`` contract before any implementation.
"""
from __future__ import annotations

import datetime
import inspect

import pytest

from quirk.scanner.hardware_eol import EOL_TABLE_META


def _strip_comment_lines(source: str) -> str:
    """Strips '#'-comment-only lines before a substring search, mirroring
    tests/test_cve_score_guard.py's helper, so a future explanatory comment
    naming a forbidden token cannot self-invalidate the gate."""
    return "\n".join(
        line for line in source.splitlines() if not line.strip().startswith("#")
    )


def _device(eol_date, tier="Tier 1", **overrides) -> dict:
    row = {
        "vendor": "Cisco",
        "model": "IOS",
        "host": "10.0.0.1",
        "port": 22,
        "pqc_status": "unsupported",
        "remediation_tier": tier,
        "eol_date": eol_date,
        "cnsa_deadline": None,
    }
    row.update(overrides)
    return row


@pytest.mark.parametrize(
    "day_offset,expected_label",
    [
        (-1, "already passed"),
        (0, "0-3 months"),
        (90, "0-3 months"),
        (91, "3-6 months"),
        (180, "3-6 months"),
        (181, "6-12 months"),
        (365, "6-12 months"),
        (366, "12+ months"),
        (5000, "12+ months"),
    ],
)
def test_bucket_boundaries(day_offset, expected_label) -> None:
    from quirk.scanner.hardware_forecast import build_eol_forecast

    today = datetime.date(2026, 8, 16)
    eol_date = (today + datetime.timedelta(days=day_offset)).isoformat()
    result = build_eol_forecast([_device(eol_date)], today=today)

    labels = [bucket["label"] for bucket in result["buckets"]]
    assert labels == [expected_label]


def test_devices_with_null_eol_date_are_excluded() -> None:
    from quirk.scanner.hardware_forecast import build_eol_forecast

    today = datetime.date(2026, 8, 16)
    result = build_eol_forecast([_device(None)], today=today)

    assert result["buckets"] == []
    assert result["narrative"] == ""
    assert result["total_devices_with_eol"] == 0


def test_unparseable_eol_date_is_excluded_not_raised() -> None:
    from quirk.scanner.hardware_forecast import build_eol_forecast

    today = datetime.date(2026, 8, 16)
    result = build_eol_forecast([_device("not-a-date")], today=today)

    assert result["buckets"] == []
    assert result["narrative"] == ""


def test_bucket_sentence_includes_count_and_tier_breakdown() -> None:
    from quirk.scanner.hardware_forecast import build_eol_forecast

    today = datetime.date(2026, 8, 16)
    eol_date = (today + datetime.timedelta(days=30)).isoformat()
    devices = [
        _device(eol_date, tier="Tier 1"),
        _device(eol_date, tier="Tier 1"),
        _device(eol_date, tier="Tier 2"),
    ]
    result = build_eol_forecast(devices, today=today)

    assert len(result["buckets"]) == 1
    bucket = result["buckets"][0]
    assert bucket["count"] == 3
    sentence = bucket["sentence"]
    assert "3" in sentence
    assert "2 Tier 1" in sentence
    assert "1 Tier 2" in sentence


def test_narrative_never_uses_unqualified_will() -> None:
    from quirk.scanner.hardware_forecast import build_eol_forecast

    today = datetime.date(2026, 8, 16)
    devices = [
        _device((today + datetime.timedelta(days=-10)).isoformat()),
        _device((today + datetime.timedelta(days=30)).isoformat()),
        _device((today + datetime.timedelta(days=120)).isoformat()),
        _device((today + datetime.timedelta(days=200)).isoformat()),
        _device((today + datetime.timedelta(days=1000)).isoformat()),
    ]
    result = build_eol_forecast(devices, today=today)

    assert " will " not in result["narrative"]


def test_narrative_cites_last_verified() -> None:
    from quirk.scanner.hardware_forecast import build_eol_forecast

    today = datetime.date(2026, 8, 16)
    devices = [
        _device((today + datetime.timedelta(days=-10)).isoformat()),
        _device((today + datetime.timedelta(days=30)).isoformat()),
        _device((today + datetime.timedelta(days=120)).isoformat()),
        _device((today + datetime.timedelta(days=200)).isoformat()),
        _device((today + datetime.timedelta(days=1000)).isoformat()),
    ]
    result = build_eol_forecast(devices, today=today)

    last_verified = EOL_TABLE_META["last_verified"]
    assert result["catalog_last_verified"] == last_verified
    for bucket in result["buckets"]:
        assert last_verified in bucket["sentence"]


def test_empty_device_list_returns_empty_forecast() -> None:
    from quirk.scanner.hardware_forecast import build_eol_forecast

    result = build_eol_forecast([], today=datetime.date(2026, 8, 16))

    assert result["narrative"] == ""
    assert result["buckets"] == []


def test_forecast_is_deterministic_for_fixed_today() -> None:
    from quirk.scanner.hardware_forecast import build_eol_forecast

    today = datetime.date(2026, 8, 16)
    devices = [
        _device((today + datetime.timedelta(days=-10)).isoformat()),
        _device((today + datetime.timedelta(days=30)).isoformat()),
    ]
    result_1 = build_eol_forecast(devices, today=today)
    result_2 = build_eol_forecast(devices, today=today)

    assert result_1 == result_2


def test_build_eol_forecast_signature_takes_no_score_input() -> None:
    from quirk.scanner.hardware_forecast import build_eol_forecast

    params = set(inspect.signature(build_eol_forecast).parameters)
    assert params <= {"devices", "today"}


def test_forecast_module_does_not_import_drift_events() -> None:
    import pathlib

    import quirk.scanner.hardware_forecast as forecast_module

    source = _strip_comment_lines(pathlib.Path(forecast_module.__file__).read_text())
    for forbidden in ("HardwareDriftEvent", "hardware_drift"):
        assert forbidden not in source, (
            f"quirk/scanner/hardware_forecast.py must never reference {forbidden!r} "
            f"(D-01 forward-only invariant)"
        )
