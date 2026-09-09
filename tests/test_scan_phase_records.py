"""Phase 192 OBS-01: ScanPhaseRecord model + _ensure_scan_phase_records_table.

Wave 0 scaffold: nothing writes to this table yet (Plans 03/04/05 do that).
This file locks the schema and migration only.
"""
from __future__ import annotations

import datetime

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from quirk.db import init_db


# ---------------------------------------------------------------------------
# Task 1: ScanPhaseRecord model + reason constants
# ---------------------------------------------------------------------------


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)


def test_scan_phase_record_roundtrip(tmp_path) -> None:
    from quirk.models import ScanPhaseRecord

    db_path = tmp_path / "roundtrip.db"
    engine = init_db(str(db_path))
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        row = ScanPhaseRecord(
            scan_run_id="2026-09-08T00:00:00+00:00",
            phase_name="tls_scanning",
            status="ran",
            duration_sec=4.2,
            recorded_at=_now(),
        )
        session.add(row)
        session.commit()

        fetched = session.query(ScanPhaseRecord).filter_by(
            scan_run_id="2026-09-08T00:00:00+00:00", phase_name="tls_scanning",
        ).one()
        assert fetched.status == "ran"
        assert fetched.duration_sec == 4.2
    finally:
        session.close()


def test_scan_phase_record_duplicate_raises_integrity_error(tmp_path) -> None:
    from quirk.models import ScanPhaseRecord

    db_path = tmp_path / "dup.db"
    engine = init_db(str(db_path))
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        session.add(ScanPhaseRecord(
            scan_run_id="run-1", phase_name="ssh_scanning",
            status="ran", recorded_at=_now(),
        ))
        session.commit()

        session.add(ScanPhaseRecord(
            scan_run_id="run-1", phase_name="ssh_scanning",
            status="skipped", reason="failed", recorded_at=_now(),
        ))
        with pytest.raises(IntegrityError):
            session.commit()
    finally:
        session.rollback()
        session.close()


def test_scan_phase_record_same_phase_different_scan_run_both_persist(tmp_path) -> None:
    from quirk.models import ScanPhaseRecord

    db_path = tmp_path / "diffrun.db"
    engine = init_db(str(db_path))
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        session.add(ScanPhaseRecord(
            scan_run_id="run-1", phase_name="api_scanning",
            status="ran", recorded_at=_now(),
        ))
        session.add(ScanPhaseRecord(
            scan_run_id="run-2", phase_name="api_scanning",
            status="ran", recorded_at=_now(),
        ))
        session.commit()

        count = session.query(ScanPhaseRecord).filter_by(phase_name="api_scanning").count()
        assert count == 2
    finally:
        session.close()


def test_scan_phase_skip_reasons_exact_membership() -> None:
    from quirk.models import SCAN_PHASE_SKIP_REASONS

    assert len(SCAN_PHASE_SKIP_REASONS) == 5
    assert SCAN_PHASE_SKIP_REASONS == frozenset({
        "disabled-by-config",
        "missing-extra",
        "no-eligible-targets",
        "missing-credentials",
        "failed",
    })


# ---------------------------------------------------------------------------
# Task 2: _ensure_scan_phase_records_table migration + init_db() wiring
# ---------------------------------------------------------------------------


def test_init_db_creates_scan_phase_records_table_on_fresh_db(tmp_path) -> None:
    from sqlalchemy import inspect as sa_inspect

    db_path = tmp_path / "fresh.db"
    engine = init_db(str(db_path))
    names = set(sa_inspect(engine).get_table_names())
    assert "scan_phase_records" in names


def test_init_db_twice_does_not_raise_and_leaves_one_table(tmp_path) -> None:
    from sqlalchemy import inspect as sa_inspect

    db_path = tmp_path / "twice.db"
    engine1 = init_db(str(db_path))
    names1 = set(sa_inspect(engine1).get_table_names())
    assert "scan_phase_records" in names1

    engine2 = init_db(str(db_path))
    names2 = set(sa_inspect(engine2).get_table_names())
    assert names1 == names2


def test_init_db_adds_table_to_preexisting_db_without_touching_others(tmp_path) -> None:
    """A DB with other QUIRK tables but no scan_phase_records gets the table
    added without existing tables being dropped or altered."""
    from sqlalchemy import inspect as sa_inspect
    from quirk.models import Base, ScanPhaseRecord

    db_path = tmp_path / "preexisting.db"

    # Simulate a pre-Phase-192 DB: create all tables EXCEPT scan_phase_records.
    from sqlalchemy import create_engine
    engine = create_engine(f"sqlite:///{db_path}")
    tables_without_new = [
        t for name, t in Base.metadata.tables.items() if name != "scan_phase_records"
    ]
    Base.metadata.create_all(engine, tables=tables_without_new, checkfirst=True)

    names_before = set(sa_inspect(engine).get_table_names())
    assert "scan_phase_records" not in names_before
    assert "scan_checkpoints" in names_before  # a pre-existing table sentinel

    engine2 = init_db(str(db_path))
    names_after = set(sa_inspect(engine2).get_table_names())
    assert "scan_phase_records" in names_after
    assert names_before.issubset(names_after)


