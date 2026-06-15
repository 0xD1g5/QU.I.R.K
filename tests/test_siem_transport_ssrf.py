"""RED test for AUDIT-11: SIEM transport SSRF guard (metadata/link-local rejection).

Asserts that send_syslog_raw raises ValueError (or a dedicated SSRF rejection)
for metadata/link-local hosts (169.254.169.254) WITHOUT opening a socket.

TODAY (current main): send_syslog_raw applies FORMAT-ONLY validation (non-empty host,
port range).  It proceeds straight to socket.socket() for 169.254.169.254 — so the
negative case assertion (raises before socket) FAILS.  This is the RED signal.

AUDIT-11 adds validate_external_url(f"syslog://{host}:{port}", allow_internal=True)
to send_syslog_raw BEFORE the socket.socket() call.  With allow_internal=True:
  - RFC1918 / loopback (127.0.0.1, 10.x.x.x, 192.168.x.x) → PASS (D-02: internal
    syslog collectors must remain reachable)
  - 169.254.0.0/16 metadata/link-local → BLOCKED (always-blocked regardless of
    allow_internal)

WAVE 2 (plan 131-03) makes send_syslog_raw call validate_external_url, making this
test GREEN.

pytest -q tests/test_siem_transport_ssrf.py
"""
from __future__ import annotations

import socket
from unittest.mock import MagicMock, patch, call

import pytest


# ---------------------------------------------------------------------------
# Tests — NEGATIVE: metadata/link-local host MUST be blocked before socket
# ---------------------------------------------------------------------------


class TestSendSyslogRawSSRFGuard:
    """AUDIT-11: metadata/link-local hosts are rejected before socket construction."""

    def test_metadata_host_rejected_before_socket(self):
        """AUDIT-11 RED: send_syslog_raw('...', host='169.254.169.254', port=514)
        must raise (ValueError or similar) without constructing a socket.

        TODAY this FAILS because transport goes straight to socket.socket() for any
        non-empty host — 169.254.169.254 reaches the socket layer unchecked.
        """
        from quirk.siem.transport import send_syslog_raw

        socket_constructed = []

        class _SentinelSocket:
            """Raises AssertionError if ever instantiated — should not be reached."""
            def __init__(self, *args, **kwargs):
                socket_constructed.append(True)
                raise AssertionError(
                    "socket.socket was constructed for a metadata/link-local host — "
                    "AUDIT-11 SSRF guard is missing from send_syslog_raw"
                )

        with patch("quirk.siem.transport.socket.socket", _SentinelSocket):
            # Must raise BEFORE constructing a socket
            with pytest.raises((ValueError, PermissionError, OSError)) as exc_info:
                send_syslog_raw(
                    "CEF:0|QUIRK|scanner|1.0.0|audit11|SSRF-test|5|dhost=meta",
                    host="169.254.169.254",
                    port=514,
                    protocol="udp",
                )

        # The exception must NOT be the AssertionError from our sentinel
        assert not isinstance(exc_info.value, AssertionError), (
            "socket.socket was constructed — SSRF guard did not fire before socket"
        )
        # And the socket sentinel must NOT have been called
        assert not socket_constructed, (
            "socket.socket was instantiated for metadata host 169.254.169.254 — "
            "AUDIT-11 guard missing"
        )

    def test_link_local_169_254_0_1_rejected(self):
        """AUDIT-11 RED: 169.254.0.1 (link-local range, not just .169.254) is blocked."""
        from quirk.siem.transport import send_syslog_raw

        socket_constructed = []

        class _SentinelSocket:
            def __init__(self, *args, **kwargs):
                socket_constructed.append(True)
                raise AssertionError("socket constructed for link-local host")

        with patch("quirk.siem.transport.socket.socket", _SentinelSocket):
            with pytest.raises((ValueError, PermissionError, OSError)) as exc_info:
                send_syslog_raw(
                    "CEF:0|QUIRK|scanner|1.0.0|audit11|SSRF-test|5|",
                    host="169.254.0.1",
                    port=514,
                    protocol="udp",
                )

        assert not isinstance(exc_info.value, AssertionError), (
            "socket was constructed for 169.254.0.1 — SSRF guard missing"
        )
        assert not socket_constructed, (
            "socket.socket instantiated for 169.254.0.1"
        )


# ---------------------------------------------------------------------------
# Tests — POSITIVE: internal/loopback MUST still reach the socket layer
# ---------------------------------------------------------------------------


class TestSendSyslogRawInternalAllowed:
    """AUDIT-11 positive: RFC1918/loopback hosts must PASS the guard (D-02 invariant).

    These tests are structured so they PASS against current main (no guard = no block)
    AND will continue to PASS after AUDIT-11 lands (guard allows internal with
    allow_internal=True).  They ensure the fix does not regress D-02.
    """

    def _make_mock_socket(self):
        """Return a context-manager-compatible mock socket."""
        mock_sock = MagicMock()
        mock_sock.__enter__ = MagicMock(return_value=mock_sock)
        mock_sock.__exit__ = MagicMock(return_value=False)
        return mock_sock

    def test_loopback_127_0_0_1_reaches_socket(self):
        """127.0.0.1 (loopback) must NOT be blocked — syslog collectors are internal.

        Per CONTEXT.md D-02 and the existing test_siem_transport.py loopback invariant.
        """
        from quirk.siem.transport import send_syslog_raw

        mock_sock = self._make_mock_socket()

        with patch("quirk.siem.transport.socket.socket", return_value=mock_sock):
            # Must NOT raise ValueError for loopback
            send_syslog_raw(
                "CEF:0|QUIRK|scanner|1.0.0|audit11|loopback-ok|5|dhost=localhost",
                host="127.0.0.1",
                port=514,
                protocol="udp",
            )

        # Socket was used (send reached transport layer)
        mock_sock.sendto.assert_called_once()

    def test_rfc1918_10_x_reaches_socket(self):
        """10.x.x.x (RFC1918) must NOT be blocked — internal syslog collectors."""
        from quirk.siem.transport import send_syslog_raw

        mock_sock = self._make_mock_socket()

        with patch("quirk.siem.transport.socket.socket", return_value=mock_sock):
            send_syslog_raw(
                "CEF:0|QUIRK|scanner|1.0.0|audit11|private-ok|5|",
                host="10.0.0.1",
                port=514,
                protocol="udp",
            )

        mock_sock.sendto.assert_called_once()

    def test_rfc1918_192_168_reaches_socket(self):
        """192.168.x.x (RFC1918) must NOT be blocked."""
        from quirk.siem.transport import send_syslog_raw

        mock_sock = self._make_mock_socket()

        with patch("quirk.siem.transport.socket.socket", return_value=mock_sock):
            send_syslog_raw(
                "CEF:0|QUIRK|scanner|1.0.0|audit11|private-ok|5|",
                host="192.168.1.100",
                port=514,
                protocol="udp",
            )

        mock_sock.sendto.assert_called_once()
