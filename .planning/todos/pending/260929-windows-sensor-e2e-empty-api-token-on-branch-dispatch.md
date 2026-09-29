# Windows Sensor E2E fails with an empty `--api-token` on a branch `workflow_dispatch`

**Filed:** 2026-09-29 (during Phase 216 close-out)
**Priority:** P2 — a required-ish CI job, red on a phase branch, green on `main`
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
