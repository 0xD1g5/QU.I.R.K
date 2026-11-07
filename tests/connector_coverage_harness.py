"""Shared hermetic harness for the Phase 235.3 connector-coverage tests.

Not a test module (no ``test_`` prefix, so pytest does not collect it). Plans
14 and 21 import it to run a real in-process ``run_scan.main()`` against
loopback stubs, with every path (cwd, output.directory, output.db_path,
--db-path) under a tmp dir and the cloud credential environment scrubbed.

Stubs bind ``127.0.0.1`` on an ephemeral port only and never use chaos-lab
ports. The TLS stub's certificate is generated per call; no key is committed.
"""
from __future__ import annotations

import contextlib
import copy
import datetime
import http.server
import os
import socket
import ssl
import sys
import threading
from typing import Any, Dict, Iterator, List, Optional

import yaml

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_CLOUD_ENV_PREFIXES = ("AWS_", "AZURE_", "GOOGLE_", "GCLOUD_", "CLOUDSDK_")

S3_EMPTY_LIST_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<ListAllMyBucketsResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">'
    "<Owner><ID>harness</ID></Owner><Buckets/></ListAllMyBucketsResult>"
)


def _deep_merge(base: Dict[str, Any], extra: Dict[str, Any]) -> Dict[str, Any]:
    for key, value in extra.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = copy.deepcopy(value)
    return base


def build_config(tmp_path, overrides: Optional[Dict[str, Any]] = None) -> str:
    """Write a config.yaml under *tmp_path* and return its path.

    Starts from ``quirk/config_template.yaml``'s live keys, points
    ``output.directory`` / ``output.db_path`` under *tmp_path*, then deep-merges
    *overrides* (e.g. ``{"connectors": {"enable_jwt": True}}``).
    """
    tmpl = os.path.join(_REPO, "quirk", "config_template.yaml")
    with open(tmpl, encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    out = os.path.join(str(tmp_path), "out")
    data["output"] = {
        "directory": out,
        "db_path": os.path.join(str(tmp_path), "quirk.db"),
    }
    if overrides:
        _deep_merge(data, overrides)
    path = os.path.join(str(tmp_path), "config.yaml")
    with open(path, "w", encoding="utf-8") as fh:
        yaml.safe_dump(data, fh, sort_keys=False)
    return path


def scrub_cloud_env(monkeypatch) -> None:
    """Remove every cloud credential variable and disable ambient lookups."""
    for name in list(os.environ):
        if name.startswith(_CLOUD_ENV_PREFIXES):
            monkeypatch.delenv(name, raising=False)
    nowhere = os.path.join(os.sep, "nonexistent-quirk-235-3")
    monkeypatch.setenv("AWS_EC2_METADATA_DISABLED", "true")
    monkeypatch.setenv("AWS_CONFIG_FILE", os.path.join(nowhere, "aws-config"))
    monkeypatch.setenv(
        "AWS_SHARED_CREDENTIALS_FILE", os.path.join(nowhere, "aws-credentials")
    )


def closed_port() -> int:
    """A loopback port that was bound and then closed (connection refused)."""
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@contextlib.contextmanager
def _http_server(handler_cls) -> Iterator[http.server.HTTPServer]:
    srv = http.server.HTTPServer(("127.0.0.1", 0), handler_cls)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    try:
        yield srv
    finally:
        srv.shutdown()
        srv.server_close()
        thread.join(timeout=5)


@contextlib.contextmanager
def jwks_stub(body: str) -> Iterator[str]:
    """Serve *body* at ``/.well-known/jwks.json``; yield the base URL."""
    payload = body.encode("utf-8")

    class _Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            if self.path == "/.well-known/jwks.json":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
            else:
                self.send_response(404)
                self.send_header("Content-Length", "0")
                self.end_headers()

        def log_message(self, *args, **kwargs):  # silence
            pass

    with _http_server(_Handler) as srv:
        yield f"http://127.0.0.1:{srv.server_address[1]}"


@contextlib.contextmanager
def s3_stub(status: int = 200, code: Optional[str] = None) -> Iterator[str]:
    """Answer S3 requests; yield the endpoint URL.

    Default: ListBuckets with an empty bucket list. With *status* / *code*
    (e.g. ``status=403, code="InvalidAccessKeyId"``) answer the S3 XML error.
    """
    if code is None and status == 200:
        payload = S3_EMPTY_LIST_XML.encode("utf-8")
    else:
        payload = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            f"<Error><Code>{code or 'AccessDenied'}</Code>"
            "<Message>harness stub</Message><RequestId>0</RequestId></Error>"
        ).encode("utf-8")

    class _Handler(http.server.BaseHTTPRequestHandler):
        def _answer(self):
            self.send_response(status)
            self.send_header("Content-Type", "application/xml")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(payload)

        do_GET = do_HEAD = do_POST = do_PUT = _answer  # noqa: N815

        def log_message(self, *args, **kwargs):  # silence
            pass

    with _http_server(_Handler) as srv:
        yield f"http://127.0.0.1:{srv.server_address[1]}"


