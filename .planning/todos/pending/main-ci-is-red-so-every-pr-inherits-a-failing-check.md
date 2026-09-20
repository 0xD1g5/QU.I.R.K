# `main`'s CI is red, so every PR inherits a failing required check

**Filed:** 2026-09-17 (demo-prep, noticed while opening PR #31)
**Priority:** P1 — a permanently-red gate is one that stops being read
**Status:** open

## What is failing

`tests/test_backlog_reconciliation_gate.py::test_back_star_ci_enforced_leg` fails on `main` and
has for at least three consecutive runs (`ea16b91f`, `148afccf`, `789690d0`):

```
Failed: 1 BACK-* ID(s) found neither closed-with-evidence nor listed in
.planning/HORIZON.md's Open-Item Ledger
```

Verified as pre-existing rather than assumed: `git stash` -> run -> `git stash pop` reproduces it
identically on a clean tree, and `gh run view` on `main`'s own workflow runs shows the same node.

A second node, `tests/test_fuzz_cli_safety.py::test_no_fuzz_flag_no_fuzz_errors`, fails **locally**
with a 30s `subprocess.TimeoutExpired` on a real `run_scan.py` invocation. It did NOT fail in CI.
Shape suggests resource contention (the chaos lab was running), but that was not confirmed.

## Why it matters beyond the one test

CI is no longer usable as a merge signal. Both PR #31 and PR #32 show a failing required check
that has nothing to do with their content, and the only honest way to read them is the
stash-and-compare: *does this branch's failing-node SET match main's?* That works, but it is
manual, it does not scale, and it trains everyone to ignore a red X.

This also falsified a recorded baseline: a memory entry asserted "0 failures, empty failing-node
set, verified 2026-09-08". It is not zero. Any recorded pass count should be recomputed, never
trusted.

## Fix

Identify the one unreconciled `BACK-*` ID and either close it with evidence or list it in
HORIZON.md's Open-Item Ledger — whichever is true. Note there is already a related pending todo,
`backlog-gate-false-positive-on-archived-roadmap-prose.md`, which may or may not be the same
defect; check before treating them as separate.
