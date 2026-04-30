"""Phase 41 ROBUST-01..03 acceptance tests.

Stubs created in Wave 0; turned green by Plan 04 (D-12 advisory + D-14
BaseException wrapper) and Plan 03 (D-08 per-scanner timeout reads).

Each stub is marked with pytest xfail (strict=False) so it is visible
in the suite but non-blocking until the relevant plan lands the wiring.
When the wiring is in place, remove the xfail marker and implement the
test body — the existing ``raise NotImplementedError`` will be replaced
with real assertions.
"""
from __future__ import annotations

import pytest


@pytest.mark.xfail(reason="Plan 04 wires D-12 advisory", strict=False)
def test_missing_extra_advisory_stderr(capsys: pytest.CaptureFixture[str]) -> None:
    """ROBUST-01 / D-12: stderr advisory format
    ``[advisory] scanner=<name> extra=<group> not installed -- run \
`pip install quirk[<group>]` to enable``.
    """
    raise NotImplementedError("Plan 04")


@pytest.mark.xfail(reason="Plan 04 wires D-13 exit code", strict=False)
def test_missing_extra_exit_code_zero() -> None:
    """ROBUST-01 / D-13: missing optional extra -> exit 0 (scan completes)."""
    raise NotImplementedError("Plan 04")


@pytest.mark.xfail(reason="Plan 03 wires per-scanner timeout reads from cfg.scan.timeouts", strict=False)
def test_per_scanner_timeout_respected_tls() -> None:
    """ROBUST-02: TLS scanner reads cfg.scan.timeouts.tls_seconds, not cfg.scan.timeout_seconds."""
    raise NotImplementedError("Plan 03")


@pytest.mark.xfail(reason="Plan 04 wires D-14 BaseException wrapper", strict=False)
def test_unexpected_exception_captured_in_scan_errors() -> None:
    """ROBUST-03 / D-14: unexpected exception -> scan_errors[] entry with
    category='exception', scan continues.
    """
    raise NotImplementedError("Plan 04")


@pytest.mark.xfail(reason="Plan 04 wires D-14 BaseException wrapper", strict=False)
def test_keyboard_interrupt_propagates() -> None:
    """D-14: KeyboardInterrupt and SystemExit are NOT swallowed by the
    BaseException wrapper.
    """
    raise NotImplementedError("Plan 04")
