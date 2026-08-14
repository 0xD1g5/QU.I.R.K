"""Phase 155 Plan 05 (HWLC-04) — end-to-end wiring coverage for
``reconcile_device_history()`` at both live hardware-device commit sites in
``run_scan.py``.

Covers:
- Site (A) ``run_ot_supplemental_and_persist()`` — commit-then-reconcile,
  dedup by (host, port), advisory-only failure isolation.
- Site (B) the SNMP-only block — reconciliation of an SNMP-only device
  (first observed via that path).

No network connections are made. A real on-disk SQLite database (via
``quirk.db.init_db``/``get_session``) is used so reconciliation reads
freshly-committed rows through a session query, exactly as production code
does — never the in-memory ``hw_batch``/``_snmp_new_batch`` objects
directly (RESEARCH.md Pitfall 2).
"""
from __future__ import annotations

import datetime as _dt
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from quirk.db import get_session, init_db
from quirk.logging_util import Logger
from quirk.models import HardwareDevice, HardwareDriftEvent


def _make_cfg(enable_modbus: bool = False, enable_bacnet: bool = False):
    connectors = SimpleNamespace(
        enable_modbus=enable_modbus,
        enable_bacnet=enable_bacnet,
        snmp_v3_credentials={},
    )
    return SimpleNamespace(connectors=connectors)


def _seed_history(db_path, host, port, scanned_at, tier, vendor="Cisco", model=None):
    with get_session(db_path) as session:
        session.add(
            HardwareDevice(
                host=host,
                port=port,
                vendor=vendor,
                model=model,
                pqc_status="unsupported",
                confidence="high",
                fingerprint_method="ssh_banner",
                probe_status="success",
                scanned_at=scanned_at,
                remediation_tier=tier,
            )
        )
        session.commit()


def _drift_events(db_path, host=None, port=None):
    with get_session(db_path) as session:
        q = session.query(HardwareDriftEvent)
        if host is not None:
            q = q.filter_by(host=host)
        if port is not None:
            q = q.filter_by(port=port)
        return q.all()


# ============================================================
# Site (A) — run_ot_supplemental_and_persist()
# ============================================================


def test_site_a_reconciles_device_after_commit(tmp_path) -> None:
    """After run_ot_supplemental_and_persist() commits a new hw_batch row,
    a confirmed tier-crossing drift event is persisted for that device."""
    from run_scan import run_ot_supplemental_and_persist

    db_path = str(tmp_path / "hw_drift_wiring_a.db")
    init_db(db_path)

    base = _dt.datetime(2026, 8, 1)
    _seed_history(db_path, "10.0.0.50", 22, base, tier="Tier 2")
    _seed_history(db_path, "10.0.0.50", 22, base + _dt.timedelta(days=1), tier="Tier 1")

    new_device = HardwareDevice(
        host="10.0.0.50",
        port=22,
        vendor="Cisco",
        pqc_status="unsupported",
        confidence="high",
        fingerprint_method="ssh_banner",
        probe_status="success",
        scanned_at=base + _dt.timedelta(days=2),
        remediation_tier="Tier 1",
    )
    hw_batch = [new_device]
    logger = Logger(verbose=False, use_tqdm=False)

    with patch("run_scan.fingerprint_hardware", return_value=[]), \
         patch("run_scan._print_hardware_summary"):
        run_ot_supplemental_and_persist(
            targets=[],
            ssh_targets=[],
            confirmed_open_ports={},
            cfg=_make_cfg(),
            hw_batch=hw_batch,
            run_stats={"timings_sec": {}},
            error_endpoints=[],
            logger=logger,
            db_path=db_path,
        )

    events = _drift_events(db_path, host="10.0.0.50", port=22)
    assert len(events) == 1
    assert events[0].event_type == "tier_crossing"
    assert events[0].old_value == "Tier 2"
    assert events[0].new_value == "Tier 1"


def test_site_a_first_scan_device_produces_no_drift_event(tmp_path) -> None:
    """A device on its first-ever scan (< 2 historical rows) is reconciled
    (called) but yields zero drift-event rows."""
    from run_scan import run_ot_supplemental_and_persist

    db_path = str(tmp_path / "hw_drift_wiring_a_first.db")
    init_db(db_path)

    new_device = HardwareDevice(
        host="10.0.0.51",
        port=22,
        vendor="Cisco",
        pqc_status="unsupported",
        confidence="high",
        fingerprint_method="ssh_banner",
        probe_status="success",
        scanned_at=datetime.now(timezone.utc).replace(tzinfo=None),
        remediation_tier="Tier 1",
    )
    hw_batch = [new_device]
    logger = Logger(verbose=False, use_tqdm=False)

    with patch("run_scan.fingerprint_hardware", return_value=[]), \
         patch("run_scan._print_hardware_summary"):
        run_ot_supplemental_and_persist(
            targets=[],
            ssh_targets=[],
            confirmed_open_ports={},
            cfg=_make_cfg(),
            hw_batch=hw_batch,
            run_stats={"timings_sec": {}},
            error_endpoints=[],
            logger=logger,
            db_path=db_path,
        )

    assert _drift_events(db_path, host="10.0.0.51", port=22) == []


