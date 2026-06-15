"""RED test — AUDIT-12: _cmd_enroll must use a single session/transaction.

Contract: the existence check and the INSERT of the sensors + sensor_tokens
rows must occur within a SINGLE database session (no separate pre-check
session followed by a separate insert session).

Current state: _cmd_enroll calls init_db() TWICE:
  1. engine_precheck = init_db(db_path_precheck)  ← pre-check session
  2. engine = init_db(db_path)                     ← insert session

This two-call pattern has a TOCTOW (Time-Of-Check-To-Time-Of-Write) race
window: between the pre-check SELECT and the INSERT a concurrent enroll can
sneak in.  The IntegrityError backstop is the only guard.

AUDIT-12 requires collapsing to a single init_db() call so the check and
write happen atomically in one transaction.

Assertion strategy: structural — assert that _cmd_enroll calls init_db()
exactly ONCE.  If two separate calls are made, the test fails.  This is the
correct RED target because the behavioral assertions (duplicate rejection)
already PASS against current main (the IntegrityError backstop works).

Wave 2 (plan 131-03) will refactor _cmd_enroll to use a single session.

pytest -q tests/test_console_enroll_race.py
"""
from __future__ import annotations

import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import pytest

from quirk.models import Base, Sensor, SensorToken


# ---------------------------------------------------------------------------
# Helper: make an isolated SQLite DB in tmp_path
# ---------------------------------------------------------------------------

def _make_db(tmp_path):
    db_path = str(tmp_path / "test_enroll_race.db")
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return db_path, engine, Session


# ---------------------------------------------------------------------------
# Test 1 (RED): _cmd_enroll must call init_db() exactly once (single-session)
# ---------------------------------------------------------------------------

def test_cmd_enroll_uses_single_session(tmp_path, monkeypatch):
    """AUDIT-12 RED: _cmd_enroll must call init_db() exactly once (single-session).

    The current implementation calls init_db() TWICE:
      1. engine_precheck = init_db(db_path_precheck)  ← pre-check engine
      2. engine = init_db(db_path)                     ← insert engine

    AUDIT-12 contract: a single init_db() call, a single engine, and a single
    session/transaction for both the existence check and the insert.

    EXPECTED FAILURE: current code calls init_db() TWICE, so init_db_call_count
    will be 2, not 1.

    Wave 2 (131-03) will refactor _cmd_enroll to a single-transaction pattern.
    """
    db_path, engine, RealSession = _make_db(tmp_path)
    monkeypatch.setenv("QUIRK_DB_PATH", db_path)

    # Track how many times init_db is called by patching quirk.db.init_db.
    # _cmd_enroll imports init_db from quirk.db inside the function body, so
    # patching the quirk.db module attribute is the correct interception point.
    init_db_call_count = [0]

    import quirk.db as quirk_db_mod
    real_init_db = quirk_db_mod.init_db

    def tracking_init_db(path):
        init_db_call_count[0] += 1
        return real_init_db(path)

    monkeypatch.setattr(quirk_db_mod, "init_db", tracking_init_db)

    # Patch _default_db_path so both calls resolve to our test DB
    import quirk.dashboard.api.deps as deps_mod
    monkeypatch.setattr(deps_mod, "_default_db_path", lambda: db_path)

    from quirk.cli.console_cmd import run_console

    # Execute enroll — must write 1 Sensor + 1 SensorToken row
    run_console(["enroll", "--sensor-id", "test-sensor-race-01", "--segment", "corp"])

    # AUDIT-12 CONTRACT: exactly ONE init_db() call (single-session pattern).
    # EXPECTED FAILURE: current code calls init_db() TWICE.
    assert init_db_call_count[0] == 1, (
        f"AUDIT-12 RED: expected _cmd_enroll to call init_db() exactly 1 time, "
        f"but it was called {init_db_call_count[0]} time(s). "
        "Current code calls init_db() for a pre-check engine AND again for the "
        "insert engine, creating two distinct sessions with a TOCTOW race window. "
        "Wave 2 (131-03) will collapse to a single init_db() + single transaction."
    )


# ---------------------------------------------------------------------------
# Test 2 (behavioral, passes today): two enrolls of same id → exactly 1 row pair
# ---------------------------------------------------------------------------

def test_duplicate_enroll_yields_one_row_pair(tmp_path, monkeypatch):
    """Behavioral contract (passes today): two enroll calls for the same sensor_id
    must yield exactly 1 sensors row and 1 sensor_tokens row.

    This test is expected to PASS against current main (IntegrityError backstop
    already prevents double-insert). It documents the behavioral contract that
    must be preserved after the single-session refactor (Wave 2, 131-03).

    NOT a RED test — included here as a regression guard.
    """
    db_path, engine, Session = _make_db(tmp_path)
    monkeypatch.setenv("QUIRK_DB_PATH", db_path)

    from quirk.cli.console_cmd import run_console

    # First enroll — must succeed
    run_console(["enroll", "--sensor-id", "S-RACE-01", "--segment", "dmz"])

    # Second enroll — same sensor_id: must not duplicate rows
    # (may return normally with "already enrolled" or exit — either is OK)
    try:
        run_console(["enroll", "--sensor-id", "S-RACE-01", "--segment", "dmz"])
    except SystemExit:
        pass  # IntegrityError path calls sys.exit(1) — acceptable

    db = Session()
    try:
        sensor_count = db.query(Sensor).filter(Sensor.sensor_id == "S-RACE-01").count()
        token_count = db.query(SensorToken).filter(SensorToken.sensor_id == "S-RACE-01").count()
        assert sensor_count == 1, (
            f"Expected exactly 1 sensors row after duplicate enroll, found {sensor_count}"
        )
        assert token_count == 1, (
            f"Expected exactly 1 sensor_tokens row after duplicate enroll, found {token_count}"
        )
    finally:
        db.close()
