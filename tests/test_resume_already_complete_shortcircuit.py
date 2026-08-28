"""Phase 171 (RESUME-05, D-01, locked): tests for the resume-already-complete
short-circuit.

Resuming a scan whose `reports` stage checkpoint is already `completed` must
print a message naming the scan and its finish time, exit 0, and write ZERO
new ScanCheckpoint rows. Prior to this fix, `run_scan.py`'s `--resume-scan-id`
block fell all the way through `main()`, re-appending discovery/inventory/
reports checkpoint rows on every resume of an already-complete scan (verified
by manual reproduction against a seeded sqlite DB: row count grew 3 -> 8
mid-scan before this fix; see 171-01-SUMMARY.md).

Test 1-3 exercise the pure `_resume_already_complete_message()` helper.
Test 4-5 are structural (parse the real run_scan.py source) so a passing
mirror test can never mask an unwired call site.
"""
from __future__ import annotations

import ast
import inspect
import re
from datetime import datetime
from pathlib import Path

import run_scan

_REPO_ROOT = Path(__file__).resolve().parent.parent
_RUN_SCAN_PATH = _REPO_ROOT / "run_scan.py"


def test_in_progress_scan_returns_none():
    """No 'reports' stage in completed_stages -> in-progress scan, must never
    short-circuit."""
    result = run_scan._resume_already_complete_message(
        {"discovery", "inventory"}, None, "2026-08-28T00:00:00"
    )
    assert result is None


def test_complete_scan_with_timestamp_returns_message():
    completed_at = datetime(2026, 8, 28, 0, 0, 0)
    scan_run_id = "2026-08-28T00:00:00"
    result = run_scan._resume_already_complete_message(
        {"discovery", "inventory", "reports"}, completed_at, scan_run_id
    )
    assert result is not None
    assert scan_run_id in result
    assert completed_at.isoformat() in result
    assert "already complete" in result
    assert "nothing to resume" in result


def test_complete_scan_with_none_completed_at_does_not_raise():
    scan_run_id = "2026-08-28T00:00:00"
    result = run_scan._resume_already_complete_message(
        {"discovery", "inventory", "reports"}, None, scan_run_id
    )
    assert result is not None
    assert "already complete" in result
    assert "nothing to resume" in result


def test_short_circuit_call_site_precedes_stage_checkpoint_writes():
    """Structural: the _resume_already_complete_message( call site inside
    main() must appear BEFORE the inventory and reports stage checkpoint
    writes in the real run_scan.py source (proves the short-circuit actually
    precedes stage work, not merely exists somewhere in the file)."""
    source = _RUN_SCAN_PATH.read_text()

    call_site_match = re.search(r"(?<!def )_resume_already_complete_message\(", source)
    assert call_site_match is not None, "call site not found in run_scan.py"
    call_site_pos = call_site_match.start()

    inventory_write_match = re.search(
        r'write_scan_checkpoint\(\s*args\.db_path, scan_run_id, "inventory"', source
    )
    assert inventory_write_match is not None, "inventory checkpoint write not found"

    reports_write_match = re.search(
        r'write_scan_checkpoint\(args\.db_path, scan_run_id, "reports"', source
    )
    assert reports_write_match is not None, "reports checkpoint write not found"

    assert call_site_pos < inventory_write_match.start(), (
        "_resume_already_complete_message( call site must precede the "
        "inventory stage checkpoint write"
    )
    assert call_site_pos < reports_write_match.start(), (
        "_resume_already_complete_message( call site must precede the "
        "reports stage checkpoint write"
    )


def test_short_circuit_exits_immediately():
    """Structural: sys.exit(0) must appear within 5 lines of the
    _resume_already_complete_message( call site (proves the short-circuit
    actually exits rather than computing a message and discarding it)."""
    source = _RUN_SCAN_PATH.read_text()
    lines = source.splitlines()

    call_site_line_idx = None
    for idx, line in enumerate(lines):
        if "_resume_already_complete_message(" in line and "def _resume_already_complete_message(" not in line:
            call_site_line_idx = idx
            break
    assert call_site_line_idx is not None, "call site not found in run_scan.py"

    window = lines[call_site_line_idx : call_site_line_idx + 6]
    assert any("sys.exit(0)" in line for line in window), (
        "sys.exit(0) must appear within 5 lines of the "
        "_resume_already_complete_message( call site"
    )


def test_helper_signature_matches_expected_contract():
    """Sanity check the helper is defined at module level with the expected
    parameter names (guards against a signature drift silently breaking the
    call site wiring elsewhere in main())."""
    sig = inspect.signature(run_scan._resume_already_complete_message)
    params = list(sig.parameters.keys())
    assert params == ["completed_stages", "reports_completed_at", "scan_run_id"]
