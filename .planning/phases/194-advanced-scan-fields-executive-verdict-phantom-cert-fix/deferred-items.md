# Deferred items — Phase 194

## 194-08: `test_backlog_reconciliation_gate.py::test_full_corpus_local_only_leg` — pre-existing, out of scope

**Found during:** Task 2's full-suite gate run (`.venv/bin/python -m pytest -q -m ""`).

**Failure:** 6 fake/example `BACK-*` IDs referenced inside `.planning/milestones/v5.20-phases/
189-config-correctness-drain/{189-REVIEW.md, 189-VERIFICATION.md, 189-03-PLAN.md,
189-03-SUMMARY.md}` (`BACK-1`, `BACK-900`, `BACK-9999`, `BACK-99` — used as worked examples of the
gate's own enumeration logic, not real backlog items) are neither closed-with-evidence nor listed
in `.planning/HORIZON.md`'s Open-Item Ledger, tripping the "local-only, full-corpus" leg of the
backlog-reconciliation gate (RQ-2). This leg is explicitly local-only (skips honestly on a fresh
CI checkout where `.planning/milestones/` is absent per `.gitignore`), so it only ever runs on a
machine with the full untracked milestone-doc corpus present — this machine.

**Scope:** Out of scope for 194-08. Zero files under `.planning/milestones/v5.20-phases/189-*` were
touched by any 194-08 commit (`git log --oneline -- .planning/milestones/v5.20-phases/189-config-correctness-drain/`
shows no 194-08 commits). Phase 189 (v5.20) was closed before Phase 194 began; this is a residue of
that phase's own review/verification prose, not something this plan introduced.

**Not fixed here** per the scope-boundary rule (only auto-fix issues directly caused by the current
task's changes). Reproduction:

```bash
.venv/bin/python -m pytest -q tests/test_backlog_reconciliation_gate.py::test_full_corpus_local_only_leg -m ""
```

**Suggested fix for a future phase:** either (a) add honest ledger rows / a "Resolved by" note to
`.planning/HORIZON.md` disambiguating these four IDs as gate-logic worked examples, not real
backlog items, or (b) narrow the 189-phase docs' prose so `BACK-1`/`BACK-900`/`BACK-9999`/`BACK-99`
read unambiguously as examples to the gate's own regex (e.g. wrap in code fences the gate already
excludes, if such an exclusion exists).
