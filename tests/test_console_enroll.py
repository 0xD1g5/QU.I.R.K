"""console enroll provisioning tests — Phase 109 CONSOLE-01.

Covers:
  - test_console_enroll: sensors + sensor_tokens rows written; raw token's SHA-256
    matches token_hash; raw token not stored in any DB column.
  - test_console_enroll_duplicate: re-enrolling the same sensor_id exits non-zero
    and writes no second row pair.

pytest -k "console_enroll" selects all tests.
"""
from __future__ import annotations

import hashlib
import sys

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from quirk.models import Base, Sensor, SensorToken


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_db(tmp_path):
    """Create an isolated SQLite DB in tmp_path and return (engine, Session)."""
    db_path = str(tmp_path / "test_enroll.db")
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return db_path, engine, Session


# ---------------------------------------------------------------------------
# test_console_enroll — nominal path
# ---------------------------------------------------------------------------

def test_console_enroll(tmp_path, monkeypatch, capsys):
    """sensors + sensor_tokens rows written; token hash-only persistence.

    Asserts:
      1. One sensors row with sensor_id="S1" and segment="dmz".
      2. One sensor_tokens row whose token_hash == SHA-256(raw_token).
      3. The raw token does not appear in sensors.* or sensor_tokens.* columns.
      4. run_console enroll returns normally (no SystemExit — WR-04).
    """
    db_path, engine, Session = _make_db(tmp_path)
    monkeypatch.setenv("QUIRK_DB_PATH", db_path)

    from quirk.cli.console_cmd import run_console

    # WR-04: enroll success path no longer calls sys.exit(0) — returns normally
    run_console(["enroll", "--sensor-id", "S1", "--segment", "dmz"])

    # Capture stdout — raw token is printed there
    captured = capsys.readouterr()
    stdout_lines = captured.out.strip().splitlines()
    # The raw token is the last line of stdout (after the "Bearer token (copy ...)" label)
    raw_token_line = next(
        (ln for ln in reversed(stdout_lines) if not ln.startswith("Bearer")),
        None,
    )
    assert raw_token_line is not None and len(raw_token_line) > 10, (
        f"Could not extract raw token from stdout: {captured.out!r}"
    )
    raw_token = raw_token_line.strip()

    # Assert sensors row
    db = Session()
    try:
        sensor_row = db.query(Sensor).filter(Sensor.sensor_id == "S1").first()
        assert sensor_row is not None, "sensors row not written by enroll"
        assert sensor_row.segment == "dmz", (
            f"Expected segment='dmz', got {sensor_row.segment!r}"
        )

        # Assert sensor_tokens row
        token_row = db.query(SensorToken).filter(SensorToken.sensor_id == "S1").first()
        assert token_row is not None, "sensor_tokens row not written by enroll"

        # Hash of the printed token must match the stored hash (token_hash = SHA-256(raw_token))
        expected_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        assert token_row.token_hash == expected_hash, (
            f"token_hash mismatch: stored={token_row.token_hash!r} "
            f"expected={expected_hash!r} (raw_token={raw_token!r})"
        )

        # Raw token must NOT appear in any DB column
        all_sensor_values = [
            str(sensor_row.sensor_id or ""),
            str(sensor_row.segment or ""),
            str(sensor_row.engagement or ""),
            str(sensor_row.sensor_version or ""),
        ]
        for col_val in all_sensor_values:
            assert raw_token not in col_val, (
                f"Raw token found in sensors column value: {col_val!r}"
            )

        assert raw_token not in (token_row.token_hash or ""), (
            "Raw token must not be stored in sensor_tokens.token_hash (should be the hash)"
        )
    finally:
        db.close()


# ---------------------------------------------------------------------------
# test_console_enroll_duplicate — no second row pair on re-enroll
# ---------------------------------------------------------------------------

def test_console_enroll_duplicate(tmp_path, monkeypatch, capsys):
    """Re-running enroll with the same sensor_id exits non-zero and writes no second row pair.

    Asserts:
      1. First enroll exits 0, writes 1 sensors row + 1 sensor_tokens row.
      2. Second enroll with same sensor_id raises SystemExit with non-zero code.
      3. After the second attempt, row counts are still 1/1 (no partial second write).
    """
    db_path, engine, Session = _make_db(tmp_path)
    monkeypatch.setenv("QUIRK_DB_PATH", db_path)

    from quirk.cli.console_cmd import run_console

    # --- First enroll: expect success (WR-04: returns normally, no SystemExit) ---
    run_console(["enroll", "--sensor-id", "S-DUP", "--segment", "corp"])

    # --- Second enroll: same sensor_id → must exit non-zero ---
    with pytest.raises(SystemExit) as exc_info_dup:
        run_console(["enroll", "--sensor-id", "S-DUP", "--segment", "corp"])
    assert exc_info_dup.value.code != 0, (
        f"Duplicate enroll should exit non-zero, got {exc_info_dup.value.code}"
    )

    # --- Row counts must still be exactly 1/1 ---
    db = Session()
    try:
        sensor_count = db.query(Sensor).filter(Sensor.sensor_id == "S-DUP").count()
        token_count = db.query(SensorToken).filter(SensorToken.sensor_id == "S-DUP").count()
        assert sensor_count == 1, (
            f"Expected exactly 1 sensors row after duplicate enroll, found {sensor_count}"
        )
        assert token_count == 1, (
            f"Expected exactly 1 sensor_tokens row after duplicate enroll, found {token_count}"
        )
    finally:
        db.close()
