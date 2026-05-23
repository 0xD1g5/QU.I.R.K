# Phase 91: Code Cleanup + Bookkeeping - Context

**Gathered:** 2026-05-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Remove dead code (BACK-49–57) with static-analysis confidence, eliminate deprecation warnings, bring Nyquist VALIDATION.md bookkeeping current, and document the JWT `verify=False` advisory — all with CI guards against regression (CLEAN-01..04). Parallel-safe with Phase 89 (disjoint files: 91 touches `quirk/` modules + tests/conftest + CONCERNS.md + docs; 89 touches the chaos lab).

**Not in scope:** new features; opportunistic dead-code deletion beyond the listed BACK items; behavioral refactors.
</domain>

<decisions>
## Implementation Decisions

### CLEAN-01 — Tier-A removals (file/comment/syntax, no call-graph risk)
- **D-01:** Apply BACK-53 (legacy sqlite remnants), BACK-55 (stale comments), BACK-56 (`datetime.utcnow` → `datetime.now(timezone.utc)` deprecation). CI guard: `python -W error::DeprecationWarning -m pytest` passes with zero deprecation-related failures (run with `QUIRK_DB_PATH` set, see D-03).

### CLEAN-02 — Tier-B removals (function/module deletions)
- **D-02:** **Delete only** the listed items BACK-49/50/51/52/54 — no opportunistic deletions beyond the list. Each deletion is **vulture/AST call-graph confirmed** (NOT grep — dynamic imports, `__init__` re-exports, and optional-extra paths hide reachability) before removal, followed by a clean-venv smoke test (`pip install -e . && quirk --version && quirk doctor`) after each deletion batch. Tier-A (D-01) ships before Tier-B (v5.0-D-06).
- **D-02b (report-the-rest):** ALSO run a repo-wide `vulture` pass and write a `dead-code-candidates.md` report (in the phase dir or `docs/`) cataloguing everything else it flags — **without deleting any of it**. This is a *reviewed backlog* for a future phase, not an action list. RATIONALE: QUIRK's optional-extra import paths (`quirk[adcs]`/`[motion]`/etc.), dynamic scanner registration, `__init__` re-exports, and local-import-shadow patterns make vulture over-report; the happy-path clean-venv smoke test cannot exercise every optional-install path, so acting on raw vulture hits risks removing config/install-reachable code. The report captures the cleanup signal safely; deletion of any reported candidate requires its own future per-item review.

### CLEAN-03 — Bookkeeping (+ folded Phase 87/88 carry-ins)
- **D-03:** Bring Nyquist `VALIDATION.md` files affected by v5.0 current (BACK-62); the INFRA-03 Nyquist coverage module (`tests/test_infra03_nyquist_coverage.py`) passes with no stale references. **PLUS two folded carry-ins:**
  - **(a) conftest DB-isolation:** add a `tests/conftest.py` autouse fixture that points `QUIRK_DB_PATH` at an isolated `tmp_path` DB, so the suite never hits the ambient `_default_db_path()` (`quirk/dashboard/api/deps.py:26`) and the `Multiple QU.I.R.K. DBs found` collection error is permanently eliminated (currently breaks 7 DB-backed test modules on local trees). This is the *collection-error* fix only — unrelated to the ~39 pre-existing DB-independent failures.
  - **(b) stale CONCERNS removal:** remove the CONCERNS.md §1.11 dual-scoring-engine entry — `quirk/assessment/readiness_score.py` is deleted and `quirk/reports/writer.py` imports `compute_readiness_score` from `quirk.intelligence.scoring` (verified in Phase 88). One canonical engine; the entry is false.

### CLEAN-04 — JWT verify=False advisory
- **D-04:** Document the intentional inspection-mode `verify=False` (BACK-58) with **an inline code comment at the call site AND a brief docs note** (operators-guide / security notes) — a developer reading the code and an operator reading docs both understand why it is safe in the scanner's threat model.

### Claude's Discretion
- Exact files for each BACK item (researcher/vulture determine reachability), the precise conftest fixture shape, and the docs location for the JWT note — implementation details.

### Carried forward (locked)
- Tier-A before Tier-B (v5.0-D-06); clean-venv smoke test after each Tier-B batch; vulture/AST not grep for reachability.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements + backlog item definitions
- `.planning/REQUIREMENTS.md` — CLEAN-01..04.
- BACK-49..58 definitions — locate in `.planning/ROADMAP.md` backlog table and/or `.planning/audit-2026-05-08/AUDIT-TASKS.md` (the audit ledger); researcher must resolve each BACK item to concrete files before deletion.

### Carry-in targets
- `tests/conftest.py` — add the autouse `QUIRK_DB_PATH` fixture (D-03a).
- `quirk/dashboard/api/deps.py:26` — `_default_db_path()` (the ambient resolver the fixture sidesteps).
- `.planning/codebase/CONCERNS.md` §1.11 — the stale dual-engine entry to remove (D-03b).
- `tests/test_infra03_nyquist_coverage.py` — INFRA-03 Nyquist coverage gate (must pass).

### Cleanup targets
- JWT `verify=False` call site (BACK-58) — identity/JWT scanner.
- `datetime.utcnow` usages (BACK-56) — deprecation fix.

### Rules
- `./CLAUDE.md` — PEP 8, minimal diffs, `python -m compileall` + tests after changes.
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `vulture` (or AST analysis) for reachability — the mandated tool for Tier-B (D-02).
- Phase 88 finding: scoring is ONE engine (informs D-03b CONCERNS removal).

### Established Patterns
- Forward-locking CI guards (e.g. deprecation-as-error pytest run) to prevent regression.
- Clean-venv smoke test (`pip install -e . && quirk --version && quirk doctor`) as the post-deletion safety check.

### Integration Points
- `tests/conftest.py` (DB isolation); `.planning/codebase/CONCERNS.md`; docs/ (JWT note); per-phase VALIDATION.md files.
</code_context>

<specifics>
## Specific Ideas

- Tier-B reachability MUST use vulture/AST, never grep (dynamic imports / re-exports / optional-extra paths hide callers).
- The conftest fix is the permanent cure for the `Multiple QU.I.R.K. DBs` annoyance that's dogged Phases 87–88.
</specifics>

<deferred>
## Deferred Ideas

- Opportunistic dead-code beyond BACK-49/50/51/52/54 (kept out of scope by D-02).
- BACK-A11Y-01 (dashboard a11y baselines + violations) — a separate UI/a11y workstream, NOT part of 91's code cleanup; remains its own backlog item.
</deferred>

---

*Phase: 91-code-cleanup-bookkeeping*
*Context gathered: 2026-05-22*
