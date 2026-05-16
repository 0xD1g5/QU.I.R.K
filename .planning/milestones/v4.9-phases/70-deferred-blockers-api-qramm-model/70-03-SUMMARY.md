---
phase: 70
plan: 03
subsystem: db-migrations
tags: [audit-closure, sql-injection-defense-in-depth, BLOCK-08, CR-07]
requires: [BLOCK-08]
provides: [_SAFE_COL_TYPE_RE, col_type-ddl-allowlist, audit-closure-CR-04-05-06-07]
affects: [quirk/db.py, .planning/audit-2026-05-08/AUDIT-TASKS.md]
tech-stack:
  added: []
  patterns: [allowlist-regex-fail-fast]
key-files:
  created: [tests/test_db_migrations.py]
  modified:
    - quirk/db.py
    - .planning/audit-2026-05-08/AUDIT-TASKS.md
decisions:
  - D-06 implemented verbatim — _SAFE_COL_TYPE_RE bounds VARCHAR length to 4 digits and accepts only the 5 literal types currently in use
  - D-07 do-not-touch list respected — _ensure_identity/gcp/email/broker_columns untouched (literal "TEXT" only, no col_type variable)
metrics:
  duration_minutes: 6
  tasks_completed: 3
  files_changed: 3
  completed: 2026-05-15
---

# Phase 70 Plan 03: Deferred BLOCKERs — col_type DDL Allowlist + Audit Row Flips Summary

**One-liner:** Defense-in-depth `_SAFE_COL_TYPE_RE` allowlist guard for SQL-injection on DDL type fragments in four `_ensure_*_columns` migration helpers, plus the AUDIT-TASKS row-flip closing all four Phase 70 BLOCKER rows (CR-04/05/06/07).

## Tasks Completed

| Task | Name | Commit | Files |
| ---- | ---- | ------ | ----- |
| 1 | RED tests for `_SAFE_COL_TYPE_RE` matrix + four poisoned-dict guards | `26dc019` | `tests/test_db_migrations.py` |
| 2 | Add `_SAFE_COL_TYPE_RE` constant + 4 `ValueError` guards | `43284dc` | `quirk/db.py` |
| 3 | Flip CR-04/05/06/07 to `[x] closed` with Phase 70 evidence | `4f4de00` | `.planning/audit-2026-05-08/AUDIT-TASKS.md` |

## What Was Built

### `_SAFE_COL_TYPE_RE` allowlist (`quirk/db.py:34`)

```python
_SAFE_COL_TYPE_RE = re.compile(r"^(TEXT|INTEGER|REAL|BOOLEAN|DATETIME|VARCHAR\(\d{1,4}\))$")
```

Sits adjacent to the existing `_SAFE_COL_RE` constant (L30). Bounded `\d{1,4}` ensures `VARCHAR(99999)` and longer rejected.

### Two-line guard in four helpers

Inserted immediately after the existing `_SAFE_COL_RE.match(col)` check, **before** the `if col not in existing:` branch — so a poisoned `col_type` fails fast on every iteration even when the column already exists:

```python
if not _SAFE_COL_TYPE_RE.match(col_type):
    raise ValueError(f"Unsafe column type in migration: {col_type!r}")
```

Applied to:
- `_ensure_v43_columns` (`_V43_COLUMN_DDLS` — TEXT, VARCHAR(16))
- `_ensure_phase41_columns` (`_PHASE41_COLUMN_DDLS` — VARCHAR(32))
- `_ensure_phase46_columns` (`_PHASE46_COLUMN_DDLS` — BOOLEAN)
- `_ensure_phase54_qramm_columns` (`_PHASE54_QRAMM_ANSWER_DDLS` — TEXT)

### D-07 do-not-touch list confirmed

`_ensure_identity_columns`, `_ensure_gcp_columns`, `_ensure_email_columns`, `_ensure_broker_columns` interpolate the literal string `"TEXT"` directly in their f-string — they bind no `col_type` variable. Unmodified per D-07. `_ensure_qramm_profiles_fk` (added by Plan 70-01) does not iterate a `col_type` dict — also untouched.

### Tests added (`tests/test_db_migrations.py`)

7 test functions, 16 parametrized cases:
- `test_safe_col_type_re_accepts_real_values` — 8 accept cases (TEXT, INTEGER, REAL, BOOLEAN, DATETIME, VARCHAR(16), VARCHAR(32), VARCHAR(9999))
- `test_safe_col_type_re_rejects_unsafe_values` — 8 reject cases (`TEXT; DROP TABLE x`, `VARCHAR(99999)`, `varchar(16)`, empty, `TEXT NOT NULL`, `INTEGER PRIMARY KEY`, `BLOB`, `VARCHAR()`)
- 4 poisoned-dict tests — one per guarded helper
- `test_all_guarded_helpers_accept_real_values` — regression on real values

### Audit row flips

All four Phase 70 BLOCKER rows in `.planning/audit-2026-05-08/AUDIT-TASKS.md` now read `Phase 70 | [x] closed — closed by Phase 70 (BLOCK-NN): <resolution>. <test refs>`:
- CR-04 → 70-01 (FK + PRAGMA)
- CR-05 → 70-01 (delete_session ordering)
- CR-06 → 70-02 (classifier except narrowing)
- CR-07 → 70-03 (col_type allowlist)

Each row's per-row detail block (L396–432 region) now has a `> **closed by Phase 70**` paragraph appended per Phase 69 precedent.

## Verification Results

- `python -m compileall quirk` — clean
- `pytest tests/test_db_migrations.py` — 16 passed
- `pytest tests/test_db_migrations.py tests/test_init_db_idempotent.py tests/test_qramm_models.py tests/test_qramm_delete_session_fk.py` — 65 passed (no regression in Plan 70-01 or 70-02 suites that exist on main)
- Grep verification:
  - `_SAFE_COL_TYPE_RE` constant: 1 hit at line 34
  - `_SAFE_COL_TYPE_RE.match(col_type)` guard: 4 hits (one per helper)
  - `Unsafe column type in migration` raise: 4 hits
  - AUDIT-TASKS rows flipped: 4 (`Phase 70 | [x] closed`)
  - AUDIT-TASKS detail blocks: 4 `> **closed by Phase 70**`

## Deviations from Plan

None — plan executed exactly as written.

The plan referenced `tests/test_cbom_scan_route.py` (owned by Plan 70-02) for cross-plan verification. That file does not exist in the current main-tree HEAD because Plan 70-02's executor is producing it on a parallel branch; the orchestrator will reconcile on merge. No impact on Plan 70-03's own tests, which all pass.

## Authentication Gates

None.

## Decisions Made

- **D-06 verbatim** — used the exact regex from CONTEXT.md without modification.
- **D-07 respected** — confirmed by reading each of the four "do-not-touch" helpers; none of them iterate a `col_type` from a dict.

## Self-Check: PASSED

- `tests/test_db_migrations.py` — FOUND
- `quirk/db.py` modified (`_SAFE_COL_TYPE_RE` at L34, four guards inserted) — FOUND
- `.planning/audit-2026-05-08/AUDIT-TASKS.md` — 4 rows flipped, 4 detail blocks appended — FOUND
- Commit `26dc019` — FOUND
- Commit `43284dc` — FOUND
- Commit `4f4de00` — FOUND
