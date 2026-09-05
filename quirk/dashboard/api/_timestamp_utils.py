"""The single API-layer timestamp-stamping contract (SCORE-03, Phase 184.3).

SCORE-03 measured that ``GET /api/scans`` served ``"scanned_at":
"2026-09-04T15:28:56.218111"`` — no UTC offset — which ECMAScript's
``new Date()`` parses as *local* time, producing a 4-hour skew between the
value stored in the database and the instant a client renders.

Per CONTEXT.md D-01, the database deliberately stores **naive UTC**
datetimes (``datetime.now(timezone.utc).replace(tzinfo=None)`` at ~80 call
sites across the scanner, engine, notify, siem, and ticketing modules).
Migrating those columns to timezone-aware storage was explicitly rejected —
``routes/scan.py`` compares ``scanned_at`` against naive bounds throughout
(the ``SESSION_BRACKET`` logic, job windows), and making storage aware would
turn every one of those into a naive-vs-aware ``TypeError``.

This module is instead the ONE place in the API layer where a UTC offset is
attached to an outgoing instant, on the **serialization direction only**
(D-02, D-03a). It never converts a naive value's wall-clock digits — it
*assumes* naive input is already UTC (the D-01 house pattern) and attaches
``+00:00`` unchanged. An aware, non-UTC input IS converted to UTC first, so
the emitted offset is always ``+00:00``.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Optional

from pydantic import PlainSerializer


def stamp_utc_iso(value: Optional[datetime]) -> Optional[str]:
    """Return ``value`` as an ISO-8601 string carrying a literal ``+00:00``.

    - ``None`` in -> ``None`` out.
    - Naive input is ASSUMED to already be UTC (the D-01 house pattern) and
      gets ``timezone.utc`` ATTACHED via ``replace(tzinfo=...)`` — never
      converted. Converting a naive value here would silently re-introduce
      the exact skew this module exists to remove (naive-UTC storage is not
      naive-local storage).
    - Aware, non-UTC input IS converted to UTC via ``astimezone`` so the
      emitted offset is always the literal ``+00:00`` D-02 selected.
    - A non-datetime input (defensive only — mirrors the existing
      ``hasattr(value, "isoformat")`` guard at ``routes/scan.py:1666``) is
      returned via ``str()`` unchanged rather than raising.
    """
    if value is None:
        return None
    if not hasattr(value, "isoformat"):
        return str(value)
    if value.tzinfo is None:
        aware = value.replace(tzinfo=timezone.utc)
    else:
        aware = value.astimezone(timezone.utc)
    return aware.isoformat()


def _stamp_utc(value: datetime) -> str:
    """Non-Optional wrapper for ``PlainSerializer`` (which never sees ``None``
    — Pydantic short-circuits ``Optional[UTCDateTime] = None`` fields before
    invoking the serializer for the ``None`` case)."""
    result = stamp_utc_iso(value)
    assert result is not None  # pragma: no cover - defensive; see docstring
    return result


# `when_used="json"` is LOAD-BEARING, not an optimization: it scopes the
# offset-stamping to the JSON serialization path only. The default
# `when_used="always"` would ALSO rewrite the value returned by
# `model_dump()` from a `datetime` object into a `str`, which would raise
# `TypeError` at `routes/scan.py:1533-1543`'s naive-datetime bound
# comparisons — the exact failure mode D-01 cited when rejecting a DB
# migration in favor of a serialization-boundary fix.
UTCDateTime = Annotated[
    datetime,
    PlainSerializer(_stamp_utc, return_type=str, when_used="json"),
]
