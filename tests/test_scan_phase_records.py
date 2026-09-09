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


def test_wrapped_phase_exception_detail_is_credential_safe() -> None:
    """T-192-03 / review CR-02: the failed-phase `detail` column must route
    through safe_str() — a DSN / password embedded in exception text must never
    reach scan_phase_records verbatim (it is persisted, API-served, and
    rendered on all four report surfaces)."""
    from run_scan import _wrapped_phase

    run_stats = _make_run_stats()
    error_endpoints: list = []

    def _fn():
        raise ConnectionError(
            'could not connect: "postgresql://svc:hunter2@db.internal:5432/app"'
        )

    result = _wrapped_phase(
        run_stats, "db_scanning", "db_connector", _fn, error_endpoints, _StubLogger()
    )
    assert result == []

    rows = run_stats["phase_records"].rows()
    assert len(rows) == 1
    assert rows[0]["reason"] == "failed"
    detail = rows[0]["detail"]
    # safe_str collapses credential-shaped messages to the class name only.
    assert "hunter2" not in detail
    assert "svc:" not in detail
    assert "ConnectionError" in detail


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


def test_record_resumed_writes_honest_unclassified_skipped_row() -> None:
    """Review WR-07: checkpoint-skipped phases in a resumed run get an honest
    row (unclassified shape, explicit resume detail) instead of being absent —
    absence-as-a-signal is forbidden by D-10."""
    from run_scan import _PhaseRecorder, _record_resumed_stage_phases

    run_stats = {"phase_records": _PhaseRecorder()}
    _record_resumed_stage_phases(run_stats, ("aws_scanning", "db_scanning"))

    rows = run_stats["phase_records"].rows()
    assert [r["phase_name"] for r in rows] == ["aws_scanning", "db_scanning"]
    for row in rows:
        assert row["status"] == "skipped"
        assert row["reason"] is None
        assert row["detail"] == "completed in prior run (resumed)"
        assert row["duration_sec"] is None

    # No recorder present (run_stats without phase_records) is a no-op.
    _record_resumed_stage_phases({}, ("tls_scanning",))


def test_flush_resume_backfill_never_overwrites_prior_run_real_row(tmp_path) -> None:
    """Review WR-07: if the prior run already flushed a real row for a phase,
    a resumed run's backfill marker for the same (scan_run_id, phase_name)
    must not clobber it."""
    from run_scan import _PhaseRecorder, _flush_scan_phase_records
    from quirk.models import ScanPhaseRecord

    db_path = str(tmp_path / "resume_backfill.db")
    init_db(db_path)
    scan_run_id = "run-resume-1"

    prior = _PhaseRecorder()
    prior.record_ran("tls_scanning", 2.5)
    _flush_scan_phase_records(db_path, prior, scan_run_id)

    resumed = _PhaseRecorder()
    resumed.record_resumed("tls_scanning")  # backfill marker for same phase
    resumed.record_resumed("ssh_scanning")  # phase with no prior row
    _flush_scan_phase_records(db_path, resumed, scan_run_id)

    engine = init_db(db_path)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        tls = session.query(ScanPhaseRecord).filter_by(
            scan_run_id=scan_run_id, phase_name="tls_scanning",
        ).one()
        assert tls.status == "ran"  # real prior row preserved
        assert tls.duration_sec == 2.5
        ssh = session.query(ScanPhaseRecord).filter_by(
            scan_run_id=scan_run_id, phase_name="ssh_scanning",
        ).one()
        assert ssh.status == "skipped"
        assert ssh.reason is None
        assert ssh.detail == "completed in prior run (resumed)"
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


# ---------------------------------------------------------------------------
# Plan 04 Task 2: classified skips in cloud/storage/broker/email/vault guards
# + the completeness sweep proving no unclassified skip path remains.
# ---------------------------------------------------------------------------


def _s3_guard(recorder, enable_s3: bool, boto3_available: bool):
    """Mirrors run_scan.py's `_run_s3_phase` guard exactly (post Plan 04)."""
    if not enable_s3:
        return recorder.skip("disabled-by-config", "enable_s3 is false")
    if not boto3_available:
        return recorder.skip("missing-extra", "boto3 not installed")
    return None