# ---------------------------------------------------------------------------
# Plan 03 Task 1: _PhaseRecorder + _wrapped_phase emission
# ---------------------------------------------------------------------------


class _StubLogger:
    """Minimal logger stub — _wrapped_phase only calls .error()."""

    def __init__(self):
        self.errors: list = []

    def error(self, msg):
        self.errors.append(msg)


def _make_run_stats(with_recorder: bool = True) -> dict:
    from run_scan import _PhaseRecorder

    run_stats: dict = {"timings_sec": {}}
    if with_recorder:
        run_stats["phase_records"] = _PhaseRecorder()
    return run_stats


def test_wrapped_phase_ran_records_status_ran_with_duration() -> None:
    from run_scan import _wrapped_phase

    run_stats = _make_run_stats()
    result = _wrapped_phase(
        run_stats, "tls_scanning", "tls", lambda: [], [], _StubLogger()
    )
    assert result == []
    assert "tls_scanning" in run_stats["timings_sec"]

    rows = run_stats["phase_records"].rows()
    assert len(rows) == 1
    assert rows[0]["phase_name"] == "tls_scanning"
    assert rows[0]["status"] == "ran"
    assert rows[0]["duration_sec"] is not None


def test_wrapped_phase_skipped_sentinel_records_status_skipped_no_timing() -> None:
    from run_scan import _wrapped_phase, _PHASE_SKIPPED

    run_stats = _make_run_stats()
    result = _wrapped_phase(
        run_stats, "vault_scanning", "vault", lambda: _PHASE_SKIPPED, [], _StubLogger()
    )
    assert result == []
    assert "vault_scanning" not in run_stats["timings_sec"]

    rows = run_stats["phase_records"].rows()
    assert len(rows) == 1
    assert rows[0]["status"] == "skipped"


def test_wrapped_phase_classified_skip_records_reason_and_detail() -> None:
    from run_scan import _wrapped_phase, _PHASE_SKIPPED

    run_stats = _make_run_stats()
    recorder = run_stats["phase_records"]

    def _fn():
        return recorder.skip("missing-extra", "hvac not installed")

    result = _wrapped_phase(run_stats, "hvac_scanning", "hvac", _fn, [], _StubLogger())
    assert result == []

    rows = recorder.rows()
    assert len(rows) == 1
    assert rows[0]["status"] == "skipped"
    assert rows[0]["reason"] == "missing-extra"
    assert rows[0]["detail"] == "hvac not installed"


def test_wrapped_phase_exception_records_failed_and_still_appends_error_endpoint() -> None:
    from run_scan import _wrapped_phase

    run_stats = _make_run_stats()
    error_endpoints: list = []

    def _fn():
        raise RuntimeError("boom")

    result = _wrapped_phase(
        run_stats, "ssh_scanning", "ssh", _fn, error_endpoints, _StubLogger()
    )
    assert result == []
    assert len(error_endpoints) == 1
    assert error_endpoints[0].scan_error_category == "exception"

    rows = run_stats["phase_records"].rows()
    assert len(rows) == 1
    assert rows[0]["status"] == "skipped"
    assert rows[0]["reason"] == "failed"
    assert "RuntimeError" in rows[0]["detail"]


def test_wrapped_phase_keyboard_interrupt_propagates_and_records_nothing() -> None:
    from run_scan import _wrapped_phase

    run_stats = _make_run_stats()

    def _fn():
        raise KeyboardInterrupt()

    with pytest.raises(KeyboardInterrupt):
        _wrapped_phase(run_stats, "jwt_scanning", "jwt", _fn, [], _StubLogger())

    assert run_stats["phase_records"].rows() == []


def test_wrapped_phase_unclassified_skip_records_none_reason_honest_detail() -> None:
    from run_scan import _wrapped_phase, _PHASE_SKIPPED

    run_stats = _make_run_stats()
    result = _wrapped_phase(
        run_stats, "kms_scanning", "kms", lambda: _PHASE_SKIPPED, [], _StubLogger()
    )
    assert result == []

    rows = run_stats["phase_records"].rows()
    assert len(rows) == 1
    assert rows[0]["reason"] is None
    assert rows[0]["detail"] == "Skip reason not classified"


