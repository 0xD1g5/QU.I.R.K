"""Phase 142 CVE-02: `quirk cve status` CLI entrypoint.

Mirrors `quirk qramm status` (quirk/cli/qramm_cmd.py) and `quirk compliance
status` (quirk/compliance/__init__.py:status_report) — third instance of the
one-catalog-one-command precedent. Reads CVE_TABLE_META from
quirk.scanner.hw_cve, computes days remaining against
STALENESS_THRESHOLD_DAYS, prints a table whose header includes "CVE", and
exits 0 if FRESH or 1 if STALE.

Per Phase 51 DEBT-01, no datetime.utcnow() — use datetime.date.today() for
date-only arithmetic.
"""
from __future__ import annotations

import datetime
import logging
import os
import sys

from quirk.scanner.hw_cve import (
    CVE_TABLE_META,
    STALENESS_THRESHOLD_DAYS,
    status_report,
)

logger = logging.getLogger(__name__)


def _resolve_today() -> datetime.date:
    """Return datetime.date.today(), or the override date when
    QUIRK_CI_STALENESS_OVERRIDE_DATE is set in the environment.

    Override semantics match the pytest gate (tests/test_cve_staleness.py)
    so `QUIRK_CI_STALENESS_OVERRIDE_DATE=2026-09-01 quirk cve status` and the
    corresponding pytest run agree on the verdict.

    Malformed override values are logged and the function falls back to
    datetime.date.today() rather than raising (mirrors qramm_cmd._resolve_today,
    T-142-05).
    """
    override = os.environ.get("QUIRK_CI_STALENESS_OVERRIDE_DATE")
    if override:
        try:
            return datetime.date.fromisoformat(override)
        except (ValueError, KeyError) as e:
            logger.warning("CVE cmd env override invalid: %s", e)
    return datetime.date.today()


def run_cve_status(argv: "list[str] | None" = None) -> None:
    """Print CVE snapshot staleness table and exit 0 (FRESH) or 1 (STALE).

    Accepts an optional "--format json" pass-through delegating to
    hw_cve.status_report("json").
    """
    argv = argv or []
    if "--format" in argv:
        idx = argv.index("--format")
        fmt = argv[idx + 1] if idx + 1 < len(argv) else "text"
        if fmt == "json":
            status_report("json")
            today = _resolve_today()
            last_verified = datetime.date.fromisoformat(
                CVE_TABLE_META["last_verified"]
            )
            age = (today - last_verified).days
            fresh = age <= STALENESS_THRESHOLD_DAYS
            sys.exit(0 if fresh else 1)

    today = _resolve_today()
    last_verified = datetime.date.fromisoformat(CVE_TABLE_META["last_verified"])
    age = (today - last_verified).days
    days_remaining = STALENESS_THRESHOLD_DAYS - age
    fresh = age <= STALENESS_THRESHOLD_DAYS
    verdict = "FRESH" if fresh else "STALE"

    print(
        f"{'CVE Source':<16} {'Last Verified':<14} "
        f"{'Days Remaining':<16} Status"
    )
    print("-" * 70)
    print(
        f"{CVE_TABLE_META['source']:<16} "
        f"{CVE_TABLE_META['last_verified']:<14} "
        f"{days_remaining:<16} "
        f"{verdict}"
    )

    sys.exit(0 if fresh else 1)
