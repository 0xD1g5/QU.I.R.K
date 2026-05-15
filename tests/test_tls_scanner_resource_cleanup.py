"""
BLOCK-01 (CR-07) — sslyze Scanner cleanup tests.

Verifies that _scan_one_sslyze deletes its sslyze Scanner instance on every
exit path (normal completion AND exception during get_results), so the
internal nassl thread/process pool is released deterministically rather
than lingering until GC.

Test strategy (per D-07): inject a fake Scanner class via monkeypatch on
the module attribute `SslyzeScanner`. The fake's __del__ flips a tracking
flag we can assert on after the call.
"""
from __future__ import annotations

import gc

import pytest

from quirk.scanner import tls_scanner


class _Tracker:
    """Mutable flag holder — captured by closure in the fake Scanner."""
    def __init__(self):
        self.deleted = False


def _make_fake_scanner_cls(tracker: _Tracker, raise_exc: BaseException = None):
    """
    Build a Scanner-shaped class.
    - queue_scans is a no-op.
    - get_results either returns [] (normal) or raises the provided exception.
    - __del__ flips tracker.deleted = True so we can assert cleanup ran.

    Reference-cycle note: the fake Scanner holds a reference to itself via
    a sentinel attribute, breaking CPython refcount-driven auto-release.
    Only an explicit `del scanner` (or gc.collect on the cycle) drops it.
    This makes the test actually distinguish "fix present" from "no fix":
    without try/finally+del, the cycle survives the exception unwind and
    __del__ never fires before our assertion.
    """
    class _FakeScanner:
        def __init__(self, *args, **kwargs):
            # mirror sslyze.Scanner(per_server_concurrent_connections_limit=2)
            # Self-reference creates a cycle that defeats refcount cleanup.
            self._self_ref = self

        def queue_scans(self, requests):
            return None

        def get_results(self):
            if raise_exc is not None:
                raise raise_exc
            return iter([])  # empty -> _scan_one_sslyze returns None

        def __del__(self):
            tracker.deleted = True

    return _FakeScanner


def test_sslyze_scanner_deleted_on_get_results_exception(monkeypatch):
    """
    When sslyze.get_results() raises mid-scan, the Scanner object must
    still be released (try/finally + del scanner). This is the BLOCK-01
    leak fix: without try/finally, the Scanner instance lingers in the
    exception frame until the surrounding scope ends.
    """
    tracker = _Tracker()
    fake_cls = _make_fake_scanner_cls(tracker, raise_exc=RuntimeError("boom"))

    monkeypatch.setattr(tls_scanner, "SSLYZE_AVAILABLE", True)
    monkeypatch.setattr(tls_scanner, "SslyzeScanner", fake_cls)

    # _scan_one_sslyze catches all Exception subclasses and returns None.
    # We don't expect a raise to escape — we only assert cleanup ran.
    result = tls_scanner._scan_one_sslyze(
        host="127.0.0.1",
        port=443,
        timeout=2,
        include_sni=False,
        logger=None,
    )

    # NOTE: do NOT gc.collect() here — we want to prove the fix released the
    # Scanner during _scan_one_sslyze, not after a generation-2 sweep. The
    # try/finally with explicit `del scanner` breaks the self-reference cycle
    # immediately. Without the fix the cycle survives function return.
    assert result is None  # exception path falls through to None
    assert tracker.deleted is True, (
        "sslyze Scanner was not released after get_results() raised — "
        "BLOCK-01 try/finally cleanup missing in _scan_one_sslyze"
    )


def test_sslyze_scanner_deleted_on_normal_completion(monkeypatch):
    """
    Sanity check: on the normal (no-exception) path, the Scanner must also
    be released. Without the explicit `del scanner`, the local would stay
    alive until the function returns — this test guards against a future
    refactor that moves the Scanner out of the function scope.
    """
    tracker = _Tracker()
    fake_cls = _make_fake_scanner_cls(tracker, raise_exc=None)

    monkeypatch.setattr(tls_scanner, "SSLYZE_AVAILABLE", True)
    monkeypatch.setattr(tls_scanner, "SslyzeScanner", fake_cls)

    result = tls_scanner._scan_one_sslyze(
        host="127.0.0.1",
        port=443,
        timeout=2,
        include_sni=False,
        logger=None,
    )

    # Again: no gc.collect() — the fix's `del scanner` must break the
    # self-reference cycle deterministically on the success path too.
    assert result is None  # empty results -> None
    assert tracker.deleted is True, (
        "sslyze Scanner was not released after normal completion — "
        "BLOCK-01 try/finally cleanup did not run on the success path"
    )
