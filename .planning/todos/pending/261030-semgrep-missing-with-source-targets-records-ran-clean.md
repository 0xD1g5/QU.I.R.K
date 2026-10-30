# Missing semgrep with `source_targets` set is recorded as a source scan that ran clean

**Filed:** 2026-10-30 (Phase 235 post-GO code review, finding CR-02; operator decision Q1 "Keep GO, file for 5.28.1 (Recommended)")
**Priority:** P1 for 5.28.1. A false clean on the default state of a fresh install.
**Source:** `.planning/phases/235-release-launch-gate/235-REVIEW.md` CR-02
**Where it lives:** **[package]** `quirk/scanner/source_scanner.py:69-76`, `run_scan.py:3290-3304` (and `_wrapped_phase`, `run_scan.py:288-323`), `quirk/cli/doctor_cmd.py:57-63`; sibling in `quirk/scanner/container_scanner.py:74` (syft).

## The defect

`scan_source_repo` returns `[]` when `shutil.which("semgrep")` is falsy and reports it only through `logger.v`
(`source_scanner.py:69-76`). `_run_source_phase` (`run_scan.py:3290-3304`) does not check for the binary, and
`_wrapped_phase` records `record_ran` for any non-sentinel return (`run_scan.py:318`). Scan Coverage
(`quirk/reports/coverage.py:160`) then shows Source Code as **ran** with zero findings, which reads as a clean repo.
semgrep is not a dependency or extra in `pyproject.toml`, so this is the default on a fresh install, and Phase 235
D-24 made a missing semgrep informational in `quirk doctor`, removing the last exit-code signal.

## README claim check (done 2026-10-30, by reading the code path)

README.md:104 said "the Semgrep `p/cryptography` ruleset is unavailable, so the source domain reads Not assessed".
**That claim was FALSE when semgrep is not installed.** "Not assessed" only arises from the *raise* path
(`SourceRulesetUnavailable` -> `_wrapped_phase` except branch -> `record_failed`, `run_scan.py:327-338`). The
missing-binary path never raises, returns `[]`, and takes the `record_ran` branch. The same applied to
`docs/report-interpretation.md:1968`.

## Status of the wording fixes (updated 2026-10-30)

- DONE, repo README: :104, :155 and :156 name both Semgrep cases (3fff0460). Ledger row `DCL-README-P235-0014` /
  `DCL-README-P235-0009`.
- DONE, `docs/report-interpretation.md` (~:1968): fixed in 0bfe552f.
- DONE, guides (operator decision "Fix all, one more CI round (Recommended)"; commit: the `docs(235)` commit that
  carries this todo update, find it with `git log --oneline -3 -- docs/architecture.md`): `docs/architecture.md:81`,
  `docs/operators-guide.md:1099` and `:1221`, `docs/connectors/git.md:12`, `docs/quirk-overview.md:75`,
  `docs/chaos-lab.md:319` and the port-table row at :1635 now name both cases; `docs/quirk-master-guide.md`
  regenerated; vault re-synced; 7 doc-claim-ledger rows re-anchored.
- DONE, GitHub release v5.28.0 body: the orchestrator appended a "Correction (2026-10-30)" paragraph with
  `gh release edit`; the original text is unchanged.
- 5.28.1 TASK: correct the PyPI long description. It is frozen at 5.28.0 and says only "so the source domain reads
  Not assessed"; it comes free with the corrected README in the 5.28.1 wheel, so verify the 5.28.1 PyPI page after
  publishing.
- 5.28.1 TASK: correct the CHANGELOG `[5.28.0]` Known-defects wording (source scanning "records a 'ruleset
  unavailable' scan error and reads Not assessed" is unqualified), or add a 5.28.1 note that states both cases.
- The operator override for SC4 ("Override: accept until 5.28.1 (Recommended)") covers the frozen PyPI description
  until then.

## Candidate fix

```python
def _run_source_phase():
    ...
    if not shutil.which("semgrep"):
        return _recorder.skip("missing-binary", "semgrep is not installed (QRK-INSTALL-008)")
    return scan_source_targets(...)
```

Optionally make doctor print a yellow "configured but missing" line (or fail) when `enable_source` /
`enable_container` is on and the binary is absent. Same pattern for syft. Then correct README:104 / the report
interpretation text to describe both states, and remove the README disclosure line once fixed.

## Feasibility & Effort

- **Feasibility: CONFIRMED by code read; fix LIKELY.** The skip mechanism (`_recorder.skip`) already exists and is
  used three lines above. Not run end-to-end here (no source-phase run was performed in this session).
- **Effort: S** for source + container skip and tests; **M** if doctor gains config-aware checks.
- **Unknowns:** whether `skip("missing-binary", ...)` renders sensibly in coverage, report and dashboard (reason enum
  may need a new value); whether other optional-binary phases share the shape.
- **Spike needed?** No; one in-process run with `PATH` stripped would confirm the current behaviour first.
