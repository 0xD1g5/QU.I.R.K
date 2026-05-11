"""Regression tests for CR-08 — init_db() idempotency contract.

Verifies that:
- Calling init_db() twice on a fresh DB completes without error and leaves schema unchanged
- All _ensure_* helpers are idempotent under repeated invocation
- init_db() brings a partially-migrated DB to the full schema
"""
from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy import inspect as sa_inspect

from quirk.db import init_db
from quirk.models import Base
import quirk.db as quirk_db_module


def _column_snapshot(engine) -> dict:
    """Return a dict mapping table_name -> sorted list of column names."""
    insp = sa_inspect(engine)
    return {
        t: sorted(c["name"] for c in insp.get_columns(t))
        for t in insp.get_table_names()
    }


def test_init_db_twice_on_fresh_db(tmp_path: Path) -> None:
    """Calling init_db() twice must not raise and must leave schema unchanged."""
    db = tmp_path / "fresh.db"
    engine1 = init_db(str(db))
    snap1 = _column_snapshot(engine1)
    engine2 = init_db(str(db))   # second call must not raise
    snap2 = _column_snapshot(engine2)
    assert snap1 == snap2, f"Schema drift after re-init: {snap1} vs {snap2}"


def test_all_ensure_functions_idempotent(tmp_path: Path) -> None:
    """Every _ensure_* function in quirk.db must be safe to call multiple times."""
    db = tmp_path / "ensure.db"
    engine = init_db(str(db))
    ensure_funcs = [
        getattr(quirk_db_module, name)
        for name in dir(quirk_db_module)
        if name.startswith("_ensure_") and callable(getattr(quirk_db_module, name))
        # Exclude _ensure_parent_dir — it takes a path string, not an engine
        and name != "_ensure_parent_dir"
    ]
    assert len(ensure_funcs) >= 5, (
        f"Expected at least 5 _ensure_* helpers, found {len(ensure_funcs)}: "
        f"{[f.__name__ for f in ensure_funcs]}"
    )
    for fn in ensure_funcs:
        fn(engine)  # second invocation
        fn(engine)  # third invocation
    # If we got here, every helper is idempotent under repeat invocation.


def test_init_db_after_simulated_partial_migration(tmp_path: Path) -> None:
    """init_db() must bring a partially-migrated DB to the full schema."""
    db_partial = tmp_path / "partial.db"
    db_full = tmp_path / "full.db"

    # Full path: normal init_db
    engine_full = init_db(str(db_full))
    full_snap = _column_snapshot(engine_full)

    # Partial path: create only base tables (no _ensure_* helpers), then call init_db
    partial_engine = create_engine(f"sqlite:///{db_partial}", future=True)
    Base.metadata.create_all(partial_engine)
    partial_engine.dispose()

    # init_db should bring the partial DB to the full schema
    engine_caught_up = init_db(str(db_partial))
    caught_up_snap = _column_snapshot(engine_caught_up)
    assert caught_up_snap == full_snap, (
        f"init_db did not catch up partial migration.\n"
        f"Missing tables: {set(full_snap) - set(caught_up_snap)}\n"
        f"Missing columns: "
        + str({
            t: list(set(full_snap[t]) - set(caught_up_snap.get(t, [])))
            for t in full_snap if full_snap[t] != caught_up_snap.get(t)
        })
    )
