---
phase: 149-test-suite-triage
plan: 01
subsystem: test-infra
tags: [skip-registry, ast-gate, ci-meta-test, triage-ledger]
requires: []
provides:
  - skip_registry_gate_green
  - pre_existing_triage_149_category
  - test-triage-149_ledger_skeleton
affects:
  - tests/skip_registry.py
  - tests/test_skip_registry.py
  - pyproject.toml
tech-stack:
  added: []
  patterns:
    - "AST-based meta-gate enforces skip-marker registration (existing Phase 41 D-03 pattern, now covers skip/skipif/xfail)"
key-files:
  created:
    - docs/test-triage-149.md
  modified:
    - tests/skip_registry.py
    - tests/test_skip_registry.py
    - pyproject.toml
decisions:
  - "D-04 drift repair: 30 unregistered skip markers found live (vs RESEARCH.md's ~25-29 snapshot); all 30 dispositioned as optional_extra or live_infra, none deleted (all guard real optional-dependency or environment conditions) and none used pre_existing_triage_149 (reserved for Plans 02-10's full-suite quarantine work per plan instructions)"
  - "4 pre-existing registry entries had their line numbers updated in place (test_chaos_storage.py x2, test_dnssec_scanner.py, test_kerberos_scanner.py) rather than duplicated, since they drifted beyond the +/-2 line tolerance but still refer to the same skip guard"
  - "Ambiguous-category skips (platform gates: test_jobs_api.py Linux-only zombie check, test_scheduler_cmd.py Windows SIGTERM skip; defensive fixture guards: test_credential_leakage.py, test_db_migrate_cli.py) were mapped to the closer of the two existing categories (live_infra for platform/environment conditions, optional_extra for missing-dependency-shaped guards) rather than inventing a third category prematurely"
metrics:
  duration: 45min
  completed: 2026-08-11
---

# Phase 149 Plan 01: Skip-Registry Gate Repair + Ledger Skeleton Summary

AST-based skip-registry meta-gate repaired from ~30 unregistered violations to fully
green, extended to detect `@pytest.mark.skip`/`@pytest.mark.xfail` alongside the existing
`skipif`/`skip()`/`importorskip()` coverage, and a 9-cluster triage ledger created for
Plans 02-10 to append per-test disposition rows against.

## What Was Built

### Task 1: D-04 drift repair

Ran the live gate (`pytest tests/test_skip_registry.py -q -m ""`) rather than trusting
RESEARCH.md's possibly-stale snapshot, and found 30 unregistered violations (RESEARCH.md
had captured ~25-29, truncated by terminal scrollback). Every violation was opened at its
reported line and dispositioned:

- 26 new entries registered under a `# Phase 149 D-04: registered pre-existing drift`
  banner in `tests/skip_registry.py` — 15 `optional_extra` (boto3, bs4, httpx, impacket,
  playwright, pypdf, pysnmp, python-docx guards) and 11 `live_infra` (Docker/chaos-lab
  guards, fixture-regen guards, platform-specific gates).
- 4 pre-existing entries had drifted line numbers beyond the +/-2 tolerance and were
  updated in place rather than duplicated: `test_chaos_storage.py` (41→44, 67→71),
  `test_dnssec_scanner.py` (475→480), `test_kerberos_scanner.py` (360→384).
- Zero deletions — every violation guards a real optional-dependency check or
  environment/infra condition; none tested dead code.
- Zero `pre_existing_triage_149` usages here, per plan instruction (that category is
  reserved for Plans 02-10's full-suite failure quarantine, not this pre-existing drift
  cleanup).

### Task 2: AST walker extension + pyproject markers + new category

- `_is_pytest_skipif_decorator` generalized to `_is_pytest_mark_decorator(node, mark_name)`,
  same structural check (Call or bare Attribute, `pytest.mark.<name>`) parametrized on
  `mark_name`.
- Main walk loop now iterates `("skipif", "skip", "xfail")`, appending
  `@pytest.mark.{mark_name}` violations for each unregistered match.
- Verified detection empirically: added a scratch `@pytest.mark.skip(reason="scratch")`
  above an unregistered function in `tests/test_aws_connector.py`, confirmed the gate
  FAILED citing the correct file:line and `@pytest.mark.skip` kind, then reverted and
  confirmed green again.
- `pyproject.toml`'s `markers` list gained `"skip_registry_gate: marks the skip-registry
  meta-gate test"`, closing the pre-existing `PytestUnknownMarkWarning`. Verified with
  `pytest tests/test_skip_registry.py -q -m "" -W error::pytest.PytestUnknownMarkWarning`
  raising no warning.
- `tests/skip_registry.py`'s docstring category set literal now includes
  `"pre_existing_triage_149"` for Plans 02-10 to use.

### Task 3: Ledger skeleton

Re-ran the full suite fresh (`pytest -q -m ""`) rather than trusting RESEARCH.md's
possibly-stale 116 count: actual result is **113 failed, 3078 passed, 22 skipped, 125
warnings**. Created `docs/test-triage-149.md` with:

1. Title + purpose paragraph.
2. Reconciliation line: `Built against: \`pytest -q -m ""\` → 113 failed, 3078 passed, 22
   skipped, 125 warnings — 2026-08-11`.
3. A status-legend block (`fixed`, `quarantined-skip`, `quarantined-xfail`, `deleted`,
   `environment-fix-applied`).
4. Nine `##` cluster headings in the exact specified order, each with an empty
   `| Test ID | Disposition | Sub-reason | Evidence/Notes | Registry entry? |` table.
5. Cluster 8 ("Meta-gate self-failure (D-04)") pre-filled with one row for
   `test_skip_registry.py::test_no_unregistered_skips`, disposition `fixed`, since Tasks
   1-2 already resolved it.
6. Closing footer (Phase/Plan/Updated).

## Deviations from Plan

None — plan executed exactly as written. The live violation count (30) differed from
RESEARCH.md's ~25-29 snapshot and the full-suite failure count (113) differed from
RESEARCH.md's cited 116, both explicitly anticipated by the plan's instruction to use
live, fresh counts rather than the (possibly stale) RESEARCH.md snapshot — not a
deviation, the expected behavior.

## Self-Check

- `docs/test-triage-149.md` exists: FOUND
- `tests/skip_registry.py` modified: FOUND
- `tests/test_skip_registry.py` modified: FOUND
- `pyproject.toml` modified: FOUND
- Commit `014fc75` (Task 1): FOUND
- Commit `647340a` (Task 2): FOUND
- Commit `3b97bc6` (Task 3): FOUND
- `pytest tests/test_skip_registry.py -q -m ""` exits 0: CONFIRMED (1 passed)
- `pytest -q -m ""` full-suite spot-check confirms `test_no_unregistered_skips` passes
  within the full run: CONFIRMED (not present in the 113 FAILED lines; isolated re-run
  passed 1/1)

## Self-Check: PASSED
