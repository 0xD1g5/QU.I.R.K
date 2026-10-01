---
title: test_vitest_substitute_nodes_pass is INTERMITTENTLY red with 14 vitest nodes, inside the REQUIRED Linux Full Suite job
created: 2026-09-27
source: Phase 207.1 close-out session (found while running the UAT integrity gates, not by a report)
severity: high
reproducibility: intermittent — failed once, passed twice in the same session on the same tree
status: pending
resolves_phase: 220
---

## What

`tests/test_uat_disposition_integrity.py::test_vitest_substitute_nodes_pass` failed locally with
**14 failing vitest nodes** spread across seven dashboard pages:

```
PRINT-01          — /print renders chrome-free
CbomPage          — UAT-7-27 graph node interaction
CbomPage          — UAT-7-14 graph visualization
CertificatesPage  — UAT-7-10 inventory table
ExecutivePage     — DELIV-02 report download group
ExecutivePage     — UAT-7-04 severity chart
FindingsPage      — UAT-7-09 detail slide-out
FindingsPage      — UAT-7-08 severity filtering
FindingsPage      — UAT-7-37 protocol + severity filter
FindingsPage      — focus contract F5 + F6 Escape
FindingsPage      — focus contract F6 via Close button
HardwarePage      — UAT-7-41 device table
RoadmapPage       — UAT-7-15 DAG horizon coding
RoadmapPage       — UAT-7-16 node detail panel
```

The test's own diagnostic line:
`[205-06] cited={'passed': 21, 'failed': 14, 'skipped': 0, 'total': 35}`

## Why this is HIGH, not a local curiosity

**It executes in the REQUIRED `Linux Full Suite` CI job.** The skip guard is
`VITEST_TOOLCHAIN_AVAILABLE = NPM_PATH is not None and DASHBOARD_NODE_MODULES.is_dir()`
(`tests/test_uat_disposition_integrity.py:584`). That job installs Node 24 and runs `npm ci` in
`src/dashboard` (`.github/workflows/python-ci.yml:417-426`) and only THEN runs `pytest -q -m ""`
(:437) — so the guard is satisfied and this node runs for real in CI on every PR.

This also retires, from the other side, the CLAUDE.md §UAT Corpus Integrity Gate "Known limitation"
paragraph claiming the vitest leg substitute-checks by existence only in CI. Phase 205 D-04 added the
Node toolchain; the gap is closed, and the consequence is that this failure is now a red required
check rather than a skipped leg.

## Root cause shape — batched pollution, NOT a product regression

Every failing node **passes standalone.** Verified: `npx vitest run
src/pages/__tests__/findings-filtering.test.tsx` → `1 passed`. The failures appear only when
`_run_vitest_nodes()` batches all 35 cited nodes into ONE vitest subprocess with `-t` filters.

That is the **TRIAGE-149 Cluster 2 signature** — `docs/test-triage-149.md:57-75` lists 14
quarantined tests on one shared-singleton-teardown root cause, every one recorded "passing
standalone". The count coinciding at 14 may be coincidence; do not assume the two sets are the same
without comparing them node-by-node.

## Pre-existence — measured, not assumed

NOT introduced by the Phase 207/207.1 branch:

- vitest citation set is byte-identical between `main` and `HEAD`: **58 test files** each, empty
  symmetric difference.
- `git diff main..HEAD --stat -- tests/test_uat_disposition_integrity.py src/dashboard/` returns
  **empty** — zero changes to the gate or to the dashboard.

So the batched invocation is configured identically on `main`, and `main` fails this node too. It is
**absent from the recorded local baseline**, which lists only
`test_backlog_reconciliation_gate.py::test_back_star_ci_enforced_leg` and
`test_fuzz_cli_safety.py::test_no_fuzz_flag_no_fuzz_errors` — a third instance of that baseline
record being wrong, which its own text warns to expect.

## Next step

Do NOT fix by loosening the assertion or by marking nodes skipped — the test's own message says a
skip is not proof of coverage, and 21 of 35 cited nodes DO pass, so the citations are real coverage.
Find the shared state that the batched run leaks. Start by bisecting the batch: run the 35 cited
nodes in halves to find whether a single early node poisons the rest, which is what the Cluster 2
root cause would predict.

---

## CORRECTION, same session: this is INTERMITTENT, not deterministic

The original text above said the node "FAILS", flatly. **A second and third run on the same tree
found it GREEN** — once standalone and once batched inside the same 7-gate selection that had just
produced the 14 failures (`111 passed, 0 failed`). The second measurement was taken by a separate
agent with no knowledge of the first result, which is why it was believed rather than dismissed.

**What survives the correction, and what does not:**

- **SURVIVES — the configuration argument.** The vitest citation set is byte-identical between `main`
  and `HEAD` and `git diff main..HEAD` is empty for the gate and for `src/dashboard/`. `main` is
  therefore *equally exposed*. That was never a claim about a deterministic failure; it was a claim
  about identical inputs, and it holds.
- **SURVIVES — the CI reachability argument.** `Linux Full Suite` really does install Node 24 + `npm
  ci` before `pytest -q -m ""`, so this node really does execute in the required job.
- **DOES NOT survive — "main's CI is red on this".** Unknown. An intermittent node produces a
  flaky required check, which is a different and in some ways nastier problem than a steady red: it
  cannot be diffed against a baseline, and it will be misattributed to whichever PR happens to catch
  it.

**This reframes the fix.** Do not go looking for a broken component — 21 of 35 cited nodes pass every
time and the other 14 pass standalone every time. Look for **order- or load-dependence** in the
batched vitest subprocess: shared module state across `-t`-filtered files, a timing-sensitive
`findByRole`/`waitFor` under parallel load, or vitest's own worker pool reusing an environment. The
first run that failed was on a machine also running a Playwright browser suite, which is a load
hypothesis worth testing first: re-run the batch under CPU contention and see if the 14 come back.

