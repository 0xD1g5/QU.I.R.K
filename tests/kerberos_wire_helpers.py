"""Raw-socket peers and a hang watchdog for Kerberos transport tests.

230-REVIEW-R2 CR-01: the old fixture set ``socket.setdefaulttimeout`` process
wide and always length-prefixed its reply, which hid a production hang. These
peers misbehave on the wire the way real non-KDC listeners do. Every socket
here has its own timeout, and nothing touches the process-wide default.
No impacket import, so the CI-visible tests can use this module.
"""

import socket
import struct
import threading
import time


def run_with_watchdog(fn, budget):
    """Run ``fn`` in a daemon thread; fail (not hang) if it outlives ``budget``.

    Returns ``(result, exc, elapsed)``. On a hang, the stuck daemon thread is
    abandoned and the assertion fails, so a regression fails the suite instead
    of stalling it.
    """
    box = {}

    def run():
        t0 = time.monotonic()
        try:
            box["result"] = fn()
        except BaseException as exc:  # noqa: BLE001 - reported to the caller
            box["exc"] = exc
        box["elapsed"] = time.monotonic() - t0

    t = threading.Thread(target=run, daemon=True)
    t.start()
    t.join(budget)
    assert not t.is_alive(), f"watchdog: probe did not return within {budget}s (hang)"
    return box.get("result"), box.get("exc"), box["elapsed"]


class RawPeer:
    """Loopback TCP listener that runs ``handler(conn)`` per connection."""

    def __init__(self, handler):
        self.handler = handler
        self.stop = threading.Event()
        self.sock = socket.socket()
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(5)
        self.sock.settimeout(0.2)
        self.port = self.sock.getsockname()[1]
        self._t = threading.Thread(target=self._serve, daemon=True)
        self._t.start()

    def _serve(self):
        while not self.stop.is_set():
            try:
                c, _ = self.sock.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            try:
                c.settimeout(5)
                try:
                    c.recv(65535)  # the client's request; contents ignored
                except OSError:
                    pass
                self.handler(c, self.stop)
            except OSError:
                pass
            finally:
                c.close()

    def close(self):
        self.stop.set()
        self.sock.close()


def http_unframed(c, stop):
    """A real HTTP service on port 88: no length prefix, then close."""
    c.sendall(b"HTTP/1.1 400 Bad Request\r\nContent-Length: 0\r\n\r\n")


def short_then_close(c, stop):
    """Declares 4096 bytes, sends 5, closes (truncated reply)."""
    c.sendall(b"\x00\x00\x10\x00short")


def huge_declared(c, stop):
    """Declares 1 GiB, then holds the connection open sending nothing."""
    c.sendall(struct.pack(">I", 1 << 30))
    stop.wait(10)


def silent(c, stop):
    """Accepts, never replies, holds the connection open."""
    stop.wait(10)


def close_immediately(c, stop):
    """Accepts, closes without a byte."""


def slow_drip(c, stop):
    """Declares 100 bytes, then drips one byte every 0.3 s."""
    c.sendall(struct.pack(">I", 100))
    for _ in range(100):
        if stop.wait(0.3):
            return
        c.sendall(b"\x00")


def framed(blob):
    """A well-framed reply carrying ``blob`` (protocol-faithful KDC framing)."""
    def handler(c, stop):
        c.sendall(struct.pack(">I", len(blob)) + blob)
    return handler
