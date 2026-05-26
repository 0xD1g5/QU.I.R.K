"""Unit tests for _sensor_status helper in quirk/dashboard/api/routes/sensor.py.

TDD RED phase — tests define the expected status logic before implementation.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest


def _make_sensor(
    *,
    sensor_id: str = "s1",
    segment: str = "dmz",
    sensor_version: str = "1.0",
    last_push_at=None,
    enrolled_at=None,
    expected_cadence_minutes: int = 1440,
):
    """Build a minimal Sensor-like object with the fields _sensor_status needs."""
    class _FakeSensor:
        pass

    s = _FakeSensor()
    s.sensor_id = sensor_id
    s.segment = segment
    s.sensor_version = sensor_version
    s.last_push_at = last_push_at
    s.enrolled_at = enrolled_at
    s.expected_cadence_minutes = expected_cadence_minutes
    return s


class TestSensorStatus:
    """Tests for the _sensor_status(sensor, now) -> str helper."""

    def _call(self, sensor, now):
        from quirk.dashboard.api.routes.sensor import _sensor_status
        return _sensor_status(sensor, now)

    def test_never_pushed_is_unknown(self):
        """A sensor that has never pushed (last_push_at=None) → 'unknown'."""
        now = datetime(2026, 5, 26, 12, 0, 0)
        enrolled_recently = now - timedelta(days=1)
        s = _make_sensor(last_push_at=None, enrolled_at=enrolled_recently)
        assert self._call(s, now) == "unknown"

    def test_never_pushed_long_ago_is_unknown(self):
        """A sensor enrolled > 30 days ago with no push → 'unknown' (decommissioned)."""
        now = datetime(2026, 5, 26, 12, 0, 0)
        enrolled_old = now - timedelta(days=35)
        s = _make_sensor(last_push_at=None, enrolled_at=enrolled_old)
        assert self._call(s, now) == "unknown"

    def test_never_pushed_no_enrolled_at_is_unknown(self):
        """A sensor with no last_push_at and no enrolled_at → 'unknown'."""
        now = datetime(2026, 5, 26, 12, 0, 0)
        s = _make_sensor(last_push_at=None, enrolled_at=None)
        assert self._call(s, now) == "unknown"

    def test_just_pushed_is_current(self):
        """A sensor that just pushed → 'current'."""
        now = datetime(2026, 5, 26, 12, 0, 0)
        s = _make_sensor(last_push_at=now - timedelta(minutes=5), expected_cadence_minutes=1440)
        assert self._call(s, now) == "current"

    def test_pushed_within_cadence_is_current(self):
        """A sensor that pushed within 2×cadence → 'current'."""
        now = datetime(2026, 5, 26, 12, 0, 0)
        # cadence=60 min → within 2×60=120 min means current
        s = _make_sensor(last_push_at=now - timedelta(minutes=119), expected_cadence_minutes=60)
        assert self._call(s, now) == "current"

    def test_pushed_beyond_2x_cadence_is_stale(self):
        """A sensor that pushed more than 2×cadence ago (but < 30 days) → 'stale'."""
        now = datetime(2026, 5, 26, 12, 0, 0)
        # cadence=60 min → 2×60=120 min threshold; push was 121 min ago
        s = _make_sensor(last_push_at=now - timedelta(minutes=121), expected_cadence_minutes=60)
        assert self._call(s, now) == "stale"

    def test_default_cadence_fallback(self):
        """When expected_cadence_minutes is None, fallback to 1440 min (24h)."""
        now = datetime(2026, 5, 26, 12, 0, 0)
        # last_push 2881 min ago → > 2×1440 → stale
        s = _make_sensor(last_push_at=now - timedelta(minutes=2881), expected_cadence_minutes=None)
        assert self._call(s, now) == "stale"

    def test_silent_beyond_30_days_is_stale_or_current(self):
        """A sensor pushed > 30 days ago (decommissioned threshold) is excluded by
        _build_coverage_warning but _sensor_status still reports based on last_push_at
        vs 2×cadence. If beyond 2×cadence → stale."""
        now = datetime(2026, 5, 26, 12, 0, 0)
        # 31 days ago is beyond 2×1440min cadence (2880 min = 2 days) → stale
        s = _make_sensor(
            last_push_at=now - timedelta(days=31),
            expected_cadence_minutes=1440,
        )
        assert self._call(s, now) == "stale"

    def test_last_push_exactly_at_2x_cadence_is_current(self):
        """Push exactly at 2×cadence boundary: now == last_push + 2×cadence → still current.

        The rule is strictly greater-than (now > last_push + 2×cadence) for stale.
        """
        now = datetime(2026, 5, 26, 12, 0, 0)
        cadence_min = 60
        # Exactly at 2×cadence
        s = _make_sensor(
            last_push_at=now - timedelta(minutes=2 * cadence_min),
            expected_cadence_minutes=cadence_min,
        )
        # now > last_push + 2×cadence → False (equal) → current
        assert self._call(s, now) == "current"
