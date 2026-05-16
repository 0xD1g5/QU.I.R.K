# Phase 83: Integration Gate + Cleanup - Context

**Gathered:** 2026-05-16
**Status:** Ready for planning

<domain>
## Phase Boundary

All Wave A scanner outputs (Phases 78-82) are integrated into a consistent codebase:
- `SCORE_WEIGHTS` invariant test reflects the final sum (275.0) and count (36) including all
  Phase 79 SMIME entries (+3) and Phase 80 ADCS entries (+4)
- `quirk/engine/migration_planner.py` dead module removed; `categorize_waves` logic inlined
  into `quirk/reports/writer.py`
- Full `pytest` passes green with no residual red tests from Wave A integration

Wave B — requires Wave A complete (Phases 79, 80, 82 specifically); gates Phase 84 release engineering.

</domain>

<canonical_refs>
- `.planning/REQUIREMENTS.md` — CLEAN-01
- `.planning/ROADMAP.md` — Phase 83 (3 success criteria)
- `tests/test_score_weights_invariant.py` — sum 261.0 + count 29 invariants (to be bumped)
- `quirk/intelligence/scoring.py` — `SCORE_WEIGHTS` (now 36 entries, sum 275.0)
- `quirk/engine/migration_planner.py` — dead module to remove (NOT `quirk/intelligence/` as REQUIREMENTS says)
- `quirk/reports/writer.py:14, 225` — import + call site
- Test mocks: `quirk.reports.writer.categorize_waves` (namespace-of-use, NOT migration_planner) — survive inlining unchanged

</canonical_refs>

<decisions>
## Implementation Decisions

- **Path drift:** `migration_planner.py` lives at `quirk/engine/`, not `quirk/intelligence/` as REQUIREMENTS CLEAN-01 states. Honor actual location.
- **Test mocks unchanged:** All 9 (REQUIREMENTS approximates as "7") test mock paths target `quirk.reports.writer.categorize_waves`. Mocks resolve at the namespace-of-use, not the namespace-of-definition. After inlining `categorize_waves` as a local `def` in `writer.py`, the mock paths remain valid without modification.
- **Inlining strategy:** Move the function body verbatim from `quirk/engine/migration_planner.py` into `quirk/reports/writer.py` (place before the existing function that calls it, ~line 225). Remove the import at line 14. Delete `quirk/engine/migration_planner.py`. If `quirk/engine/` becomes empty, also remove the directory + `__init__.py`.
- **Invariant bump:** Update `test_score_weights_sum_invariant` from `261.0` to `275.0` AND update `test_score_weights_count_invariant` from `29` to `36`. Update the docstring rationale to cite Phase 83 + the +14.0/+7 deltas from Phases 79 (SMIME) and 80 (ADCS).
- **Full pytest green:** All Phase 78-82 tests stay green; the previously-red `test_score_weights_invariant.py` flips green; no new red tests.

</decisions>

<code_context>
### Current state
- `quirk/engine/migration_planner.py` — 1 import in `quirk/reports/writer.py:14`; 1 call site at `writer.py:225`
- 9 test mock sites (matching REQUIREMENTS' approximate "7"): `test_cmvp_report_column.py`, `test_reports_writer.py` (×4), `test_report_injection_hardening.py`, `test_cbom_integration.py` (×3)
- All mocks target `quirk.reports.writer.categorize_waves` (correct namespace-of-use pattern)
- `SCORE_WEIGHTS` actual sum: 275.0 (was 261.0 baseline; +6.0 from SMIME, +8.0 from ADCS)
- `SCORE_WEIGHTS` actual count: 36 (was 29; +3 + 4)

</code_context>

<specifics>
- Single atomic commit recommended: `fix(83): integration gate — invariant bump + migration_planner inlined + dead module removed (CLEAN-01)`.
- Single SUMMARY commit: `docs(83): record SUMMARY for integration gate plan`.

</specifics>

<deferred>
None.

</deferred>
