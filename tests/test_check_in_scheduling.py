"""Phase 162 (HWLC-20) — scheduling a check-in re-probe.

A check-in is structurally distinct from a scored scan: `run_check_in()`
short-circuits `main()` before scan_run_id/checkpoint logic, resolves the fleet
from the database rather than a target, and never invokes discovery, the scoring
engine or the report writer.

Criterion 3 is therefore mostly a proof obligation rather than new code — a
scheduled check-in executes the *identical* code path as a manual one, because
the dispatcher's only job is to emit `--check-in`. These tests assert that no
second implementation crept in.
"""
from __future__ import annotations

import datetime
import tempfile
import os

import pytest

from quirk.cli.schedule_cmd import CHECK_IN_TARGET_SENTINEL
from quirk.db import get_session, init_db
from quirk.models import ScheduledScan


def _fresh_db():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    init_db(tmp.name)
    return tmp.name


# ---------------------------------------------------------------------------
# Criterion 1 — a check-in schedule can be created and round-trips
# ---------------------------------------------------------------------------


class TestCheckInScheduleRoundTrip:
    def test_check_in_flag_persists(self):
        db_path = _fresh_db()
        try:
            with get_session(db_path) as db:
                db.add(ScheduledScan(
                    name="nightly-checkin", cron_expr="0 2 * * *",
                    target=CHECK_IN_TARGET_SENTINEL, profile=None,
                    check_in=True, enabled=True,
                    created_at=datetime.datetime.now(datetime.timezone.utc),
                ))
                db.commit()
            with get_session(db_path) as db:
                row = db.query(ScheduledScan).one()
                assert row.check_in is True
                assert row.target == CHECK_IN_TARGET_SENTINEL
        finally:
            os.unlink(db_path)

    def test_normal_schedule_defaults_to_not_check_in(self):
        db_path = _fresh_db()
        try:
            with get_session(db_path) as db:
                db.add(ScheduledScan(
                    name="weekly-scan", cron_expr="0 0 * * 0",
                    target="10.0.0.0/24", profile="standard", enabled=True,
                    created_at=datetime.datetime.now(datetime.timezone.utc),
                ))
                db.commit()
            with get_session(db_path) as db:
                assert bool(db.query(ScheduledScan).one().check_in) is False
        finally:
            os.unlink(db_path)

    def test_check_in_column_exists_on_a_pre_existing_database(self):
        """The additive migration must reach databases created before Phase 162."""
        import sqlite3
        from sqlalchemy import inspect as sa_inspect

        db_path = _fresh_db()
        try:
            con = sqlite3.connect(db_path)
            con.execute("ALTER TABLE scheduled_scans DROP COLUMN check_in")
            con.commit()
            cols = [r[1] for r in con.execute("PRAGMA table_info(scheduled_scans)")]
            assert "check_in" not in cols
            con.close()

            engine = init_db(db_path)   # reopen the way the app does
            cols = {c["name"] for c in sa_inspect(engine).get_columns("scheduled_scans")}
            assert "check_in" in cols, (
                "HWLC-20: check_in was not added to a pre-existing scheduled_scans table"
            )
            engine.dispose()
        finally:
            os.unlink(db_path)


# ---------------------------------------------------------------------------
# Criterion 3 — scheduled check-ins reuse the manual path, with no second impl
# ---------------------------------------------------------------------------


class TestNoSecondImplementation:
    def test_only_one_check_in_entry_point_exists(self):
        """`run_check_in` must remain the single implementation. A scheduled
        check-in that grew its own copy would drift from HWLC-13's guarantees."""
        import pathlib

        hits = []
        for path in pathlib.Path(".").glob("**/*.py"):
            parts = set(path.parts)
            if parts & {".venv", "build", "node_modules", ".claude", "tests"}:
                continue
            if "def run_check_in" in path.read_text(encoding="utf-8", errors="ignore"):
                hits.append(str(path))
        assert hits == ["run_scan.py"], (
            f"HWLC-20: expected exactly one run_check_in implementation, found {hits}"
        )

    def test_dispatcher_does_not_reimplement_check_in_logic(self):
        """The scheduler's only job is to emit the flag — it must not probe,
        persist or reconcile hardware itself."""
        import pathlib

        src = pathlib.Path("quirk/cli/scheduler_cmd.py").read_text(encoding="utf-8")
        for forbidden in ("check_in_fingerprint_devices",
                          "latest_successful_hardware_devices",
                          "persist_and_reconcile"):
            assert forbidden not in src, (
                f"HWLC-20: scheduler_cmd.py references {forbidden!r} — a scheduled "
                f"check-in must delegate to run_check_in(), not reimplement it"
            )

    def test_check_in_short_circuits_before_scoring_and_reporting(self):
        """run_check_in returns from main() before the scan pipeline, so a
        scheduled check-in cannot produce a scored session or a report."""
        import inspect

        import run_scan

        src = inspect.getsource(run_scan.main)
        assert "sys.exit(run_check_in(" in src, (
            "HWLC-20: main() no longer short-circuits into run_check_in(); a "
            "scheduled check-in could fall through into the scored scan pipeline"
        )
        # The short-circuit must precede the scan pipeline, not sit after it.
        exit_at = src.index("sys.exit(run_check_in(")
        for later in ("scan_run_id: Optional[str] =", "write_scan_checkpoint("):
            if later in src:
                assert exit_at < src.index(later), (
                    f"HWLC-20: the check-in short-circuit now runs AFTER {later!r} — "
                    f"a scheduled check-in would do scored-scan work first"
                )

    def test_run_check_in_never_calls_the_scoring_engine(self):
        import inspect

        import run_scan

        src = inspect.getsource(run_scan.run_check_in)
        for forbidden in ("compute_readiness_score", "write_reports", "build_evidence_summary"):
            assert forbidden not in src, (
                f"HWLC-20/HWLC-13: run_check_in references {forbidden!r} — a check-in "
                f"is advisory-only and must never produce a scored deliverable"
            )
