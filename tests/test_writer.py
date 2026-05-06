"""Phase 52 DEBT-03: Tests for quirk.reports.writer run-stats fields."""
from __future__ import annotations
import json


def _make_minimal_cfg(output_dir: str):
    """Return a minimal cfg-like namespace matching write_reports expectations."""
    from types import SimpleNamespace
    return SimpleNamespace(
        output=SimpleNamespace(directory=output_dir),
        assessment=SimpleNamespace(
            name="Test Org",
            report_owner="Test Owner",
            data_classification="CONFIDENTIAL",
            timezone="UTC",
        ),
        intelligence=SimpleNamespace(
            profile="balanced",
            calibration_overrides=None,
        ),
    )


def test_run_stats_ports_and_hosts_scanned(tmp_path):
    """DEBT-03: run-stats JSON must include ports_scanned + hosts_scanned (top-level or nested under 'counts')."""
    from quirk.reports.writer import write_reports
    # Build a minimal run_stats dict mirroring run_scan.py:529-536 shape
    run_stats = {
        "counts": {
            "targets_total": 2,
            "tls_candidates": 2,
            "ssh_candidates": 0,
            "inventory_other": 0,
            "hosts_scanned": ["10.0.0.1", "10.0.0.2"],
            "ports_scanned": [443, 8443],
        },
    }
    cfg = _make_minimal_cfg(str(tmp_path))
    write_reports(cfg=cfg, endpoints=[], findings=[], run_stats=run_stats)
    # Locate run-stats JSON
    matches = list(tmp_path.glob("run-stats-*.json"))
    assert matches, f"no run-stats-*.json produced in {tmp_path}"
    data = json.loads(matches[0].read_text())
    # Accept either top-level or nested-under-'counts' placement (D-16 leaves both legal)
    has_top = "ports_scanned" in data and "hosts_scanned" in data
    has_nested = (
        isinstance(data.get("counts"), dict)
        and "ports_scanned" in data["counts"]
        and "hosts_scanned" in data["counts"]
    )
    assert has_top or has_nested, (
        f"run-stats JSON missing ports_scanned/hosts_scanned at top level OR under 'counts'; "
        f"keys present: top-level={list(data.keys())}, counts={list(data.get('counts', {}).keys()) if isinstance(data.get('counts'), dict) else 'N/A'}"
    )
