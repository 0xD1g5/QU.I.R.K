"""quirk sensor — Phase 108 SENSOR-01/02/03: distributed sensor agent CLI.

Subcommands
-----------
enroll          Bind sensor to a console; mint one-time enrollment token +
                persistent push credentials (hmac_key, console_api_token).
push            Run a local scan via subprocess, build the signed wire
                envelope, and POST over hard-verified HTTPS with tenacity
                retry.  Spools to disk when offline.
export-results  (stub for Plan 03) Export scan results to a .qpush file
                for air-gap transfer.

Security contract
-----------------
* verify=True is HARDCODED on the httpx.Client — no override parameter
  exists.  CI: tests/test_sensor_no_verify_false.py grep gate.
* follow_redirects=False prevents post-validation SSRF bypass.
* validate_external_url(console_url) is called before any network I/O.
* The one-time enrollment token is printed once and NEVER written to
  sensor.yaml; only the persistent push credentials (hmac_key,
  console_api_token) are stored.
* Spool filenames are {uuid4}.json.zst — no operator-controlled path
  components (T-108-08).
* v5.4 is single-process; no spool file lock required (RESEARCH Pitfall 7).
"""
from __future__ import annotations

import argparse
import hashlib
import hmac as _hmac
import json
import os
import re
import secrets
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime
from pathlib import Path

import yaml
import zstandard
from platformdirs import user_config_dir, user_data_dir
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

import quirk
from quirk.util.no_redirect import _NoRedirectHandler          # STAB-02 prerequisite
from quirk.util.url_allowlist import validate_external_url

# ---------------------------------------------------------------------------
# UUID validation regex (CR-02: sensor_id from sensor.yaml used in filenames)
# ---------------------------------------------------------------------------

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Spool constants (T-108-07: bounded dir prevents DoS via disk fill)
# ---------------------------------------------------------------------------

_SPOOL_MAX_FILES = 100
_SPOOL_MAX_BYTES = 500 * 1024 * 1024  # 500 MB


# ---------------------------------------------------------------------------
# Subparser + dispatch
# ---------------------------------------------------------------------------


def run_sensor(argv: list[str]) -> None:
    """Main entrypoint for ``quirk sensor`` subcommands.

    argv = sys.argv[2:] — does NOT include 'quirk' or 'sensor'.
    """
    parser = argparse.ArgumentParser(
        prog="quirk sensor",
        description="Distributed sensor management (Phase 108)",
    )
    sub = parser.add_subparsers(dest="action", required=True)

    enroll_p = sub.add_parser("enroll", help="Enroll sensor against a console")
    enroll_p.add_argument("console_url", help="Console base URL (https://...)")
    enroll_p.add_argument("--segment", required=True, help="Network segment label")
    enroll_p.add_argument("--engagement", default=None, help="Optional engagement tag")
    enroll_p.add_argument("--config", default=None, help="Override sensor.yaml path")
    enroll_p.add_argument(
        "--api-token",
        dest="api_token",
        default=None,
        help="Operator-provided console Bearer token for ongoing pushes",
    )

    push_p = sub.add_parser("push", help="Run local scan and push results to console")
    push_p.add_argument("--config", default=None, help="Override sensor.yaml path")
    push_p.add_argument(
        "--scan-config",
        dest="scan_config",
        default="config.yaml",
        help="Scan config.yaml path",
    )

    export_p = sub.add_parser(
        "export-results",
        help="Export results to .qpush file for air-gap transfer (Plan 03)",
    )
    export_p.add_argument("--config", default=None, help="Override sensor.yaml path")
    export_p.add_argument(
        "--scan-config",
        dest="scan_config",
        default="config.yaml",
        help="Scan config.yaml path",
    )
    export_p.add_argument("--output", default=".", help="Directory to write .qpush file")

    merge_p = sub.add_parser(
        "merge",
        help="Merge all sensor data and produce unified CBOM + score",
    )
    merge_p.add_argument("--db", default=None, help="Override console DB path")
    merge_p.add_argument(
        "--stale-days",
        type=int,
        default=30,
        dest="stale_days",
        help="Exclude sensors silent for longer than this many days",
    )

    args = parser.parse_args(argv)
    try:
        if args.action == "enroll":
            _cmd_enroll(args)
        elif args.action == "push":
            _cmd_push(args)
        elif args.action == "export-results":
            _cmd_export_results(args)
        elif args.action == "merge":
            _cmd_merge(args)
    except KeyboardInterrupt:
        # Clean shutdown on Ctrl-C / SIGINT (SENSOR-06 Windows clean-shutdown invariant)
        print("\nInterrupted.", file=sys.stderr)
        sys.exit(130)


