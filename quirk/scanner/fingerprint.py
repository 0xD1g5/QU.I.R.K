from __future__ import annotations

import ipaddress
import socket
import ssl
from dataclasses import dataclass
from typing import Optional


@dataclass
class Fingerprint:
    is_open: bool
    proto: str            # "TLS", "SSH", "HTTP", "UNKNOWN", "CLOSED"
    detail: str = ""      # banner or category like MTLS_REQUIRED / NOT_TLS_ON_PORT / TIMEOUT


def _is_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
        return True
    except Exception:
        return False


def _tcp_connect(host: str, port: int, timeout: int) -> socket.socket:
    s = socket.create_connection((host, port), timeout=timeout)
    s.settimeout(timeout)
    return s


def _try_read_ssh_banner(s: socket.socket) -> Optional[str]:
    try:
        data = s.recv(64)
        if data.startswith(b"SSH-"):
            return data.decode("utf-8", errors="replace").strip()
    except Exception:
        return None
    return None


def _tls_handshake(host: str, port: int, timeout: int, server_hostname: Optional[str]) -> tuple[bool, str]:
    """
    Attempt a TLS handshake without certificate validation.
    Returns (success, detail_or_error_category).
    """
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    try:
        raw = _tcp_connect(host, port, timeout)
    except socket.timeout:
        return False, "TIMEOUT"
    except ConnectionRefusedError:
        return False, "REFUSED"
    except OSError:
        return False, "UNREACHABLE"

    try:
        with raw:
            with ctx.wrap_socket(raw, server_hostname=server_hostname) as ss:
                try:
                    v = ss.version() or "TLS"
                except Exception:
                    v = "TLS"
                return True, v
    except ssl.SSLError as e:
        msg = str(e).lower()

        # Strong indicators the peer is NOT speaking TLS
        # (different OpenSSL builds phrase these differently across macOS/WSL/Windows)
        not_tls_markers = [
            "wrong version number",
            "unknown protocol",
            "http request",
            "packet length too long",
            "record layer failure",
            "unexpected eof",
        ]
        if any(m in msg for m in not_tls_markers):
            return False, "NOT_TLS_ON_PORT"

        # mTLS / client-cert required
        if "certificate required" in msg or ("tlsv1 alert" in msg and "certificate" in msg):
            return False, "MTLS_REQUIRED"

        if "alert handshake failure" in msg:
            return False, "TLS_HANDSHAKE_FAILED"

        return False, "TLS_HANDSHAKE_FAILED"
    except socket.timeout:
        return False, "TIMEOUT"
    except Exception:
        return False, "TLS_HANDSHAKE_FAILED"


def _http_probe_plain(host: str, port: int, timeout: int) -> tuple[bool, str]:
    """
    Plain HTTP probe (NO TLS).
    Returns (is_http, detail). Includes an HTTPS-port-rejection guard.
    """
    try:
        s = _tcp_connect(host, port, timeout)
    except socket.timeout:
        return False, "TIMEOUT"
    except Exception:
        return False, "CONNECT_FAILED"

    try:
        with s:
            req = b"GET / HTTP/1.0\r\nHost: localhost\r\nUser-Agent: quirk\r\n\r\n"
            s.sendall(req)
            data = s.recv(512)

            if not data.startswith(b"HTTP/"):
                return False, "NO_HTTP_SIGNATURE"

            # If this is an HTTPS listener, nginx often returns this message
            lower = data.lower()
            if b"plain http request was sent to https port" in lower:
                return False, "HTTP_TO_HTTPS_PORT_REJECTED"

            first_line = data.split(b"\r\n", 1)[0].decode("utf-8", errors="replace")
            return True, first_line
    except socket.timeout:
        return False, "TIMEOUT"
    except Exception:
        return False, "HTTP_PROBE_FAILED"


def fingerprint_service(host: str, port: int, timeout: int = 3) -> Fingerprint:
    """
    Protocol classifier v3.7.3

    Order:
      1) SSH banner (accurate, cheap)
      2) TLS handshake (authoritative when success)
      3) If TLS is NOT confirmed (NOT_TLS_ON_PORT OR TLS_HANDSHAKE_FAILED),
         attempt a *safe* plaintext HTTP probe:
            - If HTTP responds and is NOT "HTTPS port rejection", classify as HTTP.
            - Otherwise classify as TLS-associated blocker (MTLS_REQUIRED/HANDSHAKE_FAILED)
      4) Unknown open port
    """
    # Open check + SSH banner
    try:
        s = _tcp_connect(host, port, timeout)
    except socket.timeout:
        return Fingerprint(False, "CLOSED", "TIMEOUT")
    except ConnectionRefusedError:
        return Fingerprint(False, "CLOSED", "REFUSED")
    except OSError:
        return Fingerprint(False, "CLOSED", "UNREACHABLE")

    # BLOCK-01 / CR-08 (Phase 69, D-06): defense-in-depth socket cleanup.
    # `with s:` covers normal and Exception-typed exit from the SSH banner
    # check, but a BaseException (KeyboardInterrupt / SystemExit) raised
    # between `s = _tcp_connect(...)` above and entering the `with` block
    # below would leak the socket. The outer try/except BaseException
    # guarantees s.close() runs on every exit path, then re-raises.
    try:
        with s:
            banner = _try_read_ssh_banner(s)
            if banner:
                return Fingerprint(True, "SSH", banner)
    except BaseException:
        try:
            s.close()
        except Exception:
            pass
        raise

    # TLS check
    server_hostname = None if _is_ip(host) else host
    tls_ok, tls_detail = _tls_handshake(host, port, timeout, server_hostname=server_hostname)
    if tls_ok:
        return Fingerprint(True, "TLS", tls_detail)

    # If mTLS required, keep it TLS-associated (don't probe HTTP)
    if tls_detail == "MTLS_REQUIRED":
        return Fingerprint(True, "TLS", "MTLS_REQUIRED")

    # If TLS appears absent OR handshake failed, try safe HTTP probe
    if tls_detail in {"NOT_TLS_ON_PORT", "TLS_HANDSHAKE_FAILED"}:
        is_http, http_detail = _http_probe_plain(host, port, timeout)
        if is_http:
            return Fingerprint(True, "HTTP", http_detail)

        # If HTTP probe indicates HTTPS rejection, that implies TLS listener
        if http_detail == "HTTP_TO_HTTPS_PORT_REJECTED":
            return Fingerprint(True, "TLS", "TLS_PRESENT_HTTP_REJECTED")

        # Otherwise keep TLS-ish error category if we had one
        if tls_detail == "TLS_HANDSHAKE_FAILED":
            return Fingerprint(True, "TLS", "TLS_HANDSHAKE_FAILED")
        return Fingerprint(True, "UNKNOWN", "OPEN_NOT_TLS")

    # Timeouts or other failures: treat as TLS-associated blocker (conservative)
    if tls_detail in {"TIMEOUT"}:
        return Fingerprint(True, "TLS", "TIMEOUT")

    return Fingerprint(True, "UNKNOWN", tls_detail)