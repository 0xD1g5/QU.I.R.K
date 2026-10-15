---
type: todo
created: 2026-10-13
source: Phase 224 doc-claim ledger (DOC-04), gap closure GC3-OPS (fork B); ledger row DCL-OPS-A-0599 (docs/operators-guide.md §3.2 "--fuzz-budget has a hard ceiling")
priority: low
area: run_scan.py (_fuzz_budget_exceeds_ceiling), quirk/scanner/rest_fuzzer.py (_resolve_budget)
status: pending
resolves_phase: null
owner: "999.136"
---

# `--fuzz-budget 0` or a negative value is accepted and fuzzes nothing

`_fuzz_budget_exceeds_ceiling` (`run_scan.py:1061-1069`) rejects only values above `MAX_FUZZ_BUDGET` with
`FUZZ-002`. `_resolve_budget` (`quirk/scanner/rest_fuzzer.py:95-114`) documents "The effective budget (>= 1 and
<= MAX_FUZZ_BUDGET)" but checks only the upper bound. A budget of `0` or `-5` passes both checks. Every budgeted
dispatch is guarded by `budget_used < effective_budget` (`rest_fuzzer.py:562,574,600,715`), so the run fuzzes nothing
and reports no findings, which reads like a clean API.

Probe (isolated HOME, non-TTY): `--fuzz --fuzz-budget=-5` and `--fuzz-budget=0` -> `QRK-FUZZ-001` (the TTY refusal;
the budget check passed), `--fuzz-budget=501` -> `QRK-FUZZ-002`.

The operators-guide now states there is no lower bound. A guardrail flag should reject a non-positive budget.

- [ ] Reject `fuzz_budget < 1` with `FUZZ-002` (or argparse `type=` validation) before the TTY check.
- [ ] Make `_resolve_budget` enforce its documented `>= 1`.
- [ ] Test both, then remove the "no lower bound" sentence from the operators-guide.

## Feasibility & Effort

- **CONFIRMED** upper-bound-only check at `run_scan.py:1069` (`return budget > MAX_FUZZ_BUDGET`) and
  `quirk/scanner/rest_fuzzer.py:109` (`if effective > MAX_FUZZ_BUDGET:`).
- **CONFIRMED** the argparse option is `type=int, default=50` with no range (`run_scan.py:1765-1774`).
- **LIKELY** effort **S**: one comparison in each function plus a test next to the existing FUZZ-002 test.
  **UNKNOWN**: whether `FUZZ-002`'s catalogue text (quirk/errors.py) should be widened or a new code added. No spike.
