"""Phase 70 BLOCK-08/CR-07: tests for `_SAFE_COL_TYPE_RE` allowlist + ValueError
guard in the four `_ensure_*_columns` helpers that interpolate a `col_type`
fragment from a module-level DDL dict.

Coverage:
    - Parametrized accept/reject matrix on `_SAFE_COL_TYPE_RE` (regex coverage).
    - Poisoned-dict tests on each of the four guarded helpers — confirming a
      bad `col_type` raises ValueError before any DDL is interpolated.
    - Regression test that `init_db()` (which calls every helper) still works
      against the real DDL values now flowing through the new guard.
"""
from __future__ import annotations

from pathlib import Path

import pytest

import quirk.db as quirk_db
from quirk.db import (
    _SAFE_COL_TYPE_RE,
    _ensure_phase41_columns,
    _ensure_phase46_columns,
    _ensure_phase54_qramm_columns,
    _ensure_v43_columns,
    init_db,
)


# ---------------------------------------------------------------------------
# Regex matrix
# ---------------------------------------------------------------------------

_ACCEPT_VALUES = [
    "TEXT",
    "INTEGER",
    "REAL",
    "BOOLEAN",
    "DATETIME",
    "VARCHAR(16)",
    "VARCHAR(32)",
    "VARCHAR(9999)",
]

_REJECT_VALUES = [
    "TEXT; DROP TABLE x",
    "VARCHAR(99999)",
    "varchar(16)",
    "",
    "TEXT NOT NULL",
    "INTEGER PRIMARY KEY",
    "BLOB",
    "VARCHAR()",
]


@pytest.mark.parametrize("value", _ACCEPT_VALUES)
def test_safe_col_type_re_accepts_real_values(value: str) -> None:
    """Every real DDL fragment in current quirk/db.py dicts must match."""
    assert _SAFE_COL_TYPE_RE.match(value) is not None, (
        f"Allowlist regex unexpectedly rejected real value: {value!r}"
    )


@pytest.mark.parametrize("value", _REJECT_VALUES)
def test_safe_col_type_re_rejects_unsafe_values(value: str) -> None:
    """Injection canaries and out-of-band values must NOT match."""
    assert _SAFE_COL_TYPE_RE.match(value) is None, (
        f"Allowlist regex unexpectedly accepted unsafe value: {value!r}"
    )


# ---------------------------------------------------------------------------
# Poisoned-dict tests — one per guarded helper.
# Pattern: spin up a fresh DB via init_db (so the existing helpers complete
# before we poison), then monkeypatch a bad `col_type` into the relevant
# DDL dict and re-invoke the helper. The new guard must raise ValueError.
# ---------------------------------------------------------------------------


def test_v43_columns_rejects_poisoned_col_type(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = init_db(str(tmp_path / "poison_v43.db"))
    monkeypatch.setitem(
        quirk_db._V43_COLUMN_DDLS, "evil_col", "TEXT; DROP TABLE x"
    )
    with pytest.raises(ValueError, match="Unsafe column type"):
        _ensure_v43_columns(engine)


def test_phase41_columns_rejects_poisoned_col_type(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = init_db(str(tmp_path / "poison_p41.db"))
    monkeypatch.setitem(
        quirk_db._PHASE41_COLUMN_DDLS, "evil_col", "TEXT; DROP TABLE x"
    )
    with pytest.raises(ValueError, match="Unsafe column type"):
        _ensure_phase41_columns(engine)


def test_phase46_columns_rejects_poisoned_col_type(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = init_db(str(tmp_path / "poison_p46.db"))
    monkeypatch.setitem(
        quirk_db._PHASE46_COLUMN_DDLS, "evil_col", "TEXT; DROP TABLE x"
    )
    with pytest.raises(ValueError, match="Unsafe column type"):
        _ensure_phase46_columns(engine)


def test_phase54_qramm_columns_rejects_poisoned_col_type(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = init_db(str(tmp_path / "poison_p54.db"))
    monkeypatch.setitem(
        quirk_db._PHASE54_QRAMM_ANSWER_DDLS,
        "evil_col",
        "TEXT; DROP TABLE x",
    )
    with pytest.raises(ValueError, match="Unsafe column type"):
        _ensure_phase54_qramm_columns(engine)


# ---------------------------------------------------------------------------
# Regression: real values still pass after the guard lands.
# ---------------------------------------------------------------------------


def test_all_guarded_helpers_accept_real_values(tmp_path: Path) -> None:
    """init_db() must complete cleanly with every real `col_type` flowing
    through the new `_SAFE_COL_TYPE_RE` guard."""
    db_path = tmp_path / "real.db"
    engine = init_db(str(db_path))
    # Re-run the guarded helpers explicitly to exercise the guard a second
    # time on real values (idempotent).
    _ensure_v43_columns(engine)
    _ensure_phase41_columns(engine)
    _ensure_phase46_columns(engine)
    _ensure_phase54_qramm_columns(engine)