# ---------------------------------------------------------------------------
# Atomic YAML write (copy of token_cmd._write_token_to_config idiom)
# ---------------------------------------------------------------------------


def _write_sensor_config(config_path: str, sensor_cfg: dict) -> None:
    """Write sensor.yaml using atomic tempfile + os.replace (crash-safe).

    dir= param MUST be same directory as target so os.replace is same-filesystem.
    Parent directory must already exist (call os.makedirs(..., exist_ok=True) first).
    """
    dir_ = os.path.dirname(os.path.abspath(config_path))
    fd, tmp = tempfile.mkstemp(dir=dir_, prefix=".quirk_sensor_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            yaml.dump(sensor_cfg, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        os.replace(tmp, config_path)  # atomic on POSIX; best-effort on Windows
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _default_sensor_yaml_path() -> str:
    """Return the default sensor.yaml path (platformdirs cross-OS config dir)."""
    return os.path.join(user_config_dir("quirk"), "sensor.yaml")


# ---------------------------------------------------------------------------
# SENSOR-01: enroll
# ---------------------------------------------------------------------------


def _cmd_enroll(args: argparse.Namespace) -> None:
    """Enroll sensor: write bound sensor.yaml + print one-time token."""
    console_url: str = args.console_url

    # T-108-04: SSRF guard — validate before any network I/O
    result = validate_external_url(console_url)
    if not result.ok:
        print(
            f"ERROR: console URL blocked by SSRF allowlist — {result.reason}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Resolve config path
    config_path: str = args.config or _default_sensor_yaml_path()
    config_dir = os.path.dirname(os.path.abspath(config_path))

    # Ensure parent directory exists (fresh system support)
    os.makedirs(config_dir, exist_ok=True)

    # Prompt for api_token if not supplied
    api_token: str = getattr(args, "api_token", None) or ""

    # Mint sensor identity
    sensor_id = str(uuid.uuid4())

    # One-time enrollment token (T-108-05: raw token printed once, never stored)
    raw_token = secrets.token_urlsafe(32)
    # token_hash is available for context/logging only — console-side storage is Phase 109
    _token_hash = hashlib.sha256(raw_token.encode()).hexdigest()  # noqa: F841

    # Persistent push credentials
    hmac_key = secrets.token_bytes(32).hex()

    # Build sensor.yaml dict — enrollment token is NEVER included
    sensor_cfg = {
        "console_url": console_url,
        "sensor_id": sensor_id,
        "segment": args.segment,
        "engagement": args.engagement,
        "sensor_version": quirk.__version__,
        "hmac_key": hmac_key,
        "console_api_token": api_token,
    }

    # Atomic write
    _write_sensor_config(config_path, sensor_cfg)

    # Print the one-time enrollment token — shown once, never written to disk
    print(f"Enrollment token (shown once — save it now):\n{raw_token}", flush=True)
    print("WARNING: this token will not be shown again.", file=sys.stderr)
    print(f"Sensor config written to: {config_path}", file=sys.stderr)

    sys.exit(0)


# ---------------------------------------------------------------------------
# Wire envelope + compression + signing helpers
# (canonical serializer — Plan 03 export-results MUST reuse these byte-for-byte)
# ---------------------------------------------------------------------------


def _endpoint_to_dict(ep) -> dict:
    """Serialize a CryptoEndpoint ORM row to a JSON-safe dict.

    Reads columns explicitly (not __dict__) so no SQLAlchemy internal state
    leaks into the payload.  Path-like values are normalized to forward slashes.
    host is always a hostname/IP string — no path separators.
    """
    def _str(v) -> str | None:
        """Coerce to str; normalize any path-like value to forward slashes."""
        if v is None:
            return None
        s = str(v)
        # Replace OS-specific path separators (Windows) with forward slashes
        return s.replace("\\", "/")

    def _dt(v) -> str | None:
        """Coerce a datetime to ISO-8601 UTC string."""
        if v is None:
            return None
        if hasattr(v, "strftime"):
            return v.strftime("%Y-%m-%dT%H:%M:%SZ")
        return str(v)

    return {
        "host": _str(ep.host),
        "port": ep.port,
        "protocol": _str(ep.protocol),
        "scanned_at": _dt(ep.scanned_at),
        "tls_version": _str(ep.tls_version),
        "cipher_suite": _str(ep.cipher_suite),
        "cert_subject": _str(ep.cert_subject),
        "cert_issuer": _str(ep.cert_issuer),
        "cert_sans": _str(ep.cert_sans),
        "cert_sig_alg": _str(ep.cert_sig_alg),
        "cert_pubkey_alg": _str(ep.cert_pubkey_alg),
        "cert_pubkey_size": ep.cert_pubkey_size,
        "cert_not_before": _dt(ep.cert_not_before),
        "cert_not_after": _dt(ep.cert_not_after),
        "sensor_id": _str(getattr(ep, "sensor_id", None)),
        "segment": _str(getattr(ep, "segment", None)),
    }


def _build_envelope(sensor_cfg: dict, endpoints: list) -> dict:
    """Build the canonical wire envelope dict.

    NOTE: received_at is NOT included — the console stamps it on ingest (Phase 109).
    NOTE: all values must be JSON-serializable primitives — no Path objects,
          no OS-specific datetime formatting, no backslash path separators.
    """
    return {
        "payload_id": str(uuid.uuid4()),
        "pushed_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "schema_version": "1.0.0",
        "sensor_version": sensor_cfg["sensor_version"],
        "sensor_id": sensor_cfg["sensor_id"],
        "segment": sensor_cfg["segment"],
        "findings": [_endpoint_to_dict(ep) for ep in endpoints],
    }


def _build_compressed_payload(envelope: dict) -> bytes:
    """Serialize envelope to JSON and compress with zstd level-3."""
    raw = json.dumps(envelope, ensure_ascii=False).encode("utf-8")
    return zstandard.ZstdCompressor(level=3).compress(raw)


def _sign(body: bytes, key: bytes) -> str:
    """Return 'hmac-sha256=<hex>' HMAC-SHA256 signature over body."""
    return "hmac-sha256=" + _hmac.new(key, body, hashlib.sha256).hexdigest()


# ---------------------------------------------------------------------------
# SENSOR-02: push — tenacity retry + httpx hard-verified HTTPS
# ---------------------------------------------------------------------------


def _is_retryable(exc: BaseException) -> bool:
    """Return True for transient network errors and 5xx server errors.

    4xx client errors are permanent — never retry.
    ConnectError/TimeoutException are transient network failures.
    HTTPStatusError is raised by _do_push only for 5xx (server error) responses.
    """
    import httpx

    return isinstance(exc, (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError))


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    retry=retry_if_exception(_is_retryable),
    reraise=True,
)
def _do_push(client, url: str, headers: dict, content: bytes):
    """POST payload to console; retries on 5xx and transient connection errors.

    4xx responses are NOT retried — they indicate permanent rejection.
    verify=True and follow_redirects=False are enforced by the caller;
    there is no parameter to override them.
    """
    import httpx

    resp = client.post(url, headers=headers, content=content)
    if resp.status_code >= 500:
        resp.raise_for_status()  # raises HTTPStatusError → triggers tenacity retry
    return resp


def _run_local_scan(scan_config: str, output_dir: Path) -> int:
    """Invoke run_scan as subprocess. Returns proc.returncode.

    Uses list-form Popen — no shell=True, no metacharacter expansion (T-63-07 pattern).
    Never calls the run_scan main function directly — subprocess only (test-gated invariant).
    """
    cmd = [
        sys.executable,
        "-m",
        "run_scan",
        "--config",
        scan_config,
        "--output",
        str(output_dir),
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    _stdout, _stderr = proc.communicate()
    return proc.returncode


def _read_scan_endpoints(db_path: str) -> list:
    """Open the scan SQLite DB produced by the local scan and return CryptoEndpoint rows."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    from quirk.models import CryptoEndpoint

    engine = create_engine(f"sqlite:///{db_path}")
    with Session(engine) as session:
        return session.query(CryptoEndpoint).all()


# ---------------------------------------------------------------------------
# Spool helpers (SENSOR-03)
# ---------------------------------------------------------------------------


def _spool_dir() -> Path:
    """Return the spool directory path, creating it if needed."""
    d = Path(user_data_dir("quirk")) / "spool"
    os.makedirs(d, exist_ok=True)
    return d


def _evict_if_full(spool_dir: Path) -> None:
    """Evict oldest spool file(s) when max-file-count or max-total-bytes is exceeded.

    Emits a stderr warning per eviction so operators notice spool pressure.

    WR-01: sizes are captured in a single stat pass during the initial sort so
    a second stat() is never called after the loop starts.  unlink(missing_ok=True)
    prevents FileNotFoundError if another process removes the file between the
    glob and the unlink (the spool dir is in user_data_dir, accessible to any
    process running as the same user).
    """
    files: list = []
    for p in spool_dir.glob("*.json.zst"):
        try:
            st = p.stat()
            files.append((p, st.st_size, st.st_mtime))
        except FileNotFoundError:
            pass  # file removed by another process between glob and stat — skip it
    files.sort(key=lambda t: t[2])
    total_bytes = sum(sz for _, sz, _ in files)
    while (len(files) >= _SPOOL_MAX_FILES or total_bytes > _SPOOL_MAX_BYTES) and files:
        path, size, _ = files.pop(0)
        total_bytes -= size
        path.unlink(missing_ok=True)
        print(
            f"WARNING: spool full — evicted oldest payload: {path.name}",
            file=sys.stderr,
        )


def _spool_payload(payload_id: str, body: bytes) -> None:
    """Write compressed payload to the spool dir as {payload_id}.json.zst.

    Filename is UUID-only — no operator-controlled path components (T-108-08).
    """
    d = _spool_dir()
    os.makedirs(d, exist_ok=True)
    _evict_if_full(d)
    dest = d / f"{payload_id}.json.zst"
    dest.write_bytes(body)


def _flush_spool(client, push_url: str, headers_fn) -> None:
    """Re-push all spooled payloads FIFO (oldest-first) at the start of each push.

    Unlinks on 200 or 409 (duplicate → already accepted).
    Leaves the file in place on connection failure.

    v5.4 is single-process; no file lock is required (RESEARCH Pitfall 7).
    """
    import httpx

    d = _spool_dir()
    files = sorted(d.glob("*.json.zst"), key=lambda p: p.stat().st_mtime)
    for f in files:
        body = f.read_bytes()
        headers = headers_fn(body)
        try:
            resp = _do_push(client, push_url, headers, body)
            if resp.status_code in (200, 409):
                f.unlink()
        except (httpx.ConnectError, httpx.TimeoutException, Exception):
            # Leave spooled file; will retry on next push
            pass


# ---------------------------------------------------------------------------
# SENSOR-02: _cmd_push
# ---------------------------------------------------------------------------


def _cmd_push(args: argparse.Namespace) -> None:
    """Run local scan, build and sign envelope, push over HTTPS; spool on failure."""
    import httpx

    config_path: str = args.config or _default_sensor_yaml_path()

    # Read sensor.yaml
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            sensor_cfg = yaml.safe_load(f) or {}
    except FileNotFoundError:
        print(f"ERROR: sensor.yaml not found: {config_path}", file=sys.stderr)
        print("Run 'quirk sensor enroll' first.", file=sys.stderr)
        sys.exit(1)

    console_url: str = sensor_cfg.get("console_url", "")

    # T-108-04: SSRF guard
    result = validate_external_url(console_url)
    if not result.ok:
        print(
            f"ERROR: console URL blocked by SSRF allowlist — {result.reason}",
            file=sys.stderr,
        )
        sys.exit(1)

    push_url = console_url.rstrip("/") + "/api/sensor/push"
    hmac_key_hex: str = sensor_cfg.get("hmac_key", "")

    # CR-03: validate hmac_key before use — bytes.fromhex("") raises ValueError
    # which propagates as an unhandled traceback from _make_headers at line ~488.
    if not hmac_key_hex or len(hmac_key_hex) != 64:
        print(
            "ERROR: sensor.yaml is missing or has invalid hmac_key (must be 64-char hex)",
            file=sys.stderr,
        )
        print("Re-run 'quirk sensor enroll' to regenerate credentials.", file=sys.stderr)
        sys.exit(1)
    try:
        bytes.fromhex(hmac_key_hex)
    except ValueError:
        print("ERROR: sensor.yaml hmac_key is not valid hex", file=sys.stderr)
        sys.exit(1)

    api_token: str = sensor_cfg.get("console_api_token", "")

    # Run local scan in a temp output dir
    output_dir = Path(tempfile.mkdtemp())
    try:
        scan_config: str = args.scan_config
        rc = _run_local_scan(scan_config, output_dir)
        if rc != 0:
            print(f"WARNING: local scan exited with code {rc}", file=sys.stderr)

        # Find the scan DB file in output_dir
        db_files = list(output_dir.rglob("*.db"))
        if db_files:
            endpoints = _read_scan_endpoints(str(db_files[0]))
        else:
            endpoints = []

        # Build canonical wire envelope
        envelope = _build_envelope(sensor_cfg, endpoints)
        payload_id = envelope["payload_id"]
        body = _build_compressed_payload(envelope)

        def _make_headers(b: bytes) -> dict:
            return {
                "Content-Type": "application/octet-stream",
                "X-Sensor-Signature": _sign(b, bytes.fromhex(hmac_key_hex)),
                "Authorization": f"Bearer {api_token}",
            }

        headers = _make_headers(body)

        # verify=True and follow_redirects=False HARDCODED — no override parameter
        with httpx.Client(verify=True, follow_redirects=False) as client:
            # Flush any spooled payloads FIFO before pushing the current one
            _flush_spool(client, push_url, _make_headers)

            try:
                resp = _do_push(client, push_url, headers, body)
                if resp.status_code in (200, 409):
                    pass  # Delivered (200) or already accepted (409)
                else:
                    # 4xx permanent error — spool for audit; exit non-zero
                    _spool_payload(payload_id, body)
                    print(
                        f"ERROR: push rejected with HTTP {resp.status_code}",
                        file=sys.stderr,
                    )
                    sys.exit(2)
            except (httpx.ConnectError, httpx.TimeoutException) as exc:
                # Terminal network failure after retries — spool for later delivery
                _spool_payload(payload_id, body)
                print(
                    f"WARNING: push failed (offline) — spooled payload {payload_id}: {exc}",
                    file=sys.stderr,
                )
                sys.exit(3)
            except Exception as exc:
                _spool_payload(payload_id, body)
                print(f"ERROR: push failed: {exc}", file=sys.stderr)
                sys.exit(4)
    finally:
        # Clean up temp output dir
        import shutil

        shutil.rmtree(output_dir, ignore_errors=True)

    sys.exit(0)


# ---------------------------------------------------------------------------
# SENSOR-04: export-results — air-gap .qpush file
# ---------------------------------------------------------------------------


def _cmd_export_results(args: argparse.Namespace) -> None:
    """Export scan results to a .qpush file for air-gap transfer (SENSOR-04).

    Reuses _build_envelope and _build_compressed_payload BYTE-FOR-BYTE so the
    compressed payload body is identical to an HTTPS push request body.
    No network I/O — no httpx, no validate_external_url call.

    .qpush file format (WR-03):
        <JSON header line>\\n<compressed payload bytes>

    The JSON header line carries the HMAC-SHA256 signature so Phase 109
    import-results can verify file integrity without out-of-band key transport:
        {"hmac-sha256": "hmac-sha256=<hex>"}\\n

    The compressed payload bytes that follow the header are byte-for-byte
    identical to the HTTPS push request body — _build_compressed_payload is
    shared by both paths (byte-identity invariant, T-108-06).

    Output file: {output}/{sensor_id}-{payload_id}.qpush
    """
    config_path: str = args.config or _default_sensor_yaml_path()

    # Read sensor.yaml
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            sensor_cfg = yaml.safe_load(f) or {}
    except FileNotFoundError:
        print(f"ERROR: sensor.yaml not found: {config_path}", file=sys.stderr)
        print("Run 'quirk sensor enroll' first.", file=sys.stderr)
        sys.exit(1)

    sensor_id: str = sensor_cfg.get("sensor_id", "")

    # CR-02: validate sensor_id is a well-formed UUID before using it in the
    # output filename.  A tampered sensor.yaml with sensor_id: "../etc/evil"
    # would otherwise write the .qpush file to an arbitrary path outside --output.
    if not _UUID_RE.match(sensor_id):
        print(
            "ERROR: sensor.yaml contains an invalid sensor_id (must be UUID)",
            file=sys.stderr,
        )
        sys.exit(1)

    # WR-03: read hmac_key so the signature can be embedded in the .qpush file.
    # The key is validated here (same rules as _cmd_push CR-03 gate) before use.
    hmac_key_hex: str = sensor_cfg.get("hmac_key", "")
    if not hmac_key_hex or len(hmac_key_hex) != 64:
        print(
            "ERROR: sensor.yaml is missing or has invalid hmac_key (must be 64-char hex)",
            file=sys.stderr,
        )
        print("Re-run 'quirk sensor enroll' to regenerate credentials.", file=sys.stderr)
        sys.exit(1)
    try:
        hmac_key_bytes = bytes.fromhex(hmac_key_hex)
    except ValueError:
        print("ERROR: sensor.yaml hmac_key is not valid hex", file=sys.stderr)
        sys.exit(1)

    scan_config: str = args.scan_config

    # Run local scan in a temp output dir
    output_dir_path = Path(tempfile.mkdtemp())
    try:
        rc = _run_local_scan(scan_config, output_dir_path)
        if rc != 0:
            print(f"WARNING: local scan exited with code {rc}", file=sys.stderr)

        # Read scan endpoints from DB
        db_files = list(output_dir_path.rglob("*.db"))
        if db_files:
            endpoints = _read_scan_endpoints(str(db_files[0]))
        else:
            endpoints = []

        # Build canonical wire envelope — SAME helpers as push (byte-identity invariant)
        envelope = _build_envelope(sensor_cfg, endpoints)
        payload_id = envelope["payload_id"]

        # Compress — SAME helper as push (body byte-identity invariant)
        body = _build_compressed_payload(envelope)

        # WR-03: embed HMAC signature in a JSON header line prepended to the file.
        # The header is a single newline-terminated JSON object; the compressed body
        # follows immediately after. This keeps the compressed body bytes unchanged
        # (preserving the byte-identity invariant) while adding verifiable integrity
        # for the air-gap transport path.
        signature = _sign(body, hmac_key_bytes)
        header_line = json.dumps({"hmac-sha256": signature}, ensure_ascii=True).encode("ascii") + b"\n"
        qpush_content = header_line + body

        # Write to output file: {sensor_id}-{payload_id}.qpush
        output_path = Path(args.output)
        output_path.mkdir(parents=True, exist_ok=True)
        dest = output_path / f"{sensor_id}-{payload_id}.qpush"
        dest.write_bytes(qpush_content)

        print(str(dest), flush=True)
        print(
            f"Exported {len(endpoints)} finding(s) to: {dest}",
            file=sys.stderr,
        )
    finally:
        import shutil
        shutil.rmtree(output_dir_path, ignore_errors=True)

    sys.exit(0)


# ---------------------------------------------------------------------------
# MERGE-05: merge — thin wrapper over merge_scan() (D-06 auto-trigger seam)
# ---------------------------------------------------------------------------


def _cmd_merge(args: argparse.Namespace) -> None:
    """Merge all sensor data and produce a unified CBOM + score (MERGE-05).

    Thin wrapper over merge_scan() — no merge logic duplicated here.
    The standalone merge_scan() callable remains the v5.5 auto-trigger seam (D-06).
    """
    from quirk.merge.scan import merge_scan
    from quirk.dashboard.api.deps import _default_db_path
    from quirk.db import get_session, init_db

    db_path = args.db or _default_db_path()
    init_db(db_path)
    output_dir = os.path.dirname(os.path.abspath(db_path))
    with get_session(db_path) as db:
        result = merge_scan(db, stale_days=args.stale_days, output_dir=output_dir)

    print(f"Merged scan_id: {result['scan_id']}")
    print(f"Score: {result['score']} ({result['rating']})")
    if result.get("cbom_json_path"):
        print(f"CBOM (JSON): {result['cbom_json_path']}")
    if result.get("cbom_xml_path"):
        print(f"CBOM (XML):  {result['cbom_xml_path']}")
    if result.get("coverage_warning"):
        w = result["coverage_warning"]
        print(f"WARNING: {w['reason']}")
        for sid in w["missing_sensors"]:
            print(f"  - {sid}")
    sys.exit(0)
