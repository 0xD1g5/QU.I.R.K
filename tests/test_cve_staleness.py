"""Phase 142 (CVE-02) — CVE snapshot staleness gate, override, and CLI smoke tests.

Mirrors tests/test_qramm_staleness.py 1:1 with cve names substituted (D-09/D-10/D-12).
This file fails RED until quirk.scanner.hw_cve exists (Wave 1).
"""
from __future__ import annotations

import datetime
import os
import subprocess
import sys
from pathlib import Path

import pytest


# ---------------- CVE-02: table shape ----------------

def test_cve_table_meta_shape() -> None:
    from quirk.scanner.hw_cve import CVE_TABLE_META, STALENESS_THRESHOLD_DAYS

    required_keys = {"last_verified", "source"}
    assert required_keys.issubset(CVE_TABLE_META.keys()), (
        f"CVE_TABLE_META missing required keys: "
        f"{required_keys - set(CVE_TABLE_META.keys())}"
    )

    # last_verified must be a parseable ISO date.
    datetime.date.fromisoformat(CVE_TABLE_META["last_verified"])

    assert isinstance(STALENESS_THRESHOLD_DAYS, int)
    assert STALENESS_THRESHOLD_DAYS == 30  # D-09: shorter than QRAMM's 90


# ---------------- CVE-02: staleness gate + boundary math ----------------

def _check_staleness(today: datetime.date) -> int:
    from quirk.scanner.hw_cve import CVE_TABLE_META
    last_verified = datetime.date.fromisoformat(CVE_TABLE_META["last_verified"])
    return (today - last_verified).days


def test_cve_table_not_stale() -> None:
    """Production gate: with no override, current CVE_TABLE_META must be FRESH."""
    from quirk.scanner.hw_cve import CVE_TABLE_META, STALENESS_THRESHOLD_DAYS

    override = os.environ.get("QUIRK_CI_STALENESS_OVERRIDE_DATE")
    today = (
        datetime.date.fromisoformat(override)
        if override
        else datetime.date.today()
    )
    age = _check_staleness(today)
    assert age <= STALENESS_THRESHOLD_DAYS, (
        f"CVE_TABLE_META.last_verified is {age} days old "
        f"(>{STALENESS_THRESHOLD_DAYS}). Re-verify against NVD and bump "
        f"last_verified in quirk/scanner/hw_cve.py."
    )


def test_cve_staleness_boundary_30_days_not_stale() -> None:
    """Exactly 30 days old is NOT stale (strict `>`)."""
    from quirk.scanner.hw_cve import (
        CVE_TABLE_META, STALENESS_THRESHOLD_DAYS, is_cve_table_stale,
    )
    last_verified = datetime.date.fromisoformat(CVE_TABLE_META["last_verified"])
    fake_today = last_verified + datetime.timedelta(days=STALENESS_THRESHOLD_DAYS)
    assert is_cve_table_stale(today=fake_today) is False


def test_cve_staleness_boundary_31_days_is_stale() -> None:
    """31 days old IS stale."""
    from quirk.scanner.hw_cve import (
        CVE_TABLE_META, STALENESS_THRESHOLD_DAYS, is_cve_table_stale,
    )
    last_verified = datetime.date.fromisoformat(CVE_TABLE_META["last_verified"])
    fake_today = last_verified + datetime.timedelta(days=STALENESS_THRESHOLD_DAYS + 1)
    assert is_cve_table_stale(today=fake_today) is True


# ---------------- CVE-02/D-10: CLI smoke tests ----------------

def _run_scan_path() -> Path:
    return Path(__file__).resolve().parents[1] / "run_scan.py"


def test_cve_status_cli_smoke_fresh() -> None:
    """Subprocess `python run_scan.py cve status` exits 0 (FRESH) with the
    current CVE_TABLE_META, when not overridden."""
    env = dict(os.environ)
    env.pop("QUIRK_CI_STALENESS_OVERRIDE_DATE", None)
    result = subprocess.run(
        [sys.executable, str(_run_scan_path()), "cve", "status"],
        capture_output=True, text=True, timeout=15, env=env,
    )
    assert result.returncode == 0, (
        f"exit={result.returncode} stdout={result.stdout!r} "
        f"stderr={result.stderr!r}"
    )
    assert "FRESH" in result.stdout


def test_cve_status_cli_smoke_stale_via_override() -> None:
    """OVERRIDE_DATE forces STALE -> CLI exits 1, stdout contains 'STALE'."""
    from quirk.scanner.hw_cve import CVE_TABLE_META
    last_verified = datetime.date.fromisoformat(CVE_TABLE_META["last_verified"])
    fake_today = (
        last_verified + datetime.timedelta(days=100)
    ).isoformat()

    env = dict(os.environ)
    env["QUIRK_CI_STALENESS_OVERRIDE_DATE"] = fake_today
    result = subprocess.run(
        [sys.executable, str(_run_scan_path()), "cve", "status"],
        capture_output=True, text=True, timeout=15, env=env,
    )
    assert result.returncode == 1, (
        f"expected exit=1 (STALE), got exit={result.returncode}; "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert "STALE" in result.stdout
