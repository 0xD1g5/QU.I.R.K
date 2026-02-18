import socket
from dataclasses import dataclass
from typing import Optional


@dataclass
class FingerprintResult:
    is_open: bool
    proto: str          # TLS | SSH | HTTP | UNKNOWN | CLOSED
    detail: str         # banner/status/error/notes


def _peek(sock: socket.socket, n: int = 64) -> bytes:
    try:
        sock.settimeout(1.0)
        return sock.recv(n)
    except Exception:
        return b""


def _looks_like_tls(data: bytes) -> bool:
    # TLS record header commonly: 0x16 0x03 0x01/0x02/0x03/0x04...
    return len(data) >= 3 and data[0] == 0x16 and data[1] == 0x03


def _looks_like_ssh(data: bytes) -> bool:
    return data.startswith(b"SSH-")


def fingerprint_service(host: str, port: int, timeout: int = 3) -> FingerprintResult:
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            # Step 1: passive peek (some services send banners)
            data = _peek(sock, 128)

            if _looks_like_ssh(data):
                banner = data.decode(errors="ignore").strip()
                return FingerprintResult(True, "SSH", banner or "SSH banner detected")

            # Step 2: quick HTTP probe (safe + common)
            try:
                sock.settimeout(1.5)
                req = b"HEAD / HTTP/1.1\r\nHost: x\r\nConnection: close\r\n\r\n"
                sock.sendall(req)
                resp = _peek(sock, 128)
                if resp.startswith(b"HTTP/"):
                    status = resp.decode(errors="ignore").splitlines()[0].strip()
                    return FingerprintResult(True, "HTTP", status or "HTTP detected")
            except Exception:
                pass

            # Step 3: TLS heuristic (some services reply only after ClientHello, but some speak first)
            if _looks_like_tls(data):
                return FingerprintResult(True, "TLS", "TLS record header observed")

            # If nothing obvious: it's open, but unknown protocol or requires specific handshake
            if data:
                snippet = data[:80].decode(errors="ignore").strip()
                return FingerprintResult(True, "UNKNOWN", f"Banner bytes: {snippet}")
            return FingerprintResult(True, "UNKNOWN", "Open port, no banner (may require protocol-specific handshake)")

    except ConnectionRefusedError:
        return FingerprintResult(False, "CLOSED", "Connection refused")
    except TimeoutError:
        return FingerprintResult(False, "CLOSED", "Timeout (filtered or host down)")
    except OSError as e:
        return FingerprintResult(False, "CLOSED", f"OS error: {e}")
