"""Phase 237 COUNT-04 (D-05): a null error_category must not drop later entries.

Writer: run_scan._collect_stage_partial_failures coalesces a missing category.
Reader: _load_partial_failures parses each entry in its own try and coalesces
explicit nulls, so one bad entry skips only itself.
"""
from __future__ import annotations

import json
from datetime import datetime

from quirk.cli.job_progress import write_scan_checkpoint
from quirk.db import init_db
from quirk.models import CryptoEndpoint, ScanCheckpoint
from quirk.scanner.target_outcome import OUTCOME_UNREACHABLE, TargetOutcomes

RUN_ID = "2026-11-16T00:00:00+00:00"


def _session(db_path):
    from sqlalchemy.orm import sessionmaker

    engine = init_db(str(db_path))
    return sessionmaker(bind=engine)()


def _valid(scanner="vault_scanner", category="targets_unreachable"):
    return {
        "scanner": scanner,
        "error_category": category,
        "error_message": "boom",
        "endpoint_count": 0,
    }


def _seed_raw_summary(db_path, payload):
    init_db(str(db_path))
    write_scan_checkpoint(
        str(db_path), RUN_ID, "inventory", "completed",
        partial_failure=True, error_summary=payload,
    )


def _load(db_path):
    from quirk.dashboard.api.routes.scan import _load_partial_failures

    db = _session(db_path)
    try:
        return _load_partial_failures(db, RUN_ID)
    finally:
        db.close()


def test_null_category_entry_does_not_drop_later_entries(tmp_path):
    db_path = tmp_path / "q.db"
    null_entry = _valid("db_scanner", None)
    _seed_raw_summary(db_path, [_valid("a"), null_entry, _valid("c")])
    got = _load(db_path)
    assert [e.scanner for e in got] == ["a", "db_scanner", "c"]
    assert got[1].error_category == "exception"


def test_malformed_entry_skips_only_itself(tmp_path):
    db_path = tmp_path / "q.db"
    init_db(str(db_path))
    db = _session(db_path)
    db.add(ScanCheckpoint(
        scan_run_id=RUN_ID, stage="inventory", status="completed",
        partial_failure=True, completed_at=datetime(2026, 11, 16),
        error_summary=json.dumps([_valid("a"), "not-a-dict", _valid("c")]),
    ))
    db.commit()
    db.close()
    got = _load(db_path)
    assert [e.scanner for e in got] == ["a", "c"]


def test_writer_coalesces_null_category():
    import run_scan

    ep = CryptoEndpoint(host="db1", port=0, protocol="ERROR", scan_error="x")
    assert ep.scan_error_category is None
    stats: dict = {}
    out = run_scan._collect_stage_partial_failures(stats, "inventory", [ep], 0)
    assert out[0]["error_category"] == "exception"
    assert stats["partial_failures"][0]["error_category"] == "exception"


def test_db_then_vault_ordering_in_process(tmp_path):
    """Real classifier -> collector -> checkpoint -> loader, db before vault."""
    import run_scan

    db_path = tmp_path / "q.db"
    init_db(str(db_path))
    error_endpoints: list = []
    rec = run_scan._PhaseRecorder()

    db_out = TargetOutcomes(["db1:5432"])
    for t in db_out.expected:
        db_out.record(t, OUTCOME_UNREACHABLE, "timed out")
    inband = CryptoEndpoint(
        host="db1", port=5432, protocol="ERROR", scan_error="connection refused",
    )
    assert inband.scan_error_category is None
    run_scan._classify_connector_outcomes(
        "db_scanner", db_out, [inband], error_endpoints, rec,
    )

    vault_out = TargetOutcomes(["vault1:8200"])
    for t in vault_out.expected:
        vault_out.record(t, OUTCOME_UNREACHABLE, "timed out")
    run_scan._classify_connector_outcomes(
        "vault_scanner", vault_out, [], error_endpoints, rec,
    )
    assert any(e.host == "db1" and e.scan_error_category is None for e in error_endpoints)

    stats: dict = {}
    entries = run_scan._collect_stage_partial_failures(stats, "inventory", error_endpoints, 0)
    write_scan_checkpoint(
        str(db_path), RUN_ID, "inventory", "completed",
        partial_failure=True, error_summary=entries,
    )
    got = _load(db_path)
    assert len(got) == len(error_endpoints) >= 3
    scanners = [e.scanner for e in got]
    assert "vault_scanner" in scanners
    vault = next(e for e in got if e.scanner == "vault_scanner")
    assert vault.error_category == "targets_unreachable"
    assert next(e for e in got if e.scanner == "db1").error_category == "exception"
