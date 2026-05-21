---
phase: 85-public-launch-polish
plan: 01
subsystem: cli/db
tags: [cli, db, migration, upgrade-guide, launch, launch-04]
requires: []
provides:
  - quirk.db.run_additive_migration
  - quirk.db.ColumnMigrationResult
  - quirk.db._ADDITIVE_MIGRATIONS
  - quirk db migrate CLI subcommand
  - docs/upgrade-guide.md
affects:
  - quirk/db.py
  - run_scan.py
tech-stack:
  added: []
  patterns:
    - "@dataclass(frozen=True) result tuple for per-column migration diagnostics"
    - "Single-source-of-truth registry for additive migrations shared by init_db + run_additive_migration"
    - "Subprocess-importability gate for CLI tests in bare dev envs"
key-files:
  created:
    - tests/test_db_migrate_cli.py
    - docs/upgrade-guide.md
    - .planning/phases/85-public-launch-polish/85-01-SUMMARY.md
  modified:
    - quirk/db.py
    - run_scan.py
decisions:
  - "Additive registry is module-level constant `_ADDITIVE_MIGRATIONS`; both init_db and run_additive_migration iterate it — no second source of truth."
  - "`init_db` runs full migration even when called from `quirk db migrate`; `--dry-run` skips `init_db` to keep its no-write invariant strict."
  - "Subprocess CLI tests skip (not fail) when run_scan can't be imported in the local interpreter — pypdf is part of `[all]`, CI covers that path."
metrics:
  duration_minutes: ~30
  completed_date: 2026-05-21
requirements_closed: [LAUNCH-04]
---

# Phase 85 Plan 01: `quirk db migrate` CLI + Upgrade Guide Summary

Shipped a public, idempotent `quirk db migrate` subcommand backed by a new `run_additive_migration` helper in `quirk/db.py`, plus the user-facing `docs/upgrade-guide.md` that walks v4.x users through the upgrade end-to-end. LAUNCH-04 is closed.

## What was built

### `quirk.db.run_additive_migration(engine, *, dry_run=False)`
- New public helper returning `list[ColumnMigrationResult]` (a frozen dataclass with `table`, `column`, `status: "added" | "already-present"`).
- Walks the module-level `_ADDITIVE_MIGRATIONS` registry — the same registry now driving `init_db`'s column-installation loop, so there is exactly one source of truth.
- Reuses the existing allowlist-guarded `_ensure_columns` installer for the missing-subset only. The `_SAFE_COL_RE` / `_SAFE_COL_TYPE_RE` allowlists remain the sole `ALTER TABLE` path (verified: a single `ALTER TABLE` literal in the codebase, inside `_ensure_columns`).
- `dry_run=True` issues zero DDL statements (verified by `PRAGMA table_info` snapshot before/after).

### `quirk db migrate` CLI
- New subcommand intercept in `run_scan.main()`, structurally mirroring the existing `compliance` block (Phase 49 D-05).
- Flags: `--db PATH` (override), `--config PATH` (resolve `cfg.output.db_path`), `--dry-run`.
- Output: `table.column: status` per known column + a summary footer (counts of `added` vs `already-present`, plus `(dry-run; no changes written)` when applicable).
- Exit 0 on success; exit 2 only when `--dry-run` is asked against a non-existent DB file.

### `docs/upgrade-guide.md`
- 172 lines, additive-only framing per D-LAUNCH-04.
- All seven required sections in declared order (Scope, Pre-upgrade checklist, Install, Dry-run, Apply, Verify, Rollback).
- Uses the canonical PyPI distribution name `qu-i-r-k` per Phase 84 D-02 throughout.
- Cross-links `docs/release-process.md` for Sigstore attestation verification.

## Commits

| Task | Commit | Type | Files |
|------|--------|------|-------|
| RED — failing tests | `9be31e2` | test | `tests/test_db_migrate_cli.py` |
| Task 1 GREEN — helper | `05e77cb` | feat | `quirk/db.py`, `tests/test_db_migrate_cli.py` |
| Task 2 GREEN — CLI | `a2c1070` | feat | `run_scan.py`, `tests/test_db_migrate_cli.py` |
| Task 3 — upgrade guide | `9d5ab94` | docs | `docs/upgrade-guide.md` |

