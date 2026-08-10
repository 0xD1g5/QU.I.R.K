"""Phase 70 BLOCK-08/CR-07: tests for `_SAFE_COL_TYPE_RE` allowlist + ValueError
guard in the column-adding migration path.

Phase 77 D-21 update: the four per-feature helpers (_ensure_v43_columns,
_ensure_phase41_columns, _ensure_phase46_columns, _ensure_phase54_qramm_columns)
were consolidated into a single generic `_ensure_columns(engine, table, expected)`
helper. The allowlist guard semantics are unchanged — these tests now exercise
the same guard via the new entry point and the migrated tuple constants.

Coverage:
    - Parametrized accept/reject matrix on `_SAFE_COL_TYPE_RE` (regex coverage).
    - Poisoned-tuple tests on the generic helper — confirming a bad `col_type`
      raises ValueError before any DDL is interpolated, exercised once per
      original migration feature for parity.
    - Regression test that `init_db()` still works against the real DDL values
      now flowing through the generic guard.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from quirk.db import (
    _BROKER_COLUMNS,
    _EMAIL_COLUMNS,
    _GCP_COLUMNS,
    _IDENTITY_COLUMNS,
    _PHASE41_COLUMNS,
    _PHASE46_COLUMNS,
    _PHASE54_QRAMM_ANSWER_COLUMNS,
    _PHASE146_SCANJOB_COLUMNS,
    _SAFE_COL_TYPE_RE,
    _V43_COLUMNS,
    _ensure_columns,
    get_engine,
    init_db,
    run_additive_migration,
)


# ---------------------------------------------------------------------------
# Regex matrix
# ---------------------------------------------------------------------------

_ACCEPT_VALUES = [
    "TEXT",
    "INTEGER",
    "REAL",
    "BOOLEAN",
    "DATETIME",
    "VARCHAR(16)",
    "VARCHAR(32)",
    "VARCHAR(9999)",
]

_REJECT_VALUES = [
    "TEXT; DROP TABLE x",
    "VARCHAR(99999)",
    "varchar(16)",
    "",
    "TEXT NOT NULL",
    "INTEGER PRIMARY KEY",
    "BLOB",
    "VARCHAR()",
]


@pytest.mark.parametrize("value", _ACCEPT_VALUES)
def test_safe_col_type_re_accepts_real_values(value: str) -> None:
    """Every real DDL fragment in current quirk/db.py dicts must match."""
    assert _SAFE_COL_TYPE_RE.match(value) is not None, (
        f"Allowlist regex unexpectedly rejected real value: {value!r}"
    )


@pytest.mark.parametrize("value", _REJECT_VALUES)
def test_safe_col_type_re_rejects_unsafe_values(value: str) -> None:
    """Injection canaries and out-of-band values must NOT match."""
    assert _SAFE_COL_TYPE_RE.match(value) is None, (
        f"Allowlist regex unexpectedly accepted unsafe value: {value!r}"
    )


# ---------------------------------------------------------------------------
# Poisoned-tuple tests — one per original migration feature.
# Pattern: spin up a fresh DB via init_db (so the existing migrations complete
# before we poison), then invoke `_ensure_columns` with a poisoned (col, ddl)
# tuple. The guard must raise ValueError before any DDL is interpolated.
# (Phase 77 D-21: the 4 prior dict-based helpers collapsed into a single
# generic helper; the poisoned-dict pattern becomes a poisoned-tuple pattern.)
# ---------------------------------------------------------------------------


_POISON = (("evil_col", "TEXT; DROP TABLE x"),)


def test_v43_path_rejects_poisoned_col_type(tmp_path: Path) -> None:
    engine = init_db(str(tmp_path / "poison_v43.db"))
    with pytest.raises(ValueError, match="Unsafe column type"):
        _ensure_columns(engine, "crypto_endpoints", _POISON)


def test_phase41_path_rejects_poisoned_col_type(tmp_path: Path) -> None:
    engine = init_db(str(tmp_path / "poison_p41.db"))
    with pytest.raises(ValueError, match="Unsafe column type"):
        _ensure_columns(engine, "crypto_endpoints", _POISON)


def test_phase46_path_rejects_poisoned_col_type(tmp_path: Path) -> None:
    engine = init_db(str(tmp_path / "poison_p46.db"))
    with pytest.raises(ValueError, match="Unsafe column type"):
        _ensure_columns(engine, "crypto_endpoints", _POISON)


def test_phase54_qramm_path_rejects_poisoned_col_type(tmp_path: Path) -> None:
    engine = init_db(str(tmp_path / "poison_p54.db"))
    with pytest.raises(ValueError, match="Unsafe column type"):
        _ensure_columns(engine, "qramm_answers", _POISON)


def test_phase146_scanjob_path_rejects_poisoned_col_type(tmp_path: Path) -> None:
    engine = init_db(str(tmp_path / "poison_p146.db"))
    with pytest.raises(ValueError, match="Unsafe column type"):
        _ensure_columns(engine, "scan_jobs", _POISON)


# ---------------------------------------------------------------------------
# Regression: real values still pass after the guard lands.
# ---------------------------------------------------------------------------


def test_all_guarded_paths_accept_real_values(tmp_path: Path) -> None:
    """init_db() must complete cleanly, and re-running every consolidated
    migration tuple through the generic guard must remain idempotent."""
    db_path = tmp_path / "real.db"
    engine = init_db(str(db_path))
    # Re-run the consolidated migrations explicitly to exercise the generic
    # guard a second time on real values (idempotent).
    _ensure_columns(engine, "crypto_endpoints", _IDENTITY_COLUMNS)
    _ensure_columns(engine, "crypto_endpoints", _GCP_COLUMNS)
    _ensure_columns(engine, "crypto_endpoints", _V43_COLUMNS)
    _ensure_columns(engine, "crypto_endpoints", _EMAIL_COLUMNS)
    _ensure_columns(engine, "crypto_endpoints", _BROKER_COLUMNS)
    _ensure_columns(engine, "crypto_endpoints", _PHASE41_COLUMNS)
    _ensure_columns(engine, "crypto_endpoints", _PHASE46_COLUMNS)
    _ensure_columns(engine, "qramm_answers", _PHASE54_QRAMM_ANSWER_COLUMNS)
    _ensure_columns(engine, "scan_jobs", _PHASE146_SCANJOB_COLUMNS)


# ---------------------------------------------------------------------------
# Phase 140 BRIDGE-02: bridge-evidence columns migrate additively/idempotently.
# ---------------------------------------------------------------------------


def test_bridge_evidence_columns_migrate_additively(tmp_path: Path) -> None:
    """`bridge_evidence_json`/`bridge_confirmed_at` land on hardware_devices
    via the additive migration and re-running it is a safe no-op."""
    import sqlite3

    db_path = tmp_path / "bridge.db"
    init_db(str(db_path))

    def _table_info_names() -> set[str]:
        conn = sqlite3.connect(str(db_path))
        try:
            rows = conn.execute("PRAGMA table_info(hardware_devices)").fetchall()
        finally:
            conn.close()
        return {row[1] for row in rows}

    cols = _table_info_names()
    assert "bridge_evidence_json" in cols
    assert "bridge_confirmed_at" in cols

    # Second run must be a no-op: no exception, columns unchanged.
    engine = get_engine(str(db_path))
    results = run_additive_migration(engine, dry_run=False)
    bridge_results = [
        r for r in results if r.table == "hardware_devices" and r.column.startswith("bridge_")
    ]
    assert len(bridge_results) == 2
    assert all(r.status == "already-present" for r in bridge_results)

    cols_after = _table_info_names()
    assert cols_after == cols


# ---------------------------------------------------------------------------
# Phase 141 OTICS-06: modbus/bacnet columns migrate additively onto a
# pre-existing hardware_devices table (the exact scenario that silently
# broke live — a DB created before Phase 141 landed).
# ---------------------------------------------------------------------------


def test_otics_columns_migrate_onto_pre_existing_table(tmp_path: Path) -> None:
    """modbus_*/bacnet_* columns must retrofit onto a hardware_devices table
    that predates Phase 141 (not just get created fresh via create_all).

    Regression test: _OTICS_HW_COLUMNS was added to quirk/models.py (141-01)
    but not registered in _ADDITIVE_MIGRATIONS, so init_db() against an
    existing database never added the columns — the Modbus/BACnet scanner's
    DB write silently failed with 'no such column: modbus_vendor' on any
    database created before this migration entry existed.
    """
    import sqlite3

    from quirk.db import _OTICS_HW_COLUMNS

    db_path = tmp_path / "otics.db"

    # Simulate a pre-Phase-141 database: init_db(), then drop the OTICS
    # columns back out so the table matches what a real legacy DB looks like.
    init_db(str(db_path))
    conn = sqlite3.connect(str(db_path))
    try:
        for col, _ in _OTICS_HW_COLUMNS:
            conn.execute(f"ALTER TABLE hardware_devices DROP COLUMN {col}")
        conn.commit()
    finally:
        conn.close()

    def _table_info_names() -> set[str]:
        conn = sqlite3.connect(str(db_path))
        try:
            rows = conn.execute("PRAGMA table_info(hardware_devices)").fetchall()
        finally:
            conn.close()
        return {row[1] for row in rows}

    assert "modbus_vendor" not in _table_info_names()

    # Re-running init_db (as any CLI/dashboard invocation does at startup)
    # must retrofit the missing columns onto the existing table.
    init_db(str(db_path))

    cols = _table_info_names()
    for col, _ in _OTICS_HW_COLUMNS:
        assert col in cols, f"{col} not retrofitted onto pre-existing hardware_devices table"

    # Idempotent: a second run reports already-present, not an error.
    engine = get_engine(str(db_path))
    results = run_additive_migration(engine, dry_run=False)
    otics_results = [
        r for r in results
        if r.table == "hardware_devices" and (r.column.startswith("modbus_") or r.column.startswith("bacnet_"))
    ]
    assert len(otics_results) == len(_OTICS_HW_COLUMNS)
    assert all(r.status == "already-present" for r in otics_results)


# ---------------------------------------------------------------------------
# Phase 146 DISC-04: scan_jobs is the first "pure" table (created only via
# Base.metadata.create_all, never a bespoke ALTER TABLE) to also require an
# additive migration — a legacy pre-Phase-146 scan_jobs table must gain the
# three new batch-progress columns via init_db(), without data loss.
# ---------------------------------------------------------------------------


def test_legacy_scan_jobs_table_gains_batch_progress_columns(tmp_path: Path) -> None:
    """A hand-created legacy scan_jobs table (no batch-progress columns)
    gains all three Phase 146 columns after init_db(), with prior rows intact."""
    import sqlite3

    from sqlalchemy import inspect as sa_inspect

    db_path = tmp_path / "legacy_scan_jobs.db"
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute(
            """
            CREATE TABLE scan_jobs (
                job_id TEXT PRIMARY KEY,
                status TEXT,
                target TEXT,
                profile TEXT,
                calibration TEXT,
                enable_nmap INTEGER
            )
            """
        )
        conn.execute(
            "INSERT INTO scan_jobs (job_id, status, target, profile, calibration, enable_nmap) "
            "VALUES ('job-1', 'queued', '10.0.0.0/24', 'standard', 'balanced', 1)"
        )
        conn.commit()
    finally:
        conn.close()

    engine = init_db(str(db_path))

    columns = {c["name"] for c in sa_inspect(engine).get_columns("scan_jobs")}
    for col, _ in _PHASE146_SCANJOB_COLUMNS:
        assert col in columns, f"{col} not migrated onto legacy scan_jobs table"

    # No data loss: the pre-existing row survives with its original values.
    conn = sqlite3.connect(str(db_path))
    try:
        row = conn.execute(
            "SELECT job_id, status, target FROM scan_jobs WHERE job_id = 'job-1'"
        ).fetchone()
    finally:
        conn.close()
    assert row == ("job-1", "queued", "10.0.0.0/24")


def test_scan_jobs_migration_idempotent(tmp_path: Path) -> None:
    """A second init_db() call is a safe no-op; run_additive_migration then
    reports all three scan_jobs columns as already-present."""
    db_path = tmp_path / "scan_jobs_idempotent.db"
    init_db(str(db_path))
    init_db(str(db_path))  # second call must not raise

    engine = get_engine(str(db_path))
    results = run_additive_migration(engine, dry_run=False)
    scanjob_results = [r for r in results if r.table == "scan_jobs"]
    assert len(scanjob_results) == len(_PHASE146_SCANJOB_COLUMNS)
    assert all(r.status == "already-present" for r in scanjob_results)
