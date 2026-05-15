"""Phase 74-03 (D-11, WR-12): is_qramm_model_stale public helper tests.

Centralizes staleness math (currently duplicated across modules). Uses nested
`QRAMM_MODEL["last_verified"]` access — NO module-level `LAST_VERIFIED`
constant per RESEARCH C-6 + user input override.

QRAMM_MODEL["last_verified"] = "2026-05-05"; STALENESS_THRESHOLD_DAYS = 90.
Boundary: `age > STALENESS_THRESHOLD_DAYS` (strict greater-than).
"""
from __future__ import annotations

import datetime

import pytest

from quirk.qramm.model_meta import is_qramm_model_stale


def test_is_qramm_model_stale_far_future_is_stale() -> None:
    """2026-12-31 is ~240 days past 2026-05-05 — clearly stale."""
    assert is_qramm_model_stale(today=datetime.date(2026, 12, 31)) is True


def test_is_qramm_model_stale_near_date_is_fresh() -> None:
    """2026-05-15 is ~10 days past 2026-05-05 — well within threshold."""
    assert is_qramm_model_stale(today=datetime.date(2026, 5, 15)) is False


def test_is_qramm_model_stale_default_today_returns_bool() -> None:
    """Default `today=None` defaults to today() and returns a bool."""
    result = is_qramm_model_stale()
    assert isinstance(result, bool)


@pytest.mark.parametrize(
    "today,expected",
    [
        # 2026-05-05 + 90 days = 2026-08-03 — `age == 90`, not stale (strict `>`)
        (datetime.date(2026, 8, 3), False),
        # 2026-05-05 + 91 days = 2026-08-04 — `age == 91`, stale
        (datetime.date(2026, 8, 4), True),
    ],
)
def test_is_qramm_model_stale_boundary(today: datetime.date, expected: bool) -> None:
    """Boundary at age == STALENESS_THRESHOLD_DAYS is NOT stale."""
    assert is_qramm_model_stale(today=today) is expected
