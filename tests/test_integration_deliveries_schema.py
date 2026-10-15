"""Schema guard: init_db creates integration_deliveries table (Phase 101 / NOTIFY-07).

Verifies:
  - Table 'integration_deliveries' exists after init_db
  - Column set is a superset of the agreed 7-column schema
  - scan_id is indexed; finding_hash and error_summary are nullable;
    destination and status are non-null
"""
from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import inspect as sa_inspect

from quirk.db import get_engine, init_db


def test_integration_deliveries_table_created(tmp_path: Path) -> None:
    """NOTIFY-07: init_db must create the integration_deliveries table."""
    db_path = str(tmp_path / "quirk_test.db")
    init_db(db_path)
    engine = get_engine(db_path)
    inspector = sa_inspect(engine)
    tables = inspector.get_table_names()
    assert "integration_deliveries" in tables, (
        f"integration_deliveries table not found. Tables present: {tables}"
    )


def test_integration_deliveries_column_set(tmp_path: Path) -> None:
    """NOTIFY-07: integration_deliveries must have the agreed 7-column schema."""
    db_path = str(tmp_path / "quirk_test.db")
    init_db(db_path)
    engine = get_engine(db_path)
    inspector = sa_inspect(engine)
    cols = {c["name"] for c in inspector.get_columns("integration_deliveries")}
    required = {"id", "scan_id", "finding_hash", "destination", "status",
                "attempted_at", "error_summary"}
    assert cols >= required, (
        f"Missing columns: {required - cols}. Found: {sorted(cols)}"
    )


def test_integration_deliveries_nullable_constraints(tmp_path: Path) -> None:
    """NOTIFY-07: nullable constraints — destination and status must be non-null."""
    db_path = str(tmp_path / "quirk_test.db")
    init_db(db_path)
    engine = get_engine(db_path)
    inspector = sa_inspect(engine)
    col_map = {c["name"]: c for c in inspector.get_columns("integration_deliveries")}
    # destination and status: non-null
    assert not col_map["destination"]["nullable"], "destination must be NOT NULL"
    assert not col_map["status"]["nullable"], "status must be NOT NULL"
    # finding_hash and error_summary: nullable
    assert col_map["finding_hash"]["nullable"], "finding_hash must be nullable"
    assert col_map["error_summary"]["nullable"], "error_summary must be nullable"


def test_integration_deliveries_scan_id_indexed(tmp_path: Path) -> None:
    """NOTIFY-07: scan_id must be indexed for delivery lookup performance."""
    db_path = str(tmp_path / "quirk_test.db")
    init_db(db_path)
    engine = get_engine(db_path)
    inspector = sa_inspect(engine)
    indexes = inspector.get_indexes("integration_deliveries")
    indexed_cols = {col for idx in indexes for col in idx["column_names"]}
    assert "scan_id" in indexed_cols, (
        f"scan_id is not indexed. Indexes: {indexes}"
    )


def test_integration_deliveries_idempotent(tmp_path: Path) -> None:
    """NOTIFY-07: calling init_db twice must not raise (idempotent migration)."""
    db_path = str(tmp_path / "quirk_test.db")
    init_db(db_path)
    init_db(db_path)  # second call must not raise


def test_integration_deliveries_audit_origin_columns(tmp_path: Path) -> None:
    """Push audit rows carry the source address and sensor id (nullable)."""
    db_path = str(tmp_path / "quirk_test.db")
    init_db(db_path)
    inspector = sa_inspect(get_engine(db_path))
    col_map = {c["name"]: c for c in inspector.get_columns("integration_deliveries")}
    assert {"client_ip", "sensor_id"} <= set(col_map)
    assert col_map["client_ip"]["nullable"] and col_map["sensor_id"]["nullable"]


def test_integration_deliveries_origin_columns_added_to_old_table(tmp_path: Path) -> None:
    """An existing 7-column table gains client_ip / sensor_id through init_db."""
    import sqlite3

    db_path = str(tmp_path / "old.db")
    con = sqlite3.connect(db_path)
    con.execute(
        "CREATE TABLE integration_deliveries (id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " scan_id VARCHAR(64) NOT NULL, finding_hash VARCHAR(64),"
        " destination VARCHAR(64) NOT NULL, status VARCHAR(16) NOT NULL,"
        " attempted_at DATETIME NOT NULL, error_summary TEXT)"
    )
    con.commit()
    con.close()
    init_db(db_path)
    cols = {c["name"] for c in sa_inspect(get_engine(db_path)).get_columns("integration_deliveries")}
    assert {"client_ip", "sensor_id"} <= cols
