---
phase: 149-test-suite-triage
plan: 07
subsystem: testing
tags: [dashboard-api, query-encoding, error-envelope, rebrand-drift, auth-invariant, db-migration, stale-fixture, skip-registry]

requires:
  - phase: 149-test-suite-triage plan 06
    provides: cluster_9_group_a_scanner_detection_failures_dispositioned, tests_scanner_subdirectory_walker_gap_closed

provides:
  - cluster_9_group_b_dashboard_api_db_migration_failures_dispositioned
  - route_coverage_api_config_security_relevance_answered

affects:
  - tests/test_dashboard_scan_history.py
  - tests/test_dashboard_theme.py
  - tests/test_route_coverage.py
  - tests/test_db_migrate_cli.py
  - tests/test_init_db_idempotent.py
  - tests/skip_registry.py
  - docs/test-triage-149.md

tech-stack:
  added: []
  patterns:
    - "Query-string '+' is not a caller concern for Starlette/httpx TestClient: raw f-string URLs embedding datetime.isoformat()'s '+00:00' UTC offset get decoded as a literal space (application/x-www-form-urlencoded convention), corrupting timestamps server-side before any application code runs. Callers must urllib.parse.quote() timestamp query params, not just pass isoformat() output directly into an f-string URL."
    - "_ADDITIVE_MIGRATIONS growth (quirk/db.py) requires test fixtures that simulate a 'legacy DB' to be kept in sync — a fixture creating only the tables that existed at fixture-authoring time silently breaks when a later phase adds a new (table, columns) entry, since run_additive_migration ALTERs existing tables rather than creating missing ones."
    - "dir()-based test discovery over a shared name prefix (_ensure_*) is fragile when a differently-shaped helper (generic 3-arg _ensure_columns vs. per-table 1-arg _ensure_*(engine)) joins the same prefix family; needs an explicit exclusion list, same precedent as _ensure_parent_dir."

key-files:
  created: []
  modified:
    - tests/test_dashboard_scan_history.py
    - tests/test_dashboard_theme.py
    - tests/test_route_coverage.py
    - tests/test_db_migrate_cli.py
    - tests/test_init_db_idempotent.py
    - tests/skip_registry.py
    - docs/test-triage-149.md

key-decisions:
  - "test_route_coverage.py's AUTH-02 finding (GET /api/config missing require_auth) was individually investigated and confirmed as stale test inventory, NOT a real unprotected route: quirk/dashboard/api/routes/config.py's own module docstring states the endpoint is deliberately unauthenticated ('no auth required (frontend needs this before login)'), mirrors /api/health's designed pre-auth exemption, and returns only a UI branding enum (vertical name), no scan/crypto/secret data. Explicitly NOT flagged SECURITY: in the ledger, per the plan's must_haves requirement to make this distinction explicit for Phase 150 triage."
  - "4 of the 5 /api/compare test failures were confirmed as a test-construction bug (unescaped '+' in a raw f-string query URL, decoded as a literal space by Starlette/httpx query parsing), not the API-contract drift RESEARCH.md flagged as likely — verified directly by re-issuing the identical request with urllib.parse.quote()-encoded params, which returns 200 with the full expected schema."
  - "The 5th /api/compare test (test_compare_self) IS genuine contract drift: format_error() now wraps every detail string in a structured '[QRK-<CODE>] ... Fix: ...' envelope; the underlying 400 status and self-compare rejection logic are unchanged and correct."

requirements-completed: [SUITE-01]

duration: 45min
completed: 2026-08-12
---

# Phase 149 Plan 07: Cluster 9 Group B — Dashboard/API/DB-Migration Failures Summary

Individually investigated all 12 Cluster 9 Group B failures across 5 files (dashboard
scan-history/compare API, theme CSS tokens, route-coverage security gate, DB migration
CLI, init_db idempotency), confirming distinct root causes for each rather than a
blanket classification, and quarantined all 12 with `@pytest.mark.xfail` plus matching
`tests/skip_registry.py` entries. The security-relevant `test_route_coverage.py` finding
was explicitly resolved as stale test inventory (GET /api/config is intentionally public
by design), not a real unprotected route.

## Performance

- **Duration:** 45 min
- **Started:** 2026-08-12T01:05:00Z
- **Completed:** 2026-08-12T01:50:00Z
- **Tasks:** 3
- **Files modified:** 7