def _self_signed_pem(tmp_path):
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    now = datetime.datetime.now(datetime.timezone.utc)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "harness-tls-stub")])
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=30))
        .sign(key, hashes.SHA256())
    )
    cp = os.path.join(str(tmp_path), "harness-cert.pem")
    kp = os.path.join(str(tmp_path), "harness-key.pem")
    with open(cp, "wb") as fh:
        fh.write(cert.public_bytes(serialization.Encoding.PEM))
    with open(kp, "wb") as fh:
        fh.write(key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        ))
    return cp, kp


@contextlib.contextmanager
def tls_stub(tmp_path) -> Iterator[int]:
    """Serve TLS on ``127.0.0.1:<ephemeral>`` with a throwaway cert; yield the port."""
    cp, kp = _self_signed_pem(tmp_path)
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(cp, kp)
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(50)
    srv.settimeout(0.5)
    port = srv.getsockname()[1]
    stop = threading.Event()

    def serve():
        while not stop.is_set():
            try:
                conn, _ = srv.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            try:
                conn.settimeout(5)
                tls = ctx.wrap_socket(conn, server_side=True)
                tls.recv(1)
                tls.close()
            except Exception:
                with contextlib.suppress(Exception):
                    conn.close()

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    try:
        yield port
    finally:
        stop.set()
        srv.close()
        thread.join(timeout=5)


def quirk_output_snapshot() -> Optional[List[str]]:
    """Sorted listing of the repo's ``./quirk-output`` (None when absent).

    Compare before and after a scan to prove the run wrote only under tmp.
    """
    repo_out = os.path.join(_REPO, "quirk-output")
    return sorted(os.listdir(repo_out)) if os.path.isdir(repo_out) else None


def run_scan_in_process(config_path: str, db_path: str) -> None:
    """Run ``run_scan.main()`` in this process, cwd = the config's directory.

    ``--db-path`` must equal ``output.db_path`` (``init_db()`` only initialises
    the config's path; see memory: run_scan.py --db-path silent no-op trap).
    """
    import pytest

    import run_scan

    mp = pytest.MonkeyPatch()
    try:
        mp.chdir(os.path.dirname(os.path.abspath(config_path)))
        mp.setattr(sys, "argv", [
            "run_scan.py", "--config", str(config_path), "--db-path", str(db_path),
        ])
        run_scan.main()
    finally:
        mp.undo()


def phase_rows(db_path: str, scan_run_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """``scan_phase_records`` rows as dicts (latest run when *scan_run_id* is None)."""
    from quirk.db import get_session
    from quirk.models import ScanPhaseRecord

    with get_session(db_path) as session:
        q = session.query(ScanPhaseRecord)
        if scan_run_id is None:
            first = q.order_by(ScanPhaseRecord.id.desc()).first()
            if first is None:
                return []
            scan_run_id = first.scan_run_id
        rows = q.filter_by(scan_run_id=scan_run_id).order_by(ScanPhaseRecord.id).all()
        return [
            {
                "scan_run_id": r.scan_run_id,
                "phase_name": r.phase_name,
                "status": r.status,
                "reason": r.reason,
                "detail": r.detail,
            }
            for r in rows
        ]