def _vault_guard(recorder, enable_vault: bool, hvac_available: bool, vault_addr):
    """Mirrors run_scan.py's `_run_vault_phase` guard exactly (post Plan 04)."""
    if not enable_vault:
        return recorder.skip("disabled-by-config", "enable_vault is false")
    if not hvac_available:
        return recorder.skip("missing-extra", "hvac not installed (extras: vault)")
    if not vault_addr:
        return recorder.skip(
            "no-eligible-targets", "connectors.vault_addr / VAULT_ADDR is not set",
        )
    return None


def _email_guard(recorder, enable_email: bool, cfg_email_skip: bool, email_hosts: list):
    """Mirrors run_scan.py's `_run_email_phase` guard exactly (post Plan 04)."""
    if not enable_email:
        return recorder.skip("disabled-by-config", "enable_email is false")
    if cfg_email_skip:
        return recorder.skip("missing-extra", "sslyze not installed (extras: motion)")
    if not email_hosts:
        return recorder.skip("no-eligible-targets", "no TLS-scanned hosts to derive email hosts from")
    return None


def _broker_guard(recorder, enable_broker: bool, cfg_broker_skip: bool, broker_hosts: list):
    """Mirrors run_scan.py's `_run_broker_phase` guard exactly (post Plan 04)."""
    if not enable_broker:
        return recorder.skip("disabled-by-config", "enable_broker is false")
    if cfg_broker_skip:
        return recorder.skip(
            "missing-extra", "sslyze/kafka-python/redis not installed (extras: motion)",
        )
    if not broker_hosts:
        return recorder.skip(
            "no-eligible-targets", "no TLS-scanned hosts and connectors.broker_targets is empty",
        )
    return None


def test_s3_guard_enabled_boto3_unavailable_reports_missing_extra() -> None:
    from run_scan import _PhaseRecorder, _PHASE_SKIPPED

    recorder = _PhaseRecorder()
    result = _s3_guard(recorder, enable_s3=True, boto3_available=False)
    assert result is _PHASE_SKIPPED
    recorder.record_skipped("s3_scanning")
    assert recorder.rows()[0]["reason"] == "missing-extra"


def test_vault_guard_enabled_hvac_available_no_addr_reports_no_eligible_targets() -> None:
    from run_scan import _PhaseRecorder, _PHASE_SKIPPED

    recorder = _PhaseRecorder()
    result = _vault_guard(recorder, enable_vault=True, hvac_available=True, vault_addr="")
    assert result is _PHASE_SKIPPED
    recorder.record_skipped("vault_scanning")
    row = recorder.rows()[0]
    assert row["reason"] == "no-eligible-targets"
    assert "vault_addr" in row["detail"]
    assert "VAULT_ADDR" in row["detail"]


def test_email_guard_disabled_zero_hosts_reports_disabled_by_config() -> None:
    """enable_email=False must win over the empty-hosts branch."""
    from run_scan import _PhaseRecorder, _PHASE_SKIPPED

    recorder = _PhaseRecorder()
    result = _email_guard(recorder, enable_email=False, cfg_email_skip=True, email_hosts=[])
    assert result is _PHASE_SKIPPED
    recorder.record_skipped("email_scanning")
    assert recorder.rows()[0]["reason"] == "disabled-by-config"


def test_email_guard_enabled_missing_extra_reports_missing_extra_not_disabled() -> None:
    from run_scan import _PhaseRecorder, _PHASE_SKIPPED

    recorder = _PhaseRecorder()
    result = _email_guard(recorder, enable_email=True, cfg_email_skip=True, email_hosts=["a.example.com"])
    assert result is _PHASE_SKIPPED
    recorder.record_skipped("email_scanning")
    assert recorder.rows()[0]["reason"] == "missing-extra"


