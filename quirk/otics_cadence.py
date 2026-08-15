"""Advisory-safety control for recurring OT/ICS probing (HWLC-12, Phase 156).

Implements D-16/D-19/D-20/D-21/D-26 from 156-CONTEXT.md: a named, non-overridable
cadence floor below which recurring (scheduled) Modbus/BACnet probing is not
permitted, a deterministic cron minimum-gap derivation that never averages
firing intervals, config-dict inspection helpers, and a strictly-allowlisted
key-stripping helper.

This module performs no I/O and has no side effects — every enforcement point
(dispatch-time hard gate, write-time advisory surfaces in Plan 02) calls into
the same named constant and the same derivation function here, so the floor
value and its wording cannot drift between call sites.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from croniter import croniter

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# The recurring-probe cadence floor, in hours (7 days), per D-19. This is a
# floor, not an operator-overridable default: there is deliberately no config
# key that can lower it. A schedule whose derived minimum firing gap is below
# this value is not permitted to recurringly probe Modbus/BACnet.
OTICS_MIN_INTERVAL_HOURS: int = 168

# The exact, exhaustive allowlist of connectors: keys strip_otics_keys() may
# remove (T-156-03). Removal is by explicit named pop over this two-entry
# tuple — never a substring/heuristic sweep — so stripping cannot collaterally
# disable an unrelated safety control such as enable_snmp.
OTICS_CONNECTOR_KEYS: tuple = ("enable_modbus", "enable_bacnet")

# 10 firings / 9 consecutive gaps, justified in 156-RESEARCH.md D-20.
OTICS_CRON_SAMPLE_COUNT: int = 10

# Write-time operator advisory template (D-26). Placeholders: cron_expr,
# min_gap_hours, floor_hours.
OTICS_FLOOR_ADVISORY_TEMPLATE: str = (
    "OT/ICS minimum cadence floor: schedule {cron_expr!r} fires at least every "
    "{min_gap_hours:.2f}h, below the {floor_hours}h floor. Modbus/BACnet probing "
    "will be suppressed for this schedule if the scheduler is later run with a "
    "config that enables them. Set connectors.enable_recurring_otics and use a "
    "cron interval at or above the floor to allow recurring OT/ICS probing."
)

# Dispatch-time observability line template (D-22). Placeholders: schedule_name,
# cron_expr, removed, reason.
OTICS_SUPPRESSION_LOG_TEMPLATE: str = (
    "OT/ICS probing suppressed for schedule {schedule_name!r} (cron={cron_expr!r}): "
    "removed keys {removed} — reason: {reason}"
)


def _now_naive_utc() -> datetime:
    """Timezone-naive UTC now, matching schedules.py's _utcnow_naive convention."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ---------------------------------------------------------------------------
# Cron derivation
# ---------------------------------------------------------------------------


def min_gap_hours(
    cron_expr: str,
    base: Optional[datetime] = None,
    samples: int = OTICS_CRON_SAMPLE_COUNT,
) -> Optional[float]:
    """Return the minimum consecutive firing gap of ``cron_expr``, in hours.

    Deliberately takes the MINIMUM of consecutive gaps across ``samples``
    firings, never the average — an irregular expression like ``0 0 * * 1,2``
    must report its worst-case (minimum) gap of 24h, not its ~84h average
    (156-RESEARCH.md Common Pitfalls: "Averaging cron gaps instead of taking
    the minimum").

    Entire body is exception-wrapped and returns None on any failure — a
    malformed/unparseable cron expression never raises here (T-156-02).
    Bounded to exactly ``samples`` get_next() iterations so no
    attacker-supplied expression can drive an unbounded loop.
    """
    try:
        if base is None:
            base = _now_naive_utc()
        it = croniter(cron_expr, base)
        firings = [it.get_next(datetime) for _ in range(samples)]
        if len(firings) < 2:
            return None
        gaps_hours = [
            (firings[i + 1] - firings[i]).total_seconds() / 3600.0
            for i in range(len(firings) - 1)
        ]
        return min(gaps_hours)
    except Exception:
        return None


def violates_otics_floor(cron_expr: str, base: Optional[datetime] = None) -> bool:
    """True when ``cron_expr``'s derived minimum gap is below the floor.

    Fail-closed: an underivable cadence (min_gap_hours returns None) is
    treated as violating the floor, never as compliant. For a safety control
    protecting fragile production control systems, an unknown cadence must be
    treated as too fast. A gap exactly equal to the floor satisfies it (not a
    violation).
    """
    gap = min_gap_hours(cron_expr, base=base)
    if gap is None:
        return True
    return gap < OTICS_MIN_INTERVAL_HOURS


# ---------------------------------------------------------------------------
# Config-dict inspection helpers
# ---------------------------------------------------------------------------


def otics_enabled_in_config(base: dict) -> bool:
    """True when either OTICS_CONNECTOR_KEYS entry is truthy in base['connectors']."""
    connectors = base.get("connectors")
    if not isinstance(connectors, dict):
        return False
    return any(bool(connectors.get(key)) for key in OTICS_CONNECTOR_KEYS)


def recurring_otics_opted_in(base: dict) -> bool:
    """True when base['connectors']['enable_recurring_otics'] is truthy."""
    connectors = base.get("connectors")
    if not isinstance(connectors, dict):
        return False
    return bool(connectors.get("enable_recurring_otics"))


def strip_otics_keys(base: dict) -> list:
    """Pop only the OTICS_CONNECTOR_KEYS entries from base['connectors'], in place.

    Explicit named pop per allowlist entry only — never iterates keys and
    matches on a substring like "modbus" (T-156-03). Returns the list of
    names actually removed (empty list when none present / no connectors
    block).
    """
    connectors = base.get("connectors")
    if not isinstance(connectors, dict):
        return []
    removed = []
    for key in OTICS_CONNECTOR_KEYS:
        if key in connectors:
            connectors.pop(key)
            removed.append(key)
    return removed


# ---------------------------------------------------------------------------
# Rendered messages
# ---------------------------------------------------------------------------


def floor_advisory(cron_expr: str) -> Optional[str]:
    """Rendered write-time advisory when cron_expr violates the floor, else None.

    Single function both write-time surfaces (API and CLI) call, so the
    wording cannot diverge between them.
    """
    if not violates_otics_floor(cron_expr):
        return None
    gap = min_gap_hours(cron_expr)
    # gap may be None here (underivable cron) — render 0.0 as the worst case
    # for display purposes; violates_otics_floor already fail-closed on it.
    rendered_gap = gap if gap is not None else 0.0
    return OTICS_FLOOR_ADVISORY_TEMPLATE.format(
        cron_expr=cron_expr,
        min_gap_hours=rendered_gap,
        floor_hours=OTICS_MIN_INTERVAL_HOURS,
    )


def suppression_log_line(
    schedule_name: str, cron_expr: str, removed: list, reason: str
) -> str:
    """Rendered dispatch-time observability line (D-22)."""
    return OTICS_SUPPRESSION_LOG_TEMPLATE.format(
        schedule_name=schedule_name,
        cron_expr=cron_expr,
        removed=removed,
        reason=reason,
    )