def test_wrapped_phase_without_phase_records_key_behaves_as_before() -> None:
    from run_scan import _wrapped_phase

    run_stats = {"timings_sec": {}}  # no "phase_records" key at all
    result = _wrapped_phase(
        run_stats, "container_scanning", "container", lambda: ["x"], [], _StubLogger()
    )
    assert result == ["x"]
    assert "container_scanning" in run_stats["timings_sec"]
    assert "phase_records" not in run_stats


# ---------------------------------------------------------------------------
# Plan 03 Task 2: _flush_scan_phase_records
# ---------------------------------------------------------------------------


def test_flush_scan_phase_records_writes_one_row_per_phase(tmp_path) -> None:
    from run_scan import _PhaseRecorder, _flush_scan_phase_records
    from quirk.models import ScanPhaseRecord

    db_path = str(tmp_path / "flush.db")
    init_db(db_path)

    recorder = _PhaseRecorder()
    recorder.record_ran("tls_scanning", 1.23)
    recorder.record_ran("ssh_scanning", 0.5)
    scan_run_id = "run-flush-1"

    _flush_scan_phase_records(db_path, recorder, scan_run_id)

    engine = init_db(db_path)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        rows = session.query(ScanPhaseRecord).filter_by(scan_run_id=scan_run_id).all()
        assert len(rows) == 2
        assert {r.scan_run_id for r in rows} == {scan_run_id}
    finally:
        session.close()


def test_flush_scan_phase_records_twice_does_not_duplicate(tmp_path) -> None:
    from run_scan import _PhaseRecorder, _flush_scan_phase_records
    from quirk.models import ScanPhaseRecord

    db_path = str(tmp_path / "flush_twice.db")
    init_db(db_path)

    recorder = _PhaseRecorder()
    recorder.record_ran("tls_scanning", 1.23)
    scan_run_id = "run-flush-2"

    _flush_scan_phase_records(db_path, recorder, scan_run_id)
    _flush_scan_phase_records(db_path, recorder, scan_run_id)  # re-flush, same rows

    engine = init_db(db_path)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        rows = session.query(ScanPhaseRecord).filter_by(
            scan_run_id=scan_run_id, phase_name="tls_scanning",
        ).all()
        assert len(rows) == 1
    finally:
        session.close()


def test_flush_scan_phase_records_missing_db_path_returns_silently() -> None:
    from run_scan import _PhaseRecorder, _flush_scan_phase_records

    recorder = _PhaseRecorder()
    recorder.record_ran("tls_scanning", 1.0)

    assert _flush_scan_phase_records(None, recorder, "id") is None
    assert _flush_scan_phase_records("/nonexistent/no.db", recorder, "id") is None


def test_flush_scan_phase_records_no_rows_is_a_noop(tmp_path) -> None:
    from run_scan import _PhaseRecorder, _flush_scan_phase_records
    from quirk.models import ScanPhaseRecord

    db_path = str(tmp_path / "norows.db")
    init_db(db_path)
    recorder = _PhaseRecorder()  # no record_* calls made

    _flush_scan_phase_records(db_path, recorder, "run-norows")

    engine = init_db(db_path)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        assert session.query(ScanPhaseRecord).count() == 0
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Plan 04 Task 1: classified skips in the target-list scanner phase guards.
#
# The `_run_X_phase()` closures live nested inside `run_scan.main()` and are
# not independently importable, so — following this codebase's established
# convention (see tests/test_run_scan_adcs_wiring.py's `_run_adcs_phase`
# mirror) — each helper below mirrors its run_scan.py counterpart's guard
# exactly, using a real `_PhaseRecorder` so the recorded reason/detail are
# asserted against the actual `_PhaseRecorder.skip()` contract rather than a
# hand-rolled stand-in.
# ---------------------------------------------------------------------------


def _mk_cfg(**connector_overrides):
    from types import SimpleNamespace

    defaults = dict(
        enable_jwt=False, jwt_targets=[],
        enable_smime=False, smime_targets=[],
    )
    defaults.update(connector_overrides)
    connectors = SimpleNamespace(**defaults)
    return SimpleNamespace(connectors=connectors)


def _jwt_guard(recorder, cfg):
    """Mirrors run_scan.py's `_run_jwt_phase` guard exactly (post Plan 04)."""
    if not cfg.connectors.enable_jwt:
        return recorder.skip("disabled-by-config", "enable_jwt is false")
    if not cfg.connectors.jwt_targets:
        return recorder.skip("no-eligible-targets", "connectors.jwt_targets is empty")
    return None


