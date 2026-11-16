"""Phase 237 COUNT-06 (D-07/D-09/D-14/D-15): one definition of scan completeness."""
from __future__ import annotations

import subprocess
import sys
from datetime import datetime

from quirk.db import init_db


def _session(db_path):
    from sqlalchemy.orm import sessionmaker

    return sessionmaker(bind=init_db(str(db_path)))()


def _cp(db, run_id, stage, status="completed"):
    from quirk.models import ScanCheckpoint

    db.add(ScanCheckpoint(
        scan_run_id=run_id, stage=stage, status=status,
        completed_at=datetime(2026, 11, 16),
    ))


def _job(db, job_id, status, run_id):
    from quirk.models import ScanJob

    db.add(ScanJob(
        job_id=job_id, status=status, target="t", profile="quick",
        calibration="balanced", scan_run_id=run_id,
    ))


# --- helper (237-02) ---

def test_reports_completed_is_complete(tmp_path):
    from quirk.intelligence.scan_completion import (
        incomplete_scan_run_ids, running_scan_run_ids, session_status,
    )

    db = _session(tmp_path / "q.db")
    _cp(db, "r1", "inventory")
    _cp(db, "r1", "reports")
    db.commit()
    inc, run = incomplete_scan_run_ids(db), running_scan_run_ids(db)
    assert session_status("r1", inc, run) == "complete"


def test_checkpoints_without_reports_is_incomplete(tmp_path):
    from quirk.intelligence.scan_completion import (
        incomplete_scan_run_ids, running_scan_run_ids, session_status,
    )

    db = _session(tmp_path / "q.db")
    _cp(db, "r2", "inventory")
    db.commit()
    inc, run = incomplete_scan_run_ids(db), running_scan_run_ids(db)
    assert inc == {"r2"}
    assert session_status("r2", inc, run) == "incomplete"


def test_active_job_makes_it_running(tmp_path):
    from quirk.intelligence.scan_completion import (
        incomplete_scan_run_ids, running_scan_run_ids, session_status,
    )

    db = _session(tmp_path / "q.db")
    _cp(db, "r3", "inventory")
    _cp(db, "r4", "inventory")
    _job(db, "j3", "running", "r3")
    _job(db, "j4", "queued", "r4")
    _job(db, "j5", "failed", "r5")
    _job(db, "j6", "running", None)
    db.commit()
    inc, run = incomplete_scan_run_ids(db), running_scan_run_ids(db)
    assert run == {"r3", "r4"}
    assert session_status("r3", inc, run) == "running"
    assert session_status("r4", inc, run) == "running"


def test_no_checkpoint_rows_is_complete(tmp_path):
    from quirk.intelligence.scan_completion import (
        incomplete_scan_run_ids, running_scan_run_ids, session_status,
    )

    db = _session(tmp_path / "q.db")
    _cp(db, "other", "inventory")
    db.commit()
    inc, run = incomplete_scan_run_ids(db), running_scan_run_ids(db)
    assert session_status("legacy", inc, run) == "complete"


def test_empty_run_id_is_complete():
    from quirk.intelligence.scan_completion import session_status

    assert session_status(None, {"x"}, {"x"}) == "complete"
    assert session_status("", {"x"}, {"x"}) == "complete"


def test_agrees_with_list_resumable(tmp_path, capsys):
    import argparse
    import run_scan
    from quirk.intelligence.scan_completion import incomplete_scan_run_ids

    db_path = tmp_path / "q.db"
    db = _session(db_path)
    _cp(db, "done", "inventory")
    _cp(db, "done", "reports")
    _cp(db, "partial-a", "inventory")
    _cp(db, "partial-b", "tls")
    _cp(db, "failed-reports", "reports", status="failed")
    db.commit()
    inc = incomplete_scan_run_ids(db)
    db.close()
    assert inc == {"partial-a", "partial-b", "failed-reports"}
    run_scan._handle_list_resumable(argparse.Namespace(db_path=str(db_path)))
    out = capsys.readouterr().out
    for rid in inc:
        assert rid in out
    assert "done" not in out.replace("Done", "")


def test_import_hygiene_no_fastapi_or_pydantic():
    code = (
        "import sys, quirk.intelligence.scan_completion; "
        "bad = [m for m in ('fastapi', 'pydantic') if m in sys.modules]; "
        "assert not bad, bad; print('import cost OK')"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True, text=True, timeout=120, close_fds=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
