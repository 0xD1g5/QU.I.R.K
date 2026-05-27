---
phase: 116-windows-packaging-spike
verified: 2026-05-27T00:00:00Z
status: human_needed
score: 9/9 must-haves verified (gap closed 2026-05-27)
overrides_applied: 0
gap_closure: "The Phase 108 hardgate test was narrowed to scope its literal continue-on-error check to the windows-sensor-smoke job block only. The smoke hard gate stays protected; the legitimately non-blocking windows-packaging-spike job (D-02) is now allowed. All 7 hardgate tests pass. Remaining: live windows-latest CI build (human_needed — runs on push)."
gaps:
  - truth: "python -m pytest tests/ -q passes with no regression from Phase 116 changes"
    status: failed
    reason: "Phase 116 added `continue-on-error: true` to the new windows-packaging-spike CI job, which breaks the pre-existing Phase 108 hard-gate test `test_no_continue_on_error_literal_in_file` in tests/test_windows_ci_hardgate.py (line 90-97). That test does a whole-file text scan banning the literal string anywhere in python-ci.yml. The intent of the test is to protect the windows-sensor-smoke job from being silently softened; it was written before any second job with continue-on-error existed. The test must be narrowed to scope the file-wide check to the windows-sensor-smoke job only, or a per-job allowlist must be added."
    artifacts:
      - path: ".github/workflows/python-ci.yml"
        issue: "Contains `continue-on-error: true` (required for the spike job per D-02), which triggers the Phase 108 whole-file ban"
      - path: "tests/test_windows_ci_hardgate.py"
        issue: "test_no_continue_on_error_literal_in_file (line 90-97) scans the entire CI file for the literal string; this was correct before Phase 116 added a second job that legitimately uses continue-on-error"
    missing:
      - "Narrow `test_no_continue_on_error_literal_in_file` to check only the `windows-sensor-smoke` job (or maintain a per-job allowlist), rather than the whole CI file text, so the spike job's `continue-on-error: true` does not trigger it"
human_verification:
  - test: "Observe the windows-packaging-spike CI job result after pushing this branch"
    expected: "Job completes on windows-latest; pyinstaller-spike-evidence artifact is uploaded containing pyinstaller-build.log, build/quirk/warn-quirk.txt, and dist/quirk.exe (or the build log with the RESULT: BUILD_FAILED line). Update the RESULT placeholder in docs/windows-packaging-spike.md with the observed outcome."
    why_human: "The windows-packaging-spike CI job only runs on push/PR to the GitHub Actions windows-latest runner. The branch has not been pushed yet. The live build result cannot be verified locally."
---

# Phase 116: Windows Packaging Spike Verification Report

