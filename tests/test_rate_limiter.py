"""Tests for quirk.engine.rate_limiter.TokenBucket (BLOCK-06 / CR-07, CR-08).

Covers:
- Capacity guard (CR-07): tokens > capacity raises ValueError immediately
- Condition-based wait (CR-08): no time.sleep busy-wait
- rate <= 0 fast path: returns immediately
- Default acquire(tokens=1.0): succeeds when capacity available
"""
from __future__ import annotations

import threading
import time

import pytest

from quirk.engine import rate_limiter
from quirk.engine.rate_limiter import TokenBucket


def test_acquire_raises_when_tokens_exceed_capacity():
    """CR-07: oversized acquires must raise ValueError mentioning tokens and capacity, not loop forever."""
    bucket = TokenBucket(rate_per_sec=10, capacity=5)
    with pytest.raises(ValueError) as excinfo:
        bucket.acquire(tokens=6)
    msg = str(excinfo.value)
    assert "tokens" in msg
    assert "capacity" in msg


def test_unlimited_rate_fast_path():
    """D-03: rate <= 0 short-circuits before entering Condition path."""
    bucket = TokenBucket(rate_per_sec=0)
    start = time.perf_counter()
    bucket.acquire()
    elapsed = time.perf_counter() - start
    # Should be effectively instantaneous; cap at 100ms to detect accidental blocking.
    assert elapsed < 0.1, f"rate=0 fast path took {elapsed}s, expected < 100ms"


def test_acquire_blocks_via_condition_no_busy_wait(monkeypatch):
    """CR-08: when waiting for refill, acquire must use Condition.wait, not time.sleep."""

    def _raise_if_called(*args, **kwargs):
        raise AssertionError("time.sleep must not be called — use Condition.wait instead")

    monkeypatch.setattr(rate_limiter.time, "sleep", _raise_if_called)

    # Small rate + capacity so first acquire drains and second must wait for refill.
    bucket = TokenBucket(rate_per_sec=10, capacity=1)
    bucket.acquire()  # drains the bucket

    # Second acquire forces wait path; run in a thread with a 2s join.
    done = threading.Event()

    def _worker():
        bucket.acquire()
        done.set()

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    t.join(timeout=2.0)

    assert done.is_set(), "acquire did not return within 2s via Condition.wait path"


def test_acquire_default_token_one_succeeds():
    """Default tokens=1.0 acquire on a fresh bucket returns without raising."""
    bucket = TokenBucket(rate_per_sec=10, capacity=10)
    bucket.acquire()  # default tokens=1.0
