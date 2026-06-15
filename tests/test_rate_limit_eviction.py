"""RED test — AUDIT-06: RateLimitMiddleware idle-bucket eviction.

Contract: after an IP's bucket entries all fall outside the 60-second
rolling window, the bucket must be evicted from self._buckets on the
next dispatch call (no unbounded growth).

This test MUST FAIL against current main because the current implementation
uses a defaultdict(deque) that grows without bound — idle buckets are
never removed.  Wave 2 (plan 131-01) will implement eviction.
"""
from __future__ import annotations

import asyncio
from collections import deque
from unittest.mock import AsyncMock, MagicMock

import pytest

from quirk.dashboard.api.middleware.rate_limit import RateLimitMiddleware, _WINDOW_SECONDS


# ---------------------------------------------------------------------------
# Minimal starlette-compatible stub Request/Response
# ---------------------------------------------------------------------------

class _FakeClient:
    def __init__(self, host: str):
        self.host = host


class _FakeURL:
    def __init__(self, path: str):
        self.path = path


class _FakeRequest:
    """Minimal Request stub exposing .method, .url.path, .client.host."""

    def __init__(self, method: str = "POST", path: str = "/api/jobs", host: str = "10.0.0.1"):
        self.method = method
        self.url = _FakeURL(path)
        self.client = _FakeClient(host)


async def _dummy_call_next(request):
    """Stub call_next that returns a minimal 200 response."""
    from starlette.responses import Response
    return Response(content=b"ok", status_code=200)


# ---------------------------------------------------------------------------
# Test: idle bucket evicted from _buckets after window expires
# ---------------------------------------------------------------------------

def test_idle_bucket_evicted_after_window(monkeypatch):
    """AUDIT-06: a bucket whose only timestamp is outside the rolling window
    must be removed from _buckets (not left as an empty deque) when the next
    dispatch call for any IP occurs.

    Verifies that after IP-A dispatches at t=0, and then a NEW request (from
    any IP) dispatches at t=120 (>60s later), IP-A's bucket is no longer
    present in _buckets.

    EXPECTED FAILURE: current implementation never deletes empty buckets.
    """
    # Construct middleware with a minimal ASGI app stub
    app_stub = MagicMock()
    middleware = RateLimitMiddleware(app=app_stub)

    # Replace time.monotonic so we control the clock
    monotonic_clock = [0.0]

    def fake_monotonic():
        return monotonic_clock[0]

    import quirk.dashboard.api.middleware.rate_limit as rl_mod
    monkeypatch.setattr(rl_mod.time, "monotonic", fake_monotonic)

    # --- t = 0: IP-A makes a POST (mutating) request ---
    req_a = _FakeRequest(method="POST", path="/api/jobs", host="192.168.1.1")
    asyncio.get_event_loop().run_until_complete(
        middleware.dispatch(req_a, _dummy_call_next)
    )

    # IP-A must be in _buckets at t=0 with one timestamp entry
    assert "192.168.1.1" in middleware._buckets, (
        "IP-A must be added to _buckets on first mutating dispatch"
    )
    assert len(middleware._buckets["192.168.1.1"]) == 1, (
        "IP-A bucket must contain exactly 1 timestamp after first dispatch"
    )

    # --- t = 120 (2× window): IP-B makes a POST ---
    monotonic_clock[0] = float(_WINDOW_SECONDS * 2)
    req_b = _FakeRequest(method="POST", path="/api/jobs", host="10.0.0.2")
    asyncio.get_event_loop().run_until_complete(
        middleware.dispatch(req_b, _dummy_call_next)
    )

    # After IP-B's dispatch at t=120, IP-A's single timestamp (at t=0)
    # is 120 seconds old — well outside the 60-second window.
    # The middleware should evict the now-empty bucket for IP-A.
    #
    # AUDIT-06 CONTRACT: idle buckets must be evicted to prevent memory growth.
    # This assertion MUST FAIL today (empty deque is left in _buckets).
    assert "192.168.1.1" not in middleware._buckets, (
        "AUDIT-06 RED: idle IP-A bucket was NOT evicted from _buckets after "
        f"its entries expired. Current _buckets keys: {list(middleware._buckets.keys())}. "
        "Wave 2 (131-01) will implement eviction on each dispatch call."
    )
