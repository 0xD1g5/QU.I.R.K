"""quirk console — Phase 108 SENSOR-04 / Phase 109 CONSOLE-01: console-side CLI.

Subcommands
-----------
enroll          Provision a sensor: write a sensors row + a sensor_tokens row
                (SHA-256 hash of the minted bearer token) to the console DB,
                and print the raw bearer token once to stdout.

import-results  Read a .qpush air-gap file, decompress and validate the wire
                envelope, and route through the single ingest entry point
                (_ingest_envelope).  The ±15-min replay window is SKIPPED for
                air-gap imports per D-15 transport carve-out; payload_id dedup
                is preserved (full DB dedup → 409 is Phase 109).

Security contract
-----------------
* enroll: raw bearer token is printed once to stdout; only the SHA-256 hex
  digest is stored in sensor_tokens.token_hash — raw token NEVER persisted
  (T-109-01 mitigation).  IntegrityError on duplicate sensor_id triggers a
  clean rollback + fixed error message + sys.exit(1); exception text is never
  printed (T-109-03 / LEAK-02 mitigation).
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
import logging
import sys
import uuid
from datetime import datetime, timezone

import zstandard

logger = logging.getLogger(__name__)

# 20 MB decompression cap — 2× the 10 MB HTTPS body limit (D-09, CR-01).
# A .qpush file that expands beyond this is rejected; prevents zstd bomb attacks.
_MAX_DECOMPRESS_BYTES = 20 * 1024 * 1024
# C-layer zstd window cap. Must be a power of two — zstd rounds max_window_size
# up to the next window-log exponent, so a non-power-of-two (e.g. 20 MB) would
# silently become 32 MB. We set it explicitly to 32 MB (the next valid window
# above the 20 MB application cap); the authoritative 20 MB limit is still
# enforced by the post-read length check below (WR-01).
_ZSTD_MAX_WINDOW = 32 * 1024 * 1024

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

    enroll_p = sub.add_parser(
        "enroll",
        help="Provision a new sensor: write sensors + sensor_tokens rows and mint bearer token",
    )
    enroll_p.add_argument(
        "--sensor-id",
        default=None,
        help="Sensor UUID (generated if omitted; printed to stderr so operator can copy to sensor.yaml)",
    )
    enroll_p.add_argument(
        "--segment",
        required=True,
        help="Network segment label (e.g. dmz, corp, prod)",
    )
    enroll_p.add_argument(
        "--engagement",
        default=None,
        help="Optional engagement tag",
    )
    enroll_p.add_argument(
        "--config",
        default="config.yaml",
        help="Console config.yaml path",
    )

    revoke_p = sub.add_parser(
        "revoke-sensor",
        help="Revoke the active token(s) for a sensor (AUTH-02 / D-07)",
    )
    revoke_p.add_argument("sensor_id", help="Sensor UUID to revoke")
    revoke_p.add_argument(
        "--config",
        default="config.yaml",
        help="Console config.yaml path",
    )

    args = parser.parse_args(argv)
    if args.action == "import-results":
        _cmd_import_results(args)
    elif args.action == "enroll":
        _cmd_enroll(args)
    elif args.action == "revoke-sensor":
        _cmd_revoke_sensor(args)


def _cmd_enroll(args: argparse.Namespace) -> None:
    """Provision a sensor in the console DB and mint a one-time bearer token.

    Writes exactly two rows atomically:
      - sensors:       sensor_id, segment, engagement, enrolled_at, expected_cadence_minutes=1440
      - sensor_tokens: sensor_id (FK), token_hash (SHA-256 hex of raw token), created_at

    The raw bearer token is printed once to stdout; only its SHA-256 hex digest is
    persisted.  The raw token is never stored or logged (T-109-01 mitigation).

    On IntegrityError (duplicate sensor_id or token_hash collision): rollback first,
    emit a fixed error string to stderr, exit 1.  The raw exception is never printed
    (T-109-03 / LEAK-02).

    DB path resolution: QUIRK_DB_PATH env var → canonical quirk-output/quirk.db
    (via _default_db_path()).  --config is accepted for CLI parity with import-results
    but DB path is resolved through the env-var / canonical logic, not config.yaml
    parsing (RESEARCH Open Question 1 recommendation: avoid a YAML dep on the enroll
    path; operators set QUIRK_DB_PATH for non-default locations).
    """
    import hashlib
    import secrets
    from datetime import datetime, timezone

    from sqlalchemy.exc import IntegrityError
    from sqlalchemy.orm import sessionmaker

    from quirk.dashboard.api.deps import _default_db_path
    from quirk.db import init_db
    from quirk.models import Sensor, SensorToken

    # Resolve sensor_id: use provided value or generate a UUID4
    sensor_id = args.sensor_id or str(uuid.uuid4())
    if not args.sensor_id:
        print(f"Generated sensor_id: {sensor_id}", file=sys.stderr)

    segment: str = args.segment
    engagement: str | None = args.engagement

    # STAB-01: pre-check for existing sensor_id BEFORE minting any token.
    # D-01: if already enrolled, exit 0 without printing a token (no token churn).
    # D-02: retain IntegrityError backstop below for the pre-check/insert race window.
    # WR-04: return normally (not sys.exit(0)) — avoids SystemExit in unit tests.
    # T-115-02: fixed-string message; no exception text serialised.
    db_path_precheck = _default_db_path()
    engine_precheck = init_db(db_path_precheck)
    _SessionPrecheck = sessionmaker(
        bind=engine_precheck,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    with _SessionPrecheck() as _pre_db:
        _existing = _pre_db.query(Sensor).filter(Sensor.sensor_id == sensor_id).first()
        if _existing is not None:
            print(
                f"INFO: sensor already enrolled — sensor_id={sensor_id}",
                file=sys.stderr,
            )
            print(f"sensor_id: {sensor_id}", file=sys.stderr)
            return  # D-01: no new token minted; WR-04: return, not sys.exit(0)

    # Mint raw token; derive hash — raw token never persisted (T-109-01)
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    db_path = _default_db_path()
    engine = init_db(db_path)
    Session = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )

    with Session() as db:
        try:
            db.add(
                Sensor(
                    sensor_id=sensor_id,
                    segment=segment,
                    engagement=engagement,
                    enrolled_at=now,
                    last_push_at=None,
                    expected_cadence_minutes=1440,
                    sensor_version=None,
                )
            )
            db.flush()
            db.add(
                SensorToken(
                    sensor_id=sensor_id,
                    token_hash=token_hash,
                    created_at=now,
                )
            )
            db.commit()
        except IntegrityError:
            db.rollback()
            print("ERROR: sensor_id already enrolled", file=sys.stderr)
            sys.exit(1)

    # Print the raw enrollment token once to stdout.
    #
    # v5.5 PER-SENSOR TOKEN MODEL (T-113-09):
    #   This token IS the per-sensor push credential.  It is shown ONCE and never
    #   recoverable — only its SHA-256 hash is persisted in sensor_tokens.
    #   Place this raw value in the sensor's `console_api_token` field in
    #   sensor.yaml on the sensor host.
    #
    #   If this token is lost, run `quirk console revoke-sensor <sensor_id>` and
    #   then re-enroll (`quirk console enroll`) to mint a fresh token + sensor_id.
    #
    #   The shared QUIRK_API_TOKEN still governs operator/dashboard auth; it is
    #   unaffected by this per-sensor push credential (D-02).
    print(f"Bearer token (copy now — shown once, never recoverable):\n{raw_token}")
    print(
        "\nNOTE: This token IS the per-sensor push credential (v5.5 per-sensor auth).\n"
        "      Place this raw value in console_api_token in the sensor's sensor.yaml.\n"
        "      If lost: quirk console revoke-sensor <sensor_id> then re-enroll.",
        file=sys.stderr,
    )
    print(f"sensor_id: {sensor_id}", file=sys.stderr)
    # WR-04: return normally — run_console returns after dispatch; sys.exit(0) is
    # unnecessary and prevents atexit handlers + unit test without SystemExit monkeypatching.


def _cmd_revoke_sensor(args: argparse.Namespace) -> None:
    """Stamp revoked_at = now on active token row(s) for the target sensor.

    AUTH-02 / D-07: Revocation is isolated to a single sensor's active token
    row(s); other sensors' token rows are untouched.

    D-08: Revocation only — there is no token-reissue path. A revoked sensor
    must be re-enrolled as a fresh sensor to resume pushes.

    On no active (non-revoked) token: prints an error to stderr and exits 1
    (mirrors _cmd_enroll's IntegrityError/sys.exit(1) pattern — T-109-03).

    WR-04: return normally on success — no sys.exit(0).
    """
    from datetime import datetime, timezone

    from sqlalchemy.orm import sessionmaker

    from quirk.dashboard.api.deps import _default_db_path
    from quirk.db import init_db
    from quirk.models import SensorToken

    sensor_id: str = args.sensor_id

    db_path = _default_db_path()
    engine = init_db(db_path)
    Session = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )

    with Session() as db:
        active_rows = (
            db.query(SensorToken)
            .filter(
                SensorToken.sensor_id == sensor_id,
                SensorToken.revoked_at.is_(None),
            )
            .all()
        )
        if not active_rows:
            print(
                f"ERROR: no active token found for sensor_id {sensor_id!r}",
                file=sys.stderr,
            )
            sys.exit(1)

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        for row in active_rows:
            row.revoked_at = now
        db.commit()

    print(f"Revoked token(s) for sensor_id: {sensor_id}")
    # WR-04: return normally


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
    # WR-01: max_window_size enforces the cap at the C layer before Python allocates.
    # stream_reader().read(N+1) is a secondary Python-level check.
    try:
        dctx = zstandard.ZstdDecompressor(max_window_size=_ZSTD_MAX_WINDOW)
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

    # Success summary (SENSOR-04 operator confirmation of what was ingested).
    finding_count = len(envelope.get("findings", []) or [])
    print(
        "Imported: sensor_id={sid} segment={seg} payload_id={pid} findings={n}".format(
            sid=envelope.get("sensor_id", ""),
            seg=envelope.get("segment", ""),
            pid=envelope.get("payload_id", ""),
            n=finding_count,
        )
    )
    # WR-04: return normally — run_console returns after dispatch; sys.exit(0) is
    # unnecessary and prevents atexit handlers + unit test without SystemExit monkeypatching.


class DuplicatePayloadError(Exception):
    """Raised when a payload_id already exists in sensor_pushes (dedup gate)."""


class UnknownSensorError(Exception):
    """Raised when a push/import references a sensor_id with no enrolled row.

    Surfaced when the SensorPush insert trips the FOREIGN KEY constraint —
    the sensor must be provisioned via `quirk console enroll` before its data
    can be ingested (HTTPS push or air-gap import alike).
    """


def _parse_dt(value: object) -> datetime | None:
    """Parse an ISO-8601 datetime string to tz-naive UTC.

    Returns None on any parse failure — malformed strings must not crash ingest.
    """
    if not isinstance(value, str) or not value:
        return None
    try:
        return (
            datetime.fromisoformat(value.replace("Z", "+00:00"))
            .replace(tzinfo=None)
        )
    except (ValueError, TypeError):
        return None


def _ingest_envelope(
    envelope: dict,
    config_path: str,
    skip_replay_window: bool = False,
    qpush_sig: str | None = None,
    db=None,  # Session | None — injected by HTTPS route; created internally for CLI
) -> None:
    """Shared ingest path for HTTPS push and air-gap import.

    Performs:
    - sensor_pushes dedup (payload_id UNIQUE → DuplicatePayloadError on replay)
    - sensors.last_push_at update
    - CryptoEndpoint row creation per finding (tagged with envelope sensor_id/segment)

    Parameters
    ----------
    envelope:
        Decoded push envelope dict (must contain payload_id, sensor_id, segment,
        findings).
    config_path:
        Console config.yaml path (accepted for CLI parity; not currently parsed
        here — DB path resolved via _default_db_path()).
    skip_replay_window:
        When True the ±15-min clock-window is bypassed (air-gap D-15 carve-out).
        Replay-window enforcement lives in the HTTPS route, not here.
    qpush_sig:
        HMAC-SHA256 signature string from WR-03 framing header (air-gap) or the
        X-Sensor-Signature header (HTTPS path).  Carried as metadata; crypto
        verification is deferred to v5.5 (T-109-11).
    db:
        An injected SQLAlchemy Session (HTTPS path) or None (CLI path, which opens
        and closes its own session).  When injected the caller owns commit/rollback.
    """
    from sqlalchemy.exc import IntegrityError
    from sqlalchemy.orm import sessionmaker

    from quirk.dashboard.api.deps import _default_db_path
    from quirk.db import init_db
    from quirk.models import CryptoEndpoint, Sensor, SensorPush
    from quirk.util.safe_exc import safe_str

    _own_session = db is None
    if _own_session:
        engine = init_db(_default_db_path())
        _Session = sessionmaker(
            bind=engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )
        db = _Session()

    try:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        sensor_id: str = envelope.get("sensor_id", "")
        segment: str = envelope.get("segment", "")
        payload_id: str = envelope.get("payload_id", "")
        findings: list = envelope.get("findings", []) or []

        # --- Dedup: insert SensorPush row; flush to trigger UNIQUE constraint ---
        # SQLite enforces PRAGMA foreign_keys=ON (quirk/db.py), so an unenrolled
        # sensor_id raises an FK IntegrityError here too. Discriminate: only the
        # UNIQUE(payload_id) violation is a true duplicate; an FK failure means the
        # sensor was never enrolled and must surface as UnknownSensorError, not a
        # misleading "payload_id already imported".
        try:
            db.add(SensorPush(
                payload_id=payload_id,
                sensor_id=sensor_id,
                received_at=now,
            ))
            db.flush()
        except IntegrityError as exc:
            db.rollback()
            orig = str(getattr(exc, "orig", "") or exc).upper()
            if "UNIQUE" in orig:
                raise DuplicatePayloadError(payload_id)
            if "FOREIGN KEY" in orig:
                raise UnknownSensorError(sensor_id)
            raise

        # --- Update sensors.last_push_at (+ sensor_version from the push) ---
        sensor_row = db.query(Sensor).filter(Sensor.sensor_id == sensor_id).first()
        if sensor_row is not None:
            sensor_row.last_push_at = now
            # DASH-02: populate sensor_version from the push envelope so the
            # registry shows a real version instead of always "—".
            _sv = envelope.get("sensor_version")
            if isinstance(_sv, str) and _sv:
                sensor_row.sensor_version = _sv

        # --- Persist CryptoEndpoint rows (envelope sensor_id/segment are authoritative) ---
        for finding in findings:
            if not isinstance(finding, dict):
                continue
            ep = CryptoEndpoint(
                host=finding.get("host") or "",
                port=finding.get("port") or 0,
                protocol=finding.get("protocol"),
                scanned_at=_parse_dt(finding.get("scanned_at")),
                tls_version=finding.get("tls_version"),
                cipher_suite=finding.get("cipher_suite"),
                cert_subject=finding.get("cert_subject"),
                cert_issuer=finding.get("cert_issuer"),
                cert_sans=finding.get("cert_sans"),
                cert_sig_alg=finding.get("cert_sig_alg"),
                cert_pubkey_alg=finding.get("cert_pubkey_alg"),
                cert_pubkey_size=finding.get("cert_pubkey_size"),
                cert_not_before=_parse_dt(finding.get("cert_not_before")),
                cert_not_after=_parse_dt(finding.get("cert_not_after")),
                # Envelope top-level values override per-finding sensor_id/segment
                # (forward-compat — older sensors may emit None in per-finding dict)
                sensor_id=sensor_id,
                segment=segment,
            )
            db.add(ep)

        if _own_session:
            db.commit()
        else:
            # Injected session: flush so rows are visible; caller owns final commit
            db.flush()

    except DuplicatePayloadError:
        # Re-raise after rollback already done above (or by outer caller)
        if _own_session:
            # Air-gap path: surface as operator message
            print(
                f"ERROR: payload_id already imported: {envelope.get('payload_id', '')}",
                file=sys.stderr,
            )
            sys.exit(1)
        raise
    except UnknownSensorError:
        # Rollback already done at the FK catch above.
        if _own_session:
            # Air-gap path: surface as operator message
            print(
                f"ERROR: sensor not enrolled: {envelope.get('sensor_id', '')}",
                file=sys.stderr,
            )
            sys.exit(1)
        raise
    except Exception as exc:
        if _own_session:
            try:
                db.rollback()
            except Exception:
                pass
            logger.warning("Ingest failed: %s", safe_str(exc))
            print(f"ERROR: ingest failed", file=sys.stderr)
            sys.exit(1)
        raise
    finally:
        if _own_session:
            db.close()
