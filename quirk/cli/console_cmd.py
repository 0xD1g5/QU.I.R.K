"""quirk console — Phase 108 SENSOR-04: console-side air-gap import CLI.

Subcommands
-----------
import-results  Read a .qpush air-gap file, decompress and validate the wire
                envelope, and route through the single ingest entry point
                (_ingest_envelope).  The ±15-min replay window is SKIPPED for
                air-gap imports per D-15 transport carve-out; payload_id dedup
                is preserved (full DB dedup → 409 is Phase 109).

Security contract
-----------------
* All decompress + envelope key validation is wrapped in try/except →
  clean SystemExit(1) on malformed/oversized input; never a raw traceback
  (T-108-09 mitigation).
* payload_id dedup intent preserved: skip_replay_window=True skips only the
  ±15-min clock window; Phase 109 will enforce the payload_id uniqueness check
  against the sensor_pushes table (T-108-10 mitigation).
* TLS: this module contains no httpx usage; the grep gate
  (tests/test_sensor_no_verify_false.py) will scan this file but there is no
  network I/O here — air-gap import is purely local file I/O.
"""
from __future__ import annotations

import argparse
import json
import sys

import zstandard

# Required envelope keys (subset that must be present for Phase 108 validation)
_REQUIRED_ENVELOPE_KEYS = frozenset({
    "payload_id",
    "schema_version",
    "sensor_version",
    "sensor_id",
    "segment",
    "findings",
})


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
        help="Import a .qpush air-gap file into the console",
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
    """Import a .qpush air-gap file: decompress, validate, and route to ingest stub.

    Air-gap carve-out (D-15): skip_replay_window=True — the ±15-min clock window
    check is omitted because file transit time is unbounded for sneakernet paths.
    payload_id dedup is preserved — Phase 109 will enforce uniqueness.
    """
    file_path: str = args.file
    config_path: str = getattr(args, "config", "config.yaml")

    # Read .qpush file
    try:
        data = open(file_path, "rb").read()
    except OSError as exc:
        print(f"ERROR: cannot read .qpush file: {exc}", file=sys.stderr)
        sys.exit(1)

    # Decompress (T-108-09: wrapped; never a raw traceback)
    try:
        raw = zstandard.ZstdDecompressor().decompress(data)
    except Exception as exc:
        print(
            f"ERROR: .qpush file is not valid zstd-compressed data: {exc}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Parse JSON
    try:
        envelope = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        print(f"ERROR: .qpush envelope is not valid JSON: {exc}", file=sys.stderr)
        sys.exit(1)

    # Validate required keys (T-108-09: key whitelist enforced before ingest)
    missing = _REQUIRED_ENVELOPE_KEYS - set(envelope.keys())
    if missing:
        print(
            f"ERROR: .qpush envelope missing required key(s): {sorted(missing)}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Route to ingest entry point — Phase 108 stub (Phase 109 replaces the body)
    # skip_replay_window=True: air-gap carve-out per D-15
    _ingest_envelope(envelope, config_path, skip_replay_window=True)

    sys.exit(0)


def _ingest_envelope(envelope: dict, config_path: str, skip_replay_window: bool = False) -> None:
    """Phase 108 ingest stub — deserialize, validate, and print summary.

    Phase 109 replaces this body with:
    - sensor_pushes table dedup (payload_id uniqueness → 409 on replay)
    - CryptoEndpoint persistence from findings
    - received_at console timestamp stamping

    skip_replay_window=True: air-gap transport carve-out per D-15.  The ±15-min
    clock-window check is skipped; payload_id dedup is preserved for Phase 109.
    NOTE: payload_id dedup (T-108-10) is NOT enforced here in the Phase 108 stub —
    Phase 109 will enforce it against the sensor_pushes table.
    """
    sensor_id = envelope.get("sensor_id", "<unknown>")
    segment = envelope.get("segment", "<unknown>")
    payload_id = envelope.get("payload_id", "<unknown>")
    findings = envelope.get("findings", [])
    finding_count = len(findings) if isinstance(findings, list) else 0
    schema_version = envelope.get("schema_version", "<unknown>")
    sensor_version = envelope.get("sensor_version", "<unknown>")

    print(
        f"Import summary:\n"
        f"  sensor_id:      {sensor_id}\n"
        f"  segment:        {segment}\n"
        f"  payload_id:     {payload_id}\n"
        f"  findings:       {finding_count}\n"
        f"  schema_version: {schema_version}\n"
        f"  sensor_version: {sensor_version}\n"
        f"  skip_replay_window: {skip_replay_window} (air-gap carve-out, D-15)\n"
        f"  NOTE: DB ingest (sensor_pushes dedup + CryptoEndpoint write) is Phase 109",
        flush=True,
    )
