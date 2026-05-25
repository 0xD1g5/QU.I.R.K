"""Tests for quirk/siem/transport.py — syslog UDP/TCP transport (Phase 103 SIEM-01).

Covers:
- send_syslog_raw delivers CEF over UDP; captured datagram contains b"CEF:0" and <12> prefix
- send_syslog_raw delivers CEF over TCP; same assertions
- Unreachable endpoint raises OSError (caller isolation pattern)
- Empty host raises ValueError
- Port 0 and port 70000 raise ValueError
- Loopback host (127.0.0.1) is NOT blocked — syslog collectors are internal
"""
from __future__ import annotations

import socket
import socketserver
import threading

import pytest


# ---------------------------------------------------------------------------
# Helpers: in-process UDP/TCP capture servers
# ---------------------------------------------------------------------------

class _UDPCapture(socketserver.UDPServer):
    """UDP server that captures incoming datagrams for assertion."""

    allow_reuse_address = True

    def __init__(self, host: str, port: int) -> None:
        self.captured: list[bytes] = []
        super().__init__((host, port), self._Handler)

    class _Handler(socketserver.BaseRequestHandler):
        def handle(self) -> None:
            self.server.captured.append(self.request[0])


class _TCPCapture(socketserver.TCPServer):
    """TCP server that captures the first received bytes for assertion."""

    allow_reuse_address = True

    def __init__(self, host: str, port: int) -> None:
        self.captured: list[bytes] = []
        super().__init__((host, port), self._Handler)

    class _Handler(socketserver.StreamRequestHandler):
        def handle(self) -> None:
            data = self.rfile.read(4096)
            self.server.captured.append(data)


# ---------------------------------------------------------------------------
# Tests — UDP delivery
# ---------------------------------------------------------------------------

class TestSendSyslogRawUDP:
    """send_syslog_raw delivers over UDP with correct framing."""

    def test_send_cef_udp_delivers(self):
        """UDP datagram captured by in-process server contains b'CEF:0'."""
        from quirk.siem.transport import send_syslog_raw

        server = _UDPCapture("127.0.0.1", 0)
        port = server.server_address[1]
        t = threading.Thread(target=server.handle_request, daemon=True)
        t.start()

        send_syslog_raw("CEF:0|QUIRK|scanner|1.0.0|test|Test Finding|5|dhost=localhost", "127.0.0.1", port, "udp")

        t.join(timeout=3)
        assert server.captured, "No UDP datagram received by capture server"
        assert b"CEF:0" in server.captured[0], (
            f"Expected b'CEF:0' in captured datagram: {server.captured[0]!r}"
        )

    def test_send_cef_udp_has_pri_prefix(self):
        """UDP datagram starts with the <12> syslog priority prefix (<PRI>)."""
        from quirk.siem.transport import send_syslog_raw

        server = _UDPCapture("127.0.0.1", 0)
        port = server.server_address[1]
        t = threading.Thread(target=server.handle_request, daemon=True)
        t.start()

        send_syslog_raw("CEF:0|QUIRK|scanner|1.0.0|test|Test|5|dhost=localhost", "127.0.0.1", port, "udp")

        t.join(timeout=3)
        assert server.captured, "No UDP datagram received"
        # pri = LOG_USER(1)*8 + LOG_WARNING(4) = 12 -> b"<12>"
        assert server.captured[0].startswith(b"<12>"), (
            f"Expected datagram to start with b'<12>', got: {server.captured[0][:10]!r}"
        )


# ---------------------------------------------------------------------------
# Tests — TCP delivery
# ---------------------------------------------------------------------------

class TestSendSyslogRawTCP:
    """send_syslog_raw delivers over TCP with correct framing."""

    def test_send_cef_tcp_delivers(self):
        """TCP bytes captured by in-process server contain b'CEF:0'."""
        from quirk.siem.transport import send_syslog_raw

        server = _TCPCapture("127.0.0.1", 0)
        port = server.server_address[1]
        t = threading.Thread(target=server.handle_request, daemon=True)
        t.start()

        send_syslog_raw("CEF:0|QUIRK|scanner|1.0.0|test|Test Finding|5|dhost=localhost", "127.0.0.1", port, "tcp")

        t.join(timeout=3)
        assert server.captured, "No TCP data received by capture server"
        assert b"CEF:0" in server.captured[0], (
            f"Expected b'CEF:0' in captured TCP data: {server.captured[0]!r}"
        )

    def test_send_cef_tcp_has_pri_prefix(self):
        """TCP payload starts with the <12> syslog priority prefix."""
        from quirk.siem.transport import send_syslog_raw

        server = _TCPCapture("127.0.0.1", 0)
        port = server.server_address[1]
        t = threading.Thread(target=server.handle_request, daemon=True)
        t.start()

        send_syslog_raw("CEF:0|QUIRK|scanner|1.0.0|test|Test|5|dhost=localhost", "127.0.0.1", port, "tcp")

        t.join(timeout=3)
        assert server.captured, "No TCP data received"
        assert server.captured[0].startswith(b"<12>"), (
            f"Expected TCP payload to start with b'<12>', got: {server.captured[0][:10]!r}"
        )

    def test_send_cef_tcp_ends_with_lf(self):
        """CR-02: TCP payload ends with LF (RFC 6587 non-transparent framing)."""
        from quirk.siem.transport import send_syslog_raw

        server = _TCPCapture("127.0.0.1", 0)
        port = server.server_address[1]
        t = threading.Thread(target=server.handle_request, daemon=True)
        t.start()

        send_syslog_raw("CEF:0|QUIRK|scanner|1.0.0|test|Test|5|dhost=localhost", "127.0.0.1", port, "tcp")

        t.join(timeout=3)
        assert server.captured, "No TCP data received"
        assert server.captured[0].endswith(b"\n"), (
            f"TCP payload must end with LF (RFC 6587 non-transparent framing). "
            f"Got tail: {server.captured[0][-4:]!r}"
        )


