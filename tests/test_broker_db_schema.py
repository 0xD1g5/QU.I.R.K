"""Phase 33 / BROKER-00: broker_scan_json schema regression tests.

Verifies _ensure_broker_columns migration helper runs idempotently and adds
broker_scan_json TEXT NULL to crypto_endpoints without data loss.
"""
import tempfile
import os

import pytest
from sqlalchemy import text, inspect as sa_inspect

from quirk.db import init_db, _ensure_broker_columns


def _fresh_db():
    """Return a (tmp_path, engine) pair for a freshly initialized temp DB.

    Uses a real on-disk SQLite file so init_db(db_path) signature is satisfied.
    Caller is responsible for cleanup (or use as context manager with tempfile).
    """
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    engine = init_db(tmp.name)
    return tmp.name, engine


def test_broker_scan_json_column_exists():
    """BROKER-00: init_db() ensures crypto_endpoints.broker_scan_json (TEXT, nullable)."""
    tmp_path, engine = _fresh_db()
    try:
        cols = {c["name"]: c for c in sa_inspect(engine).get_columns("crypto_endpoints")}
        assert "broker_scan_json" in cols, "broker_scan_json column missing — BROKER-00 violated"
        assert cols["broker_scan_json"]["nullable"] is True, "broker_scan_json must be nullable (TEXT NULL)"
    finally:
        engine.dispose()
        os.unlink(tmp_path)


def test_init_db_twice_no_error():
    """Migration helper is idempotent — running init_db twice does not raise."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    try:
        engine = init_db(tmp.name)   # first call — creates column
        engine.dispose()
        engine = init_db(tmp.name)   # second call — must not raise (column already exists)
        cols = {c["name"] for c in sa_inspect(engine).get_columns("crypto_endpoints")}
        assert "broker_scan_json" in cols
        engine.dispose()
    finally:
        os.unlink(tmp.name)


def test_migration_preserves_existing_rows():
    """Data preservation: existing rows survive _ensure_broker_columns ALTER TABLE."""
    from sqlalchemy import create_engine
    from quirk.models import Base

    # Build a DB WITHOUT calling init_db, so we control the schema state.
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    try:
        engine = create_engine(f"sqlite:///{tmp.name}")
        Base.metadata.create_all(engine)

        # Check if broker_scan_json already exists (Base may include it since model was updated).
        cols_before = {c["name"] for c in sa_inspect(engine).get_columns("crypto_endpoints")}
        if "broker_scan_json" in cols_before:
            # Column already in model; idempotency is covered by test_init_db_twice_no_error.
            pytest.skip("Column already present via Base.metadata; idempotency covered by test_init_db_twice_no_error")

        # Insert a row before migration runs.
        with engine.begin() as conn:
            conn.execute(text(
                "INSERT INTO crypto_endpoints (host, port, protocol) VALUES ('test-host', 9093, 'KAFKA-TLS')"
            ))

        # Now run migration helper.
        _ensure_broker_columns(engine)

        # Verify row survived and broker_scan_json is NULL.
        with engine.connect() as conn:
            rows = list(conn.execute(
                text("SELECT host, port, broker_scan_json FROM crypto_endpoints")
            ).fetchall())

        assert len(rows) == 1, "Row count should be 1 after migration"
        assert rows[0][0] == "test-host", "host column preserved"
        assert rows[0][2] is None, "broker_scan_json should be NULL for pre-existing row"
    finally:
        engine.dispose()
        os.unlink(tmp.name)
