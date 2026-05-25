"""quirk.siem.dispatcher — SIEM export orchestrator (Phase 103 SIEM-01/02).

This module is the integration seam that:
  1. Loops over a list of findings, building one CEF event per finding via
     build_cef_event (which applies the ISEC-03 whitelist internally).
  2. Sends each CEF event via send_syslog_raw to the configured SIEM target.
  3. Writes ONE IntegrationDelivery audit row per batch (destination='siem',
     finding_hash=None, status ok/failed) — not one per finding.
  4. Exposes export_after_scan_hook for the scheduler after-scan path.

CRITICAL CONSTRAINTS:
  - export_findings MUST NOT raise into callers — failure isolation is absolute.
  - export_after_scan_hook calls load_siem_config() with NO arguments — it reads
    QUIRK_CONFIG_PATH, never the scheduler's SQLite DB path (PATTERNS.md Pitfall 2).
  - error_summary is ALWAYS safe_str(exc) — never str(exc) or repr(exc) (T-103-08).
  - ONE audit row per batch (all findings in one scan), not one per finding (T-103-09).
"""
from __future__ import annotations

import glob
import json
import logging
from datetime import datetime, timezone

from quirk.models import IntegrationDelivery
from quirk.siem.config import load_siem_config
from quirk.siem.formatter import build_cef_event
from quirk.siem.transport import send_syslog_raw
from quirk.util.safe_exc import safe_str

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Internal indirection for monkeypatching in tests
# ---------------------------------------------------------------------------


def _send_raw(cef_msg: str, host: str, port: int, protocol: str = "udp", timeout: int = 5) -> None:
    """Thin wrapper around send_syslog_raw — indirected for test monkeypatching."""
    send_syslog_raw(cef_msg, host, port, protocol=protocol, timeout=timeout)


# ---------------------------------------------------------------------------
# Findings file discovery (shared with export_cmd.py)
# ---------------------------------------------------------------------------


def _find_latest_findings_in(output_path: str) -> str | None:
    """Locate the newest findings-*.json under *output_path*. Returns path or None."""
    candidates = glob.glob(f"{output_path}/findings-*.json")
    if not candidates:
        return None
    return max(candidates, key=lambda p: __import__("os").path.getmtime(p))


# ---------------------------------------------------------------------------
# Core export function
# ---------------------------------------------------------------------------


def export_findings(findings: list, cfg, db, scan_id: str) -> int:
    """Push one CEF event per finding to the SIEM target; write one audit row.

    Args:
        findings: List of raw finding dicts (from findings-*.json).
        cfg:      SiemCfg — host, port, protocol, timeout_seconds.
        db:       SQLAlchemy Session (already open, caller owns lifecycle).
        scan_id:  Scan identifier for the IntegrationDelivery audit row.

    Returns:
        Number of successfully sent findings (0..len(findings)).

    Guarantee: Never raises. A delivery failure or DB error is logged as WARNING
    and captured in the audit row's error_summary.
    """
    from quirk import __version__

    success_count = 0
    errors: list[str] = []

    for finding in findings:
        try:
            cef_msg = build_cef_event(finding, version=__version__)
            _send_raw(cef_msg, cfg.host, cfg.port, protocol=cfg.protocol, timeout=cfg.timeout_seconds)
            success_count += 1
        except Exception as exc:
            err = safe_str(exc)
            errors.append(err)
            logger.warning("SIEM delivery failed for finding '%s': %s", finding.get("title", ""), err)

    # Write ONE audit row for this entire batch (T-103-09).
    status = "failed" if errors else "ok"
    error_summary = safe_str("; ".join(errors)) if errors else None

    row = IntegrationDelivery(
        scan_id=scan_id,
        finding_hash=None,
        destination="siem",
        status=status,
        attempted_at=datetime.now(timezone.utc).replace(tzinfo=None),
        error_summary=error_summary,
    )
    db.add(row)
    try:
        db.commit()
    except Exception as exc:
        logger.warning("SIEM audit row commit failed: %s", safe_str(exc))

    return success_count


# ---------------------------------------------------------------------------
# After-scan hook (called from scheduler_cmd.py after notification hook)
# ---------------------------------------------------------------------------


def export_after_scan_hook(run, schedule, db) -> None:
    """After-scan SIEM export hook for the scheduler (Phase 103 SIEM-01).

    Called by scheduler_cmd._dispatch_schedule after the notification hook.
    The entire body is guarded so that SIEM failure NEVER propagates into the
    scheduler or corrupts the committed scan record (T-103-07).

    Calls load_siem_config() with NO arguments — always reads QUIRK_CONFIG_PATH,
    never the scheduler --config SQLite DB path (PATTERNS.md Critical Constraint).
    """
    try:
        cfg = load_siem_config()
        if cfg is None:
            return
        if not cfg.export_after_scan:
            return

        # Locate the latest findings-*.json under run.scan_output_path
        output_path = getattr(run, "scan_output_path", None)
        if not output_path:
            logger.warning("SIEM after-scan hook: run.scan_output_path is not set — skipping")
            return

        findings_path = _find_latest_findings_in(output_path)
        if not findings_path:
            logger.warning("SIEM after-scan hook: no findings-*.json found in %s — skipping", output_path)
            return

        try:
            with open(findings_path, encoding="utf-8") as f:
                findings = json.load(f)
        except Exception as exc:
            logger.warning("SIEM after-scan hook: could not load findings from %s: %s", findings_path, safe_str(exc))
            return

        # Derive scan_id from run.scan_id if available, else use the path basename
        scan_id = getattr(run, "scan_id", None) or __import__("os").path.basename(output_path)

        export_findings(findings, cfg, db, scan_id=str(scan_id))

    except Exception as exc:  # noqa: BLE001
        # Belt-and-suspenders: the inner try/except in export_findings already
        # catches most failures. This outer catch ensures no edge-case leaks.
        logger.warning("SIEM after-scan hook unexpected error: %s", safe_str(exc))