# ---------------------------------------------------------------------------
# Tests — Unreachable endpoint raises OSError
# ---------------------------------------------------------------------------

class TestSendSyslogRawUnreachable:
    """An unreachable endpoint must raise OSError for the caller to isolate."""

    def test_unreachable_raises(self):
        """send_syslog_raw to a refused TCP port raises OSError."""
        from quirk.siem.transport import send_syslog_raw

        # Grab a free port then close it immediately so it is refused
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            refused_port = s.getsockname()[1]
        # Port is now closed/refused

        with pytest.raises(OSError):
            send_syslog_raw("CEF:0|test", "127.0.0.1", refused_port, "tcp", timeout=1)


# ---------------------------------------------------------------------------
# Tests — Input validation (ValueError)
# ---------------------------------------------------------------------------

class TestSendSyslogRawValidation:
    """send_syslog_raw raises ValueError for empty host or bad port."""

    def test_rejects_empty_host(self):
        from quirk.siem.transport import send_syslog_raw

        with pytest.raises(ValueError, match="host"):
            send_syslog_raw("CEF:0|test", "", 514)

    def test_rejects_port_zero(self):
        from quirk.siem.transport import send_syslog_raw

        with pytest.raises(ValueError, match="port"):
            send_syslog_raw("CEF:0|test", "127.0.0.1", 0)

    def test_rejects_port_too_high(self):
        from quirk.siem.transport import send_syslog_raw

        with pytest.raises(ValueError, match="port"):
            send_syslog_raw("CEF:0|test", "127.0.0.1", 70000)

    def test_rejects_port_negative(self):
        from quirk.siem.transport import send_syslog_raw

        with pytest.raises(ValueError, match="port"):
            send_syslog_raw("CEF:0|test", "127.0.0.1", -1)

    def test_rejects_unknown_protocol(self):
        """WR-01: unknown protocol raises ValueError instead of silently falling through to UDP."""
        from quirk.siem.transport import send_syslog_raw

        with pytest.raises(ValueError, match="protocol"):
            send_syslog_raw("CEF:0|test", "127.0.0.1", 514, protocol="tls")

    def test_rejects_invalid_protocol_string(self):
        """WR-01: an arbitrary unknown string raises ValueError."""
        from quirk.siem.transport import send_syslog_raw

        with pytest.raises(ValueError, match="protocol"):
            send_syslog_raw("CEF:0|test", "127.0.0.1", 514, protocol="sctp")


# ---------------------------------------------------------------------------
# Tests — Loopback NOT blocked (CONTEXT.md D-02)
# ---------------------------------------------------------------------------

class TestSendSyslogRawLoopback:
    """127.0.0.1 with a live receiver succeeds — no internal-IP block."""

    def test_does_not_block_loopback(self):
        """Loopback (127.0.0.1) host with active listener does NOT raise ValueError.

        Per CONTEXT.md D-02: syslog collectors are commonly on internal networks.
        Unlike send_webhook (which calls validate_external_url), send_syslog_raw
        must NOT block internal/loopback targets. This test asserts that a
        successful send to 127.0.0.1 with a live UDP server does not raise any
        ValueError about the host being internal.
        """
        from quirk.siem.transport import send_syslog_raw

        server = _UDPCapture("127.0.0.1", 0)
        port = server.server_address[1]
        t = threading.Thread(target=server.handle_request, daemon=True)
        t.start()

        # Must NOT raise ValueError (no internal-host block)
        send_syslog_raw("CEF:0|QUIRK|scanner|1.0.0|test|Test|5|dhost=localhost", "127.0.0.1", port, "udp")

        t.join(timeout=3)
        assert server.captured, "Expected datagram delivered to loopback receiver"
