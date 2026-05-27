---
phase: 116-windows-packaging-spike
plan: "01"
subsystem: ci/packaging
tags: [pyinstaller, windows, ci, freeze_support, spike]
dependency_graph:
  requires: []
  provides: [windows-packaging-spike CI job, freeze_support guard]
  affects: [.github/workflows/python-ci.yml, run_scan.py]
tech_stack:
  added: []
  patterns: [non-blocking CI job (continue-on-error), PyInstaller onefile spike]
key_files:
  created: []
  modified:
    - run_scan.py
    - .github/workflows/python-ci.yml
decisions:
  - "D-01: freeze run_scan.py (the .py file, not module:function) as PyInstaller entry target"
  - "D-02: continue-on-error: true at job AND build-step level so spike cannot gate pipeline"
  - "D-03: pyinstaller==6.20.0 installed inline in CI step only; absent from pyproject.toml"
  - "D-06: no .spec/EXE/installer/NSIS committed; EXE only ever exists as CI artifact"
metrics:
  duration_minutes: 10
  completed: 2026-05-27
  tasks_completed: 2
  tasks_total: 2
  files_changed: 2
---

# Phase 116 Plan 01: Windows Packaging Spike CI Job + freeze_support Summary

**One-liner:** Non-blocking `windows-packaging-spike` CI job runs PyInstaller 6.20.0 `--onefile` build of `run_scan.py` on `windows-latest` and uploads build evidence; `multiprocessing.freeze_support()` guard added to prevent Windows frozen spawn recursion.

## What Was Built

### Task 1: freeze_support guard in run_scan.py

Added `import multiprocessing` (alphabetically placed in stdlib block between `json` and `os`) and inserted `multiprocessing.freeze_support()` as the first statement inside the `if __name__ == "__main__":` block, immediately before `_run_main_with_job_guard()`. This is a two-line change required by PyInstaller on Windows: when a frozen EXE uses the `spawn` start method (Windows default), the EXE re-executes itself to launch worker processes; `freeze_support()` intercepts that re-entry and prevents recursive main-module import. `_run_main_with_job_guard` is unchanged.

Verified: `python -m compileall -q run_scan.py` exits 0; `python run_scan.py --help` exits 0.

**Commit:** 723f8ca

### Task 2: Non-blocking windows-packaging-spike CI job

Added a new top-level job `windows-packaging-spike` to `.github/workflows/python-ci.yml` after `windows-sensor-smoke`, mirroring its checkout/setup-python-3.11/editable-install pattern. Key properties:

- `continue-on-error: true` at **job level** (D-02: spike failure must not gate the pipeline)
- `pip install pyinstaller==6.20.0` inline in a CI step; **not** added to `pyproject.toml` (D-03)
- PyInstaller flags: `--onefile --name quirk`, `--collect-all quirk/sqlalchemy/fastapi`, `--copy-metadata quirk-scanner`, `--hidden-import` entries for SQLAlchemy SQLite dialect + uvicorn submodules, three `--add-data` entries using the Windows `;` separator
- Build step also has `continue-on-error: true` so the evidence-upload step always runs
- `Tee-Object -FilePath pyinstaller-build.log` captures build output; PowerShell backtick (`` ` ``) line continuations used throughout (windows-latest default shell is pwsh)
- Report step prints `RESULT: BUILD_SUCCESS` with EXE size (MB) or `RESULT: BUILD_FAILED`
- `actions/upload-artifact@v4` with `if: always()` uploads `pyinstaller-build.log`, `build/quirk/warn-quirk.txt`, `dist/quirk.exe` with `retention-days: 30`

No `.spec`, EXE, installer, or NSIS file is committed (D-06 scope guard).

**Commit:** 300ec19

## Deviations from Plan

None — plan executed exactly as written. The CI YAML precisely matches the `116-RESEARCH.md §Code Examples (CI Job YAML)` source-of-truth block (PowerShell backtick continuations, `;` separator, artifact upload). The `---` separator in Build/FAILED messages was used instead of `—` to avoid Unicode in the PowerShell string; functionally identical.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes introduced. The CI job runs in a GitHub-hosted VM; the uploaded EXE is a transient artifact (T-116-02 disposition: `retention-days: 30`, evidence-only). T-116-01 mitigated: pyinstaller pinned at `==6.20.0`, slopcheck [OK]. T-116-04 mitigated: `continue-on-error: true` at both job and step level.

## Known Stubs

None. This plan adds CI infrastructure and a Python guard; no data-bound UI rendering or placeholder text.

## Self-Check: PASSED

- `run_scan.py` — exists, imports multiprocessing, freeze_support in __main__ block, compiles clean
- `.github/workflows/python-ci.yml` — valid YAML, contains `windows-packaging-spike` job
- Commit 723f8ca — exists
- Commit 300ec19 — exists
- `grep -c pyinstaller pyproject.toml` — returns 0
- No `.spec`/`.nsi`/`dist/`/`build/` committed
