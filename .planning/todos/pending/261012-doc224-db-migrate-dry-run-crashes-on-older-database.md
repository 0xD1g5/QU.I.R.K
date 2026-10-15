---
type: todo
created: 2026-10-12
source: Phase 224 plan 08 (docs/upgrade-guide.md audit)
priority: medium
area: quirk/db.py (run_additive_migration)
status: pending
resolves_phase: null
owner: "999.129"
---

# `quirk db migrate --dry-run` crashes with `NoSuchTableError` on a database from an older release

**Filed:** 2026-10-12 (Phase 224 plan 08, docs/upgrade-guide.md audit)
**Priority:** P2 — the dry-run is the upgrade guide's safety step and it fails on exactly the databases the guide is for
**Status:** open
Frontmatter added by Phase 227 (D-02): priority derived from the body Priority line (P2 → medium).

## What happens

A database created by `quirk-scanner==4.10.0` (`init_db` from that release) was copied three times and fed to
`quirk db migrate --dry-run --db <copy>`, once with the repo checkout and once with the published
`quirk-scanner==5.25.0` installed in a scratch venv with no extras. Both end:

```
sqlalchemy.exc.NoSuchTableError: sensor_tokens        (exit 1)
```

`run_additive_migration` (`quirk/db.py:331`) reflects each table in `_ADDITIVE_MIGRATIONS` with
`insp.get_columns(table)` and does not tolerate a table that does not exist yet. The real run does not hit this
because `run_scan.py:1492-1495` calls `init_db(db_path)` first, which creates the missing tables. The dry-run
skips that step on purpose (`elif not os.path.exists(db_path)` branch) and so never creates them either.

The same real run then reports `Summary: 0 added, ...` for every database, because `init_db` has already added
every column before the report is produced; only the dry-run can ever print `added` lines.

## Fix

In `run_additive_migration`, when `dry_run` is true and a table is absent from the inspector, report its
columns as `added` (or a distinct `table-missing` status) instead of reflecting it. `docs/upgrade-guide.md` now
documents the crash as a known limitation and should be updated when this is fixed.

## Feasibility & Effort

- Feasibility: CONFIRMED. Reproduced on a 4.10.0-created database against both the working tree and the
  published 5.25.0 wheel; traceback ends at `quirk/db.py:331`.
- Effort: S — one guarded branch plus a test that builds a database lacking a late table.
- Unknowns: whether the report should treat a missing table as one `added` line per column or a single line.
- Spike needed: no.
