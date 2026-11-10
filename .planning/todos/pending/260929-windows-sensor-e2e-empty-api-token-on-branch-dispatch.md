# Windows Sensor E2E fails with an empty `--api-token` on a branch `workflow_dispatch`

**Filed:** 2026-09-29 (during Phase 216 close-out)
**Priority:** P2 — a required-ish CI job, red on a phase branch, green on `main`
**Owner:** 999.119 (HORIZON.md ledger row; backlog .planning/backlog/999.119-ci-and-chaos-lab-hygiene-carry-forward/).
**Re-pointed:** 2026-10-01 by Phase 221 (INT-01). The previous owner phase closed without picking this up.
**Status:** pending

## What happened

`python-ci.yml` job **Windows Sensor E2E (frozen -> Linux-built console)** failed on
run [36618376788](https://github.com/0xD1g5/QU.I.R.K/actions/runs/36618376788), branch
`phase-216-a11y-harness-repair`, dispatched via `workflow_dispatch`.

Failing step: `Frozen sensor enroll -> push auth round-trip`. Verbatim cause:

    quirk sensor enroll: error: argument --api-token: expected one argument
    Write-Error: frozen quirk.exe sensor enroll exited 2
    ##[error]Process completed with exit code 1.

`$raw_token` is read at `python-ci.yml:326` from `$env:RUNNER_TEMP\e2e_token.txt`, written by
the preceding console-enroll step. That file was empty or whitespace, so `--api-token` received
no value and argparse rejected the invocation.

## Two separate defects

1. **The parse step's guard is ineffective against an empty-but-present token.** It has
   `Write-Error "Could not parse *** from console enroll stdout"; exit 1`, yet GitHub records
   that step as *succeeded* while the file it wrote was empty. A guard that only checks "did I
   find something" and not "is what I found non-empty" passes an empty string downstream.
2. **The failure surfaces two steps later as a confusing argparse error**, not at the point the
   token went missing. The consuming step should assert `-not [string]::IsNullOrWhiteSpace($raw_token)`
   with a message naming `e2e_token.txt`, so the red points at the real cause.

## Attribution — NOT Phase 216

- `git diff --name-only main..HEAD` touches **zero** sensor, Windows, freeze/PyInstaller, or
  Python source paths. The phase touched `src/dashboard/tests/a11y/`, `src/dashboard/src/`,
  `quirk/dashboard/static/` (rebuilt bundles), `docs/`, `.planning/`, and
  `.github/workflows/dashboard-quality.yml` — never `python-ci.yml`.
- The job is `success` on **5 of main's last 5** python-ci runs (36604466116, 36512285080,
  36511623277, 36502551943, 36493422175), so it is not chronically broken either.

## The untested hypothesis — do this first

The one variable that differs: **main's green runs were all `push`-triggered; this red run was
`workflow_dispatch` on a non-default branch.** If the console enroll's token derives from a
repo/environment secret that is not exposed on a branch dispatch, the token would be empty for
exactly this reason and the job would be green on every push and red on every branch dispatch —
matching all observations.

**Cheapest decisive test:** re-dispatch `python-ci.yml` on `main` via `workflow_dispatch` (not a
push). If Windows Sensor E2E fails there too, the trigger type is the cause and no product code
is implicated. A single-job `gh run rerun --job` was attempted and refused because the parent run
was still in progress; retry once the run completes.

## Why this was invisible until now

Neither `python-ci.yml` nor `dashboard-quality.yml` triggers on a phase-branch push — both are
`pull_request`, `push: branches: [main]`, `workflow_dispatch`. So the required `Linux Full Suite`
and this job had **never run on this branch** before Phase 216 dispatched them deliberately.
Phase-branch CI state is unobserved by default in this repo, which is squarely Phase 220's
"the gates that report CI health actually measure it" territory.

## Related

- Phase 220 (v5.26) — CI Instrument Truth. This belongs to that phase's scope.
- `main`'s `Linux Full Suite` is currently **failure** on run 36604466116, which is already a
  named Phase 220 goal ("`main`'s Python CI is green").

## Update 2026-09-29 — trigger-type hypothesis now has one confirming data point

PR #38 (same tree as the failing dispatch, `pull_request`-triggered) ran this job **green**:
run `36624566175`, job `109599195909`, 2m14s. Same code: RED under `workflow_dispatch`
(`36618376788`), GREEN under `pull_request`. That isolates the trigger, not the code. It does
NOT yet name the mechanism — the empty `e2e_token.txt` points at something dispatch-only
(a secret/env not exposed to dispatch runs, or a conditional step). Next step: diff the
job's `if:`/`env:` handling between the two event types in `python-ci.yml`.

## Root cause found 2026-11-09 — the token was not empty, it started with "-"

The trigger-type hypothesis above is **wrong**. Run
[42612837583](https://github.com/0xD1g5/QU.I.R.K/actions/runs/42612837583) (PR #74) failed the
identical way on a `pull_request` event, and its log shows the console-enroll step parsed and saved
a token (`Console enroll OK — sensor_id=… token=[masked]`).

`secrets.token_urlsafe(32)` draws from `A-Z a-z 0-9 - _`, so about 1 token in 64 starts with `-`.
`--api-token $raw_token` then hands argparse `--api-token -Xyz…`, which it reads as a new option:
`argument --api-token: expected one argument`. Reproduced locally with argparse and with the real
`quirk sensor enroll`. The "one confirming data point" above was a 1-in-64 event that happened to
land on a dispatch; five green push runs beside it are what a 63-in-64 pass rate looks like.

It was not CI-only: `packaging/windows/install.ps1` passed `"--api-token", $EnrollmentToken` as
two arguments, so a customer install failed the same way for about 1 token in 64, and the guides'
`--api-token <token>` examples did too.

**Fix (branch `fix/api-token-leading-dash`):** `quirk/tokens.py::mint_token()` never returns a
dash-led token and replaces the three `secrets.token_urlsafe(32)` call sites (`console enroll`,
`sensor enroll`, `token generate/rotate`), guarded by `tests/test_tokens.py`; the workflow and
`install.ps1` pass `--api-token=<value>` as one argument; the workflow also fails fast on a
genuinely empty `e2e_token.txt` (defect 1 above); the guides use the `=` form; and
`scripts/branch_ci_state.py`'s `DISPATCH_ADVISORY_JOBS` exception is retired, so the job is
required on dispatches again. Close the ledger row once that is on `main`.