**Phase Goal:** Produce a written, evidence-backed feasibility + sizing assessment for packaging the QUIRK sensor as a PyInstaller frozen EXE hosted as a Windows Scheduled Task (or Service), validated on windows-latest CI, ending in a go/no-go recommendation and v5.6 effort estimate. No production packaging artifact ships.
**Verified:** 2026-05-27
**Status:** gaps_found
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | docs/windows-packaging-spike.md exists and covers all 5 WINPKG-01 criterion-1 topics: PyInstaller spec viability, hidden-import surface, Scheduled-Task-vs-Service, CI validation results, v5.6 effort estimate | VERIFIED | File exists at 315 non-empty lines; all 5 sections present at lines 20, 66, 138, 194, 265 |
| 2 | Assessment ends with a single unambiguous GO/NO-GO/DEFER line plus rationale | VERIFIED | `## Recommendation` at line 292; `**GO (conditional on live CI build)**` at line 294 with rationale citing D-05 threshold |
| 3 | Scheduled Task recommended as primary v5.6 host model; NSSM Windows Service documented as always-on alternative | VERIFIED | `## Windows Host Model` section line 138; trade-off table; "Scheduled Task recommended as primary (D-04)"; `schtasks` setup command and `nssm install` command both present |
| 4 | --onedir vs --onefile trade-off documented; --onedir recommended for v5.6 production | VERIFIED | `### --onefile vs. --onedir Trade-off` table present; "Recommendation for v5.6: Use `--onedir`" present |
| 5 | Assessment cites windows-packaging-spike CI job + pyinstaller-spike-evidence artifact; carries evidence-only / not-for-production warning (D-06) | VERIFIED | CI job cited (commit 300ec19); `pyinstaller-spike-evidence` artifact cited; `### Evidence-Only Warning (D-06)` section with explicit "CI EXE is evidence-only and is NOT a production binary" |
| 6 | docs/UAT-SERIES.md has a Series 116 section and Obsidian vault copy is synced | VERIFIED | `## UAT Series 116 — Windows Packaging Spike (Phase 116)` present; vault file at `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md` exists with Series 116 and QU.I.R.K. frontmatter |
| 7 | windows-packaging-spike CI job: continue-on-error true, runs-on windows-latest, pyinstaller==6.20.0 inline install, full flag set with Windows `;` separator, upload-artifact step | VERIFIED | YAML parses cleanly; job-level `continue-on-error: true`; `runs-on: windows-latest`; `pip install pyinstaller==6.20.0`; `--collect-all sqlalchemy`, `--collect-all fastapi`, `--copy-metadata quirk-scanner`, `--hidden-import sqlalchemy.dialects.sqlite`, all 3 `--add-data` entries with `;` separator; `actions/upload-artifact@v4` with `if: always()` |
| 8 | pyinstaller NOT in pyproject.toml (D-03) | VERIFIED | `grep -c pyinstaller pyproject.toml` returns 0 |
| 9 | Full pytest regression: no tests broken by Phase 116 changes | FAILED | `test_windows_ci_hardgate.py::test_no_continue_on_error_literal_in_file` fails; Phase 116 added `continue-on-error: true` to the CI file (required for the spike job per D-02), triggering the Phase 108 whole-file ban; 45 other failures are all pre-existing and unrelated to the 13 files Phase 116 modified |

**Score:** 8/9 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `docs/windows-packaging-spike.md` | Five-topic feasibility assessment with go/no-go | VERIFIED | 315 non-empty lines; all 5 sections, Recommendation section, GO conditional, evidence-only warning, illustrative .spec appendix |
| `.github/workflows/python-ci.yml` | windows-packaging-spike job, non-blocking, full flag set | VERIFIED | Job exists; continue-on-error: true at job and step level; all required flags and upload step present; YAML valid |
| `run_scan.py` | freeze_support() guard in __main__ block | VERIFIED | `import multiprocessing` at line 3; `multiprocessing.freeze_support()` at line 2256, first statement in `if __name__ == "__main__"` block |
| `docs/UAT-SERIES.md` | Series 116 section | VERIFIED | Section `## UAT Series 116 — Windows Packaging Spike (Phase 116)` present; Last Updated: 2026-05-27 |
| `tests/test_windows_ci_hardgate.py` | Should still pass after Phase 116 changes | STUB/BROKEN | `test_no_continue_on_error_literal_in_file` fails — whole-file text ban on `continue-on-error: true` conflicts with the legitimately-added spike job |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `.github/workflows/python-ci.yml` | `run_scan.py` | `pyinstaller --onefile ... run_scan.py` | VERIFIED | `run_scan.py` present as freeze target in the build step |
| `.github/workflows/python-ci.yml` | `pyinstaller-spike-evidence` artifact | `actions/upload-artifact@v4` | VERIFIED | Upload step present with `if: always()` and `retention-days: 30` |
| `docs/windows-packaging-spike.md` | `windows-packaging-spike` CI job | cites job name + pyinstaller-spike-evidence | VERIFIED | Both the job name and artifact name are cited in the CI Validation Results section |

---

### Data-Flow Trace (Level 4)

