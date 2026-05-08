"""Phase 55 QRAMM-07: `quirk qramm status` CLI entrypoint.

Mirrors `quirk compliance status` (quirk/compliance/__init__.py:status_report)
and `quirk doctor` (quirk/cli/doctor_cmd.py:run_doctor). Reads QRAMM_MODEL
from quirk.qramm.model_meta, computes days remaining against
STALENESS_THRESHOLD_DAYS, prints a four-column table, exits 0 if FRESH or
1 if STALE.

Per Phase 51 DEBT-01, no datetime.utcnow() — use datetime.date.today()
for date-only arithmetic.
"""
from __future__ import annotations

import datetime
import os
import sys

from quirk.qramm.model_meta import QRAMM_MODEL, STALENESS_THRESHOLD_DAYS


def _resolve_today() -> datetime.date:
    """Return datetime.date.today(), or the override date when
    QUIRK_CI_STALENESS_OVERRIDE_DATE is set in the environment.

    Override semantics match the pytest gate (test_qramm_staleness.py) so
    `QUIRK_CI_STALENESS_OVERRIDE_DATE=2026-09-01 quirk qramm status` and
    the corresponding pytest run agree on the verdict.
    """
    override = os.environ.get("QUIRK_CI_STALENESS_OVERRIDE_DATE")
    if override:
        return datetime.date.fromisoformat(override)
    return datetime.date.today()


def run_qramm_status() -> None:
    """Print QRAMM model staleness table and exit 0 (FRESH) or 1 (STALE)."""
    today = _resolve_today()
    last_verified = datetime.date.fromisoformat(QRAMM_MODEL["last_verified"])
    age = (today - last_verified).days
    days_remaining = STALENESS_THRESHOLD_DAYS - age
    fresh = age <= STALENESS_THRESHOLD_DAYS
    verdict = "FRESH" if fresh else "STALE"

    print(
        f"{'QRAMM Version':<16} {'Last Verified':<14} "
        f"{'Days Remaining':<16} Status"
    )
    print("-" * 70)
    print(
        f"{QRAMM_MODEL['qramm_version']:<16} "
        f"{QRAMM_MODEL['last_verified']:<14} "
        f"{days_remaining:<16} "
        f"{verdict}"
    )

    sys.exit(0 if fresh else 1)