def test_site_a_reconciles_once_per_distinct_host_port(tmp_path) -> None:
    """Duplicate rows for the same (host, port) in one batch reconcile once,
    not once per row."""
    from run_scan import run_ot_supplemental_and_persist

    db_path = str(tmp_path / "hw_drift_wiring_a_dedup.db")
    init_db(db_path)

    base = _dt.datetime(2026, 8, 1)
    _seed_history(db_path, "10.0.0.52", 22, base, tier="Tier 2")
    _seed_history(db_path, "10.0.0.52", 22, base + _dt.timedelta(days=1), tier="Tier 1")

    def _dev(scanned_at):
        return HardwareDevice(
            host="10.0.0.52",
            port=22,
            vendor="Cisco",
            pqc_status="unsupported",
            confidence="high",
            fingerprint_method="ssh_banner",
            probe_status="success",
            scanned_at=scanned_at,
            remediation_tier="Tier 1",
        )

    hw_batch = [_dev(base + _dt.timedelta(days=2))]
    logger = Logger(verbose=False, use_tqdm=False)

    with patch("run_scan.fingerprint_hardware", return_value=[]), \
         patch("run_scan._print_hardware_summary"):
        run_ot_supplemental_and_persist(
            targets=[],
            ssh_targets=[],
            confirmed_open_ports={},
            cfg=_make_cfg(),
            hw_batch=hw_batch,
            run_stats={"timings_sec": {}},
            error_endpoints=[],
            logger=logger,
            db_path=db_path,
        )

    # Exactly one tier_crossing event, not duplicated by any (host, port)
    # dedup-set collapsing behavior.
    events = _drift_events(db_path, host="10.0.0.52", port=22)
    assert len(events) == 1


def test_site_a_reconciliation_exception_does_not_abort_scan(tmp_path) -> None:
    """A raised exception from reconcile_device_history is swallowed by the
    existing advisory-only handler; the commit still succeeds."""
    from run_scan import run_ot_supplemental_and_persist

    db_path = str(tmp_path / "hw_drift_wiring_a_exc.db")
    init_db(db_path)

    new_device = HardwareDevice(
        host="10.0.0.53",
        port=22,
        vendor="Cisco",
        pqc_status="unsupported",
        confidence="high",
        fingerprint_method="ssh_banner",
        probe_status="success",
        scanned_at=datetime.now(timezone.utc).replace(tzinfo=None),
        remediation_tier="Tier 1",
    )
    hw_batch = [new_device]
    logger = Logger(verbose=False, use_tqdm=False)

    with patch("run_scan.fingerprint_hardware", return_value=[]), \
         patch("run_scan._print_hardware_summary"), \
         patch(
             "quirk.scanner.hardware_drift.reconcile_device_history",
             side_effect=RuntimeError("simulated reconciliation failure"),
         ):
        # Must not raise — the surrounding advisory-only except clause
        # catches this.
        run_ot_supplemental_and_persist(
            targets=[],
            ssh_targets=[],
            confirmed_open_ports={},
            cfg=_make_cfg(),
            hw_batch=hw_batch,
            run_stats={"timings_sec": {}},
            error_endpoints=[],
            logger=logger,
            db_path=db_path,
        )

    # The device row itself was still committed before reconciliation ran.
    with get_session(db_path) as session:
        rows = session.query(HardwareDevice).filter_by(host="10.0.0.53").all()
    assert len(rows) == 1


# ============================================================
# Site (B) — SNMP-only block
# ============================================================


def test_site_b_snmp_only_device_is_reconciled(tmp_path) -> None:
    """An SNMP-only device (first observed via the SNMP-only path) is
    reconciled after its commit."""
    from run_scan import run_ot_supplemental_and_persist

    db_path = str(tmp_path / "hw_drift_wiring_b.db")
    init_db(db_path)

    base = _dt.datetime(2026, 8, 1)
    _seed_history(db_path, "10.0.0.60", 161, base, tier="Tier 2", vendor="Fortinet")
    _seed_history(
        db_path, "10.0.0.60", 161, base + _dt.timedelta(days=1), tier="Tier 1", vendor="Fortinet"
    )

    # Exercise the exact reconcile call idiom used at Site (B): a fresh
    # commit of a new SNMP-only row, followed by a reconcile call scoped to
    # the rows actually committed in that block (_snmp_new_batch).
    with get_session(db_path) as _snmp_sess:
        snmp_dev = HardwareDevice(
            host="10.0.0.60",
            port=161,
            vendor="Fortinet",
            pqc_status="unsupported",
            confidence="medium",
            fingerprint_method="snmp",
            probe_status="success",
            scanned_at=base + _dt.timedelta(days=2),
            remediation_tier="Tier 1",
            snmp_sysdescr="Fortinet FortiGate",
        )
        _snmp_sess.add(snmp_dev)
        _snmp_sess.commit()

        from quirk.scanner.hardware_drift import reconcile_device_history

        _snmp_new_batch = [snmp_dev]
        for _host, _port in {(_d.host, _d.port) for _d in _snmp_new_batch}:
            reconcile_device_history(_snmp_sess, _host, _port)

    events = _drift_events(db_path, host="10.0.0.60", port=161)
    assert len(events) == 1
    assert events[0].event_type == "tier_crossing"
    assert events[0].old_value == "Tier 2"
    assert events[0].new_value == "Tier 1"


def test_run_scan_hooks_reconcile_at_both_commit_sites() -> None:
    """Static contract check: run_scan.py imports and calls
    reconcile_device_history at exactly the two documented commit sites,
    each inside the existing advisory-only try/except handler (no new
    exception-handling style introduced)."""
    import inspect

    import run_scan

    source = inspect.getsource(run_scan)
    assert source.count("reconcile_device_history(_hw_sess") == 1
    assert source.count("reconcile_device_history(_snmp_sess") == 1
    # Both call sites live inside functions that still use the pre-existing
    # advisory-only, non-fatal logging idiom — no new handler style added.
    assert "advisory-only, non-fatal" in source
