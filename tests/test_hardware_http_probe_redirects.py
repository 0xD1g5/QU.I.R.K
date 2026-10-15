"""The hardware HTTP management probe stays on the host it was asked to probe.

A 3xx answer counts as "responded" and its Location is never fetched, so a
scan target cannot send the probe to a different host.
"""
from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from quirk.scanner.hardware_scanner import _probe_http_mgmt


def _serve(handler_cls):
    server = HTTPServer(("127.0.0.1", 0), handler_cls)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


@pytest.fixture
def other_host():
    hits = []

    class Vendor(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            hits.append(self.path)
            body = b"<title>FortiGate</title>"
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass

    server = _serve(Vendor)
    yield server, hits
    server.shutdown()
    server.server_close()


def _redirector(location):
    class Redirect(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            self.send_response(302)
            self.send_header("Location", location)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def log_message(self, *a):
            pass

    return _serve(Redirect)


def test_redirect_is_not_followed_and_counts_as_responded(other_host):
    target, hits = other_host
    redirect = _redirector(f"http://127.0.0.1:{target.server_port}/landing")
    try:
        result = _probe_http_mgmt("127.0.0.1", redirect.server_port, timeout=3)
    finally:
        redirect.shutdown()
        redirect.server_close()
    assert hits == []
    assert result == {"entry": None, "body": "", "responded": True}


def test_direct_vendor_answer_still_matches(other_host):
    """Positive control: a vendor page served directly is still recognised."""
    target, hits = other_host
    result = _probe_http_mgmt("127.0.0.1", target.server_port, timeout=3)
    assert hits
    assert result is not None and result["entry"] is not None
    assert "FortiGate" in result["body"]
