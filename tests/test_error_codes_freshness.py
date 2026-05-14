"""Phase 68 D-03 gate: docs/error-codes.md must match quirk errors --dump-md.

Mirrors tests/test_compliance_freshness.py — both prevent silent drift between
a generator and its committed output.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ERROR_CODES_MD = REPO_ROOT / "docs" / "error-codes.md"


def test_error_codes_md_exists():
    assert ERROR_CODES_MD.exists(), (
        "docs/error-codes.md is missing. Generate with: "
        "python run_scan.py errors --dump-md > docs/error-codes.md"
    )


def test_error_codes_md_is_current():
    """docs/error-codes.md must match `quirk errors --dump-md` output."""
    result = subprocess.run(
        [sys.executable, "run_scan.py", "errors", "--dump-md"],
        capture_output=True, text=True, cwd=REPO_ROOT, timeout=15,
    )
    assert result.returncode == 0, (
        f"quirk errors --dump-md failed: stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    generated = result.stdout.rstrip("\n")
    current = ERROR_CODES_MD.read_text().rstrip("\n")
    assert generated == current, (
        "docs/error-codes.md is stale. Regenerate with: "
        "python run_scan.py errors --dump-md > docs/error-codes.md"
    )


def test_error_codes_md_contains_install_section():
    text = ERROR_CODES_MD.read_text()
    assert "## INSTALL" in text
    assert "| QRK-INSTALL-001 |" in text
    assert "| QRK-INSTALL-004 |" in text
    assert "lsof -i :8512" in text
