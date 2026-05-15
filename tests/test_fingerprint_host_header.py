"""Phase 77 D-04 / scanners-protocol/IN-04: HTTP probe sends target hostname.

The previous probe hard-coded ``Host: localhost`` in the HTTP/1.0 request
line, which mis-routes virtual-host servers and leaks intent. The fix
substitutes the actual target hostname (the function already receives it
as the ``host`` parameter).
"""
from __future__ import annotations

import socket
from unittest.mock import MagicMock, patch


def test_http_probe_plain_sends_target_host_header() -> None:
    from quirk.scanner import fingerprint as fp

    fake_sock = MagicMock(spec=socket.socket)
    # response just needs to be a valid HTTP signature so the probe doesn't
    # short-circuit before we observe the bytes it sent.
    fake_sock.recv.return_value = b"HTTP/1.1 200 OK\r\nServer: x\r\n\r\n"
    # context-manager protocol used inside _http_probe_plain (`with s:`)
    fake_sock.__enter__.return_value = fake_sock
    fake_sock.__exit__.return_value = False

    with patch.object(fp, "_tcp_connect", return_value=fake_sock):
        fp._http_probe_plain("example.org", 80, timeout=2)

    # _http_probe_plain calls sock.sendall(req); inspect the bytes
    assert fake_sock.sendall.called, "Expected the probe to call sock.sendall"
    sent = fake_sock.sendall.call_args[0][0]
    assert b"Host: example.org" in sent
    assert b"Host: localhost" not in sent