def test_jwt_guard_disabled_and_no_targets_reports_disabled_by_config() -> None:
    """Precedence rule: disabled-by-config wins over no-eligible-targets when both true."""
    from run_scan import _PhaseRecorder, _PHASE_SKIPPED

    recorder = _PhaseRecorder()
    cfg = _mk_cfg(enable_jwt=False, jwt_targets=[])

    result = _jwt_guard(recorder, cfg)

    assert result is _PHASE_SKIPPED
    recorder.record_skipped("jwt_scanning")
    row = recorder.rows()[0]
    assert row["reason"] == "disabled-by-config"
    assert row["detail"] == "enable_jwt is false"


def test_jwt_guard_enabled_no_targets_reports_no_eligible_targets() -> None:
    from run_scan import _PhaseRecorder, _PHASE_SKIPPED

    recorder = _PhaseRecorder()
    cfg = _mk_cfg(enable_jwt=True, jwt_targets=[])

    result = _jwt_guard(recorder, cfg)

    assert result is _PHASE_SKIPPED
    recorder.record_skipped("jwt_scanning")
    row = recorder.rows()[0]
    assert row["reason"] == "no-eligible-targets"
    assert "connectors.jwt_targets" in row["detail"]


def _smime_guard(recorder, cfg, cfg_smime_skip: bool):
    """Mirrors run_scan.py's `_run_smime_phase` guard exactly (post Plan 04):
    enable check first, THEN the (disabled|missing-extra)-conflating
    cfg_smime_skip flag, so a disabled connector still reports
    disabled-by-config rather than missing-extra."""
    if not getattr(cfg.connectors, "enable_smime", False):
        return recorder.skip("disabled-by-config", "enable_smime is false")
    if cfg_smime_skip:
        return recorder.skip("missing-extra", "ldap3 not installed (extras: adcs)")
    if not getattr(cfg.connectors, "smime_targets", None):
        return recorder.skip("no-eligible-targets", "connectors.smime_targets is empty")
    return None


def test_smime_guard_enabled_targets_present_missing_extra_reports_missing_extra() -> None:
    from run_scan import _PhaseRecorder, _PHASE_SKIPPED

    recorder = _PhaseRecorder()
    cfg = _mk_cfg(enable_smime=True, smime_targets=["ldap://dc.example.com"])

    result = _smime_guard(recorder, cfg, cfg_smime_skip=True)

    assert result is _PHASE_SKIPPED
    recorder.record_skipped("smime_scanning")
    row = recorder.rows()[0]
    assert row["reason"] == "missing-extra"


def _openapi_guard(recorder, spec_path):
    """Mirrors run_scan.py's `_run_openapi_phase` no-spec-path branch exactly
    (post Plan 04) — previously a bare `return []` that looked like the phase
    ran and found nothing."""
    if not spec_path:
        return recorder.skip("no-eligible-targets", "scan.openapi_spec_path is not set")
    return None


def test_openapi_guard_no_spec_path_reports_no_eligible_targets_not_ran() -> None:
    from run_scan import _PhaseRecorder, _PHASE_SKIPPED

    recorder = _PhaseRecorder()

    result = _openapi_guard(recorder, spec_path=None)

    assert result is _PHASE_SKIPPED
    recorder.record_skipped("openapi_scanning")
    row = recorder.rows()[0]
    assert row["status"] == "skipped"
    assert row["reason"] == "no-eligible-targets"


def _fuzz_guard(recorder, fuzz_flag: bool, openapi_endpoints: list):
    """Mirrors run_scan.py's `_run_fuzz_phase` two classified guards exactly
    (post Plan 04)."""
    if not fuzz_flag:
        return recorder.skip("disabled-by-config", "--fuzz not set")
    if not openapi_endpoints:
        return recorder.skip("no-eligible-targets", "no OpenAPI endpoints discovered")
    return None


def test_fuzz_guard_flag_unset_reports_disabled_by_config() -> None:
    from run_scan import _PhaseRecorder, _PHASE_SKIPPED

    recorder = _PhaseRecorder()
    result = _fuzz_guard(recorder, fuzz_flag=False, openapi_endpoints=[])
    assert result is _PHASE_SKIPPED
    recorder.record_skipped("fuzz_scanning")
    assert recorder.rows()[0]["reason"] == "disabled-by-config"


def test_fuzz_guard_no_openapi_endpoints_reports_no_eligible_targets() -> None:
    from run_scan import _PhaseRecorder, _PHASE_SKIPPED

    recorder = _PhaseRecorder()
    result = _fuzz_guard(recorder, fuzz_flag=True, openapi_endpoints=[])
    assert result is _PHASE_SKIPPED
    recorder.record_skipped("fuzz_scanning")
    assert recorder.rows()[0]["reason"] == "no-eligible-targets"
