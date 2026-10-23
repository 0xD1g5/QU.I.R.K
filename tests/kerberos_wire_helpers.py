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


def late_close(delay):
    """Reads the request, stays silent ``delay`` s, then closes with zero bytes.

    230-REVIEW-R4 WR-01: an idle-closing listener, or a proxy whose backend
    connect timed out.  A zero-byte close, but not a fast one.
    """
    def handler(c, stop):
        stop.wait(delay)
    return handler


def reset_immediately(c, stop):
    """Reads the request, then resets with zero bytes (SO_LINGER 1,0 -> RST).

    230-REVIEW-R4 WR-03: a real ``ConnectionResetError`` on the client's
    ``recv``, not a hand-built exception.
    """
    c.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))


# --- 230-08 D-29: loopback UDP peers (no impacket import) --------------------


def tcp_port_is_closed(port):
    """True when a TCP connect to 127.0.0.1:``port`` is refused (nothing listens)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1)
    try:
        s.connect(("127.0.0.1", port))
    except ConnectionRefusedError:
        return True
    except OSError:
        return False
    finally:
        s.close()
    return False


class UdpPeer:
    """Loopback UDP listener that runs ``handler(sock, data, addr, stop)`` per datagram.

    ``require_no_tcp`` re-binds until the chosen port number has no TCP
    listener, so the scanner's real TCP connect is refused and its real UDP
    fallback runs against this peer.  Every socket has its own timeout.
    """

    def __init__(self, handler, require_no_tcp=True):
        self.handler = handler
        self.stop = threading.Event()
        self.requests = []
        for _ in range(50):
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
            if not require_no_tcp or tcp_port_is_closed(port):
                break
            sock.close()
        else:  # pragma: no cover - 50 collisions in a row
            raise RuntimeError("could not find a UDP port with no TCP listener")
        self.sock = sock
        self.sock.settimeout(0.2)
        self.port = port
        self._t = threading.Thread(target=self._serve, daemon=True)
        self._t.start()

    def _serve(self):
        while not self.stop.is_set():
            try:
                data, addr = self.sock.recvfrom(65535)
            except socket.timeout:
                continue
            except OSError:
                return
            self.requests.append(data)
            try:
                self.handler(self.sock, data, addr, self.stop)
            except OSError:
                pass

    def close(self):
        self.stop.set()
        self._t.join(2)
        self.sock.close()


def closed_udp_port():
    """A UDP port number with nothing bound and nothing listening on TCP."""
    peer = UdpPeer(udp_silent)
    port = peer.port
    peer.close()
    return port


def udp_silent(sock, data, addr, stop):
    """Receives the datagram and never replies."""


def udp_reply(blob):
    """Replies to every datagram with ``blob`` from the KDC address."""
    def handler(sock, data, addr, stop):
        sock.sendto(blob, addr)
    return handler


def udp_reply_from_other_port(blob):
    """Spoof control: the reply comes from a DIFFERENT source port than the
    address the scanner probed.  A connected UDP socket must discard it."""
    def handler(sock, data, addr, stop):
        other = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            other.settimeout(1)
            other.bind(("127.0.0.1", 0))
            other.sendto(blob, addr)
        finally:
            other.close()
    return handler


def udp_empty(sock, data, addr, stop):
    """Replies with a zero-length datagram."""
    sock.sendto(b"", addr)
