import socket
from datetime import datetime, timezone
from typing import List, Tuple, Optional, Callable

from qcscan.models import CryptoEndpoint
from qcscan.logging_util import Logger


def scan_ssh_one(host: str, port: int, timeout: int, logger: Optional[Logger] = None) -> CryptoEndpoint:
    ep = CryptoEndpoint(
        host=host,
        port=port,
        protocol="SSH",
        scanned_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )

    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            sock.settimeout(2.0)
            banner = sock.recv(1024).decode(errors="ignore").strip()

            # Reuse tls_version field for banner in MVP
            ep.tls_version = banner
            ep.cipher_suite = "SSH"

            if logger:
                logger.v(f"🔑 SSH {host}:{port} {banner}")

    except Exception as e:
        ep.scan_error = f"SSH_ERROR: {e}"
        if logger:
            logger.v(f"⚠️ SSH {host}:{port} SSH_ERROR ({e})")

    return ep


def scan_ssh_targets(
    cfg,
    targets: List[Tuple[str, int]],
    logger: Optional[Logger] = None,
    progress_cb: Optional[Callable[[int], None]] = None
) -> List[CryptoEndpoint]:
    results: List[CryptoEndpoint] = []
    for host, port in targets:
        results.append(scan_ssh_one(host, port, cfg.scan.timeout_seconds, logger))
        if progress_cb:
            progress_cb(1)
    return results
    