def test_broker_guard_disabled_reports_disabled_by_config_not_missing_extra() -> None:
    """Proves _broker_missing_extra's disabled/missing-extra conflation was split
    correctly — a disabled broker connector must never surface as missing-extra."""
    from run_scan import _PhaseRecorder, _PHASE_SKIPPED

    recorder = _PhaseRecorder()
    # cfg_broker_skip=True mirrors _broker_missing_extra(enable_broker=False, ...) == True
    result = _broker_guard(recorder, enable_broker=False, cfg_broker_skip=True, broker_hosts=["h"])
    assert result is _PHASE_SKIPPED
    recorder.record_skipped("broker_scanning")
    assert recorder.rows()[0]["reason"] == "disabled-by-config"


def test_all_skip_details_are_nonempty_strings() -> None:
    from run_scan import _PhaseRecorder

    recorder = _PhaseRecorder()
    scenarios = [
        lambda: _jwt_guard(recorder, _mk_cfg(enable_jwt=False, jwt_targets=[])),
        lambda: _jwt_guard(recorder, _mk_cfg(enable_jwt=True, jwt_targets=[])),
        lambda: _smime_guard(recorder, _mk_cfg(enable_smime=True, smime_targets=["x"]), True),
        lambda: _openapi_guard(recorder, spec_path=None),
        lambda: _fuzz_guard(recorder, fuzz_flag=False, openapi_endpoints=[]),
        lambda: _s3_guard(recorder, enable_s3=True, boto3_available=False),
        lambda: _vault_guard(recorder, enable_vault=True, hvac_available=True, vault_addr=""),
        lambda: _email_guard(recorder, enable_email=False, cfg_email_skip=True, email_hosts=[]),
        lambda: _broker_guard(recorder, enable_broker=False, cfg_broker_skip=True, broker_hosts=[]),
    ]
    for i, scenario in enumerate(scenarios):
        scenario()
        recorder.record_skipped(f"phase_{i}")

    for row in recorder.rows():
        assert row["status"] == "skipped"
        assert row["reason"] is not None
        assert isinstance(row["detail"], str) and row["detail"] != ""


def test_no_unclassified_phase_skip_sentinel_returns_remain() -> None:
    """Runtime source scan (Plan 04's completeness gate — NOT a hand-derived list,
    per this project's own TOOL-04 lesson about hand-maintained occurrence lists
    going stale). The only literal `return _PHASE_SKIPPED` left in run_scan.py must
    be the one inside `_PhaseRecorder.skip()` itself; every scanner-phase guard site
    must instead route through a classified `_recorder.skip(reason, detail)` call."""
    import inspect
    import run_scan

    source = inspect.getsource(run_scan)
    bare_returns = [
        line for line in source.splitlines()
        if line.strip() == "return _PHASE_SKIPPED"
    ]
    assert len(bare_returns) == 1, (
        f"expected exactly 1 bare 'return _PHASE_SKIPPED' (inside _PhaseRecorder.skip()), "
        f"found {len(bare_returns)}"
    )


def test_every_recorder_skip_call_site_uses_a_reason_from_the_frozen_set() -> None:
    """Runtime source scan: every `_recorder.skip("...", ...)` / `recorder.skip("...", ...)`
    call site in run_scan.py must pass one of the five frozen SCAN_PHASE_SKIP_REASONS —
    catches a typo'd or invented reason string at the point it's introduced."""
    import inspect
    import re
    import run_scan
    from quirk.models import SCAN_PHASE_SKIP_REASONS

    source = inspect.getsource(run_scan)
    reasons_used = re.findall(r'_recorder\.skip\(\s*"([^"]+)"', source)
    assert len(reasons_used) >= 20, (
        f"expected at least 20 classified recorder.skip(...) call sites across the "
        f"scanner phase guards, found {len(reasons_used)}"
    )
    for reason in reasons_used:
        assert reason in SCAN_PHASE_SKIP_REASONS, f"unknown skip reason literal: {reason!r}"
    # `failed` is only ever emitted by _PhaseRecorder.record_failed(), never a
    # guard-site skip() call — guards only ever use the other four reasons.
    assert "failed" not in reasons_used


