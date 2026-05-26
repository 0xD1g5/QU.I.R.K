---
phase: 110-cross-sensor-merge-scoring
plan: "03"
subsystem: cli
tags: [merge, cli, sensor, distributed, uat]
dependency_graph:
  requires: [110-02]
  provides: [quirk.cli.sensor_cmd._cmd_merge, quirk sensor merge subcommand]
  affects: [quirk/cli/sensor_cmd.py]
tech_stack:
  added: []
  patterns: [thin-wrapper CLI over standalone callable, lazy imports in CLI handler, monkeypatch test dispatch]
key_files:
  created:
    - tests/test_merge_cli.py
  modified:
    - quirk/cli/sensor_cmd.py
    - docs/UAT-SERIES.md
decisions:
  - "CLI is a thin wrapper over merge_scan() — no merge/scoring logic inlined (T-110-08 grep gate)"
  - "Lazy imports inside _cmd_merge follow existing _cmd_push/_cmd_export_results pattern"
  - "sys already imported at module level — not re-imported inside _cmd_merge (PEP 8)"
  - "coverage_warning printed as WARNING line + per-sensor indent lines on stdout (not stderr)"
metrics:
  duration: "~15 minutes"
  completed: "2026-05-25"
  tasks_completed: 2
  files_created: 1
  files_modified: 2
---

# Phase 110 Plan 03: CLI Dispatch + UAT Docs Summary

**One-liner:** `quirk sensor merge` CLI subcommand thin-wires to merge_scan() with scan_id/score/coverage_warning output, plus Series 110 UAT documentation and Obsidian vault sync.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Wire quirk sensor merge subcommand + CLI test | 7e2123b | quirk/cli/sensor_cmd.py, tests/test_merge_cli.py |
| 2 | Update docs/UAT-SERIES.md and sync to Obsidian | 44e8c21 | docs/UAT-SERIES.md |

## What Was Built

### Task 1: quirk sensor merge Subcommand

Added `merge` subparser to `quirk/cli/sensor_cmd.py` after the `export-results` parser registration:
- `merge_p = sub.add_parser("merge", ...)` with `--db` (default None) and `--stale-days` (type=int, default=30, dest="stale_days")
- `elif args.action == "merge": _cmd_merge(args)` branch inside the existing `try` dispatch block

Implemented `_cmd_merge(args)` following the `_cmd_push`/`_cmd_export_results` lazy-import pattern:
- Lazy-imports: `merge_scan` from `quirk.merge.scan`, `_default_db_path` from `quirk.dashboard.api.deps`, `init_db` and `get_session` from `quirk.db`
- Resolves `db_path = args.db or _default_db_path()`
- Calls `init_db(db_path)` then opens `get_session(db_path)` context manager
- Calls `merge_scan(db, stale_days=args.stale_days)` — the standalone callable (D-06 seam)
- Prints `Merged scan_id: {scan_id}`, `Score: {score} ({rating})`
- If `coverage_warning` is non-null: prints `WARNING: {reason}` and `  - {sid}` per missing sensor
- Calls `sys.exit(0)` — `sys` already imported at module level (no re-import)

No union, scoring, or coverage logic is inlined in the CLI (T-110-08 grep gate verified).

Created `tests/test_merge_cli.py` with 4 tests:
- `test_merge_cli_dispatch`: monkeypatches merge_scan; asserts scan_id/score/rating in stdout; exit 0; `mock_merge.assert_called_once()`
- `test_merge_cli_coverage_warning`: monkeypatches with non-null coverage_warning; asserts WARNING + both sensor IDs printed
- `test_merge_cli_custom_db_and_stale_days`: asserts stale_days=14 forwarded to merge_scan via `--stale-days 14`
- `test_merge_cli_no_merge_logic_inlined`: `inspect.getsource()` asserts `build_evidence_summary` and `compute_readiness_score` absent from sensor_cmd.py

All 4 tests pass. Full merge suite (CLI + merge_scan unit): 12/12.

### Task 2: UAT-SERIES.md Series 110 + Obsidian Sync

Added Series 110: Cross-Sensor Merge & Scoring to `docs/UAT-SERIES.md` covering:
- UAT-110-01: CLI dispatch prints scan_id/score/rating, exits 0 (automated)
- UAT-110-02: coverage_warning WARNING + missing sensors printed (automated)
- UAT-110-03: Option-A union scoring — score equals full-union single call (automated)
- UAT-110-04: scanned_at preserved — source CryptoEndpoint.scanned_at not mutated (automated)
- UAT-110-05: two-segment same-IP yields two CBOM components (automated)
- UAT-110-06: manual console run with enrolled sensors (human)

Updated `Last Updated` header line to prepend Phase 110 COMPLETE summary.

Synced to Obsidian vault via `printf frontmatter + cat + cp` pattern to `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md`.

Committed `docs/UAT-SERIES.md` via `gsd-tools.cjs commit "docs(phase-110): update UAT-SERIES.md"` per CLAUDE.md mandatory step 4.

## Grep Gates (Verified)

- `grep -c "merge_scan" quirk/cli/sensor_cmd.py` = 5 (lazy import + call + docstring references) — PRESENT
- `grep "_cmd_merge" quirk/cli/sensor_cmd.py` — PRESENT (def + dispatch)
- `grep "build_evidence_summary" quirk/cli/sensor_cmd.py` — NOT FOUND (T-110-08 clean)
- `grep "compute_readiness_score" quirk/cli/sensor_cmd.py` — NOT FOUND (T-110-08 clean)

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries. The CLI reads the local console DB via the existing `get_session` + `init_db` pattern. No new trust boundaries introduced.

## Self-Check: PASSED

- quirk/cli/sensor_cmd.py merge subparser: FOUND (`grep "add_parser.*merge"`)
- quirk/cli/sensor_cmd.py _cmd_merge: FOUND (line 701)
- tests/test_merge_cli.py: FOUND
- docs/UAT-SERIES.md Series 110: FOUND (`grep "Series 110"`)
- Obsidian vault UAT-Series.md: FOUND (`/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md`)
- Commit 7e2123b: FOUND (`git log --oneline`)
- Commit 44e8c21: FOUND (`git log --oneline`)
- `python -m pytest tests/test_merge_cli.py tests/test_merge_scan.py -q`: 12 passed
- `python -m compileall quirk`: CLEAN
