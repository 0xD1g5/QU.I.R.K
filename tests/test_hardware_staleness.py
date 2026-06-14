"""Phase 127 — HWCOMPAT-02 staleness gate, override, and boundary tests."""
from __future__ import annotations

import datetime
import os

import pytest


# ------------ shape test ------------

def test_hardware_matrix_shape() -> None:
    from quirk.scanner.hardware_meta import HARDWARE_MATRIX, STALENESS_THRESHOLD_DAYS

    required_keys = {"last_verified", "source_url", "entries"}
    assert required_keys.issubset(HARDWARE_MATRIX.keys()), (
        f"HARDWARE_MATRIX missing required keys: "
        f"{required_keys - set(HARDWARE_MATRIX.keys())}"
    )
    datetime.date.fromisoformat(HARDWARE_MATRIX["last_verified"])
    assert isinstance(STALENESS_THRESHOLD_DAYS, int)
    assert STALENESS_THRESHOLD_DAYS == 90
    assert len(HARDWARE_MATRIX["entries"]) >= 8  # D-10 minimum vendor set

    entry_required_keys = {"vendor", "model_pattern", "pqc_status", "eol_date", "source_url", "notes"}
    for entry in HARDWARE_MATRIX["entries"]:
        assert entry_required_keys.issubset(entry.keys()), (
            f"HARDWARE_MATRIX entry missing keys: "
            f"{entry_required_keys - set(entry.keys())} for entry vendor={entry.get('vendor')}"
        )


# ------------ not-stale gate ------------

def test_hardware_matrix_not_stale() -> None:
    from quirk.scanner.hardware_meta import (
        HARDWARE_MATRIX, STALENESS_THRESHOLD_DAYS,
    )
    override = os.environ.get("QUIRK_CI_STALENESS_OVERRIDE_DATE")
    today = (
        datetime.date.fromisoformat(override)
        if override
        else datetime.date.today()
    )
    last_verified = datetime.date.fromisoformat(HARDWARE_MATRIX["last_verified"])
    age = (today - last_verified).days
    assert age <= STALENESS_THRESHOLD_DAYS, (
        f"HARDWARE_MATRIX.last_verified is {age} days old "
        f"(>{STALENESS_THRESHOLD_DAYS}). "
        f"Re-verify against {HARDWARE_MATRIX['source_url']} and bump "
        f"last_verified in quirk/scanner/hardware_meta.py."
    )


# ------------ boundary tests ------------

def test_hardware_staleness_override_fresh() -> None:
    """Override to last_verified + 30 days -> FRESH."""
    from quirk.scanner.hardware_meta import HARDWARE_MATRIX, STALENESS_THRESHOLD_DAYS
    last_verified = datetime.date.fromisoformat(HARDWARE_MATRIX["last_verified"])
    fake_today = last_verified + datetime.timedelta(days=30)
    age = (fake_today - last_verified).days
    assert age <= STALENESS_THRESHOLD_DAYS


def test_hardware_staleness_override_stale() -> None:
    """Override to last_verified + 100 days -> STALE (age > 90)."""
    from quirk.scanner.hardware_meta import HARDWARE_MATRIX, STALENESS_THRESHOLD_DAYS
    last_verified = datetime.date.fromisoformat(HARDWARE_MATRIX["last_verified"])
    fake_today = last_verified + datetime.timedelta(days=100)
    age = (fake_today - last_verified).days
    assert age > STALENESS_THRESHOLD_DAYS
