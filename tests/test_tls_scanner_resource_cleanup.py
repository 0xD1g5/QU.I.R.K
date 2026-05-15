"""
BLOCK-01 (CR-07) — sslyze Scanner cleanup tests.

Verifies that _scan_one_sslyze deletes its sslyze Scanner instance on every
exit path (normal completion AND exception during get_results), so the
internal nassl thread/process pool is released deterministically rather
than lingering until GC.

Test strategy (per D-07):
  * Behavior tests inject a fake Scanner via monkeypatch on
    `quirk.scanner.tls_scanner.SslyzeScanner`. The fake's __del__ appends
    to a module-level list we can assert ran.
  * The fake holds a self-reference cycle (`self._self_ref = self`) so
    that __del__ ONLY fires after a cycle-collector pass — exercising
    the BLOCK-01 fix's in-`finally` `gc.collect()`.
  * A source-shape test asserts the `try/finally + del scanner +
    gc.collect()` pattern is structurally present in `_scan_one_sslyze`.
    This locks the fix against future refactors regardless of what
    refcount cleanup CPython happens to provide.
"""
from __future__ import annotations

import gc
import inspect
import re

from quirk.scanner import tls_scanner


# Module-level so closures don't have to capture it
_DEL_CALLS: list[int] = []


class _FakeScannerBase:
    """Shared shape; subclasses override get_results to vary behavior."""
    def __init__(self, *args, **kwargs):
        # Self-reference defeats refcount cleanup; only cycle-collector frees.
        self._self_ref = self

    def queue_scans(self, requests):
        return None

    def get_results(self):
        return iter([])

    def __del__(self):
        _DEL_CALLS.append(1)


class _FakeScannerRaisesOnGetResults(_FakeScannerBase):
    def get_results(self):
        raise RuntimeError("boom from get_results")


class _FakeScannerNormal(_FakeScannerBase):
    pass


def _invoke(monkeypatch, fake_cls):
    _DEL_CALLS.clear()
    monkeypatch.setattr(tls_scanner, "SSLYZE_AVAILABLE", True)
    monkeypatch.setattr(tls_scanner, "SslyzeScanner", fake_cls)
    tls_scanner._scan_one_sslyze(
        host="127.0.0.1",
        port=443,
        timeout=2,
        include_sni=False,
        logger=None,
    )


# ---------------------------------------------------------------------------
# Behavior tests
# ---------------------------------------------------------------------------

def test_sslyze_scanner_released_on_exception_path(monkeypatch):
    """
    When get_results() raises mid-scan, the fake Scanner's __del__ must
    fire — proving sslyze's Scanner cleanup actually runs even when
    get_results explodes. The fake uses a self-reference cycle, so
    __del__ only fires after a cycle-collector pass, exercising the
    BLOCK-01 fix's in-`finally` `gc.collect()`.
    """
    _invoke(monkeypatch, _FakeScannerRaisesOnGetResults)
    gc.collect()

    assert _DEL_CALLS, (
        "FakeScanner.__del__ never fired after _scan_one_sslyze exception path — "
        "BLOCK-01 cleanup is broken: Scanner is leaked across exception unwinds"
    )


def test_sslyze_scanner_released_on_normal_path(monkeypatch):
    """
    Sanity check on the success path: the FakeScanner (self-reference
    cycle) must be released via __del__ by end of test. Guards against
    a refactor that hoists Scanner out of function scope.
    """
    _invoke(monkeypatch, _FakeScannerNormal)
    gc.collect()

    assert _DEL_CALLS, (
        "FakeScanner.__del__ never fired on the success path — "
        "BLOCK-01 cleanup did not run on normal completion"
    )


# ---------------------------------------------------------------------------
# Structural test — guards against accidental removal of the cleanup pattern
# ---------------------------------------------------------------------------

def test_scan_one_sslyze_has_tryfinally_del_and_gc_collect():
    """
    Source-shape guard: `_scan_one_sslyze` must contain the BLOCK-01
    cleanup pattern (try/finally with `del scanner` and `gc.collect()`).
    CPython refcounting often masks the leak in pure-Python tests, so
    the behavioral tests above can falsely pass after a regression.
    This structural assertion locks the fix in place.
    """
    src = inspect.getsource(tls_scanner._scan_one_sslyze)
    assert "finally:" in src, "missing `finally:` in _scan_one_sslyze (BLOCK-01)"
    assert re.search(r"\bdel\s+scanner\b", src), (
        "missing `del scanner` in _scan_one_sslyze (BLOCK-01 cleanup)"
    )
    assert re.search(r"gc\.collect\s*\(\s*\)", src), (
        "missing `gc.collect()` in _scan_one_sslyze (BLOCK-01 cleanup)"
    )
