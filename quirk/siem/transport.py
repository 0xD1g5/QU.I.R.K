"""quirk.siem.transport — stdlib socket syslog transport (Phase 103 SIEM-01).

Implements send_syslog_raw(): delivers a pre-formatted CEF string over UDP or TCP
using the stdlib socket module only (zero new pip deps).

RFC 3164 framing: prepends <PRI> byte sequence (<facility*8 + syslog_severity>).
  facility = LOG_USER (1)
  syslog severity = LOG_WARNING (4)
  encoded PRI = 1*8+4 = 12 -> b"<12>"

The <PRI> prefix is the transport layer's responsibility; the formatter
(quirk/siem/formatter.py) returns the raw CEF string without a prefix.

Endpoint validation: validates only that host is non-empty and 1 <= port <= 65535.
Do NOT call validate_external_url — syslog collectors are commonly on internal
networks and MUST NOT be blocked (CONTEXT.md D-02).

On failure (unreachable endpoint, timeout, network error), OSError propagates to
the caller.  The dispatcher wraps each send in try/except and writes an
IntegrationDelivery audit row; the transport itself never swallows errors.
"""
from __future__ import annotations

import logging
import socket

logger = logging.getLogger(__name__)

# Syslog priority: LOG_USER facility (1), LOG_WARNING severity (4) -> 12
_SYSLOG_PRI = (1 * 8) + 4  # = 12


def send_syslog_raw(
    cef_msg: str,
    host: str,
    port: int,
    protocol: str = "udp",
    timeout: int = 5,
) -> None:
    """Send a pre-formatted CEF string with RFC 3164 <PRI> prefix via socket.

    Args:
        cef_msg:  Complete CEF:0 line (without <PRI> prefix — transport adds it).
        host:     Syslog receiver hostname or IP address.  Must be non-empty.
        port:     Syslog receiver port.  Must be 1 <= port <= 65535.
        protocol: "udp" (SOCK_DGRAM, default) or "tcp" (SOCK_STREAM).
        timeout:  Socket timeout in seconds (default: 5).

    Raises:
        ValueError: If host is empty or port is outside [1, 65535].
        OSError:    On any socket error (connection refused, timeout, etc.).
                    The caller (dispatcher) wraps each call in try/except.

    Note:
        Endpoint validation is FORMAT-ONLY (non-empty host, valid port range).
        Internal/loopback targets are explicitly NOT blocked — syslog collectors
        are commonly on internal networks (CONTEXT.md D-02).
    """
    # --- Validate format only (not SSRF/internal-block) ---
    if not host:
        raise ValueError("host must be a non-empty string")
    if not isinstance(port, int) or not (1 <= port <= 65535):
        raise ValueError(f"port must be an integer in range [1, 65535], got: {port!r}")

    # --- Build payload: <PRI>CEF:0|... encoded as UTF-8 ---
    payload = f"<{_SYSLOG_PRI}>{cef_msg}".encode("utf-8")

    socktype = socket.SOCK_STREAM if protocol == "tcp" else socket.SOCK_DGRAM

    with socket.socket(socket.AF_INET, socktype) as sock:
        sock.settimeout(timeout)
        if socktype == socket.SOCK_STREAM:
            sock.connect((host, port))
            sock.sendall(payload)
        else:
            sock.sendto(payload, (host, port))

    logger.debug("SIEM syslog sent (%s): %s:%d", protocol.upper(), host, port)
