"""quirk.cli.ticket_cmd — `quirk ticket` CLI entrypoint (Phase 104 TICKET-01, 105 TICKET-02).

Entry point for creating tickets from scan findings.

Usage:
  quirk ticket create [--input PATH] [--output-dir DIR] [--backend {jira,servicenow}]

Exit codes:
  0  Success — tickets created/updated for all findings.
  2  Total failure — no findings processed (bad config, missing file, missing extra).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from quirk.ticketing.config import load_ticketing_config
from quirk.util.optional_extra import is_extra_available
from quirk.util.safe_exc import safe_str


# ---------------------------------------------------------------------------
# Findings file discovery
# ---------------------------------------------------------------------------


def _find_latest_findings(output_dir: str) -> str | None:
    """Return the path to the newest findings-*.json in *output_dir*, or None."""
    candidates = list(Path(output_dir).glob("findings-*.json"))
    if not candidates:
        return None
    return str(max(candidates, key=lambda p: p.stat().st_mtime))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def run_ticket(argv: list[str]) -> None:
    """quirk ticket entry point. argv is sys.argv[2:] (after the subcommand name).

    Exit codes:
      0 — tickets created/updated for all findings
      2 — total failure (missing extra, missing file, bad config, or dispatch error)
    """
    parser = argparse.ArgumentParser(
        prog="quirk ticket",
        description=(
            "Create tickets from scan findings. "
            "Requires [tickets] extra and a [ticketing] block in QUIRK_CONFIG_PATH."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "EXAMPLES:\n"
            "  quirk ticket create\n"
            "      Create tickets from the latest output/findings-*.json.\n\n"
            "  quirk ticket create --input /path/to/findings-20260524-120000.json\n"
            "      Create tickets from a specific findings file.\n\n"
            "  quirk ticket create --output-dir /data/quirk/output\n"
            "      Search for findings-*.json in a custom output directory.\n\n"
            "  quirk ticket create --backend servicenow\n"
            "      Create tickets in ServiceNow instead of Jira.\n"
        ),
    )
    parser.add_argument(
        "action",
        choices=["create"],
        help="Action to perform (currently only 'create' is supported)",
    )
    parser.add_argument(
        "--input",
        default=None,
        metavar="PATH",
        help="Path to a specific findings-*.json file (default: latest in --output-dir)",
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        metavar="DIR",
        help="Directory to search for the latest findings-*.json (default: output)",
    )
    parser.add_argument(
        "--backend",
        choices=["jira", "servicenow"],
        default="jira",
        help="Ticketing backend to use (default: jira)",
    )

    args = parser.parse_args(argv)

    # ISEC-04: advisory + graceful skip if [tickets] not installed
    if not is_extra_available("tickets"):
        print(
            "ERROR: Ticketing skipped — run `pip install quirk[tickets]` to enable.",
            file=sys.stderr,
        )
        sys.exit(2)

    # --- Resolve the findings file path ---
    if args.input:
        findings_path = args.input
    else:
        findings_path = _find_latest_findings(args.output_dir)

    if not findings_path or not Path(findings_path).exists():
        print(
            "ERROR: no findings file found. Run a scan first, or pass --input <path>.",
            file=sys.stderr,
        )
        sys.exit(2)

    # --- Load findings ---
    try:
        with open(findings_path, encoding="utf-8") as f:
            findings = json.load(f)
    except Exception as exc:
        print(f"ERROR: could not read findings file: {safe_str(exc)}", file=sys.stderr)
        sys.exit(2)

    if not isinstance(findings, list):
        print(
            f"ERROR: findings file does not contain a list — got {type(findings).__name__}",
            file=sys.stderr,
        )
        sys.exit(2)

    # --- Load ticketing config ---
    cfg = load_ticketing_config()
    if cfg is None:
        print(
            "ERROR: ticketing config not found. Set QUIRK_CONFIG_PATH.",
            file=sys.stderr,
        )
        sys.exit(2)

    # --- Construct the backend channel (separate from dispatch — WR-02) ---
    # Channel construction is isolated so that ValueError (SSRF), ImportError, or other
    # init errors produce a clearly-labelled message, not "audit-row persistence failed".
    import os  # noqa: PLC0415

    db_path = os.environ.get("QUIRK_DB_PATH") or "quirk.db"
    scan_id = Path(findings_path).stem[:64]  # drop .json, cap at String(64) (WR-03)

    if args.backend == "servicenow":
        if cfg.servicenow is None:
            print(
                "ERROR: [ticketing.servicenow] block not configured. "
                "Add a servicenow sub-block to QUIRK_CONFIG_PATH.",
                file=sys.stderr,
            )
            sys.exit(2)
        try:
            from quirk.ticketing.servicenow import ServiceNowChannel  # noqa: PLC0415
            channel = ServiceNowChannel(cfg.servicenow)
        except (ValueError, ImportError) as exc:
            print(
                f"ERROR: ticketing backend init failed: {safe_str(exc)}",
                file=sys.stderr,
            )
            sys.exit(2)
    else:  # default: jira
        if cfg.jira is None:
            print(
                "ERROR: [ticketing.jira] block not configured. "
                "Add a jira sub-block to QUIRK_CONFIG_PATH.",
                file=sys.stderr,
            )
            sys.exit(2)
        try:
            from quirk.ticketing.jira import JiraChannel  # noqa: PLC0415
            channel = JiraChannel(cfg.jira)
        except (ValueError, ImportError) as exc:
            print(
                f"ERROR: ticketing backend init failed: {safe_str(exc)}",
                file=sys.stderr,
            )
            sys.exit(2)

    # --- Dispatch findings through the constructed channel ---
    try:
        from quirk.db import get_session  # noqa: PLC0415

        with get_session(db_path) as db:
            for finding in findings:
                channel.dispatch_finding(finding, db, scan_id=scan_id)

        print(f"Ticket run complete: {len(findings)} finding(s) processed.")
    except SystemExit:
        raise
    except Exception as exc:
        # Catches DB-level failures after channel construction and dispatch.
        # If this path is reached, all per-finding audit rows may have been rolled
        # back by get_session — no audit records were persisted (WR-04).
        err_msg = safe_str(exc)
        print(
            f"ERROR: audit-row persistence failed, no audit records were saved: {err_msg}",
            file=sys.stderr,
        )
        sys.exit(2)