def test_no_skip_call_site_embeds_a_credential_looking_detail_string() -> None:
    """T-192-12: skip `detail` strings may only name config keys / env vars, never
    values. Scans every literal detail string passed to a `.skip(...)` call site for
    credential-shaped substrings that would indicate a value (not a name) leaked in."""
    import inspect
    import re
    import run_scan

    source = inspect.getsource(run_scan)
    calls = re.findall(r'_recorder\.skip\(([^;]*?)\)\n', source, re.S)
    assert calls, "expected at least one recorder.skip(...) call site to scan"
    forbidden_value_markers = ("hunter2", "Bearer ", "-----BEGIN")
    for call_args in calls:
        for marker in forbidden_value_markers:
            assert marker not in call_args


# ---------------------------------------------------------------------------
# Plan 05: pre-flight missing-credentials guards (vault, db) + the ADCS/broker
# disposition. Mirrors run_scan.py's real `_run_vault_phase` / `_run_db_phase`
# closures exactly (same convention as tests/test_run_scan_adcs_wiring.py),
# patching the real scanner entry points at their own module location so a
# spy assertion proves the connector is genuinely never invoked.
# ---------------------------------------------------------------------------


def _vault_cfg(vault_token=None, vault_addr="https://vault.example.com:8200"):
    from types import SimpleNamespace

    connectors = SimpleNamespace(
        enable_vault=True,
        vault_addr=vault_addr,
        vault_token=vault_token,
        vault_transit_mount="transit",
        vault_tls_verify=True,
    )
    return SimpleNamespace(connectors=connectors)


def _run_vault_phase_mirror(recorder, cfg, logger):
    """Mirrors run_scan.py's `_run_vault_phase` guard exactly (post Plan 05)."""
    import os as _os

    from quirk.config_redaction import credential_is_set

    if not cfg.connectors.enable_vault:
        return recorder.skip("disabled-by-config", "enable_vault is false")
    from quirk.scanner.vault_connector import scan_vault_targets, HVAC_AVAILABLE
    if not HVAC_AVAILABLE:
        return recorder.skip("missing-extra", "hvac not installed (extras: vault)")
    if not (cfg.connectors.vault_addr or _os.environ.get("VAULT_ADDR")):
        return recorder.skip(
            "no-eligible-targets", "connectors.vault_addr / VAULT_ADDR is not set",
        )
    if not credential_is_set("connectors", "vault_token", cfg.connectors.vault_token):
        return recorder.skip(
            "missing-credentials", "connectors.vault_token / VAULT_TOKEN not set",
        )
    _vault_token = cfg.connectors.vault_token or _os.environ.get("VAULT_TOKEN", "")
    return scan_vault_targets(
        vault_addr=cfg.connectors.vault_addr or _os.environ.get("VAULT_ADDR", ""),
        token=_vault_token,
        transit_mount=cfg.connectors.vault_transit_mount or "transit",
        tls_verify=cfg.connectors.vault_tls_verify,
        logger=logger,
        session_start=None,
        cfg=cfg,
    )


def test_vault_guard_no_token_no_env_reports_missing_credentials_and_never_scans(
    monkeypatch,
) -> None:
    from unittest.mock import patch

    from run_scan import _PhaseRecorder

    monkeypatch.delenv("VAULT_TOKEN", raising=False)
    monkeypatch.setattr("quirk.scanner.vault_connector.HVAC_AVAILABLE", True)
    recorder = _PhaseRecorder()
    cfg = _vault_cfg(vault_token=None)

    with patch(
        "quirk.scanner.vault_connector.scan_vault_targets", return_value=[],
    ) as mock_scan:
        result = _run_vault_phase_mirror(recorder, cfg, logger=None)

    mock_scan.assert_not_called()
    from run_scan import _PHASE_SKIPPED
    assert result is _PHASE_SKIPPED
    recorder.record_skipped("vault_scanning")
    row = recorder.rows()[0]
    assert row["reason"] == "missing-credentials"
    assert "vault_token" in row["detail"]
    assert "VAULT_TOKEN" in row["detail"]


