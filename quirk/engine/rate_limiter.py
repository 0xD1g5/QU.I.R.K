from __future__ import annotations

import threading
import time


class TokenBucket:
    """
    Simple token-bucket rate limiter.
    rate_per_sec: tokens added per second
    capacity: max tokens
    """
    def __init__(self, rate_per_sec: float, capacity: float | None = None):
        self.rate = float(rate_per_sec)
        self.capacity = float(capacity if capacity is not None else max(1.0, self.rate))
        self.tokens = self.capacity
        self.updated = time.perf_counter()
        self._cond = threading.Condition()

    def acquire(self, tokens: float = 1.0):
        if self.rate <= 0:
            return
        if tokens > self.capacity:
            raise ValueError(f"tokens {tokens} > capacity {self.capacity}")
        with self._cond:
            while True:
                now = time.perf_counter()
                elapsed = now - self.updated
                self.updated = now
                self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
                if self.tokens >= tokens:
                    self.tokens -= tokens
                    self._cond.notify_all()
                    return
                wait_secs = (tokens - self.tokens) / self.rate
                self._cond.wait(timeout=wait_secs)
