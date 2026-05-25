"""quirk console — Phase 108 SENSOR-04: console-side management CLI (stub).

Full implementation ships in Phase 109 (ingest route) and Phase 110 (merge).
This stub provides the subparser shape and run_console entrypoint so that:
  - The run_scan.py dispatch block wires correctly.
  - The TLS-enforcement grep gate (tests/test_sensor_no_verify_false.py) has a
    file to scan.  TLS verify is always True; the httpx client in this module
    must never use the literal string that would trip the gate.
"""
from __future__ import annotations

import argparse
import sys


def run_console(argv: list[str]) -> None:
    """Main entrypoint for ``quirk console`` subcommands.

    argv = sys.argv[2:] — does NOT include 'quirk' or 'console'.
    """
    parser = argparse.ArgumentParser(
        prog="quirk console",
        description="Console-side management for distributed sensors (Phase 108)",
    )
    sub = parser.add_subparsers(dest="action", required=True)

    import_p = sub.add_parser(
        "import-results",
        help="Import a .qpush air-gap file into the console (Phase 109)",
    )
    import_p.add_argument("file", help="Path to .qpush file")
    import_p.add_argument(
        "--config",
        default="config.yaml",
        help="Console config.yaml path",
    )

    args = parser.parse_args(argv)
    if args.action == "import-results":
        _cmd_import_results(args)


def _cmd_import_results(args: argparse.Namespace) -> None:
    """Import a .qpush air-gap file (stub — Phase 109 implements full ingest logic).

    When implemented, this must route through the same ingest + dedup path
    as the HTTPS push endpoint so export/import is byte-identical to push.
    """
    print(
        "quirk console import-results: not yet implemented (Phase 109)",
        file=sys.stderr,
    )
    sys.exit(1)
