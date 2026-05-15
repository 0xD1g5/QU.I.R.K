"""
BLOCK-01 (CR-08) — fingerprint socket cleanup tests.

Verifies that `fingerprint_service` closes the TCP socket returned by
`_tcp_connect` on every exception path between the assignment line and
the `with s:` block — including KeyboardInterrupt / SystemExit /
BaseException raised inside `_try_read_ssh_banner`.

Test strategy (per D-07): monkeypatch `_tcp_connect` to return a tracked
fake socket, and monkeypatch `_try_read_ssh_banner` to raise the chosen
exception. Assert the fake socket's close() was called.

Note on the plan vs. code naming: the plan refers to `fingerprint_port`;
the actual function in quirk/scanner/fingerprint.py is named
`fingerprint_service` (the SSH-banner branch starting at line 146 with
the bare `s = _tcp_connect(...)` then `with s:` two lines later).
"""
from __future__ import annotations

import inspect
import re

import pytest

from quirk.scanner import fingerprint


class _FakeSocket:
    """Minimal socket-shaped object tracking close() and supporting `with`."""

    def __init__(self):
        self.close_count = 0

    def close(self):
        self.close_count += 1

    # Context manager protocol — `with s:` calls __exit__ which closes.
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False  # never suppress


# ---------------------------------------------------------------------------
# Behavior tests
# ---------------------------------------------------------------------------

def test_socket_closed_on_keyboard_interrupt(monkeypatch):
    """
    KeyboardInterrupt inside `_try_read_ssh_banner` (or anywhere between
    `s = _tcp_connect(...)` and entering `with s:`) must still close the
    socket. Without the BLOCK-01 fix the socket leaks because the bare
    `with s:` block won't be entered if the interrupt fires before its
    __enter__.

    KeyboardInterrupt is a BaseException — not an Exception — so the
    existing `except Exception` clauses in `fingerprint_service` do not
    catch it. The new `try/except BaseException` (D-06) must.
    """
    fake = _FakeSocket()
    monkeypatch.setattr(fingerprint, "_tcp_connect", lambda host, port, timeout: fake)

    def _raise_kbi(s):
        raise KeyboardInterrupt("simulated Ctrl-C")

    monkeypatch.setattr(fingerprint, "_try_read_ssh_banner", _raise_kbi)

    with pytest.raises(KeyboardInterrupt):
        fingerprint.fingerprint_service("127.0.0.1", 22, timeout=2)

    assert fake.close_count >= 1, (
        "fingerprint socket was NOT closed when KeyboardInterrupt raised "
        "between _tcp_connect and the with-block — BLOCK-01 (CR-08) leak"
    )


def test_socket_closed_on_system_exit(monkeypatch):
    """
    Same guarantee for SystemExit (the other common BaseException
    subclass that bypasses `except Exception`).
    """
    fake = _FakeSocket()
    monkeypatch.setattr(fingerprint, "_tcp_connect", lambda host, port, timeout: fake)

    def _raise_se(s):
        raise SystemExit("simulated exit")

    monkeypatch.setattr(fingerprint, "_try_read_ssh_banner", _raise_se)

    with pytest.raises(SystemExit):
        fingerprint.fingerprint_service("127.0.0.1", 22, timeout=2)

    assert fake.close_count >= 1, (
        "fingerprint socket was NOT closed when SystemExit raised "
        "between _tcp_connect and the with-block — BLOCK-01 (CR-08) leak"
    )


def test_socket_closed_on_normal_ssh_banner_path(monkeypatch):
    """
    Sanity check: when _try_read_ssh_banner returns a banner cleanly,
    the existing `with s:` context manager still closes the socket as
    before. Guards the BLOCK-01 fix against breaking the happy path.
    """
    fake = _FakeSocket()
    monkeypatch.setattr(fingerprint, "_tcp_connect", lambda host, port, timeout: fake)
    monkeypatch.setattr(
        fingerprint, "_try_read_ssh_banner", lambda s: "SSH-2.0-OpenSSH_9.0"
    )

    result = fingerprint.fingerprint_service("127.0.0.1", 22, timeout=2)

    assert result.is_open is True
    assert result.proto == "SSH"
    assert result.detail == "SSH-2.0-OpenSSH_9.0"
    assert fake.close_count >= 1, (
        "fingerprint socket was not closed on the normal SSH banner path"
    )


# ---------------------------------------------------------------------------
# Structural test — guards against accidental removal of the cleanup pattern
# ---------------------------------------------------------------------------

def test_fingerprint_service_has_baseexception_socket_close():
    """
    Source-shape guard: the SSH-banner branch in `fingerprint_service`
    must contain a `try/except BaseException` (or equivalent) that
    closes the socket. CPython's eager refcount cleanup can mask the
    KeyboardInterrupt leak when the FakeSocket is the only reference,
    so this structural check is the durable guarantee.
    """
    src = inspect.getsource(fingerprint.fingerprint_service)
    assert re.search(r"except\s+BaseException", src), (
        "missing `except BaseException` in fingerprint_service — "
        "BLOCK-01 (CR-08) socket cleanup pattern absent"
    )
    assert re.search(r"\bs\.close\s*\(\s*\)", src), (
        "missing `s.close()` call in fingerprint_service — "
        "BLOCK-01 (CR-08) socket cleanup pattern absent"
    )
