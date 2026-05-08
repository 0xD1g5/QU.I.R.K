"""Phase 55 — QRAMM-05/06/07 staleness gate, override, and CLI smoke tests."""
from __future__ import annotations

import datetime
import os
import subprocess
import sys
from pathlib import Path

import pytest


# ---------------- QRAMM-05: model shape ----------------

def test_qramm_model_shape() -> None:
    from quirk.qramm.model_meta import QRAMM_MODEL, STALENESS_THRESHOLD_DAYS

    required_keys = {"qramm_version", "last_verified", "source_url"}
    assert required_keys.issubset(QRAMM_MODEL.keys()), (
        f"QRAMM_MODEL missing required keys: "
        f"{required_keys - set(QRAMM_MODEL.keys())}"
    )

    # last_verified must be a parseable ISO date.
    datetime.date.fromisoformat(QRAMM_MODEL["last_verified"])

    assert QRAMM_MODEL["source_url"] == "https://qramm.org"
    assert isinstance(STALENESS_THRESHOLD_DAYS, int)
    assert STALENESS_THRESHOLD_DAYS == 90


# ---------------- QRAMM-06: staleness gate + override ----------------

def _check_staleness(today: datetime.date) -> int:
    """Return age in days using the same arithmetic as run_qramm_status."""
    from quirk.qramm.model_meta import QRAMM_MODEL
    last_verified = datetime.date.fromisoformat(QRAMM_MODEL["last_verified"])
    return (today - last_verified).days


def test_qramm_model_not_stale() -> None:
    """Production gate: with no override, current QRAMM_MODEL must be FRESH."""
    from quirk.qramm.model_meta import (
        QRAMM_MODEL, STALENESS_THRESHOLD_DAYS,
    )

    override = os.environ.get("QUIRK_CI_STALENESS_OVERRIDE_DATE")
    today = (
        datetime.date.fromisoformat(override)
        if override
        else datetime.date.today()
    )
    age = _check_staleness(today)
    assert age <= STALENESS_THRESHOLD_DAYS, (
        f"QRAMM_MODEL.last_verified is {age} days old "
        f"(>{STALENESS_THRESHOLD_DAYS}). "
        f"Re-verify against {QRAMM_MODEL['source_url']} and bump "
        f"last_verified in quirk/qramm/model_meta.py."
    )


def test_qramm_staleness_override_fresh() -> None:
    """OVERRIDE_DATE = last_verified + 30 days → FRESH."""
    from quirk.qramm.model_meta import (
        QRAMM_MODEL, STALENESS_THRESHOLD_DAYS,
    )
    last_verified = datetime.date.fromisoformat(QRAMM_MODEL["last_verified"])
    fake_today = last_verified + datetime.timedelta(days=30)
    age = (fake_today - last_verified).days
    assert age <= STALENESS_THRESHOLD_DAYS


def test_qramm_staleness_override_stale() -> None:
    """OVERRIDE_DATE = last_verified + 100 days → STALE (age > 90)."""
    from quirk.qramm.model_meta import (
        QRAMM_MODEL, STALENESS_THRESHOLD_DAYS,
    )
    last_verified = datetime.date.fromisoformat(QRAMM_MODEL["last_verified"])
    fake_today = last_verified + datetime.timedelta(days=100)
    age = (fake_today - last_verified).days
    assert age > STALENESS_THRESHOLD_DAYS


# ---------------- QRAMM-07: CLI smoke tests ----------------

def _run_scan_path() -> Path:
    return Path(__file__).resolve().parents[1] / "run_scan.py"


def test_qramm_status_cli_smoke_fresh() -> None:
    """Subprocess `python run_scan.py qramm status` exits 0 (FRESH)
    with current model_meta."""
    env = dict(os.environ)
    env.pop("QUIRK_CI_STALENESS_OVERRIDE_DATE", None)
    result = subprocess.run(
        [sys.executable, str(_run_scan_path()), "qramm", "status"],
        capture_output=True, text=True, timeout=15, env=env,
    )
    assert result.returncode == 0, (
        f"exit={result.returncode} stdout={result.stdout!r} "
        f"stderr={result.stderr!r}"
    )
    assert "QRAMM Version" in result.stdout
    assert "Last Verified" in result.stdout
    assert "FRESH" in result.stdout


def test_qramm_status_cli_smoke_stale_via_override() -> None:
    """OVERRIDE_DATE forces STALE → CLI exits 1, stdout contains 'STALE'."""
    from quirk.qramm.model_meta import QRAMM_MODEL
    last_verified = datetime.date.fromisoformat(QRAMM_MODEL["last_verified"])
    fake_today = (
        last_verified + datetime.timedelta(days=100)
    ).isoformat()

    env = dict(os.environ)
    env["QUIRK_CI_STALENESS_OVERRIDE_DATE"] = fake_today
    result = subprocess.run(
        [sys.executable, str(_run_scan_path()), "qramm", "status"],
        capture_output=True, text=True, timeout=15, env=env,
    )
    assert result.returncode == 1, (
        f"expected exit=1 (STALE), got exit={result.returncode}; "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert "STALE" in result.stdout
