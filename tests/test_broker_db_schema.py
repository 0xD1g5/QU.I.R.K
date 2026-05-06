"""Phase 33 / BROKER-00: broker_scan_json schema regression tests.

Verifies _ensure_broker_columns migration helper runs idempotently and adds
broker_scan_json TEXT NULL to crypto_endpoints without data loss.
"""
import tempfile
import os

from sqlalchemy import inspect as sa_inspect

from quirk.db import init_db


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


# NOTE: A `test_migration_preserves_existing_rows` test previously lived here but
# was a no-op — `broker_scan_json` is now part of `Base.metadata`, so the data-
# preservation path was unreachable and the test always pytest.skipped. Migration
# idempotency is covered by `test_init_db_twice_no_error`. Removed in Phase 41
# Plan 05 (D-04 stale-skip cleanup).
