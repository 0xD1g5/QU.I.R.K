"""Phase 81 CMVP-03/05: `quirk compliance cmvp refresh|status` CLI dispatcher.

Mirrors quirk/cli/qramm_cmd.py shape. The refresh action fetches NIST CMVP
data via quirk.compliance.cmvp.refresh_cache and routes failures through the
CMVP-REFRESH-* error codes in quirk/errors.py. The status action prints
cache freshness (text or JSON) and exits 0 (FRESH) / 1 (STALE).

v4.10-D-01: no code path here ever emits ``certified: True``. Coverage is
informational; the CMVP-07 AST gate (Plan 81-04) enforces this at CI.
"""
from __future__ import annotations

import datetime
import json
import logging
import os
import sys

logger = logging.getLogger(__name__)


def _resolve_today() -> datetime.date:
    """Return datetime.date.today(), or the override date when
    QUIRK_CI_STALENESS_OVERRIDE_DATE is set.

    Override semantics mirror quirk/cli/qramm_cmd.py:_resolve_today so the CLI
    and pytest gate agree on the verdict.
    """
    override = os.environ.get("QUIRK_CI_STALENESS_OVERRIDE_DATE")
    if override:
        try:
            return datetime.date.fromisoformat(override)
        except (ValueError, KeyError) as e:
            logger.warning("CMVP cmd env override invalid: %s", e)
    return datetime.date.today()


def _emit_error(code: str, detail: str) -> None:
    """Print a formatted error line to stderr using quirk.errors registry."""
    try:
        from quirk.errors import ERROR_CODES
        entry = ERROR_CODES.get(code)
        if entry is not None:
            sys.stderr.write(
                f"[{entry.code}] {entry.cause}\n"
                f"  Detail: {detail}\n"
                f"  Fix: {entry.fix}\n"
            )
            return
    except (ImportError, AttributeError):
        pass
    sys.stderr.write(f"[{code}] {detail}\n")


def _run_refresh(comp_args) -> None:
    from quirk.compliance.cmvp import (
        refresh_cache,
        CMVPRefreshNetworkError,
        CMVPRefreshParseError,
    )
    try:
        result = refresh_cache(dry_run=getattr(comp_args, "dry_run", False))
    except CMVPRefreshNetworkError as e:
        _emit_error("CMVP-REFRESH-NETWORK", str(e))
        sys.exit(1)
    except CMVPRefreshParseError as e:
        _emit_error("CMVP-REFRESH-PARSE", str(e))
        sys.exit(1)

    if getattr(comp_args, "dry_run", False):
        # result is a diff dict
        added = result.get("added", [])
        removed = result.get("removed", [])
        changed = result.get("changed", [])
        print("CMVP refresh DRY-RUN — no files written")
        print(f"  Added   ({len(added):>3}): {', '.join(added) if added else '(none)'}")
        print(f"  Removed ({len(removed):>3}): {', '.join(removed) if removed else '(none)'}")
        print(f"  Changed ({len(changed):>3}): {', '.join(changed) if changed else '(none)'}")
        sys.exit(0)

    # result is the new cache dict
    mod_count = len(result.get("modules", []))
    last_verified = result.get("last_verified", "?")
    if mod_count == 0:
        _emit_error(
            "CMVP-REFRESH-NO-CHANGES",
            "CMVP cache refresh produced 0 modules — bundled cache retained.",
        )
        sys.exit(0)
    print(f"CMVP cache refreshed: {mod_count} modules, last_verified={last_verified}")
    sys.exit(0)


def _run_status(comp_args) -> None:
    """Print CMVP cache freshness table or JSON; exit 0 FRESH / 1 STALE."""
    from quirk.compliance.cmvp import (
        _load_cache,
        STALENESS_THRESHOLD_DAYS,
    )
    cache = _load_cache()
    today = _resolve_today()
    last_verified = datetime.date.fromisoformat(cache["last_verified"])
    age = (today - last_verified).days
    days_remaining = STALENESS_THRESHOLD_DAYS - age
    fresh = age <= STALENESS_THRESHOLD_DAYS
    verdict = "FRESH" if fresh else "STALE"
    module_count = len(cache.get("modules", []))

    fmt = getattr(comp_args, "format", "text")
    if fmt == "json":
        payload = {
            "schema_version": cache.get("schema_version", "1.0"),
            "last_verified": cache["last_verified"],
            "source_url": cache.get("source_url", ""),
            "module_count": module_count,
            "age_days": age,
            "days_remaining": days_remaining,
            "threshold_days": STALENESS_THRESHOLD_DAYS,
            "status": verdict,
        }
        print(json.dumps(payload, indent=2))
    else:
        print(
            f"{'Last Verified':<14} {'Modules':<10} "
            f"{'Days Remaining':<16} Status"
        )
        print("-" * 60)
        print(
            f"{cache['last_verified']:<14} "
            f"{module_count:<10} "
            f"{days_remaining:<16} "
            f"{verdict}"
        )
        print(f"Source: {cache.get('source_url', '')}")

    sys.exit(0 if fresh else 1)


def run_cmvp(comp_args) -> None:
    """Dispatch `compliance cmvp <action>` to refresh or status branch."""
    action = getattr(comp_args, "cmvp_action", None)
    if action == "refresh":
        _run_refresh(comp_args)
    elif action == "status":
        _run_status(comp_args)
    else:
        sys.stderr.write(f"Unknown cmvp action: {action!r}\n")
        sys.exit(2)