## Accomplishments

- **Task 1 (7 tests — dashboard scan-history/compare + theme):**
  - `test_dashboard_scan_history.py`'s 5 `/api/compare` failures split into two distinct
    causes, disproving RESEARCH.md's assumption that all 5 shared one contract-drift
    cause:
    - 4 (`test_compare_schema`, `test_compare_score_delta`, `test_compare_finding_diff`,
      `test_compare_endpoint_diff`) are a **test-construction bug**: the tests build
      request URLs via a raw f-string embedding `datetime.isoformat()`'s UTC offset
      verbatim (e.g. `...563021+00:00`). Starlette/httpx query-string decoding treats a
      literal `+` as a space (`application/x-www-form-urlencoded` convention),
      corrupting the timestamp before `compare_scans()`'s
      `datetime.fromisoformat(a)` ever runs, producing a 400. Directly confirmed by
      re-issuing the identical request with both params passed through
      `urllib.parse.quote()`: returns 200 with the full expected schema. The
      `/api/compare` endpoint itself is correct.
    - 1 (`test_compare_self`) is **genuine API-contract drift**: `format_error()` now
      wraps every `detail` string in a structured `[QRK-<CODE>] <message> Fix:
      <remediation>` envelope (a later phase standardized error responses across the
      dashboard API). The 400 status and self-compare rejection logic are still
      correct — only the test's exact-string assertion is stale.
  - `test_dashboard_theme.py`'s 2 failures are a **confirmed intentional rebrand**: `git
    log`/`git show` on commit `ac242d1` ("feat(ui): apply Obsidian Pro design system
    foundation", 2026-05-07) shows its own commit message states "Accent shifted from
    blue (210 100% 56%) to Obsidian Pro teal (#4ba8a8)" — the tests predate that
    rebrand and assert the old blue token.
  - Registered 7 new `pre_existing_triage_149` entries in `tests/skip_registry.py`.
- **Task 2 (5 tests — route coverage, DB migrate CLI, init_db idempotency):**
  - `test_route_coverage.py::test_all_data_routes_have_auth_dependency`: the lone
    AUTH-02 violation is `GET /api/config`. Read
    `quirk/dashboard/api/routes/config.py` and confirmed via its own module docstring
    ("Runtime config endpoint — no auth required (frontend needs this before login)")
    and `app.py`'s router registration (no router-level `require_auth`, mirroring
    `/api/health`) that this is **deliberately unauthenticated by design**, returning
    only a UI branding enum (`vertical` name), no scan/crypto/secret data. This test's
    exemption set (`{"/api/health", "/api/health/"}`) was never updated when
    `/api/config` was added for the vertical-system feature — **stale test inventory,
    explicitly NOT a SECURITY: real finding.**
  - `test_db_migrate_cli.py`'s 3 failures: read `quirk/db.py`'s `_ADDITIVE_MIGRATIONS`
    tuple and confirmed a `("sensor_tokens", _V55_SENSOR_TOKEN_COLUMNS)` entry was
    added by Phase 113 AUTH-02 (per-sensor auth) after this test's
    `_create_legacy_schema()` fixture was written. `_create_legacy_schema()` only
    `CREATE TABLE`s `crypto_endpoints`/`qramm_answers`; `run_additive_migration` ALTERs
    existing tables' columns (doesn't create missing tables), so walking a table
    absent from the fixture's legacy schema raises `NoSuchTableError: sensor_tokens`.
    Stale fixture, not a migration-helper regression.
  - `test_init_db_idempotent.py::test_all_ensure_functions_idempotent`: read
    `_ensure_columns`'s signature (`engine, table, expected`, Phase 77 D-21) and
    confirmed it's a generic shared helper invoked BY the real per-table `_ensure_*`
    functions (e.g. `_ensure_qramm_tables` calls it internally), not itself a
    single-arg `_ensure_*(engine)` idempotent helper. The test's `dir()`-based
    discovery already excludes `_ensure_parent_dir` for the identical reason
    (different signature) but never added the same exclusion for `_ensure_columns`.
    Every genuine per-table `_ensure_*` helper IS idempotent; only the discovery
    heuristic is stale.
  - Registered 5 new `pre_existing_triage_149` entries; corrected a pre-existing
    `test_db_migrate_cli.py` `optional_extra` entry (line 166 → 203) whose line number
    drifted past the ±2 tolerance window after the 3 new xfail decorators shifted it.
- **Task 3 (ledger + meta-gate):** Wrote all 12 Cluster 9 Group B rows to
  `docs/test-triage-149.md` with distinct Evidence/Notes for each, and confirmed
  `test_route_coverage.py`'s row explicitly reads "**stale test inventory** (not a real
  unprotected route)" per the plan's must_haves requirement — not left ambiguous.
  Confirmed `pytest tests/test_skip_registry.py -q -m ""` stays green (1 passed).

## Task Commits

1. **Task 1: Quarantine test_dashboard_scan_history.py + test_dashboard_theme.py (7 tests)** — `5abc2f5`
2. **Task 2: Quarantine test_route_coverage.py, test_db_migrate_cli.py, test_init_db_idempotent.py (5 tests)** — `bdd92cf`
3. **Task 3: Write Cluster 9 Group B ledger rows** — `d6da850`

## Files Created/Modified

- `tests/test_dashboard_scan_history.py` - Added 5 `@pytest.mark.xfail(strict=False)` decorators
- `tests/test_dashboard_theme.py` - Added `import pytest` + 2 `@pytest.mark.xfail(strict=False)` decorators
- `tests/test_route_coverage.py` - Added 1 `@pytest.mark.xfail(strict=False)` decorator
- `tests/test_db_migrate_cli.py` - Added 3 `@pytest.mark.xfail(strict=False)` decorators
- `tests/test_init_db_idempotent.py` - Added 1 `@pytest.mark.xfail(strict=False)` decorator
- `tests/skip_registry.py` - Added 12 `pre_existing_triage_149` entries; corrected 1
  pre-existing `test_db_migrate_cli.py` entry's drifted line number (166 → 203)
- `docs/test-triage-149.md` - Filled in the 12-row Cluster 9 Group B table

## Decisions Made

See `key-decisions` in frontmatter. The consequential one for Phase 150 priority: the
`test_route_coverage.py` AUTH-02 finding was individually verified against the actual
route handler and app registration rather than assumed — `/api/config` is genuinely,
intentionally public (mirrors `/api/health`, exposes no sensitive data), so this is
stale test inventory to fix by widening the exemption set, not a security defect to
prioritize.

## Deviations from Plan

None. All 3 tasks executed exactly as planned; 12/12 acceptance-criteria xfail
decorators + registry entries added, matching the plan's numeric expectations exactly
(unlike Plan 06, individual investigation here did not surface any test that turned out
to be non-reproducible — all 12 genuinely fail in this sandbox).

## Issues Encountered

None. The `test_db_migrate_cli.py` line-number drift (166 → 203) after adding 3 new
xfail decorators was expected boilerplate maintenance for the ±2-line-tolerance
meta-gate, not a defect.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

Cluster 9 Group B is fully closed (12/12 tests individually investigated and
dispositioned, ledger updated, `test_skip_registry.py` meta-gate green). The
`test_route_coverage.py` security-relevance question is explicitly answered (stale
inventory, not a real finding) so Phase 150 can deprioritize it relative to any genuine
`SECURITY:`-flagged rows from other clusters. No blockers introduced for remaining
Phase 149 clusters/groups in subsequent 149-0X plans.

---
*Phase: 149-test-suite-triage*
*Completed: 2026-08-12*

## Self-Check

- `tests/test_dashboard_scan_history.py` modified: FOUND
- `tests/test_dashboard_theme.py` modified: FOUND
- `tests/test_route_coverage.py` modified: FOUND
- `tests/test_db_migrate_cli.py` modified: FOUND
- `tests/test_init_db_idempotent.py` modified: FOUND
- `tests/skip_registry.py` modified: FOUND
- `docs/test-triage-149.md` modified: FOUND
- Commit `5abc2f5` (Task 1): FOUND
- Commit `bdd92cf` (Task 2): FOUND
- Commit `d6da850` (Task 3): FOUND
- `pytest tests/test_skip_registry.py -q -m ""` exits 0: CONFIRMED (1 passed)
- `pytest tests/test_dashboard_scan_history.py tests/test_dashboard_theme.py tests/test_route_coverage.py tests/test_db_migrate_cli.py tests/test_init_db_idempotent.py -q -m ""`: CONFIRMED (12 passed, 12 xfailed, 0 failed)

## Self-Check: PASSED
