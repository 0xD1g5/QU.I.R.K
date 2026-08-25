"""Phase 161 Plan 04 (HWLC-14) — the notification trigger inside
``persist_and_reconcile()``.

Plan 161-01 built the notification consumer; without a caller it is
unreachable — the "feature built, never reachable" failure shape recorded for
Phase 141. These tests prove the hook fires, that it is correctly filtered, and
that it can never abort a scan, a sensor push, or an air-gap import.

The hook sits inside ``persist_and_reconcile()`` rather than at each of its four
call sites (run_scan.py 449/550/2391 and console_cmd.py 677) so no scan path can
silently skip notifications. The helper imports the dispatcher locally at call
time, so patching the attribute on ``quirk.notify.dispatcher`` is sufficient —
there is deliberately no name to patch on ``hardware_drift``.

No network connections are made.
"""
from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from quirk.db import get_session, init_db
from quirk.models import (
    HardwareDevice,
    HardwareDriftEvent,
    IntegrationDelivery,
    VendorPqcTrendEvent,
)
from quirk.scanner.hardware_drift import persist_and_reconcile


def _make_device(host="10.0.0.5", port=22, vendor="Cisco"):
    return HardwareDevice(
        host=host,
        port=port,
        vendor=vendor,
        pqc_status="unsupported",
        confidence="high",
        fingerprint_method="ssh_banner",
        probe_status="success",
        scanned_at=datetime(2026, 8, 20, 12, 0, 0),
        remediation_tier="Tier 2",
    )


def _drift_event(host="10.0.0.5", port=22):
    return HardwareDriftEvent(
        host=host,
        port=port,
        event_type="tier_crossing",
        old_value="Tier 1",
        new_value="Tier 2",
        detected_at=datetime(2026, 8, 20, 12, 0, 0),
    )


def _trend_event(vendor="Cisco"):
    return VendorPqcTrendEvent(
        vendor=vendor,
        event_type="vendor_pqc_trend",
        old_value="0/3",
        new_value="1/3",
        detected_at=datetime(2026, 8, 20, 12, 0, 0),
    )


def _run(tmp_path, *, drift=None, trend=None, spy=None):
    """Persist one device batch with the reconcilers stubbed to a fixed outcome."""
    db_path = str(tmp_path / "hook.db")
    init_db(db_path)
    devices = [_make_device()]

    with get_session(db_path) as session, patch(
        "quirk.scanner.hardware_drift.reconcile_device_history",
        return_value=list(drift or []),
    ), patch(
        "quirk.scanner.hardware_drift.reconcile_vendor_pqc_trend",
        return_value=list(trend or []),
    ), patch(
        "quirk.notify.dispatcher.dispatch_hardware_lifecycle_notifications",
        spy if spy is not None else MagicMock(),
    ):
        return persist_and_reconcile(session, devices, cfg=None, logger=None)


def test_hook_calls_dispatcher_once_with_the_drift_events(tmp_path):
    """A batch producing one HardwareDriftEvent dispatches exactly once."""
    spy = MagicMock()
    _run(tmp_path, drift=[_drift_event()], spy=spy)

    assert spy.call_count == 1, (
        f"HWLC-14: dispatcher called {spy.call_count} times — the trigger is "
        f"unreachable or fires more than once per reconcile"
    )
    dispatched = spy.call_args[0][0]
    assert len(dispatched) == 1


def test_vendor_trend_events_never_reach_the_dispatcher(tmp_path):
    """VendorPqcTrendEvent rows are outside HWLC-14's trigger (D-02)."""
    spy = MagicMock()
    _run(tmp_path, drift=[_drift_event()], trend=[_trend_event()], spy=spy)

    assert spy.call_count == 1
    dispatched = spy.call_args[0][0]
    # Assert over EVERY element, not just the first.
    assert all(isinstance(e, HardwareDriftEvent) for e in dispatched), (
        f"HWLC-14/D-02: non-drift rows reached the dispatcher — "
        f"{[type(e).__name__ for e in dispatched]}"
    )
    assert not any(isinstance(e, VendorPqcTrendEvent) for e in dispatched)


def test_no_drift_events_means_no_dispatch(tmp_path):
    """A batch yielding only vendor-trend rows must not call the dispatcher."""
    spy = MagicMock()
    _run(tmp_path, drift=[], trend=[_trend_event()], spy=spy)

    assert spy.call_count == 0, (
        "HWLC-14: dispatcher invoked with no qualifying drift events"
    )


def test_raising_dispatcher_cannot_perturb_the_return_value(tmp_path):
    """Delivery is advisory-only: a raising dispatcher changes nothing."""
    ok_spy = MagicMock()
    purged_ok, events_ok = _run(tmp_path, drift=[_drift_event()], spy=ok_spy)

    boom = MagicMock(side_effect=RuntimeError("notification layer down"))
    purged_bad, events_bad = _run(tmp_path, drift=[_drift_event()], spy=boom)

    assert boom.call_count == 1, "the raising spy was never reached"
    assert purged_bad == purged_ok, (
        f"HWLC-14: purge count changed when the dispatcher raised "
        f"({purged_bad} vs {purged_ok})"
    )
    assert len(events_bad) == len(events_ok), (
        f"HWLC-14: event list changed when the dispatcher raised "
        f"({len(events_bad)} vs {len(events_ok)})"
    )


def test_import_error_on_the_dispatcher_is_non_fatal(tmp_path):
    """An unavailable notification layer must not abort the caller."""
    db_path = str(tmp_path / "hook_import.db")
    init_db(db_path)

    real_import = __builtins__["__import__"] if isinstance(__builtins__, dict) else __builtins__.__import__

    def _blocked(name, *args, **kwargs):
        if name == "quirk.notify.dispatcher":
            raise ImportError("notification extra not installed")
        return real_import(name, *args, **kwargs)

    with get_session(db_path) as session, patch(
        "quirk.scanner.hardware_drift.reconcile_device_history",
        return_value=[_drift_event()],
    ), patch(
        "quirk.scanner.hardware_drift.reconcile_vendor_pqc_trend", return_value=[]
    ), patch("builtins.__import__", side_effect=_blocked):
        purged, events = persist_and_reconcile(
            session, [_make_device()], cfg=None, logger=None
        )

    assert len(events) == 1, (
        "HWLC-14: an ImportError on the dispatcher perturbed the return value"
    )


def test_config_off_writes_no_delivery_rows(tmp_path):
    """With notify_on_hardware_lifecycle unset, nothing is delivered or audited."""
    db_path = str(tmp_path / "hook_cfg.db")
    init_db(db_path)

    with get_session(db_path) as session, patch(
        "quirk.scanner.hardware_drift.reconcile_device_history",
        return_value=[_drift_event()],
    ), patch(
        "quirk.scanner.hardware_drift.reconcile_vendor_pqc_trend", return_value=[]
    ):
        persist_and_reconcile(session, [_make_device()], cfg=None, logger=None)

    with get_session(db_path) as session:
        assert session.query(IntegrationDelivery).count() == 0, (
            "HWLC-14: delivery rows written while the global opt-in is unset"
        )
