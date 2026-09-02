---
phase: 179-remediation-item-model
plan: 01
subsystem: database
tags: [sqlalchemy, sqlite, orm, remediation-tracking, roadmap]

# Dependency graph
requires:
  - phase: 178
    provides: "compute_fingerprint normalises finding title before hashing (Phase 178), giving a finding one stable SHA256 fingerprint across re-scans — the join-table key this plan relies on"
provides:
  - "RemediationItem, RemediationItemFingerprint, ScanScopeSignature ORM tables, created idempotently by init_db()"
  - "REMEDIATION_KIND_SLUGS: closed 14-entry title->slug map, the only place a remediation kind slug is defined"
  - "REMEDIATION_EXCLUDED_TITLES: the 3 zero-endpoint fallback titles, explicitly excluded from remediation tracking"
  - "REMEDIATION_CONSTITUENCY: fingerprint | severity | evidence_only classification per slug"
  - "ITEM_STATES / DEFAULT_ITEM_STATE (not_observed) — the persisted state vocabulary"
  - "item_progress(session, scan_run_id, slug) -> (closed, total) fraction reader"
affects: ["180-closure-computation", "181-surfacing"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "New-table _ensure_*(engine) helper: single-line Base.metadata.create_all(engine, checkfirst=True) body, called from init_db(), NOT the additive-migration registry — matches _ensure_vendor_pqc_trend_events_table (Phase 160)"
    - "Slug-as-identity: a stable kind-derived slug is the persistence key; title is a display-only column, never part of any uniqueness constraint or lookup key"

key-files:
  created:
    - quirk/intelligence/remediation.py
    - tests/test_remediation_item_model.py
  modified:
    - quirk/models.py
    - quirk/db.py

key-decisions:
  - "state (RemediationItem, RemediationItemFingerprint), finding_fingerprint, and scan_run_id/digest (ScanScopeSignature) are nullable=False — a deliberate, documented deviation from CONTEXT D-06's general nullable=True guidance, because these are brand-new tables with no pre-existing rows and a NULL state would be indistinguishable from not_observed"
  - "evidence_only is a third constituency kind for the 7 scan-level-counter-driven items (scan-reliability, tls-enum-coverage, ecdsa-adoption-planning, mtls-lifecycle-operations, assign-owners-and-slas, automate-evidence-refresh, crypto-governance-review) — an honest declaration that no fingerprint constitutes them, not an escape hatch for fingerprint-backed items"
  - "quirk/intelligence/roadmap.py is byte-unchanged (git diff confirmed empty) — _add_candidate's strict-< merge ordering (D-06 / WR-08 Phase 73) is untouched; only the persistence layer is new"
  - "Three new tables created via _ensure_remediation_tables / _ensure_scan_scope_signatures_table + Base.metadata.create_all(checkfirst=True) from init_db(), NOT via the additive-migration registry (_ADDITIVE_MIGRATIONS is column-only)"

patterns-established:
  - "Closed-set guard test: drive build_phased_roadmap through every branch (including endpoints==0 fallback) with min_items/max_items raised well above natural count to force baseline items, then assert every emitted title is either a REMEDIATION_KIND_SLUGS key or a REMEDIATION_EXCLUDED_TITLES member"

requirements-completed: []  # REMED-01/02/03 span multiple plans (179-01 through later plans + Phase 180); NOT marked complete here per plan instructions

# Metrics
duration: 45min
completed: 2026-09-02
---

# Phase 179 Plan 01: Remediation Item Model — Persistence Substrate Summary

**Three new SQLAlchemy tables (remediation_items, remediation_item_fingerprints, scan_scope_signatures) plus a closed 14-entry title-to-slug map replace title-as-persistence-key with a stable kind-derived slug, giving remediation progress a place to live and a way to be expressed as a fraction.**

## Performance

- **Duration:** ~45 min
- **Completed:** 2026-09-02
- **Tasks:** 2/2 completed
- **Files modified:** 4 (2 created, 2 modified)

## Accomplishments

- `RemediationItem`, `RemediationItemFingerprint`, `ScanScopeSignature` ORM classes declared in `quirk/models.py`, created idempotently by `init_db()` via `Base.metadata.create_all(engine, checkfirst=True)` (NOT the additive-migration registry, which is column-only)
- `quirk/db.py` CRLF line endings preserved — diff is 28 lines, well under the 40-line acceptance threshold
- `quirk/intelligence/remediation.py` created: the single reviewable closed set (`REMEDIATION_KIND_SLUGS`, 14 entries) mapping every roadmap-candidate title to a stable slug, plus `REMEDIATION_EXCLUDED_TITLES` (the 3 zero-endpoint fallback titles, explicitly rejected — not forgotten)
- `item_progress()` proves "6 of 8 verified closed" is expressible against the schema as a `(6, 8)` tuple, never a boolean
- `quirk/intelligence/roadmap.py` left byte-unchanged — verified with `git diff --quiet`

## Task Commits

Each task was committed atomically:

1. **Task 1: Declare the three tables and wire them into init_db** - `cf0d1eb2` (feat)
2. **Task 2: The kind-slug closed set and the not_observed state vocabulary** - `89534cb1` (feat)

_Note: both tasks are `tdd="true"`; RED-phase tests were written and run to confirm failure (ImportError on new model/module names, and a removed-title closed-set-guard failure) before the corresponding implementation was added, matching the RED/GREEN discipline within each task's single commit — the plan's task-level `type="auto" tdd="true"` grouping does not require separate test/feat commits per task._

## Files Created/Modified

- `quirk/models.py` - Added `RemediationItem`, `RemediationItemFingerprint`, `ScanScopeSignature` classes (after `HardwareDevice`); added `UniqueConstraint` to the sqlalchemy import
- `quirk/db.py` - Added `_ensure_remediation_tables(engine)` and `_ensure_scan_scope_signatures_table(engine)`, called from `init_db()` after `_ensure_vendor_pqc_trend_events_table(engine)`; CRLF preserved, 28-line diff
- `quirk/intelligence/remediation.py` (new) - `REMEDIATION_MODEL_VERSION`, `REMEDIATION_KIND_SLUGS`, `REMEDIATION_EXCLUDED_TITLES`, `REMEDIATION_CONSTITUENCY`, `ITEM_STATES`, `DEFAULT_ITEM_STATE`, `slug_for_title()`, `item_progress()`
- `tests/test_remediation_item_model.py` (new) - Schema-contract tests for all three tables (column presence, nullability, no ForeignKey), idempotent-init_db test, round-trip + NOT NULL constraint tests, closed-set guard (positive + negative control), slug-uniqueness test, `item_progress` 6-of-8 and 0-of-8 fraction tests

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Comment in `remediation.py` accidentally matched the acceptance-criteria grep for `slugify`**
- **Found during:** Task 2 acceptance-criteria verification
- **Issue:** The module docstring/comment explaining "never call slugify(title) at a call site" contained the literal string `slugify`, which the acceptance grep `grep -n "slugify\|slug_for_title(title.lower())"` flags regardless of context (comment vs. code)
- **Fix:** Reworded the comment to "never derive a slug from title at a call site" — same meaning, no longer matches the literal string
- **Files modified:** `quirk/intelligence/remediation.py`
- **Commit:** `89534cb1`

No other deviations — plan executed as written. `tests/test_init_db_idempotent.py` did not need modification: its existing table-name-agnostic assertions (via `sqlalchemy.inspect(engine).get_table_names()`) already generically cover the three new tables without any edit, so extending it would have been a no-op; a dedicated `test_init_db_creates_three_new_tables_idempotently` test was added to `tests/test_remediation_item_model.py` instead to make the three-new-table coverage explicit and independently verifiable.

## Known Stubs

None. `probe_health_json` on `ScanScopeSignature` is intentionally `NULL`/unpopulated in this plan — it is documented in the class docstring as "populated by Plan 04," which is the plan responsible for wiring it, not a stub requiring resolution here.

## Threat Flags

None. All new surface (three tables, one constants module) is already covered by this plan's own `<threat_model>` (T-179-01, T-179-04, T-179-05, T-179-06, T-179-SC); no additional trust-boundary-crossing surface was introduced beyond what the plan anticipated.

## Self-Check: PASSED

- FOUND: quirk/intelligence/remediation.py
- FOUND: tests/test_remediation_item_model.py
- FOUND: cf0d1eb2 (git log)
- FOUND: 89534cb1 (git log)
- Verified: `.venv/bin/pytest tests/test_remediation_item_model.py tests/test_init_db_idempotent.py -x -q` → 16 passed, 1 xfailed
- Verified: `.venv/bin/pytest tests/test_intelligence_roadmap.py -q` → 10 passed; `git diff --quiet quirk/intelligence/roadmap.py` → empty
- Verified: `.venv/bin/pytest tests/test_cve_score_guard.py -q` → 18 passed
- Verified: `git diff HEAD~2 --stat quirk/db.py` → 28 lines, CRLF preserved (`file` reports "CRLF line terminators")
