"""quirk.siem.transport — stdlib socket syslog transport (Phase 103 SIEM-01).

Implements send_syslog_raw(): delivers a pre-formatted CEF string over UDP or TCP
using the stdlib socket module only (zero new pip deps).

RFC 3164 framing: prepends <PRI> byte sequence (<facility*8 + syslog_severity>).
  facility = LOG_USER (1)
  syslog severity = LOG_WARNING (4)
  encoded PRI = 1*8+4 = 12 -> b"<12>"

The <PRI> prefix is the transport layer's responsibility; the formatter
(quirk/siem/formatter.py) returns the raw CEF string without a prefix.

Endpoint validation (AUDIT-11): validates host, port range, AND performs an SSRF
guard via validate_external_url (allow_internal=True) before opening a socket:
  - RFC1918 / loopback (10.x.x.x, 192.168.x.x, 127.x.x.x) → ALLOWED (CONTEXT.md
    D-02: syslog collectors are commonly on internal networks and must stay reachable).
  - Metadata/link-local IPs (169.254.0.0/16, 169.254.169.254, fd00:ec2::254) →
    ALWAYS BLOCKED — these are cloud IMDS endpoints; a misconfigured syslog host
    pointing at 169.254.169.254 would exfiltrate cloud credentials via CEF content.
  - Cloud metadata hostname aliases (metadata.google.internal etc.) → BLOCKED.

On failure (unreachable endpoint, timeout, network error), OSError propagates to
the caller.  The dispatcher wraps each send in try/except and writes an
IntegrationDelivery audit row; the transport itself never swallows errors.
"""
from __future__ import annotations

import ipaddress
import logging
import socket

logger = logging.getLogger(__name__)

# Syslog priority: LOG_USER facility (1), LOG_WARNING severity (4) -> 12
_SYSLOG_PRI = (1 * 8) + 4  # = 12

# IPv4 link-local range (169.254.0.0/16) — always blocked for syslog hosts.
# This covers both the AWS/Azure/GCP metadata IP (169.254.169.254) and the
# broader link-local range which has no legitimate syslog collector use case.
_IPV4_LINK_LOCAL = ipaddress.ip_network("169.254.0.0/16")


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
        ValueError: If host is empty, port is outside [1, 65535], or host resolves
                    to a metadata/link-local address (AUDIT-11 SSRF guard).
        OSError:    On any socket error (connection refused, timeout, etc.).
                    The caller (dispatcher) wraps each call in try/except.

    Note:
        Internal/loopback targets are explicitly allowed — syslog collectors are
        commonly on internal networks (CONTEXT.md D-02).  Only metadata and
        link-local IPs (169.254.0.0/16) are blocked regardless of allow_internal.
    """
    # --- Validate format ---
    if not host:
        raise ValueError("host must be a non-empty string")
    if not isinstance(port, int) or not (1 <= port <= 65535):
        raise ValueError(f"port must be an integer in range [1, 65535], got: {port!r}")

    # --- SSRF guard (AUDIT-11): reject metadata/link-local hosts before socket open ---
    # Build a minimal parseable URL so validate_external_url can extract the host/IP.
    # allow_internal=True preserves D-02: RFC1918 + loopback syslog collectors are fine.
    # Metadata IPs (169.254.169.254) and metadata hostname aliases are ALWAYS blocked by
    # validate_external_url regardless of allow_internal.
    # Additionally, we explicitly block the entire 169.254.0.0/16 link-local range here
    # because allow_internal=True would otherwise pass non-metadata link-local IPs
    # (e.g. 169.254.0.1) — these have no legitimate syslog use case.
    from quirk.util.url_allowlist import validate_external_url
    _url_for_check = f"http://{host}"
    _result = validate_external_url(_url_for_check, allow_internal=True)
    if not _result.ok:
        raise ValueError(f"Syslog host rejected: {_result.reason} ({host!r})")

    # Secondary check: block the entire 169.254.0.0/16 range (link-local) not caught
    # above. validate_external_url with allow_internal=True passes link-local IPs that
    # are not in _METADATA_IPS; the syslog use case has no valid link-local collectors.
    # Only applies when host is an IP literal (hostnames are handled by validate_external_url).
    try:
        _ip = ipaddress.ip_address(host)
        if isinstance(_ip, ipaddress.IPv4Address) and _ip in _IPV4_LINK_LOCAL:
            raise ValueError(
                f"Syslog host rejected: link-local address {host!r} is in "
                "169.254.0.0/16 (metadata/IMDS range)"
            )
    except ValueError as exc:
        # Re-raise our explicit link-local rejection; ignore parse errors for hostnames
        if "link-local" in str(exc):
            raise

    # --- Build payload: <PRI>CEF:0|... encoded as UTF-8 ---
    payload = f"<{_SYSLOG_PRI}>{cef_msg}".encode("utf-8")

    _VALID_PROTOCOLS = {"udp", "tcp"}
    if protocol not in _VALID_PROTOCOLS:
        raise ValueError(f"protocol must be 'udp' or 'tcp', got: {protocol!r}")
    socktype = socket.SOCK_STREAM if protocol == "tcp" else socket.SOCK_DGRAM

    with socket.socket(socket.AF_INET, socktype) as sock:
        sock.settimeout(timeout)
        if socktype == socket.SOCK_STREAM:
            sock.connect((host, port))
            # RFC 6587 section 3.4.2: Non-Transparent-Framing — append LF so
            # the TCP receiver can determine message boundaries.  Without this
            # delimiter, most syslog daemons (rsyslog, syslog-ng, Splunk) either
            # buffer indefinitely or concatenate successive sends into one blob.
            sock.sendall(payload + b"\n")
        else:
            sock.sendto(payload, (host, port))

    logger.debug("SIEM syslog sent (%s): %s:%d", protocol.upper(), host, port)
