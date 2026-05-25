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
* Decompression is bounded by _MAX_DECOMPRESS_BYTES (20 MB) to prevent zstd
  decompression-bomb attacks (CR-01).  2× the 10 MB HTTPS body limit (D-09).
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

# 20 MB decompression cap — 2× the 10 MB HTTPS body limit (D-09, CR-01).
# A .qpush file that expands beyond this is rejected; prevents zstd bomb attacks.
_MAX_DECOMPRESS_BYTES = 20 * 1024 * 1024

# Required envelope keys (subset that must be present for Phase 108 validation)
_REQUIRED_ENVELOPE_KEYS = frozenset({
    "payload_id",
    "pushed_at",          # required by §3.1; needed for D-08 replay window (WR-02)
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

    .qpush file format (WR-03 framing):
        <JSON header line>\\n<compressed payload bytes>

    The JSON header carries the HMAC-SHA256 signature embedded by export-results:
        {"hmac-sha256": "hmac-sha256=<hex>"}\\n

    Phase 109 will perform cryptographic HMAC verification against the per-sensor
    key stored in the console config.  Phase 108 reads and validates the structure
    of the embedded signature field so the framing contract is established now.

    Air-gap carve-out (D-15): skip_replay_window=True — the ±15-min clock window
    check is omitted because file transit time is unbounded for sneakernet paths.
    payload_id dedup is preserved — Phase 109 will enforce uniqueness.
    """
    file_path: str = args.file
    config_path: str = getattr(args, "config", "config.yaml")

    # Read .qpush file (IN-01: use context manager to ensure fd is closed promptly)
    try:
        with open(file_path, "rb") as fh:
            raw_file = fh.read()
    except OSError as exc:
        print(f"ERROR: cannot read .qpush file: {exc}", file=sys.stderr)
        sys.exit(1)

    # WR-03: parse framing header if present.
    # New format: {"hmac-sha256": "hmac-sha256=<hex>"}\n<compressed-body>
    # Legacy format (no header): raw compressed bytes (first byte is not '{').
    qpush_sig: str | None = None
    if raw_file.startswith(b"{"):
        newline_pos = raw_file.find(b"\n")
        if newline_pos == -1:
            print("ERROR: .qpush file has malformed framing header (no newline)", file=sys.stderr)
            sys.exit(1)
        header_bytes = raw_file[:newline_pos]
        data = raw_file[newline_pos + 1:]
        try:
            header = json.loads(header_bytes.decode("ascii"))
        except (ValueError, UnicodeDecodeError) as exc:
            print(f"ERROR: .qpush framing header is not valid JSON: {exc}", file=sys.stderr)
            sys.exit(1)
        if "hmac-sha256" not in header:
            print(
                "ERROR: .qpush framing header missing 'hmac-sha256' field",
                file=sys.stderr,
            )
            sys.exit(1)
        qpush_sig = header["hmac-sha256"]
        if not isinstance(qpush_sig, str) or not qpush_sig.startswith("hmac-sha256="):
            print(
                "ERROR: .qpush 'hmac-sha256' field has invalid format (expected 'hmac-sha256=<hex>')",
                file=sys.stderr,
            )
            sys.exit(1)
    else:
        # Legacy format: entire file is the compressed body (no embedded signature)
        data = raw_file

    # Decompress with output-size cap (CR-01: prevent zstd decompression bomb).
    # stream_reader().read(N+1) reads at most N+1 bytes; if we get more than
    # _MAX_DECOMPRESS_BYTES the file is maliciously oversized — reject cleanly.
    try:
        dctx = zstandard.ZstdDecompressor()
        raw = dctx.stream_reader(data).read(_MAX_DECOMPRESS_BYTES + 1)
        if len(raw) > _MAX_DECOMPRESS_BYTES:
            print(
                f"ERROR: .qpush decompressed size exceeds {_MAX_DECOMPRESS_BYTES} bytes",
                file=sys.stderr,
            )
            sys.exit(1)
    except SystemExit:
        raise
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
    # qpush_sig is the embedded HMAC-SHA256 from the WR-03 framing header;
    # Phase 109 will perform cryptographic verification against the stored key.
    _ingest_envelope(envelope, config_path, skip_replay_window=True, qpush_sig=qpush_sig)

    sys.exit(0)


def _ingest_envelope(
    envelope: dict,
    config_path: str,
    skip_replay_window: bool = False,
    qpush_sig: str | None = None,
) -> None:
    """Phase 108 ingest stub — deserialize, validate, and print summary.

    Phase 109 replaces this body with:
    - sensor_pushes table dedup (payload_id uniqueness → 409 on replay)
    - CryptoEndpoint persistence from findings
    - received_at console timestamp stamping
    - HMAC-SHA256 verification of qpush_sig against the per-sensor stored key

    skip_replay_window=True: air-gap transport carve-out per D-15.  The ±15-min
    clock-window check is skipped; payload_id dedup is preserved for Phase 109.
    NOTE: payload_id dedup (T-108-10) is NOT enforced here in the Phase 108 stub —
    Phase 109 will enforce it against the sensor_pushes table.

    qpush_sig: the embedded HMAC-SHA256 from the WR-03 .qpush framing header, or
    None for HTTPS push paths (signature travels in X-Sensor-Signature header there).
    Phase 109 will verify qpush_sig against the per-sensor hmac_key stored in the
    console config before persisting the envelope.
    """
    sensor_id = envelope.get("sensor_id", "<unknown>")
    segment = envelope.get("segment", "<unknown>")
    payload_id = envelope.get("payload_id", "<unknown>")
    findings = envelope.get("findings", [])
    finding_count = len(findings) if isinstance(findings, list) else 0
    schema_version = envelope.get("schema_version", "<unknown>")
    sensor_version = envelope.get("sensor_version", "<unknown>")
    sig_status = qpush_sig if qpush_sig is not None else "<none — HTTPS path>"

    print(
        f"Import summary:\n"
        f"  sensor_id:      {sensor_id}\n"
        f"  segment:        {segment}\n"
        f"  payload_id:     {payload_id}\n"
        f"  findings:       {finding_count}\n"
        f"  schema_version: {schema_version}\n"
        f"  sensor_version: {sensor_version}\n"
        f"  qpush_sig:      {sig_status}\n"
        f"  skip_replay_window: {skip_replay_window} (air-gap carve-out, D-15)\n"
        f"  NOTE: DB ingest (sensor_pushes dedup + CryptoEndpoint write) is Phase 109",
        flush=True,
    )
