# Contributing to QU.I.R.K.

Thanks for looking at contributing. This document covers the testing standard every
change is held to — the same standard the `Linux Full Suite` CI job enforces on every
pull request and every push to `main`.

## Running the test suite

To reproduce exactly what CI runs, use:

```bash
pytest -q -m ""
```

The empty `-m ""` matters: `pyproject.toml` sets a repo-wide default of
`addopts = "-m 'not slow'"`, so a bare `pytest -q` skips slow-marked tests and runs a
**narrower** subset than CI does. `pytest -q -m ""` overrides that default and includes
slow tests too, matching the `Linux Full Suite` job's invocation verbatim.

Before running the full suite, install the project with all the same extras CI uses:

```bash
pip install -e ".[all]"
pip install pytest
```

## Installing the pre-commit artifact gate

QUIRK enforces phase-completion artifact hygiene — `VERIFICATION.md` presence,
`VALIDATION.md` freshness, `docs/UAT-SERIES.md` coverage for user-facing plans, and a
destructive-deletion guard for `.planning/phases/` — via a local git hook, not a CI
check: `.planning/` is gitignored on this public repo, so CI never sees it and cannot
enforce anything against it.

Install the hook once per clone:

```bash
git config core.hooksPath .githooks
```

That's it — `git commit` now runs `scripts/verify_phase_gates.py` before every commit.
It's cheap on unrelated commits (the phase-close checks only fire when the staged
`.planning/ROADMAP.md` diff contains a Phase-checkbox flip to complete) and blocks the
commit with a clear message when a gate is violated.

`git commit --no-verify` bypasses this hook entirely — that's git's own designed escape
hatch, not something this hook can prevent. Treat it as a safety net, not a hard
guarantee: a contributor who skips the one-time `core.hooksPath` setup, or who commits
with `--no-verify`, gets zero enforcement, silently.

## Docker containers during `-m ""` runs

`pytest -q -m ""` includes `slow`-marked chaos-lab profile tests, which start Docker
containers whenever a Docker daemon is reachable — this is intentional, since CI's
`ubuntu-latest` runner has Docker preinstalled and genuinely exercises those tests there.
Expect containers to come up and be torn down again (`./lab.sh down`) as part of the run.
A bare `pytest -q` (without the `-m ""` override) deselects `slow` tests and never touches
Docker. If you want to pre-generate the chaos lab's self-signed profile certs ahead of
time, run `./lab.sh certs` from `quantum-chaos-enterprise-lab/` — it materializes every
profile's certs without starting any containers.

## What "green" means

Green means **0 failed**. Skips and xfails are expected and do not make a run red.

Most skips come from optional extras that are deliberately not installed alongside
`.[all]` — `identity` (impacket) and `hw` (pysnmp) are intentionally excluded from the
`all` meta-extra (see `pyproject.toml`), so any test gated on those extras takes its
"optional extra not installed" skip path. Other skips come from tests that need live
infrastructure not available in CI or a local dev sandbox.

Every skip or xfail marker in the suite must be registered in `tests/skip_registry.py`.
This is enforced by `tests/test_skip_registry.py::test_no_unregistered_skips`, an
AST-walking meta-gate that fails the build if a new, unregistered skip/xfail slips in.
If you add a skip or xfail marker, register it in `tests/skip_registry.py` with a
category and a reason in the same change.

Do not treat a specific passed/skipped/xfailed count as a target — those numbers drift
as the suite grows and tests get triaged. The only fixed target is 0 failed.

## Why some tests are quarantined

A number of tests are currently marked `skip` or `xfail(strict=False)` rather than
deleted, because they were individually investigated and dispositioned during the
Phase 149 test-suite triage rather than silently ignored. The full disposition ledger —
every quarantined test, its root cause, and why it is not simply fixed or deleted — is
documented in [docs/test-triage-149.md](docs/test-triage-149.md).

If you're touching a file with a quarantined test in it, read that ledger entry first;
it usually tells you whether your change is expected to un-quarantine the test or is
unrelated.

## CI

The `Linux Full Suite` job in `.github/workflows/python-ci.yml` runs the command above
on `ubuntu-latest` with Python 3.11 on every pull request and every push to `main`. It
has no `continue-on-error` — a newly introduced failing test fails the build. There is
no separate opt-in step; if your PR breaks the suite, the check goes red and blocks
merge.

## Before you open a PR

A short checklist, mirroring the code standards in `CLAUDE.md`:

- Follow PEP 8 for Python changes.
- Run `python -m compileall` on any Python files you touched.
- Run `pytest -q -m ""` locally and confirm it's green before pushing.
- If you changed detection/classification logic, update the relevant
  `labs/*/expected_results.md` file to match.
