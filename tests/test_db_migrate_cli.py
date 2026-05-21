"""Phase 85-01 LAUNCH-04: tests for `run_additive_migration` helper and
`quirk db migrate` CLI subcommand.

Coverage:
    - Fresh DB → every additive column reports as `added`.
    - Second invocation against the same DB → every column reports
      `already-present`; no writes occur.
    - `dry_run=True` → returns the same diagnostic list but issues zero
      ALTER TABLE statements (verified by snapshotting PRAGMA table_info).
    - Returned objects expose `table`, `column`, `status`
      (`"added"` | `"already-present"`).
    - CLI: `quirk db migrate --db <path>` exits 0 with status lines.
    - CLI: `quirk db migrate --dry-run` does not modify the DB file.
    - CLI: `quirk db migrate --help` is informative.
    - CLI idempotence: double-run yields all-`already-present`.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import inspect as sa_inspect


# ---------------------------------------------------------------------------
# Helper-level tests (Task 1)
# ---------------------------------------------------------------------------


def _snapshot_columns(engine) -> dict[str, set[str]]:
    """Snapshot every table's columns for before/after diffing."""
    insp = sa_inspect(engine)
    return {t: {c["name"] for c in insp.get_columns(t)} for t in insp.get_table_names()}


def test_fresh_db_reports_every_column_added(tmp_path: Path) -> None:
    """First migrate run against a freshly-created DB reports every additive
    column as `added`."""
    from quirk.db import (
        Base,
        get_engine,
        run_additive_migration,
    )

    db_path = tmp_path / "fresh.db"
    engine = get_engine(str(db_path))
    # Create base schema only — no _ensure_columns calls yet, so all additive
    # columns are missing.
    Base.metadata.create_all(engine, checkfirst=True)

    results = run_additive_migration(engine, dry_run=False)

    assert len(results) > 0
    assert all(r.status == "added" for r in results), (
        f"Expected all 'added', got: {[(r.table, r.column, r.status) for r in results]}"
    )
    # Sanity: at least the well-known v4.x columns are present.
    cols_added = {(r.table, r.column) for r in results}
    assert ("crypto_endpoints", "kerberos_scan_json") in cols_added
    assert ("crypto_endpoints", "dat_scan_json") in cols_added
    assert ("crypto_endpoints", "chain_verified") in cols_added
    assert ("qramm_answers", "evidence_note") in cols_added


def test_second_run_reports_already_present(tmp_path: Path) -> None:
    """Re-running migrate after a successful migration reports every column
    as `already-present` and writes nothing."""
    from quirk.db import init_db, run_additive_migration, get_engine

    db_path = tmp_path / "twice.db"
    # init_db runs the full migration path on creation.
    init_db(str(db_path))

    engine = get_engine(str(db_path))
    before = _snapshot_columns(engine)

    results = run_additive_migration(engine, dry_run=False)

    assert len(results) > 0
    assert all(r.status == "already-present" for r in results), (
        f"Expected all 'already-present', got: {[(r.table, r.column, r.status) for r in results]}"
    )

    after = _snapshot_columns(engine)
    assert before == after, "Re-running migrate against a current DB modified columns"


def test_dry_run_does_not_write(tmp_path: Path) -> None:
    """`dry_run=True` returns the same diagnostic shape as a real run but
    issues zero ALTER TABLE statements."""
    from quirk.db import Base, get_engine, run_additive_migration

    db_path = tmp_path / "dry.db"
    engine = get_engine(str(db_path))
    Base.metadata.create_all(engine, checkfirst=True)

    before = _snapshot_columns(engine)

    results = run_additive_migration(engine, dry_run=True)

    after = _snapshot_columns(engine)
    assert before == after, "dry_run=True modified the schema"
    # Every column should report as `added` (i.e., what *would* be added).
    assert len(results) > 0
    assert all(r.status == "added" for r in results)


def test_result_shape(tmp_path: Path) -> None:
    """ColumnMigrationResult exposes table, column, status."""
    from quirk.db import Base, get_engine, run_additive_migration

    db_path = tmp_path / "shape.db"
    engine = get_engine(str(db_path))
    Base.metadata.create_all(engine, checkfirst=True)

    results = run_additive_migration(engine, dry_run=True)
    sample = results[0]
    assert isinstance(sample.table, str) and sample.table
    assert isinstance(sample.column, str) and sample.column
    assert sample.status in ("added", "already-present")


# ---------------------------------------------------------------------------
# CLI-level tests (Task 2)
# ---------------------------------------------------------------------------


REPO_ROOT = Path(__file__).resolve().parents[1]


def _run_cli(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(REPO_ROOT / "run_scan.py"), *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_cli_migrate_help_lists_flags(tmp_path: Path) -> None:
    proc = _run_cli(["db", "migrate", "--help"], cwd=tmp_path)
    assert proc.returncode == 0, proc.stderr
    out = proc.stdout
    assert "--db" in out
    assert "--dry-run" in out


def test_cli_migrate_fresh_db_exit_zero(tmp_path: Path) -> None:
    """`quirk db migrate --db PATH` on a fresh DB exits 0 and prints column
    status lines + a summary footer."""
    db_path = tmp_path / "cli_fresh.db"
    proc = _run_cli(["db", "migrate", "--db", str(db_path)], cwd=tmp_path)
    assert proc.returncode == 0, f"stderr: {proc.stderr}\nstdout: {proc.stdout}"
    # Status lines: `table.column: status`
    assert "crypto_endpoints.dat_scan_json" in proc.stdout
    # Summary footer
    assert "added" in proc.stdout.lower()


def test_cli_migrate_dry_run_no_write(tmp_path: Path) -> None:
    """`quirk db migrate --dry-run` does not modify the DB file mtime/size."""
    db_path = tmp_path / "cli_dry.db"
    # Seed an empty DB the same way init_db would create the file path.
    # Use init_db so the DB exists at the current schema first, then dry-run
    # against it — both should yield all-`already-present` with no writes.
    from quirk.db import init_db

    init_db(str(db_path))
    mtime_before = os.path.getmtime(db_path)
    size_before = os.path.getsize(db_path)

    proc = _run_cli(
        ["db", "migrate", "--db", str(db_path), "--dry-run"], cwd=tmp_path
    )
    assert proc.returncode == 0, f"stderr: {proc.stderr}\nstdout: {proc.stdout}"
    assert "dry-run" in proc.stdout.lower()

    mtime_after = os.path.getmtime(db_path)
    size_after = os.path.getsize(db_path)
    assert mtime_after == mtime_before, "dry-run modified DB mtime"
    assert size_after == size_before, "dry-run modified DB size"


def test_cli_migrate_idempotent_double_run(tmp_path: Path) -> None:
    """Re-running `quirk db migrate` without --dry-run yields all
    `already-present` status lines on the second run."""
    db_path = tmp_path / "cli_idemp.db"
    first = _run_cli(["db", "migrate", "--db", str(db_path)], cwd=tmp_path)
    assert first.returncode == 0, first.stderr

    second = _run_cli(["db", "migrate", "--db", str(db_path)], cwd=tmp_path)
    assert second.returncode == 0, second.stderr
    # Second run must show every line as already-present; therefore zero
    # `added` status tokens in the per-column lines.
    # Be lenient about the summary footer — only check status-line tokens.
    column_lines = [
        ln for ln in second.stdout.splitlines() if ": " in ln and "." in ln.split(": ")[0]
    ]
    assert column_lines, f"No column status lines found in: {second.stdout!r}"
    assert all(": already-present" in ln for ln in column_lines), (
        f"Found non-already-present lines on second run: {column_lines}"
    )
