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

README.md:104 says "the Semgrep `p/cryptography` ruleset is unavailable, so the source domain reads Not assessed".
**That claim is FALSE when semgrep is not installed.** "Not assessed" only arises from the *raise* path
(`SourceRulesetUnavailable` -> `_wrapped_phase` except branch -> `record_failed`, `run_scan.py:327-338`). The
missing-binary path never raises, returns `[]`, and takes the `record_ran` branch. The same applies to
`docs/report-interpretation.md:1968` ("In 5.28.0, source code scanning always records its phase as `failed`"), which
is also untrue without semgrep; that doc was NOT edited here (it is a synced, master-guide-feeding doc; fold into the
5.28.1 doc pass). Disclosed meanwhile by a new Known-defects line in the repo README (ledger row
`DCL-README-P235-0014`). The published PyPI page (5.28.0, frozen) keeps the old text.

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