Not applicable — this phase produces only a documentation file and CI YAML. No dynamic data rendering components.

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| run_scan.py compiles after freeze_support addition | `python -m compileall -q run_scan.py` | exit 0 | PASS |
| run_scan.py --help still works | `python run_scan.py --help` | exit 0 | PASS |
| CI YAML parses as valid YAML | `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/python-ci.yml'))"` | exit 0, YAML VALID | PASS |
| pyinstaller absent from pyproject.toml | `grep -c pyinstaller pyproject.toml` | 0 | PASS |
| Scope guard: no .spec/.exe/.nsi/installer committed | `git ls-files \| grep -iE '\.(spec\|nsi\|exe)$\|installer'` | (empty) | PASS |
| Regression test suite | `python -m pytest tests/ -q` | 46 failed (1 from Phase 116, 45 pre-existing) | FAIL — `test_no_continue_on_error_literal_in_file` is a Phase 116 regression |

---

### Probe Execution

No probes declared. Not a migration/tooling phase with conventional probe scripts.

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| WINPKG-01 | 116-01, 116-02 | Written feasibility and sizing assessment; PyInstaller frozen EXE on windows-latest CI; go/no-go recommendation; effort estimate; no production packaging artifact | SATISFIED | docs/windows-packaging-spike.md covers all 5 criterion topics; GO conditional recommendation present; no .spec/.exe committed; REQUIREMENTS.md row marked [x] Complete |

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `docs/windows-packaging-spike.md` | ~216 | "RESULT (to be confirmed from pyinstaller-spike-evidence artifact after first push)" | INFO (intentional) | This is a documented intentional placeholder per the plan's design (CI result not yet observed before push); the doc explicitly instructs how to fill it; not a code stub |
| `.github/workflows/python-ci.yml` | ~32 and ~61 | `continue-on-error: true` | BLOCKER | Breaks `test_no_continue_on_error_literal_in_file` from Phase 108; legitimate per D-02 but requires the hardgate test to be narrowed to scope the ban to `windows-sensor-smoke` only |

No TBD/FIXME/XXX unreferenced debt markers found in Phase 116-modified files.

---

### Human Verification Required

#### 1. Live windows-latest CI Build Result

**Test:** Push the branch and observe the `windows-packaging-spike` CI job on GitHub Actions
**Expected:** Job completes on `windows-latest`; `pyinstaller-spike-evidence` artifact is uploaded containing `pyinstaller-build.log`, `build/quirk/warn-quirk.txt`, and either `dist/quirk.exe` (BUILD_SUCCESS) or the build log with a `RESULT: BUILD_FAILED` line. After observing the result, update the `RESULT (to be confirmed from pyinstaller-spike-evidence artifact after first push)` placeholder in `docs/windows-packaging-spike.md §CI Validation Results`.
**Why human:** The `windows-packaging-spike` CI job only runs on push/PR to the GitHub-hosted `windows-latest` runner. The branch has not been pushed. The live build result cannot be observed locally.

---

### Gaps Summary

**One genuine regression** blocks the phase from fully passing:

**Test regression: `test_no_continue_on_error_literal_in_file`**

Phase 108 installed a whole-file guard (`tests/test_windows_ci_hardgate.py` line 90-97) that bans the literal string `continue-on-error: true` from appearing anywhere in `python-ci.yml`. The intent was to prevent silent softening of the `windows-sensor-smoke` hard gate. Phase 116 legitimately added `continue-on-error: true` to the new spike job per D-02 (spike must not gate the pipeline). The test's implementation is now too broad — it bans a legitimate use in a different job.

**Fix required:** Narrow `test_no_continue_on_error_literal_in_file` to check only the `windows-sensor-smoke` job (using the same YAML-parsed approach the other tests use), rather than performing a whole-file text scan. The other six tests in the same file already correctly scope to `JOB_NAME = "windows-sensor-smoke"` — only the last test uses raw text search. This is a 3-line fix.

All 45 other test failures are pre-existing and unrelated to Phase 116: they span broker scanner, CBOM motion golden snapshots, version string mismatches, openapi scanner, dashboard schema, QRAMM evidence bridge, and other areas — none of which involve any of the 13 files Phase 116 modified.

---

_Verified: 2026-05-27_
_Verifier: Claude (gsd-verifier)_
