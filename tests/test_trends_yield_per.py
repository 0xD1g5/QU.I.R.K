"""Phase 77 D-09 / cbom-intel-reports/IN-03 — _fetch_session_endpoints must
use `.yield_per(1000)` (streaming) instead of `.all()` (full materialization).
"""
from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

from quirk.intelligence import trends


def test_fetch_session_endpoints_uses_yield_per_1000() -> None:
    """The session.query(...).filter(...) chain must terminate with .yield_per(1000)."""
    fake_session = MagicMock()
    # Build a chainable mock: db.query(...).filter(...).yield_per(N) returns an iterable.
    chain_tail = MagicMock()
    chain_tail.__iter__ = lambda self: iter([])
    fake_session.query.return_value.filter.return_value.yield_per.return_value = chain_tail

    result = trends._fetch_session_endpoints(fake_session, datetime(2026, 5, 15, 12, 0, 0))

    fake_session.query.return_value.filter.return_value.yield_per.assert_called_once_with(1000)
    # Result is materialized as a list (caller compatibility preserved)
    assert isinstance(result, list)
