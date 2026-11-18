"""A trust-gate refusal on the CLI ends with exit code 2, the refusal text on
stderr and no traceback, and marks a dashboard-launched job row failed."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from quirk.models import Base, ScanJob
from quirk.util import target_trust as _tt

_ROOT = Path(__file__).resolve().parent.parent


def _write_config(tmp_path, trusted, fqdns):
    cfg = {
        "assessment": {
            "name": "t", "data_classification": "internal",
            "report_owner": "t", "timezone": "UTC",
        },
        "scan": {"concurrency": 1, "ports_tls": [443]},
        "targets": {"fqdns": fqdns, "cidrs": []},
        "output": {
            "directory": str(tmp_path / "out"),
            "db_path": str(tmp_path / "q.db"),
        },
        "security": {"trusted_targets": trusted},
    }
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(cfg))
    return path


def _run(config, *extra):
    return subprocess.run(
        [sys.executable, "run_scan.py", "--config", str(config), "--quiet", *extra],
        cwd=_ROOT, capture_output=True, text=True, timeout=120,
    )


def _job_db(tmp_path):
    db_file = str(tmp_path / "jobs.db")
    engine = create_engine(f"sqlite:///{db_file}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    with Session() as db:
        db.add(ScanJob(
            job_id="j-1", status="running", target="a.example",
            profile="standard", calibration="balanced", enable_nmap=False,
        ))
        db.commit()
    return db_file, Session


def test_non_string_entry_refusal_exits_2_without_traceback(tmp_path):
    proc = _run(_write_config(tmp_path, False, ["a.example"]))
    expected = _tt.refusal_message(
        _tt.ValidationResult(False, _tt.RC_INVALID_ALLOWLIST_ENTRY, "")
    )
    assert proc.returncode == 2, proc.stderr
    assert expected in proc.stderr
    assert "Traceback" not in proc.stderr
    assert not (tmp_path / "out").exists() or not any((tmp_path / "out").iterdir())


def test_not_in_allowlist_refusal_exits_2_without_traceback(tmp_path):
    cfg = _write_config(tmp_path, ["192.0.2.0/24"], ["198.51.100.7"])
    proc = _run(cfg)
    assert proc.returncode == 2, proc.stderr
    assert "not in the trusted-targets allowlist" in proc.stderr
    assert "Traceback" not in proc.stderr


def test_refusal_marks_the_job_row_failed(tmp_path):
    db_file, Session = _job_db(tmp_path)
    cfg = _write_config(tmp_path, False, ["a.example"])
    proc = _run(cfg, "--db-path", db_file, "--job-id", "j-1")
    assert proc.returncode == 2, proc.stderr
    assert "Traceback" not in proc.stderr
    with Session() as db:
        row = db.get(ScanJob, "j-1")
        assert row.status == "failed"
        assert "trusted_targets" in (row.error_message or "")
