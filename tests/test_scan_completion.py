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


# --- run_scan wiring (237-02) ---

import pathlib  # noqa: E402
import re  # noqa: E402

_RUN_SCAN_SRC = (pathlib.Path(__file__).resolve().parents[1] / "run_scan.py").read_text(
    encoding="utf-8"
)


def test_mark_job_scan_run_id_sets_run_id_only(tmp_path):
    from quirk.cli.job_progress import mark_job_scan_run_id
    from quirk.models import ScanJob

    db_path = tmp_path / "q.db"
    db = _session(db_path)
    _job(db, "j1", "running", None)
    db.commit()
    db.close()

    mark_job_scan_run_id(str(db_path), "j1", "run-1")
    db = _session(db_path)
    row = db.get(ScanJob, "j1")
    assert row.scan_run_id == "run-1"
    assert row.status == "running"
    assert row.completed_at is None
    db.close()

    # silent no-ops: missing job id, bad db path
    mark_job_scan_run_id(str(db_path), "nope", "run-2")
    mark_job_scan_run_id(str(tmp_path / "missing" / "x.db"), "j1", "run-3")


def test_first_checkpoint_is_inventory_without_db_path():
    """The nmap-only 'discovery' checkpoint sits under _discovery_batch_loop_ran;
    the inventory checkpoint is unconditional on the scan path, so a default
    (--discovery builtin) scan's earliest checkpoint is 'inventory'."""
    m = re.search(
        r'if _discovery_batch_loop_ran:.*?write_scan_checkpoint\([^)]*"discovery"',
        _RUN_SCAN_SRC, re.S,
    )
    assert m, "discovery checkpoint is no longer gated on the nmap batch loop"
    inv = re.search(
        r'\n( *)(?:if [^\n]*:\n *)?write_scan_checkpoint\(\s*([^,]+), scan_run_id, "inventory"',
        _RUN_SCAN_SRC,
    )
    assert inv, "inventory checkpoint call not found"
    assert inv.group(2).strip() == "_ckpt_db"
    assert "if args.db_path:\n        write_scan_checkpoint(\n            args.db_path" not in _RUN_SCAN_SRC


def test_checkpoint_db_falls_back_to_output_db():
    assert _RUN_SCAN_SRC.count("_ckpt_db = args.db_path or cfg.output.db_path") == 1
    lines = _RUN_SCAN_SRC.splitlines()
    sites = [
        i for i, ln in enumerate(lines)
        if "write_scan_checkpoint(" in ln and not ln.lstrip().startswith(("def ", "#"))
    ]
    assert len(sites) >= 8, sites
    offenders = []
    for i in sites:
        window = "\n".join(lines[max(0, i - 12): i + 2])
        paired_with_cache = "save_cache(" in window  # batch-stage resume marker
        if paired_with_cache:
            continue
        text = "\n".join(lines[i: i + 2])
        guard = "\n".join(lines[max(0, i - 2): i])
        if "write_scan_checkpoint(args.db_path" in text or re.search(
            r"write_scan_checkpoint\(\s*$\n\s*args\.db_path", text, re.M
        ) or "if args.db_path:" in guard:
            offenders.append((i + 1, lines[i].strip()))
    assert not offenders, offenders


def test_job_run_id_stamped_after_resume_override():
    override = _RUN_SCAN_SRC.index("scan_run_id = _resume_scan_id  # override")
    calls = [m.start() for m in re.finditer(r"\bmark_job_scan_run_id\(", _RUN_SCAN_SRC)]
    assert len(calls) == 1, calls
    assert calls[0] > override
    guard = _RUN_SCAN_SRC[max(0, calls[0] - 120): calls[0]]
    assert "if args.job_id and args.db_path:" in guard


# --- routes (237-04) ---

from fastapi.testclient import TestClient  # noqa: E402

from quirk.models import CryptoEndpoint  # noqa: E402

OLD_RUN = "2026-11-09T10:00:00"
NEW_RUN = "2026-11-10T10:00:00"


def _route_client(tmp_path):
    from sqlalchemy.orm import sessionmaker

    from quirk.dashboard.api.app import create_app
    from quirk.dashboard.api.deps import get_db

    eng = init_db(str(tmp_path / "r.db"))
    Maker = sessionmaker(bind=eng, autoflush=False, autocommit=False)

    def _get_db():
        d = Maker()
        try:
            yield d
        finally:
            d.close()

    app = create_app()
    app.dependency_overrides[get_db] = _get_db
    return TestClient(app), Maker


def _ep(db, run, ts, host="h"):
    db.add(CryptoEndpoint(
        host=host, port=80, protocol="HTTP", scanned_at=ts, scan_run_id=run,
    ))


def _seed_old_complete_new_incomplete(Maker):
    db = Maker()
    _ep(db, OLD_RUN, datetime(2026, 11, 9, 10), host="old-host")
    _ep(db, NEW_RUN, datetime(2026, 11, 10, 10), host="new-host")
    _cp(db, OLD_RUN, "reports")
    _cp(db, NEW_RUN, "discovery")
    db.commit()
    db.close()


def test_latest_skips_incomplete_scan(tmp_path):
    client, Maker = _route_client(tmp_path)
    _seed_old_complete_new_incomplete(Maker)
    body = client.get("/api/scan/latest").json()
    hosts = {e["host"] for e in body["findings"]}
    assert hosts == {"old-host"}


def test_latest_explicit_scan_id_loads_incomplete(tmp_path):
    client, Maker = _route_client(tmp_path)
    _seed_old_complete_new_incomplete(Maker)
    body = client.get("/api/scan/latest", params={"scan_id": NEW_RUN}).json()
    assert {e["host"] for e in body["findings"]} == {"new-host"}


def test_latest_404_when_only_incomplete(tmp_path):
    client, Maker = _route_client(tmp_path)
    db = Maker()
    _ep(db, NEW_RUN, datetime(2026, 11, 10, 10))
    _cp(db, NEW_RUN, "discovery")
    db.commit()
    db.close()
    r = client.get("/api/scan/latest")
    assert r.status_code == 404
    assert "DASHBOARD-006" in r.text


def test_latest_legacy_null_run_id_still_served(tmp_path):
    client, Maker = _route_client(tmp_path)
    db = Maker()
    _ep(db, None, datetime(2026, 11, 8, 10), host="legacy-host")
    _ep(db, NEW_RUN, datetime(2026, 11, 10, 10), host="new-host")
    _cp(db, NEW_RUN, "discovery")
    db.commit()
    db.close()
    body = client.get("/api/scan/latest").json()
    assert {e["host"] for e in body["findings"]} == {"legacy-host"}


def test_scans_status_values(tmp_path):
    client, Maker = _route_client(tmp_path)
    run_running = "2026-11-11T10:00:00"
    db = Maker()
    _ep(db, OLD_RUN, datetime(2026, 11, 9, 10))
    _ep(db, NEW_RUN, datetime(2026, 11, 10, 10))
    _ep(db, run_running, datetime(2026, 11, 11, 10))
    _cp(db, OLD_RUN, "reports")
    _cp(db, NEW_RUN, "discovery")
    _cp(db, run_running, "discovery")
    _job(db, "job-1", "running", run_running)
    db.commit()
    db.close()
    rows = {s["scan_id"]: s["status"] for s in client.get("/api/scans").json()}
    assert rows == {OLD_RUN: "complete", NEW_RUN: "incomplete", run_running: "running"}
