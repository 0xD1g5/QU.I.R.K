"""Phase 173 Plan 02 (SCOPE-02) — first-ever coverage of the `timings_sec` absent/present contract.

`_phase_timer.__exit__` used to write `run_stats["timings_sec"][name]` unconditionally, so every
gated scanner phase (dnssec, saml, kerberos, smime, aws, azure, gcp, s3, blob, k8s, adcs,
codesign, vault, email, broker, and — per the Task 1 inventory — jwt/container/source/db) recorded
a phantom nonzero duration even when its top-of-function guard fired and no real work happened.

D-02 fixed this at the generic `_phase_timer`/`_wrapped_phase` mechanism: a module-level
`_PHASE_SKIPPED` sentinel, returned by a guard clause and checked by IDENTITY (never truthiness),
tells the timer to omit the key rather than write a phantom value. This file drives `_wrapped_phase`
directly, in-process, with stub `fn` callables — no external process is spawned, no CLI, no scan I/O.

D-04 requires coverage of at least one non-broker phase, since the fix is generic, not
broker-specific. `smime_scanning` is used throughout as that required non-broker phase.

The inversion trap this guards against: if the sentinel were checked by truthiness instead of
identity, a phase that legitimately ran and returned `[]` (found nothing) would ALSO have its
timing key dropped — silently erasing real evidence that a scan phase executed. The
"ran_but_empty" tests below are the guard against shipping the fix backwards.
"""
import logging

import pytest

from run_scan import _PHASE_SKIPPED, _wrapped_phase


class _StubLogger:
    """Minimal stand-in for run_scan's logger — only .error() is used on the exception path."""

    def __init__(self):
        self.errors = []

    def error(self, msg):
        self.errors.append(msg)


def _fresh_run_stats():
    return {"timings_sec": {}}


# ---------------------------------------------------------------------------
# Absent-key contract: phase did NOT really run
# ---------------------------------------------------------------------------

def test_skipped_broker_phase_omits_timing_key():
    """Broker's guard clause returning _PHASE_SKIPPED must leave no timings_sec key.

    Fails if `_phase_timer.__exit__` reverts to writing unconditionally, or if
    `_wrapped_phase` checks truthiness instead of `is _PHASE_SKIPPED`.
    """
    run_stats = _fresh_run_stats()
    error_endpoints = []

    def _disabled_broker():
        return _PHASE_SKIPPED

    result = _wrapped_phase(
        run_stats, "broker_scanning", "broker_scanner",
        _disabled_broker, error_endpoints, _StubLogger(),
    )

    assert result == []
    assert "broker_scanning" not in run_stats["timings_sec"]


def test_skipped_smime_phase_omits_timing_key():
    """The required D-04 non-broker phase: smime's guard must also omit its key.

    Fails if `_phase_timer.__exit__` reverts to writing unconditionally, or if
    `_wrapped_phase` checks truthiness instead of `is _PHASE_SKIPPED`. Proves the
    fix is generic to the mechanism, not a broker-only patch.
    """
    run_stats = _fresh_run_stats()
    error_endpoints = []

    def _disabled_smime():
        return _PHASE_SKIPPED

    result = _wrapped_phase(
        run_stats, "smime_scanning", "smime_scanner",
        _disabled_smime, error_endpoints, _StubLogger(),
    )

    assert result == []
    assert "smime_scanning" not in run_stats["timings_sec"]


# ---------------------------------------------------------------------------
# Present-key contract: phase DID run, even if it found nothing (the inversion guard)
# ---------------------------------------------------------------------------

def test_ran_but_empty_smime_phase_keeps_timing_key():
    """smime ran for real and found zero endpoints — the key must still be present.

    Fails if the sentinel check is broadened to a falsy-value check (e.g. `if not result`
    instead of `if result is _PHASE_SKIPPED`), which would wrongly drop the timing of a
    phase that ran and found nothing — the exact inversion this contract guards against.
    """
    run_stats = _fresh_run_stats()
    error_endpoints = []

    def _ran_smime_found_nothing():
        return []  # real run, zero endpoints — NOT the sentinel

    result = _wrapped_phase(
        run_stats, "smime_scanning", "smime_scanner",
        _ran_smime_found_nothing, error_endpoints, _StubLogger(),
    )

    assert result == []
    assert "smime_scanning" in run_stats["timings_sec"]
    assert isinstance(run_stats["timings_sec"]["smime_scanning"], float)
    assert run_stats["timings_sec"]["smime_scanning"] >= 0


def test_ran_broker_three_tuple_round_trips_and_keeps_timing_key():
    """broker's real-run 3-tuple return shape must round-trip unchanged, key present.

    Fails if the sentinel-translation logic in `_wrapped_phase` accidentally intercepts
    or mutates non-sentinel return values (e.g. by checking truthiness and treating an
    empty-list-containing tuple as a skip), or if the timing key stops being written for
    a real run.
    """
    run_stats = _fresh_run_stats()
    error_endpoints = []
    populated = (["kafka-ep"], ["rabbit-ep"], ["redis-ep"])

    def _ran_broker():
        return populated

    result = _wrapped_phase(
        run_stats, "broker_scanning", "broker_scanner",
        _ran_broker, error_endpoints, _StubLogger(),
    )

    assert result == populated
    assert isinstance(result, tuple) and len(result) == 3
    assert "broker_scanning" in run_stats["timings_sec"]


# ---------------------------------------------------------------------------
# Exception path: D-14 contract must be untouched by the sentinel work
# ---------------------------------------------------------------------------

def test_exception_raising_phase_keeps_timing_key_and_records_error_row():
    """An exception inside a phase must still be captured, key present, error row recorded.

    Fails if introducing the sentinel check broke the existing D-14 BaseException
    handling — e.g. if the `with` block restructuring accidentally left the timer's
    __exit__ un-invoked on the exception path, or if `error_endpoints` stopped
    receiving the `scan_error_category="exception"` row.
    """
    run_stats = _fresh_run_stats()
    error_endpoints = []
    logger = _StubLogger()

    def _boom():
        raise ValueError("simulated scanner failure")

    result = _wrapped_phase(
        run_stats, "aws_scanning", "aws_connector",
        _boom, error_endpoints, logger,
    )

    assert result == []
    assert "aws_scanning" in run_stats["timings_sec"]
    assert len(error_endpoints) == 1
    assert error_endpoints[0].scan_error_category == "exception"
    assert error_endpoints[0].host == "aws_connector"
    assert len(logger.errors) == 1


def test_keyboard_interrupt_still_reraised():
    """KeyboardInterrupt must still propagate — D-14's user-abort contract is unchanged.

    Fails if the sentinel restructuring of the `with` block accidentally widened the
    `except (KeyboardInterrupt, SystemExit): raise` clause's scope or removed it.
    """
    run_stats = _fresh_run_stats()
    error_endpoints = []

    def _abort():
        raise KeyboardInterrupt()

    with pytest.raises(KeyboardInterrupt):
        _wrapped_phase(
            run_stats, "aws_scanning", "aws_connector",
            _abort, error_endpoints, _StubLogger(),
        )
