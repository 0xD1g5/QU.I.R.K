# Phase 149: Test Suite Triage - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-11
**Phase:** 149-Test Suite Triage
**Areas discussed:** Fix vs defer, Quarantine mechanism, Deletion bar

---

## Fix vs defer

| Option | Description | Selected |
|--------|-------------|----------|
| Disposition-only, fix nothing | 149 produces the ledger and machine-checkable quarantine markers only; all actual code fixes wait for Phase 150 | ✓ |
| Fix the obviously trivial ones inline | Fix clear one-line issues on the spot, quarantine the rest | |
| Fix everything feasible now, quarantine only genuine blockers | Front-load real fixing into 149, leave 150 as a thin CI-gate wrapper | |

**User's choice:** Disposition-only, fix nothing (recommended option).
**Notes:** Grounded by the roadmap's own framing — Phase 150's size "cannot be scoped before triage
completes," implying 149 is meant to stay a classification pass. A narrow exception was captured in
CONTEXT.md D-01 for correcting a stale assertion as part of writing an accurate ledger entry (not a
real fix pass).

---

## Quarantine mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| Extend skip_registry.py with a new category | Reuse the existing Phase 41 ALLOWED_SKIPS mechanism and its meta-test gate, adding a new category for the 149 triage set | ✓ |
| New dedicated ledger + per-test xfail markers | Build a standalone TEST-TRIAGE.md and mark tests with xfail pointing to it, kept separate from the existing skip registry | |

**User's choice:** Extend skip_registry.py with a new category (recommended option).
**Notes:** During codebase scouting for this discussion, a live full-suite pytest run showed that
`tests/test_skip_registry.py::test_no_unregistered_skips` (the meta-gate itself) is currently
failing — ~15+ skip markers have drifted unregistered since Phase 41. This became CONTEXT.md D-04:
repairing that drift is now in scope for Phase 149 as groundwork before the 149-specific entries
can be added on top of a working gate.

---

## Deletion bar

| Option | Description | Selected |
|--------|-------------|----------|
| Delete only if the feature/code path it tests is gone | Conservative — confirmed-dead code only, everything else quarantined | ✓ |
| Delete if it's redundant OR its target is gone | Also allows deletion for tests whose assertions are fully subsumed by another passing test | |

**User's choice:** Delete only if the feature/code path it tests is gone (recommended option).
**Notes:** No additional commentary — user accepted the conservative default.

---

## Claude's Discretion

- Exact ledger file format/location — CONTEXT.md only locks the requirement that it be a per-test
  disposition table (not per-file/per-category), since Success Criterion 2 requires an exact count
  match against the full-suite failure count.
- skip vs xfail choice per individual failing test.
- Ledger entry ID naming convention.

## Deferred Ideas

- Actually fixing any of the 108 failures — Phase 150 (SUITE-02/SUITE-03).
- Adding a CI gate for the full suite — Phase 150 (SUITE-03).
- Whether "environment-dependent" failures (e.g. SSRF-blocked DNS, missing openssl in sandbox)
  deserve their own disposition sub-category — left open for planning/research once the full
  108-item list is enumerated per-test.
