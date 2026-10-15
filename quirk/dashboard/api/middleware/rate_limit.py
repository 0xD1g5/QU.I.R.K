"""In-process sliding-window rate limiter — Phase 58 / CR-03 / HARDEN-API-03.

60 mutating requests (POST/PUT/DELETE/PATCH) per minute per IP.
GET/HEAD/OPTIONS and /api/health are exempt (D-05, D-10).
Zero new pip dependencies — stdlib only: collections, math, threading, time.
"""
from __future__ import annotations

import json
import logging
import math
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timezone

from quirk.errors import format_error
from quirk.util.safe_exc import safe_str

from starlette.concurrency import run_in_threadpool
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_WINDOW_SECONDS: int = 60
_MAX_REQUESTS: int = 60
_MUTATING_METHODS: frozenset[str] = frozenset({"POST", "PUT", "DELETE", "PATCH"})
_EXEMPT_PATHS: frozenset[str] = frozenset({"/api/health"})
_SENSOR_PUSH_PATH: str = "/api/sensor/push"
# Refused sensor pushes are audited at most once per source per window; the
# next row for that source carries the count of refusals it stands in for.
# The per-source audit state is capped so a rotating-source flood cannot grow
# it without bound (oldest entries are dropped first).
_MAX_AUDIT_SOURCES: int = 4096

logger = logging.getLogger(__name__)


def _write_rate_limited_row(request: Request, client_ip: str, coalesced: int = 0) -> None:
    """Record a refused sensor push (225.1 D-12). Never raises.

    Uses the app's ``get_db`` (honouring ``dependency_overrides``) and reads no
    token: the request was refused before authentication. *coalesced* is the
    number of earlier refusals from this source that were not written as
    rows of their own.
    """
    try:
        from quirk.dashboard.api.deps import get_db
        from quirk.models import IntegrationDelivery

        getdb = request.app.dependency_overrides.get(get_db, get_db)
        gen = getdb()
        try:
            db = next(gen)
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            db.add(IntegrationDelivery(
                scan_id=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                finding_hash=None,
                destination="sensor_push",
                status="rate_limited",
                attempted_at=now,
                error_summary=(
                    "rate_limited" if not coalesced else
                    f"rate_limited ({coalesced} further refusals since the previous record)"
                ),
                client_ip=client_ip if client_ip != "unknown" else None,
                sensor_id=None,
            ))
            db.commit()
        finally:
            gen.close()
    except Exception as exc:
        logger.warning("Rate-limit audit row failed: %s", safe_str(exc))


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window token bucket: 60 mutating req/min/IP (D-09 / D-10).

    Thread-safe via threading.Lock around deque read-modify-write.
    Data structure: defaultdict(deque) mapping client_host -> deque[float]
    of time.monotonic() timestamps within the current window.
    """

    def __init__(self, app) -> None:
        super().__init__(app)
        self._buckets: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()
        # Sensor-push audit coalescing: source -> monotonic time of its last
        # audit row, and source -> refusals not yet written.
        self._audited: dict[str, float] = {}
        self._unrecorded: dict[str, int] = {}

    def _note_refusal(self, client_ip: str, now: float) -> "int | None":
        """Account one refused sensor push. Caller holds ``self._lock``.

        Returns the coalesced count to write with a new audit row, or None
        when this refusal is folded into the source's current window.
        """
        last = self._audited.get(client_ip)
        if last is not None and now - last < _WINDOW_SECONDS:
            self._unrecorded[client_ip] = self._unrecorded.get(client_ip, 0) + 1
            return None
        self._audited.pop(client_ip, None)
        self._audited[client_ip] = now
        coalesced = self._unrecorded.pop(client_ip, 0)
        while len(self._audited) > _MAX_AUDIT_SOURCES:
            oldest = next(iter(self._audited))
            del self._audited[oldest]
            self._unrecorded.pop(oldest, None)
        return coalesced

    async def dispatch(self, request: Request, call_next) -> Response:
        if (
            request.method not in _MUTATING_METHODS
            or request.url.path in _EXEMPT_PATHS
        ):
            return await call_next(request)

        client_ip: str = request.client.host if request.client else "unknown"
        now: float = time.monotonic()

        limited = False
        audit_count: "int | None" = None
        retry_after: int = 1
        with self._lock:
            bucket: deque = self._buckets[client_ip]
            # Trim expired entries from the front of the window
            cutoff: float = now - _WINDOW_SECONDS
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()

            # AUDIT-06: evict idle buckets to bound memory under unique-IP load.
            # Collect keys first (never mutate dict during iteration), then delete.
            idle_ips = [
                ip for ip, bkt in self._buckets.items()
                if not bkt or bkt[-1] <= cutoff
            ]
            for ip in idle_ips:
                del self._buckets[ip]

            # Re-fetch (or re-create via defaultdict) after eviction sweep so
            # the current client's bucket is still accessible for the rate check.
            bucket = self._buckets[client_ip]

            if len(bucket) >= _MAX_REQUESTS:
                oldest: float = bucket[0]
                retry_after = math.ceil(_WINDOW_SECONDS - (now - oldest))
                limited = True
                if request.url.path == _SENSOR_PUSH_PATH:
                    audit_count = self._note_refusal(client_ip, now)
            else:
                bucket.append(now)

        if limited:
            if audit_count is not None:
                await run_in_threadpool(
                    _write_rate_limited_row, request, client_ip, audit_count
                )
            return Response(
                content=json.dumps({"detail": format_error("DASHBOARD-003")}).encode(),
                status_code=429,
                media_type="application/json",
                headers={"Retry-After": str(max(retry_after, 1))},
            )

        return await call_next(request)