**Do not "fix" this by re-running until green.** An intermittent gate in a required job is a real
defect; a passing re-run is not evidence of health, in the same way this project already records that
a skip is not a pass.


## Root Cause (Phase 220, 2026-10-01)

**NOT REPRODUCED.** A diagnostic campaign (Phase 220 Plan 01, full record at
`.planning/phases/220-ci-instrument-truth/220-diag/DIAGNOSIS.md`) ran the real batched invocation
10 times across plain runs, CPU contention (20x `yes` on a 10-core machine), concurrent with a real
Playwright/chromium browser suite, a live local HTTP server answering the jsdom-resolved fetch
origin, and the combination of all three simultaneously — the closest local approximation of this
todo's own "first failure happened while a Playwright suite was running" hypothesis. Every attempt
returned `cited={'passed': 36, 'failed': 0, 'skipped': 0, 'total': 36}` with zero `act()` warnings,
zero unhandled rejections, zero ECONNREFUSED/fetch errors, and zero console.error lines.

**What was fixed (as hygiene, not as a demonstrated cause):**

- `src/dashboard/src/pages/__tests__/executive-score-gauge.test.tsx`
- `src/dashboard/src/pages/__tests__/executive-severity-chart.test.tsx`
- `src/dashboard/src/pages/__tests__/executive-driver-cards.test.tsx`

All three rendered `ExecutivePage` without mocking `@/lib/api`'s `fetchApi`, so
`executive.tsx:231-250`'s `loadManifest()` effect issued a real, un-awaited network call on every
render. Each file now mocks `fetchApi` (mirroring `executive-report-downloads.test.tsx`'s in-repo
pattern) and `await waitFor(...)`s the mock's invocation before any assertion runs, so the effect's
async continuation settles inside the test instead of potentially outliving it. This is a genuine
correctness-hygiene fix, grounded in the in-repo pattern, not in a demonstrated causal link to the
14-node failure — DIAGNOSIS.md shows `act=0` held in this environment whether or not the fetch was
mocked.

**What remains a hypothesis, not demonstrated:** the todo's own load/timing hypothesis (cross-file
module state, a shared-worker race, or a timing-sensitive `waitFor` under load) was tested via
CPU contention, concurrent-Playwright, live-server, and single-worker-pool (`--poolOptions.threads.
singleThread=true`) isolation runs — none reproduced a failure, so none of these mechanisms were
confirmed OR ruled out with positive evidence; they simply did not fire in 10 attempts on this
platform (macOS, Node v26.10.0, vitest 2.1.9). `FindingsPage`'s `UAT-7-37` combined-filter test is
the one node that visibly slows under contention (up to ~2.84s, ~57% of vitest's 5000ms default
`testTimeout`) but never crossed the timeout or failed in any attempt — named here as the closest
thing to a live timeout-class candidate, not as a cause.

An attempted act()-warning regression-guard assertion (mutation-proving: temporarily remove one
executive test's `await waitFor(...)` and confirm the batch goes red) did NOT turn the batch red,
even with the fetchApi mock changed to resolve after a 20ms delay — `executive.tsx`'s own
`cancelled`-flag guard structurally prevents a stray `setManifest` call after unmount, so no guard
assertion was added to `test_vitest_substitute_nodes_pass` (an assertion that cannot be shown to
fail on the defect it targets is a tautology, not a guard).

**Not Cluster 2.** TRIAGE-149 Cluster 2 (`docs/test-triage-149.md:57-75`) is a Python/pytest
`AttributeError: PlaywrightContextManager` shared-singleton-teardown defect in an entirely
different test suite and runtime. It shares no mechanism, error signature, or file set with this
vitest batch failure. `docs/test-triage-149.md` is left unchanged.

**Separate finding, not a cause:** `--maxWorkers=1` (the flag this todo's own next-step text named)
silently collects zero tests in this vitest 2.1.9/npm combination, regardless of flag position or
`=`-vs-space syntax; `--poolOptions.threads.singleThread=true` is the working equivalent and was
used instead for the single-worker isolation runs.

## Local acceptance (D-10)

10 consecutive batched runs of `tests/test_uat_disposition_integrity.py::test_vitest_substitute_nodes_pass -m "" -q -rP`, after the fetchApi-mock fixes above, all reporting `1 passed`:

| Run | Timestamp (UTC) | Condition | Result |
|---|---|---|---|
| 1 | 2026-10-01T03:21:19Z | plain | 1 passed |
| 2 | 2026-10-01T03:21:25Z | plain | 1 passed |
| 3 | 2026-10-01T03:21:32Z | plain | 1 passed |
| 4 | 2026-10-01T03:21:50Z | CPU contention (20x `yes`, 10-core machine) | 1 passed |
| 5 | 2026-10-01T03:22:11Z | plain | 1 passed |
| 6 | 2026-10-01T03:22:19Z | plain | 1 passed |
| 7 | 2026-10-01T03:22:32Z | concurrent with `pytest tests/test_browser_e2e.py -m "" -q` (real Playwright/chromium, 9 passed) | 1 passed |
| 8 | 2026-10-01T03:22:54Z | plain | 1 passed |
| 9 | 2026-10-01T03:23:02Z | plain | 1 passed |
| 10 | 2026-10-01T03:23:13Z | plain | 1 passed |

Full detail (per-run census lines) in `.planning/phases/220-ci-instrument-truth/220-diag/DIAGNOSIS.md` "## D-10 Local Leg".

CI acceptance: recorded in 220-VERIFICATION.md / 220-diag/CI-EVIDENCE.md (220-08).
