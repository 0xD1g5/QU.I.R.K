"""Tests for quirk/siem/dispatcher.py — Phase 103 SIEM-01/02.

Covers:
  - export_findings: one send per finding, one audit row per batch, ok/failed status
  - export_after_scan_hook: fires when export_after_scan=True, no-op otherwise,
    never raises even when config is None or SIEM unreachable
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from quirk.db import init_db, get_session
from quirk.models import IntegrationDelivery, ScheduledScan, ScheduledRun


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_db(tmp_path):
    """Create a test SQLite database and return its path."""
    db_path = str(tmp_path / "quirk_test.db")
    init_db(db_path)
    return db_path


def _make_run(db_path, scan_output_path=None):
    """Insert a ScheduledScan + ScheduledRun pair and return the run row."""
    scan = ScheduledScan(
        name="test-scan",
        cron_expr="* * * * *",
        target="127.0.0.1",
        profile=None,
        enabled=True,
        last_run_at=None,
        created_at=datetime.utcnow(),
    )
    with get_session(db_path) as db:
        db.add(scan)
        db.flush()
        scan_id = scan.id
        run = ScheduledRun(
            schedule_id=scan_id,
            dispatched_at=datetime.utcnow(),
            status="completed",
            scan_output_path=scan_output_path,
            scan_id=None,
        )
        db.add(run)
        db.commit()
        run_id = run.id

    with get_session(db_path) as db:
        r = db.query(ScheduledRun).filter_by(id=run_id).one()
        s = db.query(ScheduledScan).filter_by(id=scan_id).one()
        return r, s


def _make_findings(tmp_path, count=3):
    """Write a findings-*.json file and return (path, findings_list)."""
    findings = [
        {
            "severity": "HIGH",
            "host": f"host{i}.example.com",
            "port": 443,
            "title": f"Finding {i}",
            "description": f"Description {i}",
            "recommendation": f"Recommendation {i}",
        }
        for i in range(count)
    ]
    out = tmp_path / "findings-20260101-000000.json"
    out.write_text(json.dumps(findings))
    return str(out), findings


def _make_siem_cfg(host="127.0.0.1", port=514, export_after_scan=True):
    """Build a SiemCfg fixture."""
    from quirk.siem.config import SiemCfg
    return SiemCfg(
        host=host,
        port=port,
        protocol="udp",
        export_after_scan=export_after_scan,
        timeout_seconds=5,
    )


# ---------------------------------------------------------------------------
# export_findings tests
# ---------------------------------------------------------------------------


def test_export_one_event_per_finding(tmp_path, monkeypatch):
    """SIEM-02: export_findings calls send_syslog_raw once per finding."""
    from quirk.siem import dispatcher

    calls = []

    def _fake_send(cef_msg, host, port, protocol="udp", timeout=5):
        calls.append(cef_msg)

    monkeypatch.setattr(dispatcher, "_send_raw", _fake_send)

    db_path = _make_db(tmp_path)
    cfg = _make_siem_cfg()
    findings = [
        {"severity": "HIGH", "host": f"h{i}", "port": 443, "title": f"F{i}"}
        for i in range(3)
    ]

    with get_session(db_path) as db:
        count = dispatcher.export_findings(findings, cfg, db, scan_id="scan-001")

    assert count == 3
    assert len(calls) == 3


def test_audit_row_written(tmp_path, monkeypatch):
    """SIEM-02 / T-103-09: one IntegrationDelivery row with destination='siem',
    finding_hash=None, status='ok' is written after a successful export."""
    from quirk.siem import dispatcher

    monkeypatch.setattr(dispatcher, "_send_raw", lambda *a, **kw: None)

    db_path = _make_db(tmp_path)
    cfg = _make_siem_cfg()
    findings = [{"severity": "LOW", "host": "h1", "port": 514, "title": "T1"}]

    with get_session(db_path) as db:
        dispatcher.export_findings(findings, cfg, db, scan_id="scan-002")

    with get_session(db_path) as db:
        rows = db.query(IntegrationDelivery).filter_by(destination="siem").all()

    assert len(rows) == 1
    row = rows[0]
    assert row.scan_id == "scan-002"
    assert row.finding_hash is None
    assert row.status == "ok"
    assert row.attempted_at is not None


def test_unreachable_endpoint(tmp_path, monkeypatch):
    """T-103-07: OSError from send → status='failed' row written, no exception raised."""
    from quirk.siem import dispatcher

    def _fail_send(cef_msg, host, port, protocol="udp", timeout=5):
        raise OSError("Connection refused")

    monkeypatch.setattr(dispatcher, "_send_raw", _fail_send)

    db_path = _make_db(tmp_path)
    cfg = _make_siem_cfg()
    findings = [{"severity": "HIGH", "host": "dead.host", "port": 514, "title": "F"}]

    with get_session(db_path) as db:
        # Must not raise
        count = dispatcher.export_findings(findings, cfg, db, scan_id="scan-003")

    assert count == 0  # no successes

    with get_session(db_path) as db:
        rows = db.query(IntegrationDelivery).filter_by(destination="siem").all()

    assert len(rows) == 1
    assert rows[0].status == "failed"
    assert rows[0].error_summary is not None
    assert "Connection refused" in rows[0].error_summary or "OSError" in rows[0].error_summary or rows[0].error_summary != ""


def test_after_scan_hook_fires(tmp_path, monkeypatch):
    """SIEM-01: hook sends events when export_after_scan=True and findings file exists."""
    from quirk.siem import dispatcher

    calls = []
    monkeypatch.setattr(dispatcher, "_send_raw", lambda *a, **kw: calls.append(a))

    db_path = _make_db(tmp_path)
    cfg = _make_siem_cfg(export_after_scan=True)
    monkeypatch.setattr(dispatcher, "load_siem_config", lambda: cfg)

    # Write a findings JSON into tmp_path
    findings_path, findings = _make_findings(tmp_path, count=2)

    run_stub = MagicMock()
    run_stub.scan_output_path = str(tmp_path)
    run_stub.scan_id = "scan-hook-01"
    schedule_stub = MagicMock()

    with get_session(db_path) as db:
        dispatcher.export_after_scan_hook(run=run_stub, schedule=schedule_stub, db=db)

    assert len(calls) == 2


def test_after_scan_hook_noop(tmp_path, monkeypatch):
    """SIEM-01: hook is a no-op when export_after_scan=False."""
    from quirk.siem import dispatcher

    calls = []
    monkeypatch.setattr(dispatcher, "_send_raw", lambda *a, **kw: calls.append(a))

    db_path = _make_db(tmp_path)
    cfg = _make_siem_cfg(export_after_scan=False)
    monkeypatch.setattr(dispatcher, "load_siem_config", lambda: cfg)

    findings_path, _ = _make_findings(tmp_path, count=2)

    run_stub = MagicMock()
    run_stub.scan_output_path = str(tmp_path)
    run_stub.scan_id = "scan-hook-02"
    schedule_stub = MagicMock()

    with get_session(db_path) as db:
        dispatcher.export_after_scan_hook(run=run_stub, schedule=schedule_stub, db=db)

    assert calls == []

    # Also verify no IntegrationDelivery rows written
    with get_session(db_path) as db:
        rows = db.query(IntegrationDelivery).filter_by(destination="siem").all()
    assert rows == []


def test_hook_never_raises_on_bad_config(tmp_path, monkeypatch):
    """T-103-07: hook is a clean no-op when load_siem_config returns None."""
    from quirk.siem import dispatcher

    calls = []
    monkeypatch.setattr(dispatcher, "_send_raw", lambda *a, **kw: calls.append(a))
    monkeypatch.setattr(dispatcher, "load_siem_config", lambda: None)

    db_path = _make_db(tmp_path)
    run_stub = MagicMock()
    run_stub.scan_output_path = str(tmp_path)
    run_stub.scan_id = "scan-hook-03"
    schedule_stub = MagicMock()

    with get_session(db_path) as db:
        # Must not raise
        dispatcher.export_after_scan_hook(run=run_stub, schedule=schedule_stub, db=db)

    assert calls == []
