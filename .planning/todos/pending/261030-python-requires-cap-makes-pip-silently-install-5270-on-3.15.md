# `requires-python = "<3.15"` makes pip on Python 3.15 silently install 5.27.0

**Filed:** 2026-10-30 (Phase 235 post-GO code review, finding CR-01; operator decision Q1 "Keep GO, file for 5.28.1 (Recommended)")
**Priority:** P1 for 5.28.1. A 3.15 user following the unpinned README Quick Start gets the previous release with no error.
**Source:** `.planning/phases/235-release-launch-gate/235-REVIEW.md` CR-01 (+ IN-01)
**Where it lives:** **[package]** `pyproject.toml:10`, `quirk/cli/doctor_cmd.py`, `quirk/errors.py:53`; plus **[tooling]** the `linux-3.15-neg` smoke leg (`scripts/release_smoke_inner.sh:213-220`).

## The defect

pip treats `Requires-Python` as a candidate filter, not a refusal. On a 3.15 interpreter it skips 5.28.0 (capped
`<3.15`) and backtracks to the newest release with no cap. Reproduced by the orchestrator 2026-10-30 in
`python:3.15-slim` (Python 3.15.2):

```
pip install --dry-run --no-deps quirk-scanner   ->  Would install quirk-scanner-5.27.0
pip download quirk-scanner                      ->  quirk_scanner-5.27.0-py3-none-any.whl
```

The `linux-3.15-neg` smoke leg cannot see this: it pins `==5.28.0` (or the wheel path), so it proves only that the
*pinned* install is refused. Yanking 5.27.0 does not fix it, it moves pip to 5.25.0.

IN-01 rides along: doctor's Python check has no upper bound, so it shows green on 3.15; 3.10 is only exercised by the
manual smoke leg (every `python-ci.yml` job is 3.11); `quirk/__init__.py:20` imports `tomllib` (3.11+) in the
unpackaged-run fallback, so a bare clone on 3.10 fails at `import quirk`.

## Candidate fix

1. `pyproject.toml`: `requires-python = ">=3.10"` (drop the cap).
2. Enforce the upper bound at runtime in `quirk/cli/doctor_cmd.py` (`_PYTHON_MAX_EXCLUSIVE = (3, 15)`; ok only when
   `_PYTHON_MIN <= sys.version_info[:2] < _PYTHON_MAX_EXCLUSIVE`), keeping INSTALL-005's "3.10 to 3.14" text true.
3. Smoke-leg change: in `linux-3.15-neg` add an **unpinned** `pip install --dry-run quirk-scanner` assertion that the
   resolved version is not older than the version under test (or that nothing is installed/refused), alongside the
   existing pinned-refusal check.
4. IN-01: guard the `tomllib` import (`except ModuleNotFoundError`), and consider a 3.10 smoke job in CI.

Open question to settle first: with the cap gone, 3.15 users get 5.28.1 installed and a runtime warning instead of a
hard refusal. Confirm that is the intended behaviour (it is the only way to stop pip backtracking).

## Feasibility & Effort

- **Feasibility: CONFIRMED defect (live reproduction); fix LIKELY.** The pip backtracking behaviour is standard, and
  dropping the cap is the usual remedy. The runtime check is a two-line change in an existing function.
- **Effort: S.** One pyproject line, a doctor check plus its test, one smoke-leg assertion. The release itself
  (5.28.1 build, tag, publish) is not counted here.
- **Unknowns:** whether 3.15 actually runs QU.I.R.K. (the cap was precautionary; the smoke leg has only proven the
  refusal, not a working 3.15 run); whether any consumer relies on the cap as the refusal signal.
- **Spike needed?** No for the pyproject change. A 3.15 run of the suite would answer the unknown but is optional.

## Do not

- Do not yank 5.27.0 as the fix; pip then resolves 5.25.0.
- Do not announce 3.15 support. The announcement draft says Python 3.10 to 3.14.
