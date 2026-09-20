# `main`'s CI is red, so every PR inherits a failing required check

**Filed:** 2026-09-17 (demo-prep, noticed while opening PR #31)
**Priority:** P1 — a permanently-red gate is one that stops being read
**Status:** RESOLVED 2026-09-20

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

---

## RESOLVED 2026-09-20 — root cause fixed, `main` is green

Closed by PR #33 (`de9e4f1d`), which fixed the root cause diagnosed in the companion todo
`backlog-gate-false-positive-on-archived-roadmap-prose.md` (now in `completed/`): archived-roadmap
NARRATIVE PROSE was minting phantom `ID::heading` keys for already-closed IDs. `BACK-51` is closed
with evidence at `HORIZON.md:49`; the key `BACK-51::Phases` came from a sentence in
`v5.23-ROADMAP.md` describing that closure.

This todo was the SYMPTOM; that one was the DEFECT. Both are now closed.

**Evidence — #33's Linux Full Suite, run 2: `5127 passed, 0 failed`.** First clean full suite in
this repo since Phase 203. The count reconciles exactly against `main` @ `e1ebe2c4` (5122 passed,
1 failed): the failing gate test converts to a pass (+1/-1) and the narrowing ships 4 new tests,
giving 5122 + 1 + 4 = 5127 with the failing-node set empty. Skipped held at 108, confirming no
skip was quietly substituted for the fix.

**Not fully resolved by this, and deliberately left open elsewhere:** a green `main` means the CI
signal is READABLE again, not that the suite is healthy in general.
`tests/test_fuzz_cli_safety.py::test_no_fuzz_flag_no_fuzz_errors` still times out locally (30s
subprocess) while passing in CI, unexplained; and the vitest `-m slow` leg still substitute-checks
by existence only in CI, because the `Linux Full Suite` job never installs Node for
`src/dashboard/` — tracked in `docs/uat-coverage-gaps.md`.
