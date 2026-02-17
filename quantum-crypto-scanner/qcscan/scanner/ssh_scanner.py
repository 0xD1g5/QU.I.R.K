import socket
from datetime import datetime, timezone
from typing import List, Tuple

from qcscan.models import CryptoEndpoint


def scan_ssh_one(host: str, port: int, timeout: int) -> CryptoEndpoint:
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

    except Exception as e:
        ep.scan_error = f"SSH_ERROR: {e}"

    return ep


def scan_ssh_targets(cfg, targets: List[Tuple[str, int]]) -> List[CryptoEndpoint]:
    results: List[CryptoEndpoint] = []
    for host, port in targets:
        results.append(scan_ssh_one(host, port, cfg.scan.timeout_seconds))
    return results
