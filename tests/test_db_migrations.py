"""Phase 70 BLOCK-08/CR-07: tests for `_SAFE_COL_TYPE_RE` allowlist + ValueError
guard in the column-adding migration path.

Phase 77 D-21 update: the four per-feature helpers (_ensure_v43_columns,
_ensure_phase41_columns, _ensure_phase46_columns, _ensure_phase54_qramm_columns)
were consolidated into a single generic `_ensure_columns(engine, table, expected)`
helper. The allowlist guard semantics are unchanged — these tests now exercise
the same guard via the new entry point and the migrated tuple constants.

Coverage:
    - Parametrized accept/reject matrix on `_SAFE_COL_TYPE_RE` (regex coverage).
    - Poisoned-tuple tests on the generic helper — confirming a bad `col_type`
      raises ValueError before any DDL is interpolated, exercised once per
      original migration feature for parity.
    - Regression test that `init_db()` still works against the real DDL values
      now flowing through the generic guard.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from quirk.db import (
    _BROKER_COLUMNS,
    _EMAIL_COLUMNS,
    _GCP_COLUMNS,
    _IDENTITY_COLUMNS,
    _PHASE41_COLUMNS,
    _PHASE46_COLUMNS,
    _PHASE54_QRAMM_ANSWER_COLUMNS,
    _SAFE_COL_TYPE_RE,
    _V43_COLUMNS,
    _ensure_columns,
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
# Poisoned-tuple tests — one per original migration feature.
# Pattern: spin up a fresh DB via init_db (so the existing migrations complete
# before we poison), then invoke `_ensure_columns` with a poisoned (col, ddl)
# tuple. The guard must raise ValueError before any DDL is interpolated.
# (Phase 77 D-21: the 4 prior dict-based helpers collapsed into a single
# generic helper; the poisoned-dict pattern becomes a poisoned-tuple pattern.)
# ---------------------------------------------------------------------------


_POISON = (("evil_col", "TEXT; DROP TABLE x"),)


def test_v43_path_rejects_poisoned_col_type(tmp_path: Path) -> None:
    engine = init_db(str(tmp_path / "poison_v43.db"))
    with pytest.raises(ValueError, match="Unsafe column type"):
        _ensure_columns(engine, "crypto_endpoints", _POISON)


def test_phase41_path_rejects_poisoned_col_type(tmp_path: Path) -> None:
    engine = init_db(str(tmp_path / "poison_p41.db"))
    with pytest.raises(ValueError, match="Unsafe column type"):
        _ensure_columns(engine, "crypto_endpoints", _POISON)


def test_phase46_path_rejects_poisoned_col_type(tmp_path: Path) -> None:
    engine = init_db(str(tmp_path / "poison_p46.db"))
    with pytest.raises(ValueError, match="Unsafe column type"):
        _ensure_columns(engine, "crypto_endpoints", _POISON)


def test_phase54_qramm_path_rejects_poisoned_col_type(tmp_path: Path) -> None:
    engine = init_db(str(tmp_path / "poison_p54.db"))
    with pytest.raises(ValueError, match="Unsafe column type"):
        _ensure_columns(engine, "qramm_answers", _POISON)


# ---------------------------------------------------------------------------
# Regression: real values still pass after the guard lands.
# ---------------------------------------------------------------------------


def test_all_guarded_paths_accept_real_values(tmp_path: Path) -> None:
    """init_db() must complete cleanly, and re-running every consolidated
    migration tuple through the generic guard must remain idempotent."""
    db_path = tmp_path / "real.db"
    engine = init_db(str(db_path))
    # Re-run the consolidated migrations explicitly to exercise the generic
    # guard a second time on real values (idempotent).
    _ensure_columns(engine, "crypto_endpoints", _IDENTITY_COLUMNS)
    _ensure_columns(engine, "crypto_endpoints", _GCP_COLUMNS)
    _ensure_columns(engine, "crypto_endpoints", _V43_COLUMNS)
    _ensure_columns(engine, "crypto_endpoints", _EMAIL_COLUMNS)
    _ensure_columns(engine, "crypto_endpoints", _BROKER_COLUMNS)
    _ensure_columns(engine, "crypto_endpoints", _PHASE41_COLUMNS)
    _ensure_columns(engine, "crypto_endpoints", _PHASE46_COLUMNS)
    _ensure_columns(engine, "qramm_answers", _PHASE54_QRAMM_ANSWER_COLUMNS)