def test_vault_guard_env_only_token_does_not_skip(monkeypatch) -> None:
    from unittest.mock import patch

    from run_scan import _PhaseRecorder

    monkeypatch.setenv("VAULT_TOKEN", "s.abcdef1234")
    monkeypatch.setattr("quirk.scanner.vault_connector.HVAC_AVAILABLE", True)
    recorder = _PhaseRecorder()
    cfg = _vault_cfg(vault_token=None)

    with patch(
        "quirk.scanner.vault_connector.scan_vault_targets", return_value=[],
    ) as mock_scan:
        result = _run_vault_phase_mirror(recorder, cfg, logger=None)

    mock_scan.assert_called_once()
    assert result == []
    assert recorder.rows() == []


def _db_cfg(pg_targets=None, mysql_targets=None, pg_user=None, pg_password=None,
            mysql_user=None, mysql_password=None):
    from types import SimpleNamespace

    connectors = SimpleNamespace(
        enable_db=True,
        pg_targets=pg_targets or [],
        mysql_targets=mysql_targets or [],
        pg_scanner_user=pg_user,
        pg_scanner_password=pg_password,
        mysql_scanner_user=mysql_user,
        mysql_scanner_password=mysql_password,
    )
    return SimpleNamespace(connectors=connectors)


def _run_db_phase_mirror(recorder, cfg, logger):
    """Mirrors run_scan.py's `_run_db_phase` guard exactly (post review CR-01).

    Deliberately has NO missing-credentials pre-gate: both connectors support
    running with no config credentials (libpq .pgpass / PGPASSWORD / trust /
    peer for pg; pymysql defaults file / env for mysql), and default the user
    ("postgres" / "root") when unset — see quirk/scanner/db_connector.py
    Phase 72 D-20 / WR-07.
    """
    if not cfg.connectors.enable_db:
        return recorder.skip("disabled-by-config", "enable_db is false")
    from quirk.scanner.db_connector import (
        scan_pg_targets, scan_mysql_targets, PSYCOPG2_AVAILABLE, PYMYSQL_AVAILABLE,
    )
    if not (PSYCOPG2_AVAILABLE or PYMYSQL_AVAILABLE):
        return recorder.skip(
            "missing-extra", "psycopg2 and PyMySQL not installed (extras: db)",
        )
    if not (cfg.connectors.pg_targets or cfg.connectors.mysql_targets):
        return recorder.skip(
            "no-eligible-targets",
            "connectors.pg_targets and connectors.mysql_targets are both empty",
        )
    result = []
    if cfg.connectors.pg_targets:
        result.extend(scan_pg_targets(
            targets=cfg.connectors.pg_targets, user=cfg.connectors.pg_scanner_user,
            password=cfg.connectors.pg_scanner_password, logger=logger,
            session_start=None, cfg=cfg,
        ))
    if cfg.connectors.mysql_targets:
        result.extend(scan_mysql_targets(
            targets=cfg.connectors.mysql_targets, user=cfg.connectors.mysql_scanner_user,
            password=cfg.connectors.mysql_scanner_password, logger=logger,
            session_start=None, cfg=cfg,
        ))
    return result


def test_db_guard_pg_uncredentialed_no_mysql_still_runs_pg_via_libpq_fallbacks() -> None:
    """Review CR-01: a pg-targets-only config with no pg_scanner_user /
    pg_scanner_password must still invoke scan_pg_targets — password=None means
    libpq resolves .pgpass / PGPASSWORD / trust / peer, and the user defaults
    to the OS/libpq default. It must NOT be pre-gated as missing-credentials."""
    from unittest.mock import patch

    from run_scan import _PhaseRecorder

    recorder = _PhaseRecorder()
    cfg = _db_cfg(pg_targets=["db.example.com:5432"], mysql_targets=[])

    with patch(
        "quirk.scanner.db_connector.scan_pg_targets", return_value=["pg-ep"],
    ) as mock_pg, patch(
        "quirk.scanner.db_connector.scan_mysql_targets", return_value=[],
    ) as mock_mysql, patch(
        "quirk.scanner.db_connector.PSYCOPG2_AVAILABLE", True,
    ), patch(
        "quirk.scanner.db_connector.PYMYSQL_AVAILABLE", True,
    ):
        result = _run_db_phase_mirror(recorder, cfg, logger=None)

    mock_pg.assert_called_once_with(
        targets=["db.example.com:5432"], user=None, password=None,
        logger=None, session_start=None, cfg=cfg,
    )
    mock_mysql.assert_not_called()
    assert result == ["pg-ep"]
    assert recorder.rows() == []


