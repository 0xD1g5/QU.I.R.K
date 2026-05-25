"""quirk.cli.export_cmd — `quirk export` CLI entrypoint (Phase 103 SIEM-01).

Entry point for exporting scan findings to external destinations. Currently
supports:
  --siem    Push one CEF:0 syslog event per finding to the configured SIEM
            target (host/port/protocol from QUIRK_CONFIG_PATH [siem] block).

Usage:
  quirk export --siem [--input PATH] [--output-dir DIR]

Exit codes:
  0  Success — findings exported.
  1  Usage error — no destination flag supplied.
  2  Runtime error — missing file, bad config, or transport error.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from quirk.siem.config import load_siem_config
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


def run_export(argv: list[str]) -> None:
    """quirk export entry point. argv is sys.argv[2:] (after the subcommand name).

    Exit codes:
      0 — success
      1 — usage error (no destination flag)
      2 — runtime error (missing file, bad config, transport failure)
    """
    parser = argparse.ArgumentParser(
        prog="quirk export",
        description=(
            "Export scan findings to an external destination. "
            "Requires at least one destination flag (e.g. --siem)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "EXAMPLES:\n"
            "  quirk export --siem\n"
            "      Push findings from the latest output/findings-*.json to the\n"
            "      SIEM target configured in QUIRK_CONFIG_PATH.\n\n"
            "  quirk export --siem --input /path/to/findings-20260524-120000.json\n"
            "      Push a specific findings file.\n\n"
            "  quirk export --siem --output-dir /data/quirk/output\n"
            "      Search for findings-*.json in a custom output directory.\n"
        ),
    )
    parser.add_argument(
        "--siem",
        action="store_true",
        help="Export findings to SIEM via syslog/CEF (requires [siem] block in QUIRK_CONFIG_PATH)",
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

    args = parser.parse_args(argv)

    # At least one destination flag must be supplied.
    if not args.siem:
        parser.print_help()
        sys.exit(1)

    # --- Resolve the findings file path ---
    if args.input:
        findings_path = args.input
    else:
        findings_path = _find_latest_findings(args.output_dir)

    if not findings_path or not Path(findings_path).exists():
        print(
            f"ERROR: no findings file found. "
            f"Run a scan first, or pass --input <path>.",
            file=sys.stderr,
        )
        sys.exit(2)

    # --- Load findings ---
    try:
        with open(findings_path, encoding="utf-8") as f:
            findings = json.load(f)
    except Exception as exc:
        print(f"ERROR: could not read findings file '{findings_path}': {safe_str(exc)}", file=sys.stderr)
        sys.exit(2)

    if not isinstance(findings, list):
        print(f"ERROR: findings file does not contain a list — got {type(findings).__name__}", file=sys.stderr)
        sys.exit(2)

    # --- SIEM export path ---
    if args.siem:
        cfg = load_siem_config()
        if cfg is None:
            print(
                "ERROR: SIEM config not found. "
                "Set QUIRK_CONFIG_PATH to a YAML file containing a [siem] block.",
                file=sys.stderr,
            )
            sys.exit(2)

        # Acquire a DB session for audit row writes
        try:
            from quirk.db import get_session
            import os

            db_path = os.environ.get("QUIRK_DB_PATH") or "quirk.db"
            from quirk import __version__ as _version

            # Import dispatcher here (deferred — avoids circular imports)
            from quirk.siem.dispatcher import export_findings

            # Use scan_id derived from the findings filename
            import os as _os
            scan_id = _os.path.basename(findings_path)

            with get_session(db_path) as db:
                count = export_findings(findings, cfg, db, scan_id=scan_id)

            print(f"SIEM export complete: {count}/{len(findings)} findings sent.")
            if count < len(findings):
                sys.exit(2)

        except SystemExit:
            raise
        except Exception as exc:
            print(f"ERROR: SIEM export failed: {safe_str(exc)}", file=sys.stderr)
            sys.exit(2)
