# Contributing to QU.I.R.K.

Thanks for looking at contributing. This document covers the testing standard every
change is held to — the same standard the `Linux Full Suite` CI job enforces on every
pull request and every push to `main`.

## Running the test suite

To select the same tests CI runs (CI uses Python 3.11 on `ubuntu-latest`), use:

```bash
pytest -q -m ""
```

The empty `-m ""` matters: `pyproject.toml` sets a repo-wide default of
`addopts = "-m 'not slow'"`, so a bare `pytest -q` skips slow-marked tests and runs a
**narrower** subset than CI does. `pytest -q -m ""` overrides that default and includes
slow tests too, selecting the same tests as the `Linux Full Suite` job (CI adds `-rs` and
a JUnit report flag on top of this command).

Before running the full suite, install the project with all the same extras CI uses:

```bash
pip install -e ".[all]"
pip install pytest
pip install "resvg-py==0.5.0"
```

The `resvg-py` pin is what lets the brand-asset drift gate render its PNG instead of
skipping; locally that test skips without it, in CI it must run.

CI also sets up Node 24 and runs `npm ci` in `src/dashboard/` before the suite. With npm on
`PATH` and `src/dashboard/node_modules` present, the vitest substitute-execution test in
`tests/test_uat_disposition_integrity.py` runs; without them it skips. To match CI, run
`npm ci` in `src/dashboard/` first.

## Installing the pre-commit artifact gate

This hook is for maintainers; contributors should leave it alone. `.githooks/pre-commit`
runs `scripts/verify_phase_gates.py` on every commit. Its phase-close checks only run when
a commit closes a phase, but its archive check runs on every commit and compares the
tracked roadmap state with the maintainers' unpublished planning records. A fresh clone
does not contain those records, so with the hook installed it rejects every commit there,
even one that touches no planning file, and under a Python without PyYAML it exits with a
`ModuleNotFoundError` traceback instead. CI does not run it, so a contribution never
needs it.

Maintainers install it once per clone:

```bash
git config core.hooksPath .githooks
```

## Docker containers during `-m ""` runs

`pytest -q -m ""` includes `slow`-marked chaos-lab profile tests, which start Docker
containers whenever a Docker daemon is reachable — this is intentional, since CI's
`ubuntu-latest` runner has Docker preinstalled and genuinely exercises those tests there.
Expect containers to come up and be torn down again (`./lab.sh down`) as part of the run.
A bare `pytest -q` (without the `-m ""` override) deselects `slow` tests and never starts
containers. To pre-generate chaos lab certs ahead of time, run `./lab.sh certs` from
`quantum-chaos-enterprise-lab/`. It creates the mTLS CA/client pair and the `email` and
`grpc-tls` profile certs without starting any containers. It does not create the
`broker`, `postgres-tls`, `redis-tls` or `kafka-tls` certs; run
`make -C labs/<profile> certs` from the repository root for each of those.

## What "green" means

Green means **0 failed**. Skips and xfails are expected and do not make a run red.

Most skips come from optional extras that are deliberately not installed alongside
`.[all]` — `identity` (impacket) and `hw` (pysnmp) are intentionally excluded from the
`all` meta-extra (see `pyproject.toml`), so any test gated on those extras skips with a
reason naming the missing package, for example "pysnmp not installed" or "impacket not
installed". Other skips come from tests that need live
infrastructure not available in CI or a local dev sandbox.

Every skip or xfail marker in the suite, apart from the auto-allowed `importorskip` case
described below, must be registered in `tests/skip_registry.py`.
This is enforced by `tests/test_skip_registry.py::test_no_unregistered_skips`, an
AST-walking meta-gate that fails the build if a new, unregistered skip/xfail slips in.

**Entries are keyed by `(file, test_qualname)`, not by line number.** The
qualname is the AST-derived dotted path of the construct's enclosing
`ClassDef`/`FunctionDef` chain — the literal `<module>` is used for module-scope skips.
This means moving a skip within its file, or adding/removing unrelated lines above it,
never re-breaks the gate; only a real change (renaming the test, deleting it, or adding
a genuinely new, unregistered skip) does. If you add a skip or xfail marker, register it
in `tests/skip_registry.py` with the test's `(file, qualname)`, a category, and a reason
in the same change.

The gate is **bidirectional**: a registry entry whose `(file, qualname)` no longer
resolves to a real skip site — because you deleted the skip, renamed the test, or the
test itself was removed — is itself a violation. Deleting or renaming a skipped test
requires removing or re-keying its registry entry in the same change; leaving a stale
entry behind fails the build.

A `pytest.importorskip("<mod>")` whose module maps to a package declared in a
`[project.optional-dependencies]` group in `pyproject.toml` is auto-allowed and needs
**no registry entry at all** — the gate checks this against `pyproject.toml` at
test-run time, so if the module stops being declared as an extra, the gate will ask you
to add one. Every other skip/xfail construct (a plain `pytest.skip`, `@pytest.mark.skip`,
`@pytest.mark.skipif`, `@pytest.mark.xfail`, or an `importorskip` on a module not
declared as an optional extra) still needs an explicit entry.

Do not treat a specific passed/skipped/xfailed count as a target — those numbers drift
as the suite grows and tests get triaged. The only fixed target is 0 failed.

## Why some tests are quarantined

A number of tests are currently marked `skip` or `xfail(strict=False)` rather than
deleted, because they were individually investigated and dispositioned during a
test-suite triage rather than silently ignored. The disposition ledger for that triage —
each test it quarantined, its root cause, and why it is not simply fixed or deleted — is
documented in [docs/test-triage-149.md](docs/test-triage-149.md). Tests quarantined
later are not all named there; `tests/skip_registry.py` records a category and a reason
for every registered skip and xfail.

If you're touching a file with a quarantined test in it, read that ledger entry first;
it usually tells you whether your change is expected to un-quarantine the test or is
unrelated.

## CI

The `Linux Full Suite` job in `.github/workflows/python-ci.yml` runs the command above
on `ubuntu-latest` with Python 3.11 on every pull request and every push to `main`. It
has no `continue-on-error` — a newly introduced failing test fails the build. There is
no separate opt-in step; if your PR breaks the suite, the check goes red and we expect it
fixed before merge. (GitHub branch protection on `main` currently requires only the
`Windows Sensor Smoke` check, so the merge button does not enforce this by itself.)

## Before you open a PR

A short checklist:

- Follow PEP 8 for Python changes.
- Run `python -m compileall` on any Python files you touched.
- Run `pytest -q -m ""` locally and confirm it's green before pushing.
- If you changed detection/classification logic, update the relevant
  `labs/*/expected_results.md` file to match.
