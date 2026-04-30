import json
import shutil
import socket
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import List, Tuple, Optional, Callable

from quirk.models import CryptoEndpoint
from quirk.logging_util import Logger


def _run_ssh_audit(host: str, port: int, timeout: int) -> Optional[dict]:
    """Run ssh-audit subprocess and return parsed JSON, or None on any failure."""
    exe = shutil.which("ssh-audit")
    if not exe:
        return None
    try:
        proc = subprocess.run(
            [exe, "-j", host, str(port)],
            capture_output=True,
            text=True,
            timeout=timeout + 5,
        )
        if proc.stdout.strip():
            return json.loads(proc.stdout)
        return None
    except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception):
        return None


def scan_ssh_one(
    host: str,
    port: int,
    timeout: int,
    logger: Optional[Logger] = None,
) -> CryptoEndpoint:
    ep = CryptoEndpoint(
        host=host,
        port=port,
        protocol="SSH",
        scanned_at=datetime.now(timezone.utc).replace(tzinfo=None),
        cipher_suite="SSH",  # D-06: SSH marker field
    )

    try:
        audit_data = _run_ssh_audit(host, port, timeout)

        if audit_data is not None:
            # ssh-audit succeeded — store full JSON
            ep.ssh_audit_json = json.dumps(audit_data)

            # Extract banner from ssh-audit JSON, store in service_detail
            banner_obj = audit_data.get("banner") or {}
            banner_raw = banner_obj.get("raw", "")
            if banner_raw:
                ep.service_detail = banner_raw

            kex_count = len(audit_data.get("kex", []))
            key_count = len(audit_data.get("key", []))
            mac_count = len(audit_data.get("mac", []))

            if logger:
                logger.v(
                    f"SSH {host}:{port} ssh-audit OK "
                    f"kex={kex_count} keys={key_count} macs={mac_count}"
                )
        else:
            # ssh-audit not available or failed — fall back to socket banner grab
            if logger:
                logger.v(
                    f"ssh-audit not found — install with: pip install ssh-audit. "
                    f"Falling back to banner scan for {host}:{port}"
                )

            with socket.create_connection((host, port), timeout=timeout) as sock:
                sock.settimeout(2.0)
                banner = sock.recv(1024).decode(errors="ignore").strip()
                ep.service_detail = banner  # D-06: store in service_detail (not protocol version field)

            if logger:
                logger.v(f"SSH {host}:{port} banner={ep.service_detail!r}")

    except Exception as e:
        ep.scan_error = f"SSH_ERROR: {e}"
        if logger:
            logger.v(f"SSH {host}:{port} SSH_ERROR ({e})")

    return ep


def scan_ssh_targets(
    cfg,
    targets: List[Tuple[str, int]],
    logger: Optional[Logger] = None,
    progress_cb: Optional[Callable[[int], None]] = None,
) -> List[CryptoEndpoint]:
    """Scan SSH targets concurrently using ThreadPoolExecutor (D-07)."""
    results: List[CryptoEndpoint] = []

    if not targets:
        return results

    # Phase 41 / D-08: read per-scanner timeout + concurrency from canonical sub-table /
    # dedicated flat field. No more cfg.scan.timeout_seconds / cfg.scan.concurrency mutation.
    ssh_timeout = getattr(cfg.scan.timeouts, "ssh_seconds", cfg.scan.timeout_seconds)
    ssh_workers = getattr(cfg.scan, "ssh_concurrency", cfg.scan.concurrency)

    if logger:
        logger.stamp(
            f"Starting SSH scans: {len(targets)} targets "
            f"(workers={ssh_workers})"
        )

    with ThreadPoolExecutor(max_workers=ssh_workers) as ex:
        futures = [
            ex.submit(scan_ssh_one, host, port, ssh_timeout, logger)
            for (host, port) in targets
        ]
        for f in as_completed(futures):
            results.append(f.result())
            if progress_cb:
                progress_cb(1)

    if logger:
        ok = len([e for e in results if not e.scan_error])
        logger.stamp(f"SSH scans complete: {ok}/{len(results)} successful")

    return results
