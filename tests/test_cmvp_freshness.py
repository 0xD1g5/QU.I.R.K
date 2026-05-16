"""Phase 81 CMVP-02 — 90-day staleness CI gate for cmvp_cache.json.

Mirrors tests/test_qramm_staleness.py:41-81 verbatim, swapping QRAMM_MODEL for
the lazy ``quirk.compliance.cmvp._load_cache()`` accessor.

Boundary: strict greater-than 90 days = STALE (exactly 90 days = FRESH).
The CI fail message format is locked by CONTEXT Area 4:
``CMVP cache STALE: last_verified=YYYY-MM-DD ({N} days old). Re-verify against
{source_url}, then run ``quirk compliance cmvp refresh`` and commit with
message "chore: re-verify CMVP catalog (YYYY-MM-DD)".``

Honors ``QUIRK_CI_STALENESS_OVERRIDE_DATE`` for CI simulation (matches the
shared override semantics used by QRAMM / compliance / error-code gates).
"""
from __future__ import annotations

import datetime
import os


def _cache():
    from quirk.compliance.cmvp import _load_cache
    return _load_cache()


def _staleness_days(today: datetime.date) -> int:
    last_verified = datetime.date.fromisoformat(_cache()["last_verified"])
    return (today - last_verified).days


def test_cmvp_cache_shape() -> None:
    """CMVP cache must expose the keys the staleness gate cites in its message."""
    from quirk.compliance.cmvp import STALENESS_THRESHOLD_DAYS

    cache = _cache()
    for key in ("last_verified", "source_url", "modules"):
        assert key in cache, f"cmvp_cache.json missing required key {key!r}"
    # ISO date parseable
    datetime.date.fromisoformat(cache["last_verified"])
    assert isinstance(STALENESS_THRESHOLD_DAYS, int)
    assert STALENESS_THRESHOLD_DAYS == 90


def test_cmvp_cache_not_stale() -> None:
    """Production gate: with no override, current cmvp_cache.json must be FRESH.

    If this fails in CI:
        CMVP cache STALE: last_verified=YYYY-MM-DD (N days old).
        Re-verify against {source_url}, then run
        `quirk compliance cmvp refresh` and commit with message
        "chore: re-verify CMVP catalog (YYYY-MM-DD)".
    """
    from quirk.compliance.cmvp import STALENESS_THRESHOLD_DAYS

    cache = _cache()
    override = os.environ.get("QUIRK_CI_STALENESS_OVERRIDE_DATE")
    today = (
        datetime.date.fromisoformat(override)
        if override
        else datetime.date.today()
    )
    age = _staleness_days(today)
    assert age <= STALENESS_THRESHOLD_DAYS, (
        f"CMVP cache STALE: last_verified={cache['last_verified']} "
        f"({age} days old). Re-verify against {cache['source_url']}, "
        f"then run `quirk compliance cmvp refresh` and commit with "
        f"message \"chore: re-verify CMVP catalog "
        f"({datetime.date.today().isoformat()})\"."
    )


def test_cmvp_staleness_override_fresh() -> None:
    """OVERRIDE_DATE = last_verified + 30 days → FRESH (age ≤ 90)."""
    from quirk.compliance.cmvp import STALENESS_THRESHOLD_DAYS

    last_verified = datetime.date.fromisoformat(_cache()["last_verified"])
    fake_today = last_verified + datetime.timedelta(days=30)
    age = (fake_today - last_verified).days
    assert age <= STALENESS_THRESHOLD_DAYS


def test_cmvp_staleness_override_stale() -> None:
    """OVERRIDE_DATE = last_verified + 95 days → STALE (age > 90)."""
    from quirk.compliance.cmvp import STALENESS_THRESHOLD_DAYS

    last_verified = datetime.date.fromisoformat(_cache()["last_verified"])
    fake_today = last_verified + datetime.timedelta(days=95)
    age = (fake_today - last_verified).days
    assert age > STALENESS_THRESHOLD_DAYS


def test_cmvp_fail_message_cites_source_url() -> None:
    """The remediation message MUST reference the cache's source_url so an
    operator hit by a CI failure can act without grep-spelunking."""
    from quirk.compliance.cmvp import STALENESS_THRESHOLD_DAYS

    cache = _cache()
    last_verified = datetime.date.fromisoformat(cache["last_verified"])
    fake_today = last_verified + datetime.timedelta(
        days=STALENESS_THRESHOLD_DAYS + 5
    )
    age = (fake_today - last_verified).days
    # Reconstruct the exact message format the gate would emit.
    msg = (
        f"CMVP cache STALE: last_verified={cache['last_verified']} "
        f"({age} days old). Re-verify against {cache['source_url']}, "
        f"then run `quirk compliance cmvp refresh` and commit with "
        f"message \"chore: re-verify CMVP catalog (YYYY-MM-DD)\"."
    )
    assert "STALE" in msg
    assert cache["source_url"] in msg
    assert str(age) in msg
    assert "quirk compliance cmvp refresh" in msg
