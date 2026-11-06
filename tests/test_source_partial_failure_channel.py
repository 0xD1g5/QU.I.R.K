"""235.1 review WR-01 / IN-01: a failed source target must reach the
partial-failure / checkpoint channel and render with a truthful title.

Per-target SOURCE error rows come back in-band from scan_source_targets
(plan 03); they never reach ``error_endpoints``, so before this fix the api
checkpoint read "completed" and the dashboard Scanner Status card was empty.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from types import SimpleNamespace

import pytest

import run_scan
from quirk.engine.findings_evaluator import evaluate_endpoints
from quirk.models import CryptoEndpoint

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _err_row(category="timeout", msg="source scan failed: TimeoutExpired: timed out after 1 s"):
    return CryptoEndpoint(
        host="repoB", port=0, protocol="SOURCE",
        scan_error=msg, scan_error_category=category,
    )


def _ok_row():
    return CryptoEndpoint(
        host="repoA", port=0, protocol="SOURCE", cipher_suite="rule.x",
        service_detail="a.py:1",
    )


def test_in01_failed_source_target_has_truthful_finding_title():
    cfg = SimpleNamespace(scan=SimpleNamespace(ports_tls=[], ports_http=[]))
    findings = evaluate_endpoints(cfg, [_err_row()])
    assert len(findings) == 1
    f = findings[0]
    assert f["title"] == "Source scan incomplete for repoB"
    assert "Informational protocol observation" not in f["title"]
    assert "does not by itself indicate a defect" not in f["description"]
    assert f["severity"] == "INFO"
    assert f["detail"].startswith("source scan failed")
    # Visible on findings tables: NOT a score-neutral hidden coverage_gap row.
    assert f.get("category") != "coverage_gap"


def test_wr01_helper_turns_in_band_error_rows_into_partial_failures():
    pf = run_scan._source_row_partial_failures("api", [_ok_row(), _err_row()])
    assert pf == [{
        "stage": "api",
        "scanner": "source_scanner",
        "error_category": "timeout",
        "error_message": "source scan failed: TimeoutExpired: timed out after 1 s",
        "endpoint_count": 0,
    }]
    assert run_scan._source_row_partial_failures("api", [_ok_row()]) == []
    assert run_scan._source_row_partial_failures("api", []) == []


@pytest.fixture(scope="module")
def failed_target_scan(tmp_path_factory):
    """In-process scan with semgrep 'present' and scan_source_targets returning
    one finding row plus one timeout error row (the plan-03 in-band shape)."""
    root = tmp_path_factory.mktemp("wr01_scan")
    src = root / "src"
    src.mkdir()
    out = root / "out"
    db = root / "quirk.db"
    text = open(os.path.join(_REPO, "quirk", "config_template.yaml"), encoding="utf-8").read()
    text = text.replace('directory: "./quirk-output"', f'directory: "{out}"')
    text = text.replace('db_path: "./quirk-output/quirk.db"', f'db_path: "{db}"')
    text = text.replace("  # source_targets: []", f"  source_targets: ['{src}']")
    cfg_path = root / "config.yaml"
    cfg_path.write_text(text, encoding="utf-8")

    mp = pytest.MonkeyPatch()
    try:
        mp.chdir(root)
        real_which = run_scan.shutil.which
        mp.setattr(
            run_scan.shutil, "which",
            lambda name, *a, **k: "/fake/bin/semgrep" if name == "semgrep" else real_which(name, *a, **k),
        )
        mp.setattr(run_scan, "scan_source_targets", lambda *a, **k: [_ok_row(), _err_row()])
        mp.setattr(sys, "argv", ["run_scan.py", "--config", str(cfg_path), "--db-path", str(db)])
        run_scan.main()
    finally:
        mp.undo()

    from quirk.db import get_session
    from quirk.models import ScanCheckpoint

    with get_session(str(db)) as session:
        row = session.query(ScanCheckpoint).filter_by(stage="api").one()
        return {
            "status": row.status,
            "partial_failure": row.partial_failure,
            "summary": json.loads(row.error_summary) if row.error_summary else None,
        }


@pytest.mark.slow
def test_wr01_e2e_api_checkpoint_records_failed_source_target(failed_target_scan):
    c = failed_target_scan
    assert c["status"] == "partial"
    assert c["partial_failure"] is True
    entries = [e for e in c["summary"] if e["scanner"] == "source_scanner"]
    assert len(entries) == 1, c["summary"]
    assert entries[0]["stage"] == "api"
    assert entries[0]["error_category"] == "timeout"