def test_db_guard_mixed_pg_uncredentialed_mysql_credentialed_runs_both_groups() -> None:
    """Review CR-01: mixed configs run BOTH target groups — the uncredentialed
    pg leg is not asymmetrically dropped (each connector owns its own auth
    failure reporting)."""
    from unittest.mock import patch

    from run_scan import _PhaseRecorder

    recorder = _PhaseRecorder()
    cfg = _db_cfg(
        pg_targets=["pg.example.com:5432"], mysql_targets=["mysql.example.com:3306"],
        pg_user=None, pg_password=None,
        mysql_user="svc", mysql_password="s3cret-placeholder",
    )

    with patch(
        "quirk.scanner.db_connector.scan_pg_targets", return_value=["pg-ep"],
    ) as mock_pg, patch(
        "quirk.scanner.db_connector.scan_mysql_targets", return_value=["mysql-ep"],
    ) as mock_mysql, patch(
        "quirk.scanner.db_connector.PSYCOPG2_AVAILABLE", True,
    ), patch(
        "quirk.scanner.db_connector.PYMYSQL_AVAILABLE", True,
    ):
        result = _run_db_phase_mirror(recorder, cfg, logger=None)

    mock_pg.assert_called_once()
    mock_mysql.assert_called_once()
    assert result == ["pg-ep", "mysql-ep"]
    assert recorder.rows() == []


def test_broker_credential_is_set_resolves_pass_env_indirection(monkeypatch) -> None:
    """Task 2: `BrokerCredential.pass_env` names an env var; presence must resolve
    through `os.environ.get(pass_env)`, not the config field's own truthiness."""
    from types import SimpleNamespace

    from run_scan import _broker_credential_is_set

    monkeypatch.delenv("QUIRK_TEST_BROKER_PW", raising=False)
    cred_unset = SimpleNamespace(user="svc", pass_env="QUIRK_TEST_BROKER_PW")
    assert _broker_credential_is_set(cred_unset) is False

    monkeypatch.setenv("QUIRK_TEST_BROKER_PW", "s3cret-placeholder")
    cred_set = SimpleNamespace(user="svc", pass_env="QUIRK_TEST_BROKER_PW")
    assert _broker_credential_is_set(cred_set) is True

    assert _broker_credential_is_set(None) is False
    assert _broker_credential_is_set(SimpleNamespace(user="svc", pass_env="")) is False


def test_missing_credentials_reason_is_reachable_in_a_real_guard_path(monkeypatch) -> None:
    """Proves `missing-credentials` is a live, tested reason — not a declared-but-
    never-emitted enum value (Plan 05 objective)."""
    from run_scan import _PhaseRecorder, _PHASE_SKIPPED

    monkeypatch.delenv("VAULT_TOKEN", raising=False)
    monkeypatch.setattr("quirk.scanner.vault_connector.HVAC_AVAILABLE", True)
    recorder = _PhaseRecorder()
    cfg = _vault_cfg(vault_token=None)

    from unittest.mock import patch
    with patch("quirk.scanner.vault_connector.scan_vault_targets", return_value=[]):
        result = _run_vault_phase_mirror(recorder, cfg, logger=None)

    assert result is _PHASE_SKIPPED
    recorder.record_skipped("vault_scanning")
    assert recorder.rows()[0]["reason"] == "missing-credentials"
