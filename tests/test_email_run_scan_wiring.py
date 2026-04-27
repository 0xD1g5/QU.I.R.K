"""Structural tests for Phase 32 Plan 04 Task 2 — run_scan.py wiring.

These tests verify the scanner+findings are wired into run_scan.py without
requiring a live scan. Behavior validated:

- Imports for scan_email_targets and evaluate_email_endpoints exist.
- email_endpoints aggregation list is initialized and consumed.
- The phase timer is named "email_scanning".
- The cfg.connectors.enable_email gate is present.
- Findings merge happens (evaluate_email_endpoints called).
- Aggregation includes email_endpoints in the master endpoints tuple.
"""
from pathlib import Path

import pytest

RUN_SCAN = Path(__file__).resolve().parent.parent / "run_scan.py"


@pytest.fixture(scope="module")
def src() -> str:
    assert RUN_SCAN.exists(), f"run_scan.py not found at {RUN_SCAN}"
    return RUN_SCAN.read_text(encoding="utf-8")


def test_run_scan_imports_email_scanner(src: str):
    assert "from quirk.scanner.email_scanner import scan_email_targets" in src


def test_run_scan_imports_evaluate_email_endpoints(src: str):
    assert "evaluate_email_endpoints" in src
    assert src.count("evaluate_email_endpoints") >= 2, "import + call expected"


def test_run_scan_email_phase_timer_label(src: str):
    assert '"email_scanning"' in src


def test_run_scan_gates_on_enable_email(src: str):
    assert "cfg.connectors.enable_email" in src


def test_run_scan_aggregates_email_endpoints(src: str):
    # Must initialize, populate, and aggregate
    assert src.count("email_endpoints") >= 3, (
        "expected init + assignment + aggregation references"
    )
    # Aggregation block: '+ email_endpoints' inside the `endpoints = (...)` tuple
    assert "+ email_endpoints" in src or "email_endpoints +" in src


def test_run_scan_call_uses_session_start_and_logger(src: str):
    # The call should pass logger and session_start, matching scanner contract
    assert "scan_email_targets(" in src
    # Find substring around the call
    idx = src.index("scan_email_targets(")
    # Look up to the next 600 chars
    block = src[idx:idx + 600]
    assert "logger=logger" in block
    assert "session_start=session_start" in block


def test_run_scan_compileall(tmp_path):
    import compileall
    ok = compileall.compile_file(str(RUN_SCAN), quiet=1)
    assert ok, "run_scan.py failed to compile"