## Verification

All automated gates green:

- `pytest tests/test_db_migrate_cli.py -x -q` → **8 passed** (4 helper-level + 4 CLI-level).
- `pytest tests/test_db_migrations.py tests/test_db_ensure_columns_generic.py -q` → **25 passed** (no regression in existing allowlist / migration tests).
- `python -m compileall quirk/db.py run_scan.py` → clean.
- `python run_scan.py db migrate --help` → prints documented flags.
- `docs/upgrade-guide.md` grep gates: `quirk db migrate`, `pip install -U qu-i-r-k`, `rollback`, `additive` — all present; 172 lines (≥ 80 required).
- `grep -n "ALTER TABLE" quirk/db.py` → one match, inside `_ensure_columns` — allowlist remains the only DDL path.

## Deviations from Plan

### 1. [Rule 1 — Bug in test setup] Synthetic legacy schema instead of `Base.metadata.create_all`
- **Found during:** Task 1 RED→GREEN handoff (first test run).
- **Issue:** The plan's "fresh DB" tests called `Base.metadata.create_all(engine)` and then asserted every additive column reported `added`. That failed because the SQLAlchemy ORM models already declare every additive column — `create_all` lays them down at table-create time, so by the time `run_additive_migration` runs, they are already present.
- **Fix:** Tests now create the bare-minimum `crypto_endpoints` / `qramm_answers` tables via raw SQL (`_create_legacy_schema` helper), simulating a pre-v4.x on-disk database. This is the actual surface `run_additive_migration` exists to upgrade. The helper itself is unchanged.
- **Files modified:** `tests/test_db_migrate_cli.py`.
- **Commit:** `05e77cb`.

### 2. [Rule 2 — Missing critical correctness] CLI test importability gate
- **Found during:** Task 2 verification (first subprocess test run).
- **Issue:** `run_scan.py` transitively imports `pypdf` (via `quirk.reports.html_renderer`, an optional `[all]` dep). Bare dev envs without `pip install -e ".[all]"` cannot import `run_scan` in a subprocess, so the four CLI tests would false-fail on any minimal local checkout.
- **Fix:** Added `_ensure_run_scan_importable()` probe at the top of each CLI test — if `python -c "import run_scan"` exits non-zero, the test calls `pytest.skip(...)` with the underlying error rather than failing. CI environments with `quirk[all]` installed run the full CLI path; bare local envs skip cleanly.
- **Pre-existing condition:** The eager `pypdf` import in `quirk/reports/html_renderer.py` is the root cause and predates this plan. Lazy-importing it would improve the dev-env story but is out of scope here.
- **Files modified:** `tests/test_db_migrate_cli.py`.
- **Commit:** `a2c1070`.

### 3. [Rule 3 — Blocking issue] Installed `pypdf` into worktree interpreter
- **Found during:** Task 2 verification.
- **Issue:** Once the importability gate was in place, the local CLI tests would *skip* rather than execute — leaving the actual CLI path unverified for this plan's own automated gate.
- **Fix:** Ran `python3.14 -m pip install --break-system-packages pypdf` in the worktree's interpreter so the full subprocess CLI test suite executes here. This is a local environment fix, not a code change.
- **Files modified:** none (env-only).
- **Commit:** none.

## Auth gates

None — fully autonomous execution.

## Known stubs

None.

## Threat flags

None — the change reuses the existing allowlist-guarded ALTER TABLE path and does not introduce any new trust-boundary surface. `run_additive_migration` does not interpolate DDL itself; all SQL still flows through `_SAFE_COL_RE` / `_SAFE_COL_TYPE_RE` inside `_ensure_columns`.

## Self-Check: PASSED

- `quirk/db.py` — FOUND (modified, contains `run_additive_migration` and `ColumnMigrationResult`)
- `run_scan.py` — FOUND (modified, contains `db migrate` subcommand intercept)
- `tests/test_db_migrate_cli.py` — FOUND (8 tests, all pass)
- `docs/upgrade-guide.md` — FOUND (172 lines)
- Commit `9be31e2` — FOUND
- Commit `05e77cb` — FOUND
- Commit `a2c1070` — FOUND
- Commit `9d5ab94` — FOUND
